import json
from unittest.mock import AsyncMock, patch
import fakeredis
import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from evaluation_runtime import run, task, event, record_usage, summary
from backend.app.infrastructure.redis_store import RedisConversationStore
from backend.app.db.async_database import async_session_scope


def test_metrics_missing_data_and_exact_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv('EVALUATION_DB', str(tmp_path/'metrics.db'))
    with run('test','fixture'):
        task('lookup', {'id':1})
        task('lookup', {'id':1})
        task('lookup', {'id':2})
        event('tool', name='lookup', success=True, latency_ms=1)
        event('tool', name='lookup', success=False, latency_ms=2)
        record_usage('fake',100,20)
    values = summary(mode='fixture',pricing={'currency':'TEST','models':{'fake':{'input_per_million':2,'output_per_million':4}}})
    assert values['task_redundancy_rate'] == pytest.approx(1/3)
    assert values['tool_success_rate'] == .5
    assert values['estimated_cost'] == pytest.approx(.00028)
    assert summary(mode='live')['tool_success_rate'] is None
    with run('test','fixture'):
        record_usage('fake')
    assert summary(mode='fixture')['estimated_cost'] is None


def test_shared_redis_conversation_ownership_and_expiration():
    client = fakeredis.FakeRedis(decode_responses=True)
    first, second = RedisConversationStore(client), RedisConversationStore(client)
    with first.turn(11,None) as (sid,record):
        record.context={'product_ids':[1]}
    with second.turn(11,sid) as (_,record):
        assert record.context['product_ids'] == [1]
    with pytest.raises(ValueError):
        with second.turn(12,sid):
            pass
    client.delete('shopping:session:'+sid)
    with pytest.raises(ValueError):
        with second.turn(11,sid):
            pass


@pytest.mark.asyncio
async def test_async_transaction_commit_and_rollback():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        await connection.execute(text('CREATE TABLE sample (id INTEGER PRIMARY KEY)'))
    async with async_session_scope(engine) as session:
        await session.execute(text('INSERT INTO sample VALUES (1)'))
    with pytest.raises(ValueError):
        async with async_session_scope(engine) as session:
            await session.execute(text('INSERT INTO sample VALUES (2)'))
            raise ValueError('rollback')
    async with async_session_scope(engine) as session:
        assert list((await session.execute(text('SELECT id FROM sample'))).scalars()) == [1]
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_api_health_and_rate_limit(monkeypatch):
    from backend.app.main import app
    monkeypatch.setattr('backend.app.main.rate_allowed',lambda identity:False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/health')).status_code == 200
        response = await client.post('/api/agent/execute',json={'message':'test'})
        assert response.status_code == 429
        assert response.headers['retry-after'] == '60'


def test_redis_rate_counter_is_atomic(monkeypatch):
    from backend.app.infrastructure.redis_store import rate_allowed
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr('backend.app.infrastructure.redis_store.get_redis',lambda:client)
    monkeypatch.setenv('RATE_LIMIT_PER_MINUTE','2')
    assert rate_allowed('user')
    assert rate_allowed('user')
    assert not rate_allowed('user')
    assert rate_allowed('other')
    assert client.ttl(next(client.scan_iter('shopping:limit:*'))) > 0


@pytest.mark.asyncio
async def test_real_async_postgres_connection_supports_host_event_loop():
    from backend.app.db.async_database import get_async_engine
    async with async_session_scope() as session:
        assert (await session.execute(text('SELECT 1'))).scalar_one() == 1
    await get_async_engine().dispose()
    get_async_engine.cache_clear()
