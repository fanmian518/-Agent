"""按用户隔离的 PostgreSQL 收藏夹服务。"""

from typing import Any

from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.postgresql import insert

from backend.app.db.database import session_scope
from backend.app.db.models import FavoriteItem, Product
from backend.app.db.user_repository import resolve_user_id


class Favorites:
    """表示一个用户的收藏夹。"""

    def __init__(self, user_id: int | None = None, engine: Engine | None = None) -> None:
        """配置收藏夹，不清空已持久化数据。

        :param user_id: 已有用户 ID；None 与购物车共用开发用户。
        :param engine: 可选独立数据库连接池。
        :return: 无返回值。
        """
        self.user_id = user_id
        self.engine = engine

    def add(self, product_id: int) -> dict[str, Any]:
        """将商品加入收藏夹。

        :param product_id: 要收藏的商品 ID。
        :return: 包含商品 ID 和收藏状态的操作结果。
        """
        with session_scope(self.engine) as session:
            user_id = resolve_user_id(session, self.user_id)
            product = session.scalar(select(Product.id).where(Product.id == product_id).with_for_update(read=True))
            if product is None:
                raise ValueError("商品不存在")
            added = session.execute(
                insert(FavoriteItem).values(user_id=user_id, product_id=product_id)
                .on_conflict_do_nothing(index_elements=["user_id", "product_id"])
                .returning(FavoriteItem.id)
            ).scalar_one_or_none()
            return {"product_id": product_id, "favorited": True, "新增": added is not None}

    @property
    def get_items(self) -> list[dict[str, int]]:
        """获取收藏夹中的商品 ID。

        :return: 按收藏顺序排列的商品 ID 列表。
        """
        with session_scope(self.engine) as session:
            user_id = resolve_user_id(session, self.user_id)
            ids = session.scalars(select(FavoriteItem.product_id).where(FavoriteItem.user_id == user_id).order_by(FavoriteItem.id))
            return [{"product_id": product_id} for product_id in ids]

    def contains(self, product_id: int) -> bool:
        """判断商品是否已在收藏夹中。

        :param product_id: 要检查的商品 ID。
        :return: 已收藏时返回 True，否则返回 False。
        """
        with session_scope(self.engine) as session:
            user_id = resolve_user_id(session, self.user_id)
            return session.scalar(select(FavoriteItem.id).where(FavoriteItem.user_id == user_id, FavoriteItem.product_id == product_id)) is not None

    def remove(self, product_id: int) -> dict[str, Any]:
        """从收藏夹删除商品。

        :param product_id: 要删除的商品 ID。
        :return: 包含商品 ID 和删除状态的操作结果。
        """
        with session_scope(self.engine) as session:
            user_id = resolve_user_id(session, self.user_id)
            result = session.execute(delete(FavoriteItem).where(FavoriteItem.user_id == user_id, FavoriteItem.product_id == product_id))
            return {"product_id": product_id, "removed": result.rowcount > 0}

    def clear(self) -> None:
        """清空收藏夹。

        :return: 无返回值。
        """
        with session_scope(self.engine) as session:
            user_id = resolve_user_id(session, self.user_id)
            session.execute(delete(FavoriteItem).where(FavoriteItem.user_id == user_id))
