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
- [城镇与交易所](#城镇与交易所)
- [能量系统](#能量系统)
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
| `NPC_ADJACENT_RADIUS` | `1` | 格 | NPC 能进行交易/互动的最大距离（通常为 1，即相邻格） |

### 曼哈顿距离说明

```
曼哈顿距离 = |x1 - x2| + |y1 - y2|

NPC_HEARING_RADIUS = 5 意味着：
Alice 在 (5,5)，Bob 在 (9,5)（距离=4）→ Alice 能听到 Bob 说话
Alice 在 (5,5)，Dave 在 (14,14)（距离=18）→ Alice 听不到
```

调大 `NPC_HEARING_RADIUS` 会让 NPC 互动范围更广，但 context 会变长（更多事件进入收件箱）。

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

### Max Tokens 调优

NPC 响应通常在 100–300 tokens 内，`1024` 已足够。

若使用本地模型且经常出现截断响应，可适当增大：
```python
LLM_MAX_TOKENS = 2048
```

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

## 城镇与交易所

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `TOWN_X` | `9` | 城镇区域左上角 X 坐标 |
| `TOWN_Y` | `9` | 城镇区域左上角 Y 坐标 |
| `EXCHANGE_X` | `10` | 交易所地块 X 坐标 |
| `EXCHANGE_Y` | `10` | 交易所地块 Y 坐标 |
| `EXCHANGE_RATE_WOOD` | `1` | 木头卖出价格（金/个） |
| `EXCHANGE_RATE_STONE` | `2` | 石头卖出价格（金/个） |
| `EXCHANGE_RATE_ORE` | `5` | 矿石卖出价格（金/个） |
| `FOOD_COST_GOLD` | `3` | 购买 1 个食物的价格（金） |

> ⚠️ 修改交易所坐标需同步更新 `agents/prompts.py` 中的系统提示词，确保 NPC 知道正确位置。

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
| 移动消耗 | `2–3`（随机） | 每次移动消耗的体力 |
| 采集消耗 | `5` | 每次采集消耗的体力 |
| 白天体力消耗 | `3/tick` | 晴天白天每 tick 消耗 |
| 雨天额外消耗 | `+1/tick` | 雨天/暴风额外体力消耗 |
| 夜晚消耗 | `2/tick` | 夜间体力消耗（低于白天） |
| 木头/石头/矿石再生周期 | `10 tick` | 每 10 tick 再生一次 |
| 食物再生周期 | `15 tick` | 每 15 tick 再生一次 |

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

### 场景四：经济模拟重点

增加经济行为频率：

```python
EXCHANGE_RATE_ORE   = 10   # 矿石更值钱，激励采矿
FOOD_COST_GOLD      = 1    # 食物便宜，NPC 更愿意购买
FOOD_ENERGY_RESTORE = 50   # 吃食物回复更多，食物更有价值
SLEEP_ENERGY_RESTORE = 30  # 降低睡眠收益，让 NPC 倾向购买食物
```