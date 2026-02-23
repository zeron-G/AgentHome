"""NPC agent: processes world context and returns a structured action."""
from __future__ import annotations

import logging

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
    def __init__(self, token_tracker: TokenTracker):
        # Use a shared agent ID for NPCs to group token usage
        super().__init__("npcs", token_tracker)

    async def process(self, npc: NPC, world: World) -> dict:
        """
        Build context for this NPC, call Gemini, return action dict.
        Falls back to rest if LLM fails.
        """
        if npc.is_processing:
            return {"action": "idle"}

        npc.is_processing = True
        try:
            system_prompt = build_npc_system_prompt(npc, world)
            context_msg, is_social = build_npc_context(npc, world)

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
            logger.info(f"[{npc.name}] action={action.get('action')} msg={action.get('message','')[:40]}")
            return action

        except Exception as e:
            logger.error(f"[{npc.name}] process error: {e}")
            return {"action": "rest", "thought": "出错了，先休息"}
        finally:
            npc.is_processing = False
