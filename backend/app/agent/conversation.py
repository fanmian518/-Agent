"""有容量和闲置期限的进程内会话；业务数据仍由数据库持久化。"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from uuid import uuid4

FILTER_FIELDS = ("exact_no_or_yes", "keyword_parts", "category", "brand", "color",
                 "min_price", "max_price", "tags", "activity", "sort_by")


@dataclass
class Conversation:
    """只保存商品 ID 和有限上下文，不缓存完整商品或身份凭据。"""

    owner: int | str
    context: dict = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
    touched: float = field(default_factory=monotonic)
    active: int = 0


class ConversationStore:
    """线程安全的短期会话存储，同一会话请求顺序执行。"""

    def __init__(self, ttl: float = 1800, capacity: int = 1000):
        """配置闲置过期时间及最大会话数。

        :param ttl: 闲置秒数。
        :param capacity: 最大会话数。
        :return: 无返回值。
        """
        self.ttl = ttl
        self.capacity = capacity
        self.records = {}
        self.lock = Lock()

    @contextmanager
    def turn(self, owner: int | str, session_id: str | None):
        """校验归属并锁定一轮会话，不接受客户端自建的会话 ID。

        :param owner: 后端提供的用户标识。
        :param session_id: 服务器此前返回的会话 ID；None 创建新会话。
        :return: yield 提供会话 ID 和上下文记录。
        """
        with self.lock:
            now = monotonic()
            for key, record in list(self.records.items()):
                if not record.active and now - record.touched >= self.ttl:
                    del self.records[key]
            if session_id is None:
                if len(self.records) >= self.capacity:
                    raise ValueError("会话数量已达上限，请稍后重试")
                session_id = uuid4().hex
                self.records[session_id] = Conversation(owner)
            record = self.records.get(session_id)
            if record is None or record.owner != owner:
                raise ValueError("会话不存在或已过期，请开始新会话")
            record.active += 1
        try:
            with record.lock:
                yield session_id, record
        finally:
            with self.lock:
                record.active -= 1
                record.touched = monotonic()


def remember(context: dict, message: str, result: dict) -> dict:
    """更新有限上下文，仅保存展示顺序中的商品 ID。

    :param context: 上一轮上下文。
    :param message: 当前用户文本。
    :param result: 已完成的图执行结果。
    :return: 新上下文；不修改上一轮对象。
    """
    updated = dict(context)
    intent = result["intent"]
    history = context.get("history", []) + [{"user": message, "action": intent["action"], "reply": result.get("error")}]
    updated["history"] = history[-6:]
    # 地址信息需要支持多轮补全：用户先提供地区和手机号、下一轮再补联系人
    # 时，保留已提取字段，避免模型和用户重复输入。
    if result.get("address_required"):
        pending = dict(context.get("pending_order", {}))
        intent_fields = (
            "province", "city", "district", "street", "community",
            "address_note", "contact_name", "phone", "address_id", "address_index",
        )
        for field_name in intent_fields:
            value = intent.get(field_name)
            if value not in (None, ""):
                pending[field_name] = value
        updated["pending_order"] = pending
    elif intent["action"] == "create_order" and result.get("order_result"):
        updated.pop("pending_order", None)
    if intent["action"] == "clarify":
        return updated
    if "products" in result:
        updated["product_ids"] = [product["id"] for product in result["products"]]
        updated["focused_id"] = updated["product_ids"][0] if len(updated["product_ids"]) == 1 else None
    if intent["action"] == "search" or intent["action"].startswith("search_and_"):
        updated["filters"] = {key: intent.get(key) for key in FILTER_FIELDS}
    if intent.get("product_id") is not None and not result.get("error"):
        updated["focused_id"] = intent["product_id"]
    for field_name in ("cart_result", "favorites_result"):
        collection = result.get(field_name) or {}
        if "items" in collection:
            updated["product_ids"] = [item["product_id"] for item in collection["items"]]
            updated["focused_id"] = updated["product_ids"][0] if len(updated["product_ids"]) == 1 else None
    return updated


class ConfiguredConversationStore:
    def __init__(self):
        self.local = ConversationStore()

    def turn(self, owner, session_id):
        from backend.app.infrastructure.redis_store import get_redis, RedisConversationStore
        from backend.app.infrastructure.settings import RuntimeSettings
        client = get_redis()
        settings = RuntimeSettings()
        store = RedisConversationStore(client, settings.session_ttl_seconds, settings.redis_prefix) if client else self.local
        return store.turn(owner, session_id)


conversations = ConfiguredConversationStore()
