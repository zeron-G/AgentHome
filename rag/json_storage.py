"""JSON-file-based RAG storage implementation.

Storage layout:
    saves/
        memories/
            npc_he.json       ← list of MemoryRecord dicts
            npc_sui.json
            ...
        world_state.json      ← latest game state snapshot
        events.json           ← recent global events log
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import config
from rag.base import BaseRAGStorage
from rag.records import MemoryRecord

logger = logging.getLogger(__name__)


class JSONRAGStorage(BaseRAGStorage):
    """Simple JSON-file storage with keyword-based memory search."""

    def __init__(self, save_dir: str | None = None):
        self._root = Path(save_dir or config.RAG_SAVE_DIR)
        self._mem_dir = self._root / "memories"
        self._mem_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._root / "world_state.json"
        self._events_path = self._root / "events.json"

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _mem_path(self, npc_id: str) -> Path:
        safe = npc_id.replace("/", "_").replace("\\", "_")
        return self._mem_dir / f"{safe}.json"

    def _load_records(self, npc_id: str) -> list[MemoryRecord]:
        p = self._mem_path(npc_id)
        if not p.exists():
            return []
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryRecord.from_dict(d) for d in data]
        except Exception as e:
            logger.warning(f"RAG: failed to load memories for {npc_id}: {e}")
            return []

    def _save_records(self, npc_id: str, records: list[MemoryRecord]) -> None:
        p = self._mem_path(npc_id)
        try:
            with p.open("w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in records], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"RAG: failed to save memories for {npc_id}: {e}")

    # ── Memory operations ──────────────────────────────────────────────────────

    def save_memory(self, record: MemoryRecord) -> None:
        records = self._load_records(record.npc_id)
        records.append(record)
        # Enforce max records cap
        max_cap = config.RAG_MAX_MEMORIES_PER_NPC
        if len(records) > max_cap:
            records = records[-max_cap:]
        self._save_records(record.npc_id, records)

    def search_memories(
        self, npc_id: str, query: str, limit: int = 5
    ) -> list[MemoryRecord]:
        """Keyword search: score each record by how many query words appear in content."""
        records = self._load_records(npc_id)
        if not records:
            return []

        query_words = set(query.lower().split())

        def score(r: MemoryRecord) -> int:
            text = r.content.lower()
            return sum(1 for w in query_words if w in text)

        # Sort by score desc, then recency desc
        scored = sorted(records, key=lambda r: (score(r), r.timestamp), reverse=True)
        return scored[:limit]

    def get_recent_memories(self, npc_id: str, limit: int = 5) -> list[MemoryRecord]:
        records = self._load_records(npc_id)
        return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]

    def delete_npc_memory(self, npc_id: str) -> None:
        p = self._mem_path(npc_id)
        if p.exists():
            p.unlink()
        logger.info(f"RAG: deleted all memories for {npc_id}")

    # ── Game state ─────────────────────────────────────────────────────────────

    def save_game_state(self, state: dict) -> None:
        try:
            with self._state_path.open("w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"RAG: failed to save game state: {e}")

    def load_game_state(self) -> dict | None:
        if not self._state_path.exists():
            return None
        try:
            with self._state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"RAG: failed to load game state: {e}")
            return None

    def delete_all(self) -> None:
        """Remove all saves."""
        import shutil
        if self._mem_dir.exists():
            shutil.rmtree(self._mem_dir)
            self._mem_dir.mkdir(parents=True, exist_ok=True)
        if self._state_path.exists():
            self._state_path.unlink()
        if self._events_path.exists():
            self._events_path.unlink()
        logger.info("RAG: all saves deleted")

    # ── Metadata ───────────────────────────────────────────────────────────────

    def list_save_info(self) -> dict:
        info: dict = {
            "has_game_state": self._state_path.exists(),
            "npc_memories": {},
        }
        if self._mem_dir.exists():
            for p in self._mem_dir.glob("*.json"):
                try:
                    with p.open("r", encoding="utf-8") as f:
                        records = json.load(f)
                    info["npc_memories"][p.stem] = len(records)
                except Exception:
                    info["npc_memories"][p.stem] = -1
        return info
