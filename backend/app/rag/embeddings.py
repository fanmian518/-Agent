"""硅基流动 BGE-M3 向量模型配置。"""

from typing import Literal

from langchain_openai import OpenAIEmbeddings

from backend.app.agent.llm_intent_parser import LLMSettings


class EmbeddingSettings(LLMSettings):
    """首版固定使用 BGE-M3，防止不同维度或模型混入同一集合。"""

    embedding_model: Literal["BAAI/bge-m3"] = "BAAI/bge-m3"


def build_embeddings() -> OpenAIEmbeddings:
    """复用硅基流动地址和密钥创建向量客户端。

    :return: 接收原始文本的 BGE-M3 客户端。
    """
    settings = EmbeddingSettings()
    return OpenAIEmbeddings(
        model=settings.embedding_model, api_key=settings.llm_api_key,
        base_url=settings.llm_base_url, check_embedding_ctx_length=False,
        chunk_size=16, request_timeout=45, max_retries=1,
        model_kwargs={"encoding_format": "float"},
    )
