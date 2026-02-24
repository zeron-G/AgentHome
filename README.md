# 🏘️ AgentHome — LLM 驱动的 AI 沙盒世界

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-✓-4285F4?style=flat-square&logo=google&logoColor=white)
![Local LLM](https://img.shields.io/badge/Local_LLM-Ollama_/_LM_Studio-F97316?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)

**一个 2D 沙盒 AI 世界：4 个 NPC + 1 个上帝，每个角色由大语言模型独立控制。**

NPC 自主决策、互相交谈、采集资源、在城镇交易所买卖，一切通过浏览器实时可视化。

</div>

---

## 功能特性

| 类别 | 特性 |
|------|------|
| 🤖 **AI 控制** | 4 NPC + 1 上帝，各有独立记忆与个性，每 5–10s 自主决策一次 |
| 🌐 **双 LLM 后端** | Google Gemini（云端）或任意 OpenAI 兼容本地服务（Ollama / LM Studio / vLLM…） |
| 🏘️ **城镇与交易所** | 中央城镇 + 交易所：卖资源换金币、花金币买食物 |
| 🌾 **食物系统** | 食物灌木丛、吃食物/睡眠回血、体力归零自动进食 |
| ⚡ **实时可视化** | WebSocket 驱动，HTML5 Canvas 渲染地块/NPC/气泡/天气粒子 |
| 🎮 **上帝控制** | 浏览器界面直接控制天气、刷新资源，无需 LLM |
| ⚙️ **网页设置** | API Key、模型、Token 限额、LLM 提供商，热更新无需重启服务器 |
| 📊 **Token 追踪** | 实时进度条，超限自动暂停，可动态扩额续跑 |

---

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥（可选，也可在网页 UI 中设置）

```bash
# 复制模板并填入你的 Gemini API Key
cp .env.example .env
# 编辑 .env，填入 GEMINI_API_KEY=AIzaSy...
```

> 如果使用本地模型，请参阅 [本地 LLM 配置指南 →](docs/local-llm.md)

### 3. 启动服务器

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 打开浏览器

访问 
**http://localhost:8000**
，游戏自动开始。

首次启动若未配置密钥，点击右侧 **⚙ 设置** 标签页，输入 Gemini API Key 或配置本地模型后保存即可。

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
│   └── world_manager.py # 世界状态变更（所有动作处理器）
│
├── agents/
│   ├── base_agent.py    # LLM 基类（Gemini / 本地双后端，懒加载，热更新）
│   ├── npc_agent.py     # NPC 决策代理
│   ├── god_agent.py     # 上帝决策代理
│   └── prompts.py       # 提示词模板 + Pydantic 动作 Schema
│
├── game/
│   ├── loop.py          # 异步游戏主循环（独立 brain loop）
│   ├── events.py        # 事件类型、WorldEvent、EventBus
│   └── token_tracker.py # Token 统计与限额控制
│
├── ws/
│   ├── manager.py       # WebSocket 连接池 + 广播
│   └── serializer.py    # World → 紧凑 JSON
│
├── frontend/
│   └── index.html       # 单文件前端（Canvas + 5 选项卡面板：世界、经济、NPC、地图编辑器、设置）
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

## 详细文档

| 文档 | 内容 |
|------|------|
| [🏗️ 架构设计](docs/architecture.md) | 异步并发模型、LLM 双后端调度、事件系统、游戏循环 |
| [🖥️ 本地 LLM 指南](docs/local-llm.md) | Ollama / LM Studio / vLLM 配置，模型推荐，常见问题 |
| [🌍 世界系统](docs/world.md) | 地块类型、资源系统、食物系统、城镇与交易所 |
| [📦 模块详解](docs/modules.md) | 每个 Python 模块的数据结构与方法说明 |
| [📡 API 参考](docs/api-reference.md) | REST API、WebSocket 消息格式、NPC/上帝动作 Schema |
| [⚙️ 配置参考](docs/config.md) | `config.py` 所有常量的默认值与说明 |

---

## Token 用量估算

| 模型 | 约 tokens/NPC/决策 | 200k 限额可运行 |
|------|-------------------|----------------|
| gemini-2.5-flash | ~800–1,200 | 约 30–60 分钟 |
| gemini-2.0-flash | ~600–1,000 | 约 40–70 分钟 |
| 本地模型 | 不计入限额 | 不受限制 |

---

<div align="center">

Made with ☕ + 🤖 · Powered by [Google Gemini](https://ai.google.dev/) & [FastAPI](https://fastapi.tiangolo.com/)

</div>