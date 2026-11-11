"""LangChain 工具注册测试。"""

from backend.app.agent.tools import CartTools, FavoritesTools, build_agent_tools
from backend.app.agent.tools.order_tools import OrderTools
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites
from backend.app.services.order_service import OrderService


def test_build_agent_tools_registers_named_tools():
    """测试业务工具可以注册为 LangChain 工具。"""
    tools = build_agent_tools(CartTools(Cart()), FavoritesTools(Favorites()))
    names = {tool.name for tool in tools}

    assert len(names) == len(tools)
    assert "add_to_cart" in names
    assert "list_favorites" in names
    assert "get_product_detail" in names
    assert "search_products" in names
    assert "pay_order" in names


def test_registered_tool_can_be_invoked():
    """测试注册后的工具可以实际调用。"""
    tools = build_agent_tools(CartTools(Cart()), FavoritesTools(Favorites()))
    add_tool = next(tool for tool in tools if tool.name == "add_to_cart")

    result = add_tool.invoke({"product_id": 1, "quantity": 1})

    assert result == {"product_id": 1, "quantity": 1}


def test_registered_pay_tool_updates_pending_order():
    """测试注册后的支付工具可以更新待支付订单。"""
    cart = Cart()
    cart.add(1)
    orders = OrderService(cart)
    order = orders.create_order()
    tools = build_agent_tools(
        CartTools(cart),
        FavoritesTools(Favorites()),
        order_tools=OrderTools(orders),
    )
    pay_tool = next(tool for tool in tools if tool.name == "pay_order")

    result = pay_tool.invoke(
        {"order_id": order["order_id"], "payment_method": "支付宝"}
    )

    assert result["status"] == "paid"
