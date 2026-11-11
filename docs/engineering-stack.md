# 智能购物 Agent：LangGraph 工程补齐

流程框架使用 LangGraph 状态图；LangChain Core 工具协议、langchain-openai 和 langchain-postgres 是底层集成，不重复包装为另一套编排框架。已移除未使用的 langchain 和 langchain-community 顶层依赖。

| 能力 | 实现 | 证据 |
|---|---|---|
| Redis 会话 / 可续租锁 | infrastructure/redis_store.py | 双客户端共享、归属、过期、Lua 锁测试通过；独立 Redis 服务未实跑 |
| Redis 原子限流 | Agent / 登录接口 | 429、Retry-After、计数测试；配置后服务异常返回 503 |
| 热点目录缓存 | GET /api/catalog/categories，TTL 60 秒 | SQLAlchemy Async 实际查询；不缓存交易库存/价格 |
| Alembic | 冻结 v1 schema | PostgreSQL 隔离 schema 验证空库、幂等、旧部署补列；未升级现有业务 schema |
| SQLAlchemy Async / httpx | async_session_scope / AsyncClient | 异步提交回滚、API 测试；asyncpg 兼容 Windows 事件循环；现有交易继续同步 |
| 混合检索 | pgvector + 参数化关键词 + RRF | 现有 PostgreSQL 知识库测试通过；关键词候选上限 40 |
| tenacity | 模型网络/408/429/5xx 重试 | 显式重试统计，结构校验/认证/余额错误不重试 |
| OpenTelemetry | Agent/工具 span，模型及 Token attributes | OTLP 导出可配置；Collector 未联调 |
| pytest-asyncio | 异步 API/限流/事务 | 已写入有意义回归测试 |
| Docker Compose / Nginx | 数据库、Redis、迁移、API、前端 | Compose 检查、前端构建通过；Docker 服务未启动，镜像未实跑 |
| GitHub Actions | .github/workflows/ci.yml | 测试与镜像构建配置；未远端执行 |
| 评测 | evaluation_runtime | 实际 LangGraph 流程、工具、Token、耗时 JSON/HTML |

## 本地入口

在 project_final_env 安装 requirements.txt 和 requirements-dev.txt。

    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
    python -m pytest -q -p no:cacheprovider
    alembic upgrade head
    python -m backend.app.db.init_db --seed-products
    docker compose up --build

现有 .env 保留。REDIS_URL 为空使用进程内会话，配置后失败不会静默分裂成本地会话。新部署或需要版本管理时执行迁移，先备份数据库；基线接管已有表，禁用删除式降级。当前没有迁移现有业务 schema。Nginx 映射 http://127.0.0.1:8080，API 不直接暴露宿主端口。

OTEL_EXPORTER_OTLP_ENDPOINT 指向 Collector 基础地址。REDIS_PREFIX、SESSION_TTL_SECONDS、RATE_LIMIT_PER_MINUTE 可配置。

## 评测入口

    $env:EVALUATION_DB="output/evaluation/benchmark.sqlite3"
    python -m evaluation_runtime.benchmark --output output/evaluation/shopping-offline
    python -m evaluation_runtime.benchmark --live --output output/evaluation/shopping-live
    python -m evaluation_runtime --project shopping-langgraph --mode live-readonly --output output/evaluation/report --pricing evaluation_runtime/pricing.example.json

--live 明确执行 4 个模型请求，只暴露公开目录查询，不允许购物车/订单/支付。普通接口默认 live 分组，测试用 test，离线样本独立分组。

任务冗余比较同一请求内相同动作和规范化参数。本项目目前单意图每题一动作，0% 不证明复杂拆分能力。工具调用成功率不等于答案正确率。

成本配置 models 中以模型名为键，填写 input_per_million 和 output_per_million 数字及 currency。未核实价格、usage 缺失、有未知重试费用时显示 N/A，不能当作账单。

本次真实 4 请求：输入 8,407 / 输出 484 Token，4/4 工具成功，P50 4.65 秒，P95 14.31 秒。仅小样本只读流程，不代表所有业务正确率/并发吞吐。完整结果在 output/evaluation/shopping-live.json。
