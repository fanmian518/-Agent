"""以有效待支付订单作为库存预占记录，无需重复维护库存计数。"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Order, OrderItem

RESERVATION_TTL = timedelta(minutes=30)


def reserved_quantity(session: Session, product_id: int, now: datetime) -> int:
    """统计指定商品尚未过期的预占数量。

    :param session: 当前事务；调用方必须先锁定商品行再用于写入判断。
    :param product_id: 商品 ID。
    :param now: 带时区的当前时间。
    :return: 有效待支付订单中的数量合计。
    """
    return session.scalar(select(func.coalesce(func.sum(OrderItem.quantity), 0)).join(
        Order, Order.id == OrderItem.order_id
    ).where(OrderItem.product_id == product_id, Order.status == "pending_payment",
            Order.created_at > now - RESERVATION_TTL))
