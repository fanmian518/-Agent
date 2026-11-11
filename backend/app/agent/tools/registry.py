"""LangChain 工具注册表。"""

from typing import Any

from langchain_core.tools import StructuredTool

from backend.app.agent.tools.cart_tools import CartTools
from backend.app.agent.tools.favorites_tools import FavoritesTools
from backend.app.agent.tools.product_tools import ProductTools
from backend.app.agent.tools.order_tools import OrderTools
from backend.app.agent.tools.knowledge_tools import answer_knowledge, search_knowledge


def build_agent_tools(
    cart_tools: CartTools,
    favorites_tools: FavoritesTools,
    product_tools: ProductTools | None = None,
    order_tools: OrderTools | None = None,
) -> list[StructuredTool]:
    """将业务工具注册为 LangChain 工具。

    :param cart_tools: 购物车工具实例。
    :param favorites_tools: 收藏夹工具实例。
    :param product_tools: 商品工具实例；未传入时自动创建。
    :param order_tools: 订单工具实例；未传入时注册返回配置错误的占位工具。
    :return: 可传给 LangChain Agent 的工具列表。
    """
    products = product_tools or ProductTools()
    return [
        StructuredTool.from_function(func=search_knowledge, name="search_knowledge",
            description="检索商品说明、活动或售后知识，返回来源原文；价格库存应查业务数据库。"),
        StructuredTool.from_function(func=answer_knowledge, name="answer_knowledge",
            description="基于商品说明、活动或售后来源生成带引用回答；价格库存应查业务数据库。"),
        StructuredTool.from_function(
            func=cart_tools.add_to_cart,
            name="add_to_cart",
            description="将指定商品 ID 和数量加入购物车。",
        ),
        StructuredTool.from_function(
            func=cart_tools.list_cart,
            name="list_cart",
            description="查看购物车中的商品 ID、数量和总件数。",
        ),
        StructuredTool.from_function(
            func=cart_tools.update_cart,
            name="update_cart",
            description="修改购物车中指定商品的数量。",
        ),
        StructuredTool.from_function(
            func=cart_tools.remove_from_cart,
            name="remove_from_cart",
            description="从购物车删除指定商品 ID。",
        ),
        StructuredTool.from_function(
            func=cart_tools.clear_cart,
            name="clear_cart",
            description="清空购物车。",
        ),
        StructuredTool.from_function(
            func=favorites_tools.add_to_favorites,
            name="add_to_favorites",
            description="将指定商品 ID 加入收藏夹。",
        ),
        StructuredTool.from_function(
            func=favorites_tools.list_favorites,
            name="list_favorites",
            description="查看收藏夹中的商品 ID。",
        ),
        StructuredTool.from_function(
            func=favorites_tools.remove_from_favorites,
            name="remove_from_favorites",
            description="从收藏夹删除指定商品 ID。",
        ),
        StructuredTool.from_function(
            func=favorites_tools.clear_favorites,
            name="clear_favorites",
            description="清空收藏夹。",
        ),
        StructuredTool.from_function(
            func=order_tools.create_order if order_tools else (lambda: {"error": "订单工具未配置"}),
            name="create_order",
            description="根据购物车创建待支付订单。",
        ),
        StructuredTool.from_function(
            func=order_tools.pay_order if order_tools else (lambda order_id, payment_method: {"error": "订单工具未配置"}),
            name="pay_order",
            description="使用指定支付方式确认待支付订单。",
        ),
        StructuredTool.from_function(
            func=products.search,
            name="search_products",
            description="按结构化条件搜索商品并返回结果。",
        ),
        StructuredTool.from_function(
            func=products.get_detail,
            name="get_product_detail",
            description="根据商品 ID 获取商品详情。",
        ),
    ]
