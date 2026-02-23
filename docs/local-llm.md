# 🖥️ 本地 LLM 配置指南

[← 返回主页](../README.md)

本指南介绍如何将 AgentHome 的 AI 后端切换为本地运行的大语言模型，实现**完全离线、零 API 费用**运行。

---

## 目录

- [工作原理](#工作原理)
- [模型要求](#模型要求)
- [支持的服务](#支持的服务)
- [Ollama 配置（推荐）](#ollama-配置推荐)
- [LM Studio 配置](#lm-studio-配置)
- [llama.cpp server 配置](#llamacpp-server-配置)
- [vLLM 配置](#vllm-配置)
- [推荐模型列表](#推荐模型列表)
- [在网页 UI 中切换](#在网页-ui-中切换)
- [通过 .env 配置](#通过-env-配置)
- [常见问题](#常见问题)

---

## 工作原理

AgentHome 使用 [openai](https://pypi.org/project/openai/) Python 包连接本地模型。主流本地 LLM 服务（Ollama、LM Studio 等）都提供与 OpenAI API 兼容的接口，因此无需任何适配层即可直接使用。

```
AgentHome (openai.AsyncOpenAI)
    │
    │  HTTP  POST /v1/chat/completions
    ▼
本地 LLM 服务（Ollama / LM Studio / llama.cpp…）
    │
    ▼
本地模型（llama3 / qwen2.5 / mistral…）
```

切换提供商只需在 **⚙ 设置** 面板点击一个按钮，或修改 `.env` 文件，**无需重启服务器**。

---

## 模型要求

> ⚠️ **关键要求**：本地模型必须支持 **JSON 输出模式**（`response_format: json_object`）

NPC 的所有决策都以结构化 JSON 格式返回。如果模型不支持 JSON 模式，输出将经常解析失败，NPC 会退化为默认行为（休息/随机移动）。

**判断模型是否支持 JSON 模式的方法：**
- 查看服务文档，确认支持 `response_format: {"type": "json_object"}`
- 以 Ollama 为例：大多数指令微调（Instruct）版本的模型均支持
- 若不确定，可先尝试运行，观察终端日志中是否频繁出现 `JSON parse error`

**其他要求：**
- 模型参数量建议 **7B 以上**，以保证决策质量
- 推荐使用 **指令微调（Instruct/Chat）** 版本，而非基础（Base）版本
- 上下文窗口建议 **8k tokens** 以上

---

## 支持的服务

| 服务 | 默认 Base URL | 特点 |
|------|--------------|------|
| **Ollama** | `http://localhost:11434/v1` | 最易上手，命令行管理模型，跨平台 |
| **LM Studio** | `http://localhost:1234/v1` | 图形界面，支持 GGUF，适合 Windows/Mac |
| **llama.cpp server** | `http://localhost:8080/v1` | 极度轻量，低配设备首选 |
| **vLLM** | `http://localhost:8000/v1` | 高吞吐，适合 GPU 服务器 |
| **Xinference** | `http://localhost:9997/v1` | 支持多种后端（vLLM/llama.cpp/transformers） |
| **其他兼容服务** | 自定义 | 只要实现 `/v1/chat/completions` 即可 |

---

## Ollama 配置（推荐）

### 安装 Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 下载安装包：https://ollama.com/download/windows
```

### 拉取并运行模型

```bash
# 拉取推荐模型（约 4-8 GB）
ollama pull llama3.1          # 推荐，综合性能好
ollama pull qwen2.5:7b        # 中文理解更好
ollama pull mistral-nemo      # 轻量且能力强

# 验证模型可用
ollama list

# 启动 Ollama 服务（通常开机自启，也可手动）
ollama serve
```

### 验证 API 可用性

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1",
    "messages": [{"role": "user", "content": "hello"}],
    "response_format": {"type": "json_object"}
  }'
```

若返回 JSON 格式的响应，则配置成功。

### 在 AgentHome 中使用

在 `.env` 中：
```
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.1
```

或直接在网页 **⚙ 设置** 面板中填入上述信息。

---

## LM Studio 配置

### 安装与启动

1. 下载 [LM Studio](https://lmstudio.ai/)（支持 Windows / macOS / Linux）
2. 在模型库中下载所需模型（推荐 `Meta-Llama-3.1-8B-Instruct-GGUF`）
3. 左侧菜单选择 **Local Server** → 点击 **Start Server**

默认监听 `http://localhost:1234`

### 在 AgentHome 中使用

```
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=meta-llama-3.1-8b-instruct  # 与 LM Studio 中加载的模型名一致
```

> **提示**：LM Studio 的模型名需与 UI 中显示的模型标识符匹配，通常可在服务器日志中找到。

---

## llama.cpp server 配置

适合需要极致轻量或自定义编译的场景。

```bash
# 编译（参考官方文档）
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make

# 启动服务器（GGUF 格式模型）
./llama-server \
  -m /path/to/model.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 8192          # 上下文窗口
```

```
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8080/v1
LOCAL_LLM_MODEL=llama3   # llama.cpp server 通常忽略此字段，填任意值即可
```

---

## vLLM 配置

适合有 NVIDIA GPU 的服务器，吞吐量远超 CPU 推理。

```bash
pip install vllm

python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

```
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8000/v1
LOCAL_LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

---

## 推荐模型列表

以下模型经过验证，JSON 输出格式良好，适合 AgentHome：

| 模型 | 参数量 | 特点 | Ollama 命令 |
|------|--------|------|------------|
| `llama3.1` | 8B | 综合能力强，英文为主 | `ollama pull llama3.1` |
| `llama3.2` | 3B | 轻量，低配设备可用 | `ollama pull llama3.2` |
| `qwen2.5:7b` | 7B | 中英双语，JSON 合规性优秀 | `ollama pull qwen2.5:7b` |
| `qwen2.5:14b` | 14B | 更强的推理和创意能力 | `ollama pull qwen2.5:14b` |
| `mistral-nemo` | 12B | 推理能力强，上下文长 | `ollama pull mistral-nemo` |
| `deepseek-r1:8b` | 8B | 推理型，决策质量高 | `ollama pull deepseek-r1:8b` |
| `gemma2:9b` | 9B | Google 出品，指令遵循好 | `ollama pull gemma2:9b` |

**不推荐使用：**
- 基础（Base）模型，非指令微调版本
- 参数量低于 3B 的模型（决策质量差）
- 不支持 JSON 模式的旧版模型

---

## 在网页 UI 中切换

1. 打开 `http://localhost:8000`
2. 点击右侧 **⚙ 设置** 标签页
3. 在 LLM 提供商区域点击 **🖥 本地模型** 按钮
4. 填入 **Base URL**（如 `http://localhost:11434/v1`）
5. 填入 **模型名**（如 `qwen2.5:7b`）
6. 点击 **保存设置**

切换立即生效，正在进行的 LLM 调用完成后，新调用将使用新配置。

---

## 通过 .env 配置

在项目根目录的 `.env` 文件中：

```bash
# 使用本地模型
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b

# （可选）同时保留 Gemini Key，方便随时切换回云端
GEMINI_API_KEY=AIzaSy...
```

修改 `.env` 后需重启服务器才能生效（区别于网页 UI 的热更新）。

---

## 常见问题

### Q: NPC 频繁 `JSON parse error`，不做任何动作

**原因**：模型输出不符合 JSON 格式，或输出了额外的解释文字。

**解决方案**：
1. 确认模型支持 `response_format: json_object`
2. 换用更大参数量的模型（≥7B）
3. 换用 JSON 合规性更好的模型（如 `qwen2.5`）

---

### Q: 连接超时，`LLM call failed: Connection refused`

**原因**：本地服务未启动，或端口/URL 配置错误。

**解决方案**：
1. 确认本地服务正在运行（`ollama serve` / LM Studio 已启动）
2. 在浏览器中访问 `http://localhost:11434`，确认服务响应
3. 检查 Base URL 是否正确（注意是否包含 `/v1` 后缀）

---

### Q: 响应速度很慢，NPC 决策间隔很长

**原因**：CPU 推理速度慢（无 GPU 加速）。

**解决方案**：
1. 使用更小的模型（3B–7B）
2. 使用量化版本（Q4_K_M 精度，体积和速度均有改善）
3. 增大 `NPC_MIN_THINK_SECONDS` 和 `NPC_MAX_THINK_SECONDS`，与模型响应速度匹配：
   ```python
   # config.py
   NPC_MIN_THINK_SECONDS = 15  # 给本地模型更多时间
   NPC_MAX_THINK_SECONDS = 30
   ```

---

### Q: 本地模型时 Token 计数显示 0 或不变

**原因**：部分本地服务不返回 `usage` 字段。

**说明**：Token 计数只影响 **Token 限额** 功能。使用本地模型时，Token 限额不是必须关注的指标（没有 API 费用），可以将限额设置为一个很大的值（如 999,999,999）或不关注该功能。

---

### Q: 如何同时使用多个本地模型（不同 NPC 用不同模型）？

当前版本所有 agent 共享同一个 `LOCAL_LLM_MODEL` 配置，不支持按 NPC 单独配置。

如需此功能，可以考虑：
- 使用支持模型路由的中间层（如 [LiteLLM](https://github.com/BerriAI/litellm)）
- 在代码层面修改 `NPCAgent` 和 `GodAgent` 的初始化，为每个 agent 传入不同的模型名