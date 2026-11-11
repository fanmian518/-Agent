"""业务表结构的离线验证。"""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.app.db.models import Base


def test_business_tables_compile() -> None:
    """验证所有业务表可生成 PostgreSQL 建表语句。

    :return: 无返回值，表和外键目标应完整。
    """
    assert set(Base.metadata.tables) == {
        "products", "users", "cart_items", "favorite_items", "orders", "order_items", "auth_sessions", "addresses", "coupons", "reviews", "followed_shops", "browsing_history"
    }
    for table in Base.metadata.sorted_tables:
        assert "CREATE TABLE" in str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for foreign_key in table.foreign_keys:
            assert foreign_key.column is not None


def test_business_constraints() -> None:
    """验证用户商品唯一性、数量和金额约束已声明。

    :return: 无返回值，关键数据库约束应存在。
    """
    expected = {
        "cart_items": {"uq_cart_user_product", "cart_quantity_positive"},
        "favorite_items": {"uq_favorite_user_product"},
        "orders": {"order_total_nonnegative", "order_coupon_valid", "order_payable_valid", "order_status_valid"},
        "order_items": {"order_quantity_positive", "order_price_nonnegative"},
    }
    for name, names in expected.items():
        assert names <= {constraint.name for constraint in Base.metadata.tables[name].constraints}
