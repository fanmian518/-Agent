"""购物 Agent FastAPI 应用入口。"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import agent, cart, favorites, orders, products, auth, addresses, user_data

from backend.app.api.routes import catalog
from backend.app.infrastructure.redis_store import get_redis, rate_allowed
from backend.app.db.async_database import get_async_engine
from backend.app.infrastructure.telemetry import configure_telemetry


@asynccontextmanager
async def lifespan(app):
    provider = configure_telemetry()
    yield
    if get_async_engine.cache_info().currsize:
        await get_async_engine().dispose()
        get_async_engine.cache_clear()
    if get_redis.cache_info().currsize and get_redis() is not None:
        get_redis().close()
    get_redis.cache_clear()
    if provider:
        provider.force_flush()


app = FastAPI(title="Shopping Agent API", version="0.2.0", lifespan=lifespan)


@app.middleware('http')
async def limit_agent(request: Request, call_next):
    if request.url.path.startswith(('/api/agent', '/api/auth')):
        identity = request.client.host if request.client else 'unknown'
        try:
            allowed = await asyncio.to_thread(rate_allowed, identity)
        except RedisError:
            return JSONResponse({'detail': '限流服务暂时不可用'}, status_code=503)
        if not allowed:
            return JSONResponse({'detail': '请求过于频繁'}, status_code=429, headers={'Retry-After': '60'})
    return await call_next(request)

app.include_router(catalog.router, prefix='/api')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(addresses.router, prefix="/api")
app.include_router(user_data.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """检查服务是否正常运行。

    :return: 服务状态。
    """
    return {"status": "ok"}
