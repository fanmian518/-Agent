"""购物车持久化、用户隔离和失败回滚测试。"""

import pytest
from sqlalchemy import insert

from backend.app.db.models import User
from backend.app.services.cart_service import Cart


def test_cart_survives_new_instance():
    """验证新实例读取已提交购物项。

    :return: 无返回值。
    """
    Cart().add(1, 2)
    assert Cart().get_items == [{"product_id": 1, "quantity": 2}]


def test_cart_user_isolation(isolated_business_database):
    """验证清空一个用户不影响其他用户。

    :param isolated_business_database: 独立测试数据库。
    :return: 无返回值。
    """
    with isolated_business_database.begin() as connection:
        user_id = connection.execute(insert(User).values(phone="another-test-user").returning(User.id)).scalar_one()
    Cart().add(1)
    other = Cart(user_id=user_id)
    assert other.get_items == []
    other.add(1, 3)
    Cart().clear()
    assert other.get_items == [{"product_id": 1, "quantity": 3}]


def test_invalid_quantity_rolls_back():
    """验证超库存操作不改变已保存数量。

    :return: 无返回值。
    """
    cart = Cart()
    cart.add(1, 2)
    with pytest.raises(ValueError, match="库存"):
        cart.add(1, 1000000)
    assert Cart().get_items == [{"product_id": 1, "quantity": 2}]
    with pytest.raises(ValueError, match="不存在"):
        cart.add(999999)
