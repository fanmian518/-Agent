from contextlib import asynccontextmanager
from functools import lru_cache
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from backend.app.db.config import DatabaseSettings


@lru_cache(maxsize=1)
def get_async_engine():
    # asyncpg supports the default Windows Proactor loop; synchronous paths keep psycopg.
    return create_async_engine(DatabaseSettings().url.set(drivername='postgresql+asyncpg'), pool_pre_ping=True, connect_args={'timeout': 5})


@asynccontextmanager
async def async_session_scope(engine=None):
    factory = async_sessionmaker(engine if engine is not None else get_async_engine(), expire_on_commit=False)
    async with factory.begin() as session:
        yield session
