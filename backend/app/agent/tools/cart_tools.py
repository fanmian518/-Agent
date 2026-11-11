"""购物车 Agent 工具。"""

from typing import Any

from backend.app.services.cart_service import Cart


class CartTools:
    """将购物车服务包装成 Agent 可调用工具。"""

    def __init__(self, cart: Cart) -> None:
        """初始化工具。

        :param cart: 要操作的购物车实例。
        :return: 无返回值。
        """
        self.cart = cart

    def add_to_cart(self, product_id: int, quantity: int = 1) -> dict[str, Any]:
        """加入商品。

        :param product_id: 商品 ID。
        :param quantity: 加入数量。
        :return: 加购结果。
        """
        return self.cart.add(product_id, quantity)

    def list_cart(self) -> dict[str, Any]:
        """查看购物车。

        :return: 商品 ID、数量和总件数。
        """
        return {"items": self.cart.get_items, "total_items": self.cart.total_items}

    def update_cart(self, product_id: int, quantity: int) -> dict[str, Any]:
        """修改商品数量。

        :param product_id: 商品 ID。
        :param quantity: 新数量。
        :return: 修改结果。
        """
        return self.cart.update_quantity(product_id, quantity)

    def remove_from_cart(self, product_id: int) -> dict[str, Any]:
        """删除商品。

        :param product_id: 商品 ID。
        :return: 删除结果。
        """
        return self.cart.remove(product_id)

    def clear_cart(self) -> dict[str, str]:
        """清空购物车。

        :return: 清空结果。
        """
        self.cart.clear()
        return {"message": "购物车已清空"}
