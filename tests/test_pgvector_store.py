"""PGVector 工厂的配置验证测试，不连接数据库或模型服务。"""

from unittest.mock import Mock, patch

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine

from backend.app.rag.vector_store import build_vector_store


def test_pgvector_factory_uses_supplied_engine_and_preserves_collection():
    """确保集成复用传入连接池且不会删除已有集合。

    :return: 无返回值。
    """
    engine = create_engine("postgresql+psycopg://test:test@127.0.0.1/test")
    embeddings = Mock(spec=Embeddings)
    try:
        with patch("backend.app.rag.vector_store.PGVector") as vector_store:
            result = build_vector_store(embeddings, collection_name="test_model_v1", engine=engine)
        vector_store.assert_called_once_with(
            embeddings=embeddings,
            collection_name="test_model_v1",
            connection=engine,
            use_jsonb=True,
            create_extension=False,
            pre_delete_collection=False,
        )
        assert result is vector_store.return_value
    finally:
        engine.dispose()


def test_pgvector_factory_rejects_empty_collection_before_connecting():
    """拒绝空集合名且不读取数据库配置。

    :return: 无返回值。
    """
    with patch("backend.app.rag.vector_store.get_engine") as get_engine:
        with pytest.raises(ValueError, match="集合名称"):
            build_vector_store(Mock(spec=Embeddings), collection_name=" ")
        get_engine.assert_not_called()


def test_pgvector_factory_rejects_other_database_backends():
    """避免将其他数据库误用为 pgvector 后端。

    :return: 无返回值。
    """
    engine = create_engine("sqlite://")
    try:
        with pytest.raises(ValueError, match="PostgreSQL"):
            build_vector_store(Mock(spec=Embeddings), collection_name="test", engine=engine)
    finally:
        engine.dispose()
