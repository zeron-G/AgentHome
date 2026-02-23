# 🏘️ AgentHome — LLM 驱动的 AI 沙盒世界

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-✓-4285F4?style=flat-square&logo=google&logoColor=white)
![Local LLM](https://img.shields.io/badge/Local_LLM-Ollama_/_LM_Studio-F97316?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)

**一个 2D 沙盒 AI 世界：4 个 NPC + 1 个上帝，每个角色由大语言模型独立控制。**
NPC 自主决策、互相交谈、采集资源、在城镇交易所买卖，一切实时呈现于浏览器。

[快速启动](#-快速启动) · [功能特性](#-功能特性) · [本地模型](#-本地-llm-支持) · [架构设计](#-架构设计) · [开发参考](#-开发参考)

</div>

---

## ✨ 功能特性

| 类别 | 特性 |
|------|------|
| 🤖 **AI 控制** | 4 NPC + 1 上帝，各有独立记忆与个性，每 5-10s 自主决策 |
| 🌐 **双 LLM 后端** | Google Gemini（云端）或任意 OpenAI 兼容本地服务器 |
| 🏘️ **城镇与交易所** | 中央城镇 + 交易所：卖资源换金币、花金币买食物 |
| 🌾 **食物系统** | 食物灌木丛、吃食物/睡眠回血、体力归零自动进食 |
| ⚡ **实时可视化** | WebSocket 驱动，Canvas 渲染地块/NPC/气泡/天气粒子 |
| 🎮 **上帝控制** | 浏览器界面直接控制天气、刷新资源 |
| ⚙️ **网页设置** | API Key、模型、Token 限额、LLM 提供商，热更新无需重启 |
| 📊 **Token 追踪** | 实时进度条，超限自动暂停，可动态扩额续跑 |

---

## 🚀 快速启动

### 前提条件

- Python **3.11+**
- Google Gemini API Key（使用云端）或本地 LLM 服务（Ollama / LM Studio / llama.cpp 等）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置（可选）

创建 `.env` 文件（也可在启动后通过网页设置面板配置）：

```bash
# Gemini 云端（默认）
GEMINI_API_KEY=AIzaSy...your_key...
GEMINI_MODEL=gemini-2.5-flash

# 或者使用本地模型
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1   # Ollama / LM Studio
LOCAL_LLM_MODEL=llama3
```

### 启动服务器

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

然后打开浏览器访问 **http://localhost:8000** ，游戏自动开始。

> **首次使用提示**：若未在 `.env` 中配置，点击右侧 **⚙ 设置** 标签页，输入 API Key 或配置本地模型后保存即可。

---

## 🖥️ 本地 LLM 支持

AgentHome 支持任意 **OpenAI 兼容**接口的本地模型服务，无需 API Key，完全本地运行。

### 支持的服务

| 服务 | Base URL | 说明 |
|------|----------|------|
| **Ollama** | `http://localhost:11434/v1` | 最易上手，`ollama pull llama3` 即可 |
| **LM Studio** | `http://localhost:1234/v1` | 图形界面，适合新手 |
| **llama.cpp server** | `http://localhost:8080/v1` | 轻量，适合低配设备 |
| **vLLM** | `http://localhost:8000/v1` | 高性能，适合 GPU 服务器 |

### 模型要求

> ⚠️ 本地模型**必须支持 `response_format: json_object`（JSON 模式）**，否则 NPC 决策可能解析失败。

推荐模型（支持 JSON 输出的指令微调模型）：

- `llama3`、`llama3.1`、`llama3.2` — 综合能力强
- `qwen2.5`、`qwen2.5-coder` — 中英文双语，JSON 合规性好
- `mistral-nemo`、`mixtral:8x7b` — 推理能力强
- `deepseek-r1:14b` — 推理型，适合复杂决策

### 快速切换

在浏览器 **⚙ 设置** 标签页点击 `🖥 本地模型` 按钮，填入 Base URL 和模型名称后保存，切换立即生效，无需重启服务器。

---

## 🗺️ 项目结构

```
agenthome/
├── main.py                  # FastAPI 入口（WebSocket + REST API）
├── config.py                # 所有常量（世界参数、汇率、能量、LLM 配置）
├── requirements.txt         # 依赖（fastapi, google-genai, openai, pydantic…）
├── .env                     # 密钥与本地配置（可选）
│
├── engine/
│   ├── world.py             # 数据模型（Tile、NPC、Inventory、World、世界生成）
│   └── world_manager.py     # 世界状态变更（所有动作处理器）
│
├── agents/
│   ├── base_agent.py        # LLM 基类（Gemini / 本地 OpenAI 兼容，懒加载，热更新）
│   ├── npc_agent.py         # NPC 决策代理
│   ├── god_agent.py         # 上帝决策代理
│   └── prompts.py           # 提示词模板 + Pydantic 动作 Schema
│
├── game/
│   ├── loop.py              # 异步游戏主循环（独立 brain loop）
│   ├── events.py            # 事件类型、WorldEvent、EventBus
│   └── token_tracker.py     # Token 统计与限额控制
│
├── ws/
│   ├── manager.py           # WebSocket 连接池 + 广播
│   └── serializer.py        # World → 紧凑 JSON
│
└── frontend/
    └── index.html           # 单文件前端（Canvas + 3 标签面板 + 聊天日志）
```

---

## 🏗️ 架构设计

### 异步并发模型

```
uvicorn (asyncio 事件循环)
├── WebSocket /ws              ← 浏览器实时连接
├── GET  /api/settings         ← 读取当前配置
├── POST /api/settings         ← 热更新（API Key / 模型 / 限额 / LLM 提供商）
└── GameLoop
    ├── _world_tick_loop()     每 3s: 时间推进 → 被动效果 → 广播快照
    ├── _npc_brain_loop(Alice) 独立循环: LLM决策 → 动作 → 事件 → 广播
    ├── _npc_brain_loop(Bob)
    ├── _npc_brain_loop(Carol)
    ├── _npc_brain_loop(Dave)
    └── _god_brain_loop()      独立循环: LLM观察 → 干预 → 广播
```

- 所有 LLM 调用与世界 tick **完全异步分离**
- `asyncio.Lock` 保护所有世界状态写入
- NPC brain loop 随机错开 1-4 秒启动，避免 API 请求并发峰值

### LLM 双后端调度

```
call_llm()
    ├── config.LLM_PROVIDER == "local"
    │       └── _call_local()
    │               ├── 将 JSON Schema 追加到 system prompt
    │               ├── response_format: {"type": "json_object"}
    │               ├── 剥离 markdown 代码围栏
    │               └── 记录 token（prompt_tokens / completion_tokens）
    └── config.LLM_PROVIDER == "gemini" (默认)
            └── _call_gemini()
                    ├── response_schema=Pydantic模型（结构化输出）
                    └── 记录 token（usage_metadata）
```

### 事件系统

```
动作执行 → WorldEvent 生成 → EventBus.dispatch()
                                  ├── world.recent_events（最多 30 条，全局日志）
                                  └── NPC.memory.inbox（按曼哈顿距离过滤，NPC 下次决策时读取）
```

---

## 🌍 世界设定

### 地图（20 × 20 格）

| 地块类型 | 颜色 | 说明 |
|---------|------|------|
| 草地 🌿 | 绿色 | 可通行，可能有食物灌木丛 |
| 岩石 ⛰️ | 灰色 | 有石头/矿石资源，阻挡移动 |
| 森林 🌲 | 深绿 | 有木头资源，可通行 |
| 城镇 🏘️ | 棕色 | 中央 3×3 区域，可通行 |
| 交易所 🏛️ | 金色 | 城镇中心 `(10,10)`，可买卖资源 |

### NPC 库存

每个 NPC 持有：`wood`（木头）、`stone`（石头）、`ore`（矿石）、`food`（食物）、`gold`（金币）

### 交易所汇率

| 资源 | 卖出价格 | 买入 |
|------|----------|------|
| 木头 🪵 | 1 金/个 | — |
| 石头 🪨 | 2 金/个 | — |
| 矿石 💎 | 5 金/个 | — |
| 食物 🌾 | — | 3 金/个 |

---

## 📋 开发参考

### NPC 动作 Schema

| 动作 | 关键参数 | 效果 |
|------|---------|------|
| `move` | `dx, dy`（-1/0/1），`thought` | 移动 1 格，消耗 2-3 体力 |
| `gather` | `thought` | 采集当前格资源（含食物），消耗 5 体力 |
| `talk` | `message`，`target_id`（可选） | 发送消息，附近 NPC 收到 |
| `interrupt` | `message`，`target_id` | 打断对话 |
| `trade` | `target_id`，`offer_item/qty`，`request_item/qty` | 与相邻 NPC 交换物品 |
| `rest` | `thought` | 回复 20 体力 |
| `sleep` | `thought` | 回复 50 体力 |
| `eat` | `thought` | 消耗 1 食物，回复 30 体力 |
| `think` | `note` | 写入个人笔记 |
| `exchange` | `exchange_item`，`exchange_qty` | 在交易所卖资源换金币 |
| `buy_food` | `quantity` | 在交易所花金币买食物 |

### 上帝动作 Schema

| 动作 | 参数 | 效果 |
|------|------|------|
| `set_weather` | `weather`（sunny/rainy/storm），`commentary` | 改变天气 |
| `spawn_resource` | `resource_type`，`x`，`y`，`quantity`，`commentary` | 在指定位置刷新资源 |

### REST API

#### `GET /api/settings`

```json
{
  "api_key_set": true,
  "model_name": "gemini-2.5-flash",
  "token_limit": 200000,
  "llm_provider": "gemini",
  "local_llm_base_url": "http://localhost:11434/v1",
  "local_llm_model": "llama3"
}
```

#### `POST /api/settings`

```json
{
  "api_key":          "AIzaSy...",              // Gemini API Key（可选）
  "model_name":       "gemini-2.5-flash",       // 模型名（可选）
  "token_limit":      300000,                   // Token 上限（可选）
  "llm_provider":     "local",                  // "gemini" 或 "local"（可选）
  "local_llm_base_url": "http://localhost:1234/v1",  // 本地服务地址（可选）
  "local_llm_model":  "qwen2.5"                 // 本地模型名（可选）
}
```

### WebSocket 消息格式

#### 服务端 → 前端（每 tick 广播）

```json
{
  "type": "world_state",
  "tick": 142,
  "time": { "hour": 14.0, "day": 3, "phase": "day", "time_str": "Day 3 14:00" },
  "weather": "sunny",
  "tiles": [
    { "x": 10, "y": 10, "t": "o", "e": 1 },
    { "x": 3,  "y": 3,  "t": "r", "r": "s", "q": 8, "mq": 10 },
    { "x": 7,  "y": 7,  "t": "g", "r": "f", "q": 3, "mq": 5 }
  ],
  "npcs": [
    {
      "id": "npc_alice", "name": "Alice", "x": 5, "y": 5,
      "color": "#4CAF50", "energy": 82,
      "inventory": { "wood": 3, "stone": 0, "ore": 1, "food": 2, "gold": 5 },
      "last_action": "talk", "last_message": "Bob，你有多余的石头吗？",
      "last_message_tick": 140, "is_processing": false
    }
  ],
  "events": [
    { "type": "npc_spoke",     "actor": "Alice", "summary": "Alice: \"你好！\"" },
    { "type": "npc_exchanged", "actor": "Bob",   "item": "wood", "qty": 5, "gold": 5 }
  ],
  "token_usage": {
    "total_tokens_used": 45230, "limit": 200000,
    "paused": false, "usage_pct": 22.6
  }
}
```

#### 前端 → 服务端

```json
// 改变天气
{ "type": "god_command", "command": "set_weather", "value": "storm" }

// 刷新资源（包括食物）
{ "type": "god_command", "command": "spawn_resource",
  "resource_type": "food", "x": 8, "y": 12, "quantity": 5 }

// 游戏控制
{ "type": "control", "command": "pause" }
{ "type": "control", "command": "resume" }
{ "type": "control", "command": "set_limit", "value": 500000 }
```

### 地图编码（紧凑格式）

| 字段 | 值 | 含义 |
|------|----|------|
| `"t"` | `g` / `r` / `f` / `o` | 草地 / 岩石 / 森林 / 城镇 |
| `"r"` | `w` / `s` / `o` / `f` | 木头 / 石头 / 矿石 / 食物 |
| `"e"` | `1` | 交易所地块标记 |
| `"q"` | 数字 | 当前资源数量 |
| `"mq"` | 数字 | 资源上限 |
| `"n"` | 数组 | 当前格的 NPC ID 列表 |

### `config.py` 常量速查

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `WORLD_TICK_SECONDS` | `3.0` | 世界时间推进间隔（秒） |
| `NPC_MIN_THINK_SECONDS` | `5` | NPC 最短决策间隔 |
| `NPC_MAX_THINK_SECONDS` | `10` | NPC 最长决策间隔 |
| `GOD_MIN_THINK_SECONDS` | `20` | 上帝最短决策间隔 |
| `GOD_MAX_THINK_SECONDS` | `40` | 上帝最长决策间隔 |
| `DEFAULT_TOKEN_LIMIT` | `200,000` | 会话 Token 上限 |
| `LLM_PROVIDER` | `"gemini"` | LLM 提供商（gemini / local） |
| `LOCAL_LLM_BASE_URL` | `http://localhost:11434/v1` | 本地服务地址 |
| `LOCAL_LLM_MODEL` | `"llama3"` | 本地模型名 |
| `EXCHANGE_RATE_WOOD` | `1` | 木头兑换汇率（金/个） |
| `EXCHANGE_RATE_STONE` | `2` | 石头兑换汇率（金/个） |
| `EXCHANGE_RATE_ORE` | `5` | 矿石兑换汇率（金/个） |
| `FOOD_COST_GOLD` | `3` | 购买 1 个食物的价格（金） |
| `FOOD_ENERGY_RESTORE` | `30` | 吃食物回复的体力 |
| `SLEEP_ENERGY_RESTORE` | `50` | 睡眠回复的体力 |
| `EXCHANGE_X / Y` | `10 / 10` | 交易所坐标 |

---

## 📊 Token 用量管理

- **默认限额**：200,000 tokens / 会话
- **实时追踪**：每次 LLM 调用后更新，支持 Gemini 格式（`usage_metadata`）和 OpenAI 格式（`prompt_tokens / completion_tokens`）
- **超限暂停**：超过限额 → `paused=True` → 前端显示暂停遮罩 → 可在设置中扩额继续
- **用量估算**（供参考）：

  | 模型 | 约 tokens/NPC/决策 | 200k 限额可运行 |
  |------|-------------------|----------------|
  | gemini-2.5-flash | ~800–1,200 | 约 30–60 分钟 |
  | gemini-2.0-flash | ~600–1,000 | 约 40–70 分钟 |
  | 本地模型 | 无限制 | 不受 Token 限额影响 |

---

## ⚠️ 已知限制

1. **单步移动**：NPC 没有路径规划，无法自动寻路到远处目标（如交易所）
2. **交易单边生效**：`trade` 发起后直接执行，对方不能拒绝
3. **JSON 解析失败**：LLM 输出格式不合规时会 fallback 为 `rest/move`（本地模型更常见）
4. **无持久化**：重启服务器后世界状态重置
5. **Token 计数**：Gemini 计数来自 API 报告，与实际计费可能有微小差异
6. **食物供需**：食物再生较慢（每 15 tick +1），高需求时可能不足

---

## 🔮 未来改进方向

- [ ] **A\* 寻路**：让 NPC 能规划路径前往交易所、资源点或其他 NPC
- [ ] **NPC 职业分工**：初始资源分配差异化，形成自发贸易需求
- [ ] **更多建筑**：市场、旅馆、仓库、矿山等
- [ ] **玩家角色**：加入可键盘控制的人类玩家
- [ ] **存档系统**：世界状态序列化到 JSON，支持断点续跑
- [ ] **对话历史压缩**：用摘要代替原始历史，大幅节省 Token
- [ ] **前端地图缩放**：鼠标滚轮放大缩小，点击 NPC 聚焦
- [ ] **多模型混用**：不同 NPC 分配不同模型（如快速 flash + 强力 pro 搭配）
- [ ] **语音合成**：NPC 说话时触发 TTS 播放

---

<div align="center">

Made with ☕ + 🤖 · Powered by [Google Gemini](https://ai.google.dev/) & [FastAPI](https://fastapi.tiangolo.com/)

</div>