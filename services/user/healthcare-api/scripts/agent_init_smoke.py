"""
LangChain Healthcare Agent initialization smoke test
Run: python3 services/user/healthcare-api/scripts/agent_init_smoke.py
"""

import sys
from pathlib import Path

# Ensure local package path (robust to any working directory)
# This script lives at: services/user/healthcare-api/scripts/agent_init_smoke.py
# So the healthcare-api package root is two levels up from this file.
API_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_PATH))

from core.langchain.agents import HealthcareLangChainAgent  # noqa: E402
from core.mcp.direct_mcp_client import DirectMCPClient  # noqa: E402


def main() -> None:
    mcp_client = DirectMCPClient()
    agent = HealthcareLangChainAgent(mcp_client)
    print("✅ LangChain agent initialized successfully")
    print("Agent:", type(agent))


if __name__ == "__main__":
    main()
