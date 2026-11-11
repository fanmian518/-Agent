"""按用户隔离的数据库购物车，默认使用开发测试用户。"""

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from backend.app.db.database import session_scope
from backend.app.db.models import CartItem, Product
from backend.app.db.user_repository import resolve_user_id


class Cart:
    """购物项持久化到 PostgreSQL，不回退内存。"""

    def __init__(self, user_id: int | None = None, engine: Engine | None = None) -> None:
        """配置购物车，不清空已有记录。

        :param user_id: 已有用户 ID；None 使用固定开发用户。
        :param engine: 可选独立数据库连接池。
        :return: 无返回值。
        """
        self.user_id = user_id
        self.engine = engine

    def _user(self, session: Session) -> int:
        """解析并锁定用户行，串行化同一用户的购物车修改。

        :param session: 当前事务会话。
        :return: 用户 ID；用户不存在则报错。
        """
        return resolve_user_id(session, self.user_id)

    def _change(self, product_id: int, quantity: int, increment: bool) -> dict[str, int]:
        """在同一事务内校验库存并保存数量。

        :param product_id: 商品 ID。
        :param quantity: 增量或目标数量。
        :param increment: 是否累加数量。
        :return: 商品 ID 和最终数量。
        """
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("商品数量必须为整数")
        if increment and quantity <= 0:
            raise ValueError("商品数量必须大于 0")
        if quantity < 0:
            raise ValueError("商品数量不能小于 0")
        with session_scope(self.engine) as session:
            user_id = self._user(session)
            item = session.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id))
            if not increment and item is None:
                raise ValueError("商品不在购物车中")
            if not increment and quantity == 0:
                session.delete(item)
                return {"product_id": product_id, "quantity": 0}
            product = session.scalar(select(Product).where(Product.id == product_id).with_for_update())
            if product is None:
                raise ValueError("商品不存在")
            if product.stock == 0:
                raise ValueError("商品暂时缺货")
            final_quantity = quantity + (item.quantity if increment and item else 0)
            if final_quantity > product.stock:
                raise ValueError("商品数量超过库存")
            if item is None:
                session.add(CartItem(user_id=user_id, product_id=product_id, quantity=final_quantity))
            else:
                item.quantity = final_quantity
            return {"product_id": product_id, "quantity": final_quantity}

    def add(self, product_id: int, quantity: int = 1) -> dict[str, int]:
        """添加商品或累加数量。

        :param product_id: 商品 ID。
        :param quantity: 正整数增量。
        :return: 商品 ID 与累计数量。
        """
        return self._change(product_id, quantity, True)

    def update_quantity(self, product_id: int, quantity: int) -> dict[str, int]:
        """修改已有购物项，零表示删除。

        :param product_id: 商品 ID。
        :param quantity: 非负目标数量。
        :return: 商品 ID 与目标数量。
        """
        return self._change(product_id, quantity, False)

    @property
    def get_items(self) -> list[dict[str, int]]:
        """读取当前用户的购物项。

        :return: 按加入顺序排列的商品 ID 和数量。
        """
        with session_scope(self.engine) as session:
            user_id = self._user(session)
            rows = session.execute(select(CartItem.product_id, CartItem.quantity).where(CartItem.user_id == user_id).order_by(CartItem.id))
            return [dict(row) for row in rows.mappings()]

    def remove(self, product_id: int) -> dict[str, int | bool]:
        """删除指定商品。

        :param product_id: 商品 ID。
        :return: 商品 ID 与是否实际删除。
        """
        with session_scope(self.engine) as session:
            user_id = self._user(session)
            result = session.execute(delete(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id))
            return {"product_id": product_id, "removed": result.rowcount > 0}

    def clear(self) -> None:
        """仅清空当前用户的购物车。

        :return: 无返回值。
        """
        with session_scope(self.engine) as session:
            user_id = self._user(session)
            session.execute(delete(CartItem).where(CartItem.user_id == user_id))

    @property
    def total_items(self) -> int:
        """统计购物车总件数。

        :return: 购物项数量之和。
        """
        return sum(item["quantity"] for item in self.get_items)
