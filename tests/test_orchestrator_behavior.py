import asyncio
import json
from typing import Any, Dict

import pytest

# Ensure we import the FastAPI app and globals from the healthcare-api service
from main import app as healthcare_app  # type: ignore
import main as healthcare_main  # type: ignore
from fastapi.testclient import TestClient


class MockLLM:
    """Minimal mock LLM that returns a structured agent selection."""

    def __init__(self, agent_to_select: str):
        self.agent_to_select = agent_to_select

    async def generate(
        self, model: str, prompt: str, format: Dict[str, Any], stream: bool = False
    ) -> Dict[str, Any]:
        # Return a JSON string under 'response' with the selected agent name
        return {"response": json.dumps({"agent": self.agent_to_select})}


class DummyAgent:
    agent_name = "dummy"
    agent_type = "test"

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "message": "This is a dummy success",
            "formatted_summary": "✅ Dummy completed successfully.",
        }


class FailingAgent:
    agent_name = "failing"
    agent_type = "test"

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("simulated failure")


class SlowAgent:
    agent_name = "slow"
    agent_type = "test"

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Sleep long enough to exceed the configured timeout
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "message": "Completed slowly",
            "formatted_summary": "Slow completion",
        }


@pytest.fixture()
def client() -> TestClient:
    # Use a new TestClient each time to avoid cross-test state
    return TestClient(healthcare_app)


def _set_globals(agents: Dict[str, Any], llm_agent_name: str) -> None:
    # Override discovered agents and LLM client in the running app/module
    healthcare_main.discovered_agents = agents
    healthcare_main.llm_client = MockLLM(llm_agent_name)


@pytest.mark.unit
def test_provenance_header_on_success(client: TestClient) -> None:
    # Arrange: one dummy agent, router selects it
    _set_globals({"dummy": DummyAgent()}, "dummy")

    # Act
    resp = client.post("/process", json={"message": "hello", "format": "human"})

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    # Header should include pretty agent name
    assert body["formatted_response"].startswith("🤖 **Dummy Agent Response:**")
    # And the result is present
    assert body["result"]["success"] is True


@pytest.mark.unit
def test_fallback_trigger_on_agent_failure(client: TestClient) -> None:
    # Arrange: one failing agent, router selects it
    _set_globals({"failing": FailingAgent()}, "failing")

    # Act
    resp = client.post("/process", json={"message": "trigger failure", "format": "human"})

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    # Fallback uses base agent header
    assert body["formatted_response"].startswith("🤖 **Base Agent Response:**")
    # Disclaimer phrase should be included
    assert "not medical advice" in body["formatted_response"].lower()
    # Result should indicate fallback agent name
    assert body["result"].get("agent_name") == "base"


@pytest.mark.unit
def test_timeout_behavior_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Arrange: slow agent + small timeout via orchestrator config patch
    _set_globals({"slow": SlowAgent()}, "slow")

    def patched_load_config() -> Dict[str, Any]:
        # Minimal config with tiny per-agent timeout and provenance enabled
        return {
            "selection": {"enable_fallback": True},
            "timeouts": {"router_selection": 1, "per_agent_default": 0.1, "per_agent_hard_cap": 1},
            "provenance": {"show_agent_header": True},
            "synthesis": {"prefer": ["formatted_summary", "message"]},
            "fallback": {
                "agent_name": "base",
                "message_template": "Base fallback for '{user_message}'",
            },
        }

    monkeypatch.setattr(healthcare_main, "load_orchestrator_config", patched_load_config)

    # Act
    resp = client.post("/process", json={"message": "something slow", "format": "human"})

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    # Should have fallen back due to timeout
    assert body["formatted_response"].startswith("🤖 **Base Agent Response:**")
    assert body["result"].get("agent_name") == "base"
