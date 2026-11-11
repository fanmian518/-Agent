"""商品 Agent 工具。"""

from typing import Any

from backend.app.db.product_repository import get_product_by_id
from backend.app.services.product_service import search_products


class ProductTools:
    """将商品服务包装成 Agent 可调用工具。"""

    def search(
        self,
        exact_no_or_yes: bool,
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
        """按结构化条件搜索商品。

        :param exact_no_or_yes: 是否使用精确匹配。
        :param category: 商品分类。
        :param brand: 商品品牌。
        :param color: 商品颜色。
        :param min_price: 最低价格。
        :param max_price: 最高价格。
        :param keyword_parts: 商品名称关键词。
        :param tags: 商品标签。
        :param activity: 商品活动。
        :param sort_by: 排序方式。
        :return: 搜索结果。
        """
        return search_products(
            exact_no_or_yes=exact_no_or_yes,
            category=category,
            brand=brand,
            color=color,
            min_price=min_price,
            max_price=max_price,
            keyword_parts=keyword_parts,
            tags=tags,
            activity=activity,
            sort_by=sort_by,
        )

    def get_detail(self, product_id: int) -> dict[str, Any]:
        """获取商品详情。

        :param product_id: 商品 ID。
        :return: 商品信息。
        """
        product = get_product_by_id(product_id)
        if product is None:
            raise ValueError("商品不存在")
        return product
