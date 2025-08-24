import sys
from pathlib import Path

import pytest


def _add_service_paths() -> None:
    service_root = Path(__file__).parent.parent / "services" / "user" / "healthcare-api"
    service_src = service_root / "src"
    for p in (service_root, service_src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


@pytest.mark.asyncio
async def test_orchestrator_process_with_context():
    _add_service_paths()
    from local_llm.ollama_client import OllamaConfig, build_chat_model  # type: ignore

    from core.langchain.orchestrator import LangChainOrchestrator  # type: ignore

    class DummyMCP:
        async def call_tool(self, name: str, arguments: dict):  # pragma: no cover
            return {"status": "success", "content": {"ok": True}}

    model = build_chat_model(
        OllamaConfig(model="llama3.1:8b", base_url="http://172.20.0.10:11434", temperature=0.0),
    )
    orch = LangChainOrchestrator(mcp_client=DummyMCP(), chat_model=model)
    # Provide extra context and ensure it doesn't break structured-chat execution
    result = await orch.process("test query", context={"user_id": "u1", "session": "s1"})
    assert isinstance(result, dict)
    assert "formatted_summary" in result
    assert "agent_name" in result
    assert "agents_used" in result
