"""NPC agent: three-layer hierarchical decision-making.

Layer 1 – Strategic (every NPC_STRATEGY_INTERVAL world ticks):
    Lightweight LLM call → sets npc.goal + npc.plan (list of steps).

Layer 2 – Tactical (rule-based, no LLM):
    Reads npc.plan to build focused execution context for Layer 3.

Layer 3 – Execution (every brain cycle):
    Standard LLM call with dynamic context (market only at exchange,
    social only when nearby characters exist, goal/plan injected).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import config
from agents.base_agent import BaseAgent
from agents.prompts import (
    NPCAction,
    NPCStrategy,
    build_npc_context,
    build_npc_system_prompt,
    build_strategy_context,
    build_strategy_system_prompt,
)
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

    # ── Layer 1: Strategic planning ──────────────────────────────────────────

    def _needs_strategy(self, npc: NPC, world: World) -> bool:
        """Return True when the NPC should run a new strategic planning call."""
        if not npc.goal:
            return True  # First run — no strategy yet
        ticks_since = world.time.tick - npc.strategy_tick
        if ticks_since >= config.NPC_STRATEGY_INTERVAL:
            return True
        # Also re-plan if plan is exhausted (all steps done, goal still unmet)
        if not npc.plan and npc.strategy_tick > 0:
            return True
        return False

    async def _refresh_strategy(self, npc: NPC, world: World) -> None:
        """Level-1: Call LLM with lightweight strategic prompt, update npc.goal/plan."""
        try:
            system_prompt = build_strategy_system_prompt(npc, world)
            context_msg = build_strategy_context(npc, world)

            result = await self.call_llm(
                system_prompt=system_prompt,
                context_message=context_msg,
                history=[],          # no history — strategic calls are stateless
                response_schema=NPCStrategy,
            )

            if result is None:
                return

            npc.goal = result.goal.strip()
            npc.plan = [s.strip() for s in result.steps if s.strip()]
            npc.mood = result.mood.strip() if result.mood else ""
            npc.strategy_tick = world.time.tick
            logger.info(
                f"[{npc.name}] NEW STRATEGY goal='{npc.goal[:50]}' "
                f"mood='{npc.mood}' steps={len(npc.plan)}"
            )
        except Exception as e:
            logger.warning(f"[{npc.name}] strategy refresh error: {e}")

    # ── Layer 2: Tactical (rule-based, no LLM) ───────────────────────────────

    def _advance_plan_if_needed(self, npc: NPC, last_action: str) -> None:
        """Heuristic: mark the current plan step done after certain actions.

        This is intentionally lightweight — the goal is not perfect tracking
        but preventing the NPC from looping on the same step forever.
        """
        if not npc.plan:
            return

        step = npc.plan[0].lower()

        # Actions that likely complete the first plan step
        completing_actions = {
            "gather": ["采集", "收集", "木头", "石头", "矿", "食物", "草药"],
            "craft":  ["制造", "craft", "绳", "工具", "药水", "面包"],
            "build":  ["建造", "build", "床", "桌", "椅"],
            "sell":   ["卖出", "sell", "交易所"],
            "buy":    ["买入", "buy"],
            "sleep":  ["睡", "sleep", "bed"],
            "rest":   ["休息", "rest", "椅"],
        }

        for action_type, keywords in completing_actions.items():
            if last_action == action_type and any(kw in step for kw in keywords):
                popped = npc.plan.pop(0)
                logger.debug(f"[{npc.name}] plan step done: '{popped[:40]}'")
                break

    # ── RAG helpers ──────────────────────────────────────────────────────────

    def _retrieve_memories(self, npc: NPC, world: World) -> str:
        """Pull relevant memories from RAG and format as a string."""
        if not self._rag or not config.RAG_ENABLED:
            return ""
        try:
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
            lines = [f"- [Tick{r.tick}] {r.content}" for r in records]
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

    # ── Main entry point ─────────────────────────────────────────────────────

    async def process(self, npc: NPC, world: World) -> dict:
        """Three-layer hierarchical decision cycle.

        1. Strategic layer: refresh goal/plan via lightweight LLM call when due.
        2. Tactical layer: rule-based step tracking, no LLM.
        3. Execution layer: focused LLM call using dynamic context.
        """
        if npc.is_processing:
            return {"action": "idle"}

        npc.is_processing = True
        try:
            # ── Layer 1: Strategic ─────────────────────────────────────────
            if self._needs_strategy(npc, world):
                await self._refresh_strategy(npc, world)

            # ── Layer 2: Tactical (rule-based) ────────────────────────────
            self._advance_plan_if_needed(npc, npc.last_action)

            # ── Layer 3: Execution ────────────────────────────────────────
            # Note: last_action_result is read during context building below,
            # then cleared by world_manager after the next action executes.
            rag_memories = self._retrieve_memories(npc, world)

            # Compute situation flags once; pass to both builders
            tile = world.get_tile(npc.x, npc.y)
            at_exchange = bool(tile and tile.is_exchange)
            nearby = world.get_nearby_npcs_for_npc(npc, config.NPC_HEARING_RADIUS)
            nearby_count = len(nearby)
            if world.player:
                pdist = abs(world.player.x - npc.x) + abs(world.player.y - npc.y)
                if pdist <= config.NPC_HEARING_RADIUS:
                    nearby_count += 1

            system_prompt = build_npc_system_prompt(
                npc, world,
                at_exchange=at_exchange,
                nearby_count=nearby_count,
            )
            context_msg, is_social, _ae, _nc = build_npc_context(
                npc, world, rag_memories
            )

            result = await self.call_llm(
                system_prompt=system_prompt,
                context_message=context_msg,
                history=npc.memory.conversation_history,
                response_schema=NPCAction,
            )

            if result is None:
                import random
                return random.choice(_FALLBACK_ACTIONS)

            # Store exchange in memory
            npc.memory.add_history_turn("user", context_msg)
            npc.memory.add_history_turn("model", result.model_dump_json())

            # Clear inbox after reading
            npc.memory.clear_inbox()

            action = result.model_dump(exclude_none=True)

            # Save to RAG
            self._save_action_memory(npc, action, world)

            logger.info(
                f"[{npc.name}] action={action.get('action')} "
                f"msg={action.get('message','')[:40]}"
            )
            return action

        except Exception as e:
            logger.error(f"[{npc.name}] process error: {e}")
            return {"action": "rest", "thought": "出错了，先休息"}
        finally:
            npc.is_processing = False
