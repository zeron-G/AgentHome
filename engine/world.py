"""Core world data models and world generation."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import config


class TileType(str, Enum):
    GRASS = "grass"
    WATER = "water"
    ROCK = "rock"
    FOREST = "forest"
    TOWN = "town"


class WeatherType(str, Enum):
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"


class ResourceType(str, Enum):
    WOOD = "wood"
    STONE = "stone"
    ORE = "ore"
    FOOD = "food"
    HERB = "herb"    # gatherable from forest tiles


@dataclass
class Resource:
    resource_type: ResourceType
    quantity: int
    max_quantity: int


@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    resource: Optional[Resource] = None
    npc_ids: list = field(default_factory=list)
    is_exchange: bool = False   # marks the exchange building tile
    player_here: bool = False   # player occupies this tile
    furniture: Optional[str] = None  # "bed" | "table" | "chair" | None


@dataclass
class WorldTime:
    tick: int = 0
    hour: float = 6.0
    day: int = 1
    hours_per_tick: float = 0.5   # game hours advanced each world tick

    @property
    def phase(self) -> str:
        h = self.hour
        if 5 <= h < 8:
            return "dawn"
        elif 8 <= h < 18:
            return "day"
        elif 18 <= h < 21:
            return "dusk"
        else:
            return "night"

    @property
    def time_str(self) -> str:
        return f"Day {self.day} {int(self.hour):02d}:{int((self.hour % 1) * 60):02d}"

    def advance(self):
        self.tick += 1
        self.hour += self.hours_per_tick
        if self.hour >= 24.0:
            self.hour -= 24.0
            self.day += 1


@dataclass
class Inventory:
    # Raw resources
    wood: int = 0
    stone: int = 0
    ore: int = 0
    food: int = 0
    herb: int = 0
    # Crafted items
    rope: int = 0
    potion: int = 0
    tool: int = 0
    bread: int = 0
    # Currency
    gold: int = 0

    def get(self, item: str) -> int:
        return getattr(self, item, 0)

    def set(self, item: str, value: int):
        if hasattr(self, item):
            setattr(self, item, max(0, value))

    def total_items(self) -> int:
        """Count of all items that occupy inventory slots (gold excluded)."""
        return self.wood + self.stone + self.ore + self.food + self.herb + \
               self.rope + self.potion + self.tool + self.bread

    def has_space(self, qty: int = 1) -> bool:
        return self.total_items() + qty <= config.INVENTORY_MAX_SLOTS

    def to_dict(self) -> dict:
        return {
            "wood": self.wood, "stone": self.stone, "ore": self.ore,
            "food": self.food, "herb": self.herb,
            "rope": self.rope, "potion": self.potion,
            "tool": self.tool, "bread": self.bread,
            "gold": self.gold,
        }


@dataclass
class AgentMemory:
    # List of {"role": "user"/"model", "text": str}
    conversation_history: list = field(default_factory=list)
    personal_notes: list = field(default_factory=list)
    inbox: list = field(default_factory=list)   # events received since last cycle
    max_history_turns: int = config.HISTORY_MAX_TURNS
    max_notes: int = config.NOTES_MAX_COUNT

    def add_history_turn(self, role: str, text: str):
        self.conversation_history.append({"role": role, "text": text})
        max_items = self.max_history_turns * 2
        if len(self.conversation_history) > max_items:
            self.conversation_history = self.conversation_history[-max_items:]

    def add_note(self, note: str):
        self.personal_notes.append(note)
        if len(self.personal_notes) > self.max_notes:
            self.personal_notes.pop(0)

    def clear_inbox(self):
        self.inbox.clear()

    def add_to_inbox(self, event_summary: str):
        self.inbox.append(event_summary)


# ── NPC Profile (background card) ─────────────────────────────────────────────

@dataclass
class NPCProfile:
    """Rich NPC background card — import/exportable as JSON."""
    npc_id: str
    name: str
    title: str = ""           # "采矿者" / "商人" / "草药师"
    backstory: str = ""       # Background story (2-3 sentences)
    personality: str = ""     # One-line personality summary
    goals: list = field(default_factory=list)          # Current objectives (up to 3)
    speech_style: str = ""    # Speaking style description
    relationships: dict = field(default_factory=dict)  # {npc_id: "友好/竞争/中立"}
    color: str = "#888888"

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "title": self.title,
            "backstory": self.backstory,
            "personality": self.personality,
            "goals": list(self.goals),
            "speech_style": self.speech_style,
            "relationships": dict(self.relationships),
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NPCProfile":
        allowed = {
            "npc_id", "name", "title", "backstory", "personality",
            "goals", "speech_style", "relationships", "color",
        }
        return cls(**{k: v for k, v in d.items() if k in allowed})

    def apply_to_npc(self, npc: "NPC"):
        """Hot-apply profile changes to a live NPC."""
        npc.name = self.name
        npc.personality = self.personality
        if self.color:
            npc.color = self.color
        npc.profile = self


# ── Market System ──────────────────────────────────────────────────────────────

@dataclass
class MarketPrice:
    item: str
    base: float       # base price (gold per unit)
    current: float    # live fluctuating price
    min_p: float      # floor price
    max_p: float      # ceiling price

    @property
    def trend(self) -> str:
        if self.current > self.base * 1.1:
            return "↑"
        elif self.current < self.base * 0.9:
            return "↓"
        return "→"

    @property
    def change_pct(self) -> float:
        return round((self.current - self.base) / self.base * 100, 1)


@dataclass
class MarketState:
    prices: dict = field(default_factory=dict)   # item -> MarketPrice
    history: dict = field(default_factory=dict)  # item -> list[float]
    last_update_tick: int = 0


def _make_market() -> MarketState:
    """Initialize market with base prices from config."""
    state = MarketState()
    for item, base in config.MARKET_BASE_PRICES.items():
        min_p = round(base * config.MARKET_PRICE_MIN_RATIO, 2)
        max_p = round(base * config.MARKET_PRICE_MAX_RATIO, 2)
        state.prices[item] = MarketPrice(
            item=item, base=base, current=base, min_p=min_p, max_p=max_p,
        )
        state.history[item] = [base]
    return state


@dataclass
class NPC:
    npc_id: str
    name: str
    x: int
    y: int
    personality: str
    color: str
    inventory: Inventory = field(default_factory=Inventory)
    memory: AgentMemory = field(default_factory=AgentMemory)
    is_processing: bool = False
    last_action: str = "idle"
    last_message: str = ""
    last_message_tick: int = -99
    energy: int = 100
    last_thought: str = ""
    profile: Optional[NPCProfile] = None
    pending_proposals: list = field(default_factory=list)  # incoming trade proposals
    equipped: Optional[str] = None  # "tool" | "rope" | None (single equipment slot)

    # ── Hierarchical decision-making (Level-1 Strategic layer) ─────────────
    goal: str = ""                     # current long-term goal text
    plan: list = field(default_factory=list)  # ordered list of plan-step strings
    strategy_tick: int = -999          # world tick when strategy was last generated


@dataclass
class Player:
    """Human player character."""
    player_id: str = "player"
    name: str = field(default_factory=lambda: config.PLAYER_NAME)
    x: int = field(default_factory=lambda: config.PLAYER_START_X)
    y: int = field(default_factory=lambda: config.PLAYER_START_Y)
    inventory: Inventory = field(default_factory=Inventory)
    energy: int = 100
    is_god_mode: bool = False
    last_action: str = "idle"
    last_message: str = ""
    inbox: list = field(default_factory=list)
    equipped: Optional[str] = None  # "tool" | "rope" | None
    dialogue_queue: list = field(default_factory=list)  # pending NPC→player dialogues


@dataclass
class GodEntity:
    personality: str = "神秘而公正的神明，默默观察世界，偶尔干预以维持平衡，文字富有诗意"
    memory: AgentMemory = field(default_factory=AgentMemory)
    is_processing: bool = False
    last_commentary: str = "世界在我的注视下缓缓运转..."
    pending_commands: list = field(default_factory=list)


@dataclass
class World:
    width: int = config.WORLD_WIDTH
    height: int = config.WORLD_HEIGHT
    tiles: list = field(default_factory=list)
    weather: WeatherType = WeatherType.SUNNY
    time: WorldTime = field(default_factory=WorldTime)
    npcs: list = field(default_factory=list)
    god: GodEntity = field(default_factory=GodEntity)
    player: Optional[Player] = None
    recent_events: list = field(default_factory=list)
    market: MarketState = field(default_factory=_make_market)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return next((n for n in self.npcs if n.npc_id == npc_id), None)

    def get_nearby_npcs(self, x: int, y: int, radius: int) -> list:
        return [n for n in self.npcs if abs(n.x - x) + abs(n.y - y) <= radius]

    def get_nearby_npcs_for_npc(self, npc: NPC, radius: int) -> list:
        return [
            n for n in self.npcs
            if n.npc_id != npc.npc_id
            and abs(n.x - npc.x) + abs(n.y - npc.y) <= radius
        ]

    def add_event(self, summary: str):
        self.recent_events.append(summary)
        if len(self.recent_events) > 30:
            self.recent_events.pop(0)


# ── Default NPC Profiles ──────────────────────────────────────────────────────

def _default_profiles() -> list[NPCProfile]:
    return [
        NPCProfile(
            npc_id="npc_alice",
            name="Alice",
            title="草药探险家",
            backstory=(
                "Alice 从小在森林边长大，对草木的了解无人能及。"
                "她离开家乡来到这片土地，希望找到传说中的珍稀草药，"
                "顺带发现世界的奥秘。"
            ),
            personality="好奇心旺盛，喜欢探索和收集草药，话多且友善，总是充满热情",
            goals=["探索地图每一个角落", "收集足够的草药酿造药水", "与所有人建立友好关系"],
            speech_style="热情健谈，喜欢分享发现，常用感叹词，语气轻快",
            relationships={"npc_bob": "友好", "npc_carol": "友好", "npc_dave": "中立"},
            color="#4CAF50",
        ),
        NPCProfile(
            npc_id="npc_bob",
            name="Bob",
            title="精明商人",
            backstory=(
                "Bob 曾是城市里的富商，在一场风波后来到这片土地重新开始。"
                "他深谙贸易之道，善于发现供需缺口。"
                "他的目标是在这个小世界里重建自己的商业帝国。"
            ),
            personality="沉稳精明，擅长交易和谈判，说话简洁但每句都有目的",
            goals=["积累足够的金币成为首富", "掌握市场价格规律", "制造工具降低生产成本"],
            speech_style="简洁直接，喜欢报价和讨价还价，常用数字和比率",
            relationships={"npc_alice": "友好", "npc_carol": "竞争", "npc_dave": "友好"},
            color="#2196F3",
        ),
        NPCProfile(
            npc_id="npc_carol",
            name="Carol",
            title="市场分析师",
            backstory=(
                "Carol 是一位来自学术界的经济学研究者，专门研究自发秩序的形成。"
                "她亲身参与这个小世界，观察并影响经济规律的演变。"
                "她有时会忍不住通过囤积资源来验证自己的价格理论。"
            ),
            personality="聪明机智，善于观察和分析，偶尔神秘，喜欢评论他人行为",
            goals=["观察并记录市场价格变化规律", "通过囤积稀缺资源影响市场", "收集足够信息撰写研究笔记"],
            speech_style="分析性语气，常说'有趣'和'我注意到'，偶尔引用数据",
            relationships={"npc_alice": "友好", "npc_bob": "竞争", "npc_dave": "中立"},
            color="#FFC107",
        ),
        NPCProfile(
            npc_id="npc_dave",
            name="Dave",
            title="勤劳工匠",
            backstory=(
                "Dave 是一个实干家，从小就跟随父亲在矿山工作，"
                "学会了高效采集和加工原材料的技艺。"
                "他相信通过双手劳动能创造一切，最看不起投机取巧的人。"
            ),
            personality="勤劳踏实，专注采集和制造，效率极高，对偷懒者没有耐心",
            goals=["制造足够多的工具提升效率", "开发完整生产链（采矿→冶炼→工具）", "攒够金币在交易所大量囤货"],
            speech_style="朴实直接，喜欢谈论效率和产量，不喜欢闲聊废话",
            relationships={"npc_alice": "中立", "npc_bob": "友好", "npc_carol": "中立"},
            color="#F44336",
        ),
    ]


# ── World generation ──────────────────────────────────────────────────────────

def _place_cluster(tiles, width, height, tile_type: TileType, cx: int, cy: int, radius: int):
    """Place a cluster of the given tile type around (cx, cy)."""
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if tiles[ny][nx].tile_type == TileType.GRASS:
                        tiles[ny][nx].tile_type = tile_type


def create_world(seed: int = 42) -> World:
    rng = random.Random(seed)
    width, height = config.WORLD_WIDTH, config.WORLD_HEIGHT

    # Initialize all grass
    tiles: list[list[Tile]] = [
        [Tile(x=x, y=y, tile_type=TileType.GRASS) for x in range(width)]
        for y in range(height)
    ]

    # Rock clusters (4 patches near corners)
    for rcx, rcy in [(3, 3), (16, 3), (3, 16), (16, 16)]:
        _place_cluster(tiles, width, height, TileType.ROCK, rcx, rcy, rng.randint(2, 3))

    # Forest patches (avoid town area 8-12)
    forests_placed = 0
    forest_attempts = 0
    while forests_placed < 8 and forest_attempts < 50:
        forest_attempts += 1
        fcx = rng.randint(1, width - 2)
        fcy = rng.randint(1, height - 2)
        if 7 <= fcx <= 13 and 7 <= fcy <= 13:
            continue
        _place_cluster(tiles, width, height, TileType.FOREST, fcx, fcy, rng.randint(1, 3))
        forests_placed += 1

    # Town area: 3×3 at (9,9)–(11,11)
    for ty in range(9, 12):
        for tx in range(9, 12):
            tiles[ty][tx].tile_type = TileType.TOWN
            tiles[ty][tx].resource = None

    tiles[config.EXCHANGE_Y][config.EXCHANGE_X].is_exchange = True

    # Resources on tiles
    for row in tiles:
        for tile in row:
            if tile.tile_type == TileType.FOREST:
                r = rng.random()
                if r < 0.65:
                    qty = rng.randint(4, 10)
                    tile.resource = Resource(ResourceType.WOOD, qty, 10)
                elif r < 0.85:
                    qty = rng.randint(2, 5)
                    tile.resource = Resource(ResourceType.HERB, qty, 5)
            elif tile.tile_type == TileType.ROCK:
                if rng.random() < 0.65:
                    if rng.random() < 0.3:
                        qty = rng.randint(1, 5)
                        tile.resource = Resource(ResourceType.ORE, qty, 5)
                    else:
                        qty = rng.randint(4, 10)
                        tile.resource = Resource(ResourceType.STONE, qty, 10)

    # Food bushes on grass (~10 spots)
    food_placed, food_attempts = 0, 0
    while food_placed < 10 and food_attempts < 200:
        food_attempts += 1
        fx = rng.randint(0, width - 1)
        fy = rng.randint(0, height - 1)
        t = tiles[fy][fx]
        if t.tile_type == TileType.GRASS and t.resource is None:
            t.resource = Resource(ResourceType.FOOD, rng.randint(2, 5), 5)
            food_placed += 1

    # Clear NPC & player spawn points
    for sx, sy in [(5, 5), (14, 5), (5, 14), (14, 14)]:
        tiles[sy][sx].tile_type = TileType.GRASS
        tiles[sy][sx].resource = None

    px, py = config.PLAYER_START_X, config.PLAYER_START_Y
    if 0 <= px < width and 0 <= py < height:
        if tiles[py][px].tile_type in (TileType.WATER, TileType.ROCK):
            tiles[py][px].tile_type = TileType.GRASS
        tiles[py][px].resource = None

    # Create NPC profiles and NPCs
    profiles = _default_profiles()
    profile_map = {p.npc_id: p for p in profiles}

    npcs = []
    for npc_id, name, x, y, color in [
        ("npc_alice", "Alice", 5,  5,  "#4CAF50"),
        ("npc_bob",   "Bob",   14, 5,  "#2196F3"),
        ("npc_carol", "Carol", 5,  14, "#FFC107"),
        ("npc_dave",  "Dave",  14, 14, "#F44336"),
    ]:
        prof = profile_map.get(npc_id)
        npc = NPC(
            npc_id=npc_id, name=name, x=x, y=y,
            personality=prof.personality if prof else "",
            color=color, profile=prof,
        )
        npcs.append(npc)

    for npc in npcs:
        tiles[npc.y][npc.x].npc_ids.append(npc.npc_id)

    player = None
    if config.PLAYER_ENABLED:
        player = Player()
        if 0 <= player.x < width and 0 <= player.y < height:
            tiles[player.y][player.x].player_here = True

    return World(
        width=width, height=height, tiles=tiles,
        npcs=npcs, god=GodEntity(), player=player,
        market=_make_market(),
    )
