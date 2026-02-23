"""God agent: observes world and decides weather/resource interventions."""
from __future__ import annotations

import logging

from agents.base_agent import BaseAgent
from agents.prompts import GodAction, GOD_SYSTEM_PROMPT, build_god_context
from engine.world import GodEntity, World
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class GodAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker):
        super().__init__("god", token_tracker)

    async def process(self, god: GodEntity, world: World) -> dict | None:
        """Build world context for God, call Gemini, return action dict or None."""
        if god.is_processing:
            return None

        god.is_processing = True
        try:
            system_prompt = GOD_SYSTEM_PROMPT.format(personality=god.personality)
            context_msg = build_god_context(god, world)

            result = await self.call_llm(
                system_prompt=system_prompt,
                context_message=context_msg,
                history=god.memory.conversation_history,
                response_schema=GodAction,
            )

            if result is None:
                return None

            # Store exchange in God's memory
            god.memory.add_history_turn("user", context_msg)
            god.memory.add_history_turn("model", result.model_dump_json())

            # Clear pending commands after processing
            god.pending_commands.clear()

            action = result.model_dump(exclude_none=True)
            logger.info(f"[God] action={action.get('action')} commentary={action.get('commentary','')[:60]}")
            return action

        except Exception as e:
            logger.error(f"[God] process error: {e}")
            return None
        finally:
            god.is_processing = False
