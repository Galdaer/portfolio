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
async def test_orchestrator_hides_sources_when_flag_false():
    _add_service_paths()
    from core.langchain.orchestrator import LangChainOrchestrator  # type: ignore
    from local_llm.ollama_client import OllamaConfig, build_chat_model  # type: ignore

    class DummyMCP:
        async def call_tool(self, name: str, arguments: dict):  # pragma: no cover
            return {"status": "success", "content": {"ok": True}}

    class DummyAction:
        def __init__(self, tool: str):
            self.tool = tool

    class DummyAgent:
        def __init__(self):
            self.show_agent_header = True

        async def process(self, query: str, *, context=None):
            return {
                "success": True,
                "formatted_summary": "Summary only",
                "agent_name": "medical_search",
                "intermediate_steps": [
                    (
                        DummyAction("search_medical_literature"),
                        {
                            "results": [
                                {"title": "Study A", "url": "http://example.com/a"},
                            ]
                        },
                    )
                ],
            }

    model = build_chat_model(
        OllamaConfig(model="llama3.1:8b", base_url="http://localhost:11434", temperature=0.0)
    )
    orch = LangChainOrchestrator(mcp_client=DummyMCP(), chat_model=model)
    orch.agent = DummyAgent()

    result = await orch.process("test query", show_sources=False)
    assert isinstance(result, dict)
    assert "citations" in result and isinstance(result["citations"], list)
    formatted = result.get("formatted_summary", "")
    assert "Sources:" not in formatted
