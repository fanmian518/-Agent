"""商品数据访问层：统一按 product_id 查询商品。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.data.products import PRODUCTS
from backend.app.db.database import get_engine
from backend.app.db.models import Product


def get_product_by_id(product_id: int) -> dict[str, Any] | None:
    """按商品 ID 查询商品，优先使用 PostgreSQL。

    :param product_id: 商品唯一 ID。
    :return: 商品详情字典；不存在时返回 None。
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            row = connection.execute(
                select(Product).where(Product.id == product_id)
            ).mappings().first()
        engine.dispose()
        if row is not None:
            return dict(row)
    except SQLAlchemyError:
        pass
    return next((dict(product) for product in PRODUCTS if product["id"] == product_id), None)
