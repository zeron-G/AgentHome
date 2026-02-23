# AgentHome — LLM 驱动的 AI 沙盒世界

> 一个 2D 沙盒游戏：4 个 NPC + 1 个上帝，每个角色由 Google Gemini 独立控制，具有独立记忆、实时对话和资源交互能力，通过浏览器可视化。

---

## 目录

- [快速启动](#快速启动)
- [完整启动流程](#完整启动流程)
- [项目结构](#项目结构)
- [整体架构设计](#整体架构设计)
- [模块详解 — 逐函数说明](#模块详解--逐函数说明)
  - [config.py](#configpy)
  - [engine/world.py](#engineworldpy)
  - [engine/world_manager.py](#engineworld_managerpy)
  - [game/events.py](#gameevents.py)
  - [game/token_tracker.py](#gametoken_trackerpy)
  - [game/loop.py](#gamelooppy)
  - [agents/prompts.py](#agentspromptspy)
  - [agents/base_agent.py](#agentsbase_agentpy)
  - [agents/npc_agent.py](#agentsnpc_agentpy)
  - [agents/god_agent.py](#agentsgod_agentpy)
  - [ws/manager.py](#wsmanagerpy)
  - [ws/serializer.py](#wsserializerpy)
  - [main.py](#mainpy)
  - [frontend/index.html](#frontendindexhtml)
- [WebSocket 协议](#websocket-协议)
- [NPC 动作 Schema](#npc-动作-schema)
- [上帝动作 Schema](#上帝动作-schema)
- [Token 用量管理](#token-用量管理)
- [目前存在的问题](#目前存在的问题)
- [可以改进的地方](#可以改进的地方)

---

## 快速启动

**前提**：Python 3.11+，已安装依赖，`.env` 文件中有 API Key。

```bash
cd d:\data\code\github\agenthome

# 使用项目所在 conda 环境
d:\program\codesupport\anaconda\envs\agent\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 浏览器访问
# http://localhost:8000
```

---

## 完整启动流程

### 1. 环境准备

```bash
# 确认 Python 版本 >= 3.11
d:\program\codesupport\anaconda\envs\agent\python.exe --version

# 安装依赖
d:\program\codesupport\anaconda\envs\agent\Scripts\pip.exe install -r requirements.txt
```

### 2. 配置 API Key

编辑 `.env` 文件（已预置）：

```env
GEMINI_API_KEY=你的Google_Gemini_API_Key
GEMINI_MODEL=gemini-2.5-flash
```

可用模型查询：到 [Google AI Studio](https://aistudio.google.com) 确认你的 key 有权访问哪些模型。经测试，`gemini-2.5-flash` 可用，`gemini-2.0-flash` 已对新用户关闭。

### 3. 启动服务器

```bash
# 前台启动（推荐开发时使用，可看日志）
d:\program\codesupport\anaconda\envs\agent\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 带热重载（修改代码后自动重启，注意：热重载会重置世界状态）
d:\program\codesupport\anaconda\envs\agent\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 后台静默启动
d:\program\codesupport\anaconda\envs\agent\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 > game.log 2>&1 &
```

### 4. 访问游戏

浏览器打开 `http://localhost:8000`

### 5. 验证正常运行

服务器日志应依次出现：
```
INFO: Started server process [xxxxx]
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
[INFO] game.loop: Game loop starting...
[INFO] agents.npc_agent: [Alice] action=move ...   ← NPC 开始行动
[INFO] agents.npc_agent: [Bob] action=gather ...
```

### 6. 关闭服务器

```bash
# 前台：Ctrl+C

# 后台进程：
pkill -f "uvicorn main:app"
# 或查找 PID 后 kill
```

---

## 项目结构

```
agenthome/
│
├── main.py                 # FastAPI 应用入口，WebSocket 端点，生命周期
├── config.py               # 所有可调参数（模型、timing、token限额等）
├── requirements.txt        # Python 依赖
├── .env                    # 环境变量（API Key、Model名）
│
├── engine/                 # 世界数据模型与状态变更
│   ├── __init__.py
│   ├── world.py            # 所有数据类 + create_world() 世界生成
│   └── world_manager.py    # 动作执行逻辑（移动/采集/交易/上帝操作）
│
├── agents/                 # LLM Agent 逻辑
│   ├── __init__.py
│   ├── prompts.py          # 提示词模板 + Pydantic 动作 Schema
│   ├── base_agent.py       # Gemini API 调用基类，含 token 记录
│   ├── npc_agent.py        # NPC 决策处理器
│   └── god_agent.py        # 上帝决策处理器
│
├── game/                   # 游戏核心逻辑
│   ├── __init__.py
│   ├── loop.py             # 主游戏循环（世界tick + NPC/上帝各自异步循环）
│   ├── events.py           # 事件类型、WorldEvent、EventBus（邻近过滤）
│   └── token_tracker.py    # Token 计数、限额、暂停控制
│
├── ws/                     # WebSocket 服务
│   ├── __init__.py
│   ├── manager.py          # 连接池管理、广播
│   └── serializer.py       # 世界状态 → JSON 序列化
│
└── frontend/               # 前端（单页应用）
    └── index.html          # 完整 HTML + CSS + JS（Canvas渲染 + UI）
```

---

## 整体架构设计

### 并发模型

游戏运行在单个 Python 异步事件循环（asyncio）中，共有 **6 个并发协程**：

```
FastAPI/uvicorn event loop
    │
    ├── WebSocket handler(s)        ← 每个浏览器连接一个
    │
    ├── _world_tick_loop()          ← 每 3 秒：推进时间 + 被动效果 + 广播
    │
    ├── _npc_brain_loop(Alice)      ← 独立节奏：LLM 调用 → 执行动作
    ├── _npc_brain_loop(Bob)
    ├── _npc_brain_loop(Carol)
    ├── _npc_brain_loop(Dave)
    │
    └── _god_brain_loop()           ← 每 20-40 秒：LLM 决策 → 天气/资源
```

### 数据流

```
NPC Brain Loop:
  1. build_npc_context(npc, world)      → 构建当前状态文本
  2. call_llm(system, context, history) → Gemini API 异步调用
  3. 返回 NPCAction(JSON)
  4. async with world_lock:
       apply_npc_action(npc, action)    → 修改 world 状态
  5. event_bus.dispatch(events)         → 写入邻近NPC的inbox
  6. ws_manager.broadcast(snapshot)     → 推送给所有浏览器

World Tick Loop:
  1. world.time.advance()               → 推进游戏时间
  2. world_manager.apply_passive()      → 体力消耗、资源再生
  3. 处理 pending_commands（玩家上帝指令）
  4. ws_manager.broadcast(snapshot)     → 推送世界状态
```

### 对话/打断机制

NPC 的"打断"效果通过**收件箱（inbox）+ 独立循环节奏**实现：

1. Alice 说话 → 生成 `WorldEvent(NPC_SPOKE)` → EventBus 分发给 5 格内所有 NPC 的 inbox
2. 下一轮 Bob 的 brain loop 被触发时，inbox 中已有 Alice 的话
3. Bob 的 LLM 上下文包含 inbox 内容，自然做出回应或选择打断
4. 若 Bob 选择 `interrupt` 动作，消息会带 `[打断]` 前缀广播
5. Bob 说话后，think time 缩短为 3-6 秒（正常 5-10 秒），模拟对话节奏加快

### 世界生成（固定种子）

`create_world(seed=42)` 使用固定随机种子，保证每次启动地图相同：
- 中心湖泊（半径 2）+ 3 条分支河流
- 4 个角落各一个岩石群（半径 2-3）
- 6 个随机森林群（半径 1-3）
- 森林：75% 概率有木头资源（4-10 个）
- 岩石：65% 概率有资源，其中 30% 是矿石，70% 是石头

---

## 模块详解 — 逐函数说明

---

### config.py

全局配置，所有参数都可在此调整，无需修改业务代码。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GEMINI_API_KEY` | 从 `.env` 读取 | Google Gemini API Key |
| `MODEL_NAME` | `gemini-2.5-flash` | 使用的 Gemini 模型 |
| `WORLD_WIDTH` | `20` | 世界宽度（格子数） |
| `WORLD_HEIGHT` | `20` | 世界高度（格子数） |
| `WORLD_TICK_SECONDS` | `3.0` | 世界时间/被动效果更新间隔（秒） |
| `NPC_MIN_THINK_SECONDS` | `5.0` | NPC 两次决策之间最短等待时间 |
| `NPC_MAX_THINK_SECONDS` | `10.0` | NPC 两次决策之间最长等待时间 |
| `GOD_MIN_THINK_SECONDS` | `20.0` | 上帝两次决策之间最短等待时间 |
| `GOD_MAX_THINK_SECONDS` | `40.0` | 上帝两次决策之间最长等待时间 |
| `HISTORY_MAX_TURNS` | `20` | 每个 NPC 保留的最大对话历史轮数 |
| `NOTES_MAX_COUNT` | `10` | 每个 NPC 的最大个人笔记条数 |
| `NPC_HEARING_RADIUS` | `5` | NPC 能"听到"对话的曼哈顿距离（格子） |
| `NPC_ADJACENT_RADIUS` | `1` | 交易要求的最大距离（格子） |
| `DEFAULT_TOKEN_LIMIT` | `200_000` | 会话 Token 总用量上限 |
| `LLM_TEMPERATURE` | `0.85` | LLM 创造性参数（0=保守，1=随机） |
| `LLM_MAX_TOKENS` | `1024` | 单次 LLM 返回的最大 Token 数 |

---

### engine/world.py

核心数据模型，所有游戏实体都在这里定义。

#### 枚举类型

```python
TileType   # "grass" | "water" | "rock" | "forest"
WeatherType # "sunny" | "rainy" | "storm"
ResourceType # "wood" | "stone" | "ore"
```

#### 数据类

**`Resource`**
```python
@dataclass
class Resource:
    resource_type: ResourceType  # 资源类型
    quantity: int                # 当前数量
    max_quantity: int            # 最大容量（wood/stone:10, ore:5）
```

**`Tile`**
```python
@dataclass
class Tile:
    x: int                        # 横坐标（0 到 width-1）
    y: int                        # 纵坐标（0 到 height-1）
    tile_type: TileType           # 地块类型
    resource: Optional[Resource]  # 该格的资源（可为 None）
    npc_ids: list                 # 当前站在这格的 NPC id 列表
```

**`WorldTime`**
```python
@dataclass
class WorldTime:
    tick: int          # 全局 tick 计数（从 0 开始，每次 world tick +1）
    hour: float        # 当前游戏小时（0.0-23.99）
    day: int           # 当前天数（从 1 开始）
    hours_per_tick: float  # 每次 tick 推进几游戏小时（默认 0.5）

    # 属性
    @property phase: str     # "dawn"(5-8h) | "day"(8-18h) | "dusk"(18-21h) | "night"
    @property time_str: str  # 格式化时间字符串，如 "Day 3 14:30"

    def advance()  # 推进一个 tick：tick+1, hour+=0.5，满24时 hour-=24, day+=1
```

**`Inventory`**
```python
@dataclass
class Inventory:
    wood: int   # 木头数量
    stone: int  # 石头数量
    ore: int    # 矿石数量

    def get(item: str) -> int         # 按名称获取数量（"wood"/"stone"/"ore"）
    def set(item: str, value: int)    # 按名称设置数量，自动 max(0, value)
```

**`AgentMemory`**
```python
@dataclass
class AgentMemory:
    conversation_history: list  # [{"role":"user"/"model","text":str}, ...]
    personal_notes: list        # ["笔记1", "笔记2", ...]，上限 max_notes 条
    inbox: list                 # 本轮收到的事件摘要字符串列表
    max_history_turns: int      # = HISTORY_MAX_TURNS（20）
    max_notes: int              # = NOTES_MAX_COUNT（10）

    def add_history_turn(role, text)
    # 追加一轮对话记录，超限时从头部删除最旧记录
    # 实际存储条目数 = max_history_turns * 2（user + model 各一条算一轮）

    def add_note(note: str)
    # 追加个人笔记，超过 max_notes 时删除最旧一条

    def clear_inbox()
    # 清空收件箱（在 NPC 读完 inbox 后调用）

    def add_to_inbox(event_summary: str)
    # 向收件箱追加一条事件摘要
```

**`NPC`**
```python
@dataclass
class NPC:
    npc_id: str          # 唯一标识，如 "npc_alice"
    name: str            # 显示名称，如 "Alice"
    x: int               # 当前 X 坐标
    y: int               # 当前 Y 坐标
    personality: str     # 性格描述字符串，注入到 LLM 系统提示
    color: str           # 前端显示颜色（十六进制，如 "#4CAF50"）
    inventory: Inventory # 背包
    memory: AgentMemory  # 记忆（对话历史 + 笔记 + 收件箱）
    is_processing: bool  # True 表示正在等待 LLM 响应（防重入）
    last_action: str     # 上次动作类型（"move"/"gather"/"talk"等）
    last_message: str    # 上次说的话（用于前端显示气泡）
    last_message_tick: int  # 上次说话时的 tick（用于气泡超时判断）
    energy: int          # 体力值（0-100），耗尽不影响行动但会持续扣
```

**`GodEntity`**
```python
@dataclass
class GodEntity:
    personality: str          # 神明性格描述
    memory: AgentMemory       # 记忆（只保留与 LLM 的对话历史）
    is_processing: bool       # 防重入标志
    last_commentary: str      # 最新旁白（显示在前端上帝面板）
    pending_commands: list    # 玩家通过 UI 排队的指令 [{"command":...}, ...]
```

**`World`**
```python
@dataclass
class World:
    width: int                    # 地图宽度（格子）
    height: int                   # 地图高度（格子）
    tiles: list[list[Tile]]       # 二维格子数组，tiles[y][x]
    weather: WeatherType          # 当前天气
    time: WorldTime               # 当前时间对象
    npcs: list[NPC]               # 所有 NPC 列表
    god: GodEntity                # 上帝对象
    recent_events: list[str]      # 近 30 条全局事件摘要

    def get_tile(x, y) -> Optional[Tile]
    # 安全获取格子，越界返回 None

    def get_npc(npc_id) -> Optional[NPC]
    # 按 npc_id 查找 NPC

    def get_nearby_npcs(npc, radius) -> list[NPC]
    # 获取距离 npc 曼哈顿距离 <= radius 的所有其他 NPC

    def add_event(summary: str)
    # 向 recent_events 追加一条事件摘要，超 30 条时删最旧
```

#### 世界生成函数

```python
def _place_cluster(tiles, width, height, tile_type, cx, cy, radius)
# 内部辅助：以 (cx,cy) 为圆心、radius 为半径，将草地格子改为 tile_type
# 只覆盖草地（不覆盖水域），避免破坏已有水域形状

def create_world(seed: int = 42) -> World
# 完整世界生成，固定种子保证每次启动地图相同
# 返回一个已初始化好 tiles、npcs、god 的 World 对象
# NPC 初始位置：Alice(3,3) Bob(16,3) Carol(3,16) Dave(16,16)
```

---

### engine/world_manager.py

负责所有世界状态变更，每个变更都可能产生事件。

```python
class WorldManager:
    def __init__(self, event_bus: EventBus)
    # 持有 event_bus 引用，但实际上 WorldManager 本身不 dispatch 事件
    # 调用方负责对返回的 events 调用 event_bus.dispatch()
```

#### `apply_passive(world)`

每次 world tick 调用一次，处理被动效果：

- **体力消耗**：每个 NPC 每 tick 消耗 1 点（白天）或 2 点（夜晚/黎明/黄昏），暴风天额外 +1
- **黎明回复**：phase=="dawn" 时每 tick 回复 1 点体力
- **资源再生**：每 10 tick 触发一次，每个未满的资源格再生 1 点（雨天 +1，共 2 点）

#### `apply_npc_action(npc, action, world) -> list[WorldEvent]`

接收 LLM 返回的 action dict，执行对应操作，返回产生的事件列表。

| action.action | 调用的内部方法 | 说明 |
|---------------|---------------|------|
| `"move"` | `_do_move()` | 移动，消耗 2 点体力（暴风 3 点） |
| `"gather"` | `_do_gather()` | 采集当前格资源，消耗 5 点体力 |
| `"talk"` / `"interrupt"` | `_do_talk()` | 发言，interrupt 前缀加 `[打断]` |
| `"trade"` | `_do_trade()` | 双向物品交换，要求双方在 1 格内 |
| `"rest"` | 内联 | 回复 20 点体力，不产生事件 |
| `"think"` | 内联 | 写入 personal_notes，不产生事件 |

**`_do_move(npc, action, world, tick)`**
- 从 action 取 `dx`, `dy`，各限制在 [-1, 1]
- 边界检查，水域阻挡
- 更新 `old_tile.npc_ids`（移除）和 `new_tile.npc_ids`（添加）
- 产生 `NPC_MOVED` 事件（广播半径 2 格）

**`_do_gather(npc, world, tick)`**
- 检查当前格是否有资源且 quantity > 0
- 每次最多采集 2 个，更新资源 quantity 和 NPC 背包
- 资源耗尽时额外产生 `RESOURCE_DEPLETED` 事件

**`_do_talk(npc, action, world, tick)`**
- 取 action 中的 `message` 和 `target_id`
- interrupt 动作的消息加 `[打断] ` 前缀
- 更新 `npc.last_message` 和 `npc.last_message_tick`（用于前端气泡）
- 产生 `NPC_SPOKE` 事件（广播半径 5 格）

**`_do_trade(npc, action, world, tick)`**
- 验证目标 NPC 存在且在 1 格内
- 验证双方各自拥有足够物品
- 原子性双向物品交换（同一 tick 内完成，无需握手）
- 产生 `NPC_TRADED` 事件

#### `apply_god_action(action, world) -> list[WorldEvent]`

处理上帝 LLM 决策或玩家直接指令：

- `"set_weather"`：修改 `world.weather`，更新 `god.last_commentary`
- `"spawn_resource"`：在指定格子放置资源（不能放在水域）

#### `apply_direct_god_command(cmd, world) -> list[WorldEvent]`

将前端 WebSocket 消息（`god_command` 类型）转为 action dict，调用 `apply_god_action()`。直接执行，不经过 LLM。

---

### game/events.py

事件系统，连接世界变更和 NPC 感知。

#### `EventType`（字符串枚举）

| 值 | 触发时机 |
|----|----------|
| `npc_spoke` | NPC 说话或打断 |
| `npc_moved` | NPC 移动成功 |
| `npc_gathered` | NPC 采集资源 |
| `npc_traded` | NPC 完成交易 |
| `npc_rested` | NPC 休息（当前未使用） |
| `npc_thought` | NPC 记录笔记（当前未使用） |
| `weather_changed` | 天气变化 |
| `resource_spawned` | 上帝刷新资源 |
| `resource_depleted` | 资源耗尽 |
| `time_advanced` | 时间推进（当前未使用） |
| `god_commentary` | 上帝旁白（当前未使用） |

#### `WorldEvent`

```python
@dataclass
class WorldEvent:
    event_type: EventType   # 事件类型
    tick: int               # 发生时的 tick
    actor_id: Optional[str] # 行为者 npc_id（None 表示全局事件）
    origin_x: Optional[int] # 事件发生的 X 坐标（None = 全局广播）
    origin_y: Optional[int] # 事件发生的 Y 坐标（None = 全局广播）
    radius: int             # 邻近感知半径（默认 5）
    payload: dict           # 额外数据，因 event_type 不同而不同

    def to_summary(world) -> str
    # 将事件转为人类可读的中文摘要字符串
    # 用于：写入 NPC inbox、写入 world.recent_events、前端聊天记录

    def to_dict(world) -> dict
    # 将事件转为 JSON 可序列化的 dict
    # 用于 WebSocket 广播中的 events 数组
```

#### `EventBus`

```python
class EventBus:
    def dispatch(event: WorldEvent, world: World)
    # 1. 调用 event.to_summary() 写入 world.recent_events
    # 2. 遍历所有 NPC：
    #    - 跳过行为者自身
    #    - 若 origin_x 为 None（全局事件）→ 写入所有 NPC 的 inbox
    #    - 若有坐标 → 计算曼哈顿距离，≤ radius 的 NPC 才写入 inbox
```

---

### game/token_tracker.py

追踪 Gemini API 调用的 token 消耗，实现超限自动暂停。

```python
@dataclass
class AgentTokenUsage:
    prompt_tokens: int      # 输入 token 数
    completion_tokens: int  # 输出 token 数

    @property total: int    # 总计 = prompt + completion
```

```python
class TokenTracker:
    def __init__(session_limit: int = 200_000)
    # 初始化，设定会话上限

    @property paused: bool
    # 是否已暂停（超限时自动设为 True）

    @property total_tokens: int
    # 当前会话总消耗 token 数

    async def record(agent_id, usage_metadata) -> int
    # 从 Gemini response.usage_metadata 提取 token 数并累加
    # 使用 asyncio.Lock 保证并发安全
    # 超限时自动设 paused=True
    # 返回本次消耗的 token 数

    def resume(new_limit=None)
    # 恢复游戏，可选传入新的限额

    def set_limit(new_limit: int)
    # 更新限额，若当前用量已低于新限额则自动恢复

    def snapshot() -> dict
    # 返回用量快照，格式：
    # {
    #   "total_tokens_used": int,
    #   "prompt_tokens": int,
    #   "completion_tokens": int,
    #   "limit": int,
    #   "paused": bool,
    #   "usage_pct": float,      # 百分比，保留1位小数
    #   "per_agent": {           # 各 agent 分项
    #     "npcs": {"total":int, "prompt":int, "completion":int},
    #     "god":  {"total":int, ...}
    #   }
    # }
```

**注意**：NPC 共用 agent_id `"npcs"`，上帝用 `"god"`，因此 per_agent 只有两条记录。

---

### game/loop.py

游戏主编排层，管理所有异步循环。

```python
class GameLoop:
    def __init__()
    # 初始化所有组件（world, event_bus, world_manager, token_tracker,
    #                   ws_manager, serializer, npc_agent, god_agent）
    # 创建 asyncio.Lock 用于世界状态互斥访问
    # 注意：create_world() 在此调用，world 在服务器进程生命周期内持续

    async def start()
    # 启动所有异步任务：
    #   - _world_tick_loop()
    #   - _god_brain_loop()
    #   - _npc_brain_loop(npc) × 4
    # 使用 asyncio.gather() 并发运行，任一异常不影响其他

    async def stop()
    # 设 _running=False，各循环在下次 while 检查时自然退出

    def handle_god_command(cmd: dict)
    # 将玩家 god_command 消息追加到 world.god.pending_commands
    # 供下一次 world_tick_loop 处理

    def handle_control(cmd: dict)
    # 处理游戏控制指令：
    #   "pause"     → token_tracker._paused = True
    #   "resume"    → token_tracker.resume()
    #   "set_limit" → token_tracker.set_limit(value)
```

#### `_world_tick_loop()`

```
每 WORLD_TICK_SECONDS(3秒) 循环一次：
1. async with world_lock: 推进时间 + 应用被动效果
2. 若有 pending_commands：
   async with world_lock: 处理所有积压的玩家上帝指令
   dispatch events → broadcast（含事件）→ continue（跳过普通 broadcast）
3. broadcast 当前世界状态（不含新事件）
4. sleep(WORLD_TICK_SECONDS)
```

#### `_npc_brain_loop(npc)`

```
初始 sleep 1-4 秒（错开所有 NPC 的首次 LLM 调用时间）

循环：
1. 若 token_tracker.paused → sleep 2秒 → continue
2. await npc_agent.process(npc, world)    # LLM 调用（可能耗时2-10秒）
3. 若 action 不为 idle：
   async with world_lock: apply_npc_action → 得到 events
   dispatch 所有 events（写入邻近 NPC inbox）
   broadcast_with_events（含事件推送给前端）
4. 计算等待时间：
   - 上次动作为 talk → 3-6 秒（快速响应对话）
   - 其他 → 5-10 秒（正常思考时间）
5. sleep(等待时间)
```

#### `_god_brain_loop()`

```
初始 sleep 5-10 秒（延迟首次上帝决策）

循环：
1. 若 token_tracker.paused → sleep 2秒 → continue
2. await god_agent.process(world.god, world)  # LLM 调用
3. 若返回 action：
   async with world_lock: apply_god_action
   dispatch events → broadcast_with_events
4. sleep(20-40 秒)
```

#### `_broadcast()` / `_broadcast_with_events(events)`

```python
async def _broadcast()
# 序列化当前世界状态（无事件）并广播给所有 WebSocket 客户端

async def _broadcast_with_events(events: list[WorldEvent])
# 序列化当前世界状态（含事件列表）并广播
```

---

### agents/prompts.py

LLM 提示词模板和结构化输出 Schema。

#### Pydantic Schema

**`NPCAction`**：LLM 必须返回的 JSON 结构（通过 `response_schema` 强制）

```python
class NPCAction(BaseModel):
    action: str            # 必填：动作类型
    dx: Optional[int]      # move 用：X 方向 (-1/0/1)
    dy: Optional[int]      # move 用：Y 方向 (-1/0/1)
    thought: Optional[str] # move/gather/rest 用：内心想法（不广播）
    message: Optional[str] # talk/interrupt 用：说的话
    target_id: Optional[str] # talk/interrupt/trade 用：目标 NPC id
    offer_item: Optional[str]  # trade 用："wood"/"stone"/"ore"
    offer_qty: Optional[int]   # trade 用：给出数量
    request_item: Optional[str] # trade 用：索取物品类型
    request_qty: Optional[int]  # trade 用：索取数量
    note: Optional[str]    # think 用：要记录的笔记内容
```

**`GodAction`**：上帝 LLM 必须返回的 JSON 结构

```python
class GodAction(BaseModel):
    action: str              # "set_weather" | "spawn_resource"
    weather: Optional[str]   # set_weather 用："sunny"/"rainy"/"storm"
    resource_type: Optional[str]  # spawn_resource 用："wood"/"stone"/"ore"
    x: Optional[int]         # spawn_resource 用：X 坐标
    y: Optional[int]         # spawn_resource 用：Y 坐标
    quantity: Optional[int]  # spawn_resource 用：刷新数量
    commentary: str          # 必填：上帝旁白（显示在前端）
```

#### 提示词构建函数

```python
def build_npc_system_prompt(npc, world) -> str
# 将 NPC_SYSTEM_PROMPT 模板用 npc.name/personality 和 world.width/height 填充
# 结果作为 system_instruction 传给 Gemini
# 包含：角色设定、世界规则、所有动作格式说明

def build_npc_context(npc, world) -> tuple[str, bool]
# 构建每轮决策的用户消息（world snapshot）
# 返回：(context_string, is_social_mode)
# 社交模式（有附近 NPC 或 inbox 非空）→ NPC_CONTEXT_SOCIAL
# 独思模式（无人在附近且 inbox 为空）→ NPC_CONTEXT_ALONE
# 包含：tick/时间/天气、位置/体力/背包、当前地块信息、
#        附近 NPC（社交模式）、个人笔记、收件箱（社交模式）、近期事件

def build_god_context(god, world) -> str
# 构建上帝的世界状态观察
# 包含：tick/时间、天气、所有 NPC 的位置/背包/体力/上次动作、
#        近 10 条全局事件、玩家 pending_commands（若有）
```

---

### agents/base_agent.py

Gemini API 调用的基础封装。

```python
class BaseAgent:
    def __init__(agent_id: str, token_tracker: TokenTracker)
    # agent_id：用于 token 统计分类（"npcs" 或 "god"）
    # 创建 genai.Client(api_key=GEMINI_API_KEY)

    async def call_llm(
        system_prompt: str,
        context_message: str,
        history: list[dict],          # [{"role":"user"/"model","text":str}, ...]
        response_schema: Type[BaseModel]
    ) -> Optional[BaseModel]
    # 核心 LLM 调用方法：
    # 1. 将 history 转为 Gemini Content 对象列表
    # 2. 追加 context_message 作为最新用户消息
    # 3. 配置 GenerateContentConfig：
    #    - system_instruction = system_prompt
    #    - response_mime_type = "application/json"（强制 JSON 输出）
    #    - response_schema = response_schema（Pydantic 模型，强制结构）
    #    - temperature / max_output_tokens 从 config 读取
    # 4. 调用 client.aio.models.generate_content()（异步）
    # 5. 从 response.usage_metadata 记录 token 用量
    # 6. 解析 response.text → json.loads() → response_schema(**data)
    # 7. 异常处理：JSONDecodeError → 返回 None，其他异常 → 记录日志返回 None
```

**关键实现细节**：
- 使用 `genai_types.Part(text=turn["text"])` 而非 `Part.from_text(turn["text"])`，因为 google-genai 1.x 中 `from_text` 的 `text` 参数是关键字参数
- `response_mime_type="application/json"` + `response_schema` 组合强制模型只输出合法 JSON，大幅减少解析失败率

---

### agents/npc_agent.py

NPC 的决策处理器。

```python
class NPCAgent(BaseAgent):
    def __init__(token_tracker: TokenTracker)
    # 以 agent_id="npcs" 初始化（所有 NPC 共用同一个 NPCAgent 实例）

    async def process(npc: NPC, world: World) -> dict
    # NPC 大脑：一次完整的决策周期
    # 1. is_processing 防重入检查（若已在处理则返回 idle）
    # 2. 设 npc.is_processing = True（前端显示 ⏳ 图标）
    # 3. 构建 system_prompt 和 context_message
    # 4. 调用 call_llm()，传入 npc.memory.conversation_history
    # 5. 若失败：从 _FALLBACK_ACTIONS 随机选一个（rest/move）
    # 6. 成功：将本轮 (context, response) 写入 conversation_history
    # 7. 清空 npc.memory.inbox（已读）
    # 8. 返回 action.model_dump(exclude_none=True)
    # finally: is_processing = False

_FALLBACK_ACTIONS = [
    {"action": "rest", "thought": "我需要稍微休息一下"},
    {"action": "move", "dx": 1, "dy": 0, "thought": "四处走走看看"},
    {"action": "move", "dx": 0, "dy": 1, "thought": "探索一下"},
]
```

---

### agents/god_agent.py

上帝的决策处理器。

```python
class GodAgent(BaseAgent):
    def __init__(token_tracker: TokenTracker)
    # agent_id="god"

    async def process(god: GodEntity, world: World) -> dict | None
    # 上帝大脑：一次完整决策
    # 1. is_processing 防重入
    # 2. 构建 god system_prompt（含 god.personality）和 god context
    # 3. 调用 call_llm()，schema 为 GodAction
    # 4. 将对话写入 god.memory.conversation_history
    # 5. 清空 god.pending_commands（玩家请求已被 LLM 读取）
    # 6. 返回 action dict 或 None（失败时）
```

---

### ws/manager.py

WebSocket 连接池，支持多浏览器同时连接。

```python
class WSManager:
    def __init__()
    # 内部维护 _connections: list[WebSocket]
    # asyncio.Lock 保护并发修改

    async def connect(ws: WebSocket)
    # 接受连接（ws.accept()），加入连接池

    async def disconnect(ws: WebSocket)
    # 从连接池移除

    async def broadcast(data: dict)
    # 将 data 序列化为 JSON 字符串（ensure_ascii=False 保证中文正常）
    # 发送给所有已连接客户端
    # 发送失败（断开）的连接自动从池中移除

    async def send_to(ws: WebSocket, data: dict)
    # 单独发送给指定连接（用于 connect 时的初始快照）

    @property connection_count: int
    # 当前连接数
```

---

### ws/serializer.py

世界状态序列化，将 Python 对象转为前端可用的 JSON。

```python
class WorldSerializer:
    def world_snapshot(world, token_tracker, events=None) -> dict
    # 生成完整世界快照，结构见 WebSocket 协议章节
    # events: 本次 tick 产生的事件列表（无事件时传 [] 或 None）

    def _serialize_tiles(world) -> list[dict]
    # 将 20×20=400 个 Tile 对象序列化
    # 使用单字母缩写节省带宽：
    #   "t": tile_type 首字母（g/w/r/f）
    #   "r": resource_type 首字母（w/s/o），仅当有资源时包含
    #   "q": resource quantity（仅当有资源时）
    #   "mq": max_quantity（仅当有资源时）
    #   "n": npc_ids 列表（仅当有 NPC 时）

    def _serialize_npc(npc) -> dict
    # 序列化单个 NPC 的前端需要信息
    # 包含：id/name/x/y/color/energy/inventory/last_action/
    #        last_message/last_message_tick/is_processing
```

---

### main.py

FastAPI 应用入口。

```python
app = FastAPI(title="AgentHome")
game_loop = GameLoop()   # 模块级单例，应用启动时创建

# 路由
GET /          → 返回 frontend/index.html（FileResponse）
GET /static/*  → 静态文件服务（frontend/ 目录）
WS  /ws        → WebSocket 端点

# WebSocket 端点处理逻辑
async def websocket_endpoint(ws):
    1. ws_manager.connect(ws)
    2. 立即发送当前世界快照（让新连接立刻看到地图）
    3. 循环接收消息：
       - "god_command" → game_loop.handle_god_command(msg)
       - "control"     → game_loop.handle_control(msg)
       - "god_direct"  → 同 god_command（两者等价）
    4. disconnect 时清理连接池

# 生命周期
@app.on_event("startup")
# 创建 asyncio.Task 启动 game_loop.start()
# 注意：game_loop 是模块级对象，在 import main 时已创建，startup 时才启动循环

@app.on_event("shutdown")
# 调用 game_loop.stop()（设 _running=False）
```

---

### frontend/index.html

单文件前端（HTML + CSS + JS 合并），无外部依赖。

#### 布局结构

```
#header      顶部状态栏：标题、Tick、时间、天气、Token进度条
#main        主区域（flex 横向）
  #canvas-wrap  左侧地图区域
    canvas#world-canvas    主渲染画布 600×600px（30px/格 × 20格）
    canvas#weather-overlay 天气效果叠加层（position:absolute）
  #side         右侧面板 300px
    #god-panel  上帝控制台（天气按钮 + 资源刷新按钮 + 旁白）
    #npc-list   4个 NPC 状态行
    #npc-detail 选中 NPC 详情
    #chat-wrap  世界日志（滚动聊天记录）
#status-bar  底部连接状态
#tooltip     鼠标悬停格子信息（fixed定位）
#paused-overlay  Token超限暂停遮罩层
```

#### JS 核心变量

```javascript
state = {
  world: null,         // 最新世界快照（来自 WS）
  selectedNpc: null,   // 当前选中的 NPC id
  spawnMode: null,     // 待刷新的资源类型（"wood"/"stone"/"ore"/null）
  selectedTile: null,  // 刷新目标格子 {x, y}
  tick: 0,
  ws: null,
  connected: false,
  rain_particles: [],  // 雨滴粒子数组
}

tileMap = {}          // 以 "x,y" 为 key 的格子快速查找表
npcBubbles = {}       // 气泡缓存 {npcId: {msg, npc}}，tick 超时自动清除
```

#### JS 主要函数

| 函数 | 说明 |
|------|------|
| `connectWS()` | 建立 WebSocket 连接，断开后 3 秒自动重连 |
| `sendMsg(obj)` | 向服务器发送 JSON 消息 |
| `handleWorldState(msg)` | 收到 world_state 消息时的总调度函数 |
| `updateHeader(msg)` | 更新顶部 tick/时间/天气显示 |
| `updateTokenUI(usage)` | 更新 Token 进度条和暂停遮罩 |
| `updateNpcList(npcs)` | 重渲染右侧 NPC 状态列表 |
| `updateNpcDetail(npcs)` | 更新选中 NPC 的详情面板 |
| `updateGodSpeech(god)` | 更新上帝旁白文本 |
| `appendChatEvent(ev, time)` | 向聊天记录追加一条事件，保留最多 200 条 |
| `buildTileMap(tiles)` | 从 tiles 数组构建 "x,y" → tile 的查找表 |
| `renderWorld(msg)` | 主渲染函数（Canvas 2D）：格子→资源→NPC→气泡 |
| `renderWeather(weather)` | 在叠加层渲染天气效果 |
| `animateRain(heavy)` | 雨/暴风粒子动画（requestAnimationFrame 驱动） |
| `setWeather(weather)` | 发送天气变更指令给服务器 |
| `prepareSpawn(type)` | 进入资源刷新模式，等待用户点击地图 |
| `executeSpawn(x, y)` | 在选定格子刷新资源，发送给服务器 |
| `resumeGame()` | 从暂停状态恢复，可选设置新限额 |

#### Canvas 渲染层级（从底到顶）

1. **格子背景**：按 `tile_type` 着色的矩形 + 0.5px 边框
2. **高亮选中格**：spawn 模式下白色边框
3. **资源图标**：
   - 木头（`w`）：棕色树干圆 + 绿色树冠圆
   - 石头（`s`）：灰色矩形
   - 矿石（`o`）：金色菱形
   - 透明度随 `quantity/max_quantity` 变化（越少越透明）
4. **NPC 圆圈**：彩色圆 + 旋转虚线环（处理中时）+ 名称标签
5. **对话气泡**：固定 tick 差内显示，自动截断超长文本
6. **天气叠加**（独立 canvas）：蓝色半透明（雨）/ 暗色（暴风）+ 粒子动画

---

## WebSocket 协议

### 服务端 → 前端

每次世界 tick 或有事件发生时推送：

```json
{
  "type": "world_state",
  "tick": 142,
  "time": {
    "hour": 14.5,
    "day": 3,
    "phase": "day",
    "time_str": "Day 3 14:30"
  },
  "weather": "sunny",
  "tiles": [
    { "x": 3, "y": 4, "t": "f", "r": "w", "q": 8, "mq": 10 },
    { "x": 3, "y": 3, "t": "g", "n": ["npc_alice"] }
  ],
  "npcs": [
    {
      "id": "npc_alice",
      "name": "Alice",
      "x": 3, "y": 3,
      "color": "#4CAF50",
      "energy": 82,
      "inventory": { "wood": 3, "stone": 0, "ore": 1 },
      "last_action": "talk",
      "last_message": "Bob，你有石头吗？",
      "last_message_tick": 140,
      "is_processing": false
    }
  ],
  "god": { "commentary": "孩子们在努力生存..." },
  "events": [
    {
      "type": "npc_spoke",
      "tick": 142,
      "actor": "Alice",
      "summary": "Alice: \"Bob，你有石头吗？\"",
      "message": "Bob，你有石头吗？",
      "target_id": "npc_bob"
    }
  ],
  "token_usage": {
    "total_tokens_used": 45230,
    "prompt_tokens": 38000,
    "completion_tokens": 7230,
    "limit": 200000,
    "paused": false,
    "usage_pct": 22.6,
    "per_agent": {
      "npcs": { "total": 42000, "prompt": 36000, "completion": 6000 },
      "god":  { "total": 3230, "prompt": 2000, "completion": 1230 }
    }
  }
}
```

**Tiles 字段缩写**：

| 字段 | 说明 |
|------|------|
| `t` | 地块类型首字母：`g`=grass, `w`=water, `r`=rock, `f`=forest |
| `r` | 资源类型首字母：`w`=wood, `s`=stone, `o`=ore（无资源时省略） |
| `q` | 资源当前数量（无资源时省略） |
| `mq` | 资源最大数量（无资源时省略） |
| `n` | 当前在该格的 NPC id 列表（无 NPC 时省略） |

### 前端 → 服务端

```json
// 上帝改变天气
{ "type": "god_command", "command": "set_weather", "value": "storm" }

// 上帝刷新资源（先点地图选格子，再点资源按钮发送）
{ "type": "god_command", "command": "spawn_resource",
  "resource_type": "ore", "x": 10, "y": 10, "quantity": 8 }

// 手动暂停
{ "type": "control", "command": "pause" }

// 恢复（不改限额）
{ "type": "control", "command": "resume" }

// 修改 token 限额（同时恢复游戏）
{ "type": "control", "command": "set_limit", "value": 500000 }
```

---

## NPC 动作 Schema

LLM 必须返回以下之一（Gemini 的 `response_schema` 参数强制执行 JSON 格式，但不强制枚举值）：

| action | 必填字段 | 可选字段 | 说明 |
|--------|---------|---------|------|
| `"move"` | `dx`(-1/0/1), `dy`(-1/0/1) | `thought` | 向指定方向移动一格 |
| `"gather"` | — | `thought` | 采集当前格资源 |
| `"talk"` | `message` | `target_id`, `thought` | 向范围内 NPC 说话 |
| `"interrupt"` | `message`, `target_id` | — | 打断目标 NPC，带 `[打断]` 前缀 |
| `"trade"` | `target_id`, `offer_item`, `offer_qty`, `request_item`, `request_qty` | — | 与相邻 NPC 交易 |
| `"rest"` | — | `thought` | 休息，恢复 20 点体力 |
| `"think"` | `note` | — | 记录个人笔记（私密，仅自己可见） |

---

## 上帝动作 Schema

| action | 必填字段 | 说明 |
|--------|---------|------|
| `"set_weather"` | `weather`("sunny"/"rainy"/"storm"), `commentary` | 改变天气 |
| `"spawn_resource"` | `resource_type`("wood"/"stone"/"ore"), `x`, `y`, `quantity`, `commentary` | 在指定位置刷新资源 |

---

## Token 用量管理

### 估算每次调用的 Token 消耗

- **NPC 系统提示**（固定部分）：约 300-400 token
- **NPC 历史对话**（最多 20 轮，每轮约 400 token）：0-8000 token
- **NPC 当前上下文**：约 200-500 token
- **NPC 响应**：约 50-150 token
- **单次 NPC 调用合计**：约 600-2000 token（随历史积累增加）

- **上帝调用**（历史较短）：约 800-1500 token

### 实际消耗速率（参考）

以 4 NPC + 上帝为例：
- NPC 每 5-10 秒决策一次
- 上帝每 20-40 秒决策一次
- 理论每分钟：4NPC × 6-12次 + 上帝 1.5-3次 = 30-52 次 LLM 调用
- 每分钟 token 消耗：约 20,000-80,000（取决于历史积累）
- **200k 限额约可支撑 3-10 分钟**

### 调整建议

| 场景 | 建议配置 |
|------|---------|
| 快速演示（3-5分钟） | `DEFAULT_TOKEN_LIMIT = 200_000` |
| 长时间观察（30分钟） | `DEFAULT_TOKEN_LIMIT = 1_000_000` |
| 控制对话历史长度 | `HISTORY_MAX_TURNS = 10`（减少历史） |
| 降低调用频率 | `NPC_MIN_THINK_SECONDS = 10` |

---

## 目前存在的问题

### 1. JSON 解析偶发失败

**表现**：后台日志出现 `JSON parse error: Unterminated string`
**原因**：`LLM_MAX_TOKENS=1024` 时，若 LLM 在 `thought` 或 `message` 字段生成较长的中文，可能触发截断，导致 JSON 不完整
**影响**：该 NPC 本轮 fallback 为随机 move/rest，不影响游戏运行
**临时缓解**：已将上限从 512 提升到 1024，可进一步调大

### 2. 交易成功率低

**表现**：NPC 很少成功完成 trade 动作
**原因**：trade 要求双方在 **1 格**内（曼哈顿距离 ≤ 1），且要求另一方 *已经拥有* 被请求的物品。NPC 不会提前"约好"到同一格交易，完全依赖 LLM 自发决策
**影响**：游戏内资源流通依赖采集，交易偶发

### 3. 世界状态无持久化

**表现**：服务器重启后世界重置到初始状态
**原因**：World 对象纯内存保存
**影响**：无法保存游戏进度

### 4. NPC 体力可归零但无惩罚

**表现**：体力耗尽后 NPC 继续正常行动
**原因**：`apply_passive` 只做数值检查，未实现体力耗尽的行动限制
**影响**：体力系统目前只是视觉反馈

### 5. 上帝 pending_commands 在玩家直接指令时被重复处理

**表现**：玩家发送 god_command → 追加到 `pending_commands` → `world_tick_loop` 处理直接执行 → 同时 `god_brain_loop` 读到并通知 LLM（可能导致上帝再次执行）
**原因**：直接指令通过 `world_tick_loop` 立即执行后，`pending_commands` 应该清空，但 `god_brain_loop` 也会在下次决策时读取（若 `pending_commands` 未及时清空）
**实际影响**：`world_tick_loop` 处理直接指令后会 `clear()` pending_commands，god_brain_loop 读到的 pending 应该已是空，但如果两者在同一 tick 内竞争，可能有微小概率重复

### 6. 无法指定 NPC 目标位置导航

**表现**：NPC 每次只能移动 1 格，无法记住要去某个目标并持续导航
**原因**：LLM 只决策单步动作，下一轮面对新上下文时可能忘记之前的移动意图
**影响**：NPC 的移动看起来随机或迟缓，长途跋涉效率低

### 7. 模型不稳定性

**表现**：偶发 API 超时或错误，通过 fallback 处理
**原因**：Gemini API 的网络不稳定，或模型处理时间偶发超长
**影响**：有 fallback 保护，不影响游戏整体运行

---

## 可以改进的地方

### 功能扩展

#### A. 持久化（存档/读档）
```
# 方向：将 World 序列化为 JSON 保存到文件
# 触发：每 N tick 自动保存，或玩家手动触发
import json, pickle
# world_state.json → create_world() 改为 load_world()
```

#### B. NPC 自主导航系统
```
# 方向：在 NPC 状态中增加 "target_pos" 字段
# LLM 不需要每次决策移动方向，只需决定目标格子
# 由代码层做 A* 或 BFS 寻路，自动执行移动
```

#### C. 交易协商系统（两轮握手）
```
# 当前：NPC 单方面发起 trade 并立即执行（要求对方恰好有货）
# 改进：
#   Tick N: Alice 发 trade_offer → 写入 Bob 的 inbox
#   Tick N+1: Bob 读到 offer → LLM 决策 accept/reject
#   Tick N+2: 执行或取消
# 这样交易更真实，成功率也更高
```

#### D. 更丰富的资源系统
```
# 食物系统：新增 food 资源（草地 farm），NPC 需要定期进食
# 建造：NPC 可以用资源在空地上建造小屋（给自己提供休息点）
# 工具：不同工具提升采集效率（弓/斧/镐）
```

#### E. NPC 社交关系系统
```
# 每个 NPC 维护对其他 NPC 的好感度（-100 到 100）
# 好感度影响 LLM 上下文中的描述
# 交易成功、帮助行为 → 增加好感
# 抢资源、拒绝交易 → 降低好感
```

#### F. 地图交互（玩家可编辑地图）
```
# 玩家可以直接修改格子类型（将草地变为森林等）
# 需要在 WebSocket 协议增加 "edit_tile" 消息类型
```

### 性能优化

#### G. 增量地图更新（减少带宽）
```
# 当前：每次广播发送全部 400 个格子（约 15KB/次）
# 改进：只发送本次 tick 变化的格子 delta
# 前端维护完整 tileMap，只更新收到的 delta 部分
```

#### H. NPC 对话记忆压缩
```
# 当前：保留最近 20 轮完整对话文本（随时间线性增长）
# 改进：每 N 轮让 LLM 生成一段摘要，替换旧历史
# 节省 prompt token，同时保留语义记忆
```

#### I. 流式输出（streaming）
```
# 当前：等待完整 JSON 响应（2-5秒延迟）
# 改进：使用 client.aio.models.generate_content_stream()
# 但结构化 JSON 输出目前不支持流式，需要改为无 schema 的自由格式+后处理
```

### 体验改进

#### J. 前端 NPC 路径轨迹可视化
```
# 在 Canvas 上显示 NPC 近几次移动的轨迹（淡化箭头）
# 让观察者更容易理解 NPC 的意图
```

#### K. NPC 对话历史面板
```
# 右侧面板增加选中 NPC 的完整对话历史查看
# 包括内心想法（thought 字段）
```

#### L. 上帝旁白历史
```
# 记录上帝的历史旁白，显示在日志中
# 让观察者了解上帝的干预意图
```

#### M. 游戏速度控制
```
# 前端增加速度滑块：0.5× / 1× / 2× 速度
# 后端 WORLD_TICK_SECONDS 可通过 WebSocket 消息动态调整
```

#### N. 多种 NPC 初始配置预设
```
# 内置几套不同的 NPC 性格组合
# 玩家可在启动时选择（如：和谐村庄 / 竞争市场 / 诗意世界）
```

---

*最后更新：2026-02-22 | 模型：gemini-2.5-flash | 运行时：Python 3.11 + FastAPI + Google Generative AI SDK 1.64.0*
