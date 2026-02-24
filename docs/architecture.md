# 🏗️ 架构设计

[← 返回主页](../README.md)

---

## 目录

- [整体技术栈](#整体技术栈)
- [异步并发模型](#异步并发模型)
- [LLM 双后端调度](#llm-双后端调度)
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
│                     浏览器 (前端)                         │
│  HTML5 Canvas  +  原生 JavaScript  +  WebSocket Client   │
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
│  │  │ WorldTick  │  │ NPCBrain ×4 │  │ GodBrain  │  │   │
│  │  │  + Market  │  │   Loops     │  │   Loop    │  │   │
│  │  └────────────┘  └─────────────┘  └───────────┘  │   │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
    ┌─────▼──────┐              ┌───────▼──────┐
    │ Google     │              │ 本地 LLM      │
    │ Gemini API │              │ (Ollama/      │
    │ (云端)     │              │  LM Studio…) │
    └────────────┘              └──────────────┘
```

---

## 异步并发模型

服务器启动后，`GameLoop.start()` 同时创建 **6 个独立的 asyncio Task**：

```
GameLoop.start()
├── Task: _world_tick_loop()      # 世界时间推进 + 被动效果 + 市场更新
├── Task: _npc_brain_loop(Alice)  # Alice 的大脑（独立循环）
├── Task: _npc_brain_loop(Bob)    # Bob 的大脑
├── Task: _npc_brain_loop(Carol)  # Carol 的大脑
├── Task: _npc_brain_loop(Dave)   # Dave 的大脑
└── Task: _god_brain_loop()       # 上帝的大脑
```

### 为什么是独立 Task 而非共享循环？

- **真正的并发决策**：4 个 NPC 同时在"思考"，不互相阻塞
- **差异化节奏**：每个 NPC 的 LLM 响应时间不同，各自维护自己的等待周期
- **故障隔离**：单个 NPC 的 LLM 调用失败不影响其他角色

### NPC Brain Loop 时序

```
[Alice Brain Loop]
  ─── sleep(random 1-4s) ──▶ LLM call ──▶ apply action ──▶ broadcast
                                                              │
                             ◀── sleep(5-10s 或 talk 后 3-6s) ┘
                             ──▶ LLM call ──▶ ...
```

NPC 说话（`talk`）后等待时间延长到 3–6s，给对话留出节奏感。

---

## LLM 双后端调度

`BaseAgent.call_llm()` 根据 `config.LLM_PROVIDER` 在运行时动态分发：

```python
async def call_llm(system_prompt, context_message, history, response_schema):
    if config.LLM_PROVIDER == "local":
        return await _call_local(...)    # OpenAI 兼容接口
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
_local_client  = None   # 调用 _get_local_client()  时懒加载

def update_api_key(new_key):
    self._api_key = new_key
    self._gemini_client = None   # 下次调用时重建

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
    actor      = "Alice",
    summary    = 'Alice 说: "你好！"',
    origin_x   = 5,
    origin_y   = 5,
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
| `weather_changed` | 上帝动作 | 全局 |
| `resource_spawned` | 上帝动作 | 全局 |
| `god_commentary` | 上帝决策 | 全局 |

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

    base_wait = random(5, 10)
    if npc.last_action == "talk":
        base_wait = random(3, 6)     # 对话后给其他 NPC 回复的时间
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

    await sleep(random 20-40s)       # 上帝行动频率较低
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
[Alice] propose_trade → Bob (ore ×2, request stone ×5)
         │
         ▼ 存入 bob.pending_proposals
         │
[系统提示] 下次 Bob 决策时，提案模块被注入 system prompt：
         "你有待处理的提案，本轮必须回应"
         │
         ├── Bob: accept_trade (proposal_from="npc_alice")
         │      → 双方库存原子交换 → trade_accepted 事件
         │
         ├── Bob: reject_trade (proposal_from="npc_alice")
         │      → 清除提案 → trade_rejected 事件 → Alice inbox 收到通知
         │
         └── Bob: counter_trade (proposal_from="npc_alice",
                  offer_item="stone", offer_qty=3,
                  request_item="ore", request_qty=2)
                → 向 Alice 发新提案 → trade_countered 事件
                → Alice 下一轮回应（最多往返数轮）
```

过期处理：提案超过 10 ticks 未响应，由 `apply_passive()` 自动清除（防止无限积压）。

---

## WebSocket 数据流

```
[浏览器] ──connect──▶ [FastAPI /ws]
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

[浏览器] ──god_command──▶ [FastAPI /ws]
                               │
                               ▼
                    god.pending_commands.append(cmd)
                    (在下一个 world tick 处理)

[浏览器] ──player_action──▶ [FastAPI /ws]
                                │
                                ▼
                    game_loop.handle_player_action(msg)
                    apply_player_action → broadcast
```

---

## 前端界面架构

### 应用状态机

```
AppState: cover → (新游戏) → new_game_modal → playing
          cover → (读档)   → load_modal     → playing
          cover → (快速)   → playing (直接)
          playing → (设置)  → 返回封面
```

### 封面屏幕

- 全屏深色背景 + HTML5 Canvas 粒子网络动画（连线效果）
- 游戏 LOGO + 副标题
- 三按钮：新游戏 / 读取存档 / 快速开始

### 新游戏流程（Modal）

两个 Tab：

**Tab A - 地图设置**：
- 随机种子输入框
- 20×20 网格地图编辑器（点击/拖动涂色）
- 地块调色板：草地 / 岩石 / 森林 / 城镇

**Tab B - NPC 档案**：
- 4 个 NPC 卡片，可编辑 title / backstory / goals / speech_style
- 导入/导出 JSON 按钮

### 主游戏界面

```
┌──── Header: Day/时间/天气/Token进度条/模拟按钮 ──────────┐
├──── Canvas (20×20地图) ────────┬──── 4-Tab 面板 ─────────┤
│   NPC 圆形头像 + 能量弧         │  👥 NPC 卡片           │
│   说话气泡（3s淡出）            │  📊 经济面板           │
│   思考时旋转虚线环              │  🎮 控制面板           │
│   天气粒子（雨滴/闪电）         │  ⚙️ 设置面板           │
├──── 玩家控制条 (WASD) ─────────┴────────────────────────┤
└──── 事件日志（滚动）───────────────────────────────────────┘
```

### 经济面板（📊 Economy Tab）

- **价格表**：物品 | 当前价 | 基准 | 趋势 ↑↓ | 变化%
- **价格历史折线图**：HTML5 Canvas 绘制，物品选择器，最近 30 个价格点，渐变填充
- **最近交易记录**：来自 `npc_sold` / `npc_bought` / `trade_accepted` 事件

### NPC 卡片（👥 NPC Tab）

每个 NPC 卡片包含：
- 彩色圆形头像 + 名字 + 称号
- 能量条（低于30显示红色）
- 库存概览（仅显示数量>0的物品）
- 展开：背景故事 / 当前目标 / 上次发言
- 编辑按钮 → 弹窗热编辑档案

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
