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

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.langchain.tools import create_mcp_tools

logger = get_healthcare_logger("core.langchain.agents")


class HealthcareLangChainAgent:
    """LangChain-powered healthcare agent with configurable behavior."""

    def __init__(
        self,
        mcp_client,
        chat_model: Optional[BaseChatModel] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        verbose: bool = False,
        max_iterations: int = 3,
        memory_max_token_limit: int = 2000,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.5
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
        self.mcp_client = mcp_client
        # Enable verbose when requested explicitly or via environment toggle
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
                base_url=_os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
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

        # Tools
        self.tools = create_mcp_tools(
            mcp_client, max_retries=int(tool_max_retries), retry_base_delay=float(tool_retry_base_delay)
        )

        # Prompt following LangChain structured chat agent format (per official docs)
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Respond to the human as helpfully and accurately as possible. You have access to the following tools:\n"
                    "{tools}\n\n"
                    "Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).\n\n"
                    "Valid \"action\" values: \"Final Answer\" or {tool_names}\n\n"
                    "Provide only ONE action per $JSON_BLOB, as shown:\n"
                    "```\n"
                    "{{\n"
                    "  \"action\": $TOOL_NAME,\n"
                    "  \"action_input\": $INPUT\n"
                    "}}\n"
                    "```\n\n"
                    "Follow this format:\n"
                    "Question: input question to answer\n"
                    "Thought: consider previous and subsequent steps\n"
                    "Action:\n"
                    "```\n"
                    "$JSON_BLOB\n"
                    "```\n"
                    "Observation: action result\n"
                    "... (repeat Thought/Action/Observation N times)\n"
                    "Thought: I know what to respond\n"
                    "Action:\n"
                    "```\n"
                    "{{\n"
                    "  \"action\": \"Final Answer\",\n"
                    "  \"action_input\": \"Final response to human\"\n"
                    "}}\n"
                    "```\n\n"
                    "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation"
                ),
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_structured_chat_agent(
            llm=self.llm, tools=self.tools, prompt=prompt
        )

        # Configure AgentExecutor with proper structured chat settings
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # Enable for debugging
            max_iterations=5,  # Increase iterations for tool usage
            early_stopping_method="generate",
            handle_parsing_errors=True,
            return_intermediate_steps=True,
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
            # Prepare input for AgentExecutor
            # The AgentExecutor manages agent_scratchpad automatically; do NOT pass it.
            # We will manually pass chat_history as a list of BaseMessages if memory exists.
            chat_history = []
            try:
                mem = getattr(self, "memory", None)
                if mem is not None:
                    chat_mem = getattr(mem, "chat_memory", None)
                    if chat_mem is not None:
                        msgs = getattr(chat_mem, "messages", [])
                        # Ensure it's a list before passing through
                        if isinstance(msgs, list):
                            chat_history = list(msgs)
            except Exception:
                # If anything goes wrong, fall back to empty history to avoid type issues
                chat_history = []

            input_data = {"input": query, "chat_history": chat_history}
            
            if self.verbose:
                try:
                    logger.debug(
                        "AgentExecutor input prepared",
                        extra={
                            "healthcare_context": {
                                "keys": list(input_data.keys()),
                                "types": {k: type(v).__name__ for k, v in input_data.items()},
                            }
                        },
                    )
                except Exception:
                    pass
            
            # If context is provided, we could incorporate it into the query itself
            # but avoid passing extra keys that aren't in the prompt template
            if context and isinstance(context, dict) and context:
                # For now, we'll keep context separate from the LangChain execution
                # since our prompt doesn't expect a context variable
                pass
            
            # Let AgentExecutor manage agent_scratchpad automatically (from intermediate_steps)
            callbacks: Optional[list[BaseCallbackHandler]] = [self._debug_callback] if self.verbose else None
            config: Optional[RunnableConfig] = {"callbacks": callbacks} if callbacks else None
            result = await self.executor.ainvoke(input_data, config=config)
            agent_name = "medical_search"  # default label until router is added
            formatted = result.get("output", "")
            if self.show_agent_header:
                formatted = f"🤖 {agent_name.replace('_', ' ').title()} Agent Response:\n\n" + formatted

            # Manually update memory transcript after successful execution (if available)
            try:
                mem = getattr(self, "memory", None)
                if mem is not None:
                    chat_mem = getattr(mem, "chat_memory", None)
                    if chat_mem is not None:
                        # Safely record the exchange as plain strings
                        if hasattr(chat_mem, "add_user_message"):
                            chat_mem.add_user_message(query)
                        if formatted and hasattr(chat_mem, "add_ai_message"):
                            chat_mem.add_ai_message(formatted)
            except Exception:
                # Non-fatal if memory update fails
                pass

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

            tb = e.__traceback__
            frames = []
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
            chosen = None
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
            except Exception:
                logger.error(f"LangChain agent processing failed: {e}")

            return {
                "success": False,
                "formatted_summary": f"Agent processing error: {error_details['message']}",
                "intermediate_steps": [],
                "agent_name": "medical_search",
                "error": error_details["message"],
                "error_details": error_details,
            }
