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
    wood:  int = 0
    stone: int = 0
    ore:   int = 0
    food:  int = 0
    gold:  int = 0

    def get(self, item: str) -> int:
        """按名称获取资源数量，不存在的字段返回 0"""

    def set(self, item: str, value: int):
        """按名称设置资源数量，自动 max(0, value)"""
```

支持的 item 名称：`wood`、`stone`、`ore`、`food`、`gold`

### AgentMemory（NPC 记忆）

```python
@dataclass
class AgentMemory:
    history:        list[dict]  # LLM 对话历史，格式 [{"role":"user","text":"..."}, ...]
    inbox:          list[str]   # 待处理的事件摘要，下次决策时读取后清空
    personal_notes: str         # 通过 think 动作写入的持久笔记
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
    personality:       str            # 个性描述，注入 LLM system prompt
    inventory:         Inventory
    memory:            AgentMemory
    energy:            int = 100
    last_action:       str = ""
    last_message:      str = ""
    last_message_tick: int = 0
    is_processing:     bool = False   # LLM 正在处理中标志
```

### God（上帝）

```python
@dataclass
class God:
    commentary:       str        # 最近一次旁白
    pending_commands: list[dict] # 浏览器 UI 直接指令队列
    memory:           AgentMemory
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
    tiles:         dict[tuple[int,int], Tile]   # (x,y) → Tile
    npcs:          list[NPC]
    god:           God
    time:          WorldTime
    weather:       WeatherType
    recent_events: list[WorldEvent]   # 最多 30 条全局事件日志
    size:          int = 20
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

每 World Tick 调用，处理被动效果（体力消耗、自动进食、资源再生）。

#### `apply_npc_action(npc, action: dict, world) → list[WorldEvent]`

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

#### `apply_god_action(action: dict, world) → list[WorldEvent]`

处理 God LLM 的动作（`set_weather` / `spawn_resource`）。

#### `apply_direct_god_command(cmd: dict, world) → list[WorldEvent]`

处理浏览器 UI 直接发送的上帝指令（不经过 LLM）。

### 各动作详细逻辑

#### `_do_move(npc, action, world, tick)`

```
目标格 = (npc.x + dx, npc.y + dy)
if 目标格越界: return []
if 目标格是 ROCK: return []
if dx/dy 超出 [-1,0,1] 范围: 截断到合法值

更新 npc.x, npc.y
更新 tile.npc_ids
体力 -= random(2, 3)
return [npc_moved event]
```

#### `_do_gather(npc, action, world, tick)`

```
当前格 = tiles[npc.x, npc.y]
if 没有资源 or resource.quantity == 0:
    return []  # 采集失败，无事件

npc.inventory[resource_type] += 1
resource.quantity -= 1
体力 -= 5

if resource.quantity == 0:
    return [npc_gathered event, resource_depleted event]
return [npc_gathered event]
```

#### `_do_talk(npc, action, world, tick, interrupt=False)`

```
message = action["message"][:200]  # 截断过长消息
npc.last_message = message
npc.last_message_tick = tick

return [npc_spoke event (radius=5, 包含 message)]
```

事件通过 EventBus 分发到附近 NPC 的 inbox，NPC 下次决策时收到。

#### `_do_trade(npc, action, world, tick)`

```
target = find_npc_by_id(action["target_id"])
if target 不存在 or target 不在相邻格: return []

offer_item = action["offer_item"]     # wood/stone/ore/food/gold
offer_qty  = action["offer_qty"]
request_item = action["request_item"]
request_qty  = action["request_qty"]

if npc.inventory[offer_item] < offer_qty: return []   # 发起方没有足够资源
if target.inventory[request_item] < request_qty: return []   # 对方没有足够资源

npc.inventory[offer_item]       -= offer_qty
npc.inventory[request_item]     += request_qty
target.inventory[offer_item]    += offer_qty
target.inventory[request_item]  -= request_qty

return [npc_traded event]
```

#### `_do_eat(npc, action, world, tick)`

```
if npc.inventory.food < 1: return []
npc.inventory.food -= 1
npc.energy = min(100, npc.energy + FOOD_ENERGY_RESTORE)
return [npc_ate event]
```

#### `_do_sleep(npc, action, world, tick)`

```
npc.energy = min(100, npc.energy + SLEEP_ENERGY_RESTORE)
return [npc_slept event]
```

#### `_do_exchange(npc, action, world, tick)`

```
tile = tiles[npc.x, npc.y]
if not tile.is_exchange: return []   # 必须站在交易所

item = action["exchange_item"]   # wood/stone/ore
qty  = action.get("exchange_qty", 1)
if npc.inventory[item] < qty: return []

rate = EXCHANGE_RATE_WOOD / STONE / ORE
gold = qty * rate
npc.inventory[item] -= qty
npc.inventory.gold  += gold
return [npc_exchanged event]
```

#### `_do_buy_food(npc, action, world, tick)`

```
tile = tiles[npc.x, npc.y]
if not tile.is_exchange: return []

qty  = action.get("quantity", 1)
cost = qty * FOOD_COST_GOLD
if npc.inventory.gold < cost: return []

npc.inventory.gold -= cost
npc.inventory.food += qty
return [npc_bought_food event]
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

### 辅助函数

```python
def _strip_code_fences(text: str) -> str:
    """移除 ```json ... ``` 代码围栏（部分本地模型会自动添加）"""
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*\n?([\s\S]*?)\n?```$", text)
    return match.group(1).strip() if match else text
```

---

## agents/npc_agent.py

### NPCAgent

```python
class NPCAgent(BaseAgent):
    def __init__(self, token_tracker: TokenTracker):
        super().__init__("npcs", token_tracker)   # 所有 NPC 共享同一个 agent_id
        self._per_npc_history: dict[str, list] = {}   # 每个 NPC 独立的对话历史

    async def process(self, npc: NPC, world: World) -> dict:
        """
        1. 检查 is_processing（防重入）
        2. 构建 system_prompt 和 context_message
        3. 调用 call_llm() 获取 NPCAction
        4. 失败时使用 fallback（rest 或随机 move）
        5. 更新 npc.memory.history，清空 inbox
        6. 返回 action dict
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

    async def process(self, god: God, world: World) -> Optional[dict]:
        """
        1. 构建上帝视角的 context（包含所有 NPC 状态、事件、天气）
        2. 调用 call_llm() 获取 GodAction
        3. 失败时返回 None（跳过本次干预）
        4. 返回 action dict 或 None
        """
```

---

## agents/prompts.py

### Pydantic Schema

#### NPCAction

```python
class NPCAction(BaseModel):
    action:       str            # 必填：动作类型
    dx:           int = 0        # move: 横向位移（-1/0/1）
    dy:           int = 0        # move: 纵向位移（-1/0/1）
    thought:      str = ""       # move/gather/rest/eat/sleep: 内心想法
    message:      str = ""       # talk/interrupt: 发言内容
    target_id:    str = ""       # talk/interrupt/trade: 目标 NPC ID
    offer_item:   str = ""       # trade: 提供的物品
    offer_qty:    int = 1        # trade: 提供的数量
    request_item: str = ""       # trade: 请求的物品
    request_qty:  int = 1        # trade: 请求的数量
    note:         str = ""       # think: 写入笔记的内容
    exchange_item: str = ""      # exchange: 要兑换的资源
    exchange_qty:  int = 1       # exchange: 要兑换的数量
    quantity:      int = 1       # buy_food: 购买数量
```

#### GodAction

```python
class GodAction(BaseModel):
    action:        str           # set_weather / spawn_resource
    weather:       str = ""      # set_weather: sunny/rainy/storm
    resource_type: str = ""      # spawn_resource: wood/stone/ore/food
    x:             int = 10      # spawn_resource: 坐标
    y:             int = 10
    quantity:      int = 5       # spawn_resource: 数量
    commentary:    str = ""      # 上帝旁白（显示在 UI 中）
```

### 提示词构建函数

#### `build_npc_system_prompt(npc: NPC, world: World) -> str`

生成 NPC 的 system prompt，包含：
- NPC 名字与个性
- 世界规则（地块类型、动作说明、资源说明）
- 交易所位置与汇率
- 完整的动作格式说明（JSON 示例）
- 社交互动鼓励（多说话、多交互）

#### `build_npc_context(npc: NPC, world: World) -> tuple[str, bool]`

根据 NPC 当前状态动态构建 context，返回 `(context_str, is_social)`：

**社交模式**（附近有其他 NPC 或 inbox 非空）：
```
当前状态: x=5, y=5, 体力=82, 库存: 木头=3 石头=0 矿石=1 食物=2 金币=5
附近的人:
  - Bob (14, 5): 体力=65, 库存: 木头=1 石头=5 矿石=0 食物=0 金币=2
消息收件箱:
  - [Tick 140] Bob 说: "Alice，你有多余的石头吗？"
近期事件: ...
```

**独思模式**（附近无人且 inbox 空）：
```
当前状态: x=14, y=14, 体力=90, 库存: ...
个人笔记: "计划前往交易所换金币..."
近期事件: ...
```

**交易所提示**（站在 `is_exchange=True` 地块时附加）：
```
📍 你当前站在交易所！可执行:
- exchange: 卖资源换金币（木=1金, 石=2金, 矿=5金）
- buy_food: 花3金买1个食物
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
        self.npc_agent     = NPCAgent(self.token_tracker)
        self.god_agent     = GodAgent(self.token_tracker)
        self._world_lock   = asyncio.Lock()
        self._running      = False
```

### 公共方法

| 方法 | 说明 |
|------|------|
| `start()` | 启动所有异步任务，`await asyncio.gather(...)` |
| `stop()` | 设置 `_running = False`，各循环在下次检查时退出 |
| `handle_god_command(cmd)` | 将浏览器 UI 指令加入 `god.pending_commands` |
| `handle_control(cmd)` | 处理 pause/resume/set_limit/set_api_key |
| `update_api_key(new_key)` | 热更新所有 agent 的 Gemini API Key |
| `update_provider(provider, local_url, local_model)` | 热切换 LLM 提供商 |

---

## game/events.py

### EventType（事件类型枚举）

```python
class EventType(str, Enum):
    npc_spoke        = "npc_spoke"
    npc_moved        = "npc_moved"
    npc_gathered     = "npc_gathered"
    npc_traded       = "npc_traded"
    npc_rested       = "npc_rested"
    npc_thought      = "npc_thought"
    npc_ate          = "npc_ate"
    npc_slept        = "npc_slept"
    npc_exchanged    = "npc_exchanged"
    npc_bought_food  = "npc_bought_food"
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
    summary:    str              # 人类可读的事件描述（显示在聊天日志）
    origin_x:   Optional[int]   # 事件发生坐标（用于半径过滤）
    origin_y:   Optional[int]
    radius:     int = 5          # 影响半径（曼哈顿距离）
    metadata:   dict             # 额外数据（message/item/qty 等）
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
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.active -= dead

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
    ) -> dict:
        return {
            "type":        "world_state",
            "tick":        world.time.tick,
            "time":        self._serialize_time(world.time),
            "weather":     world.weather.value,
            "tiles":       self._serialize_tiles(world),
            "npcs":        [self._serialize_npc(npc, world) for npc in world.npcs],
            "god":         {"commentary": world.god.commentary},
            "events":      [self._serialize_event(e) for e in events],
            "token_usage": token_tracker.snapshot(),
        }
```

### 地块序列化（紧凑格式）

只输出**非草地且有内容**的地块，以减少网络传输量：

```python
def _serialize_tiles(world: World) -> list[dict]:
    tiles = []
    for tile in world.tiles.values():
        d = {"x": tile.x, "y": tile.y}
        if tile.tile_type != TileType.GRASS:
            d["t"] = TILE_CODE[tile.tile_type]   # "r"/"f"/"o"
        if tile.is_exchange:
            d["e"] = 1
        if tile.resource and tile.resource.quantity > 0:
            d["r"]  = RESOURCE_CODE[tile.resource.resource_type]
            d["q"]  = tile.resource.quantity
            d["mq"] = tile.resource.max_quantity
        if tile.npc_ids:
            d["n"] = tile.npc_ids
        if len(d) > 2:   # 除 x/y 外有其他字段才输出
            tiles.append(d)
    return tiles
```

### 编码映射

```python
TILE_CODE     = {TileType.ROCK: "r", TileType.FOREST: "f", TileType.TOWN: "o"}
RESOURCE_CODE = {ResourceType.WOOD: "w", ResourceType.STONE: "s",
                 ResourceType.ORE: "o",  ResourceType.FOOD: "f"}
```

---

## main.py

FastAPI 应用入口，负责：

1. **静态文件服务**：`/static/*` → `frontend/` 目录
2. **首页路由**：`GET /` → `frontend/index.html`
3. **Settings API**：`GET/POST /api/settings`
4. **WebSocket 端点**：`WS /ws`
5. **生命周期钩子**：`@startup` 启动 GameLoop，`@shutdown` 停止

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
            game_loop.handle_god_command(msg)       # 直接上帝指令
        elif msg["type"] == "control":
            game_loop.handle_control(msg)           # 游戏控制
        elif msg["type"] == "god_direct":
            game_loop.handle_god_command(msg)       # 同 god_command
```