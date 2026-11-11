"""订单直接操作接口。"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.api.routes.cart import cart
from backend.app.services.order_service import OrderService
from backend.app.services.cart_service import Cart
from backend.app.api.dependencies import request_user_id

router = APIRouter(prefix="/orders", tags=["订单"])
order_service = OrderService(cart)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, user_id: int | None = Depends(request_user_id)) -> dict:
    """取消当前用户待支付订单。

    :param order_id: 对外订单号。
    :return: 取消后的订单数据。
    """
    try:
        return OrderService(Cart(user_id=user_id)).cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class PaymentRequest(BaseModel):
    """订单支付请求。"""

    payment_method: str

class CreateOrderRequest(BaseModel):
    address_id: int | None = None
    product_ids: list[int] | None = None
class RemarkRequest(BaseModel): remark: str
class RefundRequest(BaseModel): reason: str


@router.get("")
def get_orders(user_id: int | None = Depends(request_user_id)) -> dict:
    """获取订单列表。

    :return: 订单页面数据。
    """
    return {"orders": OrderService(Cart(user_id=user_id)).orders}

@router.get("/{order_id}")
def order_detail(order_id: str, user_id: int | None = Depends(request_user_id)):
    try: return OrderService(Cart(user_id=user_id)).get_order(order_id)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("")
def create_order(request: CreateOrderRequest | None = None, user_id: int | None = Depends(request_user_id)) -> dict:
    """从购物车创建待支付订单。

    :return: 新订单信息。
    """
    try:
        return OrderService(Cart(user_id=user_id)).create_order(request.product_ids if request else None, request.address_id if request else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/pay")
def pay_order(order_id: str, request: PaymentRequest, user_id: int | None = Depends(request_user_id)) -> dict:
    """确认订单支付方式。

    :param order_id: 订单号。
    :param request: 支付方式请求体。
    :return: 支付后的订单。
    """
    try:
        return OrderService(Cart(user_id=user_id)).pay_order(order_id, request.payment_method)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/{order_id}/remark")
def order_remark(order_id: str, request: RemarkRequest, user_id: int | None = Depends(request_user_id)):
    try: return OrderService(Cart(user_id=user_id)).update_remark(order_id, request.remark)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/{order_id}/refund")
def order_refund(order_id: str, request: RefundRequest, user_id: int | None = Depends(request_user_id)):
    try: return OrderService(Cart(user_id=user_id)).request_refund(order_id, request.reason)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/{order_id}/receive")
def order_receive(order_id: str, user_id: int | None = Depends(request_user_id)):
    try: return OrderService(Cart(user_id=user_id)).confirm_receive(order_id)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
