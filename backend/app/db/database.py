"""按需创建 PostgreSQL 连接池，并统一管理会话事务。"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from backend.app.db.config import DatabaseSettings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """首次使用数据库时读取配置并创建连接池。

    :return: 当前进程复用的 SQLAlchemy Engine。
    """
    return create_engine(
        DatabaseSettings().url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """提供成功提交、异常回滚并始终关闭的事务会话。

    :param engine: 可选连接池，测试时可传入独立数据库。
    :return: 上下文管理器，在 with 块内提供 Session。
    """
    with Session(engine if engine is not None else get_engine()) as session:
        with session.begin():
            yield session

