"""购物车类测试。"""

import pytest
from backend.app.services.cart_service import Cart


def test_add_and_get_cart():
    """测试加入商品并返回 product_id。"""
    cart = Cart()
    result = cart.add(1, 2)
    assert result == {"product_id": 1, "quantity": 2}
    assert cart.total_items == 2
    assert cart.get_items == [{"product_id": 1, "quantity": 2}]


def test_add_same_product_accumulates_quantity():
    """测试重复加入会累加数量。"""
    cart = Cart()
    cart.add(1, 1)
    assert cart.add(1, 2)["quantity"] == 3


def test_update_quantity():
    """测试修改商品数量。"""
    cart = Cart()
    cart.add(1)
    assert cart.update_quantity(1, 4) == {"product_id": 1, "quantity": 4}
    assert cart.get_items == [{"product_id": 1, "quantity": 4}]


def test_update_quantity_to_zero_removes_product():
    """测试数量为 0 时移除商品。"""
    cart = Cart()
    cart.add(1)
    assert cart.update_quantity(1, 0) == {"product_id": 1, "quantity": 0}
    assert cart.get_items == []


def test_remove_product():
    """测试删除商品。"""
    cart = Cart()
    cart.add(1)
    assert cart.remove(1) == {"product_id": 1, "removed": True}
    assert cart.get_items == []


def test_clear_cart():
    """测试清空购物车。"""
    cart = Cart()
    cart.add(1)
    cart.clear()
    assert cart.get_items == []
    assert cart.total_items == 0


def test_out_of_stock_product_cannot_be_added():
    """测试缺货商品不能加入购物车。"""
    with pytest.raises(ValueError, match="暂时缺货"):
        Cart().add(8)
