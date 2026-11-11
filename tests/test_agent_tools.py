"""Agent 工具层测试。"""

from backend.app.agent.tools.cart_tools import CartTools
from backend.app.agent.tools.favorites_tools import FavoritesTools
from backend.app.agent.tools.product_tools import ProductTools
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites


def test_cart_tools_delegate_to_cart_service():
    """测试购物车工具可以完成基本操作。"""
    tools = CartTools(Cart())
    assert tools.add_to_cart(1) == {"product_id": 1, "quantity": 1}
    assert tools.list_cart()["total_items"] == 1
    assert tools.update_cart(1, 2)["quantity"] == 2
    assert tools.remove_from_cart(1)["removed"] is True


def test_favorites_tools_delegate_to_service():
    """测试收藏夹工具可以完成基本操作。"""
    tools = FavoritesTools(Favorites())
    assert tools.add_to_favorites(1)["favorited"] is True
    assert tools.list_favorites()["items"] == [{"product_id": 1}]
    assert tools.remove_from_favorites(1)["removed"] is True


def test_product_tools_search_and_detail():
    """测试商品工具可以搜索并获取详情。"""
    tools = ProductTools()
    result = tools.search(exact_no_or_yes=False, category="手机")
    assert result["products"]
    assert tools.get_detail(1)["id"] == 1
