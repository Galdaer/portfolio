"""
Healthcare LangChain Agent

Provides a LangChain-powered agent wrapper that uses the local Ollama
chat model via our existing `src/local_llm/ollama_client` helpers.
The agent builds no network connections on import; construction is
lightweight and runtime-safe for PHI.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel

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
        self.verbose = verbose
        self.max_iterations = max_iterations
        self.tool_max_retries = tool_max_retries
        self.tool_retry_base_delay = tool_retry_base_delay

        # Build or use provided LLM using proper configuration system
        from src.local_llm.ollama_client import OllamaConfig, build_chat_model
        import yaml
        import os
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
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
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

        # Lightweight conversation memory for context preservation
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=memory_max_token_limit,
            return_messages=True,
            memory_key="chat_history",
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
            memory=self.memory,
        )

    async def process(self, query: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with tool access and provenance metadata."""
        try:
            # Let AgentExecutor manage agent_scratchpad internally from intermediate_steps
            result = await self.executor.ainvoke({
                "input": query,
                "context": context or {},
            })
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
            logger.error(f"LangChain agent processing failed: {e}")
            return {
                "success": False,
                "formatted_summary": f"Agent processing error: {str(e)}",
                "intermediate_steps": [],
                "agent_name": "medical_search",
                "error": str(e),
            }
