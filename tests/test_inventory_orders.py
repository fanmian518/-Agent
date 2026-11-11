"""库存预占、支付和购物车清理的数据库事务测试。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import event, insert, select, update

from backend.app.db.models import Order, Product, User
from backend.app.services.cart_service import Cart
from backend.app.services.order_service import OrderService


def stock(engine):
    """读取测试商品库存。

    :param engine: 隔离连接池。
    :return: 商品 1 的实际库存。
    """
    with engine.connect() as connection:
        return connection.execute(select(Product.stock).where(Product.id == 1)).scalar_one()


def test_reserve_cancel_and_expiry(isolated_business_database):
    """验证预占不扣实际库存，取消和过期均释放库存。

    :param isolated_business_database: 隔离连接池。
    :return: 无返回值。
    """
    engine = isolated_business_database
    with engine.begin() as connection:
        connection.execute(update(Product).where(Product.id == 1).values(stock=1))
    cart = Cart()
    cart.add(1)
    service = OrderService(cart)
    first = service.create_order()
    assert stock(engine) == 1
    with pytest.raises(ValueError, match="库存不足"):
        service.create_order()
    service.cancel_order(first["order_id"])
    service.cancel_order(first["order_id"])
    second = service.create_order()
    with engine.begin() as connection:
        connection.execute(update(Order).where(Order.order_id == second["order_id"]).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=31)))
    with pytest.raises(ValueError, match="过期"):
        service.pay_order(second["order_id"], "test")
    third = service.create_order()
    service.pay_order(third["order_id"], "test")
    assert stock(engine) == 0
    assert cart.get_items == []


def test_payment_preserves_later_cart_additions(isolated_business_database):
    """验证支付只减订单数量且不重复扣库存。

    :param isolated_business_database: 隔离连接池。
    :return: 无返回值。
    """
    before = stock(isolated_business_database)
    cart = Cart()
    cart.add(1, 2)
    service = OrderService(cart)
    order = service.create_order()
    cart.add(1, 3)
    cart.add(2)
    service.pay_order(order["order_id"], "test")
    assert cart.get_items == [{"product_id": 1, "quantity": 3}, {"product_id": 2, "quantity": 1}]
    with pytest.raises(ValueError):
        service.pay_order(order["order_id"], "test")
    assert stock(isolated_business_database) == before - 2


def test_readded_cart_item_is_preserved():
    """验证删除后重新加入的购物项不被旧订单清理。

    :return: 无返回值。
    """
    cart = Cart()
    cart.add(1)
    service = OrderService(cart)
    order = service.create_order()
    cart.remove(1)
    cart.add(1, 2)
    service.pay_order(order["order_id"], "test")
    assert cart.get_items == [{"product_id": 1, "quantity": 2}]


def test_concurrent_last_item_reservation(isolated_business_database):
    """验证不同用户同时预占最后一件时仅一个成功。

    :param isolated_business_database: 隔离连接池。
    :return: 无返回值。
    """
    engine = isolated_business_database
    with engine.begin() as connection:
        connection.execute(update(Product).where(Product.id == 1).values(stock=1))
        ids = [connection.execute(insert(User).values(phone=f"race-{i}").returning(User.id)).scalar_one() for i in range(2)]
    carts = [Cart(user_id=user_id, engine=engine) for user_id in ids]
    for cart in carts:
        cart.add(1)
    barrier = Barrier(2)

    def reserve(cart):
        """同步执行预占。

        :param cart: 测试用户购物车。
        :return: 是否成功创建订单。
        """
        barrier.wait(timeout=10)
        try:
            OrderService(cart).create_order()
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reserve, carts)) == [False, True]
    assert stock(engine) == 1


def test_concurrent_payment_deducts_once(isolated_business_database):
    """验证同一订单的并发支付最多成功一次。

    :param isolated_business_database: 隔离连接池。
    :return: 无返回值。
    """
    engine = isolated_business_database
    before = stock(engine)
    cart = Cart(engine=engine)
    cart.add(1)
    order = OrderService(cart).create_order()
    barrier = Barrier(2)

    def pay(index):
        """同步发送支付请求。

        :param index: 工作线程编号。
        :return: 请求是否成功。
        """
        barrier.wait(timeout=10)
        try:
            OrderService(Cart(engine=engine)).pay_order(order["order_id"], "test")
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(pay, range(2))) == [False, True]
    assert stock(engine) == before - 1
    assert cart.get_items == []


def test_payment_failure_rolls_back_all_changes(isolated_business_database):
    """模拟订单写入失败，验证库存和购物车修改一起回滚。

    :param isolated_business_database: 隔离连接池。
    :return: 无返回值。
    """
    engine = isolated_business_database
    cart = Cart(engine=engine)
    cart.add(1)
    service = OrderService(cart)
    order = service.create_order()
    before = stock(engine)

    def fail_order_update(conn, cursor, statement, parameters, context, executemany):
        """在订单更新时注入失败。

        :param conn: 连接。
        :param cursor: 数据库游标。
        :param statement: SQL 语句。
        :param parameters: SQL 参数。
        :param context: 执行上下文。
        :param executemany: 是否批量执行。
        :return: 无返回值。
        """
        if statement.startswith("UPDATE") and ".orders SET" in statement:
            raise RuntimeError("injected failure")

    event.listen(engine, "before_cursor_execute", fail_order_update)
    try:
        with pytest.raises(RuntimeError, match="injected"):
            service.pay_order(order["order_id"], "test")
    finally:
        event.remove(engine, "before_cursor_execute", fail_order_update)
    assert stock(engine) == before
    assert cart.get_items == [{"product_id": 1, "quantity": 1}]
    assert service.orders[0]["status"] == "pending_payment"
