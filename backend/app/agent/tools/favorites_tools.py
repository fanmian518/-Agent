"""收藏夹 Agent 工具。"""

from typing import Any

from backend.app.services.favorites_service import Favorites


class FavoritesTools:
    """将收藏夹服务包装成 Agent 可调用工具。"""

    def __init__(self, favorites: Favorites) -> None:
        """初始化工具。

        :param favorites: 要操作的收藏夹实例。
        :return: 无返回值。
        """
        self.favorites = favorites

    def add_to_favorites(self, product_id: int) -> dict[str, Any]:
        """收藏商品。

        :param product_id: 商品 ID。
        :return: 收藏结果。
        """
        return self.favorites.add(product_id)

    def list_favorites(self) -> dict[str, Any]:
        """查看收藏夹。

        :return: 收藏商品 ID 列表。
        """
        return {"items": self.favorites.get_items}

    def remove_from_favorites(self, product_id: int) -> dict[str, Any]:
        """删除收藏商品。

        :param product_id: 商品 ID。
        :return: 删除结果。
        """
        return self.favorites.remove(product_id)

    def clear_favorites(self) -> dict[str, str]:
        """清空收藏夹。

        :return: 清空结果。
        """
        self.favorites.clear()
        return {"message": "收藏夹已清空"}
