"""Agent execution context utilities.

Provides lightweight dataclass capturing trace / correlation details so logs &
metrics can uniformly enrich events without per-agent duplication.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class AgentContext:
    trace_id: str
    user_id: str | None
    agent_name: str
    start_time: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_ms(self) -> float:
        return (datetime.now(UTC) - self.start_time).total_seconds() * 1000.0


def new_agent_context(agent_name: str, user_id: str | None = None, **metadata: Any) -> AgentContext:
    return AgentContext(
        trace_id=uuid.uuid4().hex,
        user_id=user_id,
        agent_name=agent_name,
        start_time=datetime.now(UTC),
        metadata=metadata,
    )


__all__ = ["AgentContext", "new_agent_context"]
