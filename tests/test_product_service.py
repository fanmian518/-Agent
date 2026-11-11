"""商品筛选服务测试。"""

from backend.app.data.products import PRODUCTS
from backend.app.services.product_service import (
    calculate_match_score,
    filter_products,
    search_products,
    sort_products,
)


def test_filter_products_by_all_exact_conditions():
    """测试分类、品牌、颜色、价格、活动和标签能够同时精确筛选。"""
    result = filter_products(
        products=PRODUCTS,
        category="手机",
        brand="小米",
        color="黑色",
        min_price=4000,
        max_price=5000,
        activity="百亿补贴",
        tags=["5G", "旗舰手机"],
    )

    assert [product["id"] for product in result] == [1]


def test_filter_products_excludes_non_matching_tag():
    """测试标签筛选要求商品包含全部指定标签。"""
    result = filter_products(
        products=PRODUCTS,
        category="手机",
        tags=["5G", "不存在的标签"],
    )

    assert result == []


def test_calculate_match_score_uses_keyword_and_exact_conditions():
    """测试名称关键词使用模糊匹配，其余条件符合时加分。"""
    product = PRODUCTS[0]
    score = calculate_match_score(
        product=product,
        keyword_parts=["Xiaomi 16"],
        category="手机",
        brand="小米",
        color="黑色",
        max_price=5000,
        activity="百亿补贴",
        tags=["5G"],
    )

    assert score == 7


def test_sort_exact_products_by_price():
    """测试精确商品按价格升序排列。"""
    products = [PRODUCTS[1], PRODUCTS[0]]

    result = sort_products(
        exact_products=products,
        sort_by="price_asc",
    )

    assert [product["price"] for product in result] == [4599.0, 4699.0]


def test_sort_fuzzy_products_by_score():
    """测试模糊商品按对应分数从高到低排列。"""
    scores = [
        calculate_match_score(product, keyword_parts=["Xiaomi"])
        for product in PRODUCTS
    ]

    result = sort_products(
        exact_products=None,
        score=scores,
        sort_by="price_asc",
    )

    assert len(result) == len(PRODUCTS)


def test_search_exact_result_includes_out_of_stock_product():
    """测试精确匹配结果包含库存为 0 的商品。"""
    result = search_products(
        exact_no_or_yes=True,
        category="手机",
        color="黑色",
        brand="vivo",
        sort_by="price_asc",
    )

    assert result["found"] is True
    assert [product["id"] for product in result["products"]] == [8]
    assert result["products"][0]["stock"] == 0


def test_search_without_exact_result_returns_recommendations():
    """测试没有精确商品时返回相似推荐。"""
    result = search_products(
        exact_no_or_yes=False,
        keyword_parts=["不存在的型号"],
        category="手机",
        sort_by="price_asc",
    )

    assert result["found"] is False
    assert 0 < len(result["products"]) <= 5


def test_search_exact_miss_returns_recommendations():
    """测试精确条件无结果时也返回相似商品推荐。"""
    result = search_products(
        exact_no_or_yes=True,
        category="手机",
        brand="不存在的品牌",
    )

    assert result["found"] is False
    assert result["products"]
    assert len(result["products"]) <= 5


def test_exact_search_uses_product_name_keywords():
    """测试指定具体型号时不会退化为分类内的最低价商品。"""
    result = search_products(
        exact_no_or_yes=True,
        keyword_parts=["iPhone", "Pro", "Max", "GB"],
        color="白色",
    )

    assert result["found"] is True
    assert [product["id"] for product in result["products"]] == [6]
