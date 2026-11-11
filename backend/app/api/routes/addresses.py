"""收货地址接口。"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.app.services.address_service import list_addresses, create_address, use_address, delete_address, set_default
from backend.app.api.dependencies import request_user_id

router = APIRouter(prefix="/addresses", tags=["地址"])
class AddressBody(BaseModel):
    contact_name: str = Field(min_length=1, max_length=64); phone: str = Field(min_length=5, max_length=32)
    province: str; city: str; district: str; street: str | None = None; community: str
    note: str | None = None; is_default: bool = False
class AddressPatch(BaseModel):
    contact_name: str | None = None; phone: str | None = None; note: str | None = None
    is_default: bool | None = None
@router.get("")
def get_addresses(user_id: int | None = Depends(request_user_id)): return {"addresses": list_addresses(user_id)}
@router.post("")
def add_address(data: AddressBody, user_id: int | None = Depends(request_user_id)):
    try: return create_address(data.model_dump(), user_id)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@router.post("/{address_id}/use")
def mark_used(address_id: int, user_id: int | None = Depends(request_user_id)):
    try: return use_address(address_id, user_id)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
@router.delete("/{address_id}")
def remove_address(address_id: int, user_id: int | None = Depends(request_user_id)):
    try: return delete_address(address_id, user_id)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
@router.put("/{address_id}")
def edit_address(address_id: int, data: AddressPatch, user_id: int | None = Depends(request_user_id)):
    try:
        from backend.app.db.database import session_scope
        from backend.app.db.models import Address
        from backend.app.db.user_repository import resolve_user_id
        from sqlalchemy import select
        with session_scope() as s:
            uid = resolve_user_id(s, user_id); row = s.scalar(select(Address).where(Address.id == address_id, Address.user_id == uid).with_for_update())
            if row is None: raise ValueError("地址不存在")
            for key, value in data.model_dump(exclude_none=True).items(): setattr(row, key, value)
            return {"id": row.id, "updated": True}
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
@router.put("/{address_id}/default")
def default_address(address_id: int, user_id: int | None = Depends(request_user_id)):
    try: return set_default(address_id, user_id)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
