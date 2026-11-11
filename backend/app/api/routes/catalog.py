"""Async catalogue metadata with a short Redis cache; inventory stays transactional."""
import asyncio
import json
from fastapi import APIRouter
from redis.exceptions import RedisError
from sqlalchemy import select
from backend.app.db.async_database import async_session_scope
from backend.app.db.models import Product
from backend.app.infrastructure.redis_store import get_redis
from backend.app.infrastructure.settings import RuntimeSettings

router = APIRouter(prefix='/catalog', tags=['商品目录'])


@router.get('/categories')
async def categories():
    client = get_redis()
    key = RuntimeSettings().redis_prefix + ':catalog:categories:v1'
    if client:
        try:
            cached = await asyncio.to_thread(client.get, key)
            if cached:
                return {'categories': json.loads(cached)}
        except (RedisError, ValueError):
            pass
    async with async_session_scope() as session:
        values = list((await session.scalars(select(Product.category).distinct().order_by(Product.category))).all())
    if client:
        try:
            await asyncio.to_thread(client.set, key, json.dumps(values, ensure_ascii=False), ex=60)
        except RedisError:
            pass
    return {'categories': values}
