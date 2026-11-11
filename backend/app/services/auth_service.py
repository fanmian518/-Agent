"""账号注册、密码校验和登录会话。"""
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from secrets import token_hex
from sqlalchemy import select
from backend.app.db.database import session_scope
from backend.app.db.models import AuthSession, User

SESSION_TTL = timedelta(days=7)

def _hash(password: str, salt: str) -> str:
    digest = pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2_sha256$200000${salt}${digest}"

def _verify(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("pbkdf2_sha256$"):
        return False
    _, rounds, salt, digest = stored.split("$", 3)
    return _hash(password, salt) == stored

def register(phone: str, password: str) -> dict:
    """注册账号并保存不可逆密码哈希。"""
    if len(phone.strip()) < 2 or len(password) < 4:
        raise ValueError("账号至少 2 个字符，密码至少 4 个字符")
    with session_scope() as session:
        if session.scalar(select(User).where(User.phone == phone.strip())):
            raise ValueError("账号已存在")
        salt = token_hex(16)
        user = User(phone=phone.strip(), password_hash=_hash(password, salt))
        session.add(user)
        session.flush()
        return {"id": user.id, "phone": user.phone}

def login(phone: str, password: str) -> dict:
    """校验账号密码并创建登录令牌。"""
    with session_scope() as session:
        user = session.scalar(select(User).where(User.phone == phone.strip()))
        if user is None:
            raise ValueError("没有该账号，请先注册")
        if not _verify(password, user.password_hash):
            raise ValueError("密码错误，请重新输入")
        token = token_hex(32)
        session.add(AuthSession(token=token, user_id=user.id, expires_at=datetime.now(timezone.utc) + SESSION_TTL))
        return {"token": token, "user": {"id": user.id, "phone": user.phone}}

def resolve_token(token: str | None) -> int:
    """解析未过期令牌，返回用户 ID。"""
    if not token:
        raise ValueError("请先登录")
    with session_scope() as session:
        row = session.scalar(select(AuthSession).where(AuthSession.token == token))
        if row is None or row.expires_at <= datetime.now(timezone.utc):
            raise ValueError("登录已过期，请重新登录")
        return row.user_id
