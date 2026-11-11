"""持久化订单与商品快照；支付仅为本地模拟确认。"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from backend.app.db.database import session_scope
from backend.app.db.models import CartItem, Order, OrderItem, Product
from backend.app.db.user_repository import resolve_user_id
from backend.app.services.cart_service import Cart
from backend.app.services.inventory_service import RESERVATION_TTL, reserved_quantity


class OrderService:
    """根据购物车用户身份创建、查询和更新数据库订单。"""

    def __init__(self, cart: Cart) -> None:
        """初始化订单服务。

        :param cart: 创建订单时使用的购物车。
        :return: 无返回值。
        """
        self.cart = cart

    @staticmethod
    def _serialize(order: Order, items: list[OrderItem]) -> dict[str, Any]:
        """将数据库快照转换为原有前端响应格式。

        :param order: 当前事务中的订单记录。
        :param items: 该订单的商品快照列表。
        :return: 可 JSON 序列化的订单页面数据。
        """
        return {
            "order_id": order.order_id,
            "address_id": order.address_id,
            "created_at": order.created_at.astimezone(timezone.utc).isoformat(),
            "expires_at": (order.created_at + RESERVATION_TTL).astimezone(timezone.utc).isoformat(),
            "items": [{"product_id": item.product_id, "name": item.product_name,
                       "price": float(item.unit_price), "quantity": item.quantity,
                       "amount": float(item.unit_price * item.quantity)} for item in items],
            "total_amount": float(order.total_amount),
            "coupon_amount": float(order.coupon_amount),
            "payable_amount": float(order.payable_amount),
            "payment_method": order.payment_method,
            "remark": order.remark,
            "refund_reason": order.refund_reason,
            "refund_status": order.refund_status,
            "confirmed_at": order.confirmed_at.astimezone(timezone.utc).isoformat() if order.confirmed_at else None,
            "status": order.status,
        }

    def create_order(self, product_ids: list[int] | None = None, address_id: int | None = None) -> dict[str, Any]:
        """根据购物车内容创建待支付订单。

        :return: 订单号、商品、金额和支付状态。
        """
        with session_scope(self.cart.engine) as session:
            user_id = resolve_user_id(session, self.cart.user_id)
            address = None
            if address_id is not None:
                from backend.app.db.models import Address
                address = session.scalar(select(Address).where(Address.id == address_id, Address.user_id == user_id).with_for_update())
                if address is None:
                    raise ValueError("收货地址不存在")
                address.use_count += 1
                address.last_used_at = datetime.now(timezone.utc)
            query = select(CartItem).where(CartItem.user_id == user_id)
            if product_ids is not None:
                if not product_ids:
                    raise ValueError("没有可下单的商品")
                query = query.where(CartItem.product_id.in_(product_ids))
            items = session.scalars(query.order_by(CartItem.id)).all()
            if not items:
                raise ValueError("购物车为空")
            products = {product.id: product for product in session.scalars(
                select(Product).where(Product.id.in_([item.product_id for item in items]))
                .order_by(Product.id).with_for_update()
            )}
            details = []
            total = Decimal("0.00")
            for item in items:
                product = products.get(item.product_id)
                if product is None:
                    raise ValueError("商品不存在")
                if item.quantity > product.stock - reserved_quantity(session, product.id, datetime.now(timezone.utc)):
                    raise ValueError("商品库存不足")
                total += product.price * item.quantity
                details.append(OrderItem(product_id=product.id, product_name=product.name,
                                         unit_price=product.price, quantity=item.quantity))
            order = Order(user_id=user_id, order_id=uuid4().hex, address_id=address_id,
                          created_at=datetime.now(timezone.utc), status="pending_payment",
                          total_amount=total, coupon_amount=Decimal("0.00"), payable_amount=total)
            session.add(order)
            session.flush()
            for item in details:
                item.order_id = order.id
            session.add_all(details)
            session.flush()
            return self._serialize(order, details)

    @property
    def orders(self) -> list[dict[str, Any]]:
        """获取已创建订单。

        :return: 订单列表。
        """
        with session_scope(self.cart.engine) as session:
            user_id = resolve_user_id(session, self.cart.user_id)
            orders = session.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.id)).all()
            if not orders:
                return []
            grouped = {order.id: [] for order in orders}
            for order in orders:
                if order.status == "pending_payment" and order.created_at + RESERVATION_TTL <= datetime.now(timezone.utc):
                    order.status = "cancelled"
            for item in session.scalars(select(OrderItem).where(OrderItem.order_id.in_(grouped)).order_by(OrderItem.id)):
                grouped[item.order_id].append(item)
            return [self._serialize(order, grouped[order.id]) for order in orders]

    def pay_order(self, order_id: str, payment_method: str) -> dict[str, Any]:
        """使用指定支付方式确认订单。

        :param order_id: 订单号。
        :param payment_method: 支付方式，例如支付宝或微信支付。
        :return: 更新后的订单。
        """
        if not payment_method.strip():
            raise ValueError("支付方式不能为空")
        if len(payment_method.strip()) > 32:
            raise ValueError("支付方式长度不能超过 32")
        with session_scope(self.cart.engine) as session:
            user_id = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == user_id, Order.order_id == order_id).with_for_update())
            if order is None:
                raise ValueError("订单不存在")
            if order.status != "pending_payment":
                raise ValueError("订单当前不可支付")
            if order.created_at + RESERVATION_TTL <= datetime.now(timezone.utc):
                raise ValueError("订单已过期，库存预占已释放")
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            products = {product.id: product for product in session.scalars(
                select(Product).where(Product.id.in_([item.product_id for item in items]))
                .order_by(Product.id).with_for_update()
            )}
            # 等待商品锁期间订单也可能过期，因此取得锁后再次校验。
            if order.created_at + RESERVATION_TTL <= datetime.now(timezone.utc):
                raise ValueError("订单已过期，库存预占已释放")
            for item in items:
                product = products.get(item.product_id)
                if product is None or product.stock < item.quantity:
                    raise ValueError("商品库存不足")
                product.stock -= item.quantity
                cart_item = session.scalar(select(CartItem).where(
                    CartItem.user_id == user_id, CartItem.product_id == item.product_id,
                    CartItem.created_at <= order.created_at,
                ))
                if cart_item is not None:
                    if cart_item.quantity <= item.quantity:
                        session.delete(cart_item)
                    else:
                        cart_item.quantity -= item.quantity
            order.payment_method = payment_method.strip()
            order.status = "paid"
            session.flush()
            return self._serialize(order, items)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """取消当前用户待支付订单并释放预占，重复取消不重复处理。

        :param order_id: 对外订单号。
        :return: 取消后的订单页面数据。
        """
        with session_scope(self.cart.engine) as session:
            user_id = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == user_id, Order.order_id == order_id).with_for_update())
            if order is None:
                raise ValueError("订单不存在")
            if order.status == "paid":
                raise ValueError("已支付订单不可取消")
            order.status = "cancelled"
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            session.flush()
            return self._serialize(order, items)

    def get_order(self, order_id: str) -> dict[str, Any]:
        """获取当前用户订单详情。"""
        with session_scope(self.cart.engine) as session:
            uid = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == uid, Order.order_id == order_id))
            if order is None: raise ValueError("订单不存在")
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            return self._serialize(order, items)

    def update_remark(self, order_id: str, remark: str) -> dict[str, Any]:
        """保存订单备注。"""
        with session_scope(self.cart.engine) as session:
            uid = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == uid, Order.order_id == order_id).with_for_update())
            if order is None: raise ValueError("订单不存在")
            order.remark = remark.strip()[:255] or None
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            return self._serialize(order, items)

    def request_refund(self, order_id: str, reason: str) -> dict[str, Any]:
        """提交退款申请，支付后订单才可申请。"""
        if not reason.strip(): raise ValueError("退款原因不能为空")
        with session_scope(self.cart.engine) as session:
            uid = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == uid, Order.order_id == order_id).with_for_update())
            if order is None: raise ValueError("订单不存在")
            if order.status != "paid": raise ValueError("当前订单不可申请退款")
            order.refund_reason = reason.strip()[:255]; order.refund_status = "pending"
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            return self._serialize(order, items)

    def confirm_receive(self, order_id: str) -> dict[str, Any]:
        """确认收货并结束订单。"""
        with session_scope(self.cart.engine) as session:
            uid = resolve_user_id(session, self.cart.user_id)
            order = session.scalar(select(Order).where(Order.user_id == uid, Order.order_id == order_id).with_for_update())
            if order is None: raise ValueError("订单不存在")
            if order.status != "paid": raise ValueError("当前订单不可确认收货")
            order.status = "completed"; order.confirmed_at = datetime.now(timezone.utc)
            items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
            return self._serialize(order, items)
