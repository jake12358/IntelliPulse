# IntelliPulse

IntelliPulse 是一个面向竞品资料分析的 AI 应用：用户上传多个竞品文档后，系统会完成文档解析、去重、切片、检索增强生成、流式分析、引用片段展示，并生成按竞品切换的竞争力仪表盘。

## 目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [配置说明](#配置说明)
- [启动与停止](#启动与停止)
- [使用流程](#使用流程)
- [核心功能](#核心功能)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [核心接口](#核心接口)
- [数据存储](#数据存储)
- [诊断与排错](#诊断与排错)
- [当前边界与后续方向](#当前边界与后续方向)

## 快速开始

推荐在 WSL2 / Linux 环境运行。Windows 原生 PowerShell 可用于查看代码，但 Node、Python、Docker 的路径和权限问题更容易在 WSL2 中统一处理。

```bash
cd /mnt/g/IntelliPulse

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

编辑 `.env`，至少填写 DashScope API Key：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
```

启动 Redis 与 PostgreSQL：

```bash
docker compose up -d
```

安装前端依赖。项目要求 Node.js 20 或更高版本：

```bash
cd frontend
nvm install 20
nvm use 20
npm install
cd ..
```

启动项目：

```bash
bash start.sh
```

启动成功后访问：

- 前端页面：http://localhost:5173/
- 后端健康检查：http://localhost:8000/health
- 后端接口文档：http://localhost:8000/docs
- Redis Stack 控制台：http://localhost:8001/

停止项目：

```bash
bash stop.sh
```

## 环境要求

- Python 3.11
- Node.js >= 20
- Docker 与 Docker Compose
- DashScope API Key
- 推荐 WSL2 / Linux shell

## 配置说明

项目当前只保留 DashScope 作为大模型接入方，配置项保持简洁。

`.env.example` 中的主要配置如下：

```env
APP_NAME=IntelliPulse
APP_ENV=development
API_PREFIX=/api

REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/intellipulse
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:123456@localhost:5432/intellipulse

UPLOAD_DIR=data/uploads
PARSED_DIR=data/parsed

LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key_here
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3

EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_DIM=384

CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175
CORS_ORIGIN_REGEX=http://(localhost|127\.0\.0\.1):[0-9]+
```

说明：

- `DASHSCOPE_API_KEY`：真实调用大模型时必须填写。
- `DASHSCOPE_MODEL`：默认使用 `qwen-plus`。
- `EMBEDDING_PROVIDER=local`：默认使用本地哈希向量，方便低成本本地演示；后续可切换为 DashScope embedding。
- `REDIS_URL`：Redis 用于保存知识切片和向量。
- `DATABASE_URL`：PostgreSQL 用于保存文档和切片元数据。
- `CORS_ORIGIN_REGEX`：允许 Vite 自动切换到 5174、5175 等端口后仍可访问后端。

## 启动与停止

一键启动：

```bash
bash start.sh
```

`start.sh` 会执行以下动作：

- 检查并启动 Docker Compose 中的 Redis / PostgreSQL。
- 检查后端依赖和运行环境。
- 启动 FastAPI 服务，默认端口为 `8000`。
- 检查前端 Node 环境。
- 启动 Vite 前端服务，默认从 `5173` 开始尝试。
- 写入运行期 PID，便于 `stop.sh` 清理。

一键停止：

```bash
bash stop.sh
```

如果浏览器提示 `localhost 拒绝连接`，优先检查：

```bash
bash stop.sh
bash start.sh
curl http://localhost:8000/health
```

如果出现 Vite 语法错误，例如 `SyntaxError: Unexpected token '.'`，通常是 Node 版本过低。请切换到 Node 20+ 后重新执行 `npm install`。

## 使用流程

1. 打开前端页面。
2. 在「资料上传」区域上传竞品文档，支持 PDF、Word、Markdown、TXT 等常见文本资料。
3. 系统会自动保存原始文件、解析文本、去重并生成文档切片。
4. 点击「开始分析」后，当前提交批次的文档 ID 会传给后端。
5. 后端只在本次提交的文档范围内检索切片，不会把历史文档混入当前分析。
6. 分析结果通过 SSE 流式返回到「流式分析」区域。
7. 「本次引用资料切片」展示模型回答实际参考过的文档片段。
8. 「竞争力仪表盘」展示按竞品切换的雷达图和对比表。

## 核心功能

- 文档上传与持久化：上传文件保存到 `data/uploads/`，解析文本保存到 `data/parsed/`。
- 文档去重：使用 SHA-256 文件哈希识别完全相同的文档，避免重复入库。
- 自动分类：通过文件名、内容关键词和 DashScope 辅助判断竞品名称与资料类型。
- 文档切片：将解析后的长文本拆分成可检索片段。
- 向量检索：为切片生成向量，并在本次提交文档范围内召回相关片段。
- 流式分析：使用 Server-Sent Events 返回分析进度和最终报告。
- 引用追踪：前端展示本次分析命中的文档切片，方便判断回答是否基于上传资料。
- 竞品仪表盘：由大模型对不同竞品进行多维度评分，前端以雷达图和表格展示。
- 本地可运行：Redis、PostgreSQL 通过 Docker Compose 提供，前后端可本地启动。

## 系统架构

```mermaid
flowchart LR
    U["用户上传文档"] --> F["React + Ant Design 前端"]
    F -->|POST /api/upload| B["FastAPI 后端"]
    B --> P["文档解析 / 去重 / 切片"]
    P --> R["Redis: 切片文本与向量"]
    P --> PG["PostgreSQL: 文档与切片元数据"]
    F -->|SSE /api/chat/stream| G["LangGraph 风格分析流程"]
    G --> S["检索节点"]
    S --> R
    G --> L["DashScope qwen-plus"]
    L --> F
    G --> D["报告与雷达图数据"]
    D --> F
```

分析流程由 `AgentState` 串联，核心节点包括：

- `supervisor`：决定分析路径和任务上下文。
- `retriever`：在当前提交文档中召回相关切片。
- `comparator`：对竞品能力、定位、优劣势进行对比。
- `sentiment`：补充情绪、口碑、风险倾向分析。
- `reporter`：生成结构化报告和仪表盘数据。

## 项目结构

```text
IntelliPulse/
├── app/                    # FastAPI 后端
│   ├── agents/             # 分析流程状态与节点
│   ├── api/routes/         # HTTP / SSE API
│   ├── core/               # 配置与日志
│   ├── db/                 # Redis / PostgreSQL 连接与仓储
│   ├── llm/                # DashScope 客户端
│   ├── models/             # Pydantic 数据结构
│   ├── services/           # 文档解析、分类、检索、报告服务
│   └── tasks/              # Celery 可选异步任务
├── frontend/               # React + TypeScript 前端
│   └── src/
│       ├── components/     # 上传区、分析窗口、仪表盘
│       ├── services/       # API 调用封装
│       └── types/          # 前端类型定义
├── scripts/                # 诊断、测试、样例导入脚本
├── samples/                # 示例资料
├── data/                   # 本地运行期数据，默认不提交到 Git
├── docker-compose.yml      # Redis Stack 与 PostgreSQL
├── start.sh                # 一键启动脚本
├── stop.sh                 # 一键停止脚本
└── PROJECT_STRUCTURE.md    # 更细的工程结构说明
```

更详细的模块职责、核心函数与数据流见 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)。

## 核心接口

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/health` | GET | 后端健康检查 |
| `/api/upload` | POST | 上传、保存、解析、去重并切片文档 |
| `/api/chat/stream` | GET | SSE 流式分析接口 |
| `/api/report/{session_id}` | GET | 获取指定会话的报告结果 |
| `/api/knowledge/documents` | GET | 获取本次提交与历史文件摘要 |
| `/api/diagnostics/storage` | GET | 检查 Redis / PostgreSQL / 本地文件状态 |

## 数据存储

本地运行时会产生以下数据：

- `data/uploads/`：上传的原始文件。
- `data/parsed/`：解析后的文本文件。
- `data/documents.json`：轻量文档注册表，保存哈希、文件路径、文档类型等信息。
- Redis：保存 `chunk:<chunk_id>` 形式的切片 JSON，包含切片文本、向量、来源文档、竞品标签等。
- PostgreSQL：保存文档与切片元数据，方便统计、诊断和后续扩展。

当前检索逻辑以 Redis 中的切片为主，并通过前端传入的 `document_ids` 保证每次分析只使用本次提交的资料。PostgreSQL 已接入真实写入，用于结构化元数据管理；后续可继续扩展为任务记录、用户空间、分析历史和审计日志。

## 诊断与排错

检查后端基础状态：

```bash
curl http://localhost:8000/health
```

检查 Redis、PostgreSQL、本地文件状态：

```bash
python scripts/diagnose_storage.py
curl http://localhost:8000/api/diagnostics/storage
```

测试 DashScope Key：

```bash
python scripts/test_dashscope.py
```

导入示例资料：

```bash
python scripts/ingest_samples.py
```

常见问题：

- `node: not found`：当前 shell 找不到 Node，请在同一个 WSL shell 中执行 `nvm use 20`。
- `SyntaxError: Unexpected token '.'`：Node 版本过低，请切换到 Node 20+。
- Vite 自动切到 5174 / 5175：说明 5173 被占用，项目已通过 CORS 正则允许这些端口。
- PostgreSQL 权限错误：不要把 PostgreSQL 数据目录绑定到 `/mnt/g` 等 Windows 挂载目录，项目已改用 Docker named volume。
- Celery Redis transport unavailable：Celery 是可选异步能力；当前上传任务可回退为本地同步执行，不影响核心分析链路。

## 当前边界与后续方向

- 默认 embedding 使用本地哈希向量，适合低成本演示；生产环境建议切换为真实语义向量模型。
- Redis 当前作为切片与向量存储，检索由后端扫描并计算相似度；后续可接入 RediSearch / RedisVL 的原生 KNN 索引。
- PostgreSQL 已保存结构化元数据，后续可扩展用户体系、任务队列、分析版本、报告归档。
- 当前项目定位为本地演示与简历项目，不包含生产级鉴权、限流、租户隔离和完整监控。
