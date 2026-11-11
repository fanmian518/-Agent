"""数据库第一步：保存模拟平台商品；其他业务表后续逐项迁移。"""

from decimal import Decimal

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """业务数据模型的统一基类。"""


class Product(Base):
    """商品目录，沿用模拟平台提供的商品 ID。"""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="products_price_nonnegative"),
        CheckConstraint("stock >= 0", name="products_stock_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), index=True)
    brand: Mapped[str] = mapped_column(String(64))
    color: Mapped[str] = mapped_column(String(32))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    activity: Mapped[str | None] = mapped_column(String(128), nullable=True)


class User(Base):
    """用户基础信息。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """登录会话令牌。"""
    __tablename__ = "auth_sessions"
    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Address(Base):
    """用户收货地址，省市区街道小区用于匹配，备注保存门牌等详细信息。"""
    __tablename__ = "addresses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32))
    province: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    street: Mapped[str | None] = mapped_column(String(128), nullable=True)
    community: Mapped[str] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(128)); value: Mapped[Decimal] = mapped_column(Numeric(12,2))
    threshold: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0); scope: Mapped[str] = mapped_column(String(32), default="all")
    desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT")); order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rating: Mapped[float] = mapped_column(Numeric(2,1)); content: Mapped[str] = mapped_column(String(2000)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class FollowedShop(Base):
    __tablename__ = "followed_shops"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True); shop_id: Mapped[int] = mapped_column(Integer, primary_key=True); followed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BrowsingHistory(Base):
    __tablename__ = "browsing_history"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True); product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True); viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CartItem(Base):
    """用户购物车中的商品数量。"""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
        CheckConstraint("quantity > 0", name="cart_quantity_positive"),
    )


class FavoriteItem(Base):
    """用户收藏的商品。"""

    __tablename__ = "favorite_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_favorite_user_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    """订单主表。"""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="order_total_nonnegative"),
        CheckConstraint("coupon_amount >= 0 AND coupon_amount <= total_amount", name="order_coupon_valid"),
        CheckConstraint("payable_amount = total_amount - coupon_amount", name="order_payable_valid"),
        CheckConstraint("status IN ('pending_payment', 'paid', 'cancelled', 'completed')", name="order_status_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending_payment", index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    coupon_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderItem(Base):
    """订单商品明细，保存下单时的价格快照。"""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    product_name: Mapped[str] = mapped_column(String(255))
    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="order_price_nonnegative"),
    )
