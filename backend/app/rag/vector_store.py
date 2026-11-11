"""通过 LangChain 的 PGVector 集成访问 PostgreSQL 向量存储。"""

from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import Engine

from backend.app.db.database import get_engine


def build_vector_store(
    embeddings: Embeddings,
    *,
    collection_name: str,
    engine: Engine | None = None,
) -> PGVector:
    """创建或连接已有向量集合，使用时才连接数据库。

    :param embeddings: 已配置的 Embedding 模型，写入和检索必须使用同一模型。
    :param collection_name: 集合名称；不同模型、维度或用途应使用不同名称。
    :param engine: 可选 PostgreSQL 连接池，默认复用业务数据库连接池。
    :return: 支持 add_documents、similarity_search 和 as_retriever 的 PGVector。
    """
    if not collection_name.strip():
        raise ValueError("向量集合名称不能为空")
    database_engine = engine if engine is not None else get_engine()
    if database_engine.dialect.name != "postgresql":
        raise ValueError("PGVector 要求 PostgreSQL 数据库")
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=database_engine,
        use_jsonb=True,
        create_extension=False,
        pre_delete_collection=False,
    )
