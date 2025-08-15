import sys
from pathlib import Path


def _add_service_paths() -> None:
    service_root = Path(__file__).parent.parent / "services" / "user" / "healthcare-api"
    service_src = service_root / "src"
    for p in (service_root, service_src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def test_healthcare_agent_import_only():
    _add_service_paths()
    from core.langchain.agents import HealthcareLangChainAgent  # type: ignore
    from local_llm.ollama_client import OllamaConfig, build_chat_model  # type: ignore

    class DummyMCP:
        async def call_tool(self, name: str, arguments: dict):  # pragma: no cover
            return {"status": "success", "content": {"ok": True}}

    # Build a chat model instance without forcing any network calls
    model = build_chat_model(OllamaConfig(model="llama3.1:8b", base_url="http://172.20.0.10:11434", temperature=0.0))
    agent = HealthcareLangChainAgent(DummyMCP(), model)
    # executor and tools should be present
    assert hasattr(agent, "executor")
    assert len(getattr(agent, "tools", [])) >= 1
