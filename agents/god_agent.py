"""God agent: observes world and decides weather/resource interventions.

Also serves as the narrative director — the embodiment of the grandfather's
will. Tracks narrative state, detects when conversations touch key clues,
and injects hidden hints into player dialogue options.

角色设定：爷爷 (IV 皇帝) — 用灵魂与恶魔签订契约的守护者。
6结局系统：失败/巩固/推翻/替代(4A)/扭曲(4B)/觉醒/真结局·世界
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.prompts import (
    GodAction,
    GOD_SYSTEM_PROMPT,
    build_god_context,
    build_god_hint_prompt,
    _load_personality,
)
from config_narrative import ALL_NPC_IDS, SEASON_CONFIG, ENDING_CONDITIONS
from engine.world import GodEntity, World
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


# ── Narrative clue keywords ────────────────────────────────────────────────
# Each entry maps a keyword group to (clue_id, default_hint_level, hint_context).
# hint_context gives the LLM background on what the clue is about so it can
# craft an appropriate hidden hint.
#
# 线索体系对齐 config_narrative.CLUE_DEFINITIONS（12条线索）

NARRATIVE_CLUE_KEYWORDS: dict[str, tuple[str, str, str]] = {
    # keyword → (clue_id, hint_level, hint_context_for_llm)

    # ── 结界与封锁 ──
    "离开": ("barrier_edge", "subtle", "村子被结界封锁着，没有人能离开也没有外人能进入"),
    "外面": ("barrier_edge", "subtle", "村子与外界之间存在着看不见的结界"),
    "城市": ("barrier_edge", "subtle", "村子之外的世界对村民来说像是一个模糊的概念"),
    "外界": ("barrier_edge", "subtle", "村子被结界与外界隔绝了"),
    "边界": ("barrier_edge", "subtle", "村子的边缘有一道看不见的墙"),

    # ── 爷爷与契约 ──
    "爷爷": ("grandpa_trace", "subtle", "爷爷并没有真正离开，他以另一种形式守护着村子"),
    "老人": ("grandpa_trace", "subtle", "村子里曾经有一位老人，他知道所有的秘密"),
    "消失": ("grandpa_trace", "cryptic", "有些人的'消失'并不意味着他们真的离开了"),
    "契约": ("soul_contract", "cryptic", "一份用灵魂为代价的契约，保护了村子但也封锁了一切"),
    "老协议": ("soul_contract", "cryptic", "很久以前有人与恶魔签下了契约，用灵魂保护了村子"),
    "约定": ("soul_contract", "cryptic", "很久以前有人与恶魔签下了契约，保护了村子但付出了代价"),
    "承诺": ("soul_contract", "subtle", "有人曾经做出了重大的承诺来保护这个地方"),

    # ── 认知屏障 ──
    "记不清": ("cognitive_fog", "subtle", "村民的记忆被模糊了——他们记不住不该记住的事"),
    "忘了": ("cognitive_fog", "subtle", "遗忘不是偶然的，而是结界对心智的保护"),
    "奇怪": ("cognitive_fog", "subtle", "如果你觉得什么事情不对劲，也许是因为真的有什么不对劲"),

    # ── 木的法阵维护 ──
    "修缮": ("array_maintenance", "subtle", "定期修缮的老物件维护着某种看不见的力量"),
    "老物件": ("array_maintenance", "subtle", "那些老物件拿在手里有温度，像是有什么东西活在其中"),
    "锻造": ("array_maintenance", "subtle", "工匠修缮的某些东西不是普通的器具，它们有特殊的用途"),
    "工具": ("array_maintenance", "subtle", "木的工具箱里有刻着神秘符号的家伙——他以为是传家宝"),
    "符号": ("array_maintenance", "cryptic", "这些符号出现在不止一个地方——工具、建筑、地图"),

    # ── 穗的感知 ──
    "天上": ("sui_perception", "subtle", "天空中也许不只有星星在看着这个村子"),
    "老爷爷": ("sui_perception", "subtle", "穗说的'天上的老爷爷'也许不只是孩子的想象"),
    "眼睛": ("sui_perception", "subtle", "有人一直在看着你们，守护着你们"),
    "梦": ("sui_perception", "subtle", "梦境有时候比现实更接近真相"),

    # ── 棠的交易 ──
    "等": ("tang_deal", "subtle", "棠在等的不只是一个人——他在等一个答案"),
    "交易": ("tang_deal", "cryptic", "有人已经和恶魔做了一笔交易，代价是被吊在两个世界之间"),
    "看见": ("tang_deal", "cryptic", "看见真相的力量有代价——清醒也可以是一种折磨"),

    # ── 岚婆的直觉 ──
    "通灵": ("lan_intuition", "subtle", "岚婆的大部分通灵是表演——但有些不是"),
    "占卜": ("lan_intuition", "subtle", "占卜的结果有时准得可怕——她自己也害怕"),
    "直觉": ("lan_intuition", "subtle", "有些人的直觉能绕过结界的认知屏障"),

    # ── 商人/恶魔 ──
    "恶魔": ("demon_nature", "cryptic", "一切来自恶魔的力量都有代价，而代价往往是你最珍视的东西"),
    "代价": ("demon_nature", "cryptic", "灵魂、自由、记忆……代价从来不止一种"),
    "商人": ("merchant_identity", "subtle", "商人是唯一能自由进出村子的外来者——为什么？"),

    # ── 仪式与传统 ──
    "仪式": ("ritual_truth", "cryptic", "村子里延续的仪式实际上与恶魔契约有关"),
    "传统": ("ritual_truth", "subtle", "某些被当作传统的习俗实际上有更深层的含义"),
    "食物消失": ("ritual_truth", "cryptic", "每年放在村中心的食物总是消失——是谁在吃？"),

    # ── 时间与轮回 ──
    "多久了": ("reincarnation", "subtle", "记忆中的时间和真实的时间也许差了很多很多年"),
    "轮回": ("reincarnation", "cryptic", "也许这不是你第一次来到这个村子"),
    "竖线": ("reincarnation", "cryptic", "山的屋子里有一面墙，上面的竖线多到数不清——每一条是一个春天"),

    # ── 禾丈夫之死 ──
    "丈夫": ("he_husband_death", "subtle", "禾的丈夫曾试图离开村子——然后他死了"),
    "爸爸": ("he_husband_death", "subtle", "穗的爸爸去了哪里？禾说'他走了'——但走向了哪里？"),

    # ── 地图与废弃区域 ──
    "地图": ("map_fragments", "subtle", "有一张古老的地图指向村子里被遗忘的区域"),
    "碎片": ("map_fragments", "subtle", "地图碎片拼合后也许能找到某个重要的位置"),
    "西边": ("map_fragments", "subtle", "村子西边有被遗忘的秘密"),
    "废弃": ("map_fragments", "subtle", "废弃的区域里可能藏着解开秘密的关键线索"),
}


class _DialogueOptions(BaseModel):
    options: list[str]


class NarrativeState(BaseModel):
    """Serializable narrative progression state.

    Tracks the player's journey through the story — per-NPC trust, discovered
    clues, current stage/season, and which keywords have triggered hints.
    """
    # Per-NPC trust (0-100 each), replaces old global trust
    npc_trust: dict[str, int] = Field(
        default_factory=lambda: {npc_id: 50 for npc_id in ALL_NPC_IDS}
    )
    clues_revealed: list[str] = []    # list of clue_ids that have been revealed
    secret_stage: int = 0             # 0=spring, 1=summer, 2=autumn, 3=winter
    current_season: str = "spring"    # tracks current season key
    hint_triggers: dict[str, int] = {}  # clue_id → number of times triggered
    endings_unlocked: list[str] = []  # ending keys that have been unlocked

    def to_dict(self) -> dict:
        """Serialize for save/load."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: dict) -> "NarrativeState":
        return cls(**d)

    def average_trust(self) -> float:
        """Return average trust across all NPCs."""
        if not self.npc_trust:
            return 50.0
        return sum(self.npc_trust.values()) / len(self.npc_trust)


class GodAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker):
        super().__init__("god", token_tracker)
        self.narrative_state = NarrativeState()

    async def process(self, god: GodEntity, world: World) -> dict | None:
        """Build world context for God, call LLM, return action dict or None."""
        if god.is_processing:
            return None

        god.is_processing = True
        try:
            system_prompt = GOD_SYSTEM_PROMPT.format(personality=god.personality)

            # Inject season-aware commentary style from god.yaml
            god_personality = _load_personality("npc_god")
            if god_personality:
                stage = self.narrative_state.secret_stage
                styles = god_personality.get("commentary_styles", {})
                style_key = f"stage_{stage}"
                style = styles.get(style_key, styles.get("stage_0", ""))
                if style:
                    season = self.narrative_state.current_season
                    system_prompt += f"\n\n【当前季节：{season}】旁白风格：{style}"

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

    def update_npc_trust(self, npc_id: str, delta: int):
        """Adjust a specific NPC's trust level (clamped to 0-100)."""
        current = self.narrative_state.npc_trust.get(npc_id, 50)
        self.narrative_state.npc_trust[npc_id] = max(0, min(100, current + delta))

    def get_npc_trust(self, npc_id: str) -> int:
        """Get a specific NPC's trust level."""
        return self.narrative_state.npc_trust.get(npc_id, 50)

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

    def update_season(self, day: int):
        """Update current season based on in-game day number."""
        for season_key, cfg in SEASON_CONFIG.items():
            start, end = cfg["day_range"]
            if start <= day <= end:
                if self.narrative_state.current_season != season_key:
                    self.narrative_state.current_season = season_key
                    self.narrative_state.secret_stage = cfg["secret_stage"]
                    logger.info(f"[God/Narrative] Season changed to {cfg['name']}")
                break

    def check_ending_conditions(self) -> Optional[str]:
        """Check if any ending condition is met. Returns ending key or None.

        Checks endings in priority order. Some endings require others to be
        unlocked first (e.g., trade endings require reinforce or overthrow).
        """
        state = self.narrative_state
        for ending_key, condition in ENDING_CONDITIONS.items():
            # Check prerequisite endings
            prereqs = condition.get("unlock_requirement")
            if prereqs:
                if not any(p in state.endings_unlocked for p in prereqs):
                    continue

            # Check minimum clue count
            min_clues = condition.get("min_clues_revealed", 0)
            if len(state.clues_revealed) < min_clues:
                continue

            # Check trust requirements (if any)
            trust_req = condition.get("trust_requirement")
            if trust_req:
                for npc_id, threshold in trust_req.items():
                    if state.npc_trust.get(npc_id, 50) < threshold:
                        break
                else:
                    # All trust requirements met
                    return ending_key
                continue  # Some trust requirement not met

            # If no trust requirement, check stage
            min_stage = condition.get("min_stage", 0)
            if state.secret_stage >= min_stage:
                return ending_key

        return None

    def unlock_ending(self, ending_key: str):
        """Record that an ending has been unlocked (for prerequisite tracking)."""
        if ending_key not in self.narrative_state.endings_unlocked:
            self.narrative_state.endings_unlocked.append(ending_key)
            logger.info(f"[God/Narrative] Ending unlocked: {ending_key}")

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
