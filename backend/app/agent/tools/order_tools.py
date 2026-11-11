"""订单 Agent 工具。"""

from typing import Any

from backend.app.services.order_service import OrderService


class OrderTools:
    """将订单服务包装成 Agent 工具。"""

    def __init__(self, orders: OrderService) -> None:
        """初始化工具。

        :param orders: 订单服务实例。
        :return: 无返回值。
        """
        self.orders = orders

    def create_order(self, product_ids: list[int] | None = None, address_id: int | None = None) -> dict[str, Any]:
        """创建待支付订单。

        :return: 订单页面所需信息。
        """
        return self.orders.create_order(product_ids, address_id)

    def pay_order(self, order_id: str, payment_method: str) -> dict[str, Any]:
        """确认待支付订单。

        :param order_id: 订单号。
        :param payment_method: 支付方式。
        :return: 支付后的订单。
        """
        return self.orders.pay_order(order_id, payment_method)
