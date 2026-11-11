"""显式初始化数据库：python -m backend.app.db.init_db --seed-products。"""

import argparse
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import Engine, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from backend.app.data.products import PRODUCTS
from backend.app.db.database import get_engine
from backend.app.db.models import Base, Product


def initialize_database(engine: Engine, seed_products: bool = False) -> dict[str, str | int]:
    """启用 pgvector、创建缺失表，并按需导入初始商品。

    :param engine: 目标 PostgreSQL 数据库连接池。
    :param seed_products: 是否导入模拟商品；已有 ID 的记录保持不变。
    :return: pgvector 扩展版本和当前商品总数。
    """
    if engine.dialect.name != "postgresql":
        raise ValueError("数据库初始化要求 PostgreSQL")
    with engine.begin() as connection:
        vector_available = True
        try:
            with connection.begin_nested():
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except DBAPIError as error:
            # pgvector is optional during the first database phase.  The
            # ordinary product tables can still be initialized without it.
            if "extension \"vector\" is not available" not in str(error.orig):
                raise
            vector_available = False
        Base.metadata.create_all(connection)
        # create_all does not add columns to existing deployments.
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))
        connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS address_id INTEGER REFERENCES addresses(id) ON DELETE SET NULL"))
        connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS remark VARCHAR(255)"))
        connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_reason VARCHAR(255)"))
        connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_status VARCHAR(32)"))
        connection.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ"))
        if seed_products:
            rows = [dict(product, price=Decimal(str(product["price"]))) for product in PRODUCTS]
            connection.execute(insert(Product).values(rows).on_conflict_do_nothing(index_elements=["id"]))
        version = None
        if vector_available:
            version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one()
            # 实际执行向量运算，验证扩展可用。
            connection.execute(text("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector")).scalar_one()
        count = connection.execute(select(func.count()).select_from(Product)).scalar_one()
    return {"vector_version": version, "product_count": count}


def main() -> int:
    """执行数据库初始化命令并输出不包含凭据的结果。

    :return: 成功为 0，配置或连接失败为 1。
    """
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL and pgvector")
    parser.add_argument("--seed-products", action="store_true", help="Insert missing demo products")
    args = parser.parse_args()
    engine = None
    try:
        engine = get_engine()
        result = initialize_database(engine, seed_products=args.seed_products)
    except (ValidationError, ValueError):
        print("数据库配置无效，请检查 .env 中的 PGHOST、PGPORT、PGDATABASE、PGUSER、PGPASSWORD。")
        return 1
    except SQLAlchemyError:
        print("数据库初始化失败，请确认服务已启动、凭据正确、服务器已安装 pgvector 且账号有建表和启用扩展权限。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    vector_status = result["vector_version"] or "not installed (vector search disabled)"
    print(f"PostgreSQL ready; pgvector={vector_status}; products={result['product_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
