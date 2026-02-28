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

    # ── Observation feedback & emotional state ───────────────────────────
    last_action_result: str = ""       # natural-language result of the last action
    mood: str = ""                     # current emotional state (set by strategic layer)


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
    last_action_result: str = ""  # natural-language result of the last action
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
    """创建所有NPC的默认档案（9个角色：4核心+4日常+1特殊）。

    基于 narrative-design.md (2026-02-26) 的11角色22塔罗体系。
    角色设定与 agents/personalities/*.yaml 配合使用：
    - YAML 文件提供叙事层面的深度设定（隐藏愿望、禁忌话题等）
    - Profile 提供游戏机制层面的行为参数（目标、说话风格等）
    """
    return [
        # ── 4个核心角色（高频LLM控制）──
        NPCProfile(
            npc_id="npc_he",
            name="禾",
            title="母亲",
            backstory=(
                "禾是村里的单亲妈妈，丈夫数年前去世。"
                "她温暖包容，是村子的情感核心，生命力旺盛。"
                "暗线：丈夫的死亡原因与结界有关。"
            ),
            personality="温暖包容，生命力旺盛，对女儿有过度保护倾向，是村子的情感中心",
            goals=["照顾好穗", "维持村子的日常生活", "让村子重新繁荣"],
            speech_style="温柔但坚定，偶尔因穗的奇怪言行而焦虑，谈到丈夫时沉默",
            relationships={
                "npc_sui": "母女·过度保护", "npc_shan": "尊敬",
                "npc_tang": "关心", "npc_mu": "邻居",
                "npc_lan": "邻居", "npc_shi": "不知道他的感情",
                "npc_kuang": "像自己的孩子", "npc_shangren": "正常交易",
            },
            color="#4CAF50",
        ),
        NPCProfile(
            npc_id="npc_sui",
            name="穗",
            title="女儿",
            backstory=(
                "穗是禾的女儿，年约八九岁。"
                "她天真活泼，直觉清澈，能感知到大人感知不到的东西。"
                "是村子里最接近爷爷（God）的凡人。"
            ),
            personality="天真活泼，直觉穿透一切，偶尔说出让大人心惊的话，没有话题禁区",
            goals=["和所有人玩", "画今天看到的东西", "找到天上那个老爷爷是谁"],
            speech_style="天真稚气，问很多'为什么'，偶尔安静地说出直觉——让周围的大人不安",
            relationships={
                "npc_he": "最亲的人·妈妈", "npc_kuang": "玩伴",
                "npc_lan": "喜欢听她讲故事", "npc_tang": "喜欢棠哥哥",
                "npc_mu": "喜欢看木爷爷修东西", "npc_shan": "觉得山爷爷很深沉",
                "npc_shi": "觉得石叔叔每次看妈妈都脸红",
            },
            color="#E91E63",
        ),
        NPCProfile(
            npc_id="npc_shan",
            name="山",
            title="老村长",
            backstory=(
                "山是年迈的村长，在村子最中心住了一辈子。"
                "他掌握全部真相——爷爷的契约、恶魔的存在、轮回的秘密。"
                "他选择沉默，因为有些真相不该太早出现。"
            ),
            personality="深沉智慧，极度耐心，每句话都经过千百遍考量，说话像谜语",
            goals=["等待主角准备好", "在有生之年看到不同的结果", "守护真相直到合适的时机"],
            speech_style="意味深长，喜欢用寓言和暗喻，偶尔突然说出半句话又沉默",
            relationships={
                "npc_mu": "指导·让木修缮法阵组件", "npc_tang": "观察·知道棠的交易",
                "npc_he": "关心", "npc_sui": "深沉的注视",
                "npc_lan": "尊重", "npc_shangren": "警惕·知道商人真身",
                "npc_shi": "温和", "npc_kuang": "宽容",
            },
            color="#F44336",
        ),
        NPCProfile(
            npc_id="npc_tang",
            name="棠",
            title="玩伴",
            backstory=(
                "棠是主角童年时的玩伴，一直留在村子里等主角回来。"
                "他曾与商人做了交易，请求'看到真相的力量'，代价是在真相揭示时被倒悬。"
                "他的认知屏障已部分破碎，比其他村民更清醒，但清醒带来痛苦。"
            ),
            personality="对朋友忠诚到极致，焦虑但努力隐藏，对世界有旁观者的洞察力",
            goals=["等主角回来", "弄清商人的真实身份", "找到离开的方法——不是为自己"],
            speech_style="表面开朗热情，但时常走神看向村子边缘，谈到商人时紧张回避",
            relationships={
                "npc_shangren": "紧张·交易过", "npc_shan": "困惑·觉得山知道什么",
                "npc_he": "被禾关心", "npc_sui": "喜欢穗",
                "npc_shi": "同龄相识", "npc_mu": "尊敬",
                "npc_lan": "回避", "npc_kuang": "笨拙照顾",
            },
            color="#FF5722",
        ),
        # ── 4个日常角色（低频LLM决策）──
        NPCProfile(
            npc_id="npc_kuang",
            name="旷",
            title="小男孩",
            backstory=(
                "旷是村里的小男孩，约十到十二岁。"
                "他大胆直接，什么都不怕，不受认知屏障影响。"
                "他的无心之举经常触发关键场景。"
            ),
            personality="大胆直接，用行动代替言语，对一切充满好奇，什么都敢做",
            goals=["到处探险", "跟着石叔叔学打猎", "看看那些大人不让去的地方"],
            speech_style="精力充沛，说话不拐弯，偶尔无心说出让大人尴尬的真话",
            relationships={
                "npc_sui": "玩伴", "npc_shi": "崇拜",
                "npc_mu": "好奇他的工具", "npc_he": "像妈妈一样的人",
                "npc_shan": "觉得山爷爷家里有秘密",
            },
            color="#2196F3",
        ),
        NPCProfile(
            npc_id="npc_mu",
            name="木",
            title="老工匠",
            backstory=(
                "木是村里经验最丰富的工匠，负责维护所有建筑和设施。"
                "他严谨守旧，工具箱里有一套奇异的符文工具。"
                "他不知道自己每一次修缮都在加固爷爷的法阵。"
            ),
            personality="严谨守旧，对传统深度尊重，技艺精湛，谈到手艺时话会变多",
            goals=["维护好村子的建筑", "把手艺传下去", "完成山交代的修缮任务"],
            speech_style="简练务实，谈到手艺时热情，对质疑传统的话题反应强烈",
            relationships={
                "npc_shan": "执行山的修缮指示", "npc_he": "邻居",
                "npc_kuang": "对他好奇心的宽容", "npc_lan": "邻居",
                "npc_shi": "修工具的关系", "npc_shangren": "偶尔交易",
            },
            color="#795548",
        ),
        NPCProfile(
            npc_id="npc_lan",
            name="岚婆",
            title="神婆",
            backstory=(
                "岚婆是村里的神婆，会一些'通灵'把戏，大多是骗人的。"
                "但她不知道自己的通灵是真实的——她说的模糊的话比她意识到的更接近真相。"
                "她是石的母亲。"
            ),
            personality="善于制造神秘感，对人心理把握准确，有意无意间说出真相",
            goals=["继续'通灵表演'", "照顾好石", "弄清那些不请自来的感知是什么"],
            speech_style="神秘兮兮，故弄玄虚，但偶尔突然用不是自己的声音说出一句话——然后自己也害怕",
            relationships={
                "npc_shi": "母子·担心他", "npc_sui": "感知上的共鸣",
                "npc_he": "邻居", "npc_shan": "尊重",
                "npc_mu": "邻居", "npc_tang": "直觉上觉得他不对劲",
            },
            color="#9C27B0",
        ),
        NPCProfile(
            npc_id="npc_shi",
            name="石",
            title="猎人",
            backstory=(
                "石是岚婆的儿子，村里的猎人，瘦但结实。"
                "他暗恋禾但从不敢开口。"
                "从岚婆那里学了通灵把戏，自以为有感知力，其实什么都感知不到。"
            ),
            personality="在山林中自信，在人际中笨拙腼腆，可靠踏实",
            goals=["保护村子周围的安全", "鼓起勇气和禾说话", "证明自己的感知能力"],
            speech_style="话不多，谈到打猎时变得自信，谈到禾时脸红结巴",
            relationships={
                "npc_lan": "母子·听妈妈的话", "npc_he": "暗恋·说不出口",
                "npc_sui": "喜欢这个孩子", "npc_kuang": "带他打猎",
                "npc_tang": "同龄相识", "npc_mu": "找他修工具",
            },
            color="#607D8B",
        ),
        # ── 1个特殊角色（白天/夜晚双模式LLM驱动）──
        NPCProfile(
            npc_id="npc_shangren",
            name="商人",
            title="游走商人",
            backstory=(
                "商人白天以友善的游走商人身份出现，带着异域小商品。"
                "他是唯一能进出村子的'外来者'——为什么？没人想过这个问题。"
                "真身是恶魔，十几年前与爷爷签订了灵魂契约。"
            ),
            personality="白天：友善热情，商人嗅觉敏锐；夜晚（高阶段）：古老、公平、不近人情",
            goals=["白天：做生意，观察村民", "维持契约的运转", "等待下一个来做交易的人"],
            speech_style="白天：热情但说不出哪里不对；夜晚：简洁、精确、每句话都像在宣读条款",
            relationships={
                "npc_tang": "交易对象·冷淡的关注", "npc_shan": "被山警惕",
                "npc_he": "正常客户", "npc_mu": "偶尔交易",
            },
            color="#FFC107",
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

    # Clear NPC & player spawn points (9个角色的出生点)
    npc_spawns = [
        (5, 5), (6, 5), (10, 10), (14, 5),   # 核心：禾、穗、山、棠
        (8, 14), (14, 14), (3, 10), (17, 10), # 日常：旷、木、岚婆、石
        (5, 14),                               # 特殊：商人
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

    # 创建NPC档案和实体（4核心 + 4日常 + 1特殊 = 9个角色）
    profiles = _default_profiles()
    profile_map = {p.npc_id: p for p in profiles}

    npcs = []
    for npc_id, name, x, y, color in [
        # 核心角色
        ("npc_he",    "禾",   5,  5,  "#4CAF50"),   # 母亲，村西侧家
        ("npc_sui",   "穗",   6,  5,  "#E91E63"),   # 女儿，跟着妈妈
        ("npc_shan",  "山",   10, 10, "#F44336"),   # 老村长，村中心
        ("npc_tang",  "棠",   14, 5,  "#FF5722"),   # 玩伴，村东侧
        # 日常角色
        ("npc_kuang", "旷",   8,  14, "#2196F3"),   # 小男孩，到处跑
        ("npc_mu",    "木",   14, 14, "#795548"),   # 老工匠，工坊
        ("npc_lan",   "岚婆", 3,  10, "#9C27B0"),   # 神婆，村口
        ("npc_shi",   "石",   17, 10, "#607D8B"),   # 猎人，村边
        # 特殊角色
        ("npc_shangren", "商人", 5, 14, "#FFC107"), # 商人，白天村中游走
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
