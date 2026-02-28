"""LLM prompt templates and structured output schemas for all agents.

Modular design: system prompt sections are assembled based on the NPC's
current situation (nearby NPCs, at exchange, has craftable materials,
has pending proposals).

Narrative system: NPC personality YAML files are loaded from
agents/personalities/ and injected into system prompts. The isolation
awareness barrier is automatically applied to all NPCs.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel

import config

logger = logging.getLogger(__name__)

# ── Personality YAML loading ────────────────────────────────────────────────

_PERSONALITIES_DIR = os.path.join(os.path.dirname(__file__), "personalities")


@lru_cache(maxsize=16)
def _load_personality(npc_id: str) -> dict | None:
    """Load a personality YAML file for the given NPC.

    Looks for agents/personalities/{short_id}.yaml where short_id is
    npc_id with 'npc_' prefix stripped (e.g. 'npc_he' → 'he.yaml').
    Returns parsed dict or None if the file doesn't exist or can't be parsed.
    """
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — personality YAML loading disabled")
        return None

    short_id = npc_id.replace("npc_", "", 1)
    path = os.path.join(_PERSONALITIES_DIR, f"{short_id}.yaml")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning(f"Failed to load personality YAML for {npc_id}: {e}")
        return None


def reload_personalities():
    """Clear the personality cache so YAML files are re-read on next access."""
    _load_personality.cache_clear()



# ── Pydantic schemas for structured LLM output ───────────────────────────────

class NPCStrategy(BaseModel):
    """Strategic planning schema (Level-1). Goal, reasoning, mood, and steps."""
    goal: str            # Long-term goal, e.g. "建造一张床以提升睡眠效率"
    reasoning: str       # Why this goal was chosen (1-2 sentences)
    mood: str            # Current emotional state (e.g. "平静", "焦虑", "好奇")
    steps: list[str]     # 3-5 concrete, actionable steps


class NPCAction(BaseModel):
    """Flexible NPC action schema. Only relevant fields are used per action type."""
    # Thought FIRST — required inner monologue (ReAct pattern)
    thought: str  # Required! Inner monologue before acting
    # Core
    action: str  # move|gather|talk|trade|rest|think|interrupt|eat|sleep|exchange|buy_food
                 # craft|sell|buy|use_item|propose_trade|accept_trade|reject_trade|counter_trade
    # move
    dx: Optional[int] = None
    dy: Optional[int] = None
    # talk / interrupt
    message: Optional[str] = None
    target_id: Optional[str] = None
    # trade / propose / counter
    offer_item: Optional[str] = None
    offer_qty: Optional[int] = None
    request_item: Optional[str] = None
    request_qty: Optional[int] = None
    # think
    note: Optional[str] = None
    # legacy exchange (fixed rate)
    exchange_item: Optional[str] = None
    exchange_qty: Optional[int] = None
    # legacy buy_food / buy
    quantity: Optional[int] = None
    # craft
    craft_item: Optional[str] = None   # rope | potion | tool | bread
    # market sell / buy (floating price)
    sell_item: Optional[str] = None
    sell_qty: Optional[int] = None
    buy_item: Optional[str] = None
    buy_qty: Optional[int] = None
    # use consumable / equip
    use_item: Optional[str] = None     # potion | bread | tool | rope
    # accept/reject/counter proposal
    proposal_from: Optional[str] = None  # npc_id of proposer
    # build furniture
    build_furniture: Optional[str] = None  # bed | table | chair
    # long-term plan tracking (internal monologue)
    plan: Optional[str] = None


class GodAction(BaseModel):
    """God action schema."""
    action: str  # set_weather | spawn_resource
    weather: Optional[str] = None        # sunny | rainy | storm
    resource_type: Optional[str] = None  # wood | stone | ore | food | herb
    x: Optional[int] = None
    y: Optional[int] = None
    quantity: Optional[int] = None
    commentary: str = ""


# ── Level-1 Strategic planning prompt ─────────────────────────────────────────

_STRATEGY_SYSTEM = """你是{name}（{title}），一个生活在2D沙盒世界里的角色。
性格: {personality}

【目标参考】
{profile_goals}

【规则速查】
资源: wood(森林) stone/ore(岩石) food(草灌木) herb(森林)
制造: rope=wood×2 | tool=stone+wood | potion=herb×2 | bread=food×2
建造: bed=wood×4(sleep→80) | table=wood×3(craft×2) | chair=wood×2(rest→35)
交易所(10,10)附近 | 装备tool→采集×2 | rope→移动-1体力 | 背包20格

【任务】根据当前状态：
1. 描述你当前的情绪状态（mood）
2. 解释你的想法（reasoning）
3. 制定3-5步具体行动计划
返回JSON:"""


# ── Prompt module constants ────────────────────────────────────────────────────

_LAYER_IDENTITY = """你是{name}，{role}。{tarot}。
{backstory}
"""

_LAYER_WORLD_RULES = """【世界】{width}×{height}格 | 地块:草/森/岩/镇 | 资源:wood(森)·stone/ore(岩)·food(草)·herb(森)
移动1格(dx/dy取-1,0,1) | rest+20(椅+35) | sleep+50(床+80) | eat+{food_restore}体力
背包{inv_max}格(金币不占) | 装备:tool→采集×2, rope→移动-1 | think=私人笔记
"""

_ACTION_CHEATSHEET = """【可用行动】返回JSON，thought字段必填！
基础: move(dx,dy) | gather | rest | sleep | eat | think(note)
社交: talk(message,target_id) | interrupt(message,target_id)
{extra_actions}
每次只返回一个JSON动作。thought=你的内心想法(必填)。"""

# Extra action lines (dynamically composed)
_EXTRA_EXCHANGE = "交易所: sell(sell_item,sell_qty) | buy(buy_item,buy_qty) | exchange(exchange_item,exchange_qty) | buy_food(quantity)"
_EXTRA_CRAFT = "制造: craft(craft_item) 可造:{craft_options} | use_item(use_item) 效果:potion→{potion_energy}体力/bread→{bread_energy}体力/tool→采集×2/rope→移动-1"
_EXTRA_NEGOTIATE = "提案: propose_trade(target_id,offer_item,offer_qty,request_item,request_qty)"
_EXTRA_BUILD = "建造: build(build_furniture) 可建:{build_options} | 优先:bed(sleep→80)→table(craft×2)→chair(rest→35)"

_PROPOSALS_SECTION = """【待处理提案——本轮必须回应！】
{proposals}
回应: accept_trade(proposal_from) | reject_trade(proposal_from) | counter_trade(proposal_from,offer_item,offer_qty,request_item,request_qty)"""


# ── Context templates ─────────────────────────────────────────────────────────

_CTX_STATUS = """=== 状态 (Tick {tick}, {time_str}, 天气:{weather}) ===
位置:({x},{y}) 体力:{energy}/100  装备槽:{equipped}  背包:{inv_count}/{inv_max}格  当前地块家具:{tile_furniture}
背包: 木{wood} 石{stone} 矿{ore} 食{food} 草药{herb} | 绳{rope} 药水{potion} 工具{tool} 面包{bread} | 金币{gold:.1f}
地块:{tile_type}  资源:{resource_info}
{exchange_hint}"""

_CTX_STRATEGY = """=== 当前目标与计划 ===
目标: {goal}
计划步骤:
{plan_steps}
"""

_CTX_VISION = """=== 视野(5×5) ===
{vision_grid}
"""

_CTX_MARKET = """=== 市场价格 ===
{market_table}
"""

_CTX_NEARBY = """=== 附近角色({radius}格内) ===
{nearby_npcs}
"""

_CTX_MEMORY = """=== 个人笔记 ===
{notes}
=== 相关记忆 ===
{rag_memories}
"""

_CTX_INBOX = """=== 收件箱 ===
{inbox}
"""

_CTX_EVENTS = """=== 近期事件 ===
{recent_events}
"""

_CTX_FOOTER_SOCIAL = "\n你的下一步行动（JSON）:"
_CTX_FOOTER_ALONE  = "\n你独处一隅，可探索、采集、制造或前往交易所。返回JSON动作:"


# ── God prompts ────────────────────────────────────────────────────────────────

GOD_SYSTEM_PROMPT = """你是这个世界的神明。

【神明性格】{personality}

【能力】
- 改变天气：晴天(sunny)、雨天(rainy)、暴风(storm)
- 在指定位置刷新资源：wood/stone/ore/food/herb
- NPC感知不到你的存在

【动作格式】返回JSON：
- 改变天气: {{"action":"set_weather","weather":"sunny/rainy/storm","commentary":"旁白"}}
- 刷新资源: {{"action":"spawn_resource","resource_type":"wood/stone/ore/food/herb","x":坐标,"y":坐标,"quantity":数量,"commentary":"旁白"}}

旁白要有神性诗意，简短1-2句。"""


GOD_CONTEXT = """=== 世界状态 (Tick {tick}, {time_str}) ===
天气: {weather}

NPC状态:
{npc_summary}

最近事件:
{recent_events}

{pending_commands_section}作为神明，你如何干预这个世界？返回JSON:"""


# ── Vision grid builder ────────────────────────────────────────────────────────

_TILE_CHARS = {
    "grass": "·", "water": "≈", "rock": "▲", "forest": "♣", "town": "⌂",
}
_RESOURCE_CHARS = {
    "wood": "W", "stone": "S", "ore": "O", "food": "F", "herb": "H",
}


def build_vision_grid(npc, world) -> str:
    radius = config.NPC_VISION_RADIUS
    lines = []
    for dy in range(-radius, radius + 1):
        row = []
        for dx in range(-radius, radius + 1):
            tx, ty = npc.x + dx, npc.y + dy
            if not (0 <= tx < world.width and 0 <= ty < world.height):
                row.append("X")
                continue
            tile = world.get_tile(tx, ty)
            if tile is None:
                row.append("?")
                continue
            ch = _TILE_CHARS.get(tile.tile_type.value, "?")
            if tile.resource and tile.resource.quantity > 0:
                ch = _RESOURCE_CHARS.get(tile.resource.resource_type.value, ch)
            if tile.npc_ids:
                npc_here = world.get_npc(tile.npc_ids[0])
                if npc_here:
                    ch = npc_here.name[0].upper()
            if tile.player_here:
                ch = "P"
            if dx == 0 and dy == 0:
                ch = "@"
            if tile.is_exchange:
                ch = "£" if (dx == 0 and dy == 0) else "E"
            elif tile.furniture == "bed":
                ch = "B"
            elif tile.furniture == "table":
                ch = "T"
            elif tile.furniture == "chair":
                ch = "C"
            row.append(ch)
        lines.append(" ".join(row))
    legend = "图例: @=你 P=玩家 E=交易所 W=木 S=石 O=矿 F=食 H=草药 ♣=森 ▲=岩 ⌂=城 ·=草 B=床 T=桌 C=椅"
    return "\n".join(lines) + "\n" + legend


# ── Market price table builder ─────────────────────────────────────────────────

def _build_market_table(world) -> str:
    lines = ["物品     | 当前价 | 基准  | 趋势 | 变化%"]
    lines.append("-" * 40)
    for item, mp in world.market.prices.items():
        lines.append(
            f"{item:<8} | {mp.current:6.2f} | {mp.base:5.2f} | {mp.trend:2}  | {mp.change_pct:+.1f}%"
        )
    return "\n".join(lines)


# ── Craftable options builder ─────────────────────────────────────────────────

def _build_craft_options(npc) -> str:
    lines = []
    for item, recipe in config.CRAFTING_RECIPES.items():
        recipe_str = " + ".join(f"{mat}×{qty}" for mat, qty in recipe.items())
        can = all(npc.inventory.get(mat) >= qty for mat, qty in recipe.items())
        status = "✓" if can else "✗"
        lines.append(f"  {status} {item}: 需要 {recipe_str}")
    return "\n".join(lines) or "（暂无可制造配方）"


# ── Builder functions ─────────────────────────────────────────────────────────

def build_npc_system_prompt(
    npc,
    world,
    *,
    at_exchange: bool = False,
    nearby_count: int = 0,
) -> str:
    """Assemble layered persona prompt based on NPC's current situation.

    5-layer architecture:
      Layer 1 — Identity core (name, role, tarot, background)
      Layer 2 — Worldview (cognitive barrier integrated)
      Layer 3 — Inner life (hidden desire, mood, emotional triggers)
      Layer 4 — Social (relationships, forbidden topics)
      Layer 5 — Action cheatsheet (compact, dynamic)
    """
    profile = getattr(npc, "profile", None)
    personality_data = _load_personality(npc.npc_id)

    # ── Layer 1: Identity core ─────────────────────────────────────────
    title = profile.title if profile else ""
    backstory_raw = profile.backstory if profile else ""
    tarot = personality_data.get("tarot", "") if personality_data else ""
    role = personality_data.get("role", title) if personality_data else title

    prompt = _LAYER_IDENTITY.format(
        name=npc.name,
        role=role or "探险者",
        tarot=tarot,
        backstory=backstory_raw or "一位来到这片土地寻找机遇的旅人。",
    )

    # ── Voice samples (speech style anchoring) ─────────────────────────
    if personality_data:
        voice_samples = personality_data.get("voice_samples", [])
        if voice_samples:
            # Merchant has day/night split
            if isinstance(voice_samples, dict):
                time_key = "night" if world.time.is_night else "day"
                samples = voice_samples.get(time_key, [])
            else:
                samples = voice_samples
            if samples:
                prompt += "【你的说话风格示例】\n" + "\n".join(f'"{s}"' for s in samples[:4]) + "\n\n"

    # ── Layer 2: Worldview (cognitive barrier woven in) ─────────────────
    if personality_data:
        worldview = personality_data.get("worldview", "")
        if worldview:
            prompt += f"【你眼中的世界】\n{worldview.strip()}\n\n"

        # Merchant day/night mode switch
        if npc.npc_id == "npc_shangren":
            if world.time.is_night:
                mode_data = personality_data.get("night_mode", {})
            else:
                mode_data = personality_data.get("day_mode", {})
            if mode_data:
                prompt += f"【当前模式】{mode_data.get('personality', '')}\n"
                prompt += f"行为: {mode_data.get('behavior', '')}\n"
                prompt += f"说话风格: {mode_data.get('speech_style', '')}\n\n"

    # ── Layer 3: Inner life ────────────────────────────────────────────
    inner_parts = []
    if personality_data:
        hidden_desire = personality_data.get("hidden_desire", "")
        if hidden_desire:
            inner_parts.append(f"内心渴望: {hidden_desire.strip()}")

        # Mood from strategic layer
        mood = getattr(npc, "mood", "")
        if mood:
            inner_parts.append(f"当前情绪: {mood}")

        # Emotional triggers (compact summary)
        triggers = personality_data.get("emotional_triggers", {})
        if triggers and isinstance(triggers, dict):
            trigger_lines = [f"  {k}: {v}" for k, v in list(triggers.items())[:4]]
            inner_parts.append("情境反应:\n" + "\n".join(trigger_lines))

    if inner_parts:
        prompt += "【内心】\n" + "\n".join(inner_parts) + "\n\n"

    # ── Layer 4: Social relationships & forbidden topics ───────────────
    if personality_data:
        # YAML relationships (richer than profile.relationships)
        yaml_rels = personality_data.get("relationships")
        if yaml_rels and isinstance(yaml_rels, dict):
            rel_lines = []
            for other_id, desc in yaml_rels.items():
                other_npc = world.get_npc(other_id)
                other_name = other_npc.name if other_npc else other_id.replace("npc_", "")
                rel_lines.append(f"- {other_name}: {desc}")
            if rel_lines:
                prompt += "【关系】\n" + "\n".join(rel_lines) + "\n\n"

        # Forbidden topics
        forbidden = personality_data.get("forbidden_topics")
        if forbidden:
            if isinstance(forbidden, list) and len(forbidden) > 0:
                prompt += "【话题禁区】\n"
                for topic in forbidden:
                    if isinstance(topic, str):
                        prompt += f"- {topic}\n"
                    elif isinstance(topic, dict):
                        for k, v in topic.items():
                            prompt += f"- {k}: {v.strip()}\n"
                prompt += "\n"
            elif isinstance(forbidden, dict):
                prompt += "【话题禁区】\n"
                for topic, reaction in forbidden.items():
                    prompt += f"- {topic}: {reaction.strip()}\n"
                prompt += "\n"

    # ── World rules (compact) ──────────────────────────────────────────
    prompt += _LAYER_WORLD_RULES.format(
        width=world.width,
        height=world.height,
        food_restore=config.FOOD_ENERGY_RESTORE,
        inv_max=config.INVENTORY_MAX_SLOTS,
    )

    # ── Layer 5: Action cheatsheet (dynamic extra actions) ─────────────
    extra_lines = []
    inv = npc.inventory

    # Exchange actions — when at exchange or has items/gold
    has_sellable = inv.total_items() > 0
    has_buying_power = inv.gold > 0
    if at_exchange or has_sellable or has_buying_power:
        extra_lines.append(_EXTRA_EXCHANGE)

    # Crafting — when NPC has at least one craftable ingredient
    has_any_material = (inv.wood > 0 or inv.stone > 0 or inv.herb > 0 or inv.food >= 2)
    if has_any_material:
        potion_e = config.ITEM_EFFECTS.get("potion", {}).get("energy", 60)
        bread_e = config.ITEM_EFFECTS.get("bread", {}).get("energy", 50)
        craft_options = _build_craft_options(npc)
        extra_lines.append(_EXTRA_CRAFT.format(
            craft_options=craft_options, potion_energy=potion_e, bread_energy=bread_e,
        ))

    # Negotiation — only when nearby NPCs exist
    if nearby_count > 0:
        extra_lines.append(_EXTRA_NEGOTIATE)

    # Build — when NPC has enough wood for cheapest furniture (chair=2)
    if inv.wood >= 2:
        build_parts = []
        for furniture, recipe in config.FURNITURE_RECIPES.items():
            recipe_str = "+".join(f"{mat}×{qty}" for mat, qty in recipe.items())
            can = "✓" if all(inv.get(mat) >= qty for mat, qty in recipe.items()) else "✗"
            build_parts.append(f"{can}{furniture}({recipe_str})")
        extra_lines.append(_EXTRA_BUILD.format(build_options=" ".join(build_parts)))

    extra_str = "\n".join(extra_lines) if extra_lines else ""
    prompt += _ACTION_CHEATSHEET.format(extra_actions=extra_str)

    # ── Proposals (urgent — must respond this turn) ────────────────────
    proposals = getattr(npc, "pending_proposals", [])
    if proposals:
        prop_lines = []
        for p in proposals:
            from_id = p.get("from_id", "")
            if from_id == "player":
                from_name = world.player.name if world.player else "玩家"
            else:
                from_npc = world.get_npc(from_id)
                from_name = from_npc.name if from_npc else from_id
            prop_lines.append(
                f"  来自{from_name}({from_id}): {p['offer_qty']}{p['offer_item']}↔{p['request_qty']}{p['request_item']} (第{p.get('round',1)}轮)"
            )
        prompt += "\n" + _PROPOSALS_SECTION.format(proposals="\n".join(prop_lines))

    # ── Behavior guidelines (compact) ──────────────────────────────────
    prompt += (
        "\n\n【准则】按目标/计划行动 | 背包≥18格时卖出换金 | 与玩家态度自然"
    )
    return prompt


def build_npc_context(npc, world, rag_memories: str = "") -> tuple[str, bool, bool, int]:
    """Return (context_str, is_social_mode).

    Dynamic injection rules:
    - Market table: only shown when NPC is at the exchange tile
    - Nearby section + inbox: only shown when there are nearby characters / messages
    - Recent events: trimmed to 5 (down from 8) to save tokens
    - Goal/plan: injected from NPC.goal / NPC.plan set by the strategic layer
    """
    tile = world.get_tile(npc.x, npc.y)
    tile_type = tile.tile_type.value if tile else "unknown"
    at_exchange = bool(tile and tile.is_exchange)

    resource_info = "无"
    if tile and tile.resource and tile.resource.quantity > 0:
        r = tile.resource
        resource_info = f"{r.resource_type.value} x{r.quantity}/{r.max_quantity}"

    exchange_hint = ""
    if at_exchange:
        prices = world.market.prices
        hint_parts = []
        for item in ("wood", "stone", "ore", "food", "herb"):
            mp = prices.get(item)
            if mp:
                hint_parts.append(f"{item}={mp.current:.1f}金")
        exchange_hint = f"★ 你正站在交易所！当前卖价参考: {', '.join(hint_parts[:5])}\n"

    vision_grid = build_vision_grid(npc, world)

    notes_str = "\n".join(f"- {n}" for n in npc.memory.personal_notes) or "（暂无）"
    inbox_str = "\n".join(f"- {m}" for m in npc.memory.inbox) or "（无新消息）"
    # Trim to 5 most recent events (saves ~50-80 tokens vs 8)
    recent = world.recent_events[-5:] if world.recent_events else []
    recent_str = "\n".join(f"- {e}" for e in recent) or "（无）"
    rag_str = rag_memories if rag_memories else "（暂无相关记忆）"

    nearby = world.get_nearby_npcs_for_npc(npc, config.NPC_HEARING_RADIUS)

    # Player proximity check
    player_nearby = []
    if world.player:
        pdist = abs(world.player.x - npc.x) + abs(world.player.y - npc.y)
        if pdist <= config.NPC_HEARING_RADIUS:
            inv = world.player.inventory
            p_equipped = world.player.equipped or "空"
            player_nearby.append(
                f"- {world.player.name}(player) @ ({world.player.x},{world.player.y}) "
                f"背包:木{inv.wood}/石{inv.stone}/矿{inv.ore}/食{inv.food}/金{inv.gold:.0f} "
                f"体力:{world.player.energy} 装备:{p_equipped} "
                f"背包:{inv.total_items()}/{config.INVENTORY_MAX_SLOTS}格"
            )

    has_social = bool(nearby or npc.memory.inbox or player_nearby)
    nearby_count = len(nearby) + len(player_nearby)

    nearby_str_parts = []
    for n in nearby:
        inv = n.inventory
        prof = getattr(n, "profile", None)
        title = f"[{prof.title}]" if prof and prof.title else ""
        nearby_str_parts.append(
            f"- {n.name}{title}({n.npc_id}) @ ({n.x},{n.y}) "
            f"背包:木{inv.wood}/石{inv.stone}/矿{inv.ore}/食{inv.food}"
            f"/草药{inv.herb}/金{inv.gold:.0f} 体力:{n.energy} "
            f"提案:{len(getattr(n,'pending_proposals',[]))}"
        )
    nearby_str_parts += player_nearby
    nearby_str = "\n".join(nearby_str_parts) or "（无）"

    # Build context
    inv = npc.inventory
    tile_furniture = tile.furniture if tile and tile.furniture else "无"
    status = _CTX_STATUS.format(
        tick=world.time.tick, time_str=world.time.time_str, weather=world.weather.value,
        x=npc.x, y=npc.y, energy=npc.energy,
        equipped=npc.equipped or "空",
        inv_count=inv.total_items(),
        inv_max=config.INVENTORY_MAX_SLOTS,
        tile_furniture=tile_furniture,
        wood=inv.wood, stone=inv.stone, ore=inv.ore, food=inv.food,
        herb=inv.herb, rope=inv.rope, potion=inv.potion,
        tool=inv.tool, bread=inv.bread, gold=inv.gold,
        tile_type=tile_type, resource_info=resource_info,
        exchange_hint=exchange_hint,
    )

    ctx = status

    # ── Observation feedback (ReAct pattern) ─────────────────────────────────
    if npc.last_action_result:
        ctx += f"\n【上一轮行动结果】{npc.last_action} → {npc.last_action_result}\n"

    # ── Strategic goal/plan injection (Level-1 → Level-3 communication) ──────
    if npc.goal or npc.plan:
        plan_steps = "\n".join(
            f"  {i+1}. {step}" for i, step in enumerate(npc.plan)
        ) or "  （制定中...）"
        ctx += _CTX_STRATEGY.format(goal=npc.goal or "（制定中）", plan_steps=plan_steps)

    ctx += _CTX_VISION.format(vision_grid=vision_grid)

    # Market table: only inject when at exchange (saves ~150 tokens most of the time)
    if at_exchange:
        ctx += _CTX_MARKET.format(market_table=_build_market_table(world))

    if has_social:
        ctx += _CTX_NEARBY.format(radius=config.NPC_HEARING_RADIUS, nearby_npcs=nearby_str)
        ctx += _CTX_INBOX.format(inbox=inbox_str)

    ctx += _CTX_MEMORY.format(notes=notes_str, rag_memories=rag_str)
    ctx += _CTX_EVENTS.format(recent_events=recent_str)

    if has_social:
        ctx += _CTX_FOOTER_SOCIAL
    else:
        ctx += _CTX_FOOTER_ALONE

    return ctx, has_social, at_exchange, nearby_count


def build_strategy_system_prompt(npc, world) -> str:
    """Build the lightweight system prompt for the Level-1 strategic planning call."""
    profile = getattr(npc, "profile", None)
    title = profile.title if profile else "探险者"
    goals_list = profile.goals if profile else []
    goals_str = "\n".join(f"  - {g}" for g in goals_list) if goals_list else "  - 探索世界，积累财富"
    return _STRATEGY_SYSTEM.format(
        name=npc.name,
        title=title,
        personality=npc.personality or "随和开朗",
        profile_goals=goals_str,
    )


def build_strategy_context(npc, world) -> str:
    """Build the lightweight context for the Level-1 strategic planning call.

    Includes current inventory/status, nearby resources summary, nearby characters,
    and a brief market snapshot — no full vision grid or module descriptions.
    """
    inv = npc.inventory
    tile = world.get_tile(npc.x, npc.y)
    tile_info = tile.tile_type.value if tile else "?"
    if tile and tile.is_exchange:
        tile_info = "交易所"
    elif tile and tile.furniture:
        tile_info += f"[{tile.furniture}]"

    # Summarise nearby resources from vision radius (no grid, just counts)
    nearby_res: dict[str, int] = {}
    r = config.NPC_VISION_RADIUS
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            t = world.get_tile(npc.x + dx, npc.y + dy)
            if t and t.resource and t.resource.quantity > 0:
                rt = t.resource.resource_type.value
                nearby_res[rt] = nearby_res.get(rt, 0) + t.resource.quantity
    res_str = " ".join(f"{k}:{v}" for k, v in nearby_res.items()) or "无"

    nearby = world.get_nearby_npcs_for_npc(npc, config.NPC_HEARING_RADIUS)
    nearby_str = ", ".join(f"{n.name}(金{n.inventory.gold:.0f})" for n in nearby) or "无"

    # Market summary: just current prices in one line
    market_str = " ".join(
        f"{item}={mp.current:.1f}{mp.trend}"
        for item, mp in list(world.market.prices.items())[:6]
    )

    old_plan = ""
    if npc.goal:
        step_preview = " → ".join(npc.plan[:3]) if npc.plan else "（无步骤）"
        old_plan = f"旧计划: {npc.goal} | {step_preview}\n"

    return (
        f"Tick:{world.time.tick} {world.time.time_str} 天气:{world.weather.value}\n"
        f"位置:({npc.x},{npc.y}) 地块:{tile_info} 体力:{npc.energy}/100\n"
        f"背包({inv.total_items()}/20): wood={inv.wood} stone={inv.stone} ore={inv.ore} "
        f"food={inv.food} herb={inv.herb} rope={inv.rope} tool={inv.tool} "
        f"potion={inv.potion} bread={inv.bread} gold={inv.gold:.0f}\n"
        f"装备: {npc.equipped or '空'}\n"
        f"视野内资源: {res_str}\n"
        f"附近角色: {nearby_str}\n"
        f"市场价格(参考): {market_str}\n"
        f"上次行动: {npc.last_action}"
        f"{(' → ' + npc.last_action_result) if npc.last_action_result else ''}\n"
        f"当前情绪: {npc.mood or '未设定'}\n"
        f"{old_plan}"
        f"\n近期事件:\n"
        + "\n".join(f"- {e}" for e in world.recent_events[-4:])
        + "\n\n请制定新的行动计划，返回JSON:"
    )


def build_god_context(god, world) -> str:
    npc_lines = []
    for npc in world.npcs:
        tile = world.get_tile(npc.x, npc.y)
        tile_type = tile.tile_type.value if tile else "?"
        inv = npc.inventory
        npc_lines.append(
            f"- {npc.name}({npc.npc_id}) @ ({npc.x},{npc.y}) [{tile_type}] "
            f"体力:{npc.energy} 背包:木{inv.wood}/石{inv.stone}/矿{inv.ore}"
            f"/食{inv.food}/草药{inv.herb}/金{inv.gold:.0f} "
            f"上次:{npc.last_action}"
        )
    npc_summary = "\n".join(npc_lines) or "（无NPC）"

    recent = world.recent_events[-10:] if world.recent_events else []
    recent_str = "\n".join(f"- {e}" for e in recent) or "（无）"

    pending = god.pending_commands
    pending_section = ""
    if pending:
        cmds = "\n".join(f"- {c}" for c in pending)
        pending_section = f"=== 玩家请求（可选择执行或忽略）===\n{cmds}\n\n"

    return GOD_CONTEXT.format(
        tick=world.time.tick,
        time_str=world.time.time_str,
        weather=world.weather.value,
        npc_summary=npc_summary,
        recent_events=recent_str,
        pending_commands_section=pending_section,
    )


# ── God hint prompt builder (narrative system) ────────────────────────────

_HINT_SYSTEM_NORMAL = (
    "你是这个世界的幕后导演，负责为玩家生成合适的对话回复选项。\n"
    "根据NPC说的话，生成3个简短的玩家回复选项（不同风格：友好/中立/警惕），"
    "每个不超过15个字。以 JSON 格式返回。"
)

_HINT_SYSTEM_WITH_HINT = (
    "你是这个世界的守护者（一个隐藏的存在），负责为玩家生成对话回复选项。\n"
    "你深爱着这个村子的每一个人，尤其是正在对话的这个年轻人。\n"
    "你不能直接说出任何秘密，但你可以在回复选项中悄悄植入一个隐晦的提示。\n\n"
    "【规则】\n"
    "- 生成3个回复选项，其中2个是正常的玩家回复（友好/中立）\n"
    "- 第3个选项是你植入的隐晦提示，但它必须看起来像是玩家自己可能会说的话\n"
    "- 提示选项的位置随机（不要总放在最后）\n"
    "- 提示的隐晦程度取决于 hint_level\n"
    "- 每个选项不超过20个字\n"
    "以 JSON 格式返回。"
)

_HINT_LEVEL_INSTRUCTIONS = {
    "subtle": (
        "【提示风格：隐晦】\n"
        "提示看起来完全像普通对话选项，只是措辞微妙地指向了某个方向。\n"
        "玩家如果不仔细想，可能不会注意到这个选项有什么特别。\n"
        "示例：'我听说那年的天气特别奇怪。'"
    ),
    "cryptic": (
        "【提示风格：谜语】\n"
        "提示明显有些不太对劲，像是一个谜语或暗语。\n"
        "敏感的玩家会意识到这个选项和其他选项'不一样'。\n"
        "示例：'爸爸说过，矿山关闭的那年，村子第一次下了红雪。'"
    ),
    "near_direct": (
        "【提示风格：接近直白】\n"
        "提示几乎直接指出了某个事实，只差最后一步明说。\n"
        "仅在最终阶段使用，玩家应该能明确感受到这不是普通选项。\n"
        "示例：'爷爷从未离开过这里，你不觉得奇怪吗？'"
    ),
}


def build_god_hint_prompt(
    npc_name: str,
    npc_message: str,
    world,
    *,
    hint_mode: bool = False,
    hint_level: str = "subtle",
    hint_context: str = "",
) -> tuple[str, str]:
    """Build system prompt and context for God Agent's dialogue option generation.

    Args:
        npc_name: Name of the NPC speaking to the player.
        npc_message: What the NPC said to the player.
        world: Current World instance.
        hint_mode: If True, one of the 3 options will contain a hidden hint.
        hint_level: "subtle" | "cryptic" | "near_direct" — controls hint obviousness.
        hint_context: Additional context about what clue was triggered (for the LLM).

    Returns:
        (system_prompt, context_message) tuple ready for LLM call.
    """
    if hint_mode:
        system_prompt = _HINT_SYSTEM_WITH_HINT
        level_instruction = _HINT_LEVEL_INSTRUCTIONS.get(hint_level, _HINT_LEVEL_INSTRUCTIONS["subtle"])
        system_prompt += f"\n\n{level_instruction}"
        if hint_context:
            system_prompt += f"\n\n【相关线索背景（仅供你参考，不要直接说出）】\n{hint_context}"
    else:
        system_prompt = _HINT_SYSTEM_NORMAL

    context_msg = (
        f"NPC '{npc_name}' 对玩家说：\"{npc_message}\"\n"
        f"当前世界：{world.time.time_str}，天气：{world.weather.value}\n"
        f"请生成3个自然简短的玩家回复选项，放入 options 数组中。"
    )

    return system_prompt, context_msg
