"""
Healthcare LangChain Agent

Provides a LangChain-powered agent wrapper that uses the local Ollama
chat model via our existing `src/local_llm/ollama_client` helpers.
The agent builds no network connections on import; construction is
lightweight and runtime-safe for PHI.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import os as _os

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.langchain.healthcare_tools import create_healthcare_tools
from agents import BaseHealthcareAgent

logger = get_healthcare_logger("core.langchain.agents")


class HealthcareLangChainAgent(BaseHealthcareAgent):
    """LangChain-powered healthcare agent with configurable behavior."""

    def __init__(
        self,
        mcp_client,
        chat_model: Optional[BaseChatModel] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        verbose: bool = False,
        max_iterations: int = 20,
        memory_max_token_limit: int = 2000,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.5,
        agent_manager: Optional[Any] = None
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
            mcp_client=mcp_client,
            agent_name="langchain_healthcare",
            agent_type="langchain_medical"
        )
        
        # LangChain-specific configuration
        self.verbose = verbose or _os.getenv("HEALTHCARE_AGENT_DEBUG", "").lower() in {"1", "true", "yes"}
        self.max_iterations = max_iterations
        self.tool_max_retries = tool_max_retries
        self.tool_retry_base_delay = tool_retry_base_delay

        # Build or use provided LLM using proper configuration system
        from src.local_llm.ollama_client import OllamaConfig, build_chat_model
        import yaml
        from pathlib import Path

        # If caller supplied a chat_model directly, prefer it
        provided_llm: Optional[BaseChatModel] = chat_model
        # Back-compat: if a BaseChatModel was accidentally passed into `model`, accept it
        if provided_llm is None and model is not None and isinstance(model, BaseChatModel):
            provided_llm = model  # type: ignore[assignment]
            model = None

        if provided_llm is None:
            # Load model configuration from config files
            config_dir = Path(__file__).parent.parent.parent / "config"
            models_config_path = config_dir / "models.yml"

            # Default model from config
            default_model = "llama3.1:8b"
            default_temperature = temperature

            try:
                if models_config_path.exists():
                    with open(models_config_path, 'r') as f:
                        models_config = yaml.safe_load(f)

                    # Use healthcare LLM from config
                    default_model = models_config.get('primary_models', {}).get('healthcare_llm', 'llama3.1:8b')

                    # Use healthcare reasoning parameters if available
                    reasoning_params = models_config.get('model_parameters', {}).get('healthcare_reasoning', {})
                    if reasoning_params:
                        default_temperature = reasoning_params.get('temperature', temperature)
            except Exception as e:
                logger.warning(f"Could not load models config, using defaults: {e}")

            # Create Ollama configuration
            config = OllamaConfig(
                model=model or default_model,
                temperature=default_temperature,
                base_url=_os.getenv("OLLAMA_URL", "http://172.20.0.10:11434"),
                num_ctx=4096  # Context window size
            )

            # Build the chat model
            self.llm = build_chat_model(config)
            logger.info(f"Initialized LangChain agent with model: {config.model}")
        else:
            self.llm = provided_llm
            logger.info("Initialized LangChain agent with provided chat_model instance")

        self.show_agent_header = True
        self.per_agent_default_timeout = 30.0
        self.per_agent_hard_cap = 90.0

        # Tools - Agent-first architecture
        self.tools = create_healthcare_tools(
            mcp_client,
            agent_manager,
            max_retries=int(tool_max_retries)
        )        # ReAct prompt template (solves agent_scratchpad issues)
        # Use official ReAct prompt from hub per handoff document
        from langchain import hub
        prompt = hub.pull("hwchase17/react")

        agent = create_react_agent(
            llm=self.llm, tools=self.tools, prompt=prompt
        )

        # Configure AgentExecutor with ReAct agent and parsing error handling
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # Enable for debugging
            max_iterations=max_iterations,  # Use dynamic iterations parameter
            handle_parsing_errors="Check your output and make sure it conforms!",  # Specific error message per handoff
            return_intermediate_steps=True,
            # NO memory parameter per handoff document
        )

        # Internal debug callback for detailed tracing
        class _LangchainAgentDebugCallback(BaseCallbackHandler):
            def __init__(self, enabled: bool = False) -> None:
                self.enabled = enabled

            # LLM callbacks
            def on_llm_start(self, serialized, prompts, **kwargs):
                if not self.enabled:
                    return
                try:
                    logger.debug(
                        "LLM start",
                        extra={
                            "healthcare_context": {
                                "prompts_count": len(prompts) if isinstance(prompts, list) else 1,
                                "prompt_preview": (prompts[0][:200] if isinstance(prompts, list) and prompts else str(prompts)[:200]),
                            }
                        },
                    )
                except Exception:
                    pass

            def on_llm_end(self, response, **kwargs):
                if not self.enabled:
                    return
                try:
                    txt = getattr(response, "content", "") or str(response)
                    logger.debug(
                        "LLM end",
                        extra={"healthcare_context": {"response_preview": str(txt)[:200]}},
                    )
                except Exception:
                    pass

            def on_llm_error(self, error, **kwargs):
                try:
                    logger.error("LLM error", extra={"healthcare_context": {"error": str(error)}})
                except Exception:
                    pass

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
                            }
                        },
                    )
                except Exception:
                    pass

            def on_tool_end(self, output, **kwargs):
                if not self.enabled:
                    return
                try:
                    logger.debug(
                        "Tool end",
                        extra={"healthcare_context": {"output_preview": str(output)[:200]}},
                    )
                except Exception:
                    pass

            def on_tool_error(self, error, **kwargs):
                try:
                    logger.error("Tool error", extra={"healthcare_context": {"error": str(error)}})
                except Exception:
                    pass

            # Chain callbacks
            def on_chain_start(self, serialized, inputs, **kwargs):
                if not self.enabled:
                    return
                try:
                    logger.debug(
                        "Chain start",
                        extra={"healthcare_context": {"inputs_keys": list(inputs.keys()) if isinstance(inputs, dict) else []}},
                    )
                except Exception:
                    pass

            def on_chain_end(self, outputs, **kwargs):
                if not self.enabled:
                    return
                try:
                    logger.debug(
                        "Chain end",
                        extra={"healthcare_context": {"outputs_keys": list(outputs.keys()) if isinstance(outputs, dict) else []}},
                    )
                except Exception:
                    pass

            def on_chain_error(self, error, **kwargs):
                try:
                    logger.error("Chain error", extra={"healthcare_context": {"error": str(error)}})
                except Exception:
                    pass

        self._debug_callback = _LangchainAgentDebugCallback(enabled=self.verbose)

    async def process(self, query: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with tool access and provenance metadata."""
        try:
            # CRITICAL: Only pass 'input' - no other keys
            # AgentExecutor handles agent_scratchpad internally
            input_data = {"input": query}
            
            if self.verbose:
                try:
                    logger.debug(
                        "AgentExecutor input prepared",
                        extra={
                            "healthcare_context": {
                                "keys": list(input_data.keys()),
                                "input_type": type(input_data["input"]).__name__,
                            }
                        },
                    )
                except Exception:
                    pass
            
            # Execute without any callbacks or config initially to isolate issues
            result = await self.executor.ainvoke(input_data)
            
            agent_name = "medical_search"  # default label until router is added
            formatted = result.get("output", "")
            if self.show_agent_header:
                formatted = f"🤖 {agent_name.replace('_', ' ').title()} Agent Response:\n\n" + formatted

            logger.info(f"LangChain agent processing successful. Output length: {len(formatted)}")
            return {
                "success": True,
                "formatted_summary": formatted,
                "intermediate_steps": result.get("intermediate_steps", []),
                "agent_name": agent_name,
            }
        except Exception as e:
            # Rich error with stack and input typing to isolate prompt var issues
            import traceback
            import sys
            import linecache
            from typing import Any, Dict, List, Optional

            tb = e.__traceback__
            frames: List[Dict[str, Any]] = []
            while tb is not None:
                frame = tb.tb_frame
                lineno = tb.tb_lineno
                filename = frame.f_code.co_filename
                funcname = frame.f_code.co_name
                line = linecache.getline(filename, lineno).rstrip("\n")
                frames.append({
                    "file": filename,
                    "line": lineno,
                    "function": funcname,
                    "code": line,
                })
                tb = tb.tb_next

            # Prefer the deepest in-repo frame for faster pinpointing
            repo_root_indicator = "/home/intelluxe/"
            chosen: Optional[Dict[str, Any]] = None
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
                logger.error(
                    "LangChain agent processing failed",
                    extra={"healthcare_context": error_details},
                )
                # Also log the full error details directly for debugging
                logger.error(f"DETAILED ERROR: {error_details['message']}")
                logger.error(f"ERROR TYPE: {error_details['type']}")
                if chosen:
                    logger.error(f"ERROR LOCATION: {chosen['file']}:{chosen['line']} in {chosen['function']}()")
                    logger.error(f"ERROR CODE: {chosen['code']}")
                logger.error(f"FULL STACK TRACE:\n{error_details['stack']}")
            except Exception:
                logger.error(f"LangChain agent processing failed: {e}")
                logger.error(f"FALLBACK STACK TRACE:\n{traceback.format_exc()}")

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
                    "agent_name": self.agent_name
                }
            
            # Process through LangChain agent
            result = await self.process(message)
            
            # Convert to BaseHealthcareAgent expected format
            if isinstance(result, dict) and result.get("success", True):
                return {
                    "success": True,
                    "response": result.get("formatted_summary", str(result)),
                    "agent_name": self.agent_name,
                    "details": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "agent_name": self.agent_name
                }
                
        except Exception as e:
            self.logger.error(f"LangChain agent _process_implementation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_name": self.agent_name
            }
