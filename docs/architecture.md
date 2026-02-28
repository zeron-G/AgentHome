# 架构设计

[← 返回主页](../README.md)

---

## 目录

- [整体技术栈](#整体技术栈)
- [异步并发模型](#异步并发模型)
- [LLM 三后端调度](#llm-三后端调度)
- [事件系统](#事件系统)
- [游戏循环详解](#游戏循环详解)
- [市场系统设计](#市场系统设计)
- [提案式交易流程](#提案式交易流程)
- [WebSocket 数据流](#websocket-数据流)
- [前端界面架构](#前端界面架构)
- [并发安全](#并发安全)

---

## 整体技术栈

```
┌─────────────────────────────────────────────────────────┐
│                     Godot 4 (前端)                       │
│  2D 游戏场景  +  GDScript  +  WebSocket Client          │
│  封面屏幕 / 新游戏流程 / 主游戏界面 / 经济面板              │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket /ws
                         │ HTTP REST /api/*
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI + uvicorn                      │
│                    (asyncio 事件循环)                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │  WebSocket   │  │  REST API     │  │   Static     │  │
│  │  Endpoint    │  │  /api/*       │  │   Files      │  │
│  └──────┬───────┘  └───────────────┘  └──────────────┘  │
│         │                                                │
│  ┌──────▼───────────────────────────────────────────┐   │
│  │                   GameLoop                        │   │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │ WorldTick  │  │ NPCBrain ×9 │  │ GodBrain  │  │   │
│  │  │  + Market  │  │   Loops     │  │   Loop    │  │   │
│  │  └────────────┘  └─────────────┘  └───────────┘  │   │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
    │ Google     │ │ Anthropic  │ │ 本地 LLM      │
    │ Gemini API │ │ Claude API │ │ (Ollama/      │
    │ (云端)     │ │ (云端)     │ │  LM Studio…) │
    └────────────┘ └────────────┘ └──────────────┘
```

---

## 异步并发模型

服务器启动后，`GameLoop.start_simulation()` 同时创建 **11 个独立的 asyncio Task**：

```
GameLoop.start_simulation()
├── Task: _world_tick_loop()         # 世界时间推进 + 被动效果 + 市场更新
├── Task: _npc_brain_loop(禾)        # 核心NPC（高频）
├── Task: _npc_brain_loop(穗)        # 核心NPC
├── Task: _npc_brain_loop(山)        # 核心NPC
├── Task: _npc_brain_loop(棠)        # 核心NPC
├── Task: _npc_brain_loop(旷)        # 日常NPC（低频，think_interval_multiplier）
├── Task: _npc_brain_loop(木)        # 日常NPC
├── Task: _npc_brain_loop(岚婆)      # 日常NPC
├── Task: _npc_brain_loop(石)        # 日常NPC
├── Task: _npc_brain_loop(商人)      # 特殊NPC（日夜提示词不同）
└── Task: _god_brain_loop()          # 爷爷 / God Agent
```

### 为什么是独立 Task 而非共享循环？

- **真正的并发决策**：9 个 NPC 同时在"思考"，不互相阻塞
- **差异化节奏**：核心 NPC 5-10s、日常 NPC 15-30s、特殊 NPC 15s
- **故障隔离**：单个 NPC 的 LLM 调用失败不影响其他角色

### NPC Brain Loop 时序

```
[禾 Brain Loop]（核心NPC）
  ─── sleep(random 1-4s) ──▶ LLM call ──▶ apply action ──▶ broadcast
                                                              │
                             ◀── sleep(5-10s 或 talk 后 3-6s) ┘
                             ──▶ LLM call ──▶ ...

[旷 Brain Loop]（日常NPC，think_interval_multiplier=2.0）
  ─── sleep(random 1-4s) ──▶ LLM call ──▶ apply action ──▶ broadcast
                                                              │
                             ◀── sleep(10-20s，乘以 multiplier) ┘
                             ──▶ LLM call ──▶ ...
```

NPC 说话（`talk`）后等待时间延长到 3–6s，给对话留出节奏感。

### 三层 NPC 决策系统

```
Layer 1 — 策略层（每 NPC_STRATEGY_INTERVAL=20 ticks）
  轻量 LLM 调用 → 设定 npc.goal 和 npc.plan

Layer 2 — 战术层（规则引擎，每个 brain cycle）
  _advance_plan_if_needed() → 弹出已完成步骤

Layer 3 — 执行层（每个 brain cycle）
  主 LLM 调用（注入 goal/plan）→ NPCAction → 世界执行
```

---

## LLM 三后端调度

`BaseAgent.call_llm()` 根据 `config.LLM_PROVIDER` 在运行时动态分发：

```python
async def call_llm(system_prompt, context_message, history, response_schema):
    if config.LLM_PROVIDER == "local":
        return await _call_local(...)    # OpenAI 兼容接口
    elif config.LLM_PROVIDER == "claude":
        return await _call_claude(...)   # Anthropic Claude SDK
    else:
        return await _call_gemini(...)   # Google Gemini SDK
```

### Gemini 后端（`_call_gemini`）

```
构建 contents 列表（历史 + 当前 context）
    │
    ▼
GenerateContentConfig(
    system_instruction = system_prompt,
    response_mime_type = "application/json",
    response_schema    = Pydantic 模型,       ← 强制结构化输出
    temperature        = config.LLM_TEMPERATURE,
    max_output_tokens  = config.LLM_MAX_TOKENS,
)
    │
    ▼
client.aio.models.generate_content(model, contents, config)
    │
    ▼
JSON 解析 → Pydantic 模型实例
记录 token（usage_metadata.prompt_token_count / candidates_token_count）
```

### Claude 后端（`_call_claude`）

```
构建 messages 列表（role: user/assistant）
    │
    ▼
anthropic.AsyncAnthropic().messages.create(
    model           = config.ANTHROPIC_MODEL,
    system          = system_prompt,
    messages        = messages,
    max_tokens      = config.LLM_MAX_TOKENS,
    temperature     = config.LLM_TEMPERATURE,
)
    │
    ▼
JSON 解析 → Pydantic 模型实例
记录 token（usage.input_tokens / output_tokens）
```

### 本地后端（`_call_local`）

```
将 Pydantic JSON Schema 追加到 system prompt
    │
    ▼
构建 OpenAI messages 列表（role: user/assistant）
    │
    ▼
AsyncOpenAI.chat.completions.create(
    model           = config.LOCAL_LLM_MODEL,
    messages        = messages,
    response_format = {"type": "json_object"},  ← JSON 模式
    temperature     = config.LLM_TEMPERATURE,
    max_tokens      = config.LLM_MAX_TOKENS,
)
    │
    ▼
剥离 markdown 代码围栏（```json ... ```）
JSON 解析 → Pydantic 模型实例
记录 token（usage.prompt_tokens / completion_tokens）
```

### 客户端生命周期（懒加载 + 热更新）

```python
# 首次调用时创建，切换配置后自动重建
_gemini_client = None   # 调用 _get_gemini_client() 时懒加载
_claude_client = None   # 调用 _get_claude_client() 时懒加载
_local_client  = None   # 调用 _get_local_client()  时懒加载

def update_api_key(new_key):
    self._api_key = new_key
    self._gemini_client = None   # 下次调用时重建

def reset_claude_client():
    self._claude_client = None   # API key 变更后重建

def reset_local_client():
    self._local_client = None    # URL/模型变更后重建
```

---

## 事件系统

每个动作执行后生成 `WorldEvent`，通过 `EventBus` 分发：

```
动作执行 (world_manager.apply_*)
    │
    ▼
生成 WorldEvent(
    event_type = EventType.npc_spoke,
    actor      = "禾",
    summary    = '禾 说: "你饿了吧？来吃点东西。"',
    origin_x   = 3,
    origin_y   = 3,
    radius     = 5,       # 影响范围（曼哈顿距离）
    metadata   = {...},
)
    │
    ▼
EventBus.dispatch(event, world)
    ├── world.recent_events.append(event)    # 全局日志（最多 30 条）
    │
    └── for npc in world.npcs:
            if manhattan_dist(npc, event) <= radius:
                npc.memory.inbox.append(event.summary)
                # NPC 下次决策时读取，决策后清空 inbox
```

### 事件类型与影响半径

| 事件 | 触发动作 | 默认半径 |
|------|---------|---------|
| `npc_spoke` | `talk` / `interrupt` | 5 格 |
| `npc_moved` | `move` | 2 格 |
| `npc_gathered` | `gather` | 3 格 |
| `npc_traded` | `trade` | 3 格 |
| `npc_rested` | `rest` | 1 格 |
| `npc_slept` | `sleep` | 1 格 |
| `npc_ate` | `eat` | 2 格 |
| `npc_exchanged` | `exchange` | 4 格 |
| `npc_bought_food` | `buy_food` | 4 格 |
| `npc_crafted` | `craft` | 3 格 |
| `npc_sold` | `sell` | 4 格 |
| `npc_bought` | `buy` | 4 格 |
| `npc_used_item` | `use_item` | 2 格 |
| `trade_proposed` | `propose_trade` | 5 格 |
| `trade_accepted` | `accept_trade` | 5 格 |
| `trade_rejected` | `reject_trade` | 5 格 |
| `trade_countered` | `counter_trade` | 5 格 |
| `market_updated` | 市场更新循环 | 全局 |
| `npc_thought` | `think` | 0 格（仅自己） |
| `weather_changed` | God 动作 | 全局 |
| `resource_spawned` | God 动作 | 全局 |
| `god_commentary` | God 决策 | 全局 |

---

## 游戏循环详解

### World Tick Loop（每 3 秒）

```
while simulation_running:
    acquire _world_lock
        world.time.advance()          # 时间推进（早晨/白天/黄昏/夜晚）
        world_manager.apply_passive() # 体力消耗 + 资源再生 + 提案清理
        if tick % MARKET_UPDATE_INTERVAL == 0:
            market_event = update_market()  # 价格更新
    release _world_lock

    if market_event:
        event_bus.dispatch(market_event)

    if god.pending_commands:          # 浏览器 UI 直接指令（无 LLM）
        for cmd in pending_commands:
            apply_direct_god_command(cmd)
        broadcast_with_events()
        continue

    broadcast()                       # 广播世界快照
    await sleep(WORLD_TICK_SECONDS)
```

### NPC Brain Loop（每 NPC 独立）

```
await sleep(random 1-4s)             # 错开启动，避免 API 并发峰值

while simulation_running:
    if token_tracker.paused:
        await sleep(2s)
        continue

    action = await npc_agent.process(npc, world)
                                     # 调用 LLM（可能耗时 1-5s）

    if action != idle:
        acquire _world_lock
            events = world_manager.apply_npc_action(npc, action, world)
        release _world_lock

        for event in events:
            event_bus.dispatch(event, world)

        broadcast_with_events(events)

    base_wait = random(NPC_MIN_THINK, NPC_MAX_THINK)
    if npc.last_action == "talk":
        base_wait = random(3, 6)     # 对话后给其他 NPC 回复的时间
    # 日常NPC（旷/木/岚/石）乘以 think_interval_multiplier
    daily_cfg = DAILY_NPC_CONFIG.get(npc.npc_id)
    if daily_cfg:
        base_wait *= daily_cfg["think_interval_multiplier"]
    await sleep(base_wait)
```

### God Brain Loop

```
await sleep(random 5-10s)           # 延迟首次行动

while simulation_running:
    if paused: await sleep(2s); continue

    action = await god_agent.process(god, world)
    if action:
        acquire _world_lock
            events = world_manager.apply_god_action(action, world)
        release _world_lock
        broadcast_with_events(events)

    await sleep(random 20-40s)       # God 行动频率较低
```

---

## 市场系统设计

### 价格更新流程

```
每 MARKET_UPDATE_INTERVAL ticks 触发：

for item in all_items:
    # 供给量：地图资源 + NPC 库存
    supply = sum(tile.resource.quantity for tiles with item)
             + sum(npc.inventory.get(item) for all npcs)
    supply = max(supply, 1)   # 避免除零

    # 需求代理：NPC 体力越低 = 对消耗品需求越高
    avg_energy = mean(npc.energy for all npcs)
    demand = (100 - avg_energy) / 100 + 0.5   # 0.5 ~ 1.5

    # 天气修正
    if storm:   food×1.4, herb×0.7
    if rainy:   herb×1.2

    # 随机波动
    noise = random(1 - volatility, 1 + volatility)

    # 目标价
    target = base × (demand / (supply / 10)) × weather_mod × noise
    target = clamp(target, min_p, max_p)

    # 指数平滑更新
    current = current × (1 - smoothing) + target × smoothing

    # 记录历史（最多30点）
    history[item].append(current)
```

### 市场价格影响行为

NPC 在 system prompt 中会收到当前市场价格表（趋势↑↓），并被鼓励：
- 高价时卖出（`sell`）、低价时买入（`buy`）
- 对稀缺资源（高价）优先采集
- 制造品价格高于原材料时主动制造（`craft`）

---

## 提案式交易流程

提案式交易允许 NPC 进行异步协商，比 `trade`（同步双向同意）更真实。

```
[禾] propose_trade → 石 (food ×2, request stone ×3)
         │
         ▼ 存入 石.pending_proposals
         │
[系统提示] 下次石决策时，提案模块被注入 system prompt：
         "你有待处理的提案，本轮必须回应"
         │
         ├── 石: accept_trade (proposal_from="npc_he")
         │      → 双方库存原子交换 → trade_accepted 事件
         │
         ├── 石: reject_trade (proposal_from="npc_he")
         │      → 清除提案 → trade_rejected 事件 → 禾 inbox 收到通知
         │
         └── 石: counter_trade (proposal_from="npc_he",
                  offer_item="stone", offer_qty=2,
                  request_item="food", request_qty=2)
                → 向禾发新提案 → trade_countered 事件
                → 禾下一轮回应（最多往返数轮）
```

过期处理：提案超过 10 ticks 未响应，由 `apply_passive()` 自动清除（防止无限积压）。

---

## WebSocket 数据流

```
[客户端] ──connect──▶ [FastAPI /ws]
                            │
                            ▼
                    发送初始世界快照（world_snapshot）

[World Tick Loop] ──每 3s──▶ broadcast(snapshot)
                                   │
                             send to all WSs

[NPC/God Action] ──▶ broadcast_with_events(snapshot + events)
                            │
                      send to all WSs

[Market Update] ──每5tick──▶ broadcast(snapshot + market_updated event)

[客户端] ──god_command──▶ [FastAPI /ws]
                               │
                               ▼
                    god.pending_commands.append(cmd)
                    (在下一个 world tick 处理)

[客户端] ──player_action──▶ [FastAPI /ws]
                                │
                                ▼
                    game_loop.handle_player_action(msg)
                    apply_player_action → broadcast
```

---

## 前端界面架构

> 注：前端正在从 HTML5 Canvas 迁移到 Godot 4，以下架构描述将在迁移完成后更新。

### 应用状态机

```
AppState: cover → (新游戏) → new_game_modal → playing
          cover → (读档)   → load_modal     → playing
          cover → (快速)   → playing (直接)
          playing → (设置)  → 返回封面
```

### 主游戏界面（目标架构）

```
┌──── Header: Day/时间/天气/季节/Token进度条/模拟按钮 ─────┐
├──── 游戏视口 (20×20地图) ──────┬──── 侧面板 ──────────────┤
│   NPC 头像 + 能量弧             │  NPC 卡片（9个）         │
│   说话气泡（3s淡出）            │  经济面板               │
│   思考时旋转虚线环              │  控制面板               │
│   天气粒子（雨滴/闪电）         │  设置面板               │
├──── 玩家控制条 ─────────────────┴────────────────────────┤
└──── 事件日志（滚动）───────────────────────────────────────┘
```

---

## 并发安全

| 机制 | 保护对象 | 说明 |
|------|---------|------|
| `asyncio.Lock (_world_lock)` | 所有世界状态写入 | NPC/God 动作、tick 推进前均 acquire |
| `asyncio.Lock (_lock in TokenTracker)` | Token 计数器 | 多个 agent 并发记录时的原子操作 |
| `npc.is_processing` | 单个 NPC 状态 | 防止同一 NPC 被重入（保险措施） |
| WebSocket 广播 | `ws_manager.active` 集合 | 广播时异常的连接被自动清理 |
| `pending_proposals` 过期清理 | NPC 提案队列 | `apply_passive()` 清除超时提案防积压 |

> **注意**：asyncio 是单线程协作式并发，Lock 保护的是协程间的切换点，而非真正的多线程竞争。此架构在 Python asyncio 单进程内是安全的。
