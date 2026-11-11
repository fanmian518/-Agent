# PostgreSQL + pgvector 基础接入

当前完成的是第二阶段的数据库基础，商品搜索、购物车、收藏夹、订单和 Agent API 仍使用原来的内存服务。执行初始化命令后会将 30 件模拟商品导入数据库，但不会自动切换现有服务的数据来源。

## 文件分工

```text
Project_Final/
├── .env.example                    # 本地数据库配置模板
├── compose.yaml                    # PostgreSQL 17 + pgvector
├── backend/app/db/
│   ├── config.py                   # 读取配置、构造连接地址
│   ├── database.py                 # 连接池和事务会话
│   ├── models.py                   # 商品表
│   └── init_db.py                  # 启用扩展、创建表、导入商品
└── backend/app/rag/vector_store.py  # LangChain PGVector 入口
```

## 1. 准备环境

在项目根目录执行：

```powershell
conda activate project_final_env
python -m pip install -r requirements.txt
python -m pip check
```

Python 驱动 `psycopg`、Python 包 `pgvector` 和 PostgreSQL 服务器上的 `vector` 扩展是不同组件。安装 pip 依赖不会安装数据库服务器。

目前项目保持 LangChain 0.3 系列；不要单独升级 `langchain-core` 到 1.x。FAISS 已从项目依赖及 RAG 入口移除，环境中以前安装的 FAISS 包可以保留。

## 2. 启动数据库

推荐在 Windows 使用 Docker Desktop（Linux 容器模式）。本配置将数据库端口绑定到 `127.0.0.1`，数据保存在命名卷中。

首次配置时，将 `.env.example` 复制为 `.env`，设置自己的 `PGPASSWORD`：

```powershell
Copy-Item .env.example .env
```

已有 `.env` 时直接补充配置，不要覆盖原文件。然后启动数据库：

```powershell
docker compose up -d postgres
docker compose ps
```

如果 5432 端口已被占用，先把 `.env` 的 `PGPORT` 改为其他空闲端口，例如 5433。修改已有数据卷对应的用户名、密码或库名不会自动修改数据库账号，需要在数据库内管理。

也可以使用已有 PostgreSQL：填写 `.env` 的主机、端口、数据库、用户名和密码即可，不需要运行 Docker。该数据库需提前创建，服务器须安装 pgvector，首次初始化的账号须有启用扩展和建表权限。

## 3. 初始化并验证

```powershell
python -m backend.app.db.init_db --seed-products
```

命令会连接数据库，执行 `CREATE EXTENSION IF NOT EXISTS vector`，创建缺失的 `products` 表，导入不存在的商品 ID，并实际执行一次向量距离计算。成功输出类似：

```text
PostgreSQL ready; pgvector=0.x.x; products=30
```

重复执行不会清表或覆盖已有商品。商品金额使用 `NUMERIC(12, 2)`，库存和价格设有非负约束。`create_all()` 只用于这一步初始化，不负责修改已有表结构；后续表结构演进使用 Alembic 迁移。

导入 `main.py` 或运行现有 Agent 测试不会自动连接、创建或修改数据库。

## 4. RAG 向量入口

使用 `build_vector_store(embeddings, collection_name=..., engine=...)` 创建 LangChain `PGVector` 对象。`embeddings` 由后续选定的模型提供，本步骤未选择模型，也未调用收费 API。

向量表由 `langchain-postgres` 管理，名称是 `langchain_pg_collection` 和 `langchain_pg_embedding`，首次调用工厂时创建。业务商品表由 SQLAlchemy 管理；不要再另外创建一套自定义向量表。

集合必须使用同一个 Embedding 模型进行写入和查询。集合名应包含模型版本和维度，更换模型时创建新集合并重建向量，不要混用不同模型的向量。当前不预设 1536 维，也未创建 HNSW 索引；等模型确定后再配置维度和索引。

返回对象支持：

```python
store.add_documents(documents, ids=document_ids)
store.similarity_search(question, k=4, filter={"product_id": product_id})
retriever = store.as_retriever(search_kwargs={"k": 4})
```

文档元数据应包含 `product_id`、`source`、文档类型等。价格、库存和支付状态仍由业务服务查询，不使用文档向量作为实时数据来源。

## 5. 测试

默认测试无需数据库：

```powershell
python -m pytest -q
```

真实 PostgreSQL 测试需要独立测试数据库（例如 `shopping_agent_test`），并提前在其中启用 `vector` 扩展。把该库的连接地址配置到环境变量 `TEST_DATABASE_URL`（格式 `postgresql+psycopg://...`，URL 内的密码特殊字符需转义），再运行：

```powershell
python -m pytest tests/test_postgres_integration.py -q
```

该测试验证商品导入幂等、保留已修改库存、向量写入检索、商品 ID 过滤和集合重新打开。测试使用自己创建的独立 schema，完成后删除该 schema；请使用测试库，不要指向生产数据库。没有设置变量时会明确跳过，不代表真实数据库验证成功。

## 后续顺序

先验证数据库服务可以连接，再逐项把商品和用户相关服务改为数据库读写，补上用户隔离。RAG 的资料导入、Embedding 模型和问答图节点随后接入；前端本阶段不改动。
