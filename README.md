# AgentHome — LLM 驱动的 AI 沙盒世界

> 一个 2D 沙盒游戏：4 个 NPC + 1 个上帝，每个角色由 Google Gemini 独立控制，具有独立记忆、实时对话、资源交互、食物系统和城镇交易所。通过浏览器可视化。

---

## 目录

- [快速启动](#快速启动)
- [完整启动流程](#完整启动流程)
- [项目结构](#项目结构)
- [整体架构设计](#整体架构设计)
- [新功能概览（v2）](#新功能概览v2)
- [模块详解](#模块详解)
- [WebSocket 协议](#websocket-协议)
- [REST API](#rest-api)
- [NPC 动作 Schema](#npc-动作-schema)
- [上帝动作 Schema](#上帝动作-schema)
- [Token 用量管理](#token-用量管理)
- [目前存在的问题](#目前存在的问题)
- [可以改进的地方](#可以改进的地方)

---

## 快速启动

**前提**：Python 3.11+，已安装依赖。API Key 可通过 `.env` 文件或网页设置面板设置。

```bash
cd d:\data\code\github\agenthome

# 使用项目所在 conda 环境
/d/program/codesupport/anaconda/envs/agent/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000

# 浏览器访问
# http://localhost:8000
```

如果是第一次启动或 API Key 未在 `.env` 中配置，打开浏览器后进入 **⚙ 设置** 标签页，输入 Gemini API Key 并保存。

---

## 完整启动流程

### 1. 创建 `.env` 文件（可选，也可在网页 UI 中设置）

```
GEMINI_API_KEY=AIzaSy...你的key...
GEMINI_MODEL=gemini-2.5-flash
```

### 2. 安装依赖

```bash
/d/program/codesupport/anaconda/envs/agent/python.exe -m pip install -r requirements.txt
```

### 3. 启动服务器

```bash
/d/program/codesupport/anaconda/envs/agent/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问 UI

打开 `http://localhost:8000`，游戏自动开始。

### 5. 关闭服务器

在终端按 `Ctrl+C`。**每次测试后请确认关闭进程**，否则端口 8000 会被占用。

---

## 项目结构

```
agenthome/
├── main.py                  # FastAPI 入口（WebSocket + REST API）
├── config.py                # 所有常量（世界大小、计时、汇率、能量等）
├── requirements.txt
├── .env                     # API Key（可选，也可在 UI 中设置）
│
├── engine/
│   ├── world.py             # 数据模型（Tile, NPC, Inventory, World, 世界生成）
│   └── world_manager.py     # 世界状态变更（所有动作处理）
│
├── agents/
│   ├── base_agent.py        # Gemini API 调用基类（懒加载 client，热更新 Key）
│   ├── npc_agent.py         # NPC 决策循环
│   ├── god_agent.py         # 上帝决策循环
│   └── prompts.py           # 提示词模板 + Pydantic 动作 Schema
│
├── game/
│   ├── loop.py              # 主异步游戏循环（各 agent 独立 brain loop）
│   ├── events.py            # 事件类型、WorldEvent、EventBus
│   └── token_tracker.py     # Token 统计、限额控制
│
├── ws/
│   ├── manager.py           # WebSocket 连接池 + 广播
│   └── serializer.py        # World → JSON（紧凑格式）
│
└── frontend/
    └── index.html           # 单文件前端（Canvas + 标签面板 + 聊天日志）
```

---

## 整体架构设计

### 异步并发模型

```
uvicorn
└── FastAPI 事件循环
    ├── WebSocket /ws      ← 浏览器连接
    ├── GET  /api/settings ← 读取当前配置
    ├── POST /api/settings ← 更新配置（API Key、模型、限额）
    └── GameLoop.start()
        ├── _world_tick_loop()    每 3s: 时间推进、被动效果、直接上帝指令、广播
        ├── _npc_brain_loop(Alice) 独立循环：LLM → 动作 → 广播
        ├── _npc_brain_loop(Bob)
        ├── _npc_brain_loop(Carol)
        ├── _npc_brain_loop(Dave)
        └── _god_brain_loop()    独立循环：LLM → 动作 → 广播
```

- 所有 LLM 调用与 world tick 完全异步分离
- `asyncio.Lock` 保护所有世界状态修改
- NPC brain loop 启动随机错开 1-4 秒，避免同时发 API 请求

### 事件系统

```
动作执行 → 生成 WorldEvent → EventBus.dispatch()
                              ├── world.recent_events（全局日志）
                              └── NPC.memory.inbox（邻近过滤，曼哈顿距离）
```

---

## 新功能概览（v2）

### 1. 食物系统
- 地图草地上随机分布 10 处食物灌木丛（🌾），可直接采集
- 新动作 `eat`：消耗库存 1 个食物，回复 30 点体力
- 新动作 `sleep`：回复 50 点体力（无需消耗资源）
- 被动机制：体力归零时，若库存有食物则自动吃一个

### 2. 城镇与交易所
- 中央区域（原湖泊）改为 3×3 城镇地块（棕色）
- 城镇中心 `(10,10)` 为交易所（🏛），可：
  - `exchange`：卖资源换金币（木头=1金，石头=2金，矿石=5金）
  - `buy_food`：花 3 金购买 1 个食物
- NPC 库存新增 `food`（食物）和 `gold`（金币）字段

### 3. 网页设置面板
- 右侧面板新增 **⚙ 设置** 标签页
- 可在网页中输入 Gemini API Key（密码框，支持显示/隐藏）
- 选择模型（gemini-2.5-flash / 2.0-flash / 1.5-flash / 1.5-pro）
- 滑块调整 Token 上限
- 设置立即生效（热更新，无需重启服务器）

### 4. 更好的可视化 UI
- 深色主题，三标签右侧面板（上帝控制 / NPC 列表 / 设置）
- 地块颜色：草地绿、岩石灰、森林深绿、城镇棕、交易所金
- NPC 渲染：彩色填充圆 + 能量弧 + 说话气泡 + 处理中动画
- 资源 emoji 图标：🌲🪨💎🌾
- 雨天/暴风粒子动画

---

## 模块详解

### `config.py`

所有游戏常量，修改此文件即可调整游戏参数，无需改代码。

| 常量 | 默认值 | 说明 |
|------|-------|------|
| `WORLD_TICK_SECONDS` | 3.0 | 世界时间推进间隔（秒） |
| `NPC_MIN/MAX_THINK_SECONDS` | 5/10 | NPC 决策间隔范围 |
| `GOD_MIN/MAX_THINK_SECONDS` | 20/40 | 上帝决策间隔范围 |
| `DEFAULT_TOKEN_LIMIT` | 200,000 | 会话 Token 上限 |
| `EXCHANGE_RATE_WOOD/STONE/ORE` | 1/2/5 | 各资源兑换金币汇率 |
| `FOOD_COST_GOLD` | 3 | 交易所购买1个食物的金币价格 |
| `FOOD_ENERGY_RESTORE` | 30 | 吃一个食物回复的体力 |
| `SLEEP_ENERGY_RESTORE` | 50 | 睡眠回复的体力 |
| `EXCHANGE_X/Y` | 10/10 | 交易所坐标 |

---

### `engine/world.py`

**数据类型定义 + 世界生成**

#### 枚举类型
- `TileType`: `GRASS / WATER / ROCK / FOREST / TOWN`
- `WeatherType`: `SUNNY / RAINY / STORM`
- `ResourceType`: `WOOD / STONE / ORE / FOOD`

#### `Tile` 字段
- `x, y`: 坐标
- `tile_type`: 地块类型
- `resource`: 可选 `Resource`（资源类型、数量、上限）
- `npc_ids`: 当前在此格的 NPC ID 列表
- `is_exchange`: 是否是交易所地块（布尔）

#### `Inventory` 字段
- `wood, stone, ore, food, gold`: 各资源/货币数量
- `get(item)` / `set(item, value)`: 按名称读写（安全，最小值为 0）

#### `NPC` 字段
- `npc_id, name, x, y, color`: 基本信息
- `personality`: 个性描述（注入提示词）
- `inventory`: `Inventory` 实例
- `memory`: `AgentMemory`（对话历史、笔记、收件箱）
- `energy`: 体力 0-100
- `last_action, last_message, last_message_tick`: 用于前端显示

#### `create_world(seed=42)`
- 生成固定种子的 20×20 世界
- 四角岩石簇（带石头/矿石资源）
- 8 处森林（带木头资源，避开城镇区域）
- 中心城镇（3×3，`(10,10)` 标记交易所）
- 草地上随机 10 处食物灌木丛
- 4 个 NPC 初始在 `(5,5),(14,5),(5,14),(14,14)`

---

### `engine/world_manager.py`

**所有世界状态变更逻辑**

#### `apply_passive(world)`
每 tick 调用：
- 按时间段和天气扣除 NPC 体力
- 体力归零且有食物时自动吃食物
- 每 10 tick 资源再生（雨天 +2，其他 +1）
- 每 15 tick 食物再生 +1

#### `apply_npc_action(npc, action, world)`
路由到对应处理方法：

| 动作 | 方法 | 效果 |
|------|------|------|
| `move` | `_do_move` | 移动 1 格（不能进水域），消耗 2-3 体力 |
| `gather` | `_do_gather` | 采集当前格资源（含食物），消耗 5 体力 |
| `talk/interrupt` | `_do_talk` | 发送消息到附近 NPC 收件箱 |
| `trade` | `_do_trade` | 相邻 NPC 间交换物品（包含 food/gold） |
| `rest` | 直接处理 | +20 体力 |
| `sleep` | `_do_sleep` | +50 体力，发事件 |
| `eat` | `_do_eat` | 消耗库存 1 食物，+30 体力 |
| `exchange` | `_do_exchange` | 在交易所将资源换金币 |
| `buy_food` | `_do_buy_food` | 在交易所花金币买食物 |
| `think` | 直接处理 | 写入 `personal_notes` |

**交易所检查**：`exchange` 和 `buy_food` 要求站在 `is_exchange=True` 的地块，否则无效。

#### `apply_god_action(action, world)` / `apply_direct_god_command(cmd, world)`
- 改变天气 / 刷新资源（`food` 类型也支持）
- 直接指令来自浏览器 UI（无 LLM）

---

### `game/events.py`

#### 事件类型 `EventType`
```
npc_spoke, npc_moved, npc_gathered, npc_traded,
npc_rested, npc_thought, npc_ate, npc_slept,
npc_exchanged, npc_bought_food,
weather_changed, resource_spawned, resource_depleted,
time_advanced, god_commentary
```

#### `EventBus.dispatch(event, world)`
- 将事件加入 `world.recent_events`（最多 30 条）
- 按曼哈顿距离 `<= event.radius` 分发到 NPC 收件箱
- 全局事件（无 origin_x/y）发给所有 NPC

---

### `game/token_tracker.py`

**异步安全的 Token 计数器**

- `record(agent_id, usage_metadata)`：从 Gemini 响应读取 token 数，累计到总计和 per-agent
- `snapshot()`：返回完整状态 dict（用于 WS 广播）
- `set_limit(n)` / `resume()`：动态调整限额并恢复
- 超过 `session_limit` 时自动设置 `paused=True`，游戏循环暂停 LLM 调用

---

### `game/loop.py`

**核心游戏调度**

#### `GameLoop.__init__()`
创建所有组件：world, event_bus, world_manager, token_tracker, ws_manager, serializer, npc_agent, god_agent, 以及 `asyncio.Lock`。

#### `start()`
同时启动 6 个 asyncio task：世界 tick + 4 个 NPC brain + 1 个 God brain。

#### `_world_tick_loop()`
- 每 3s：`world.time.advance()` + `apply_passive()`
- 处理积压的直接上帝指令
- 广播世界快照

#### `_npc_brain_loop(npc)`
- 随机错开启动（1-4s）
- 调用 `npc_agent.process()` → 获取动作
- 加锁后 `apply_npc_action()` → 事件广播
- talk 动作后等待 3-6s（让对话有节奏）；其他动作等 5-10s

#### `update_api_key(new_key)`
热更新所有 agent 的 API Key（无需重启）。

#### `handle_control(cmd)`
处理 WS 控制命令：`pause / resume / set_limit / set_api_key`。

---

### `agents/prompts.py`

#### `NPCAction` Pydantic Schema
```python
action: str  # move|gather|talk|trade|rest|think|interrupt|eat|sleep|exchange|buy_food
dx, dy: int            # move
thought: str           # move/gather/rest/eat/sleep
message: str           # talk/interrupt
target_id: str         # talk/interrupt/trade
offer_item, offer_qty  # trade
request_item, request_qty  # trade
note: str              # think
exchange_item, exchange_qty  # exchange
quantity: int          # buy_food
```

#### `GodAction` Pydantic Schema
```python
action: str  # set_weather|spawn_resource
weather: str         # sunny|rainy|storm
resource_type: str   # wood|stone|ore|food
x, y: int
quantity: int
commentary: str
```

#### `build_npc_system_prompt(npc, world)`
注入：名字、性格、世界大小、交易所坐标、完整动作格式说明。

#### `build_npc_context(npc, world)`
返回 `(context_str, is_social)`：
- **社交模式**（有附近 NPC 或有收件箱）：附近 NPC 状态（含 food/gold）+ 收件箱 + 近期事件
- **独思模式**：个人笔记 + 近期事件
- 站在交易所时额外提示可用 exchange/buy_food

---

### `agents/base_agent.py`

**Gemini API 调用基类**

- `_api_key`：当前 API Key（支持热更新）
- `_client`：懒加载，首次调用时创建，key 更新后自动重建
- `_get_client()`：返回（或创建）Gemini client
- `update_api_key(new_key)`：热更新 key，下次调用生效
- `call_llm(system_prompt, context_message, history, response_schema)`：
  - 构建 `contents`（历史 + 当前 context）
  - 使用 `response_mime_type="application/json"` + `response_schema=Pydantic模型` 强制结构化输出
  - 记录 token 到 `token_tracker`
  - 异常时返回 `None`

---

### `agents/npc_agent.py`

**NPC 决策代理**

- `process(npc, world)`：
  1. `is_processing` 防重入
  2. 调用 `call_llm` 获取 `NPCAction`
  3. 失败时使用 fallback（rest/move）
  4. 存入对话历史，清空收件箱
  5. 返回 action dict

---

### `agents/god_agent.py`

**上帝决策代理**

- `process(god, world)`：类似 NPC，返回 `GodAction` dict 或 None
- 每次决策后清空 `god.pending_commands`

---

### `ws/manager.py`

**WebSocket 连接池**

- `connect(ws)` / `disconnect(ws)`：连接管理
- `broadcast(data)`：并发发送给所有客户端，自动清理断连
- `send_to(ws, data)`：单播

---

### `ws/serializer.py`

**World → JSON（紧凑格式）**

#### 地块编码
- `"t"`: `g`=草地, `r`=岩石, `f`=森林, `o`=城镇, `w`=水域
- `"r"`: `w`=木头, `s`=石头, `o`=矿石, `f`=食物
- `"e": 1`：交易所地块标记
- `"q"`, `"mq"`：资源数量/上限
- `"n"`：此格的 NPC ID 列表

#### NPC 序列化
```json
{
  "id": "npc_alice",
  "name": "Alice",
  "x": 5, "y": 5,
  "color": "#4CAF50",
  "energy": 82,
  "inventory": { "wood": 3, "stone": 0, "ore": 1, "food": 2, "gold": 5 },
  "last_action": "talk",
  "last_message": "Bob，你有多余的石头吗？",
  "last_message_tick": 42,
  "is_processing": false
}
```

---

### `main.py`

**FastAPI 应用入口**

- `GET /`：返回 `frontend/index.html`
- `GET /static/*`：前端静态资源
- `GET /api/settings`：返回 `{api_key_set, model_name, token_limit}`
- `POST /api/settings`：更新 API key / 模型 / Token 限额（热更新）
- `WS /ws`：WebSocket 端点，处理 `god_command`、`control` 消息
- `@startup`：创建 `game_loop.start()` task

---

## WebSocket 协议

### 服务端 → 前端（每 tick 或有动作时）

```json
{
  "type": "world_state",
  "tick": 142,
  "time": { "hour": 14.0, "day": 3, "phase": "day", "time_str": "Day 3 14:00" },
  "weather": "sunny",
  "tiles": [
    { "x":10, "y":10, "t":"o", "e":1 },
    { "x":3, "y":3, "t":"r", "r":"s", "q":8, "mq":10 },
    { "x":7, "y":7, "t":"g", "r":"f", "q":3, "mq":5 }
  ],
  "npcs": [
    {
      "id":"npc_alice","name":"Alice","x":5,"y":5,"color":"#4CAF50","energy":82,
      "inventory":{"wood":3,"stone":0,"ore":1,"food":2,"gold":5},
      "last_action":"talk","last_message":"你好！","last_message_tick":140,"is_processing":false
    }
  ],
  "god": { "commentary": "世界在我的注视下缓缓运转..." },
  "events": [
    { "type":"npc_spoke","tick":142,"actor":"Alice","summary":"Alice: \"你好！\"","message":"你好！" },
    { "type":"npc_exchanged","tick":142,"actor":"Bob","item":"wood","qty":5,"gold":5 }
  ],
  "token_usage": {
    "total_tokens_used": 45230, "limit": 200000, "paused": false, "usage_pct": 22.6,
    "per_agent": { "npcs": {"total":40000}, "god": {"total":5230} }
  }
}
```

### 前端 → 服务端

```json
// 天气控制
{ "type":"god_command", "command":"set_weather", "value":"storm" }

// 刷新资源
{ "type":"god_command", "command":"spawn_resource", "resource_type":"food", "x":8, "y":12, "quantity":5 }

// 游戏控制
{ "type":"control", "command":"pause" }
{ "type":"control", "command":"resume" }
{ "type":"control", "command":"set_limit", "value":500000 }
{ "type":"control", "command":"set_api_key", "value":"AIzaSy..." }
```

---

## REST API

### `GET /api/settings`

响应：
```json
{ "api_key_set": true, "model_name": "gemini-2.5-flash", "token_limit": 200000 }
```

### `POST /api/settings`

请求体：
```json
{
  "api_key": "AIzaSy...",     // 可选，设置则热更新所有 agent
  "model_name": "gemini-2.5-flash",  // 可选
  "token_limit": 300000       // 可选
}
```

响应：
```json
{ "ok": true }
```

---

## NPC 动作 Schema

```
move        dx, dy (-1/0/1), thought
gather      thought（采集当前格资源，含食物）
talk        message (1-2句), target_id (可选)
interrupt   message, target_id
trade       target_id, offer_item, offer_qty, request_item, request_qty
            (支持 wood/stone/ore/food/gold 的任意组合)
rest        thought（+20体力）
sleep       thought（+50体力）
eat         thought（消耗1食物，+30体力）
think       note（写入个人笔记）
exchange    exchange_item (wood/stone/ore), exchange_qty（在交易所换金币）
buy_food    quantity（在交易所花金币买食物）
```

---

## 上帝动作 Schema

```
set_weather    weather (sunny/rainy/storm), commentary
spawn_resource resource_type (wood/stone/ore/food), x, y, quantity, commentary
```

---

## Token 用量管理

- 默认限额：200,000 tokens/会话
- 每次 LLM 调用后从 `response.usage_metadata` 读取并累计
- 超过限额 → `paused=True` → 前端显示暂停遮罩 → 可输入新限额恢复
- **估算**：
  - gemini-2.5-flash 约 1,000 tokens/NPC/决策
  - 5 个 agent，每 5-10s 决策一次，200k tokens ≈ 30-60 分钟游戏时间

---

## 目前存在的问题

1. **NPC 路径规划缺失**：只能单步移动，无法规划前往交易所的路径，需要多步移动
2. **交易所吸引力有限**：NPC 需要知道交易所位置并主动导航（依赖 LLM 规划）
3. **交易协商单边**：`trade` 动作是单边发起，对方不能"拒绝"（直接生效或失败）
4. **LLM 输出不确定性**：偶尔 JSON parse 失败，fallback 为 rest/move
5. **Token 计数仅统计 Gemini 报告数**：与实际计费可能有差异
6. **并发写入**：`asyncio.Lock` 保护，但高负载下可能出现轻微状态不一致
7. **无持久化**：重启后世界状态重置
8. **食物再生较慢**：食物丛每 15 tick +1，NPC 可能供不应求

---

## 可以改进的地方

1. **A\* 寻路**：让 NPC 能规划路径前往目标地块（交易所、资源点、其他 NPC）
2. **NPC 职业分工**：给每个 NPC 初始金币/资源，形成专业分工
3. **更多城镇建筑**：市场、旅馆、仓库等
4. **玩家角色**：加入可由玩家直接控制的角色
5. **存档系统**：将世界状态序列化到 JSON 文件
6. **多世界/房间**：支持多个独立的沙盒世界并行运行
7. **NPC 死亡与重生**：体力归零的惩罚机制
8. **LLM 对话历史优化**：用摘要代替原始历史，节省 token
9. **前端地图缩放**：支持放大缩小地图
10. **NPC 说话时语音合成**：集成 TTS 输出
