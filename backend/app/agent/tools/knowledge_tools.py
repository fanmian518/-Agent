"""知识检索工具，不执行交易动作。"""

from backend.app.rag.knowledge import KnowledgeService


def search_knowledge(query: str, product_id: int | None = None, k: int = 4) -> dict:
    """检索说明书、活动规则或售后文档片段。

    :param query: 知识问题。
    :param product_id: 可选商品 ID，避免混用其他商品文档。
    :param k: 返回片段数，范围 1 到 10。
    :return: 带来源的相关原文片段，不代替事实核验。
    """
    return KnowledgeService().search(query, product_id, k)


def answer_knowledge(query: str, product_id: int | None = None, k: int = 4) -> dict:
    """检索知识并生成严格基于来源的回答。

    :param query: 用户知识问题。
    :param product_id: 可选商品 ID。
    :param k: 返回片段数。
    :return: 带引用来源的回答。
    """
    return KnowledgeService().answer(query, product_id, k)
