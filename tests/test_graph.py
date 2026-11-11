"""LangGraph 最小购物流程测试。"""

from unittest.mock import Mock

from backend.app.agent.graph import shopping_graph
from backend.app.agent.graph import search_products_node, _resolve_order_address, execute_tool_node


def test_shopping_graph_searches_products():
    """测试状态图可以完成意图解析和商品搜索。"""
    result = shopping_graph.invoke({
        "user_message": "找5000元以下的黑色手机，选择最低价",
    })

    assert result["intent"]["category"] == "手机"
    assert result["products"]
    assert result["selected_products"]


def test_best_request_returns_one_even_for_fuzzy_result():
    """验证最优请求只展示一个模糊推荐商品。

    :return: 无返回值。
    """
    result = search_products_node(
        {"intent": {"exact_no_or_yes": False, "category": None, "brand": None, "color": None,
                    "min_price": None, "max_price": None, "keyword_parts": ["unknown"], "tags": [],
                    "activity": None, "sort_by": "price_asc", "single_best": True, "target_scope": "all"}},
        lambda **_: {"found": False, "products": [{"id": 1}, {"id": 2}], "message": "推荐"},
    )
    assert result["products"] == [{"id": 1}]
    assert result["selected_products"] == []


def test_basic_graph_reports_missing_tools_for_direct_action():
    """测试未注入工具的基础图不会因直接操作而出现节点错误。"""
    result = shopping_graph.invoke({"user_message": "查看购物车"})

    assert result["error"] == "当前图未配置购物车、收藏夹或订单工具。"


def test_new_order_address_reports_missing_required_fields(monkeypatch):
    """新地址缺少联系人或手机号时不能继续下单。"""
    monkeypatch.setattr("backend.app.agent.graph.find_by_area", lambda *_args: None)
    monkeypatch.setattr("backend.app.agent.graph.list_addresses", lambda *_args: [])
    address_id, required = _resolve_order_address(
        {
            "province": "山东省",
            "city": "济南市",
            "district": "历下区",
            "community": "黄金时代",
            "contact_name": None,
            "phone": None,
        },
        1,
    )
    assert address_id is None
    assert required["missing_fields"] == ["contact_name", "phone"]
    assert "联系人名称、手机号" in required["message"]


def test_cart_checkout_without_address_does_not_create_order(monkeypatch):
    """结算购物车未提供地址时只返回地址提示，不调用订单工具。"""
    monkeypatch.setattr("backend.app.agent.graph.list_addresses", lambda *_args: [])
    create_order = Mock()
    state = {
        "intent": {"action": "create_order"},
        "user_id": 1,
        "selected_products": [],
    }
    result = execute_tool_node(state, {"create_order": create_order})
    assert result["address_required"]["missing_fields"] == [
        "province", "city", "district", "community", "contact_name", "phone"
    ]
    create_order.invoke.assert_not_called()


def test_order_address_index_selects_sorted_address(monkeypatch):
    """Agent 选择第 N 个地址时，按地址弹窗顺序返回对应地址 ID。"""
    addresses = [
        {"id": 11, "province": "山东省", "city": "济南市", "district": "历下区", "community": "小区一"},
        {"id": 22, "province": "山东省", "city": "潍坊市", "district": "奎文区", "community": "小区二"},
    ]
    monkeypatch.setattr("backend.app.agent.graph.list_addresses", lambda *_args: addresses)

    address_id, required = _resolve_order_address({"address_index": 2}, 1)

    assert address_id == 22
    assert required is None
