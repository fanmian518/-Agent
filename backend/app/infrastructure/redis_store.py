import hashlib
import json
import threading
from contextlib import contextmanager
from functools import lru_cache
from uuid import uuid4

from redis import Redis
from redis.exceptions import LockError
from backend.app.infrastructure.settings import RuntimeSettings


@lru_cache(maxsize=1)
def get_redis():
    settings = RuntimeSettings()
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3) if settings.redis_url else None


def rate_allowed(identity):
    client = get_redis()
    if client is None:
        return True
    settings = RuntimeSettings()
    key = settings.redis_prefix + ':limit:' + hashlib.sha256(identity.encode()).hexdigest()
    count = client.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n", 1, key)
    return count <= settings.rate_limit_per_minute


class RedisConversationStore:
    def __init__(self, client, ttl=1800, prefix='shopping'):
        self.client, self.ttl, self.prefix = client, ttl, prefix

    @contextmanager
    def turn(self, owner, session_id):
        from backend.app.agent.conversation import Conversation
        created = session_id is None
        session_id = session_id or uuid4().hex
        key = f'{self.prefix}:session:{session_id}'
        lock = self.client.lock(key + ':lock', timeout=120, blocking_timeout=5, thread_local=False)
        if not lock.acquire():
            raise ValueError('会话正在处理中，请稍后重试')
        stop = threading.Event()
        lost = threading.Event()

        def renew():
            while not stop.wait(30):
                try:
                    lock.extend(120, replace_ttl=True)
                except Exception:
                    lost.set()
                    return

        worker = threading.Thread(target=renew, daemon=True)
        worker.start()
        try:
            raw = self.client.get(key)
            data = json.loads(raw) if raw else None
            if not created and (data is None or data['owner'] != owner):
                raise ValueError('会话不存在或已过期，请开始新会话')
            record = Conversation(owner, context=data['context'] if data else {})
            yield session_id, record
            if lost.is_set() or not lock.owned():
                raise RuntimeError('会话锁已丢失，请重新加载会话')
            self.client.set(key, json.dumps({'owner': owner, 'context': record.context}, ensure_ascii=False), ex=self.ttl)
        finally:
            stop.set()
            worker.join(timeout=4)
            try:
                lock.release()
            except LockError:
                pass
