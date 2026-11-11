"""文档分段、原子替换入库及有来源的知识检索。"""

import math
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, delete, select

from backend.app.db.database import get_engine, session_scope
from backend.app.rag.embeddings import build_embeddings
from backend.app.rag.vector_store import build_vector_store
from backend.app.agent.llm_intent_parser import LLMSettings
from langchain_openai import ChatOpenAI

COLLECTION = "shopping_knowledge_bge_m3_1024_v1"


class KnowledgeDocument(BaseModel):
    """显式导入的可信文档，不包含实时价格或库存。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=200000)
    product_id: int | None = Field(default=None, gt=0)


class KnowledgeService:
    """知识检索基础服务；不执行订单、支付或商品信息修改。"""

    def __init__(self, embeddings: Embeddings | None = None, engine: Engine | None = None):
        """配置可注入的向量模型与数据库。

        :param embeddings: 测试时注入确定性向量模型。
        :param engine: 测试时注入隔离数据库连接池。
        :return: 无返回值，不在构造阶段访问网络。
        """
        self.embeddings = embeddings
        self.engine = engine

    def _store(self):
        """按需连接固定模型的向量集合。

        :return: PGVector 实例及其数据库连接池。
        """
        engine = self.engine if self.engine is not None else get_engine()
        embeddings = self.embeddings if self.embeddings is not None else build_embeddings()
        return build_vector_store(embeddings, collection_name=COLLECTION, engine=engine), engine

    def ingest(self, documents: list[KnowledgeDocument]) -> int:
        """分段并原子替换输入来源的全部旧分段；失败保留旧文档。

        :param documents: 来源标识唯一的文档列表，同来源代表更新。
        :return: 写入的分段数量。
        """
        if not documents or len({doc.source for doc in documents}) != len(documents):
            raise ValueError("文档不能为空且来源标识不能重复")
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""])
        chunks = []
        for doc in documents:
            for index, content in enumerate(splitter.split_text(doc.content)):
                metadata = {"source": doc.source, "title": doc.title, "chunk_index": index,
                            "embedding_model": "BAAI/bge-m3"}
                if doc.product_id is not None:
                    metadata["product_id"] = doc.product_id
                chunks.append(Document(page_content=content, metadata=metadata))
        store, engine = self._store()
        vectors = store.embeddings.embed_documents([chunk.page_content for chunk in chunks])
        if len(vectors) != len(chunks) or any(len(vector) != 1024 or not all(math.isfinite(value) for value in vector) for vector in vectors):
            raise ValueError("向量返回数量、维度或数值不符合 BGE-M3 要求")
        with session_scope(engine) as session:
            collection = session.scalar(select(store.CollectionStore).where(
                store.CollectionStore.name == COLLECTION).with_for_update())
            if collection is None:
                raise ValueError("知识集合不存在")
            session.execute(delete(store.EmbeddingStore).where(
                store.EmbeddingStore.collection_id == collection.uuid,
                store.EmbeddingStore.cmetadata["source"].astext.in_([doc.source for doc in documents]),
            ))
            session.add_all([store.EmbeddingStore(id=uuid4().hex, collection_id=collection.uuid,
                embedding=vector, document=chunk.page_content, cmetadata=chunk.metadata)
                for chunk, vector in zip(chunks, vectors)])
        return len(chunks)

    def search(self, query: str, product_id: int | None = None, k: int = 4) -> dict:
        """检索有来源的原文片段；相似结果不是已验证的事实答案。

        :param query: 用户知识问题。
        :param product_id: 可选商品 ID，仅检索该商品的文档。
        :param k: 最多返回分段数，范围 1 到 10。
        :return: 命中片段、来源和余弦距离；无文档时返回空列表。
        """
        if not query.strip() or len(query) > 8000 or not 1 <= k <= 10:
            raise ValueError("问题不能为空或过长，k 必须在 1 到 10 之间")
        if product_id is not None and product_id <= 0:
            raise ValueError("商品 ID 必须大于零")
        from backend.app.rag.hybrid import keyword_recall, fuse
        store, engine = self._store()
        results = store.similarity_search_with_score(query, k=min(k * 4, 40),
            filter={"product_id": product_id} if product_id is not None else None)
        fused = fuse(results, keyword_recall(store, engine, query, product_id), k)
        return {"query": query, "matches": [{"content": item['doc'].page_content, **item['doc'].metadata,
                    "distance": float(item['distance']) if item['distance'] is not None else None,
                    "rrf_score": item['score']} for item in fused]}

    def answer(self, query: str, product_id: int | None = None, k: int = 4) -> dict:
        """基于检索原文生成带来源回答；无依据时拒绝推测。

        :param query: 用户知识问题。
        :param product_id: 可选商品 ID。
        :param k: 检索片段数量。
        :return: 回答、来源列表及原始匹配结果。
        """
        result = self.search(query, product_id, k)
        matches = result["matches"]
        if not matches:
            return {"query": query, "answer": "知识库中没有找到足够依据，无法确认。", "sources": [], "matches": []}
        settings = LLMSettings()
        model = ChatOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key,
                           model=settings.llm_model, temperature=0, timeout=45, max_retries=0)
        context = "\n\n".join(f"[{index}] {match['title']} ({match['source']})\n{match['content']}"
            for index, match in enumerate(matches, 1))
        prompt = ("你是严格的知识库问答助手。只能依据下面的检索原文回答，不能补充常识、猜测或编造。"
                  "如果原文不足以回答，明确说‘知识库中没有足够依据’。回答末尾用[1]等标记引用来源。"
                  "价格、库存、订单和支付问题不要从这些原文回答，应说明请查询业务页面。\n\n"
                  f"检索原文：\n{context}")
        try:
            from backend.app.infrastructure.reliability import invoke_model
            message = invoke_model(model, [("system", prompt), ("human", query)])
            answer = message.content if isinstance(message.content, str) else str(message.content)
        except Exception:
            raise RuntimeError("知识回答模型暂时不可用，请稍后重试。") from None
        return {"query": query, "answer": answer, "sources": [
            {"source": match["source"], "title": match["title"], "product_id": match.get("product_id")}
            for match in matches], "matches": matches}
