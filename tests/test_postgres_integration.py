"""显式设置 TEST_DATABASE_URL 后验证真实 PostgreSQL 和 pgvector。"""

import os
from uuid import uuid4

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.data.products import PRODUCTS
from backend.app.db.init_db import initialize_database
from backend.app.db.models import Product
from backend.app.rag.vector_store import build_vector_store


class TestEmbeddings(Embeddings):
    """仅用于验证数据库检索的确定性向量，不用于实际商品问答。"""

    __test__ = False

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """为测试文本提供预设向量。

        :param texts: 测试文本列表。
        :return: 三维测试向量列表。
        """
        return [self.embed_query(value) for value in texts]

    def embed_query(self, text: str) -> list[float]:
        """映射测试问题到预设向量。

        :param text: 测试文本或问题。
        :return: 三维测试向量。
        """
        return [1.0, 0.0, 0.0] if "charging" in text else [0.0, 1.0, 0.0]


def test_postgres_seed_persistence_and_vector_search():
    """验证商品初始化幂等、数据持久化及按商品 ID 限定的向量检索。

    :return: 无返回值。
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL 未配置，未执行真实 PostgreSQL 集成测试")
    admin = create_engine(url, connect_args={"connect_timeout": 5})
    if admin.dialect.name != "postgresql" or admin.dialect.driver != "psycopg":
        admin.dispose()
        pytest.fail("TEST_DATABASE_URL 必须使用 postgresql+psycopg 驱动")
    schema = "test_shopping_" + uuid4().hex
    engine = None
    created = False
    try:
        # 测试库需预先启用 vector；测试只创建和删除自己拥有的独立 schema。
        with admin.begin() as connection:
            connection.execute(text("SELECT '[1,0,0]'::vector"))
            connection.execute(CreateSchema(schema))
        created = True
        engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema},public", "connect_timeout": 5},
            execution_options={"schema_translate_map": {None: schema}},
        )
        first = initialize_database(engine, seed_products=True)
        assert first["product_count"] == len(PRODUCTS)
        with engine.begin() as connection:
            connection.execute(update(Product).where(Product.id == 1).values(stock=1))
        assert initialize_database(engine, seed_products=True) == first
        with engine.connect() as connection:
            assert connection.execute(select(Product.stock).where(Product.id == 1)).scalar_one() == 1

        store = build_vector_store(TestEmbeddings(), collection_name="test_vectors", engine=engine)
        store.add_documents(
            [
                Document(page_content="wireless charging supported", metadata={"product_id": 1, "source": "test"}),
                Document(page_content="audio controls", metadata={"product_id": 2, "source": "test"}),
            ],
            ids=["test-charging", "test-audio"],
        )
        results = store.similarity_search("charging", k=1, filter={"product_id": 1})
        assert results[0].page_content == "wireless charging supported"
        assert store.similarity_search("charging", k=1, filter={"product_id": 999}) == []
        reopened = build_vector_store(TestEmbeddings(), collection_name="test_vectors", engine=engine)
        assert reopened.similarity_search("charging", k=1)[0].metadata["product_id"] == 1
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
