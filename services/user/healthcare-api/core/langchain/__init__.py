"""LangChain integration scaffolding for the Healthcare API.

Modules:
- tools: StructuredTool wrappers around MCP
- agents: HealthcareLangChainAgent built on local ChatOllama
- orchestrator: minimal orchestrator façade

All components avoid side effects at import time and are PHI-safe.
"""
