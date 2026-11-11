"""收藏夹服务测试。"""

import pytest

from backend.app.services.favorites_service import Favorites


def test_add_favorite():
    """测试可以将有效商品加入收藏夹。"""
    favorites = Favorites()

    result = favorites.add(1)

    assert result == {
        "product_id": 1,
        "favorited": True,
        "新增": True,
    }
    assert favorites.get_items == [{"product_id": 1}]


def test_add_duplicate_favorite_does_not_duplicate_item():
    """测试重复收藏不会产生重复记录。"""
    favorites = Favorites()
    favorites.add(1)

    result = favorites.add(1)

    assert result == {
        "product_id": 1,
        "favorited": True,
        "新增": False,
    }
    assert favorites.get_items == [{"product_id": 1}]


def test_add_unknown_product_raises_error():
    """测试收藏不存在的商品会抛出异常。"""
    favorites = Favorites()

    with pytest.raises(ValueError, match="商品不存在"):
        favorites.add(999999)


def test_contains_favorite():
    """测试判断商品是否已收藏。"""
    favorites = Favorites()

    assert favorites.contains(1) is False
    favorites.add(1)
    assert favorites.contains(1) is True


def test_remove_favorite():
    """测试删除已收藏商品和删除不存在商品。"""
    favorites = Favorites()
    favorites.add(1)

    assert favorites.remove(1) == {"product_id": 1, "removed": True}
    assert favorites.get_items == []
    assert favorites.remove(1) == {"product_id": 1, "removed": False}


def test_clear_favorites():
    """测试可以清空收藏夹。"""
    favorites = Favorites()
    favorites.add(1)
    favorites.add(2)

    favorites.clear()

    assert favorites.get_items == []

