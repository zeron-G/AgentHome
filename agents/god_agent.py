"""God agent: observes world and decides weather/resource interventions."""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from agents.prompts import GodAction, GOD_SYSTEM_PROMPT, build_god_context
from engine.world import GodEntity, World
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class _DialogueOptions(BaseModel):
    options: list[str]


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

    async def generate_dialogue_options(
        self,
        npc_name: str,
        npc_message: str,
        world: World,
    ) -> list[str]:
        """Generate 3 quick-reply options for the player to respond to an NPC."""
        system_prompt = (
            "你是这个世界的幕后导演，负责为玩家生成合适的对话回复选项。\n"
            "根据NPC说的话，生成3个简短的玩家回复选项（不同风格：友好/中立/警惕），"
            "每个不超过15个字。以 JSON 格式返回。"
        )
        context_msg = (
            f"NPC '{npc_name}' 对玩家说：\"{npc_message}\"\n"
            f"当前世界：{world.time.time_str}，天气：{world.weather.value}\n"
            f"请生成3个自然简短的玩家回复选项，放入 options 数组中。"
        )

        try:
            result = await self.call_llm(
                system_prompt=system_prompt,
                context_message=context_msg,
                history=[],
                response_schema=_DialogueOptions,
            )
            if result and result.options:
                return result.options[:3]
        except Exception as e:
            logger.warning(f"[God] generate_dialogue_options error: {e}")

        return ["好的，继续说", "我没有兴趣", "能详细说说吗？"]
