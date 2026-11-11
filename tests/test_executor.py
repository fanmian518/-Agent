"""Agent 执行器测试。"""

from backend.app.agent.executor import AgentExecutor
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites


def test_executor_can_add_and_list_favorites():
    """测试 Agent 可以搜索并收藏商品，然后查看收藏夹。"""
    favorites = Favorites()
    executor = AgentExecutor(favorites=favorites)

    added = executor.execute("收藏5000元以下的黑色手机")
    listed = executor.execute("查看收藏夹")

    assert added["intent"]["action"] == "search_and_add_to_favorites"
    assert added["favorites_result"]["favorited"] is True
    assert listed["action"] == "favorites_list"
    assert listed["favorites_result"]["items"]


def test_executor_can_remove_and_clear_favorites():
    """测试 Agent 可以删除和清空收藏夹。"""
    favorites = Favorites()
    favorites.add(1)
    executor = AgentExecutor(favorites=favorites)

    removed = executor.execute("删除收藏夹商品编号1")
    cleared = executor.execute("清空收藏夹")

    assert removed["favorites_result"] == {"product_id": 1, "removed": True}
    assert cleared["action"] == "favorites_clear"


def test_executor_can_list_cart():
    """测试 Agent 可以查看购物车。"""
    result = AgentExecutor(Cart()).execute("查看购物车")

    assert result["action"] == "cart_list"
    assert result["cart_result"]["items"] == []


def test_executor_can_clear_cart():
    """测试 Agent 可以清空购物车。"""
    cart = Cart()
    cart.add(1)

    result = AgentExecutor(cart).execute("清空购物车")

    assert result["action"] == "cart_clear"
    assert cart.get_items == []


def test_executor_requires_product_id_for_remove():
    """测试删除购物车商品时必须提供商品 ID。"""
    import pytest

    with pytest.raises(ValueError, match="商品 ID"):
        AgentExecutor(Cart()).execute("删除购物车商品")
def test_execute_search():
    """测试执行器通过 LangGraph 完成意图解析和商品搜索。"""
    result = AgentExecutor().execute(
        "帮我找5000元以下的黑色手机"
    )

    assert result["intent"]["category"] == "手机"
    assert result["products"]
    assert result["selected_products"]


def test_executor_registers_tools_with_shared_services():
    """测试执行器注册的工具使用当前购物车和收藏夹实例。"""
    cart = Cart()
    favorites = Favorites()
    executor = AgentExecutor(cart=cart, favorites=favorites)

    tool_names = {tool.name for tool in executor.tools}
    add_tool = next(tool for tool in executor.tools if tool.name == "add_to_cart")
    add_tool.invoke({"product_id": 1, "quantity": 1})

    assert "add_to_cart" in tool_names
    assert {"product_id": 1, "quantity": 1} in cart.get_items


def test_execute_search_returns_recommendations_when_no_exact_result():
    """测试没有精确商品时返回推荐，不修改购物车。"""
    result = AgentExecutor().execute("推荐不存在的绿色手机")

    assert result["error"]
    assert result["products"]


def test_execute_empty_message_raises_error():
    """测试空购物指令会被执行器拒绝。"""
    import pytest

    with pytest.raises(ValueError, match="购物指令不能为空"):
        AgentExecutor().execute("  ")


def test_executor_can_get_product_detail():
    """测试 Agent 可以直接获取商品详情。"""
    result = AgentExecutor().execute("查看商品编号1的详情")

    assert result["action"] == "product_detail"
    assert result["product_detail"]["id"] == 1


def test_fuzzy_recommendations_do_not_trigger_add_to_cart():
    """测试无精确商品时只返回推荐，不会误加入购物车。"""
    cart = Cart()
    result = AgentExecutor(cart=cart).execute("推荐不存在的手机，加入购物车")

    assert result["error"]
    assert result["products"]
    assert result["selected_products"] == []
    assert cart.get_items == []


def test_add_by_product_id_honors_quantity():
    """测试按商品编号直接加购时使用用户指定数量。"""
    cart = Cart()
    AgentExecutor(cart=cart).execute("将商品编号1加入购物车，数量3")

    assert cart.get_items == [{"product_id": 1, "quantity": 3}]
