"""购物车接口。"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.services.cart_service import Cart
from backend.app.api.dependencies import request_user_id

router = APIRouter(prefix="/cart", tags=["购物车"])
cart = Cart()


class CartItemRequest(BaseModel):
    """购物车商品请求。"""

    product_id: int
    quantity: int = 1


class CartQuantityRequest(BaseModel):
    """购物车商品数量修改请求。"""

    quantity: int


@router.get("")
def get_cart(user_id: int | None = Depends(request_user_id)) -> dict:
    """获取购物车内容。

    :return: 商品列表和商品总件数。
    """
    current = Cart(user_id=user_id)
    return {"items": current.get_items, "total_items": current.total_items}


@router.post("/items")
def add_cart_item(request: CartItemRequest, user_id: int | None = Depends(request_user_id)) -> dict:
    """向购物车添加商品。

    :param request: 商品 ID 和数量。
    :return: 加入结果。
    """
    try:
        return Cart(user_id=user_id).add(request.product_id, request.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/items/{product_id}")
def update_cart_item(product_id: int, request: CartQuantityRequest, user_id: int | None = Depends(request_user_id)) -> dict:
    """修改购物车商品数量。

    :param product_id: 要修改的商品 ID。
    :param request: 修改后的商品数量。
    :return: 修改结果。
    """
    try:
        return Cart(user_id=user_id).update_quantity(product_id, request.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/items/{product_id}")
def remove_cart_item(product_id: int, user_id: int | None = Depends(request_user_id)) -> dict:
    """删除购物车中的单个商品。

    :param product_id: 要删除的商品 ID。
    :return: 删除结果。
    """
    return Cart(user_id=user_id).remove(product_id)


@router.delete("")
def clear_cart(user_id: int | None = Depends(request_user_id)) -> dict[str, str]:
    """清空购物车。

    :return: 清空结果。
    """
    Cart(user_id=user_id).clear()
    return {"message": "购物车已清空"}

@router.put("/items/{product_id}/selected")
def select_cart_item(product_id: int, user_id: int | None = Depends(request_user_id)) -> dict:
    """前端选中状态为页面状态，后端返回商品存在确认。"""
    current = Cart(user_id=user_id)
    if not any(item["product_id"] == product_id for item in current.get_items):
        raise HTTPException(status_code=404, detail="商品不在购物车中")
    return {"product_id": product_id, "selected": True}

@router.put("/selected-all")
def select_all_cart(user_id: int | None = Depends(request_user_id)) -> dict:
    return {"selected": True, "items": Cart(user_id=user_id).get_items}
