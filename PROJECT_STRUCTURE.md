# IntelliPulse 项目结构说明

本文档只描述当前项目的工程结构、核心数据结构、关键函数和模块之间的关系。部署、启动和使用流程统一维护在 `README.md`。

## 1. 总体分层

```text
IntelliPulse/
├── app/                    # 后端主应用
├── frontend/               # 前端主应用
├── scripts/                # 诊断、测试、样例导入脚本
├── samples/                # 示例竞品资料
├── data/                   # 本地运行期数据，不建议提交到 Git
├── docker-compose.yml      # Redis Stack / PostgreSQL
├── start.sh                # 本地启动脚本
├── stop.sh                 # 本地停止脚本
└── .env.example            # 环境变量模板
```

核心链路是：

```text
上传文档
  -> FastAPI 接收文件
  -> 保存原始文件
  -> 解析文本
  -> SHA-256 去重
  -> 文档分类
  -> 文本切片
  -> 生成向量
  -> Redis 保存切片
  -> PostgreSQL 保存元数据
  -> 前端发起当前批次分析
  -> 检索当前批次切片
  -> DashScope 生成流式分析
  -> 前端展示报告、引用切片、仪表盘
```

## 2. 后端结构

```text
app/
├── main.py
├── agents/
│   ├── graph.py
│   ├── state.py
│   └── nodes/
├── api/routes/
├── core/
├── db/
├── llm/
├── models/
├── services/
└── tasks/
```

### 2.1 `app/main.py`

后端入口文件，负责创建 FastAPI 应用、注册 CORS、挂载路由和初始化启动事件。

关键职责：

- 创建 `FastAPI` 实例。
- 读取 `app.core.config.settings`。
- 注册 `/health` 健康检查。
- 挂载上传、知识库、报告、诊断、流式分析等 API 路由。
- 在应用启动时确保 PostgreSQL 元数据表可用。

### 2.2 `app/core/config.py`

集中管理环境变量。

核心对象：

- `Settings`：基于 `pydantic-settings` 的配置类。
- `settings`：全局配置实例。

重要字段：

- `REDIS_URL`：Redis 连接地址。
- `DATABASE_URL`：异步 PostgreSQL 连接地址。
- `SYNC_DATABASE_URL`：同步 PostgreSQL 连接地址，供部分诊断或兼容场景使用。
- `UPLOAD_DIR` / `PARSED_DIR`：原始文件和解析文本保存目录。
- `DASHSCOPE_API_KEY` / `DASHSCOPE_MODEL`：DashScope 模型配置。
- `EMBEDDING_PROVIDER`：向量生成方式，当前默认 `local`。

### 2.3 `app/api/routes/upload.py`

文档上传链路的主入口。

核心职责：

- 接收前端上传文件。
- 保存原始文件到 `data/uploads/`。
- 调用解析服务提取文本。
- 计算文件 SHA-256 并进行去重。
- 调用文档分类服务识别竞品名称和资料类型。
- 调用 embedding 服务生成切片向量。
- 将切片写入 Redis。
- 将文档和切片元数据写入 PostgreSQL。
- 返回当前上传批次的 `document_id`、文件名、分类结果和处理状态。

关键点：

- 完全相同的文件不会重复注册为新文档。
- 如果历史文档存在但 Redis 切片丢失，上传流程会尝试重建切片，避免历史索引损坏后无法检索。
- 前端后续分析会携带本次上传返回的 `document_id`，实现批次隔离。

### 2.4 `app/api/routes/chat.py`

流式分析接口。

核心职责：

- 提供 `/api/chat/stream` SSE 接口。
- 接收用户问题、会话 ID、本次提交的 `document_ids`。
- 初始化 `AgentState`。
- 执行检索、分析、报告生成流程。
- 将阶段性结果以 SSE 事件返回前端。

关键点：

- 检索范围由 `document_ids` 限制。
- 前端不需要等待完整报告生成，可以边生成边展示。
- 返回内容包含分析文本、引用切片、竞品评分和结构化报告数据。

### 2.5 `app/api/routes/knowledge.py`

知识库文件列表接口。

核心职责：

- 返回本次提交文档和历史文件摘要。
- 聚合本地注册表、Redis 切片数、PostgreSQL 元数据计数。
- 供前端「知识库文件」区域展示和刷新。

### 2.6 `app/api/routes/report.py`

报告查询接口。

核心职责：

- 根据 `session_id` 返回已生成的分析报告。
- 为后续报告归档和历史分析回看预留接口形态。

### 2.7 `app/api/routes/diagnostics.py`

运行状态诊断接口。

核心职责：

- 检查本地文件目录是否存在。
- 检查 Redis 是否可连接以及切片数量。
- 检查 PostgreSQL 是否可连接以及文档、切片元数据数量。
- 帮助定位「上传成功但检索不到切片」这类问题。

## 3. 服务层

```text
app/services/
├── document_classifier.py
├── document_registry.py
├── embedding_service.py
├── parsing_service.py
├── reporting_service.py
└── search_service.py
```

### 3.1 `parsing_service.py`

负责从文件中抽取纯文本。

典型输入：

- PDF
- Word
- Markdown
- TXT

典型输出：

- 解析后的字符串文本。
- 保存到 `data/parsed/` 的文本文件。

该模块位于上传链路前半段，是后续分类、切片、检索的基础。

### 3.2 `document_registry.py`

本地轻量文档注册表。

核心职责：

- 计算并记录文件哈希。
- 维护 `data/documents.json`。
- 根据 SHA-256 判断文档是否重复。
- 记录原始文件路径、解析文本路径、竞品名称、资料类型、切片数量等元信息。

该注册表让项目即使在 PostgreSQL 暂时不可用时，也能保留基本文档状态。

### 3.3 `document_classifier.py`

文档分类服务。

核心职责：

- 从文件名、文本关键词中推断竞品名称。
- 从内容结构中推断资料类型。
- 在 DashScope 可用时使用模型辅助分类。

输出会影响：

- 前端文件标签。
- 仪表盘竞品维度。
- 后续检索切片的来源展示。

### 3.4 `embedding_service.py`

向量服务。

核心职责：

- 将文本切片转换为固定维度向量。
- 当前默认使用本地哈希向量，便于低成本运行和演示。
- 保留 DashScope embedding 配置项，方便后续切换为真实语义向量。

当前本地向量的优点是稳定、无需额外费用；缺点是语义能力弱于真实 embedding 模型。

### 3.5 `search_service.py`

检索服务。

核心职责：

- 从 Redis 读取 `chunk:<chunk_id>` 切片。
- 根据查询文本生成查询向量。
- 对候选切片计算相似度。
- 按 `document_ids` 限制检索范围。
- 返回最相关的切片列表。

关键设计：

- 当前分析只检索本次提交的文档，不自动混入历史文档。
- Redis 保存的是检索主数据，PostgreSQL 保存结构化元数据。
- 未来可将 Python 侧相似度计算替换为 RediSearch / RedisVL KNN 检索。

### 3.6 `reporting_service.py`

报告与仪表盘数据服务。

核心职责：

- 整理模型输出。
- 生成竞品对比表。
- 生成前端雷达图所需的结构化评分。
- 对 DashScope 返回异常或数据缺失的情况提供兜底结果。

评分数据来自模型对竞品材料的综合判断，而不是简单固定公式；这样能让不同竞品在能力维度上表现出差异。

## 4. Agent 分析流程

```text
app/agents/
├── state.py
├── graph.py
└── nodes/
    ├── supervisor.py
    ├── retriever_node.py
    ├── comparator_node.py
    ├── sentiment_node.py
    └── reporter_node.py
```

### 4.1 `state.py`

定义分析流程共享状态 `AgentState`。

常见字段包括：

- 用户问题。
- 会话 ID。
- 当前提交的文档 ID 列表。
- 检索命中的切片。
- 竞品分析结果。
- 情绪与风险分析结果。
- 最终报告。
- 仪表盘评分数据。

### 4.2 `graph.py`

定义分析节点的执行顺序。

当前流程可以理解为：

```text
supervisor
  -> retriever
  -> comparator
  -> sentiment
  -> reporter
```

### 4.3 `nodes/supervisor.py`

负责初始化分析上下文，判断本次任务应该如何组织。

### 4.4 `nodes/retriever_node.py`

调用 `search_service`，从当前提交的文档切片中召回上下文。

这是保证 RAG 真正参考上传资料的关键节点。

### 4.5 `nodes/comparator_node.py`

调用 DashScope，对不同竞品的定位、能力、优劣势进行分析。

### 4.6 `nodes/sentiment_node.py`

补充市场反馈、用户口碑、风险倾向等分析。

### 4.7 `nodes/reporter_node.py`

汇总前面节点的结果，生成最终报告、引用材料和仪表盘数据。

## 5. 数据库与缓存层

```text
app/db/
├── postgres.py
├── redis_client.py
└── repository.py
```

### 5.1 `redis_client.py`

负责 Redis 连接。

当前 Redis 的实际作用：

- 保存文档切片。
- 保存每个切片的向量。
- 保存切片来源文档、竞品名称、资料类型等上下文。
- 为 RAG 检索提供主数据来源。
- 作为 Celery 异步任务的 broker/backend 目标配置。

典型 key：

```text
chunk:<chunk_id>
```

典型 value：

```json
{
  "chunk_id": "doc_xxx_chunk_0",
  "document_id": "doc_xxx",
  "filename": "feishu_intro.pdf",
  "competitor": "飞书",
  "doc_type": "官网简介",
  "text": "切片正文...",
  "embedding": [0.12, 0.03, "..."]
}
```

### 5.2 `postgres.py`

负责 PostgreSQL 连接和表初始化。

当前使用 SQLAlchemy async engine，配合 Docker Compose 中的 PostgreSQL 15。

### 5.3 `repository.py`

PostgreSQL 仓储层。

当前 PostgreSQL 的实际作用：

- 保存文档元数据。
- 保存切片元数据。
- 支持统计文档数、切片数。
- 支持诊断接口判断数据库是否正常。

PostgreSQL 暂不承担全文检索或向量检索主职责，但它已经是结构化元数据的事实来源之一。

## 6. 大模型层

```text
app/llm/
└── dashscope_client.py
```

### `dashscope_client.py`

负责封装 DashScope 调用。

核心职责：

- 读取 DashScope API Key 和模型名。
- 发送分析提示词。
- 返回文本或结构化结果。
- 在 API Key 缺失或调用失败时抛出可诊断异常，由上层决定是否降级。

项目当前只保留 DashScope 配置，避免多套模型配置造成使用困惑。

## 7. 数据模型

```text
app/models/
└── schemas.py
```

常见数据结构：

- 上传响应：文件名、文档 ID、是否重复、竞品名称、资料类型、切片数量。
- 检索切片：切片 ID、来源文档、正文、相似度、竞品标签。
- 分析报告：会话 ID、分析文本、引用切片、竞品表格、雷达图评分。
- 诊断响应：Redis、PostgreSQL、本地目录状态。

这些 Pydantic schema 是后端接口与前端 TypeScript 类型之间的契约基础。

## 8. 前端结构

```text
frontend/src/
├── App.tsx
├── main.tsx
├── styles.css
├── components/
│   ├── UploadZone.tsx
│   ├── ChatWindow.tsx
│   └── Dashboard.tsx
├── services/
│   └── api.ts
└── types/
    └── index.ts
```

### 8.1 `App.tsx`

前端主页面，负责组织三个核心卡片：

- 资料上传。
- 竞争力仪表盘。
- 流式分析。

同时负责在上传、分析、刷新之间传递状态。

### 8.2 `UploadZone.tsx`

资料上传与知识库展示组件。

核心职责：

- 文件选择与删除。
- 上传进度展示。
- 本次提交 / 历史文件切换展示。
- 分析开始后清空待提交文件，避免分析过程中继续修改本次批次。
- 刷新知识库文件状态。

### 8.3 `ChatWindow.tsx`

流式分析组件。

核心职责：

- 发起 SSE 分析请求。
- 展示模型流式输出。
- 渲染 Markdown 风格内容。
- 展示本次引用资料切片。
- 分析开始时通知父组件重置上传区和仪表盘状态。

### 8.4 `Dashboard.tsx`

竞争力仪表盘组件。

核心职责：

- 展示按竞品切换的雷达图。
- 展示竞品评分和分析表格。
- 在新分析开始时重置旧数据。
- 在返回新结果后更新当前批次竞品数据。

### 8.5 `services/api.ts`

前端 API 封装。

核心职责：

- 上传文件。
- 获取知识库文件列表。
- 建立 SSE 连接。
- 获取报告和诊断数据。

## 9. 脚本目录

```text
scripts/
├── diagnose_runtime.py
├── diagnose_storage.py
├── ingest_samples.py
├── test_dashscope.py
└── test_phase1.py
```

- `diagnose_runtime.py`：检查 Python、依赖、环境变量等运行环境。
- `diagnose_storage.py`：检查 Redis、PostgreSQL、本地文件与切片状态。
- `ingest_samples.py`：导入 `samples/` 中的示例资料。
- `test_dashscope.py`：验证 DashScope Key 与模型调用是否正常。
- `test_phase1.py`：早期阶段链路测试脚本。

## 10. 运行期数据目录

```text
data/
├── uploads/
├── parsed/
├── redis/
└── documents.json
```

- `uploads/`：原始上传文件。
- `parsed/`：解析后的文本。
- `redis/`：Redis Stack 本地持久化数据。
- `documents.json`：轻量文档注册表。

这些内容属于本地运行期数据，默认通过 `.gitignore` 排除。

## 11. 关键设计关系

### 11.1 批次隔离

前端上传成功后会持有本次提交的 `document_id` 列表。点击分析时，这些 ID 会传给 `/api/chat/stream`。后端检索节点只在这些文档对应的切片中召回上下文。

效果：

- 上一次提交的资料不会进入本次分析。
- 历史文件可以展示，但不会默认污染当前报告。
- 仪表盘只展示本次分析返回的竞品结果。

### 11.2 去重与重建

系统通过 SHA-256 判断文件内容是否完全相同。

效果：

- 相同文件不会重复保存为多份业务文档。
- 如果文档注册表存在但 Redis 切片缺失，上传链路会尝试基于原始文件重新解析和切片。

### 11.3 引用可追踪

检索命中的切片会随分析结果返回前端。

效果：

- 用户可以直观看到模型参考了哪些资料。
- 可以判断回答是否真的基于上传文档。
- 有助于定位“模型输出了文档外内容”的问题。

### 11.4 Redis 与 PostgreSQL 分工

Redis 偏向高频检索数据，PostgreSQL 偏向结构化元数据。

当前分工：

- Redis：切片正文、向量、来源信息，是 RAG 检索的主要数据源。
- PostgreSQL：文档元数据、切片元数据、统计和诊断。

后续扩展方向：

- Redis 接入原生 KNN 索引。
- PostgreSQL 增加用户、任务、报告、分析历史等表。
- 将 `documents.json` 逐步收敛为兼容缓存或迁移辅助文件。
