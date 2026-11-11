"""业务测试使用独立 PostgreSQL schema，不修改开发购物车。"""

from uuid import uuid4

import pytest
import os
os.environ['EVALUATION_MODE'] = 'test'
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.data.products import PRODUCTS
from backend.app.db.config import DatabaseSettings
from backend.app.db.models import Base, Product


@pytest.fixture(autouse=True)
def offline_intent_parser(request, monkeypatch):
    """旧业务回归测试使用规则解析，不访问付费模型。

    :param request: 当前测试信息。
    :param monkeypatch: 临时替换图的解析器。
    :return: 无返回值。
    """
    if request.path.name not in {"test_llm_intent_parser.py", "test_conversation.py"}:
        from backend.app.agent.intent_parser import parse_intent
        monkeypatch.setattr("backend.app.agent.graph.parse_intent", parse_intent)


@pytest.fixture(autouse=True)
def isolated_business_database(request, monkeypatch):
    """为服务和 API 测试创建并清理独立表空间。

    :param request: 当前测试信息。
    :param monkeypatch: 临时替换业务连接池。
    :return: yield 提供测试数据库连接池，其他测试提供 None。
    """
    files = {"test_cart_service.py", "test_api.py", "test_executor.py", "test_agent_tools.py", "test_tool_registry.py", "test_cart_persistence.py"}
    files.update({"test_favorites_service.py", "test_favorites_persistence.py", "test_order_persistence.py"})
    files.add("test_inventory_orders.py")
    files.add("test_conversation.py")
    files.add("test_knowledge.py")
    if request.path.name not in files:
        yield None
        return
    schema = "test_cart_" + uuid4().hex
    engine = create_engine(DatabaseSettings().url)
    scoped = engine.execution_options(schema_translate_map={None: schema})
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    try:
        Base.metadata.create_all(scoped)
        with scoped.begin() as connection:
            connection.execute(Product.__table__.insert(), PRODUCTS)
        monkeypatch.setattr("backend.app.db.database.get_engine", lambda: scoped)
        monkeypatch.setattr("backend.app.db.product_repository.get_engine", lambda: scoped)
        monkeypatch.setattr("backend.app.services.product_service.get_engine", lambda: scoped)
        yield scoped
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
