"""
Healthcare LangChain Agent

Provides a LangChain-powered agent wrapper that uses the local Ollama
chat model via our existing `src/local_llm/ollama_client` helpers.
The agent builds no network connections on import; construction is
lightweight and runtime-safe for PHI.
"""

from __future__ import annotations

import contextlib
import os as _os
from pathlib import Path
from typing import Any

import yaml
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.langchain.healthcare_tools import create_healthcare_tools

logger = get_healthcare_logger("core.langchain.agents")
# Dedicated logger for LangChain's thought process and reasoning
thought_logger = get_healthcare_logger("langchain.thought_process")


class HealthcareLangChainAgent(BaseHealthcareAgent):
    """LangChain-powered healthcare agent with configurable behavior."""

    def __init__(
        self,
        mcp_client,
        chat_model: BaseChatModel | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        verbose: bool = False,
        max_iterations: int = 5,
        memory_max_token_limit: int = 2000,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.5,
        agent_manager: Any | None = None,
    ):
        """Initialize the healthcare LangChain agent.

        Args:
            mcp_client: MCP client for tool execution
            model: Ollama model name (default: llama3.1:8b)
            temperature: LLM temperature for response generation
            verbose: Enable verbose logging
            max_iterations: Maximum agent iterations
            memory_max_token_limit: Maximum tokens for conversation memory
            tool_max_retries: Maximum retries for tool calls
            tool_retry_base_delay: Base delay between tool retries
        """
        # PHASE 1.3 BASEHEALTHCAREAGENT INTEGRATION: Initialize healthcare framework
        super().__init__(
            mcp_client=mcp_client, agent_name="langchain_healthcare", agent_type="langchain_medical",
        )

        # LangChain-specific configuration with YAML-first precedence
        self.verbose = verbose or _os.getenv("HEALTHCARE_AGENT_DEBUG", "").lower() in {
            "1",
            "true",
            "yes",
        }

        def _load_yaml(path: Path) -> dict[str, Any]:
            try:
                if path.exists():
                    with open(path) as f:
                        data = yaml.safe_load(f) or {}
                        if isinstance(data, dict):
                            return data
            except Exception:
                pass
            return {}

        config_dir = Path(__file__).parent.parent.parent / "config"
        agent_cfg = _load_yaml(config_dir / "agent_settings.yml")
        orch_cfg = _load_yaml(config_dir / "orchestrator.yml")

        # Resolve iterations: YAML > ENV > constructor default
        yaml_max_iter = None
        try:
            # Prefer query_engine.enhanced_medical_query.max_iterations when present
            qe = (
                agent_cfg.get("query_engine", {}).get("enhanced_medical_query", {})
                if agent_cfg
                else {}
            )
            if isinstance(qe, dict) and qe.get("max_iterations") is not None:
                yaml_max_iter = int(qe.get("max_iterations"))
            else:
                # Fallback to a general clinical_research limit if defined
                cr = (
                    agent_cfg.get("agent_limits", {}).get("clinical_research", {})
                    if agent_cfg
                    else {}
                )
                if isinstance(cr, dict) and cr.get("max_iterations") is not None:
                    yaml_max_iter = int(cr.get("max_iterations"))
        except Exception:
            yaml_max_iter = None

        try:
            env_max_iter = int(_os.getenv("HEALTHCARE_AGENT_MAX_ITERATIONS", str(max_iterations)))
        except ValueError:
            env_max_iter = max_iterations

        self.max_iterations = int(yaml_max_iter if yaml_max_iter is not None else env_max_iter)
        self.tool_max_retries = tool_max_retries
        self.tool_retry_base_delay = tool_retry_base_delay

        # Build or use provided LLM using proper configuration system
        from src.local_llm.ollama_client import OllamaConfig, build_chat_model

        # If caller supplied a chat_model directly, prefer it
        provided_llm: BaseChatModel | None = chat_model
        # Back-compat: if a BaseChatModel was accidentally passed into `model`, accept it
        if provided_llm is None and model is not None and isinstance(model, BaseChatModel):
            provided_llm = model  # type: ignore[assignment]
            model = None

        if provided_llm is None:
            # Load model configuration from config files
            config_dir2 = Path(__file__).parent.parent.parent / "config"
            models_config_path = config_dir2 / "models.yml"

            # Default model from config
            default_model = "llama3.1:8b"
            default_temperature = temperature

            try:
                if models_config_path.exists():
                    with open(models_config_path) as f:
                        models_config = yaml.safe_load(f)

                    # Use healthcare LLM from config
                    default_model = models_config.get("primary_models", {}).get(
                        "healthcare_llm", default_model,
                    )

                    # Use healthcare reasoning parameters if available
                    reasoning_params = models_config.get("model_parameters", {}).get(
                        "healthcare_reasoning", {},
                    )
                    if isinstance(reasoning_params, dict):
                        default_temperature = reasoning_params.get(
                            "temperature", default_temperature,
                        )
            except Exception as e:
                logger.warning(f"Could not load models config, using defaults: {e}")

            # Create Ollama configuration
            config = OllamaConfig(
                model=model or default_model,
                temperature=default_temperature,
                base_url=_os.getenv("OLLAMA_URL", "http://172.20.0.10:11434"),
                num_ctx=4096,  # Context window size
            )

            # Build the chat model
            self.llm = build_chat_model(config)
            logger.info(f"Initialized LangChain agent with model: {config.model}")
        else:
            self.llm = provided_llm
            logger.info("Initialized LangChain agent with provided chat_model instance")

        self.show_agent_header = True
        # Default timeouts, can be tuned via env for clinical searches
        try:
            self.per_agent_default_timeout = float(
                _os.getenv("HEALTHCARE_AGENT_TIMEOUT_DEFAULT", "30"),
            )
        except ValueError:
            self.per_agent_default_timeout = 30.0
        try:
            self.per_agent_hard_cap = float(_os.getenv("HEALTHCARE_AGENT_TIMEOUT_HARDCAP", "90"))
        except ValueError:
            self.per_agent_hard_cap = 90.0

        # Tools - Agent-first architecture
        self.tools = create_healthcare_tools(
            mcp_client, agent_manager, max_retries=int(tool_max_retries),
        )
        # ReAct prompt template (solves agent_scratchpad issues)
        # Use official ReAct prompt from hub per handoff document
        from langchain import hub

        prompt = hub.pull("hwchase17/react")

        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

        # Configure AgentExecutor with ReAct agent and parsing error handling
        # Optional max execution time for AgentExecutor (seconds). 0 disables.
        max_exec_time: float | None
        # YAML-first: orchestrator timeouts.per_agent_hard_cap, else ENV, else None
        try:
            yaml_hard_cap = None
            if isinstance(orch_cfg, dict):
                tmo2 = orch_cfg.get("timeouts", {})
                if isinstance(tmo2, dict) and tmo2.get("per_agent_hard_cap") is not None:
                    yaml_hard_cap = float(tmo2.get("per_agent_hard_cap"))
            max_exec_env = float(_os.getenv("HEALTHCARE_AGENT_MAX_EXECUTION_SEC", "0"))
            max_exec_time = (
                yaml_hard_cap
                if (yaml_hard_cap is not None and yaml_hard_cap > 0)
                else (max_exec_env if max_exec_env > 0 else None)
            )
        except Exception:
            max_exec_time = None

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # Enable for debugging
            max_iterations=self.max_iterations,  # Use dynamic iterations parameter (env-aware)
            max_execution_time=max_exec_time,  # Optional wall-clock limit
            handle_parsing_errors="Check your output and make sure it conforms!",  # Specific error message per handoff
            return_intermediate_steps=True,
            # NO memory parameter per handoff document
        )

        # Internal debug callback for detailed tracing
        class _LangchainAgentDebugCallback(BaseCallbackHandler):
            def __init__(self, enabled: bool = False) -> None:
                self.enabled = enabled

            # Agent callbacks for thought process
            def on_agent_action(self, action, **kwargs):
                """Capture agent's reasoning and action decisions"""
                if not self.enabled:
                    return
                try:
                    thought_logger.info(f"🧠 AGENT REASONING: {action.log}")
                    thought_logger.info(
                        f"🔧 TOOL SELECTED: {action.tool} with input: {str(action.tool_input)[:200]}",
                    )
                except Exception:
                    pass

            def on_agent_finish(self, finish, **kwargs):
                """Capture final decision and output"""
                if not self.enabled:
                    return
                try:
                    thought_logger.info(f"✅ AGENT CONCLUDED: {finish.log}")
                    thought_logger.info(f"📝 FINAL OUTPUT: {str(finish.return_values)[:300]}")
                except Exception:
                    pass

            # LLM callbacks
            def on_llm_start(self, serialized, prompts, **kwargs):
                if not self.enabled:
                    return
                with contextlib.suppress(Exception):
                    thought_logger.debug(f"🤔 LLM PROMPT: {str(prompts)[:500]}")

            def on_llm_end(self, response, **kwargs):
                if not self.enabled:
                    return
                try:
                    txt = getattr(response, "content", "") or str(response)
                    thought_logger.debug(f"🧠 LLM RESPONSE: {str(txt)[:300]}")
                except Exception:
                    pass

            def on_llm_error(self, error, **kwargs):
                with contextlib.suppress(Exception):
                    logger.error("LLM error", extra={"healthcare_context": {"error": str(error)}})

            # Tool callbacks
            def on_tool_start(self, serialized, input_str, **kwargs):
                if not self.enabled:
                    return
                try:
                    name = None
                    try:
                        name = (serialized or {}).get("name")
                    except Exception:
                        name = None
                    logger.debug(
                        "Tool start",
                        extra={
                            "healthcare_context": {
                                "name": name,
                                "input_preview": str(input_str)[:200],
                            },
                        },
                    )
                except Exception:
                    pass

            def on_tool_end(self, output, **kwargs):
                if not self.enabled:
                    return
                with contextlib.suppress(Exception):
                    logger.debug(
                        "Tool end",
                        extra={"healthcare_context": {"output_preview": str(output)[:200]}},
                    )

            def on_tool_error(self, error, **kwargs):
                with contextlib.suppress(Exception):
                    logger.error("Tool error", extra={"healthcare_context": {"error": str(error)}})

            # Chain callbacks
            def on_chain_start(self, serialized, inputs, **kwargs):
                if not self.enabled:
                    return
                with contextlib.suppress(Exception):
                    logger.debug(
                        "Chain start",
                        extra={
                            "healthcare_context": {
                                "inputs_keys": list(inputs.keys())
                                if isinstance(inputs, dict)
                                else [],
                            },
                        },
                    )

            def on_chain_end(self, outputs, **kwargs):
                if not self.enabled:
                    return
                with contextlib.suppress(Exception):
                    logger.debug(
                        "Chain end",
                        extra={
                            "healthcare_context": {
                                "outputs_keys": list(outputs.keys())
                                if isinstance(outputs, dict)
                                else [],
                            },
                        },
                    )

            def on_chain_error(self, error, **kwargs):
                with contextlib.suppress(Exception):
                    logger.error("Chain error", extra={"healthcare_context": {"error": str(error)}})

        self._debug_callback = _LangchainAgentDebugCallback(enabled=self.verbose)

    async def process(
        self, query: str, *, context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a query with tool access and provenance metadata."""
        try:
            # CRITICAL: Only pass 'input' - no other keys
            # AgentExecutor handles agent_scratchpad internally
            input_data = {"input": query}

            if self.verbose:
                with contextlib.suppress(Exception):
                    logger.debug(
                        "AgentExecutor input prepared",
                        extra={
                            "healthcare_context": {
                                "keys": list(input_data.keys()),
                                "input_type": type(input_data["input"]).__name__,
                            },
                        },
                    )

            # Execute with thought process callback for debugging
            config = RunnableConfig(callbacks=[self._debug_callback]) if self.verbose else None
            result = await self.executor.ainvoke(input_data, config=config)

            # Log the intermediate steps for debugging
            if self.verbose and result.get("intermediate_steps"):
                thought_logger.info(
                    f"🔄 ITERATION COUNT: {len(result['intermediate_steps'])} steps",
                )
                for i, (action, observation) in enumerate(result["intermediate_steps"]):
                    thought_logger.info(
                        f"🔄 STEP {i + 1}: {action.tool} -> {str(observation)[:200]}",
                    )

            agent_name = "medical_search"  # default label until router is added
            formatted = result.get("output", "")
            if self.show_agent_header:
                formatted = (
                    f"🤖 {agent_name.replace('_', ' ').title()} Agent Response:\n\n" + formatted
                )

            logger.info(f"LangChain agent processing successful. Output length: {len(formatted)}")
            return {
                "success": True,
                "formatted_summary": formatted,
                "intermediate_steps": result.get("intermediate_steps", []),
                "agent_name": agent_name,
            }
        except Exception as e:
            # Rich error with stack and input typing to isolate prompt var issues
            import linecache
            import traceback

            tb = e.__traceback__
            frames: list[dict[str, Any]] = []
            while tb is not None:
                frame = tb.tb_frame
                lineno = tb.tb_lineno
                filename = frame.f_code.co_filename
                funcname = frame.f_code.co_name
                line = linecache.getline(filename, lineno).rstrip("\n")
                frames.append(
                    {
                        "file": filename,
                        "line": lineno,
                        "function": funcname,
                        "code": line,
                    },
                )
                tb = tb.tb_next

            # Prefer the deepest in-repo frame for faster pinpointing
            repo_root_indicator = "/home/intelluxe/"
            chosen: dict[str, Any] | None = None
            for fr in reversed(frames):
                if repo_root_indicator in fr["file"]:
                    chosen = fr
                    break
            if chosen is None and frames:
                chosen = frames[-1]

            error_details = {
                "message": str(e),
                "type": type(e).__name__,
                "frame": chosen,
                "stack": traceback.format_exc(),
            }

            try:
                logger.exception(
                    "LangChain agent processing failed",
                    extra={"healthcare_context": error_details},
                )
                # Also log the full error details directly for debugging
                logger.exception(f"DETAILED ERROR: {error_details['message']}")
                logger.exception(f"ERROR TYPE: {error_details['type']}")
                if chosen:
                    logger.exception(
                        f"ERROR LOCATION: {chosen['file']}:{chosen['line']} in {chosen['function']}()",
                    )
                    logger.exception(f"ERROR CODE: {chosen['code']}")
                logger.exception(f"FULL STACK TRACE:\n{error_details['stack']}")
            except Exception:
                logger.exception(f"LangChain agent processing failed: {e}")
                logger.exception(f"FALLBACK STACK TRACE:\n{traceback.format_exc()}")

            return {
                "success": False,
                "formatted_summary": f"Agent processing error: {error_details['message']}",
                "intermediate_steps": [],
                "agent_name": "medical_search",
                "error": error_details["message"],
                "error_details": error_details,
            }

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        BaseHealthcareAgent abstract method implementation for LangChain agent

        Processes healthcare requests through LangChain agent workflow
        """
        try:
            # Extract message from request
            message = request.get("message", "")
            if not message:
                return {
                    "success": False,
                    "error": "No message provided in request",
                    "agent_name": self.agent_name,
                }

            # Process through LangChain agent
            result = await self.process(message)

            # Convert to BaseHealthcareAgent expected format
            if isinstance(result, dict) and result.get("success", True):
                return {
                    "success": True,
                    "response": result.get("formatted_summary", str(result)),
                    "agent_name": self.agent_name,
                    "details": result,
                }
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "agent_name": self.agent_name,
            }

        except Exception as e:
            self.logger.exception(f"LangChain agent _process_implementation error: {e}")
            return {"success": False, "error": str(e), "agent_name": self.agent_name}
