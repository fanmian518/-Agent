"""购物 Agent 的 LangGraph 状态定义。"""

from typing import Any, TypedDict


class ShoppingState(TypedDict, total=False):
    """Agent 在各节点之间传递的共享状态。"""

    user_message: str
    user_id: int | None
    context: dict[str, Any]
    intent: dict[str, Any]
    products: list[dict[str, Any]]
    product_detail: dict[str, Any] | None
    selected_products: list[dict[str, Any]]
    cart_result: dict[str, Any] | None
    favorites_result: dict[str, Any] | None
    order_result: dict[str, Any] | None
    needs_confirmation: bool
    error: str | None
    knowledge_result: dict[str, Any] | None
    address_required: dict[str, Any] | None
