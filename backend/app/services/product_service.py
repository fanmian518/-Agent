"""商品筛选、匹配度排序和相似商品推荐服务。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.data.products import PRODUCTS
from backend.app.db.database import get_engine
from backend.app.db.models import Product


def _load_products() -> list[dict[str, Any]]:
    """从 PostgreSQL 读取商品，数据库不可用时回退到测试数据。

    :return: 商品字典列表。
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            rows = connection.execute(select(Product)).mappings().all()
        engine.dispose()
        if rows:
            return [dict(row) for row in rows]
    except SQLAlchemyError:
        pass
    return PRODUCTS


def calculate_match_score(
    product: dict[str, Any],
    keyword_parts: list[str] | None = None,
    category: str | None = None,
    brand: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    activity: str | None = None,
    tags: list[str] | None = None,
) -> int:
    """计算商品的模糊关键词匹配分数。

    :param product: 待评分的商品。
    :param keyword_parts: 已拆分的商品名称关键词。
    :param category: 商品分类。
    :param brand: 商品品牌。
    :param color: 商品颜色。
    :param min_price: 最低价格。
    :param max_price: 最高价格。
    :param activity: 平台活动。
    :param tags: 用户指定的标签列表。
    :return: 关键词匹配分数。
    """

    product_name = product["name"].casefold()
    product_tags = {
        tag.strip().casefold()
        for tag in product["tags"]
    }

    keyword_score = 0

    # 商品名称使用模糊匹配：关键词出现在名称中即可加分。
    for keyword in keyword_parts or []:
        if keyword.strip().casefold() in product_name:
            keyword_score += 1

    # 其他条件使用严格匹配：条件存在且商品符合时加分。
    if category is not None and product["category"] == category:
        keyword_score += 1

    if brand is not None and product["brand"] == brand:
        keyword_score += 1

    if color is not None and product["color"] == color:
        keyword_score += 1

    if min_price is not None and product["price"] >= min_price:
        keyword_score += 1

    if max_price is not None and product["price"] <= max_price:
        keyword_score += 1

    if activity is not None and product["activity"] == activity:
        keyword_score += 1

    matched_tag_count = sum(
        1
        for tag in tags or []
        if tag.strip().casefold() in product_tags
    )
    keyword_score += matched_tag_count

    return keyword_score


def filter_products(
    products: list[dict[str, Any]],
    category: str | None = None,
    brand: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    activity: str | None = None,
    tags: list[str] | None = None,
    keyword_parts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """按照用户明确指定的条件筛选商品。

    :param products: 商品列表。
    :param category: 商品分类。
    :param brand: 商品品牌。
    :param color: 商品颜色。
    :param min_price: 最低价格。
    :param max_price: 最高价格。
    :param activity: 平台活动。
    :param tags: 用户指定的标签列表。
    :param keyword_parts: 商品名称关键词，要求全部出现在名称中。
    :return: 满足所有明确条件的商品列表。
    """

    return [
        product
        for product in products
        if (not category or product["category"] == category) and 
        (not brand or product["brand"] == brand) and 
        (not color or product["color"] == color) and 
        (min_price is None or product["price"] >= min_price) and 
        (max_price is None or product["price"] <= max_price) and 
        (not activity or product["activity"] == activity) and 
        (not tags or all(tag.strip().casefold() in {t.strip().casefold() for t in product["tags"]} for tag in tags)) and
        (not keyword_parts or all(part.strip().casefold() in product["name"].casefold() for part in keyword_parts if part.strip()))
    ]


def sort_products(
    exact_products: list[dict[str, Any]] | None = None,
    score: list[int] | None = None,
    sort_by: str = "relevance",
    products: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """根据商品类型排序商品，精确商品不计算模糊匹配分数。

    :param exact_products: 已准确匹配的商品列表。
    :param score: 商品的匹配分数。
    :param sort_by: 排序方式。
    :return: 排序后的商品列表。
    """

    if exact_products is None and score is None:
        raise ValueError("找不到该商品")

    if exact_products is not None:
        sort_keys = {
            "price_asc": (lambda p: p["price"], False),
            "price_desc": (lambda p: p["price"], True),
        }
        key, reverse = sort_keys.get(sort_by, sort_keys["price_asc"])
        exact_products = sorted(exact_products, key=key, reverse=reverse)
        return exact_products

    scored = [
        (
            product,
            score,
        )
        for product, score in zip(products or PRODUCTS, score)
    ]

    scored.sort(
        key=lambda item: (
            -item[1],
        )
    )

    return [
        item[0]
        for item in scored
    ]


def search_products(
    exact_no_or_yes: bool | None = None,
    category: str | None = None,
    brand: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    keyword_parts: list[str] | None = None,
    tags: list[str] | None = None,
    activity: str | None = None,
    sort_by: str = "relevance",
) -> dict[str, Any]:
    """根据解析后的用户需求查找商品，无结果时推荐相似商品。

    :param exact_products: 由上层匹配逻辑确定的精确商品列表。
    :param fuzzy_products: 由上层匹配逻辑确定的模糊商品列表。
    :param category: 用户指定的商品分类。
    :param brand: 用户指定的品牌。
    :param color: 用户指定的颜色。
    :param min_price: 用户指定的最低价格。
    :param max_price: 用户指定的最高价格。
    :param keyword_parts: 用户输入拆分后的商品名称关键词。
    :param tags: 用户指定的商品标签。
    :param activity: 用户指定的平台活动。
    :param sort_by: 排序方式，可选 relevance、price_asc、price_desc。
    :return: 包含 found、message 和 products 的搜索结果。
    """

    if exact_no_or_yes is None:
        raise ValueError("exact_no_or_yes 参数不能为空")

    products = _load_products()

    if exact_no_or_yes:
        # 解析器可能保留“帮我找”“元以下的”等操作短语。
        # 只有出现在商品名称中的词才作为型号关键词参与精确筛选。
        name_keywords = [
            keyword
            for keyword in keyword_parts or []
            if keyword.strip()
            and any(
                keyword.strip().casefold() in product["name"].casefold()
                for product in products
            )
        ]
        exact_products = filter_products(
                products=products,
                category=category,
                brand=brand,
                color=color,
                min_price=min_price,
                max_price=max_price,
                activity=activity,
                tags=tags,
                keyword_parts=name_keywords,
            )

        if exact_products:
            return {
                "found": True,
                "message": "已找到符合条件的商品。",
                "products": sort_products(exact_products=exact_products, sort_by=sort_by),
            }

        recommendation_scores = [
            calculate_match_score(
                product=product,
                keyword_parts=keyword_parts,
                category=category,
                brand=brand,
                color=color,
                min_price=min_price,
                max_price=max_price,
                activity=activity,
                tags=tags,
            )
            for product in products
        ]
        return {
            "found": False,
            "message": "没有该商品，为您推荐类似商品。",
            "products": sort_products(score=recommendation_scores, products=products, sort_by=sort_by)[:5],
        }

    score = [calculate_match_score(
        product=product,
        keyword_parts=keyword_parts,
        category=category,
        brand=brand,
        color=color,
        min_price=min_price,
        max_price=max_price,
        activity=activity,
        tags=tags,
    ) 
    for product in products
    ]

    return {
        "found": False,
        "message": "没有该商品，为您推荐类似商品。",
        "products": sort_products(
            sort_by=sort_by,
            score=score,
            products=products,
        )[:5],
    }
