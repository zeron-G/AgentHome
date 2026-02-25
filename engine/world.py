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
    """创建所有NPC的默认档案（8个角色：6主要+2次要）。

    角色设定与 agents/personalities/*.yaml 配合使用：
    - YAML 文件提供叙事层面的深度设定（隐藏愿望、禁忌话题等）
    - Profile 提供游戏机制层面的行为参数（目标、说话风格等）
    """
    return [
        # ── 6个主要角色（完整LLM控制）──
        NPCProfile(
            npc_id="npc_alice",
            name="Alice",
            title="草药师",
            backstory=(
                "Alice 从小在森林边长大，对草木的了解无人能及。"
                "她心地善良，总是乐于助人，是村子里最受欢迎的人。"
                "她的草药知识来自一本旧手册——属于村子里已经消失的一位老人。"
            ),
            personality="好奇心旺盛，热心话多，喜欢研究植物和分享发现，总是充满热情",
            goals=["在森林里采集各种草药", "酿造药水帮助村民", "与所有人建立友好关系"],
            speech_style="热情健谈，喜欢分享发现，常用感叹词，语气轻快",
            relationships={
                "npc_bob": "友好", "npc_carol": "好朋友", "npc_dave": "尊敬",
                "npc_erik": "友好", "npc_lily": "像妹妹", "npc_marco": "友好",
                "npc_chen": "关心",
            },
            color="#4CAF50",
        ),
        NPCProfile(
            npc_id="npc_bob",
            name="Bob",
            title="矿工",
            backstory=(
                "Bob 沉默寡言但值得信赖。他从父亲那里继承了矿工的技艺，"
                "但父亲多年前在西边矿山失踪。他用双手说话多过用嘴巴，"
                "是村子里最好的矿工和建造者。"
            ),
            personality="沉默寡言、可靠踏实，只和熟悉的人多说话，做事从不偷懒",
            goals=["采集石头和矿石", "帮助村子建造和修缮", "制造工具提升效率"],
            speech_style="简短直接，不喜欢废话，偶尔沉默很久才回应",
            relationships={
                "npc_alice": "友好", "npc_carol": "商业", "npc_dave": "复杂",
                "npc_erik": "最好的朋友", "npc_lily": "笨拙的温柔",
                "npc_marco": "冷淡", "npc_chen": "沉默默契",
            },
            color="#2196F3",
        ),
        NPCProfile(
            npc_id="npc_carol",
            name="Carol",
            title="厨师/商人",
            backstory=(
                "Carol 是村子里最精明的商人和最好的厨师。"
                "她看似利益至上，但内心深处非常关心村子的未来。"
                "她收养了Lily，也是村子传统仪式的维护者。"
            ),
            personality="精明实际，以利益驱动但内心善良，厨艺精湛，喜欢议论村事",
            goals=["经营好交易所生意", "照顾好Lily", "让村子繁荣起来"],
            speech_style="精明干练，喜欢讨价还价，偶尔流露母性关怀",
            relationships={
                "npc_alice": "好朋友", "npc_bob": "商业", "npc_dave": "仪式传承",
                "npc_erik": "生意伙伴", "npc_lily": "养母",
                "npc_marco": "商业", "npc_chen": "友好邻居",
            },
            color="#FFC107",
        ),
        NPCProfile(
            npc_id="npc_dave",
            name="Dave",
            title="守夜人",
            backstory=(
                "Dave 是村子里年纪最大的人，也是唯一的守夜人。"
                "他的话经常让人摸不着头脑，但村民们习惯了他的古怪。"
                "他和主人公的爷爷是老朋友，爷爷消失后他变得更加神秘。"
            ),
            personality="讲古神叨，说话意味深长，对年轻人有耐心，夜间守护村子",
            goals=["守护村子的安全", "等待能承受真相的人", "在故事中隐藏线索"],
            speech_style="意味深长的古老语气，喜欢用寓言和暗喻，偶尔说出惊人的话",
            relationships={
                "npc_alice": "温和关注", "npc_bob": "复杂心疼",
                "npc_carol": "仪式指导", "npc_erik": "指导者",
                "npc_lily": "祖孙般亲情", "npc_marco": "意味深长观察",
                "npc_chen": "老友无声对话",
            },
            color="#F44336",
        ),
        NPCProfile(
            npc_id="npc_erik",
            name="Erik",
            title="铁匠",
            backstory=(
                "Erik 是村子里唯一的铁匠，对锻造有近乎偏执的追求。"
                "他从上一任铁匠继承了铁匠铺，包括地下室里一个锁着的旧箱子。"
                "Dave定期请他修缮一些'老物件'，他觉得那些东西有说不清的重量感。"
            ),
            personality="沉稳专注，对手艺极致追求，不善闲聊但欣赏者能打开话匣子",
            goals=["锻造高质量的工具", "追求完美的作品", "帮助村民修缮各种东西"],
            speech_style="简练务实，谈到手艺时会变得热情，偶尔暴躁但不记仇",
            relationships={
                "npc_alice": "友好", "npc_bob": "最好的朋友",
                "npc_carol": "生意伙伴", "npc_dave": "尊敬但不理解",
                "npc_lily": "表面不耐烦暗自享受", "npc_marco": "偶尔交集",
                "npc_chen": "尊敬",
            },
            color="#795548",
        ),
        NPCProfile(
            npc_id="npc_lily",
            name="Lily",
            title="孩子",
            backstory=(
                "Lily 是村子里唯一的孩子，大约八九岁。"
                "她的父母多年前'消失'了，Carol收养了她。"
                "她天真活泼但偶尔说出让大人心惊的话。"
            ),
            personality="天真活泼，好奇心极强，喜欢到处跑和问问题，有时安静得出奇",
            goals=["和所有人玩", "画今天看到的东西", "找到天上那个老爷爷是谁"],
            speech_style="天真稚气，问很多'为什么'，偶尔说出让大人不安的直觉",
            relationships={
                "npc_alice": "像姐姐", "npc_bob": "不怕他",
                "npc_carol": "最亲的人", "npc_dave": "最喜欢听故事",
                "npc_erik": "喜欢看打铁", "npc_marco": "喜欢听故事",
                "npc_chen": "喜欢看编织",
            },
            color="#E91E63",
        ),
        # ── 2个次要角色（低频LLM决策）──
        NPCProfile(
            npc_id="npc_marco",
            name="Marco",
            title="旅行商人",
            backstory=(
                "Marco 自称是路过的旅行商人，在村子里'暂住'了一段时间。"
                "他每天都说'明天就走'但从未真正离开过。"
                "实际上他已经被困了十几年，但不自知。"
            ),
            personality="开朗健谈，喜欢讲外面世界的故事，带着旅行者的豪爽",
            goals=["明天就出发（永远不会发生）", "讲更多外面的故事", "卖些小商品"],
            speech_style="豪爽夸张，喜欢用'外面的世界'开头，偶尔自相矛盾而不自知",
            relationships={
                "npc_alice": "友好", "npc_carol": "商业",
                "npc_dave": "困惑", "npc_lily": "喜欢这个孩子",
            },
            color="#9C27B0",
        ),
        NPCProfile(
            npc_id="npc_chen",
            name="陈婆",
            title="编织者",
            backstory=(
                "陈婆是村子里年纪最大的女性，慈祥但有些迷糊。"
                "她的手从未停过编织，上面有复杂的图案。"
                "她和主人公的爷爷是年轻时的挚友，但关于爷爷的记忆模糊了。"
            ),
            personality="慈祥迷糊，记性不太好，手从未停过编织，偶尔说出意味深长的话",
            goals=["继续编织（停不下来）", "想起那件很重要的事", "照看来往的年轻人"],
            speech_style="慢悠悠的语气，经常说到一半忘了要说什么，偶尔突然清醒地说出一句惊人的话",
            relationships={
                "npc_dave": "老友", "npc_carol": "友好邻居",
                "npc_lily": "互相喜爱", "npc_alice": "感激",
            },
            color="#607D8B",
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

    # Clear NPC & player spawn points (8个角色的出生点)
    npc_spawns = [
        (5, 5), (14, 5), (5, 14), (14, 14),  # 原4角色
        (8, 5), (10, 14), (3, 10), (17, 10),  # 新4角色
    ]
    for sx, sy in npc_spawns:
        if 0 <= sx < width and 0 <= sy < height:
            tiles[sy][sx].tile_type = TileType.GRASS
            tiles[sy][sx].resource = None

    px, py = config.PLAYER_START_X, config.PLAYER_START_Y
    if 0 <= px < width and 0 <= py < height:
        if tiles[py][px].tile_type in (TileType.WATER, TileType.ROCK):
            tiles[py][px].tile_type = TileType.GRASS
        tiles[py][px].resource = None

    # 创建NPC档案和实体（6主要 + 2次要 = 8个角色）
    profiles = _default_profiles()
    profile_map = {p.npc_id: p for p in profiles}

    npcs = []
    for npc_id, name, x, y, color in [
        # 主要角色
        ("npc_alice", "Alice", 5,  5,  "#4CAF50"),
        ("npc_bob",   "Bob",   14, 5,  "#2196F3"),
        ("npc_carol", "Carol", 5,  14, "#FFC107"),
        ("npc_dave",  "Dave",  14, 14, "#F44336"),
        ("npc_erik",  "Erik",  8,  5,  "#795548"),   # 铁匠，在Alice和Bob之间
        ("npc_lily",  "Lily",  10, 14, "#E91E63"),   # 孩子，在Carol附近
        # 次要角色
        ("npc_marco", "Marco", 3,  10, "#9C27B0"),   # 外来者，在村子西侧
        ("npc_chen",  "陈婆",  17, 10, "#607D8B"),   # 爷爷老朋友，在村子东侧
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
