"""
Regression test: ensure AgentExecutor construction does not raise due to
unsupported early_stopping_method in our installed LangChain version.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure healthcare-api package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTHCARE_API_PATH = PROJECT_ROOT / "services" / "user" / "healthcare-api"
if str(HEALTHCARE_API_PATH) not in sys.path:
    sys.path.append(str(HEALTHCARE_API_PATH))


@pytest.mark.asyncio
async def test_agentexecutor_constructs_without_early_stopping_valueerror():
    from core.langchain.agents import HealthcareLangChainAgent
    from core.mcp.direct_mcp_client import DirectMCPClient

    client = DirectMCPClient()

    # Don't require MCP server for construction; we only validate executor build
    agent = HealthcareLangChainAgent(client, verbose=False)

    # Sanity: agent has an executor and max_iterations is an int
    assert hasattr(agent, "executor")
    assert isinstance(agent.max_iterations, int)
