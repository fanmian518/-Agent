# Knowledge Ingestion and Retrieval

Set `EMBEDDING_MODEL=BAAI/bge-m3` in the project-root `.env`. The embedding
client reuses `LLM_BASE_URL` and `LLM_API_KEY`; no second key is required.
The server-side vector extension must already be enabled.

Prepare a UTF-8 JSON list of documents. Each entry has `source`, `title`,
`content`, and an optional numeric `product_id`. For example (test text only):

```json
[
  {
    "source": "demo/manual-001",
    "title": "Demonstration document, not a real product policy",
    "product_id": 1,
    "content": "This is a demonstration of knowledge ingestion only."
  }
]
```

Import using `python -m backend.app.rag.ingest <path-to-json>` from the project
root. Importing sends document content to SiliconFlow and consumes API quota.
Only import content you are authorized to transmit. Do not import credentials,
private customer records, or unsupported claims about real products.

Sources are stable identifiers: reimporting a source replaces all its old
chunks in one transaction. Other sources are preserved. Embedding generation
happens before replacement, so model failure leaves existing documents intact.
Chunks are 600 characters with 100-character overlap and include source,
title, chunk index, model name, and optional product ID metadata.

`KnowledgeService.search(query, product_id=None, k=4)` returns raw matches
with source metadata and cosine distance (lower means closer). Setting a
product ID searches only that product's documents; global policies are not
automatically included. Similarity is not proof of relevance or truth.

The `search_knowledge` LangChain tool is registered, but this stage does not
yet route natural-language questions to it or generate final cited answers.
Prices, stock and transactional records still come from business tables.
The knowledge collection is `shopping_knowledge_bge_m3_1024_v1`; changing the
embedding model requires a new collection and re-embedding documents.

Tests use deterministic embeddings, isolated PostgreSQL schemas, and no paid
model calls. No demonstration policies are automatically imported into the
production knowledge collection.
