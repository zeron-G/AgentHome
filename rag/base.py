"""Abstract base class for RAG storage — swap implementations without changing callers."""
from __future__ import annotations

from abc import ABC, abstractmethod

from rag.records import MemoryRecord


class BaseRAGStorage(ABC):
    """Swappable storage backend for NPC memories and game state."""

    # ── Memory operations ──────────────────────────────────────────────────────

    @abstractmethod
    def save_memory(self, record: MemoryRecord) -> None:
        """Persist a single memory record."""

    @abstractmethod
    def search_memories(
        self, npc_id: str, query: str, limit: int = 5
    ) -> list[MemoryRecord]:
        """Return up to `limit` relevant memories for an NPC given a query string."""

    @abstractmethod
    def get_recent_memories(self, npc_id: str, limit: int = 5) -> list[MemoryRecord]:
        """Return most recent memories for an NPC (no query needed)."""

    @abstractmethod
    def delete_npc_memory(self, npc_id: str) -> None:
        """Delete ALL memory records for a specific NPC."""

    # ── Game state persistence ─────────────────────────────────────────────────

    @abstractmethod
    def save_game_state(self, state: dict) -> None:
        """Persist a serialisable game state snapshot."""

    @abstractmethod
    def load_game_state(self) -> dict | None:
        """Load previously saved game state; return None if none exists."""

    @abstractmethod
    def delete_all(self) -> None:
        """Delete ALL saves including memories and game state."""

    # ── Metadata ───────────────────────────────────────────────────────────────

    @abstractmethod
    def list_save_info(self) -> dict:
        """Return summary info about stored saves (for the settings UI)."""
