# 📡 API 参考

[← 返回主页](../README.md)

---

## 目录

- [REST API](#rest-api)
  - [GET /api/settings](#get-apisettings)
  - [POST /api/settings](#post-apisettings)
  - [GET /api/npc_profiles](#get-apinpc_profiles)
  - [PUT /api/npc_profiles/{npc_id}](#put-apinpc_profilesnpc_id)
  - [GET /api/npc_profiles/export](#get-apinpc_profilesexport)
  - [POST /api/npc_profiles/import](#post-apinpc_profilesimport)
  - [GET /api/market](#get-apimarket)
  - [GET /api/saves](#get-apisaves)
  - [POST /api/saves/delete](#post-apisavesdelete)
  - [POST /api/saves/delete_memory](#post-apisavesdelete_memory)
- [WebSocket 协议](#websocket-协议)
  - [连接](#连接)
  - [服务端 → 客户端：world_state](#服务端--客户端world_state)
  - [客户端 → 服务端：god_command](#客户端--服务端god_command)
  - [客户端 → 服务端：control](#客户端--服务端control)
  - [客户端 → 服务端：player_action](#客户端--服务端player_action)
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
  "local_llm_model":    "llama3",
  "show_npc_thoughts":  true,
  "npc_vision_radius":  2,
  "world_tick_seconds": 3.0,
  "npc_min_think":      5.0,
  "npc_max_think":      10.0,
  "god_min_think":      20.0,
  "god_max_think":      40.0,
  "npc_hearing_radius": 5,
  "food_energy_restore":  30,
  "sleep_energy_restore": 50,
  "exchange_rate_wood":   1,
  "exchange_rate_stone":  2,
  "exchange_rate_ore":    5,
  "food_cost_gold":       3,
  "player_name":        "玩家",
  "simulation_running": false
}
```

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
  "local_llm_model":    "qwen2.5:7b",
  "show_npc_thoughts":  false,
  "npc_vision_radius":  3,
  "world_tick_seconds": 2.0,
  "player_name":        "勇者"
}
```

**响应** `200 OK`

```json
{ "ok": true }
```

---

### GET /api/npc_profiles

返回所有 NPC 的完整档案列表。

**请求**

```
GET /api/npc_profiles
```

**响应** `200 OK`

```json
[
  {
    "npc_id":       "npc_he",
    "name":         "禾",
    "title":        "村里的妈妈",
    "backstory":    "村里的单亲妈妈，丈夫数年前去世...",
    "personality":  "温暖包容，保护女儿",
    "goals":        ["照顾穗", "维持日常生活"],
    "speech_style": "温柔关心，偶尔过度保护",
    "relationships": { "npc_sui": "母女", "npc_shi": "被暗恋" },
    "color":        "#E8A87C"
  }
]
```

---

### PUT /api/npc_profiles/{npc_id}

热更新单个 NPC 的档案，立即生效（无需重启）。

**请求**

```
PUT /api/npc_profiles/npc_he
Content-Type: application/json
```

```json
{
  "npc_id":    "npc_he",
  "name":      "禾",
  "title":     "村里的妈妈",
  "backstory": "村里的单亲妈妈，温暖地照顾着女儿穗...",
  "goals":     ["照顾穗", "维持日常"],
  "speech_style": "温柔关心"
}
```

**响应** `200 OK`

```json
{ "ok": true }
```

**错误响应** `404`

```json
{ "ok": false, "error": "NPC not found" }
```

---

### GET /api/npc_profiles/export

导出所有 NPC 档案为 JSON 数组，可保存为文件供后续导入。

**请求**

```
GET /api/npc_profiles/export
```

**响应** `200 OK`

返回 JSON 数组（与 `GET /api/npc_profiles` 格式相同），可直接保存为 `.json` 文件。

---

### POST /api/npc_profiles/import

从 JSON 数组批量导入并应用 NPC 档案。

**请求**

```
POST /api/npc_profiles/import
Content-Type: application/json
```

请求体为 NPC 档案数组（格式同导出）。只有 `npc_id` 匹配的 NPC 会被更新，不存在的 NPC 静默跳过。

**响应** `200 OK`

```json
{ "ok": true, "updated": ["npc_he", "npc_sui"] }
```

---

### GET /api/market

返回当前市场状态（实时浮动价格与价格历史）。

**请求**

```
GET /api/market
```

**响应** `200 OK`

```json
{
  "prices": {
    "wood":   { "base": 1.5, "current": 1.8, "min": 0.45, "max": 4.5, "trend": "up",   "change_pct": 20.0 },
    "stone":  { "base": 2.5, "current": 2.3, "min": 0.75, "max": 7.5, "trend": "down", "change_pct": -8.0 },
    "ore":    { "base": 6.0, "current": 6.1, "min": 1.8,  "max": 18.0, "trend": "stable", "change_pct": 1.7 },
    "food":   { "base": 3.0, "current": 4.2, "min": 0.9,  "max": 9.0,  "trend": "up",   "change_pct": 40.0 },
    "herb":   { "base": 4.0, "current": 3.5, "min": 1.2,  "max": 12.0, "trend": "down", "change_pct": -12.5 },
    "rope":   { "base": 4.0, "current": 4.0, "min": 1.2,  "max": 12.0, "trend": "stable", "change_pct": 0.0 },
    "potion": { "base": 10.0, "current": 10.5, "min": 3.0, "max": 30.0, "trend": "up", "change_pct": 5.0 },
    "tool":   { "base": 8.0, "current": 8.0,  "min": 2.4, "max": 24.0, "trend": "stable", "change_pct": 0.0 },
    "bread":  { "base": 6.0, "current": 5.8,  "min": 1.8, "max": 18.0, "trend": "down",  "change_pct": -3.3 }
  },
  "history": {
    "wood":  [1.5, 1.6, 1.7, 1.8],
    "food":  [3.0, 3.4, 3.9, 4.2]
  },
  "last_update_tick": 45
}
```

| 字段 | 说明 |
|------|------|
| `prices[item].base` | 基础参考价格 |
| `prices[item].current` | 当前浮动价格 |
| `prices[item].min/max` | 价格上下限 |
| `prices[item].trend` | `"up"` / `"down"` / `"stable"` |
| `prices[item].change_pct` | 相对基础价的变化百分比 |
| `history[item]` | 最近 30 次更新的历史价格（用于折线图） |
| `last_update_tick` | 上次价格更新的 tick 编号 |

---

### GET /api/saves

返回所有存档信息。

```
GET /api/saves
```

---

### POST /api/saves/delete

删除所有存档数据。

```
POST /api/saves/delete
```

---

### POST /api/saves/delete_memory

删除指定 NPC 的 RAG 记忆。

```
POST /api/saves/delete_memory
Content-Type: application/json

{ "npc_id": "npc_he" }
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
- 市场价格更新后

**消息结构**

```json
{
  "type": "world_state",
  "tick": 142,
  "simulation_running": true,
  "time": {
    "hour":     14.0,
    "day":      3,
    "phase":    "day",
    "time_str": "Day 3 14:00"
  },
  "weather": "sunny",
  "tiles":   [ ... ],
  "npcs":    [ ... ],
  "player":  { ... },
  "god":     { "commentary": "..." },
  "events":  [ ... ],
  "token_usage": { ... },
  "settings": { ... },
  "market":  { ... }
}
```

#### `tiles` 数组

每个地块只包含有意义的字段（草地且空的地块仍会输出以保持完整性）：

```json
[
  { "x": 10, "y": 10, "t": "o", "e": 1 },
  { "x": 3,  "y": 3,  "t": "r", "r": "s", "q": 8, "mq": 10 },
  { "x": 7,  "y": 7,  "t": "f", "r": "h", "q": 3, "mq": 5, "n": ["npc_he"] },
  { "x": 5,  "y": 5,  "t": "g", "p": 1 }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `x`, `y` | `int` | 坐标 |
| `t` | `string` | 地块类型编码（见[地块编码](#地块编码参考)） |
| `e` | `int` | `1` = 交易所地块 |
| `r` | `string` | 资源类型编码 |
| `q` | `int` | 当前资源数量 |
| `mq` | `int` | 资源上限 |
| `n` | `string[]` | NPC ID 列表 |
| `p` | `int` | `1` = 玩家在此格 |

#### `npcs` 数组

```json
[
  {
    "id":                "npc_he",
    "name":              "禾",
    "x":                 3,
    "y":                 3,
    "color":             "#E8A87C",
    "energy":            82,
    "inventory": {
      "wood": 3, "stone": 0, "ore": 1, "food": 2, "gold": 5,
      "herb": 2, "rope": 1, "potion": 0, "tool": 1, "bread": 0
    },
    "last_action":       "craft",
    "last_message":      "我做好工具了！",
    "last_message_tick": 140,
    "is_processing":     false,
    "active_tool":       true,
    "active_rope":       false,
    "pending_proposals": 1,
    "thought":           "应该去找 石 谈交易",
    "profile": {
      "title":         "铁匠",
      "backstory":     "从小在矿区长大...",
      "personality":   "沉默寡言",
      "goals":         ["积累50金", "制造工具"],
      "speech_style":  "简洁直接",
      "relationships": { "npc_shi": "竞争" }
    }
  }
]
```

| 新增字段 | 说明 |
|---------|------|
| `active_tool` | `bool` — 工具效果激活（采集 ×2） |
| `active_rope` | `bool` — 绳子效果激活（移动 -1 耗能） |
| `pending_proposals` | `int` — 待响应的交易提案数量 |
| `thought` | `string` — 内心想法（`SHOW_NPC_THOUGHTS=True` 时输出） |
| `profile` | `object` — NPC 档案摘要（有档案时输出） |

#### `player` 对象

```json
{
  "id":           "player",
  "name":         "玩家",
  "x":            12,
  "y":            12,
  "energy":       90,
  "is_god_mode":  false,
  "last_action":  "move",
  "last_message": "",
  "inventory": { "wood": 0, "stone": 0, "ore": 0, "food": 1, "gold": 0, ... },
  "inbox":        ["[142] 禾 说: 你好！"]
}
```

#### `market` 对象

```json
{
  "prices": {
    "wood":  { "base": 1.5, "current": 1.8, "min": 0.45, "max": 4.5, "trend": "up", "change_pct": 20.0 }
  },
  "history": {
    "wood": [1.5, 1.6, 1.7, 1.8]
  },
  "last_update_tick": 140
}
```

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

```json
{
  "type":          "god_command",
  "command":       "spawn_resource",
  "resource_type": "herb",
  "x":             8,
  "y":             12,
  "quantity":      5
}
```

`resource_type` 可选值：`"wood"` / `"stone"` / `"ore"` / `"food"` / `"herb"`

---

### 客户端 → 服务端：control

控制游戏运行状态。

#### 开始/暂停模拟

```json
{ "type": "control", "command": "toggle_sim" }
```

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

---

### 客户端 → 服务端：player_action

控制玩家角色行动。

#### 移动

```json
{
  "type":    "player_action",
  "action":  "move",
  "dx":      1,
  "dy":      0
}
```

#### 采集

```json
{ "type": "player_action", "action": "gather" }
```

#### 发言

```json
{
  "type":    "player_action",
  "action":  "talk",
  "message": "大家好！"
}
```

#### 吃食物

```json
{ "type": "player_action", "action": "eat" }
```

---

## NPC 动作 Schema

NPC 的每次决策必须返回符合以下结构的 JSON。

### 所有动作类型

| `action` | 描述 | 关键参数 |
|----------|------|---------|
| `move` | 移动 1 格 | `dx`, `dy`（各 -1/0/1） |
| `gather` | 采集当前格资源 | — |
| `talk` | 向附近 NPC 说话 | `message`, 可选 `target_id` |
| `interrupt` | 打断对话 | `message`, `target_id` |
| `trade` | 立即直接交换（相邻格） | `target_id`, `offer_item`, `offer_qty`, `request_item`, `request_qty` |
| `rest` | 休息（+20体力） | — |
| `sleep` | 睡眠（+50体力） | — |
| `eat` | 吃库存食物（+30体力） | — |
| `think` | 写个人笔记 | `note` |
| `exchange` | 在交易所卖资源（固定汇率） | `exchange_item`, 可选 `exchange_qty` |
| `buy_food` | 在交易所买食物（固定价） | 可选 `quantity` |
| `craft` | 制造物品 | `craft_item`（rope/potion/tool/bread） |
| `sell` | 按市场价卖出物品 | `sell_item`, `sell_qty` |
| `buy` | 按市场价买入物品 | `buy_item`, `buy_qty` |
| `use_item` | 使用物品激活效果 | `use_item`（potion/bread/tool/rope） |
| `propose_trade` | 向目标发出交易提案 | `target_id`, `offer_item`, `offer_qty`, `request_item`, `request_qty` |
| `accept_trade` | 接受待处理提案 | `proposal_from`（提案发起方 NPC ID） |
| `reject_trade` | 拒绝待处理提案 | `proposal_from` |
| `counter_trade` | 发出反提案 | `proposal_from`, `offer_item`, `offer_qty`, `request_item`, `request_qty` |

### 示例

```json
// 移动
{ "action": "move", "dx": 1, "dy": 0, "thought": "向右走，靠近交易所" }

// 说话
{ "action": "talk", "message": "石，你有多余的石头吗？我可以用草药换", "target_id": "npc_shi" }

// 制造工具
{ "action": "craft", "craft_item": "tool", "thought": "有足够的材料了，做把工具提高采集效率" }

// 按市场价卖出矿石
{ "action": "sell", "sell_item": "ore", "sell_qty": 2 }

// 激活工具
{ "action": "use_item", "use_item": "tool", "thought": "用工具采集更多资源" }

// 向 石 发出提案
{
  "action": "propose_trade",
  "target_id": "npc_shi",
  "offer_item": "herb", "offer_qty": 3,
  "request_item": "stone", "request_qty": 2
}

// 接受提案
{ "action": "accept_trade", "proposal_from": "npc_shi" }

// 反提案（调整条件）
{
  "action": "counter_trade",
  "proposal_from": "npc_lan",
  "offer_item": "wood", "offer_qty": 2,
  "request_item": "herb", "request_qty": 1
}

// 记录笔记
{ "action": "think", "note": "计划：先采草药→制药水→高价卖出" }
```

---

## 上帝动作 Schema

上帝每次决策返回以下格式：

```json
// 改变天气
{
  "action":      "set_weather",
  "weather":     "rainy",
  "commentary":  "降下甘霖，草药将会生长得更茂盛。"
}

// 刷新资源
{
  "action":        "spawn_resource",
  "resource_type": "herb",
  "x":             7,
  "y":             8,
  "quantity":      5,
  "commentary":    "在森林深处播撒草药种子，帮助有需要的人。"
}
```

---

## 地块编码参考

WebSocket 消息中使用单字母编码压缩地块信息：

### 地块类型（`"t"` 字段）

| 编码 | 类型 | 颜色 |
|------|------|------|
| `"g"` | 草地 `GRASS` | `#7ec850` |
| `"r"` | 岩石 `ROCK` | `#9e9e9e` |
| `"f"` | 森林 `FOREST` | `#3a7d44` |
| `"o"` | 城镇 `TOWN` | `#c8a87a` |

### 资源类型（`"r"` 字段）

| 编码 | 资源 | 图标 | 采集地块 |
|------|------|------|---------|
| `"w"` | 木头 `WOOD` | 🌲 | 森林 |
| `"s"` | 石头 `STONE` | 🪨 | 岩石 |
| `"o"` | 矿石 `ORE` | 💎 | 岩石（稀有） |
| `"f"` | 食物 `FOOD` | 🌾 | 草地/城镇附近 |
| `"h"` | 草药 `HERB` | 🌿 | 森林 |

### 特殊标记

| 字段 | 值 | 说明 |
|------|-----|------|
| `"e"` | `1` | 交易所地块（`is_exchange=True`） |
| `"p"` | `1` | 玩家位于此格 |

---

## 事件类型参考

不同事件类型的 `metadata` 字段：

| 事件类型 | 额外字段 | 示例 summary |
|---------|---------|-------------|
| `npc_spoke` | `message` | `"禾 说: \"你好！\""` |
| `npc_moved` | `from_x`, `from_y`, `to_x`, `to_y` | `"禾 从 (5,5) 移动到 (6,5)"` |
| `npc_gathered` | `item`, `qty` | `"石 采集了 1 个草药"` |
| `npc_traded` | `offer_item`, `offer_qty`, `request_item`, `request_qty`, `partner` | `"禾 和 石 交换：3木头 换 2石头"` |
| `npc_rested` | `energy_gain` | `"岚婆 休息，体力 +20"` |
| `npc_slept` | `energy_gain` | `"木 睡眠，体力 +50"` |
| `npc_ate` | `energy_gain` | `"禾 吃了食物，体力 +30"` |
| `npc_exchanged` | `item`, `qty`, `gold` | `"石 在交易所卖出 5 木头，获得 5 金币"` |
| `npc_bought_food` | `qty`, `gold_spent` | `"岚婆 花 3 金购买了 1 个食物"` |
| `npc_thought` | `note` | `"山 写下笔记"` |
| `npc_crafted` | `item` | `"木 制造了 tool"` |
| `npc_sold` | `item`, `qty`, `gold`, `price` | `"旷 按市价卖出 2 ore，获得 12 金"` |
| `npc_bought` | `item`, `qty`, `gold`, `price` | `"棠 按市价买入 1 potion，花费 10 金"` |
| `npc_used_item` | `item`, `effect` | `"山 使用了 tool，采集效率提升"` |
| `trade_proposed` | `from`, `to`, `offer`, `request` | `"禾 向 石 提出：3草药 换 2石头"` |
| `trade_accepted` | `from`, `to`, `offer`, `request` | `"石 接受了 禾 的提案，交易完成"` |
| `trade_rejected` | `from`, `to` | `"旷 拒绝了 棠 的提案"` |
| `trade_countered` | `from`, `to`, `new_offer`, `new_request` | `"禾 反提案：4草药 换 3石头"` |
| `market_updated` | `changes` | `"市场价格已更新"` |
| `weather_changed` | `weather` | `"天气变为 暴风雨"` |
| `resource_spawned` | `resource_type`, `x`, `y`, `qty` | `"God 在 (8,12) 刷新了 5 个草药"` |
| `resource_depleted` | `resource_type`, `x`, `y` | `"(3,3) 的石头资源已耗尽"` |
| `god_commentary` | `commentary` | `"God: 世界在我的注视下..."` |
