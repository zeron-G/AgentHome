# ⚙️ 配置参考

[← 返回主页](../README.md)

所有游戏参数集中在 [`config.py`](../config.py) 中，通过环境变量（`.env` 文件）或直接修改常量值来调整。

---

## 目录

- [配置方式](#配置方式)
- [LLM 提供商](#llm-提供商)
- [Gemini 云端配置](#gemini-云端配置)
- [本地 LLM 配置](#本地-llm-配置)
- [世界参数](#世界参数)
- [计时参数](#计时参数)
- [NPC 感知参数](#npc-感知参数)
- [Agent 记忆参数](#agent-记忆参数)
- [LLM 生成参数](#llm-生成参数)
- [Token 追踪](#token-追踪)
- [市场系统](#市场系统)
- [制造系统](#制造系统)
- [城镇与交易所（传统汇率）](#城镇与交易所传统汇率)
- [能量系统](#能量系统)
- [功能开关](#功能开关)
- [玩家角色](#玩家角色)
- [RAG 记忆持久化](#rag-记忆持久化)
- [调参建议](#调参建议)

---

## 配置方式

### 方式一：`.env` 文件（推荐，支持热加载）

在项目根目录创建 `.env`：

```bash
# LLM 提供商
LLM_PROVIDER=gemini          # 或 local

# Gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash

# 本地 LLM
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b

# 玩家
PLAYER_NAME=玩家
```

### 方式二：直接修改 config.py

适合调整游戏机制参数（时间、能量、汇率等）：

```python
# config.py
WORLD_TICK_SECONDS = 5.0        # 放慢世界时间
NPC_MIN_THINK_SECONDS = 10.0   # NPC 决策更慢（节省 Token）
```

### 方式三：网页 UI 热更新

打开 **⚙ 设置** 面板，可在线修改：
- API Key
- 模型名称
- Token 限额
- LLM 提供商 / 本地服务地址 / 本地模型名
- 游戏速度、NPC 感知半径、能量恢复量等

热更新立即生效，无需重启服务器。

---

## LLM 提供商

| 常量 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `LLM_PROVIDER` | `LLM_PROVIDER` | `"gemini"` | `"gemini"` 使用 Google Gemini，`"local"` 使用本地 OpenAI 兼容服务 |

---

## Gemini 云端配置

| 常量 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `GEMINI_API_KEY` | `GEMINI_API_KEY` | `""` | Google AI Studio API Key，空则无法调用 |
| `MODEL_NAME` | `GEMINI_MODEL` | `"gemini-2.5-flash"` | 使用的 Gemini 模型 |

### 可选模型

| 模型名 | 速度 | 质量 | 约费用 |
|--------|------|------|--------|
| `gemini-2.5-flash` | 快 | 高 | 较低 |
| `gemini-2.0-flash` | 快 | 高 | 较低 |
| `gemini-1.5-flash` | 快 | 中 | 低 |
| `gemini-1.5-pro` | 慢 | 最高 | 较高 |

---

## 本地 LLM 配置

| 常量 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `LOCAL_LLM_BASE_URL` | `LOCAL_LLM_BASE_URL` | `"http://localhost:11434/v1"` | 本地服务的 OpenAI 兼容 API 地址 |
| `LOCAL_LLM_MODEL` | `LOCAL_LLM_MODEL` | `"llama3"` | 本地模型名称（需与服务中加载的模型一致） |

> 详细配置说明请参阅 [本地 LLM 指南](local-llm.md)

---

## 世界参数

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `WORLD_WIDTH` | `20` | 地图宽度（格数） |
| `WORLD_HEIGHT` | `20` | 地图高度（格数） |

> ⚠️ 修改地图尺寸需同步修改世界生成逻辑（`engine/world.py`）和前端 Canvas 渲染参数。

---

## 计时参数

| 常量 | 默认值 | 单位 | 说明 |
|------|--------|------|------|
| `WORLD_TICK_SECONDS` | `3.0` | 秒 | 世界时间推进间隔，同时也是广播频率 |
| `NPC_MIN_THINK_SECONDS` | `5.0` | 秒 | NPC 决策最短间隔 |
| `NPC_MAX_THINK_SECONDS` | `10.0` | 秒 | NPC 决策最长间隔 |
| `GOD_MIN_THINK_SECONDS` | `20.0` | 秒 | 上帝决策最短间隔 |
| `GOD_MAX_THINK_SECONDS` | `40.0` | 秒 | 上帝决策最长间隔 |

### 计时参数调优建议

**节省 Token / 低配机器：**
```python
NPC_MIN_THINK_SECONDS = 15.0
NPC_MAX_THINK_SECONDS = 30.0
GOD_MIN_THINK_SECONDS = 60.0
GOD_MAX_THINK_SECONDS = 120.0
```

**使用本地模型（响应慢）：**
```python
NPC_MIN_THINK_SECONDS = 20.0
NPC_MAX_THINK_SECONDS = 40.0
WORLD_TICK_SECONDS    = 5.0    # 给本地模型更多缓冲时间
```

**加速游戏演示：**
```python
NPC_MIN_THINK_SECONDS = 3.0
NPC_MAX_THINK_SECONDS = 6.0
WORLD_TICK_SECONDS    = 1.0
```

---

## NPC 感知参数

| 常量 | 默认值 | 单位 | 说明 |
|------|--------|------|------|
| `NPC_HEARING_RADIUS` | `5` | 格（曼哈顿距离） | NPC 能"听到"事件的最大距离 |
| `NPC_ADJACENT_RADIUS` | `1` | 格 | NPC 能进行交易/互动的最大距离 |
| `NPC_VISION_RADIUS` | `2` | 格 | NPC 视野半径（可见区域为 `(2r+1)²` 格） |

---

## Agent 记忆参数

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `HISTORY_MAX_TURNS` | `20` | 每个 NPC 保留的最大对话轮次（超出后丢弃最早的） |
| `NOTES_MAX_COUNT` | `10` | 个人笔记最大条数（通过 `think` 动作写入） |

减小这两个参数可显著降低 Token 消耗（更短的 context），但会影响 NPC 的记忆连贯性。

---

## LLM 生成参数

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_TEMPERATURE` | `0.85` | 生成温度，越高越随机/有创意，越低越保守/确定 |
| `LLM_MAX_TOKENS` | `1024` | 单次响应最大 Token 数 |

### Temperature 调优

| 值范围 | 效果 |
|--------|------|
| `0.3–0.5` | 行为保守，动作重复性高，但 JSON 格式更稳定 |
| `0.7–0.9` | 默认范围，创意与稳定性平衡 |
| `1.0–1.2` | 行为多变有创意，但 JSON 格式错误率上升（本地模型慎用） |

---

## Token 追踪

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_TOKEN_LIMIT` | `200_000` | 默认会话 Token 上限 |

超过限额后游戏自动暂停（`paused=True`），NPC 停止 LLM 调用。可在网页设置面板调整限额并恢复。

### 限额估算

| 场景 | 推荐限额 | 大约游戏时长 |
|------|---------|------------|
| 快速体验 | `50,000` | ~10 分钟 |
| 标准游戏 | `200,000` | ~40 分钟 |
| 长期运行 | `1,000,000` | 数小时 |
| 本地模型 | `999,999,999` | 无限制（不计费） |

---

## 市场系统

动态市场价格系统，每隔固定 tick 根据供需与天气更新。

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `MARKET_UPDATE_INTERVAL` | `5` | 市场价格更新间隔（ticks） |
| `MARKET_VOLATILITY` | `0.15` | 价格随机波动幅度（±15%） |
| `MARKET_SMOOTHING` | `0.3` | 价格响应速度（0=冻结，1=瞬时更新） |
| `MARKET_PRICE_MIN_RATIO` | `0.3` | 价格下限 = 基础价 × 0.3 |
| `MARKET_PRICE_MAX_RATIO` | `3.0` | 价格上限 = 基础价 × 3.0 |

### 基础价格（`MARKET_BASE_PRICES`）

| 物品 | 基础价（金） | 说明 |
|------|------------|------|
| `wood` | `1.5` | 木头（森林采集） |
| `stone` | `2.5` | 石头（岩石地块采集） |
| `ore` | `6.0` | 矿石（岩石地块稀有采集） |
| `food` | `3.0` | 食物（草原/城镇附近采集） |
| `herb` | `4.0` | 草药（森林采集） |
| `rope` | `4.0` | 绳子（制造品） |
| `potion` | `10.0` | 药水（制造品） |
| `tool` | `8.0` | 工具（制造品） |
| `bread` | `6.0` | 面包（制造品） |

### 价格计算公式

```
target = base × (demand / supply) × weather_mod × noise(±volatility)
current = current × (1 - smoothing) + target × smoothing
```

天气影响系数：
- 暴风（storm）：食物 +40%，草药 -30%
- 雨天（rainy）：草药 +20%
- 晴天（sunny）：无修正

---

## 制造系统

NPC 可消耗原材料制造高价值物品。

### 制造配方（`CRAFTING_RECIPES`）

| 成品 | 材料 |
|------|------|
| `rope` | 木头 ×2 |
| `potion` | 草药 ×2 |
| `tool` | 石头 ×1 + 木头 ×1 |
| `bread` | 食物 ×2 |

### 物品效果（`ITEM_EFFECTS`）

| 物品 | 使用效果 | 说明 |
|------|---------|------|
| `potion` | 体力 +60 | 使用后消耗 |
| `bread` | 体力 +50 | 使用后消耗 |
| `tool` | 采集产量 ×2 | 持续生效直到放弃 |
| `rope` | 移动体力消耗 -1 | 持续生效直到放弃 |

> 使用 `use_item` 动作激活物品效果（消耗品立即消耗，工具/绳子为持续状态）。

---

## 城镇与交易所（传统汇率）

以下固定汇率用于传统 `exchange`/`buy_food` 动作（NPC 站在交易所 `is_exchange=True` 地块时可用）。市场系统的 `sell`/`buy` 动作则使用浮动市场价。

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `TOWN_X` | `9` | 城镇区域左上角 X 坐标 |
| `TOWN_Y` | `9` | 城镇区域左上角 Y 坐标 |
| `EXCHANGE_X` | `10` | 交易所地块 X 坐标 |
| `EXCHANGE_Y` | `10` | 交易所地块 Y 坐标 |
| `EXCHANGE_RATE_WOOD` | `1` | 木头固定卖出价格（金/个） |
| `EXCHANGE_RATE_STONE` | `2` | 石头固定卖出价格（金/个） |
| `EXCHANGE_RATE_ORE` | `5` | 矿石固定卖出价格（金/个） |
| `FOOD_COST_GOLD` | `3` | 购买 1 个食物的固定价格（金） |

---

## 能量系统

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `FOOD_ENERGY_RESTORE` | `30` | 吃 1 个食物回复的体力 |
| `SLEEP_ENERGY_RESTORE` | `50` | 睡眠回复的体力 |

以下参数在 `engine/world_manager.py` 中硬编码（暂未提取到 config.py）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `rest` 回复量 | `20` | 休息动作回复体力 |
| 移动消耗 | `2–3`（随机） | 每次移动消耗的体力（有绳子 -1） |
| 采集消耗 | `5` | 每次采集消耗的体力 |
| 白天体力消耗 | `3/tick` | 晴天白天每 tick 消耗 |
| 雨天额外消耗 | `+1/tick` | 雨天/暴风额外体力消耗 |
| 夜晚消耗 | `2/tick` | 夜间体力消耗（低于白天） |
| 木头/石头/矿石再生周期 | `10 tick` | 每 10 tick 再生一次 |
| 食物再生周期 | `15 tick` | 每 15 tick 再生一次 |
| 草药再生周期 | `12 tick` | 每 12 tick 再生一次 |
| 提案过期时间 | `10 tick` | 超时未响应的交易提案自动清除 |

---

## 功能开关

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `SIMULATION_AUTO_START` | `False` | `True` = 服务器启动后自动开始模拟；`False` = 需玩家点击开始 |
| `SHOW_NPC_THOUGHTS` | `True` | `True` = 在前端显示 NPC 内心想法（`thought` 字段） |

---

## 玩家角色

| 常量 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `PLAYER_ENABLED` | — | `True` | 是否生成玩家角色 |
| `PLAYER_NAME` | `PLAYER_NAME` | `"玩家"` | 玩家角色名称 |
| `PLAYER_START_X` | — | `12` | 玩家初始 X 坐标 |
| `PLAYER_START_Y` | — | `12` | 玩家初始 Y 坐标 |

---

## RAG 记忆持久化

NPC 的重要行动会被保存到本地文件，下次游戏会话时通过语义搜索召回。

| 常量 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `RAG_ENABLED` | — | `True` | 是否启用 RAG 记忆持久化 |
| `RAG_SAVE_DIR` | `RAG_SAVE_DIR` | `"saves"` | 记忆文件保存目录 |
| `RAG_MAX_MEMORIES_PER_NPC` | — | `200` | 每个 NPC 最多保存的记忆条数 |
| `RAG_SEARCH_LIMIT` | — | `5` | 每次决策从 RAG 召回的记忆条数 |

---

## 调参建议

### 场景一：演示/测试

想让 NPC 尽快行动、互动频繁：

```python
WORLD_TICK_SECONDS    = 1.0
NPC_MIN_THINK_SECONDS = 2.0
NPC_MAX_THINK_SECONDS = 5.0
GOD_MIN_THINK_SECONDS = 10.0
GOD_MAX_THINK_SECONDS = 20.0
DEFAULT_TOKEN_LIMIT   = 500_000
```

### 场景二：节省 API 费用

减少 LLM 调用频率：

```python
NPC_MIN_THINK_SECONDS = 20.0
NPC_MAX_THINK_SECONDS = 40.0
GOD_MIN_THINK_SECONDS = 60.0
GOD_MAX_THINK_SECONDS = 120.0
HISTORY_MAX_TURNS     = 10    # 缩短记忆，降低每次 Token 数
DEFAULT_TOKEN_LIMIT   = 50_000
```

### 场景三：本地模型（CPU 推理）

本地模型响应慢（5–30s），适当延长间隔：

```python
NPC_MIN_THINK_SECONDS = 30.0
NPC_MAX_THINK_SECONDS = 60.0
WORLD_TICK_SECONDS    = 5.0
LLM_TEMPERATURE       = 0.7   # 略低，减少 JSON 格式错误
DEFAULT_TOKEN_LIMIT   = 999_999_999  # 本地模型不计费，设大
```

### 场景四：活跃市场经济

增加经济与制造行为频率：

```python
MARKET_UPDATE_INTERVAL = 3    # 更频繁的价格波动
MARKET_VOLATILITY      = 0.25 # 更大的价格波动幅度
MARKET_SMOOTHING       = 0.5  # 价格响应更快
# 调低基础价让利润空间更大，鼓励 NPC 更多交易
MARKET_BASE_PRICES["ore"] = 8.0
```

### 场景五：天气影响明显

加大天气对食物价格的影响：

```python
# 修改 world_manager.py 中的 weather_mod 系数
# storm: food ×2.0 (原 ×1.4)，herb ×0.5 (原 ×0.7)
```
