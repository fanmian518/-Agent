"""用户收货地址管理与小区级匹配。"""
from datetime import datetime, timezone
from sqlalchemy import select, delete
from backend.app.db.database import session_scope
from backend.app.db.models import Address
from backend.app.db.user_repository import resolve_user_id

FIELDS = ("province", "city", "district", "street", "community")

def _dump(row: Address) -> dict:
    return {"id": row.id, "contact_name": row.contact_name, "phone": row.phone,
            "province": row.province, "city": row.city, "district": row.district,
            "street": row.street, "community": row.community, "note": row.note,
            "is_default": row.is_default, "use_count": row.use_count,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None}

def list_addresses(user_id: int | None = None) -> list[dict]:
    with session_scope() as s:
        uid = resolve_user_id(s, user_id)
        rows = s.scalars(select(Address).where(Address.user_id == uid).order_by(Address.last_used_at.desc().nullslast(), Address.use_count.desc(), Address.id.desc())).all()
        return [_dump(r) for r in rows]

def create_address(data: dict, user_id: int | None = None) -> dict:
    required = [data.get(k, "").strip() for k in ("contact_name", "phone", "province", "city", "district", "community")]
    if any(not x for x in required): raise ValueError("联系人、手机号、省市区和小区不能为空")
    with session_scope() as s:
        uid = resolve_user_id(s, user_id)
        same = s.scalar(select(Address).where(Address.user_id == uid, Address.province == data["province"], Address.city == data["city"], Address.district == data["district"], Address.street == data.get("street"), Address.community == data["community"]))
        if same: raise ValueError("该小区地址已存在")
        if data.get("is_default") or s.scalar(select(Address.id).where(Address.user_id == uid)) is None:
            s.query(Address).filter(Address.user_id == uid).update({Address.is_default: False})
            data["is_default"] = True
        row = Address(user_id=uid, **{k: data.get(k) for k in ("contact_name", "phone", "province", "city", "district", "street", "community", "note", "is_default")})
        s.add(row); s.flush(); return _dump(row)

def use_address(address_id: int, user_id: int | None = None) -> dict:
    with session_scope() as s:
        uid = resolve_user_id(s, user_id); row = s.scalar(select(Address).where(Address.id == address_id, Address.user_id == uid).with_for_update())
        if row is None: raise ValueError("地址不存在")
        row.use_count += 1; row.last_used_at = datetime.now(timezone.utc)
        return _dump(row)

def delete_address(address_id: int, user_id: int | None = None) -> dict:
    with session_scope() as s:
        uid = resolve_user_id(s, user_id); row = s.scalar(select(Address).where(Address.id == address_id, Address.user_id == uid))
        if row is None: raise ValueError("地址不存在")
        s.delete(row); return {"id": address_id, "deleted": True}

def set_default(address_id: int, user_id: int | None = None) -> dict:
    with session_scope() as s:
        uid = resolve_user_id(s, user_id); row = s.scalar(select(Address).where(Address.id == address_id, Address.user_id == uid).with_for_update())
        if row is None: raise ValueError("地址不存在")
        s.query(Address).filter(Address.user_id == uid).update({Address.is_default: False}); row.is_default = True
        return _dump(row)

def find_by_area(data: dict, user_id: int | None = None) -> dict | None:
    with session_scope() as s:
        uid = resolve_user_id(s, user_id)
        row = s.scalar(select(Address).where(Address.user_id == uid, Address.province == data.get("province"), Address.city == data.get("city"), Address.district == data.get("district"), Address.community == data.get("community")))
        return _dump(row) if row else None
