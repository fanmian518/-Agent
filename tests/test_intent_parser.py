"""意图解析测试。"""

import pytest

from backend.app.agent.intent_parser import parse_intent


def test_parse_search_and_add_to_cart():
    """测试解析精确商品、价格、颜色和加购动作。"""
    intent = parse_intent("帮我找一部5000元以下的黑色小米手机，选择最低价加入购物车")

    assert intent["action"] == "search_and_add_to_cart"
    assert intent["exact_no_or_yes"] is True
    assert intent["category"] == "手机"
    assert intent["brand"] == "小米"
    assert intent["color"] == "黑色"
    assert intent["max_price"] == 5000
    assert intent["sort_by"] == "price_asc"


def test_parse_tags_and_activity():
    """测试解析多个标签和活动条件。"""
    intent = parse_intent("找支持5G和主动降噪的耳机，参加百亿补贴")

    assert intent["category"] == "耳机"
    assert intent["tags"] == ["5G", "主动降噪"]
    assert intent["activity"] == "百亿补贴"


def test_parse_fuzzy_recommendation():
    """测试类似商品请求被识别为模糊推荐。"""
    intent = parse_intent("推荐适合办公的手机")

    assert intent["exact_no_or_yes"] is False
    assert intent["category"] == "手机"


def test_empty_message_raises_error():
    """测试空指令会抛出异常。"""
    with pytest.raises(ValueError):
        parse_intent("  ")


def test_parse_cart_operations():
    """测试购物车操作动作识别。"""
    assert parse_intent("查看购物车")["action"] == "cart_list"
    assert parse_intent("清空购物车")["action"] == "cart_clear"
