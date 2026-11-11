"""多轮会话回归，使用模拟模型与隔离业务数据库。"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.app.agent import llm_intent_parser as parser
from backend.app.agent.conversation import ConversationStore
from backend.app.agent.executor import AgentExecutor
from backend.app.main import app
from backend.app.services.cart_service import Cart


def test_filters_reference_and_api_session(monkeypatch):
    """验证前端沿用会话、筛选继承与按结果序号加购。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.side_effect = [
        {"action": "search", "category": "手机"},
        {"action": "search", "inherit_filters": True, "max_price": 20000},
        {"action": "search_and_add_to_cart", "result_index": 2, "quantity": 2},
    ]
    monkeypatch.setattr(parser, "build_model", lambda: model)
    client = TestClient(app)
    first = client.post("/api/agent/execute", json={"message": "找手机"}).json()
    session_id = first["session_id"]
    second = client.post("/api/agent/execute", json={"message": "两万元以内", "session_id": session_id}).json()
    assert second["intent"]["category"] == "手机"
    assert second["intent"]["max_price"] == 20000
    third = client.post("/api/agent/execute", json={"message": "第二个加入购物车，数量2", "session_id": session_id})
    assert third.status_code == 200
    assert third.json()["cart_result"] == {"product_id": second["products"][1]["id"], "quantity": 2}
    assert "context" not in third.json()


def test_unknown_and_cross_user_sessions_rejected():
    """验证无效会话及其他用户的会话不可访问。

    :return: 无返回值。
    """
    store = ConversationStore()
    with store.turn(1, None) as (key, record):
        record.context = {"filters": {"brand": "Apple"}}
    with pytest.raises(ValueError, match="会话"):
        with store.turn(2, key):
            pytest.fail("cross-user access")
    with pytest.raises(ValueError, match="会话"):
        with store.turn(1, "unknown"):
            pytest.fail("unknown session")
    with store.turn(1, None) as (_, record):
        assert not record.context


@pytest.mark.parametrize("index", [0, 3])
def test_ambiguous_reference_clarifies(monkeypatch, index):
    """验证歧义指代或越界序号不映射为错误商品。

    :param monkeypatch: 测试替换工具。
    :param index: 模型提取的引用序号。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "search_and_add_to_cart", "result_index": index}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    result = parser.parse_intent("这款加入购物车", {"product_ids": [1, 2], "focused_id": None})
    assert result["action"] == "clarify"
    assert result["product_id"] is None


def test_failure_keeps_context_and_new_topic_resets(monkeypatch):
    """验证失败不会破坏上下文，换话题不继承筛选。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.side_effect = [
        {"action": "search", "brand": "Apple", "category": "手机"},
        RuntimeError("offline"),
        {"action": "search", "inherit_filters": True, "color": "白色"},
        {"action": "search", "category": "耳机"},
    ]
    monkeypatch.setattr(parser, "build_model", lambda: model)
    executor = AgentExecutor(Cart())
    first = executor.execute("找苹果手机")
    with pytest.raises(parser.ModelUnavailableError):
        executor.execute("白色", first["session_id"])
    third = executor.execute("白色", first["session_id"])
    assert third["intent"]["brand"] == "Apple"
    last = executor.execute("改找耳机", first["session_id"])
    assert last["intent"]["brand"] is None
    assert last["intent"]["category"] == "耳机"


def test_clear_filter_and_unique_focus(monkeypatch):
    """验证明确取消限制和已确定商品的指代。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "search", "inherit_filters": True, "clear_filters": ["color"]}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    context = {"filters": {"brand": "Apple", "color": "白色"}, "focused_id": 12, "product_ids": [12]}
    intent = parser.parse_intent("颜色不限", context)
    assert intent["brand"] == "Apple" and intent["color"] is None
    model.invoke.return_value = {"action": "product_detail", "result_index": 0}
    assert parser.parse_intent("看看这款详情", context)["product_id"] == 12


def test_expiry_and_capacity():
    """验证闲置会话过期以及容量上限。

    :return: 无返回值。
    """
    store = ConversationStore(capacity=1)
    with store.turn(1, None) as (key, record):
        pass
    with pytest.raises(ValueError, match="上限"):
        with store.turn(1, None):
            pytest.fail("capacity exceeded")
    record.touched -= store.ttl + 1
    with pytest.raises(ValueError, match="过期"):
        with store.turn(1, key):
            pytest.fail("expired session")


def test_condition_matched_products_can_be_operated_in_bulk(monkeypatch):
    """验证名称筛选后的全部精确商品可批量加购或收藏。

    :param monkeypatch: 测试替换模型。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.side_effect = [
        {"action": "search_and_add_to_cart", "category": "手机", "brand": "小米", "color": "白色", "max_price": 5000, "target_scope": "all", "quantity": 2},
        {"action": "search_and_add_to_favorites", "category": "手机", "brand": "小米", "color": "白色", "max_price": 5000, "target_scope": "all"},
    ]
    monkeypatch.setattr(parser, "build_model", lambda: model)
    executor = AgentExecutor(Cart())
    cart_result = executor.execute("将5000元以下的白色小米手机加入购物车，数量2")
    assert cart_result["cart_result"]["scope"] == "all"
    assert cart_result["cart_result"]["count"] + len(cart_result["cart_result"]["skipped"]) == len(cart_result["products"])
    assert all(item["quantity"] == 2 for item in cart_result["cart_result"]["items"])
    favorites_result = executor.execute("收藏5000元以下的白色小米手机")
    assert favorites_result["favorites_result"]["scope"] == "all"
    assert favorites_result["favorites_result"]["count"] == len(favorites_result["products"])
    assert favorites_result["favorites_result"]["skipped"] == []
