# 📡 API 参考

[← 返回主页](../README.md)

---

## 目录

- [REST API](#rest-api)
  - [GET /api/settings](#get-apisettings)
  - [POST /api/settings](#post-apisettings)
- [WebSocket 协议](#websocket-协议)
  - [连接](#连接)
  - [服务端 → 客户端：world_state](#服务端--客户端world_state)
  - [客户端 → 服务端：god_command](#客户端--服务端god_command)
  - [客户端 → 服务端：control](#客户端--服务端control)
- [NPC 动作 Schema](#npc-动作-schema)
- [上帝动作 Schema](#上帝动作-schema)
- [地块编码参考](#地块编码参考)
- [事件类型参考](#事件类型参考)

---

## REST API

### GET /api/settings

读取当前游戏配置。

**请求**

```
GET /api/settings
```

**响应** `200 OK`

```json
{
  "api_key_set":        true,
  "model_name":         "gemini-2.5-flash",
  "token_limit":        200000,
  "llm_provider":       "gemini",
  "local_llm_base_url": "http://localhost:11434/v1",
  "local_llm_model":    "llama3"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `api_key_set` | `bool` | Gemini API Key 是否已设置（不返回明文） |
| `model_name` | `string` | 当前使用的 Gemini 模型名 |
| `token_limit` | `int` | 当前 Token 会话限额 |
| `llm_provider` | `string` | `"gemini"` 或 `"local"` |
| `local_llm_base_url` | `string` | 本地 LLM 服务地址 |
| `local_llm_model` | `string` | 本地模型名称 |

---

### POST /api/settings

更新游戏配置，所有字段均为可选。变更立即热更新，无需重启服务器。

**请求**

```
POST /api/settings
Content-Type: application/json
```

```json
{
  "api_key":            "AIzaSy...",
  "model_name":         "gemini-2.0-flash",
  "token_limit":        300000,
  "llm_provider":       "local",
  "local_llm_base_url": "http://localhost:1234/v1",
  "local_llm_model":    "qwen2.5:7b"
}
```

| 字段 | 类型 | 效果 |
|------|------|------|
| `api_key` | `string` | 更新 Gemini API Key，重置所有 agent 的 client |
| `model_name` | `string` | 更新 Gemini 模型名（下次 LLM 调用生效） |
| `token_limit` | `int` | 更新 Token 限额，若当前用量低于新限额则自动恢复运行 |
| `llm_provider` | `string` | 切换 LLM 提供商（`"gemini"` 或 `"local"`） |
| `local_llm_base_url` | `string` | 更新本地服务地址，重置本地 client |
| `local_llm_model` | `string` | 更新本地模型名（下次调用生效） |

**响应** `200 OK`

```json
{ "ok": true }
```

**错误响应** `400 Bad Request`

```json
{ "ok": false, "error": "invalid JSON" }
```

---

## WebSocket 协议

### 连接

```
ws://localhost:8000/ws
```

连接建立后，服务端立即推送一次完整的世界快照（`world_state` 消息）作为初始状态。

---

### 服务端 → 客户端：world_state

在以下情况触发推送：
- 每个 World Tick（约每 3 秒）
- NPC 或上帝执行了动作（立即推送，含事件列表）
- 浏览器发送直接上帝指令后

**消息结构**

```json
{
  "type": "world_state",
  "tick": 142,
  "time": {
    "hour":     14.0,
    "day":      3,
    "phase":    "day",
    "time_str": "Day 3 14:00"
  },
  "weather": "sunny",
  "tiles":   [ ... ],
  "npcs":    [ ... ],
  "god":     { "commentary": "..." },
  "events":  [ ... ],
  "token_usage": { ... }
}
```

#### `time` 对象

| 字段 | 类型 | 值 |
|------|------|-----|
| `hour` | `float` | 当前小时（0.0–24.0） |
| `day` | `int` | 天数（从 1 开始） |
| `phase` | `string` | `morning` / `day` / `evening` / `night` |
| `time_str` | `string` | 格式化字符串，如 `"Day 3 14:00"` |

#### `weather` 字段

`"sunny"` / `"rainy"` / `"storm"`

#### `tiles` 数组

只包含**有内容的地块**（草地且无资源/NPC 的地块不输出，节省带宽）：

```json
[
  { "x": 10, "y": 10, "t": "o", "e": 1 },
  { "x": 3,  "y": 3,  "t": "r", "r": "s", "q": 8, "mq": 10 },
  { "x": 7,  "y": 7,  "t": "g", "r": "f", "q": 3, "mq": 5, "n": ["npc_alice"] }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `x`, `y` | `int` | 坐标 |
| `t` | `string` | 地块类型编码（见[地块编码](#地块编码参考)），草地省略 |
| `e` | `int` | `1` = 交易所地块（仅交易所输出此字段） |
| `r` | `string` | 资源类型编码（见[地块编码](#地块编码参考)） |
| `q` | `int` | 当前资源数量 |
| `mq` | `int` | 资源上限 |
| `n` | `string[]` | 当前格内的 NPC ID 列表 |

#### `npcs` 数组

```json
[
  {
    "id":               "npc_alice",
    "name":             "Alice",
    "x":                5,
    "y":                5,
    "color":            "#4CAF50",
    "energy":           82,
    "inventory": {
      "wood":  3,
      "stone": 0,
      "ore":   1,
      "food":  2,
      "gold":  5
    },
    "last_action":       "talk",
    "last_message":      "Bob，你有多余的石头吗？",
    "last_message_tick": 140,
    "is_processing":     false
  }
]
```

| 字段 | 说明 |
|------|------|
| `id` | NPC 唯一标识（如 `npc_alice`） |
| `name` | 显示名称 |
| `x`, `y` | 当前坐标 |
| `color` | 渲染颜色（十六进制） |
| `energy` | 当前体力（0–100） |
| `inventory` | 库存详情 |
| `last_action` | 上次动作类型 |
| `last_message` | 上次发言内容（用于气泡显示） |
| `last_message_tick` | 上次发言的 tick 编号（用于气泡超时计算） |
| `is_processing` | 是否正在等待 LLM 响应（前端显示旋转动画） |

#### `god` 对象

```json
{ "commentary": "世界在我的注视下缓缓运转..." }
```

#### `events` 数组

只包含本次推送**新发生**的事件（非历史事件）：

```json
[
  {
    "type":    "npc_spoke",
    "tick":    142,
    "actor":   "Alice",
    "summary": "Alice 说: \"你好！\"",
    "message": "你好！"
  },
  {
    "type":   "npc_exchanged",
    "tick":   142,
    "actor":  "Bob",
    "item":   "wood",
    "qty":    5,
    "gold":   5,
    "summary": "Bob 在交易所卖出 5 木头，获得 5 金币"
  },
  {
    "type":    "weather_changed",
    "tick":    140,
    "actor":   "God",
    "weather": "storm",
    "summary": "天气变为暴风雨"
  }
]
```

不同事件类型包含不同的 `metadata` 字段，详见[事件类型参考](#事件类型参考)。

#### `token_usage` 对象

```json
{
  "total_tokens_used": 45230,
  "prompt_tokens":     38000,
  "completion_tokens": 7230,
  "limit":             200000,
  "paused":            false,
  "usage_pct":         22.6,
  "per_agent": {
    "npcs": { "total": 40000, "prompt": 34000, "completion": 6000 },
    "god":  { "total": 5230,  "prompt": 4000,  "completion": 1230 }
  }
}
```

---

### 客户端 → 服务端：god_command

浏览器直接操作上帝能力（不经过 LLM，立即执行）。

#### 改变天气

```json
{
  "type":    "god_command",
  "command": "set_weather",
  "value":   "storm"
}
```

`value` 可选值：`"sunny"` / `"rainy"` / `"storm"`

#### 刷新资源

在指定坐标刷新资源（会叠加到现有资源上，不超过上限）：

```json
{
  "type":          "god_command",
  "command":       "spawn_resource",
  "resource_type": "food",
  "x":             8,
  "y":             12,
  "quantity":      5
}
```

`resource_type` 可选值：`"wood"` / `"stone"` / `"ore"` / `"food"`

---

### 客户端 → 服务端：control

控制游戏运行状态。

#### 暂停

```json
{ "type": "control", "command": "pause" }
```

#### 恢复运行

```json
{ "type": "control", "command": "resume" }
```

#### 更新 Token 限额

```json
{ "type": "control", "command": "set_limit", "value": 500000 }
```

#### 更新 API Key

```json
{ "type": "control", "command": "set_api_key", "value": "AIzaSy..." }
```

---

## NPC 动作 Schema

NPC 的每次决策必须返回符合以下结构的 JSON。

### 所有动作类型

| `action` | 描述 | 必填参数 | 可选参数 |
|----------|------|---------|---------|
| `move` | 移动 1 格 | `dx`, `dy`（各 -1/0/1） | `thought` |
| `gather` | 采集当前格资源 | — | `thought` |
| `talk` | 向附近 NPC 说话 | `message` | `target_id`, `thought` |
| `interrupt` | 打断对话 | `message`, `target_id` | — |
| `trade` | 与相邻 NPC 交易 | `target_id`, `offer_item`, `offer_qty`, `request_item`, `request_qty` | — |
| `rest` | 休息（+20体力） | — | `thought` |
| `sleep` | 睡眠（+50体力） | — | `thought` |
| `eat` | 吃库存食物（+30体力） | — | `thought` |
| `think` | 写个人笔记 | `note` | — |
| `exchange` | 在交易所卖资源 | `exchange_item` | `exchange_qty`（默认1） |
| `buy_food` | 在交易所买食物 | — | `quantity`（默认1） |

### 示例

```json
// 移动
{ "action": "move", "dx": 1, "dy": 0, "thought": "向右走，靠近交易所" }

// 说话
{ "action": "talk", "message": "Bob，你有多余的石头吗？我可以用木头换", "target_id": "npc_bob" }

// 交易（和 Bob 换石头）
{
  "action": "trade",
  "target_id": "npc_bob",
  "offer_item": "wood",  "offer_qty": 3,
  "request_item": "stone", "request_qty": 2
}

// 在交易所卖矿石
{ "action": "exchange", "exchange_item": "ore", "exchange_qty": 2 }

// 在交易所买食物
{ "action": "buy_food", "quantity": 1 }

// 睡眠
{ "action": "sleep", "thought": "体力太低了，休息一下" }

// 记录笔记
{ "action": "think", "note": "计划：先收集足够的木头，然后去交易所换金币买食物" }
```

---

## 上帝动作 Schema

上帝每次决策返回以下格式：

```json
// 改变天气
{
  "action":      "set_weather",
  "weather":     "rainy",
  "commentary":  "降下甘霖，滋润这片土地。"
}

// 刷新资源
{
  "action":        "spawn_resource",
  "resource_type": "food",
  "x":             10,
  "y":             8,
  "quantity":      5,
  "commentary":    "在城镇附近撒下食物，帮助饥饿的村民。"
}
```

| 字段 | 说明 |
|------|------|
| `action` | `"set_weather"` 或 `"spawn_resource"` |
| `weather` | `"sunny"` / `"rainy"` / `"storm"` |
| `resource_type` | `"wood"` / `"stone"` / `"ore"` / `"food"` |
| `x`, `y` | 资源刷新坐标（0–19） |
| `quantity` | 刷新数量 |
| `commentary` | 旁白文字，显示在前端 UI 中 |

---

## 地块编码参考

WebSocket 消息中使用单字母编码压缩地块信息：

### 地块类型（`"t"` 字段）

| 编码 | 类型 | 颜色 |
|------|------|------|
| 省略 | 草地 `GRASS` | `#7ec850` |
| `"r"` | 岩石 `ROCK` | `#9e9e9e` |
| `"f"` | 森林 `FOREST` | `#3a7d44` |
| `"o"` | 城镇 `TOWN` | `#c8a87a` |

### 资源类型（`"r"` 字段）

| 编码 | 资源 | 图标 |
|------|------|------|
| `"w"` | 木头 `WOOD` | 🌲 |
| `"s"` | 石头 `STONE` | 🪨 |
| `"o"` | 矿石 `ORE` | 💎 |
| `"f"` | 食物 `FOOD` | 🌾 |

### 特殊标记

| 字段 | 值 | 说明 |
|------|-----|------|
| `"e"` | `1` | 交易所地块（`is_exchange=True`） |

---

## 事件类型参考

不同事件类型的 `metadata` 字段：

| 事件类型 | 额外字段 | 示例 summary |
|---------|---------|-------------|
| `npc_spoke` | `message` | `"Alice 说: \"你好！\""` |
| `npc_moved` | `from_x`, `from_y`, `to_x`, `to_y` | `"Alice 从 (5,5) 移动到 (6,5)"` |
| `npc_gathered` | `item`, `qty` | `"Bob 采集了 1 个木头"` |
| `npc_traded` | `offer_item`, `offer_qty`, `request_item`, `request_qty`, `partner` | `"Alice 和 Bob 交换：3木头 换 2石头"` |
| `npc_rested` | `energy_gain` | `"Carol 休息，体力 +20"` |
| `npc_slept` | `energy_gain` | `"Dave 睡眠，体力 +50"` |
| `npc_ate` | `energy_gain` | `"Alice 吃了食物，体力 +30"` |
| `npc_exchanged` | `item`, `qty`, `gold` | `"Bob 在交易所卖出 5 木头，获得 5 金币"` |
| `npc_bought_food` | `qty`, `gold_spent` | `"Carol 花 3 金购买了 1 个食物"` |
| `npc_thought` | `note` | `"Dave 写下笔记"` |
| `weather_changed` | `weather` | `"天气变为 暴风雨"` |
| `resource_spawned` | `resource_type`, `x`, `y`, `qty` | `"God 在 (8,12) 刷新了 5 个食物"` |
| `resource_depleted` | `resource_type`, `x`, `y` | `"(3,3) 的石头资源已耗尽"` |
| `god_commentary` | `commentary` | `"God: 世界在我的注视下..."` |