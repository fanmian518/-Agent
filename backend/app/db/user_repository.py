"""开发用户解析；固定身份不能替代正式登录认证。"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.app.db.models import User


def resolve_user_id(session: Session, user_id: int | None = None) -> int:
    """解析用户并锁定用户行，串行化同一用户的集合操作。

    :param session: 调用方当前事务会话。
    :param user_id: 已有用户 ID；None 使用固定开发用户。
    :return: 用户 ID；指定用户不存在时抛出 ValueError。
    """
    if user_id is None:
        session.execute(insert(User).values(phone="dev-shopping-user").on_conflict_do_nothing(index_elements=["phone"]))
        query = select(User.id).where(User.phone == "dev-shopping-user")
    else:
        query = select(User.id).where(User.id == user_id)
    resolved = session.execute(query.with_for_update()).scalar_one_or_none()
    if resolved is None:
        raise ValueError("用户不存在")
    return resolved
