# 🏘️ AgentHome — LLM 驱动的 AI 沙盒世界

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-✓-4285F4?style=flat-square&logo=google&logoColor=white)
![Local LLM](https://img.shields.io/badge/Local_LLM-Ollama_/_LM_Studio-F97316?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)

**一个 2D 沙盒 AI 世界：4 个 NPC + 1 个上帝，每个角色由大语言模型独立控制。**

NPC 自主决策、互相交谈、采集资源、建造家具、在城镇交易所买卖，一切通过浏览器实时可视化。

</div>

---

## 功能特性

| 类别 | 特性 |
|------|------|
| 🤖 **分级 AI 决策** | 三层架构：战略层（每 20 tick LLM 制定目标/计划）→ 战术层（规则推进）→ 执行层（LLM 执行单步） |
| 🧠 **动态上下文注入** | Prompt 模块按当前状态条件化组装（背包空→不注入交易模块，独处→不注入社交模块），节省约 30–50% tokens |
| 🌐 **双 LLM 后端** | Google Gemini（云端）或任意 OpenAI 兼容本地服务（Ollama / LM Studio / vLLM…） |
| 👤 **统一角色系统** | NPC 与玩家共享相同动作/装备/背包规则，逻辑对等 |
| ⚔️ **装备系统** | 单装备槽（tool→采集×2 / rope→移动-1体力），use_item 即装备 |
| 🎒 **背包容量** | 最多 20 格（金币不占格），满了无法继续采集/购买 |
| 🪵 **家具建造** | 可建造床/桌/椅，影响 sleep/rest/craft 效果；NPC 和玩家均可建造 |
| 💬 **NPC→玩家对话** | NPC 对玩家说话时弹出对话框，快速回复选项由上帝 Agent 异步生成 |
| 🎮 **玩家动作平权** | 支持 craft/sell/buy/equip/build/propose_trade/dialogue_reply 等完整动作 |
| 📈 **浮动市场** | 供需+天气驱动的动态价格，历史曲线可视化 |
| 🏘️ **城镇与交易所** | 中央城镇 + 交易所：按市价卖/买，固定汇率备用 |
| ⚡ **实时可视化** | WebSocket 驱动，HTML5 Canvas 渲染地块/NPC/气泡/家具/天气粒子 |
| 🎲 **上帝控制** | 浏览器界面直接控制天气、刷新资源，也支持 LLM 驱动的上帝自主干预 |
| 📊 **Token 追踪** | 实时进度条，超限自动暂停，可动态扩额续跑 |
| 💾 **RAG 记忆持久化** | NPC 行动存入本地 JSON，语义检索注入上下文 |

---

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥（可选，也可在网页 UI 中设置）

```bash
cp .env.example .env
# 编辑 .env，填入 GEMINI_API_KEY=AIzaSy...
```

> 如果使用本地模型，请参阅 [本地 LLM 配置指南 →](docs/local-llm.md)

### 3. 启动服务器

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 打开浏览器

访问 **http://localhost:8000**，点击 **Start** 开始模拟。

---

## 项目结构

```
agenthome/
├── main.py              # FastAPI 入口（WebSocket + REST API）
├── config.py            # 全局常量（世界参数、汇率、能量、LLM 配置）
├── requirements.txt
├── .env                 # 密钥与本地配置（可选）
│
├── engine/
│   ├── world.py         # 数据模型（Tile、NPC、Inventory、World、世界生成）
│   └── world_manager.py # 世界状态变更（所有动作处理器，NPC/玩家通用）
│
├── agents/
│   ├── base_agent.py    # LLM 基类（Gemini / 本地双后端，懒加载，热更新）
│   ├── npc_agent.py     # NPC 三层决策代理（战略/战术/执行）
│   ├── god_agent.py     # 上帝决策代理 + 对话选项生成
│   └── prompts.py       # 提示词模板 + Pydantic Schema（NPCStrategy/NPCAction/GodAction）
│
├── game/
│   ├── loop.py          # 异步游戏主循环（独立 brain loop、对话异步任务）
│   ├── events.py        # 事件类型（40+）、WorldEvent、EventBus
│   └── token_tracker.py # Token 统计与限额控制
│
├── ws/
│   ├── manager.py       # WebSocket 连接池 + 广播
│   └── serializer.py    # World → 紧凑 JSON（含 goal/plan/furniture/dialogue）
│
├── frontend/
│   └── index.html       # 单文件前端（Canvas + 5 选项卡面板）
│
└── docs/                # 详细文档
    ├── architecture.md  # 架构设计与并发模型
    ├── local-llm.md     # 本地 LLM 配置指南
    ├── world.md         # 世界系统（地块、资源、交易所、食物）
    ├── modules.md       # 各模块详解
    ├── api-reference.md # REST API + WebSocket 协议参考
    └── config.md        # 所有配置常量速查
```

---

## Agent 架构：三层分级决策

```
┌─────────────────────────────────────────────────────┐
│           NPC Brain Loop (每 5–10s)                  │
│                                                     │
│  Layer 1 ─ 战略层 (每 20 world tick，轻量 LLM)        │
│    输入: 状态摘要 + 视野资源 + 市场概要 (~300 chars)    │
│    输出: NPCStrategy { goal, steps[3-5] }           │
│    存储: npc.goal / npc.plan / npc.strategy_tick    │
│                                                     │
│  Layer 2 ─ 战术层 (规则推断，0 LLM 调用)              │
│    检查 last_action + 步骤关键词 → pop 已完成步骤      │
│                                                     │
│  Layer 3 ─ 执行层 (每 brain cycle，主 LLM 调用)       │
│    上下文: 状态 + 目标/计划注入 + 视野网格              │
│    动态模块: 按当前状态条件化包含                       │
│    输出: NPCAction (单步具体动作)                     │
└─────────────────────────────────────────────────────┘
```

**Token 效益**（相较旧版单层架构）：
- 执行层 prompt 减少约 30–50%（不注入无关模块/市场表）
- 策略层调用频率极低（约每 60 秒 1 次），context 极小
- NPC 行为连贯性显著提升，不再每步"从头思考"

---

## Token 用量估算

| 模型 | 约 tokens/NPC/执行决策 | 200k 限额可运行 |
|------|----------------------|----------------|
| gemini-2.5-flash | ~500–900（动态注入后） | 约 45–90 分钟 |
| gemini-2.0-flash | ~400–800 | 约 60–100 分钟 |
| 本地模型 | 不计入限额 | 不受限制 |

---

## 详细文档

| 文档 | 内容 |
|------|------|
| [🏗️ 架构设计](docs/architecture.md) | 异步并发模型、LLM 双后端调度、事件系统、游戏循环 |
| [🖥️ 本地 LLM 指南](docs/local-llm.md) | Ollama / LM Studio / vLLM 配置，模型推荐，常见问题 |
| [🌍 世界系统](docs/world.md) | 地块类型、资源系统、食物系统、城镇与交易所 |
| [📦 模块详解](docs/modules.md) | 每个 Python 模块的数据结构与方法说明 |
| [📡 API 参考](docs/api-reference.md) | REST API、WebSocket 消息格式、NPC/上帝动作 Schema |
| [⚙️ 配置参考](docs/config.md) | `config.py` 所有常量的默认值与说明 |
| [🎭 叙事设计](docs/narrative-design.md) | 完整世界观、塔罗象征系统、11角色设定、三个结局、道具系统、支线设计 |
| [🃏 角色关系网](docs/character-relationships.md) | 角色速查、关系图谱、认知屏障等级、支线归属、三结局状态总览 |
| [🎮 游戏机制](docs/game-design.md) | 时间系统数值、白天/黑夜玩法、NPC频率分级、道具参数、结局解锁条件 |

---

## 叙事概览

> 你受不了大城市的压力，回到乡下接手了爷爷留下的小屋和园子。这个与世隔绝的小村子温暖而宁静——热心的草药师、沉默的矿工、讲故事的老人、到处跑的小女孩……一切看起来像一场田园美梦。
>
> 但梦境的边缘总有裂缝。老井夜里传来低语，天空偶尔下起红色的雪，一个"明天就走"的旅人已经说了十几年的明天。而那个从不出错的天气旁白，有时会说出一些……不该说的话。
>
> 这个村子隐藏着一个关于爱、牺牲和自由的秘密。你会发现真相吗？发现之后，你又会如何选择？

**塔罗象征系统**：11张大阿卡那牌对应11个角色，每张牌的正位=白天面，逆位=阴影面。没有纯粹的善恶，只有一体两面。

**三个结局**：你的探索深度和选择将决定故事的走向——有的结局温暖但令人不安，有的结局自由但代价沉重。每一个都值得经历。

---

## 未来发展方向

以下是项目规划的演进路线，按优先级排列。

### 🔴 P0 — 已完成 / 进行中

| 功能 | 状态 | 说明 |
|------|------|------|
| 三层分级决策架构 | ✅ 完成 | Strategic/Tactical/Execution 三层，减少 LLM 调用成本，提升行为连贯性 |
| 动态上下文注入 | ✅ 完成 | Prompt 模块按状态条件化，市场表仅在交易所显示，节省约 30–50% tokens |

### 🟠 P1 — 近期规划

#### 前端渲染引擎升级（HTML Canvas → Phaser.js）

当前前端用原生 Canvas 手写渲染，限制明显：无 tileset、无精灵动画、无摄像机缩放。

计划迁移到 **Phaser.js**（纯 JS，WebSocket 复用，迁移成本最低）：
- 支持精灵动画（NPC 行走/睡觉/交谈）
- Tileset 地图（视觉质量大幅提升）
- 摄像机跟随、缩放、点击交互
- 后端保持 Python + WebSocket 不变，前端完全解耦

> Unreal/Unity 对于当前 2D Tile 游戏属于过度工程，暂不考虑。

#### WebSocket 增量更新（Delta Diff）

当前每 tick 广播完整世界快照（全部 tiles + NPCs），随地图变大 payload 会膨胀。

计划：
- 初次连接发送完整 `world_state`
- 后续只发 `world_delta`（变化的格子、变化的 NPC）
- 预计减少 80%+ 的数据传输量

### 🟡 P2 — 中期规划

#### 动态叙事系统（涌现式叙事 + God Agent 导演）

由**上帝 Agent（爷爷的意志）作为叙事导演**，结合塔罗象征系统驱动的涌现式叙事：

- **8+1+1 角色系统**：8个NPC（6主要+2次要）+ 1个God Agent + 1个非NPC恶魔，每个角色对应一张塔罗大阿卡那
- **四季叙事弧**：以季节为单位的渐进式真相揭示（正常村居→异常浮现→碎片期→真相抉择）
- **认知屏障渐染**：玩家亲身体验结界的认知影响——不探索则选项减少、视野变暗、旁白变安抚
- **三个结局**：正常结局（轮回）、隐藏结局1（新交易）、隐藏结局2（终结），跨多周目解锁
- **11件塔罗道具**：每件有正用/逆用和不可逆的trade-off，迫使玩家权衡每次选择
- **白天种田/黑夜克苏鲁**：日间温馨经营，夜间对抗天灾渗透的异常实体

#### 内容可扩展性（应对物品/配方数量增长）

随着物品从 ~10 种增长到 ~50 种，当前"全量上下文"策略会崩溃。

规划：
- **物品分类化**：`category: tool | consumable | material | equipment`，Agent 先选类别再选物品（二级决策）
- **按需上下文**：只注入当前背包中有的物品 + 附近可见资源，不是全量列表
- **物品 RAG 知识库**：物品效果/配方存入 RAG，Agent 查询时按需检索，不占常驻 context

### 🟢 P3 — 长期探索

#### 更丰富的社会系统

- NPC 间形成派系、联盟、竞争关系（已有关系系统基础）
- 长期记忆驱动的仇恨/友谊演化（RAG 加强）
- NPC 可以雇佣/被雇佣、组队采集

#### 世界规模扩大

- 地图扩展（当前 20×20，可扩展到 40×40+）
- 多区域/多生态（沙漠、雪地、海洋区域，各有特产资源）
- 跨区域贸易路线

#### 玩家叙事深度

- 玩家角色有身份背景（初始设定：商人/探险者/工匠）
- 任务系统：NPC 主动向玩家提出请求
- 玩家声望系统（对不同 NPC 群体的好感度）

---

## 技术选型说明

| 方向 | 当前选择 | 理由 |
|------|---------|------|
| 后端语言 | Python | LLM API 生态最成熟，瓶颈是 API 延迟而非计算性能，无需迁移 |
| LLM 框架 | 自研（Pydantic + Gemini native） | 清晰可控，LangChain 抽象过厚、版本变化剧烈，不引入 |
| 前端渲染 | HTML Canvas → 计划迁移 Phaser.js | Phaser 是最低迁移成本的升级路径，Unreal/Unity 对 2D Tile 过度工程 |
| Agent 框架 | 自研三层架构 | 游戏场景特殊，通用 Agent 框架（AutoGen/CrewAI）不适配实时游戏循环 |

---

<div align="center">

Made with ☕ + 🤖 · Powered by [Google Gemini](https://ai.google.dev/) & [FastAPI](https://fastapi.tiangolo.com/)

</div>
