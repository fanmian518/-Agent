"""请求身份解析；未登录时保留开发用户兼容旧测试。"""
from fastapi import Header
from backend.app.services.auth_service import resolve_token

def request_user_id(authorization: str | None = Header(default=None)) -> int | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return resolve_token(token)
