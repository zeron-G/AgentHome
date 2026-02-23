"""Memory record dataclass for RAG storage."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class MemoryRecord:
    """A single NPC memory entry."""
    content: str
    npc_id: str
    tags: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    tick: int = 0
    location: tuple[int, int] = (0, 0)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "npc_id": self.npc_id,
            "content": self.content,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "tick": self.tick,
            "location": list(self.location),
        }

    @classmethod
    def from_dict(cls, d: dict) -> MemoryRecord:
        return cls(
            record_id=d.get("record_id", str(uuid.uuid4())[:8]),
            npc_id=d["npc_id"],
            content=d["content"],
            tags=d.get("tags", []),
            timestamp=d.get("timestamp", time.time()),
            tick=d.get("tick", 0),
            location=tuple(d.get("location", [0, 0])),
        )
