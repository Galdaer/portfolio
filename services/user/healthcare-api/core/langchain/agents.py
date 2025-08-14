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
        mcp_client: Any,
        chat_model: BaseChatModel,
        *,
        show_agent_header: bool = True,
        per_agent_default_timeout: float = 30.0,
        per_agent_hard_cap: float = 90.0,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.2,
    ) -> None:
        self.show_agent_header = show_agent_header
        self.per_agent_default_timeout = per_agent_default_timeout
        self.per_agent_hard_cap = per_agent_hard_cap

        # Tools
        self.tools = create_mcp_tools(
            mcp_client, max_retries=int(tool_max_retries), retry_base_delay=float(tool_retry_base_delay)
        )

        # Prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a healthcare AI assistant providing evidence-based medical\n"
                        "information from authoritative sources.\n\n"
                        "CRITICAL RULES:\n"
                        "- Always cite sources with links when providing medical information\n"
                        "- Never provide direct medical advice or diagnosis\n"
                        "- Use available tools to search medical literature\n"
                        "- Maintain patient privacy - never store or transmit PHI\n\n"
                        "Available tools:\n{tools}\n\n"
                        "Use tools only by their names from this list: {tool_names}.\n\n"
                        "When responding:\n"
                        "1. Search relevant medical literature using tools\n"
                        "2. Synthesize findings with clear citations\n"
                        "3. Include appropriate medical disclaimers\n"
                        "4. Format response for clarity with headers and bullet points"
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_structured_chat_agent(
            llm=chat_model, tools=self.tools, prompt=prompt
        )

        # Lightweight conversation memory for context preservation
        self.memory = ConversationSummaryBufferMemory(
            llm=chat_model,
            max_token_limit=2000,
            return_messages=True,
            memory_key="chat_history",
        )

        # Minimal executor with memory
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            max_iterations=3,
            early_stopping_method="generate",
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            memory=self.memory,
        )

    async def process(self, query: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with tool access and provenance metadata."""
        result = await self.executor.ainvoke({"input": query, "context": context or {}})
        agent_name = "medical_search"  # default label until router is added
        formatted = result.get("output", "")
        if self.show_agent_header:
            formatted = f"🤖 {agent_name.replace('_', ' ').title()} Agent Response:\n\n" + formatted
        return {
            "success": True,
            "formatted_summary": formatted,
            "intermediate_steps": result.get("intermediate_steps", []),
            "agent_name": agent_name,
        }
