"""
Typed, PHI-safe LangChain + Ollama client utilities.

Contracts
- Inputs: model name (str), base_url (str | None), temperature (float), seed (int | None)
- Outputs: ChatOllama instance and simple generate() helper returning str
- Errors: raises ValueError for invalid config; surfaces underlying client exceptions
- Success: no network call at import; only on generate()/invoke()

Compliance notes
- All PHI must stay local; this uses langchain_ollama ChatOllama (local inference)
- Do not log prompts/responses here; callers handle audit logging via existing audit modules
- No Any: strict typing to satisfy mypy rules
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatResult
from langchain_ollama import ChatOllama


@dataclass(frozen=True)
class OllamaConfig:
    model: str
    base_url: Optional[str] = None  # e.g., "http://ollama:11434"
    temperature: float = 0.0
    seed: Optional[int] = 0
    num_ctx: Optional[int] = None

    def validate(self) -> None:
        if not self.model or not isinstance(self.model, str):
            raise ValueError("model must be a non-empty string")
        if self.base_url is not None and not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string or None")
        if not (0.0 <= float(self.temperature) <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        # seed and num_ctx can be None; no further validation required here


def build_chat_model(cfg: OllamaConfig) -> BaseChatModel:
    """Create a ChatOllama with safe defaults; no network call here.

    Returns a BaseChatModel to keep the public contract generic.
    """
    cfg.validate()
    params: dict[str, object] = {}
    if cfg.num_ctx is not None:
        params["num_ctx"] = int(cfg.num_ctx)

    return ChatOllama(
        model=cfg.model,
        base_url=cfg.base_url,
        temperature=float(cfg.temperature),
        seed=cfg.seed,
        # Pass-through extra model params when provided
        **params,
    )


def generate(model: BaseChatModel, prompt: str) -> str:
    """Simple helper to synchronously generate a response from a prompt.

    This uses message-based invocation to be explicit and future-proof.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    messages = [HumanMessage(content=prompt)]
    result: ChatResult = model.generate([messages])
    # result.generations is List[List[ChatGeneration]]; take [0][0]
    first = result.generations[0][0].message
    if isinstance(first, AIMessage):
        content = first.content
        return content if isinstance(content, str) else str(content)
    # Fallback: coerce any message content to string
    return str(first.content)
