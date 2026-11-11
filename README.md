# 智能购物 Agent

一个基于 LangGraph 的全栈购物助手。用户可以用自然语言搜索和筛选商品、管理购物车与收藏夹、维护收货地址并创建订单；商品说明、活动规则和售后知识通过 RAG 检索回答。

项目面向商品咨询与购物操作场景，覆盖从需求表达、商品匹配到订单创建的关键流程。Agent 不直接发起支付，用户需在订单页面确认；库存和价格等交易事实由业务服务校验，不以缓存结果替代交易判断。

## 功能

- 将自然语言中的商品、品牌、颜色、价格和标签条件解析为结构化意图。
- 使用 LangGraph 编排意图解析、检索和工具执行，并通过动作白名单限制 Agent 可执行操作。
- 支持商品搜索、精确筛选、相似商品推荐，以及按条件批量操作购物车和收藏夹。
- 支持用户注册登录、Token 认证、用户数据隔离和多轮会话。
- 支持收货地址管理、库存检查、订单创建、支付确认后的购物车清理。
- 使用 pgvector 向量检索与关键词候选 RRF 融合提供商品知识问答。
- 提供 Vue 3 前端和 FastAPI REST API。

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router |
| 后端 | Python 3.11、FastAPI、Pydantic、SQLAlchemy |
| Agent | LangGraph、LangChain Core、OpenAI 兼容模型 API |
| 数据 | PostgreSQL、pgvector、Redis（可选） |
| 测试与交付 | Pytest、Alembic、Docker Compose、GitHub Actions |

## 架构概览

```text
Vue 3 前端
    | REST API
FastAPI
    |-- LangGraph Agent --> 意图解析 / 商品检索 / 受控业务工具
    |-- RAG -------------> pgvector + 关键词检索 + RRF
    |-- 业务服务 --------> PostgreSQL
    |-- 会话、限流 ------> Redis（配置后启用）
```

交易写入由业务服务处理并使用数据库事务；库存判断不会使用目录缓存。模型请求的网络异常及部分服务端错误支持有限重试，认证、余额及结构校验错误不会重试。支付由用户在前端完成确认。

## 环境要求

- Python 3.11
- Node.js 18 或更高版本及 npm
- PostgreSQL 17，需启用 pgvector 扩展
- Redis 7（可选；启用共享会话或限流时需要）
- 兼容 OpenAI API 的模型服务及 API Key

## 本地开发

以下命令以 Windows PowerShell 为例。在仓库根目录执行。

### 1. 安装 Python 依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### 2. 配置环境变量

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，填写本机 PostgreSQL 连接信息以及模型服务地址、API Key 和模型名。不要将含有真实密钥的 `.env` 提交到版本库。`REDIS_URL` 留空时使用进程内会话模式；需要 Redis 时填写连接地址。

主要配置项：

| 变量 | 用途 |
| --- | --- |
| `PGHOST`、`PGPORT`、`PGDATABASE`、`PGUSER`、`PGPASSWORD` | PostgreSQL 连接信息 |
| `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` | OpenAI 兼容模型服务配置 |
| `EMBEDDING_MODEL` | RAG 向量化模型 |
| `REDIS_URL` | Redis 地址；留空时使用进程内模式 |
| `REDIS_PREFIX` | Redis 键名前缀 |
| `SESSION_TTL_SECONDS` | 会话过期时间 |
| `RATE_LIMIT_PER_MINUTE` | Agent 与认证接口的每分钟请求限制 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | 可选 OpenTelemetry Collector 地址 |

### 3. 初始化数据库

确保 PostgreSQL 已启动、数据库已创建且 pgvector 可用，然后执行：

```powershell
alembic upgrade head
python -m backend.app.db.init_db --seed-products
```

迁移前请先备份数据库。迁移基线针对新部署准备；对已有业务数据库执行前，应先核对当前 schema 与迁移状态。

### 4. 启动后端

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：<http://127.0.0.1:8000/health>

### 5. 启动前端

在另一个终端执行：

```powershell
cd project/frontend
npm ci
npm run dev
```

按 Vite 输出的本地地址打开前端，通常为 <http://localhost:5173>。

## Docker Compose

Docker Compose 会启动 PostgreSQL、Redis、数据库迁移、API 和前端。先在仓库根目录创建并填写 `.env`，至少设置安全的 `PGPASSWORD`、`LLM_API_KEY` 及模型服务配置，然后执行：

```powershell
docker compose up --build
```

前端入口：<http://127.0.0.1:8080>。停止服务：

```powershell
docker compose down
```

Compose 使用命名卷保存 PostgreSQL、Redis 和评测数据。`docker compose down -v` 会删除这些持久化数据卷，请谨慎使用。

## 测试与构建

在仓库根目录运行后端测试：

```powershell
python -m pytest -q -p no:cacheprovider
```

PostgreSQL 集成测试需要测试数据库配置，缺少相应配置时可能跳过。前端类型检查和生产构建：

```powershell
cd project/frontend
npm ci
npm run build
```

## 项目结构

```text
backend/app/agent/       Agent 状态图、会话、执行器与工具
backend/app/api/         FastAPI 路由与依赖
backend/app/db/          数据库模型、连接与仓储
backend/app/rag/         文档处理、向量及混合检索
backend/app/services/    商品、购物车、收藏夹、库存和订单服务
project/frontend/        Vue 3 前端
migrations/              Alembic 数据库迁移
tests/                   后端单元与集成测试
evaluation_runtime/      Agent 评测、运行指标与报告工具
docs/                    RAG、数据库及工程说明
```

## API 与接口文档

后端启动后可访问 FastAPI 自动生成的接口文档：

- Swagger UI：<http://127.0.0.1:8000/docs>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>

常用路由以 `/api` 为前缀，包含 Agent、商品目录、认证、购物车、收藏夹、地址和订单接口。具体请求结构以 Swagger 文档和路由定义为准。

## 评测

离线评测示例：

```powershell
$env:EVALUATION_DB = "output/evaluation/benchmark.sqlite3"
python -m evaluation_runtime.benchmark --output output/evaluation/shopping-offline
```

只读在线冒烟评测会实际调用模型，并只开放公开目录查询：

```powershell
python -m evaluation_runtime.benchmark --live --output output/evaluation/shopping-live
```

在线评测会产生模型 API 调用和费用，不会执行购物车、订单或支付操作。历史小样本结果见 `output/evaluation/shopping-live.json`；其中成功率和延迟只代表该批次，不代表生产环境质量、并发能力或整体答案准确率。成本估算需要提供并核实模型单价，不能视为服务商账单。

## 安全与当前边界

- 不要提交真实 API Key、数据库密码或个人数据。
- Agent 通过白名单工具执行操作，支付须由用户确认。
- Redis 未配置时使用进程内会话；多实例部署应配置共享 Redis。
- OpenTelemetry 导出需提供 Collector；未配置时不导出到外部服务。
- Docker Compose 和 CI 配置提供部署与自动化入口，具体运行环境仍需单独验证。

## 更多说明

- [工程实现与验证记录](docs/engineering-stack.md)
- [RAG 检索说明](docs/rag.md)
- [PostgreSQL 配置说明](docs/postgresql.md)
- [模型配置说明](docs/llm.md)
