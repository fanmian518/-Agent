"""知识库分段、原子更新和商品过滤的真实数据库测试。"""

from unittest.mock import patch

import pytest
from langchain_core.embeddings import Embeddings

from backend.app.rag.knowledge import KnowledgeDocument, KnowledgeService
from backend.app.rag.embeddings import build_embeddings


class FixedEmbeddings(Embeddings):
    """仅用于离线测试的 1024 维向量。"""

    def embed_documents(self, texts):
        """转换测试文档。

        :param texts: 文本列表。
        :return: 确定性向量列表。
        """
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        """转换测试问题。

        :param text: 输入文本。
        :return: 1024 维非零向量。
        """
        return [1.0, 0.0] + [0.0] * 1022 if "charging" in text else [0.0, 1.0] + [0.0] * 1022


def test_ingest_replace_and_filter(isolated_business_database):
    """验证同来源更新、重复导入和商品过滤。

    :param isolated_business_database: 隔离测试连接池。
    :return: 无返回值。
    """
    service = KnowledgeService(FixedEmbeddings(), isolated_business_database)
    doc = KnowledgeDocument(source="manual-one", title="Manual", product_id=1, content="charging " * 200)
    assert service.ingest([doc]) > 1
    replacement = doc.model_copy(update={"content": "charging revised"})
    assert service.ingest([replacement]) == 1
    assert service.ingest([replacement]) == 1
    result = service.search("charging", product_id=1)
    assert len(result["matches"]) == 1
    assert result["matches"][0]["content"] == "charging revised"
    assert result["matches"][0]["source"] == "manual-one"
    assert not service.search("charging", product_id=2)["matches"]


def test_failed_embedding_keeps_previous_document(isolated_business_database):
    """验证生成向量失败时不会先删除旧内容。

    :param isolated_business_database: 隔离测试连接池。
    :return: 无返回值。
    """
    embeddings = FixedEmbeddings()
    service = KnowledgeService(embeddings, isolated_business_database)
    doc = KnowledgeDocument(source="manual", title="Manual", content="charging original")
    service.ingest([doc])
    with patch.object(embeddings, "embed_documents", return_value=[[1.0]]):
        with pytest.raises(ValueError, match="向量"):
            service.ingest([doc.model_copy(update={"content": "new content"})])
    assert service.search("charging")["matches"][0]["content"] == "charging original"


def test_client_configuration(monkeypatch):
    """验证兼容接口发送文本而非 OpenAI tokenizer 生成的 token ID。

    :param monkeypatch: 环境变量替换工具。
    :return: 无返回值。
    """
    monkeypatch.setenv("LLM_API_KEY", "test-only")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    with patch("backend.app.rag.embeddings.OpenAIEmbeddings") as factory:
        build_embeddings()
    assert factory.call_args.kwargs["check_embedding_ctx_length"] is False
    assert factory.call_args.kwargs["model"] == "BAAI/bge-m3"


def test_validation_before_external_access():
    """验证空文档、重复来源、非法问题提前拒绝。

    :return: 无返回值。
    """
    service = KnowledgeService()
    with pytest.raises(ValueError):
        service.ingest([])
    doc = KnowledgeDocument(source="same", title="Title", content="content")
    with pytest.raises(ValueError):
        service.ingest([doc, doc])
    with pytest.raises(ValueError):
        service.search(" ")
