"""Bounded keyword recall plus reciprocal rank fusion with pgvector results."""
import re
from langchain_core.documents import Document
from sqlalchemy import select, or_
from backend.app.db.database import session_scope


def fuse(vector_results, keyword_documents, k):
    candidates = {}
    for ranking in (vector_results, [(doc, None) for doc in keyword_documents]):
        for rank, (doc, distance) in enumerate(ranking, 1):
            key = (doc.metadata.get('source'), doc.metadata.get('chunk_index'), doc.page_content)
            candidate = candidates.setdefault(key, {'doc': doc, 'distance': distance, 'score': 0.0})
            candidate['score'] += 1 / (60 + rank)
    return sorted(candidates.values(), key=lambda x: x['score'], reverse=True)[:k]


def keyword_recall(store, engine, query, product_id=None, limit=40):
    terms = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]{1,2}', query.lower())[:16]
    if not terms:
        return []
    embedding = store.EmbeddingStore
    collection = store.CollectionStore
    clauses = [embedding.document.icontains(term, autoescape=True) for term in terms]
    statement = select(embedding).join(collection, collection.uuid == embedding.collection_id).where(collection.name == store.collection_name, or_(*clauses))
    if product_id is not None:
        statement = statement.where(embedding.cmetadata['product_id'].astext == str(product_id))
    with session_scope(engine) as session:
        rows = list(session.scalars(statement.order_by(embedding.id).limit(limit)))
        rows.sort(key=lambda row: sum(term in row.document.lower() for term in terms), reverse=True)
        return [Document(page_content=row.document, metadata=row.cmetadata or {}) for row in rows]
