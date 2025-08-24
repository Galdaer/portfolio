"""Import smoke tests for LangChain + Ollama.

No network calls are performed. These tests only verify that imports and
basic constructors are available in the active environment/venv.
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_ollama import ChatOllama  # noqa: F401

# Add the healthcare-api service src directory to sys.path for direct imports
SERVICE_SRC = Path(__file__).resolve().parents[1] / "services/user/healthcare-api/src"
sys.path.insert(0, str(SERVICE_SRC))

from local_llm.ollama_client import (  # type: ignore  # noqa: E402
    OllamaConfig,
    build_chat_model,
)


def test_imports_only() -> None:
    # Ensure dataclass constructs and the builder returns a BaseChatModel
    cfg = OllamaConfig(model="llama3.1:8b", base_url="http://172.20.0.10:11434")
    model = build_chat_model(cfg)
    # Do not invoke network; just assert the object has expected attributes
    assert hasattr(model, "invoke") or hasattr(model, "generate")
