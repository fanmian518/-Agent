"""商品查询接口。"""

from fastapi import APIRouter, HTTPException
from backend.app.db.product_repository import get_product_by_id

from backend.app.services.product_service import search_products

router = APIRouter(prefix="/products", tags=["商品"])


@router.get("")
def get_products(
    category: str | None = None,
    brand: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    activity: str | None = None,
) -> dict:
    """根据结构化条件查询商品。

    :param category: 商品分类。
    :param brand: 商品品牌。
    :param color: 商品颜色。
    :param min_price: 最低价格。
    :param max_price: 最高价格。
    :param activity: 平台活动。
    :return: 商品搜索结果。
    """
    return search_products(
        exact_no_or_yes=True,
        category=category,
        brand=brand,
        color=color,
        min_price=min_price,
        max_price=max_price,
        activity=activity,
    )

@router.get("/{product_id}")
def get_product_detail(product_id: int) -> dict:
    """按商品 ID 返回数据库商品详情。"""
    product = get_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product
