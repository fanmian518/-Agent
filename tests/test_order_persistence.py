"""真实 PostgreSQL 订单持久化回归测试。"""

from decimal import Decimal

import pytest
from sqlalchemy import func, insert, select, update

from backend.app.db.models import Order, OrderItem, Product, User
from backend.app.services.cart_service import Cart
from backend.app.services.order_service import OrderService


def test_order_snapshot_and_payment_persist(isolated_business_database):
    """验证跨实例读取、金额精度及商品快照不受改价影响。

    :param isolated_business_database: 隔离数据库连接池。
    :return: 无返回值。
    """
    with isolated_business_database.begin() as connection:
        connection.execute(update(Product).where(Product.id == 1).values(price=Decimal("0.10")))
    cart = Cart()
    cart.add(1, 3)
    created = OrderService(cart).create_order()
    assert created["total_amount"] == 0.3
    with isolated_business_database.begin() as connection:
        connection.execute(update(Product).where(Product.id == 1).values(price=999, name="changed"))
    assert OrderService(Cart()).orders == [created]
    paid = OrderService(Cart()).pay_order(created["order_id"], "支付宝")
    assert paid["status"] == "paid"
    assert OrderService(Cart()).orders == [paid]
    with pytest.raises(ValueError, match="不可支付"):
        OrderService(Cart()).pay_order(created["order_id"], "微信")


def test_order_user_isolation(isolated_business_database):
    """验证其他用户不能查看或支付订单。

    :param isolated_business_database: 隔离数据库连接池。
    :return: 无返回值。
    """
    cart = Cart()
    cart.add(1)
    created = OrderService(cart).create_order()
    with isolated_business_database.begin() as connection:
        user_id = connection.execute(insert(User).values(phone="order-other-user").returning(User.id)).scalar_one()
    other = OrderService(Cart(user_id=user_id))
    assert other.orders == []
    with pytest.raises(ValueError, match="订单不存在"):
        other.pay_order(created["order_id"], "支付宝")
    assert OrderService(cart).orders[0]["status"] == "pending_payment"


def test_failed_order_does_not_write_rows(isolated_business_database):
    """验证空购物车及库存变化导致失败时不留下订单。

    :param isolated_business_database: 隔离数据库连接池。
    :return: 无返回值。
    """
    cart = Cart()
    service = OrderService(cart)
    with pytest.raises(ValueError, match="购物车为空"):
        service.create_order()
    cart.add(1)
    cart.add(2)
    with isolated_business_database.begin() as connection:
        connection.execute(update(Product).where(Product.id == 2).values(stock=0))
    with pytest.raises(ValueError, match="库存不足"):
        service.create_order()
    with isolated_business_database.connect() as connection:
        for model in (Order, OrderItem):
            assert connection.execute(select(func.count()).select_from(model)).scalar_one() == 0
    assert len(cart.get_items) == 2
