import sys
from pathlib import Path


def _add_service_paths() -> None:
    service_root = Path(__file__).parent.parent / "services" / "user" / "healthcare-api"
    service_src = service_root / "src"
    for p in (service_root, service_src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def test_create_mcp_tools_import_only():
    _add_service_paths()
    from core.langchain.tools import create_mcp_tools  # type: ignore

    class DummyMCP:
        async def call_tool(self, name: str, arguments: dict):  # pragma: no cover - no call path
            return {
                "status": "success",
                "content": {"ok": True, "name": name, "arguments": arguments},
            }

    tools = create_mcp_tools(DummyMCP())
    names = {t.name for t in tools}
    assert {"search_medical_literature", "search_clinical_trials", "get_drug_information"}.issubset(
        names,
    )
