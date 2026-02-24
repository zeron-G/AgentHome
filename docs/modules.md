# 📦 模块详解

[← 返回主页](../README.md)

---

## 目录

- [engine/world.py](#engineworldpy)
- [engine/world_manager.py](#engineworld_managerpy)
- [agents/base_agent.py](#agentsbase_agentpy)
- [agents/npc_agent.py](#agentsnpc_agentpy)
- [agents/god_agent.py](#agentsgod_agentpy)
- [agents/prompts.py](#agentspromptspy)
- [game/loop.py](#gamelooppy)
- [game/events.py](#gameeventspy)
- [game/token_tracker.py](#gametoken_trackerpy)
- [ws/manager.py](#wsmanagerpy)
- [ws/serializer.py](#wsserializerpy)
- [main.py](#mainpy)

---

## engine/world.py

世界的所有**数据结构定义**和**世界生成函数**。

### 枚举类型

```python
class TileType(str, Enum):
    GRASS  = "grass"
    ROCK   = "rock"
    FOREST = "forest"
    TOWN   = "town"

class WeatherType(str, Enum):
    SUNNY = "sunny"
    RAINY = "rainy"
    STORM = "storm"

class ResourceType(str, Enum):
    WOOD  = "wood"
    STONE = "stone"
    ORE   = "ore"
    FOOD  = "food"
    HERB  = "herb"   # 草药，仅在森林地块生长
```

### Tile（地块）

```python
@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    resource:    Optional[Resource] = None   # 当前格的资源（可选）
    npc_ids:     list[str]          = field(default_factory=list)
    player_here: bool               = False  # 玩家是否在此格
    is_exchange: bool               = False  # 是否是交易所地块
```

### Resource（资源）

```python
@dataclass
class Resource:
    resource_type: ResourceType
    quantity:      int
    max_quantity:  int
```

### Inventory（库存）

```python
@dataclass
class Inventory:
    wood:   int = 0
    stone:  int = 0
    ore:    int = 0
    food:   int = 0
    gold:   int = 0
    herb:   int = 0    # 草药（采集于森林）
    rope:   int = 0    # 绳子（制造品，持续效果：移动消耗 -1）
    potion: int = 0    # 药水（制造品，使用后 +60 体力）
    tool:   int = 0    # 工具（制造品，持续效果：采集产量 ×2）
    bread:  int = 0    # 面包（制造品，使用后 +50 体力）

    def get(self, item: str) -> int:
        """按名称获取物品数量，不存在的字段返回 0"""

    def set(self, item: str, value: int):
        """按名称设置物品数量，自动 max(0, value)"""

    def to_dict(self) -> dict:
        """返回完整库存字典"""
```

支持的 item 名称：`wood`、`stone`、`ore`、`food`、`gold`、`herb`、`rope`、`potion`、`tool`、`bread`

### NPCProfile（NPC 档案）

```python
@dataclass
class NPCProfile:
    npc_id:        str
    name:          str
    title:         str = ""        # 职业/称号，如"铁匠"、"旅行商人"
    backstory:     str = ""        # 背景故事（2-3句）
    personality:   str = ""        # 性格描述（一句话）
    goals:         list = field(default_factory=list)   # 当前目标（最多3条）
    speech_style:  str = ""        # 说话风格，如"简洁直接"、"喜欢用谚语"
    relationships: dict = field(default_factory=dict)   # {npc_id: "友好/竞争/中立"}
    color:         str = "#888888" # 渲染颜色

    def to_dict(self) -> dict:
        """序列化为 JSON 可导出的字典"""

    @classmethod
    def from_dict(cls, d: dict) -> "NPCProfile":
        """从字典反序列化（用于 JSON 导入）"""

    def apply_to_npc(self, npc: "NPC"):
        """将档案数据热应用到 NPC 实例（不重启生效）"""
```

### MarketPrice（市场价格）

```python
@dataclass
class MarketPrice:
    item:      str
    base:      float      # 基础价格（来自 config.MARKET_BASE_PRICES）
    current:   float      # 当前浮动价格
    min_p:     float      # 价格下限 = base × MARKET_PRICE_MIN_RATIO
    max_p:     float      # 价格上限 = base × MARKET_PRICE_MAX_RATIO
    trend:     str = ""   # "up" / "down" / "stable"
    change_pct: float = 0.0  # 相对基础价的变化百分比
```

### MarketState（市场状态）

```python
@dataclass
class MarketState:
    prices:           dict[str, MarketPrice]   # item_name → MarketPrice
    history:          dict[str, deque]         # item_name → 最近30个价格点
    last_update_tick: int = 0
```

### AgentMemory（NPC 记忆）

```python
@dataclass
class AgentMemory:
    conversation_history: list[dict]  # LLM 对话历史
    inbox:                list[str]   # 待处理的事件摘要，下次决策时读取后清空
    personal_notes:       str         # 通过 think 动作写入的持久笔记

    def add_history_turn(self, role: str, text: str): ...
    def clear_inbox(self): ...
```

### NPC

```python
@dataclass
class NPC:
    npc_id:            str
    name:              str
    x:                 int
    y:                 int
    color:             str            # 十六进制颜色，如 "#4CAF50"
    personality:       str            # 个性描述（用于 system prompt）
    inventory:         Inventory
    memory:            AgentMemory
    energy:            int = 100
    last_action:       str = ""
    last_message:      str = ""
    last_message_tick: int = 0
    last_thought:      str = ""       # 最近一次内心想法（SHOW_NPC_THOUGHTS 时展示）
    is_processing:     bool = False   # LLM 正在处理中标志
    active_tool:       bool = False   # 是否正持有工具（采集 ×2 效果激活）
    active_rope:       bool = False   # 是否正使用绳子（移动耗能 -1 效果激活）
    pending_proposals: list[dict] = field(default_factory=list)  # 收到的待处理交易提案
    profile:           Optional[NPCProfile] = None  # 可选的丰富档案
```

### GodEntity（上帝）

```python
@dataclass
class GodEntity:
    last_commentary:  str        # 最近一次旁白
    pending_commands: list[dict] # 浏览器 UI 直接指令队列
    memory:           AgentMemory
    personality:      str        # 上帝性格（注入 God system prompt）
    is_processing:    bool = False
```

### PlayerEntity（玩家）

```python
@dataclass
class PlayerEntity:
    player_id:    str
    name:         str
    x:            int
    y:            int
    energy:       int = 100
    is_god_mode:  bool = False    # 上帝模式（可直接修改世界）
    inventory:    Inventory = field(default_factory=Inventory)
    last_action:  str = ""
    last_message: str = ""
    inbox:        list[str] = field(default_factory=list)   # 收到的消息
```

### WorldTime

```python
@dataclass
class WorldTime:
    tick:  int = 0
    hour:  float = 8.0    # 当前小时（0–24）
    day:   int = 1

    def advance(self):
        """推进一小时，满24小时则天数+1"""

    @property
    def phase(self) -> str:
        """返回时间段: morning/day/evening/night"""

    @property
    def time_str(self) -> str:
        """格式化字符串，如 "Day 3 14:00" """
```

### World（世界）

```python
@dataclass
class World:
    tiles:         list[list[Tile]]  # tiles[y][x]
    npcs:          list[NPC]
    god:           GodEntity
    time:          WorldTime
    weather:       WeatherType
    market:        MarketState
    recent_events: list[WorldEvent]  # 最多 30 条全局事件日志
    player:        Optional[PlayerEntity] = None
    size:          int = 20

    def get_tile(self, x, y) -> Optional[Tile]: ...
    def get_npc(self, npc_id) -> Optional[NPC]: ...
    def get_nearby_npcs_for_npc(self, npc, radius) -> list[NPC]: ...
```

### create_world(seed=42)

固定种子的世界生成函数，详见 [世界系统 → 世界生成算法](world.md#世界生成算法)。

---

## engine/world_manager.py

所有**世界状态变更**逻辑。保持纯函数风格（不持有状态，所有方法接收 `world` 参数）。

### WorldManager

```python
class WorldManager:
    def __init__(self, event_bus: EventBus): ...
```

### 主要方法

#### `apply_passive(world) → None`

每 World Tick 调用，处理被动效果（体力消耗、自动进食、资源再生、过期提案清理）。

```
- 清除超过 10 tick 的过期 pending_proposals
- 体力消耗（晴天白天 -3，雨天/暴风 -4，夜晚 -2）
- 食物采集点自动吃一个（能量 < 30 且有食物时）
- 资源再生（wood/stone/ore: 10tick, food: 15tick, herb: 12tick）
```

#### `update_market(world) → Optional[WorldEvent]`

每 `MARKET_UPDATE_INTERVAL` ticks 调用，更新所有物品的市场价格。

```
供给量  = 地图上资源数量 + 所有 NPC 库存中的该物品数量
需求代理 = 各 NPC 低于阈值时的需求度（平均体力的倒数）
天气修正 = storm: food×1.4 herb×0.7 | rainy: herb×1.2
目标价  = base × (demand / (supply / 10)) × weather_mod × noise(±volatility)
当前价  = 当前价 × (1 - smoothing) + 目标价 × smoothing
            clamp(min_p, max_p)
```

返回 `MARKET_UPDATED` 事件（若价格有变化）。

#### `apply_npc_action(npc, action: dict, world, tick) → list[WorldEvent]`

根据 `action["action"]` 路由到对应处理方法：

| action 值 | 处理方法 | 返回事件 |
|-----------|---------|---------|
| `move` | `_do_move` | `npc_moved` |
| `gather` | `_do_gather` | `npc_gathered` 或 `resource_depleted` |
| `talk` | `_do_talk` | `npc_spoke` |
| `interrupt` | `_do_talk`（interrupt=True） | `npc_spoke` |
| `trade` | `_do_trade` | `npc_traded` |
| `rest` | 内联处理 | `npc_rested` |
| `sleep` | `_do_sleep` | `npc_slept` |
| `eat` | `_do_eat` | `npc_ate` |
| `think` | 内联处理 | `npc_thought` |
| `exchange` | `_do_exchange` | `npc_exchanged` |
| `buy_food` | `_do_buy_food` | `npc_bought_food` |
| `craft` | `_do_craft` | `npc_crafted` |
| `sell` | `_do_sell` | `npc_sold` |
| `buy` | `_do_buy` | `npc_bought` |
| `use_item` | `_do_use_item` | `npc_used_item` |
| `propose_trade` | `_do_propose_trade` | `trade_proposed` |
| `accept_trade` | `_do_accept_trade` | `trade_accepted` |
| `reject_trade` | `_do_reject_trade` | `trade_rejected` |
| `counter_trade` | `_do_counter_trade` | `trade_countered` |

#### `apply_god_action(action: dict, world) → list[WorldEvent]`

处理 God LLM 的动作（`set_weather` / `spawn_resource`）。

#### `apply_direct_god_command(cmd: dict, world) → list[WorldEvent]`

处理浏览器 UI 直接发送的上帝指令（不经过 LLM）。

### 各动作详细逻辑

#### `_do_move(npc, action, world, tick)`

```
目标格 = (npc.x + dx, npc.y + dy)
if 目标格越界 or 目标格是 ROCK: return []

移动消耗 = random(2, 3) - (1 if npc.active_rope else 0)
体力 -= 移动消耗
更新 npc.x, npc.y, tile.npc_ids
return [npc_moved event]
```

#### `_do_gather(npc, action, world, tick)`

```
当前格 = tiles[npc.y][npc.x]
if 没有资源 or resource.quantity == 0: return []

产量 = 2 if npc.active_tool else 1
npc.inventory[resource_type] += 产量
resource.quantity -= 产量（不低于0）
体力 -= 5

if resource.quantity == 0:
    return [npc_gathered event, resource_depleted event]
return [npc_gathered event]
```

#### `_do_craft(npc, action, world, tick)`

```
item = action["craft_item"]       # rope/potion/tool/bread
recipe = CRAFTING_RECIPES[item]
for mat, qty in recipe.items():
    if npc.inventory.get(mat) < qty: return []   # 材料不足

# 消耗材料
for mat, qty in recipe.items():
    npc.inventory.set(mat, npc.inventory.get(mat) - qty)
npc.inventory.set(item, npc.inventory.get(item) + 1)
return [npc_crafted event]
```

#### `_do_sell(npc, action, world, tick)`

```
item = action["sell_item"]
qty  = action.get("sell_qty", 1)
if npc.inventory.get(item) < qty: return []

price = world.market.prices[item].current
gold_earned = round(price * qty)
npc.inventory.set(item, npc.inventory.get(item) - qty)
npc.inventory.gold += gold_earned
return [npc_sold event]
```

#### `_do_buy(npc, action, world, tick)`

```
item = action["buy_item"]
qty  = action.get("buy_qty", 1)
price = world.market.prices[item].current
cost = round(price * qty)
if npc.inventory.gold < cost: return []

npc.inventory.gold -= cost
npc.inventory.set(item, npc.inventory.get(item) + qty)
return [npc_bought event]
```

#### `_do_use_item(npc, action, world, tick)`

```
item = action["use_item"]
if npc.inventory.get(item) < 1: return []

effect = ITEM_EFFECTS[item]
if "energy" in effect:
    npc.energy = min(100, npc.energy + effect["energy"])
    npc.inventory.set(item, npc.inventory.get(item) - 1)   # 消耗品
if "gather_bonus" in effect:
    npc.active_tool = True     # 持续状态
if "move_energy_save" in effect:
    npc.active_rope = True     # 持续状态
return [npc_used_item event]
```

#### `_do_propose_trade(npc, action, world, tick)`

```
target = find_npc_by_id(action["target_id"])
if target 不在附近: return []

proposal = {
    "from_id": npc.npc_id,
    "from_name": npc.name,
    "offer_item": action["offer_item"],
    "offer_qty": action["offer_qty"],
    "request_item": action["request_item"],
    "request_qty": action["request_qty"],
    "tick": tick,
    "round": action.get("round", 1),
}
target.pending_proposals.append(proposal)
return [trade_proposed event]
```

目标 NPC 下次决策时，系统提示词的提案模块会提示其必须回应。

#### `_do_accept_trade(npc, action, world, tick)`

```
proposal = _find_proposal(npc, action)   # 匹配 from_id
if 无效提案: return []

# 验证双方库存
sender = find_npc(proposal["from_id"])
if sender.inventory.get(proposal["offer_item"]) < proposal["offer_qty"]: return []
if npc.inventory.get(proposal["request_item"]) < proposal["request_qty"]: return []

# 完成交换
sender.inventory[offer_item] -= offer_qty
sender.inventory[request_item] += request_qty
npc.inventory[request_item] -= request_qty
npc.inventory[offer_item] += offer_qty

npc.pending_proposals.remove(proposal)
return [trade_accepted event]
```

---

## agents/base_agent.py

所有 agent 的 **LLM 调用基类**，支持 Gemini 和本地 OpenAI 兼容服务器双后端。

### 类结构

```python
class BaseAgent:
    def __init__(self, agent_id: str, token_tracker: TokenTracker):
        self.agent_id      = agent_id
        self.token_tracker = token_tracker
        self._api_key      = config.GEMINI_API_KEY
        self._gemini_client = None   # 懒加载 google.genai.Client
        self._local_client  = None   # 懒加载 openai.AsyncOpenAI
```

### 关键方法

| 方法 | 说明 |
|------|------|
| `_get_gemini_client()` | 懒加载 Gemini client，API Key 变更后重建 |
| `_get_local_client()` | 懒加载 AsyncOpenAI client，URL 变更后重建 |
| `update_api_key(new_key)` | 热更新 Gemini API Key，重置 client |
| `reset_local_client()` | 重置本地 client（URL/模型变更后调用） |
| `call_llm(system_prompt, context_message, history, response_schema)` | 主入口，根据 `LLM_PROVIDER` 分发 |
| `_call_gemini(...)` | Gemini 后端，结构化 JSON 输出 |
| `_call_local(...)` | 本地后端，JSON 模式 + schema 注入 |

### `call_llm` 返回值

- 成功：返回 `response_schema` 对应的 Pydantic 模型实例
- 失败（网络错误、JSON 解析失败等）：返回 `None`

调用方应检查返回值是否为 `None` 并处理 fallback。

---

## agents/npc_agent.py

### NPCAgent

```python
class NPCAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker, rag_storage=None):
        super().__init__("npcs", token_tracker)   # 所有 NPC 共享同一个 agent_id
        self._rag = rag_storage

    def set_rag(self, rag_storage): ...

    def _retrieve_memories(self, npc: NPC, world: World) -> str:
        """从 RAG 检索相关记忆，返回格式化字符串"""

    def _save_action_memory(self, npc: NPC, action: dict, world: World):
        """将重要动作持久化到 RAG"""

    async def process(self, npc: NPC, world: World) -> dict:
        """
        1. 检查 is_processing（防重入）
        2. 从 RAG 召回相关记忆
        3. 构建 system_prompt 和 context_message（模块化）
        4. 调用 call_llm() 获取 NPCAction
        5. 失败时使用 fallback（rest 或随机 move）
        6. 更新 npc.memory，清空 inbox
        7. 保存动作到 RAG
        8. 返回 action dict
        """
```

NPC agent 的 `agent_id` 为 `"npcs"`（所有 NPC 共用），Token 统计合并计算。

---

## agents/god_agent.py

### GodAgent

```python
class GodAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker):
        super().__init__("god", token_tracker)

    async def process(self, god: GodEntity, world: World) -> Optional[dict]:
        """
        1. 构建上帝视角的 context（包含所有 NPC 状态、市场行情、事件）
        2. 调用 call_llm() 获取 GodAction
        3. 清空 pending_commands
        4. 失败时返回 None（跳过本次干预）
        """
```

---

## agents/prompts.py

### Pydantic Schema

#### NPCAction

```python
class NPCAction(BaseModel):
    action:        str              # 必填：动作类型
    dx:            int = 0          # move: 横向位移（-1/0/1）
    dy:            int = 0          # move: 纵向位移（-1/0/1）
    thought:       str = ""         # 内心想法（可选，所有动作均可附加）
    message:       str = ""         # talk/interrupt: 发言内容
    target_id:     str = ""         # talk/interrupt/trade/propose: 目标 NPC ID
    offer_item:    str = ""         # trade/propose_trade: 提供的物品
    offer_qty:     int = 1          # trade/propose_trade: 提供的数量
    request_item:  str = ""         # trade/propose_trade: 请求的物品
    request_qty:   int = 1          # trade/propose_trade: 请求的数量
    note:          str = ""         # think: 写入笔记的内容
    exchange_item: str = ""         # exchange（传统）: 要兑换的资源
    exchange_qty:  int = 1          # exchange: 要兑换的数量
    quantity:      int = 1          # buy_food: 购买数量
    # 新增字段（v3）
    craft_item:    Optional[str] = None    # craft: rope/potion/tool/bread
    sell_item:     Optional[str] = None    # sell（市场价）: 出售物品名
    sell_qty:      Optional[int] = None    # sell: 出售数量
    buy_item:      Optional[str] = None    # buy（市场价）: 购买物品名
    buy_qty:       Optional[int] = None    # buy: 购买数量
    use_item:      Optional[str] = None    # use_item: potion/bread/tool/rope
    proposal_from: Optional[str] = None    # accept/reject/counter_trade: 提案发起方 ID
```

#### GodAction

```python
class GodAction(BaseModel):
    action:        str           # set_weather / spawn_resource
    weather:       str = ""      # set_weather: sunny/rainy/storm
    resource_type: str = ""      # spawn_resource: wood/stone/ore/food/herb
    x:             int = 10      # spawn_resource: 坐标
    y:             int = 10
    quantity:      int = 5       # spawn_resource: 数量
    commentary:    str = ""      # 上帝旁白（显示在 UI 中）
```

### 模块化 System Prompt

`build_npc_system_prompt(npc, world)` 根据 NPC 当前状态动态组合以下模块：

| 模块 | 触发条件 | 内容 |
|------|---------|------|
| `_MODULE_BASE` | 始终 | 档案注入 + 世界规则 + 基础动作（move/gather/rest/eat/sleep/think） |
| `_MODULE_SOCIAL` | 附近有其他 NPC | talk/propose_trade 详细说明，鼓励先谈判后成交 |
| `_MODULE_EXCHANGE` | 站在交易所地块 | sell/buy 当前市场价 + 传统 exchange/buy_food 说明 |
| `_MODULE_CRAFTING` | 库存有可用制造材料 | 可制造的物品、配方、效果说明 |
| `_MODULE_PROPOSALS` | 有 pending_proposals | 列出所有提案，本轮必须响应 accept/reject/counter_trade |
| `_MODULE_NEGOTIATION` | 附近有 NPC | 协商策略与礼仪说明 |

档案注入格式：
```
【档案】
名字: {name} | 称号: {title} | 性格: {personality}
背景: {backstory}
目标: {goals[0]} / {goals[1]} / {goals[2]}
说话风格: {speech_style}
关系: {npc_b}=友好 {npc_c}=竞争
```

### Context 构建函数

#### `build_npc_context(npc: NPC, world: World, rag_memories: str) -> tuple[str, bool]`

根据 NPC 当前状态动态构建 context，返回 `(context_str, is_social)`：

Context 内容（按情况组合）：
```
[当前状态]
tick=142 | Day 3 14:00 | 天气: sunny
位置: (5,5) 地块:forest | 体力: 82/100
库存: 木头=3 石头=0 矿石=1 食物=2 金币=5 草药=2 绳子=0 药水=0 工具=1 面包=0
装备: 工具=持有中 绳子=未装备

[市场行情]（站在交易所时展示）
物品     当前价  基准   趋势  变化
wood      1.8   1.5   ↑    +20.0%
herb      3.5   4.0   ↓    -12.5%
...

[视野范围] (5×5)
地块、资源、NPC 位置

[附近的人]（附近有 NPC 时）
  - Bob (6,5): 体力=65, 库存: 木头=1 石头=5, 提案: 1条

[RAG 记忆]（有历史记忆时）
  - [Tick42] 行动: sell | 卖了3根木头

[消息收件箱]（inbox 非空时）
  - [Tick 140] Bob 说: "Alice，你有多余的石头吗？"

[近期事件]
  - [140] Alice 从(4,5)移动到(5,5)
```

---

## game/loop.py

### GameLoop

```python
class GameLoop:
    def __init__(self):
        self.world         = create_world()
        self.event_bus     = EventBus()
        self.world_manager = WorldManager(self.event_bus)
        self.token_tracker = TokenTracker()
        self.ws_manager    = WSManager()
        self.serializer    = WorldSerializer()
        self.rag           = ...      # RAG storage backend
        self.npc_agent     = NPCAgent(self.token_tracker, self.rag)
        self.god_agent     = GodAgent(self.token_tracker)
        self._world_lock   = asyncio.Lock()
        self._simulation_running = False
```

### 公共方法

| 方法 | 说明 |
|------|------|
| `start()` | 启动所有异步任务，`asyncio.create_task(...)` |
| `stop()` | 停止游戏循环 |
| `handle_god_command(cmd)` | 将浏览器 UI 指令加入 `god.pending_commands` |
| `handle_control(cmd)` | 处理 pause/resume/set_limit/toggle_sim 等控制命令 |
| `handle_player_action(msg)` | 处理玩家角色的动作（WASD 移动、采集、发言等） |
| `update_api_key(new_key)` | 热更新所有 agent 的 Gemini API Key |
| `update_provider(provider, local_url, local_model)` | 热切换 LLM 提供商 |
| `_apply_setting(key, value)` | 热更新单个 config 参数 |

### 市场更新集成

```python
async def _world_tick_loop(self):
    while self._simulation_running:
        async with self._world_lock:
            self.world.time.advance()
            self.world_manager.apply_passive(self.world)
            tick = self.world.time.tick
            if tick % config.MARKET_UPDATE_INTERVAL == 0:
                market_event = self.world_manager.update_market(self.world)
        if market_event:
            self.event_bus.dispatch(market_event, self.world)
        await self._broadcast(...)
        await asyncio.sleep(config.WORLD_TICK_SECONDS)
```

---

## game/events.py

### EventType（事件类型枚举）

```python
class EventType(str, Enum):
    # 基础 NPC 动作
    npc_spoke        = "npc_spoke"
    npc_moved        = "npc_moved"
    npc_gathered     = "npc_gathered"
    npc_traded       = "npc_traded"
    npc_rested       = "npc_rested"
    npc_thought      = "npc_thought"
    npc_ate          = "npc_ate"
    npc_slept        = "npc_slept"
    npc_exchanged    = "npc_exchanged"    # 传统固定汇率卖出
    npc_bought_food  = "npc_bought_food"  # 传统固定汇率买食物
    # 新增：市场经济
    npc_crafted      = "npc_crafted"      # 制造物品
    npc_sold         = "npc_sold"         # 按市场价卖出
    npc_bought       = "npc_bought"       # 按市场价买入
    npc_used_item    = "npc_used_item"    # 使用物品
    # 新增：提案式交易
    trade_proposed   = "trade_proposed"   # 发出交易提案
    trade_accepted   = "trade_accepted"   # 接受提案（成交）
    trade_rejected   = "trade_rejected"   # 拒绝提案
    trade_countered  = "trade_countered"  # 发出反提案
    # 新增：市场
    market_updated   = "market_updated"   # 市场价格更新
    # 环境
    weather_changed  = "weather_changed"
    resource_spawned = "resource_spawned"
    resource_depleted = "resource_depleted"
    time_advanced    = "time_advanced"
    god_commentary   = "god_commentary"
```

### WorldEvent

```python
@dataclass
class WorldEvent:
    event_type: EventType
    tick:       int
    actor:      str              # NPC 名字或 "God"
    summary:    str              # 人类可读的事件描述（显示在事件日志）
    origin_x:   Optional[int]   # 事件发生坐标（用于半径过滤）
    origin_y:   Optional[int]
    radius:     int = 5          # 影响半径（曼哈顿距离）
    metadata:   dict = field(default_factory=dict)  # 额外数据

    def to_dict(self, world: World) -> dict: ...
```

### EventBus

```python
class EventBus:
    def dispatch(self, event: WorldEvent, world: World):
        """
        1. world.recent_events.append(event)（限 30 条）
        2. for npc in world.npcs:
               if event 无坐标 or 曼哈顿距离 <= event.radius:
                   npc.memory.inbox.append(event.summary)
        """
```

---

## game/token_tracker.py

### TokenTracker

```python
class TokenTracker:
    def __init__(self, session_limit=config.DEFAULT_TOKEN_LIMIT):
        self.session_limit  = session_limit
        self._per_agent     = {}            # agent_id → AgentTokenUsage
        self._total         = AgentTokenUsage()
        self._paused        = False
        self._lock          = asyncio.Lock()
```

### 方法

| 方法 | 说明 |
|------|------|
| `record(agent_id, usage_metadata)` | 记录 Gemini 格式 token（从 `usage_metadata` 对象读取） |
| `record_raw(agent_id, prompt_tokens, completion_tokens)` | 记录 OpenAI 格式 token（直接传入整数） |
| `snapshot() → dict` | 返回完整统计（用于 WebSocket 广播） |
| `set_limit(n)` | 设置新限额，若当前用量低于新限额则自动恢复运行 |
| `resume(new_limit=None)` | 恢复运行，可选同时更新限额 |

超过限额时自动设置 `_paused = True`，GameLoop 中各 brain loop 检查此标志并暂停 LLM 调用。

---

## ws/manager.py

### WSManager

```python
class WSManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    async def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        """并发发送给所有连接的客户端，断连的自动清理"""

    async def send_to(self, ws: WebSocket, data: dict):
        """单播（用于连接时发送初始快照）"""
```

---

## ws/serializer.py

### WorldSerializer

将 `World` 对象序列化为紧凑的 JSON 格式，通过 WebSocket 发送给前端。

```python
class WorldSerializer:
    def world_snapshot(
        self,
        world: World,
        token_tracker: TokenTracker,
        events: list[WorldEvent],
        simulation_running: bool,
    ) -> dict:
        return {
            "type":               "world_state",
            "tick":               world.time.tick,
            "simulation_running": simulation_running,
            "time":               { "hour", "day", "phase", "time_str" },
            "weather":            world.weather.value,
            "tiles":              self._serialize_tiles(world),
            "npcs":               [self._serialize_npc(npc) for npc in world.npcs],
            "player":             self._serialize_player(world.player),  # or None
            "god":                {"commentary": world.god.last_commentary},
            "events":             [e.to_dict(world) for e in events],
            "token_usage":        token_tracker.snapshot(),
            "settings":           self._serialize_settings(),
            "market":             self._serialize_market(world),
        }
```

### 编码映射

```python
TILE_LETTER = {
    TileType.GRASS:  "g",
    TileType.ROCK:   "r",
    TileType.FOREST: "f",
    TileType.TOWN:   "o",
}
RESOURCE_LETTER = {
    ResourceType.WOOD:  "w",
    ResourceType.STONE: "s",
    ResourceType.ORE:   "o",
    ResourceType.FOOD:  "f",
    ResourceType.HERB:  "h",
}
```

### NPC 序列化新增字段

```python
{
    "active_tool":        npc.active_tool,       # bool: 工具效果是否激活
    "active_rope":        npc.active_rope,        # bool: 绳子效果是否激活
    "pending_proposals":  len(npc.pending_proposals),  # int: 待响应提案数量
    "thought":            npc.last_thought,       # 仅 SHOW_NPC_THOUGHTS=True 时输出
    "profile": {                                  # 仅有档案时输出
        "title", "backstory", "personality", "goals", "speech_style", "relationships"
    }
}
```

---

## main.py

FastAPI 应用入口，负责：

1. **静态文件服务**：`/static/*` → `frontend/` 目录
2. **首页路由**：`GET /` → `frontend/index.html`
3. **Settings API**：`GET/POST /api/settings`
4. **NPC 档案 API**：`GET/PUT /api/npc_profiles`（含导出/导入）
5. **市场 API**：`GET /api/market`
6. **存档 API**：`GET/POST /api/saves`
7. **WebSocket 端点**：`WS /ws`
8. **生命周期钩子**：`@startup` 启动 GameLoop，`@shutdown` 停止

### WebSocket 消息处理

```python
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await game_loop.ws_manager.connect(ws)
    # 发送初始快照
    await game_loop.ws_manager.send_to(ws, initial_snapshot)

    while True:
        msg = await ws.receive_json()
        if msg["type"] == "god_command":
            game_loop.handle_god_command(msg)
        elif msg["type"] == "god_direct":
            game_loop.handle_god_command(msg)
        elif msg["type"] == "control":
            game_loop.handle_control(msg)
        elif msg["type"] == "player_action":
            await game_loop.handle_player_action(msg)
```
