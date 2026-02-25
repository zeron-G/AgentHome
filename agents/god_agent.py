"""God agent: observes world and decides weather/resource interventions.

Also serves as the narrative director — the embodiment of the grandfather's
will. Tracks narrative state, detects when conversations touch key clues,
and injects hidden hints into player dialogue options.
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from agents.prompts import (
    GodAction,
    GOD_SYSTEM_PROMPT,
    build_god_context,
    build_god_hint_prompt,
)
from engine.world import GodEntity, World
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


# ── Narrative clue keywords ────────────────────────────────────────────────
# Each entry maps a keyword group to (clue_id, default_hint_level, hint_context).
# hint_context gives the LLM background on what the clue is about so it can
# craft an appropriate hidden hint.

NARRATIVE_CLUE_KEYWORDS: dict[str, tuple[str, str, str]] = {
    # keyword → (clue_id, hint_level, hint_context_for_llm)
    "矿山": ("mine", "subtle", "西边有一座被废弃的矿山，矿山关闭那年发生了异常的事件"),
    "矿区": ("mine", "subtle", "西边有一座被废弃的矿山，矿山关闭那年发生了异常的事件"),
    "废弃": ("mine", "subtle", "村子西边有废弃的建筑，那里藏着过去的秘密"),
    "老协议": ("pact", "cryptic", "很久以前有人与某种力量签下了协议，保护了村子但付出了代价"),
    "约定": ("pact", "cryptic", "很久以前有人与某种力量签下了协议，保护了村子但付出了代价"),
    "承诺": ("pact", "subtle", "有人曾经做出了重大的承诺来保护这个地方"),
    "离开": ("isolation", "subtle", "村子实际上被某种力量封锁着，没有人能离开也没有外人能进入"),
    "外面": ("isolation", "subtle", "村子与外界之间存在着看不见的屏障"),
    "城市": ("isolation", "subtle", "村子之外的世界对村民来说像是一个模糊的概念"),
    "外界": ("isolation", "subtle", "村子被某种力量与外界隔绝了"),
    "爷爷": ("grandpa", "subtle", "爷爷并没有真正离开，他以另一种形式守护着村子"),
    "老人": ("grandpa", "subtle", "村子里曾经有一位老人，他知道所有的秘密"),
    "消失": ("grandpa", "cryptic", "有些人的'消失'并不意味着他们真的离开了"),
    "红雪": ("omen", "cryptic", "红雪是天灾即将来临的前兆，上一次出现是在矿山关闭那年"),
    "西边": ("west", "subtle", "村子西边有被遗忘的秘密——废弃的农庄和矿山都在那个方向"),
    "废弃农庄": ("west", "subtle", "废弃农庄里可能藏着解开秘密的关键线索"),
    "仪式": ("ritual", "cryptic", "村子里延续的仪式实际上与守护协议有关"),
    "传统": ("ritual", "subtle", "某些被当作传统的习俗实际上有更深层的含义"),
    "地图": ("map", "subtle", "有一张古老的地图指向村子里被遗忘的区域"),
    "手册": ("map", "subtle", "草药手册里夹着的不只是植物的知识"),
}


class _DialogueOptions(BaseModel):
    options: list[str]


class NarrativeState(BaseModel):
    """Serializable narrative progression state.

    Tracks the player's journey through the story — trust level, discovered
    clues, current stage, and which keywords have triggered hints.
    """
    player_trust_level: int = 0       # 0-100, based on player-NPC interaction depth
    clues_revealed: list[str] = []    # list of clue_ids that have been revealed
    secret_stage: int = 0             # 0=normal, 1=anomalies, 2=fragments, 3=truth
    hint_triggers: dict[str, int] = {}  # clue_id → number of times triggered

    def to_dict(self) -> dict:
        """Serialize for save/load."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: dict) -> "NarrativeState":
        return cls(**d)


class GodAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker):
        super().__init__("god", token_tracker)
        self.narrative_state = NarrativeState()

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

    # ── Narrative hint detection ───────────────────────────────────────────

    def should_hint(self, npc_message: str, player_message: str = "") -> tuple[bool, str, str]:
        """Check if the current dialogue touches a narrative clue keyword.

        Scans both the NPC's message and the player's recent message for
        keywords defined in NARRATIVE_CLUE_KEYWORDS.

        Args:
            npc_message: What the NPC said to the player.
            player_message: What the player said (if available).

        Returns:
            (hint_mode, hint_level, hint_context):
              - hint_mode: True if a clue keyword was found.
              - hint_level: "subtle" | "cryptic" | "near_direct".
              - hint_context: Background context string for the LLM.
        """
        combined_text = f"{npc_message} {player_message}"

        for keyword, (clue_id, base_level, context) in NARRATIVE_CLUE_KEYWORDS.items():
            if keyword in combined_text:
                # Escalate hint level based on narrative stage
                hint_level = self._escalate_hint_level(base_level, clue_id)

                # Record the trigger
                self.narrative_state.hint_triggers[clue_id] = (
                    self.narrative_state.hint_triggers.get(clue_id, 0) + 1
                )

                logger.info(
                    f"[God/Narrative] Clue triggered: '{keyword}' → "
                    f"clue={clue_id} level={hint_level}"
                )
                return True, hint_level, context

        return False, "subtle", ""

    def _escalate_hint_level(self, base_level: str, clue_id: str) -> str:
        """Potentially escalate hint level based on narrative stage and prior triggers.

        As the story progresses (higher secret_stage), hints become more direct.
        If the same clue has been triggered multiple times, also escalate.
        """
        stage = self.narrative_state.secret_stage
        trigger_count = self.narrative_state.hint_triggers.get(clue_id, 0)

        levels = ["subtle", "cryptic", "near_direct"]
        base_idx = levels.index(base_level) if base_level in levels else 0

        # Escalate by stage (stage 3 = near_direct allowed)
        stage_boost = min(stage, 2)  # 0, 1, or 2 levels of boost
        # Escalate if same clue triggered 3+ times
        repeat_boost = 1 if trigger_count >= 3 else 0

        final_idx = min(base_idx + stage_boost + repeat_boost, len(levels) - 1)
        return levels[final_idx]

    # ── Dialogue option generation (with hint support) ─────────────────────

    async def generate_dialogue_options(
        self,
        npc_name: str,
        npc_message: str,
        world: World,
        player_message: str = "",
    ) -> list[str]:
        """Generate 3 quick-reply options for the player to respond to an NPC.

        Automatically detects if the conversation touches narrative clues
        and injects a hidden hint from the grandfather if appropriate.
        """
        # Check if we should inject a narrative hint
        hint_mode, hint_level, hint_context = self.should_hint(npc_message, player_message)

        system_prompt, context_msg = build_god_hint_prompt(
            npc_name=npc_name,
            npc_message=npc_message,
            world=world,
            hint_mode=hint_mode,
            hint_level=hint_level,
            hint_context=hint_context,
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

    # ── Narrative state management ─────────────────────────────────────────

    def update_trust_level(self, delta: int):
        """Adjust the player's trust level (clamped to 0-100)."""
        self.narrative_state.player_trust_level = max(
            0, min(100, self.narrative_state.player_trust_level + delta)
        )

    def reveal_clue(self, clue_id: str):
        """Mark a clue as revealed if not already."""
        if clue_id not in self.narrative_state.clues_revealed:
            self.narrative_state.clues_revealed.append(clue_id)
            logger.info(f"[God/Narrative] Clue revealed: {clue_id}")

    def advance_stage(self, stage: int):
        """Advance the secret stage (only forward, never backward)."""
        if stage > self.narrative_state.secret_stage:
            self.narrative_state.secret_stage = stage
            logger.info(f"[God/Narrative] Secret stage advanced to {stage}")

    def get_narrative_state_dict(self) -> dict:
        """Return serializable narrative state for save/load."""
        return self.narrative_state.to_dict()

    def load_narrative_state(self, data: dict):
        """Load narrative state from a saved dict."""
        try:
            self.narrative_state = NarrativeState.from_dict(data)
        except Exception as e:
            logger.warning(f"[God] Failed to load narrative state: {e}")
            self.narrative_state = NarrativeState()
