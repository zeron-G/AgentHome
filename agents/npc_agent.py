"""NPC agent: processes world context and returns a structured action."""
from __future__ import annotations

import logging
import time
from typing import Optional

import config
from agents.base_agent import BaseAgent
from agents.prompts import NPCAction, build_npc_context, build_npc_system_prompt
from engine.world import NPC, World
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)

_FALLBACK_ACTIONS = [
    {"action": "rest", "thought": "我需要稍微休息一下"},
    {"action": "move", "dx": 1, "dy": 0, "thought": "四处走走看看"},
    {"action": "move", "dx": 0, "dy": 1, "thought": "探索一下"},
]


class NPCAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker, rag_storage=None):
        # Use a shared agent ID for NPCs to group token usage
        super().__init__("npcs", token_tracker)
        self._rag = rag_storage  # Optional[BaseRAGStorage]

    def set_rag(self, rag_storage) -> None:
        """Attach a RAG storage backend (called after construction)."""
        self._rag = rag_storage

    def _retrieve_memories(self, npc: NPC, world: World) -> str:
        """Pull relevant memories from RAG and format as a string."""
        if not self._rag or not config.RAG_ENABLED:
            return ""
        try:
            # Build query from current situation
            tile = world.get_tile(npc.x, npc.y)
            tile_type = tile.tile_type.value if tile else ""
            nearby = world.get_nearby_npcs_for_npc(npc, config.NPC_HEARING_RADIUS)
            nearby_names = " ".join(n.name for n in nearby)
            query = f"{tile_type} {nearby_names} {world.weather.value}"

            records = self._rag.search_memories(
                npc.npc_id, query, limit=config.RAG_SEARCH_LIMIT
            )
            if not records:
                return ""
            lines = []
            for r in records:
                lines.append(f"- [Tick{r.tick}] {r.content}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[{npc.name}] RAG retrieve error: {e}")
            return ""

    def _save_action_memory(self, npc: NPC, action: dict, world: World) -> None:
        """Persist important actions to RAG storage."""
        if not self._rag or not config.RAG_ENABLED:
            return
        try:
            from rag.records import MemoryRecord
            action_type = action.get("action", "idle")
            # Only save meaningful events
            if action_type in ("idle", "rest"):
                return
            thought = action.get("thought", "")
            message = action.get("message", "")
            note = action.get("note", "")
            content_parts = [f"行动: {action_type}"]
            if message:
                content_parts.append(f"说: {message}")
            if thought:
                content_parts.append(f"想: {thought}")
            if note:
                content_parts.append(f"笔记: {note}")

            tags = [action_type, world.time.phase, world.weather.value]
            record = MemoryRecord(
                npc_id=npc.npc_id,
                content=" | ".join(content_parts),
                tags=tags,
                timestamp=time.time(),
                tick=world.time.tick,
                location=(npc.x, npc.y),
            )
            self._rag.save_memory(record)
        except Exception as e:
            logger.warning(f"[{npc.name}] RAG save error: {e}")

    async def process(self, npc: NPC, world: World) -> dict:
        """
        Build context for this NPC, call LLM, return action dict.
        Falls back to rest if LLM fails.
        """
        if npc.is_processing:
            return {"action": "idle"}

        npc.is_processing = True
        try:
            # Retrieve relevant memories from RAG
            rag_memories = self._retrieve_memories(npc, world)

            system_prompt = build_npc_system_prompt(npc, world)
            context_msg, is_social = build_npc_context(npc, world, rag_memories)

            result = await self.call_llm(
                system_prompt=system_prompt,
                context_message=context_msg,
                history=npc.memory.conversation_history,
                response_schema=NPCAction,
            )

            if result is None:
                import random
                return random.choice(_FALLBACK_ACTIONS)

            # Store this exchange in memory
            npc.memory.add_history_turn("user", context_msg)
            npc.memory.add_history_turn("model", result.model_dump_json())

            # Clear inbox after reading
            npc.memory.clear_inbox()

            action = result.model_dump(exclude_none=True)

            # Save action to RAG
            self._save_action_memory(npc, action, world)

            logger.info(f"[{npc.name}] action={action.get('action')} msg={action.get('message','')[:40]}")
            return action

        except Exception as e:
            logger.error(f"[{npc.name}] process error: {e}")
            return {"action": "rest", "thought": "出错了，先休息"}
        finally:
            npc.is_processing = False
