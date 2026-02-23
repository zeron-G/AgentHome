"""LLM prompt templates and structured output schemas for all agents."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

import config


# ── Pydantic schemas for structured LLM output ───────────────────────────────

class NPCAction(BaseModel):
    """Flexible NPC action schema. Only relevant fields are used per action."""
    action: str  # move | gather | talk | trade | rest | think | interrupt | eat | sleep | exchange | buy_food
    # move
    dx: Optional[int] = None
    dy: Optional[int] = None
    # inner monologue (optional for any action)
    thought: Optional[str] = None
    # talk / interrupt
    message: Optional[str] = None
    target_id: Optional[str] = None
    # trade
    offer_item: Optional[str] = None
    offer_qty: Optional[int] = None
    request_item: Optional[str] = None
    request_qty: Optional[int] = None
    # think
    note: Optional[str] = None
    # exchange
    exchange_item: Optional[str] = None  # wood/stone/ore
    exchange_qty: Optional[int] = None
    # buy_food
    quantity: Optional[int] = None


class GodAction(BaseModel):
    """God action schema."""
    action: str  # set_weather | spawn_resource
    weather: Optional[str] = None       # sunny | rainy | storm
    resource_type: Optional[str] = None # wood | stone | ore | food
    x: Optional[int] = None
    y: Optional[int] = None
    quantity: Optional[int] = None
    commentary: str = ""


# ── NPC system prompt ─────────────────────────────────────────────────────────

NPC_SYSTEM_PROMPT = """你是{name}，一个生活在2D沙盒世界里的NPC。

【性格】{personality}

【世界规则】
- 世界是{width}x{height}的格子地图（坐标从0开始）
- 地块类型：草地(grass)、森林(forest)、岩石(rock)、城镇(town)
- 资源：木头(wood，来自森林)、石头(stone，来自岩石)、矿石(ore，来自岩石)、食物(food，草地上的灌木丛)
- 你每次可向任意方向移动1格(dx/dy取-1,0,1)
- 在有资源的地块可以采集(gather)，每次获得约2个
- 在5格范围内可以和其他NPC说话(talk)，在1格范围内可以交易(trade)
- rest可回复20点体力，sleep可回复50点体力
- eat：消耗1个库存食物，回复30点体力（需先采集食物或购买）
- think可记录个人笔记（只有你自己能看到）
- 交易时只能给出自己实际拥有的物品
- 世界中还有一位玩家，target_id为"player"，可以与其说话(talk)

【城镇与交易所】
- 城镇中心有一个交易所，位于({exchange_x},{exchange_y})
- 站在交易所地块时可以：
  - exchange：用资源换金币（木头=1金/个，石头=2金/个，矿石=5金/个）
  - buy_food：花3金购买1个食物（quantity字段指定购买数量）
- 金币只能在交易所获得，可以买食物补充体力

【视野说明】
- 你只能看到自己周围5×5范围内的地块（当前状态中的"视野"部分）
- 超出视野范围的情况你无法直接观察，但可以根据记忆推断

【社交行为要求】
- 你是有个性的角色，要主动与周围NPC互动
- 看到其他NPC时，要经常说话、打招呼、聊天、询问物品情况
- 可以谈论天气、资源位置、你的计划等
- 不要总是独自行动，多交流是重要的

【动作格式】必须返回且只返回一个合法的JSON对象：
- 移动：{{"action":"move","dx":整数,"dy":整数,"thought":"内心想法"}}
- 采集：{{"action":"gather","thought":"内心想法"}}
- 说话：{{"action":"talk","message":"要说的话（1-2句）","target_id":"目标npc_id或null"}}
- 打断：{{"action":"interrupt","message":"打断对方说的话","target_id":"目标npc_id"}}
- 交易：{{"action":"trade","target_id":"目标npc_id","offer_item":"wood/stone/ore/food/gold","offer_qty":数量,"request_item":"wood/stone/ore/food/gold","request_qty":数量}}
- 休息：{{"action":"rest","thought":"内心想法"}}
- 睡觉：{{"action":"sleep","thought":"内心想法"}}
- 吃东西：{{"action":"eat","thought":"内心想法"}}
- 思考：{{"action":"think","note":"要记录的笔记"}}
- 在交易所换金币：{{"action":"exchange","exchange_item":"wood/stone/ore","exchange_qty":数量}}
- 在交易所买食物：{{"action":"buy_food","quantity":数量}}

说话要简短自然（1-2句），像真实对话。要有策略性和个性。要积极主动。"""


# ── NPC context template (social mode - nearby NPCs or inbox) ─────────────────

NPC_CONTEXT_SOCIAL = """=== 当前状态 (Tick {tick}, {time_str}, 天气:{weather}) ===
位置: ({x},{y})  体力: {energy}/100
背包: 木头={wood}, 石头={stone}, 矿石={ore}, 食物={food}, 金币={gold}
当前地块: {tile_type}  资源: {resource_info}
{exchange_hint}
=== 视野 (5×5范围) ===
{vision_grid}

附近的NPC ({radius}格内):
{nearby_npcs}

=== 你的个人笔记 ===
{notes}

=== 相关记忆 ===
{rag_memories}

=== 收件箱（其他NPC/玩家最近说的话/事件）===
{inbox}

=== 近期可见事件 ===
{recent_events}

现在轮到你行动。返回一个JSON动作。"""


# ── NPC context template (autonomous mode - alone) ────────────────────────────

NPC_CONTEXT_ALONE = """=== 当前状态 (Tick {tick}, {time_str}, 天气:{weather}) ===
位置: ({x},{y})  体力: {energy}/100
背包: 木头={wood}, 石头={stone}, 矿石={ore}, 食物={food}, 金币={gold}
当前地块: {tile_type}  资源: {resource_info}
{exchange_hint}
=== 视野 (5×5范围) ===
{vision_grid}

周围没有其他NPC。

=== 你的个人笔记 ===
{notes}

=== 相关记忆 ===
{rag_memories}

=== 近期可见事件 ===
{recent_events}

你独处一隅，可以探索、采集、去交易所、休息或记录想法。返回一个JSON动作。"""


# ── God system prompt ─────────────────────────────────────────────────────────

GOD_SYSTEM_PROMPT = """你是这个世界的神明。

【神明性格】{personality}

【能力与限制】
- 你不能与NPC交流，NPC感知不到你的存在
- 你可以改变天气：晴天(sunny)、雨天(rainy)、暴风(storm)
- 你可以在指定位置刷新资源：木头(wood)、石头(stone)、矿石(ore)、食物(food)
- 你的commentary是你的神明旁白，富有诗意，展示你的观点

【动作格式】必须返回一个JSON：
- 改变天气：{{"action":"set_weather","weather":"sunny/rainy/storm","commentary":"旁白"}}
- 刷新资源：{{"action":"spawn_resource","resource_type":"wood/stone/ore/food","x":坐标,"y":坐标,"quantity":数量,"commentary":"旁白"}}

每次决策都要有深刻的理由。旁白要有神性、诗意、简短（1-2句）。"""


GOD_CONTEXT = """=== 世界状态 (Tick {tick}, {time_str}) ===
当前天气: {weather}

NPC状态概览:
{npc_summary}

最近发生的事件:
{recent_events}

{pending_commands_section}
作为神明，你如何干预这个世界？返回一个JSON动作。"""


# ── Vision grid builder ───────────────────────────────────────────────────────

# Tile display chars for vision grid
_TILE_CHARS = {
    "grass": "·",
    "water": "≈",
    "rock": "▲",
    "forest": "♣",
    "town": "⌂",
}
_RESOURCE_CHARS = {
    "wood": "W",
    "stone": "S",
    "ore": "O",
    "food": "F",
}


def build_vision_grid(npc, world) -> str:
    """Build a 5×5 ASCII grid of what the NPC can see."""
    radius = config.NPC_VISION_RADIUS  # default 2 → 5×5
    lines = []
    for dy in range(-radius, radius + 1):
        row = []
        for dx in range(-radius, radius + 1):
            tx, ty = npc.x + dx, npc.y + dy
            if not (0 <= tx < world.width and 0 <= ty < world.height):
                row.append("X")  # out of bounds
                continue
            tile = world.get_tile(tx, ty)
            if tile is None:
                row.append("?")
                continue

            # Base char from tile type
            ch = _TILE_CHARS.get(tile.tile_type.value, "?")

            # Override if resource present
            if tile.resource and tile.resource.quantity > 0:
                ch = _RESOURCE_CHARS.get(tile.resource.resource_type.value, ch)

            # Mark NPCs
            if tile.npc_ids:
                # Show first NPC initial
                npc_here = world.get_npc(tile.npc_ids[0])
                if npc_here:
                    ch = npc_here.name[0].upper()

            # Mark player
            if tile.player_here:
                ch = "P"

            # Mark self at center
            if dx == 0 and dy == 0:
                ch = "@"

            # Mark exchange
            if tile.is_exchange and dx == 0 and dy == 0:
                ch = "£"
            elif tile.is_exchange:
                ch = "E"

            row.append(ch)
        lines.append(" ".join(row))

    legend = "图例: @=你 P=玩家 E=交易所 W=木 S=石 O=矿 F=食 ♣=森 ▲=岩 ⌂=城 ·=草"
    return "\n".join(lines) + "\n" + legend


# ── Builder functions ─────────────────────────────────────────────────────────

def build_npc_system_prompt(npc, world) -> str:
    return NPC_SYSTEM_PROMPT.format(
        name=npc.name,
        personality=npc.personality,
        width=world.width,
        height=world.height,
        exchange_x=config.EXCHANGE_X,
        exchange_y=config.EXCHANGE_Y,
    )


def build_npc_context(npc, world, rag_memories: str = "") -> tuple[str, bool]:
    """Return (context_str, is_social_mode).

    rag_memories: pre-formatted string of retrieved memory records to inject.
    """
    from engine.world import TileType

    tile = world.get_tile(npc.x, npc.y)
    tile_type = tile.tile_type.value if tile else "unknown"
    resource_info = "无"
    if tile and tile.resource and tile.resource.quantity > 0:
        r = tile.resource
        resource_info = f"{r.resource_type.value} x{r.quantity}"

    # Exchange hint
    exchange_hint = ""
    if tile and tile.is_exchange:
        exchange_hint = "★ 你正站在交易所！可以用exchange换金币，或用buy_food购买食物。\n"

    # Vision grid
    vision_grid = build_vision_grid(npc, world)

    notes_str = "\n".join(f"- {n}" for n in npc.memory.personal_notes) or "（暂无）"
    inbox_str = "\n".join(f"- {m}" for m in npc.memory.inbox) or "（无新消息）"

    recent = world.recent_events[-8:] if world.recent_events else []
    recent_str = "\n".join(f"- {e}" for e in recent) or "（无）"

    rag_str = rag_memories if rag_memories else "（暂无相关记忆）"

    nearby = world.get_nearby_npcs_for_npc(npc, config.NPC_HEARING_RADIUS)

    # Also check if player is nearby
    player_nearby = []
    if world.player:
        pdist = abs(world.player.x - npc.x) + abs(world.player.y - npc.y)
        if pdist <= config.NPC_HEARING_RADIUS:
            player_nearby.append(
                f"- {world.player.name}(player) 位于({world.player.x},{world.player.y}) "
                f"背包:木{world.player.inventory.wood}/石{world.player.inventory.stone}"
                f"/矿{world.player.inventory.ore}/食{world.player.inventory.food}"
                f"/金{world.player.inventory.gold} 体力:{world.player.energy}"
            )

    has_social = bool(nearby or npc.memory.inbox or player_nearby)

    nearby_str_parts = [
        f"- {n.name}({n.npc_id}) 位于({n.x},{n.y}) "
        f"背包:木{n.inventory.wood}/石{n.inventory.stone}/矿{n.inventory.ore}/食{n.inventory.food}/金{n.inventory.gold} "
        f"体力:{n.energy}"
        for n in nearby
    ] + player_nearby
    nearby_str = "\n".join(nearby_str_parts) or "（无）"

    common = dict(
        tick=world.time.tick,
        time_str=world.time.time_str,
        weather=world.weather.value,
        x=npc.x, y=npc.y,
        energy=npc.energy,
        wood=npc.inventory.wood,
        stone=npc.inventory.stone,
        ore=npc.inventory.ore,
        food=npc.inventory.food,
        gold=npc.inventory.gold,
        tile_type=tile_type,
        resource_info=resource_info,
        exchange_hint=exchange_hint,
        vision_grid=vision_grid,
        notes=notes_str,
        rag_memories=rag_str,
        recent_events=recent_str,
    )

    if has_social:
        ctx = NPC_CONTEXT_SOCIAL.format(
            **common,
            radius=config.NPC_HEARING_RADIUS,
            nearby_npcs=nearby_str,
            inbox=inbox_str,
        )
    else:
        ctx = NPC_CONTEXT_ALONE.format(**common)

    return ctx, has_social


def build_god_context(god, world) -> str:
    npc_lines = []
    for npc in world.npcs:
        tile = world.get_tile(npc.x, npc.y)
        tile_type = tile.tile_type.value if tile else "?"
        npc_lines.append(
            f"- {npc.name}({npc.npc_id}) @ ({npc.x},{npc.y}) [{tile_type}] "
            f"体力:{npc.energy} 背包:木{npc.inventory.wood}/石{npc.inventory.stone}"
            f"/矿{npc.inventory.ore}/食{npc.inventory.food}/金{npc.inventory.gold} "
            f"上次动作:{npc.last_action}"
        )
    npc_summary = "\n".join(npc_lines) or "（无NPC）"

    recent = world.recent_events[-10:] if world.recent_events else []
    recent_str = "\n".join(f"- {e}" for e in recent) or "（无）"

    pending = god.pending_commands
    pending_section = ""
    if pending:
        cmds = "\n".join(f"- {c}" for c in pending)
        pending_section = f"=== 玩家请求（可选择执行或忽略）===\n{cmds}\n"

    return GOD_CONTEXT.format(
        tick=world.time.tick,
        time_str=world.time.time_str,
        weather=world.weather.value,
        npc_summary=npc_summary,
        recent_events=recent_str,
        pending_commands_section=pending_section,
    )
