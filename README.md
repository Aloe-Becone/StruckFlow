# StruckFlow

结构化多智能体对话应用 —— 基于 LangChain + LangGraph 的多 Agent 协作框架，实现任务分配、资料搜索、任务执行、总结验证的完整工作流。

## 项目架构

```
StruckFlow/
├── LangChain/              # Python 后端核心
│   ├── agents/             # 多 Agent 工作流（LangGraph 状态图）
│   ├── comparison/         # 模型对比评测
│   ├── framework/          # 配置、LLM 构建、工具函数
│   ├── memory/             # 共享记忆存储（语义/关键词/标签检索）
│   ├── metrics/            # 性能指标记录
│   ├── protocol/           # SemanticObject 三层协议（G2CP）
│   ├── tools/              # SearXNG 网络搜索工具
│   ├── test/               # CUDA / SearXNG 测试
│   ├── main.py             # CLI 交互入口
│   └── .env.example        # 环境变量模板
├── web/
│   ├── flask/              # Flask REST API 后端
│   └── vue/                # Vue 3 + Element Plus 前端
└── packaging/              # openEuler RPM 打包与部署脚本
```

### 核心特性

- **多 Agent 协作**：任务分配 → 资料搜索 → 任务执行 → 总结验证，四 Agent 状态图驱动
- **G2CP 协议**：Control / Semantic / Precise 三层结构，零 token 路由 + 精确执行
- **共享记忆**：语义向量检索 + 关键词匹配 + 标签过滤，跨会话知识积累
- **模型对比**：内置文本评测模式，支持多模型横向对比

## 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.11 | 后端运行时 |
| Node.js | >= 18 | 前端构建 |
| PyTorch | >= 2.1 | Embedding 模型推理 |
| SearXNG | - | 网络搜索（可选） |

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Aloe-Becone/StruckFlow && cd StruckFlow
```

### 2. 配置环境变量

```bash
cp LangChain/.env.example LangChain/.env
vim LangChain/.env
```

**必须配置以下项**：

```env
# LLM API（二选一或同时配置）
OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=实际API地址
OPENAI_MODEL=gpt-5.5

DEEPSEEK_API_KEY=你的API_KEY
DEEPSEEK_BASE_URL=实际API地址
DEEPSEEK_MODEL=deepseek-v4-flash

# 本地 Embedding 模型路径（必须）
EMBEDDING_MODEL_PATH=/path/to/your/embedding/model
```

> **重要**：项目使用 `sentence-transformers` 加载本地 Embedding 模型（默认 Qwen 系列），你需要自行下载模型到本地，并将 `EMBEDDING_MODEL_PATH` 指向模型目录。详见下方 [Embedding 模型部署](#embedding-模型部署)。

### 3. 安装 Python 依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r LangChain/requirements.txt
```

### 4. 构建前端

```bash
cd web/vue
npm install
npm run build
cd ../..
```

### 5. 运行

```bash
# CLI 交互模式
source .venv/bin/activate
python LangChain/main.py

# Flask API 服务
python web/flask/app.py

# 前端开发服务器
cd web/vue && npm run dev
```

## Embedding 模型部署

项目的共享记忆功能依赖本地 Embedding 向量模型进行语义检索。你需要：

### 下载模型

推荐使用 Qwen 系列 Embedding 模型（项目默认适配）：

```bash
# 方式一：从 HuggingFace 下载
git lfs install
git clone https://huggingface.co/Qwen/Qwen3-Embedding-0.6B ./models/Qwen3-Embedding-0.6B

# 方式二：从 ModelScope 下载（国内更快）
pip install modelscope
modelscope download --model Qwen/Qwen3-Embedding-0.6B --local_dir ./models/Qwen3-Embedding-0.6B
```

### 配置 .env

将 `EMBEDDING_MODEL_PATH` 指向下载的模型目录：

```env
EMBEDDING_MODEL_PATH=models/Qwen3-Embedding-0.6B
EMBEDDING_BATCH_SIZE=8
EMBEDDING_NORMALIZE=true
EMBEDDING_SHOW_PROGRESS=false
```

### GPU 加速（可选）

如有 NVIDIA GPU，安装 CUDA 版 PyTorch 可显著加速向量计算：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

验证 CUDA 可用：

```bash
python LangChain/test/test-cuda.py
```

## openEuler 部署

项目提供完整的 openEuler 24.03-LTS-SP3 RPM 打包方案，详见 [packaging/README-packaging.md](packaging/README-packaging.md)。

快速部署：

```bash
# 一键部署（生产模式）
sudo bash packaging/setup-openeuler.sh --prod

# 或构建 RPM 包
bash packaging/build-rpm.sh
sudo dnf install -y ./packaging/struckflow-*.rpm
```

## 许可证

[MIT License](LICENSE)