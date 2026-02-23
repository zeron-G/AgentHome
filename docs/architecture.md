# 🏗️ 架构设计

[← 返回主页](../README.md)

---

## 目录

- [整体技术栈](#整体技术栈)
- [异步并发模型](#异步并发模型)
- [LLM 双后端调度](#llm-双后端调度)
- [事件系统](#事件系统)
- [游戏循环详解](#游戏循环详解)
- [WebSocket 数据流](#websocket-数据流)
- [并发安全](#并发安全)

---

## 整体技术栈

```
┌─────────────────────────────────────────────────────────┐
│                     浏览器 (前端)                         │
│  HTML5 Canvas  +  原生 JavaScript  +  WebSocket Client   │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket /ws
                         │ HTTP GET/POST /api/settings
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI + uvicorn                      │
│                    (asyncio 事件循环)                     │
│  ┌──────────────┐   ┌───────────────┐   ┌────────────┐ │
│  │  WebSocket   │   │  REST API     │   │  Static    │ │
│  │  Endpoint    │   │  /api/settings│   │  Files     │ │
│  └──────┬───────┘   └───────────────┘   └────────────┘ │
│         │                                               │
│  ┌──────▼───────────────────────────────────────────┐  │
│  │                   GameLoop                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │ WorldTick  │  │ NPCBrain×4 │  │  GodBrain  │  │  │
│  │  │  Loop      │  │  Loops     │  │   Loop     │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  │  │
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
├── Task: _world_tick_loop()      # 世界时间推进 + 被动效果
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
                npc.memory.inbox.append(event)   # NPC 下次决策时读取
```

### 事件类型一览

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
| `npc_thought` | `think` | 0 格（仅自己） |
| `weather_changed` | 上帝动作 | 全局 |
| `resource_spawned` | 上帝动作 | 全局 |
| `god_commentary` | 上帝决策 | 全局 |

---

## 游戏循环详解

### World Tick Loop（每 3 秒）

```
while running:
    acquire _world_lock
        world.time.advance()          # 时间推进（早晨/白天/黄昏/夜晚）
        world_manager.apply_passive() # 体力消耗 + 资源再生 + 自动进食
    release _world_lock

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

while running:
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

while running:
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

[浏览器] ──god_command──▶ [FastAPI /ws]
                               │
                               ▼
                    god.pending_commands.append(cmd)
                    (在下一个 world tick 处理)
```

---

## 并发安全

| 机制 | 保护对象 | 说明 |
|------|---------|------|
| `asyncio.Lock (_world_lock)` | 所有世界状态写入 | NPC/God 动作、tick 推进前均 acquire |
| `asyncio.Lock (_lock in TokenTracker)` | Token 计数器 | 多个 agent 并发记录时的原子操作 |
| `npc.is_processing` | 单个 NPC 状态 | 防止同一 NPC 被重入（保险措施） |
| WebSocket 广播 | `ws_manager.active` 集合 | 广播时异常的连接被自动清理 |

> **注意**：asyncio 是单线程协作式并发，Lock 保护的是协程间的切换点，而非真正的多线程竞争。此架构在 Python asyncio 单进程内是安全的。