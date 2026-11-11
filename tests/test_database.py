"""数据库配置、事务管理和 PostgreSQL 模型的离线测试。"""

from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateTable

from backend.app.db.config import DatabaseSettings
from backend.app.db.database import session_scope
from backend.app.db.init_db import initialize_database
from backend.app.db.models import Product


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """隔离测试与机器现有的数据库环境变量。

    :param monkeypatch: pytest 提供的环境变量替换工具。
    :return: 无返回值，测试结束后自动恢复环境变量。
    """
    for name in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    """提供仅供事务测试使用的内存数据库。

    :return: 通过 yield 提供独立连接池，并在测试结束后释放。
    """
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE transaction_items (id INTEGER PRIMARY KEY)"))
    try:
        yield engine
    finally:
        engine.dispose()


def test_database_url_preserves_special_characters() -> None:
    """验证用户名和密码中的特殊字符可以正确编码和还原。

    :return: 无返回值，连接地址中的身份信息应保持完整。
    """
    password = "test@:/?#% password"
    settings = DatabaseSettings(
        _env_file=None,
        PGUSER="test@user",
        PGPASSWORD=password,
    )

    url = make_url(settings.url.render_as_string(hide_password=False))

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "test@user"
    assert url.password == password
    assert url.host == "127.0.0.1"
    assert url.port == 5432
    assert url.database == "shopping_agent"


def test_database_config_masks_password() -> None:
    """验证配置对象和默认连接地址不会直接显示密码。

    :return: 无返回值，默认字符串表示及 JSON 输出应隐藏密码。
    """
    password = "test_secret_password_123"
    settings = DatabaseSettings(_env_file=None, PGPASSWORD=password)

    for output in (repr(settings), str(settings), str(settings.url), settings.model_dump_json()):
        assert password not in output
    assert settings.password.get_secret_value() == password


def test_database_config_requires_password() -> None:
    """验证未设置数据库密码时拒绝加载配置。

    :return: 无返回值，应报告缺少 PGPASSWORD。
    """
    with pytest.raises(ValidationError, match="PGPASSWORD"):
        DatabaseSettings(_env_file=None)


def test_database_config_rejects_empty_password() -> None:
    """验证空字符串不能作为数据库密码。

    :return: 无返回值，应报告密码验证失败。
    """
    with pytest.raises(ValidationError, match="PGPASSWORD"):
        DatabaseSettings(_env_file=None, PGPASSWORD="")


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_database_config_rejects_invalid_port(port: int) -> None:
    """验证数据库端口必须位于有效范围。

    :param port: 小于 1 或大于 65535 的端口值。
    :return: 无返回值，应报告 PGPORT 验证失败。
    """
    with pytest.raises(ValidationError, match="PGPORT"):
        DatabaseSettings(_env_file=None, PGPASSWORD="test-password", PGPORT=port)


@pytest.mark.parametrize("port", [1, 65535])
def test_database_config_accepts_port_boundaries(port: int) -> None:
    """验证端口范围的两个边界值均可使用。

    :param port: 有效端口范围的最小值或最大值。
    :return: 无返回值，连接地址应使用指定端口。
    """
    settings = DatabaseSettings(_env_file=None, PGPASSWORD="test-password", PGPORT=port)

    assert settings.url.port == port


def test_session_scope_commits_successful_transaction(sqlite_engine: Engine) -> None:
    """验证正常退出事务上下文后保存数据库修改。

    :param sqlite_engine: 独立的内存 SQLite 连接池。
    :return: 无返回值，新连接应查询到已提交的记录。
    """
    with session_scope(sqlite_engine) as session:
        session.execute(text("INSERT INTO transaction_items (id) VALUES (1)"))

    with sqlite_engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM transaction_items")).scalars().all() == [1]


def test_session_scope_rolls_back_failed_transaction(sqlite_engine: Engine) -> None:
    """验证事务异常时撤销本次修改并保留此前已提交的数据。

    :param sqlite_engine: 独立的内存 SQLite 连接池。
    :return: 无返回值，失败事务的记录不应写入数据库。
    """
    with session_scope(sqlite_engine) as session:
        session.execute(text("INSERT INTO transaction_items (id) VALUES (1)"))

    with pytest.raises(RuntimeError, match="模拟业务异常"):
        with session_scope(sqlite_engine) as session:
            session.execute(text("INSERT INTO transaction_items (id) VALUES (2)"))
            raise RuntimeError("模拟业务异常")

    with sqlite_engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM transaction_items")).scalars().all() == [1]


def test_database_initialization_rejects_sqlite(sqlite_engine: Engine) -> None:
    """验证 PostgreSQL 初始化不能误用于 SQLite 数据库。

    :param sqlite_engine: 独立的内存 SQLite 连接池。
    :return: 无返回值，应在执行 PostgreSQL 语句前拒绝初始化。
    """
    with pytest.raises(ValueError, match="PostgreSQL"):
        initialize_database(sqlite_engine, seed_products=True)


def test_product_model_compiles_for_postgresql() -> None:
    """验证商品表使用精确金额、JSONB 标签和非负库存约束。

    :return: 无返回值，PostgreSQL 建表语句应包含预期类型和约束。
    """
    ddl = str(CreateTable(Product.__table__).compile(dialect=postgresql.dialect()))

    assert "price NUMERIC(12, 2) NOT NULL" in ddl
    assert "tags JSONB NOT NULL" in ddl
    assert "CHECK (price >= 0)" in ddl
    assert "CHECK (stock >= 0)" in ddl
    assert "PRIMARY KEY (id)" in ddl
