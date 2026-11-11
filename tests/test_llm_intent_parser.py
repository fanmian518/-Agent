"""模型解析安全边界测试，不调用外部服务。"""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backend.app.agent import llm_intent_parser as parser
from backend.app.agent.graph import build_shopping_graph, execute_tool_node


def test_valid_intent(monkeypatch):
    """验证模型输出可转换为图状态。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "search_and_add_to_cart", "product_name": "小米手机", "keyword_parts": ["小米手机"], "quantity": 3}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    result = parser.parse_intent("小米手机加入购物车，数量3")
    assert result["quantity"] == 3
    assert result["product_id"] is None


@pytest.mark.parametrize("payload", [
    {"action": "pay_order"}, {"action": "cart_remove"},
    {"action": "cart_update", "product_id": 1},
    {"action": "search", "min_price": 100, "max_price": 10},
    {"action": "search_and_buy", "quantity": 0},
    {"action": "search", "user_id": 2},
    {"action": "search", "quantity": True},
])
def test_invalid_schema(payload):
    """验证危险动作、非法参数和额外字段被拒绝。

    :param payload: 待验证模型输出。
    :return: 无返回值。
    """
    with pytest.raises(ValidationError):
        parser.ShoppingIntent.model_validate(payload)


def test_failure_stops_before_tools(monkeypatch):
    """验证模型通信异常时图不会执行任何工具，也不泄漏异常细节。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.side_effect = RuntimeError("secret-api-key")
    monkeypatch.setattr(parser, "build_model", lambda: model)
    tool = Mock()
    tool.name = "search_products"
    with pytest.raises(parser.ModelUnavailableError) as error:
        build_shopping_graph([tool]).invoke({"user_message": "找手机"})
    assert "secret-api-key" not in str(error.value)
    tool.invoke.assert_not_called()


def test_clarification_does_not_execute(monkeypatch):
    """验证澄清需求直接返回用户，不执行工具。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "clarify", "clarification": "请在订单页面确认支付"}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    tool = Mock()
    tool.name = "search_products"
    result = build_shopping_graph([tool]).invoke({"user_message": "帮我支付"})
    assert result["error"]
    tool.invoke.assert_not_called()


def test_hallucinated_id_rejected(monkeypatch):
    """验证模型不能将型号数字当商品 ID。

    :param monkeypatch: 测试替换工具。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "search_and_buy", "product_id": 17}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    with pytest.raises(ValueError, match="商品 ID"):
        parser.parse_intent("买iphone17")


def test_graph_blocks_payment():
    """验证即使绕过模型解析也不能通过图支付。

    :return: 无返回值。
    """
    with pytest.raises(ValueError, match="订单页面"):
        execute_tool_node({"intent": {"action": "pay_order"}}, {})


def test_single_best_intent_is_preserved(monkeypatch):
    """验证模型可标记最优单件请求。

    :param monkeypatch: 测试替换模型。
    :return: 无返回值。
    """
    model = Mock()
    model.invoke.return_value = {"action": "search", "keyword_parts": ["手机"], "sort_by": "price_asc", "single_best": True}
    monkeypatch.setattr(parser, "build_model", lambda: model)
    assert parser.parse_intent("最便宜的手机")["single_best"] is True


def test_explicit_cart_operation_is_recovered_when_model_returns_search(monkeypatch):
    """模型偶发返回 search 时，明确的加购原话仍必须执行加购动作。"""
    model = Mock()
    model.invoke.return_value = {
        "action": "search",
        "category": "手机",
        "brand": "华为",
        "max_price": 5000,
    }
    monkeypatch.setattr(parser, "build_model", lambda: model)

    result = parser.parse_intent("把5000元以下的华为手机添加进购物车")

    assert result["action"] == "search_and_add_to_cart"
    assert result["target_collection"] == "none"
    assert result["target_scope"] == "all"
    assert result["target_collection"] == "none"


def test_explicit_favorite_operation_does_not_search_existing_favorites(monkeypatch):
    """加入收藏夹时应搜索全商品，而不是先筛选当前收藏夹。"""
    model = Mock()
    model.invoke.return_value = {
        "action": "search",
        "category": "手机",
        "brand": "华为",
        "max_price": 5000,
    }
    monkeypatch.setattr(parser, "build_model", lambda: model)

    result = parser.parse_intent("将5000元以下的华为手机加入收藏夹")

    assert result["action"] == "search_and_add_to_favorites"
    assert result["target_collection"] == "none"


@pytest.mark.parametrize("model_action", ["search", "cart_list", "cart_clear"])
def test_cart_checkout_is_recovered_when_model_returns_non_order_action(monkeypatch, model_action):
    """结算购物车必须创建待支付订单，不能被误识别为查询或清空购物车。"""
    model = Mock()
    model.invoke.return_value = {"action": model_action}
    monkeypatch.setattr(parser, "build_model", lambda: model)

    result = parser.parse_intent("结算购物车")

    assert result["action"] == "create_order"


def test_address_followup_extracts_contact_name_and_merges_pending_fields(monkeypatch):
    """地址补充消息应提取联系人并合并上一轮待补字段。"""
    model = Mock()
    model.invoke.return_value = {"action": "clarify"}
    monkeypatch.setattr(parser, "build_model", lambda: model)

    result = parser.parse_intent(
        "华清远见就是我的联系人名称",
        {
            "pending_order": {
                "province": "山东省", "city": "济南市", "district": "历下区",
                "community": "黄金时代", "phone": "19525363665",
            }
        },
    )

    assert result["action"] == "create_order"
    assert result["contact_name"] == "华清远见"
    assert result["province"] == "山东省"
    assert result["phone"] == "19525363665"


def test_address_index_is_separate_from_product_result_index(monkeypatch):
    """选择第几个地址必须生成 address_index，不能映射为商品序号。"""
    model = Mock()
    model.invoke.return_value = {"action": "clarify"}
    monkeypatch.setattr(parser, "build_model", lambda: model)

    result = parser.parse_intent("选择第2个地址", {})

    assert result["action"] == "create_order"
    assert result["address_index"] == 2
    assert result["result_index"] is None
    assert result["product_id"] is None
