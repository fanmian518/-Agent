"""收藏夹持久化及用户隔离回归测试。"""

import pytest
from sqlalchemy import insert, select

from backend.app.db.models import CartItem, FavoriteItem, User
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites


def test_favorites_persist_and_share_cart_user(isolated_business_database):
    """验证跨实例收藏与购物车共用开发身份。

    :param isolated_business_database: 独立测试数据库。
    :return: 无返回值。
    """
    Favorites().add(1)
    assert Favorites().get_items == [{"product_id": 1}]
    assert Favorites().add(1)["新增"] is False
    Cart().add(1)
    with isolated_business_database.connect() as connection:
        assert connection.execute(select(FavoriteItem.user_id)).scalar_one() == connection.execute(select(CartItem.user_id)).scalar_one()


def test_favorites_isolate_users(isolated_business_database):
    """验证查询、删除和清空不会影响其他用户。

    :param isolated_business_database: 独立测试数据库。
    :return: 无返回值。
    """
    with isolated_business_database.begin() as connection:
        user_id = connection.execute(insert(User).values(phone="favorite-test-user").returning(User.id)).scalar_one()
    default = Favorites()
    other = Favorites(user_id=user_id)
    default.add(1)
    assert not other.contains(1)
    assert other.remove(1)["removed"] is False
    other.add(1)
    other.add(2)
    default.remove(1)
    default.clear()
    assert other.get_items == [{"product_id": 1}, {"product_id": 2}]


def test_favorites_allow_no_stock_and_rollback_invalid_product():
    """验证缺货商品可收藏，失败操作不改变已有记录。

    :return: 无返回值。
    """
    favorites = Favorites()
    favorites.add(8)
    with pytest.raises(ValueError, match="商品不存在"):
        favorites.add(999999)
    assert Favorites().get_items == [{"product_id": 8}]
    with pytest.raises(ValueError, match="用户不存在"):
        Favorites(user_id=999999).add(1)
