"""优惠券、评价、关注店铺和浏览历史接口。"""
from datetime import datetime, timezone, timedelta
from secrets import token_hex
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from backend.app.api.dependencies import request_user_id
from backend.app.db.database import session_scope
from backend.app.db.models import Coupon, Review, FollowedShop, BrowsingHistory
from backend.app.db.user_repository import resolve_user_id

router = APIRouter(tags=["用户数据"])
class CouponBody(BaseModel): title: str; value: float = Field(ge=0); threshold: float = Field(default=0, ge=0); scope: str = "all"; desc: str | None = None; duration_days: int = 30
class ReviewBody(BaseModel): product_id: int; order_id: str | None = None; rating: float = Field(ge=1, le=5); content: str = Field(min_length=1, max_length=2000)
class ShopBody(BaseModel): shop_id: int
class HistoryBody(BaseModel): product_id: int
@router.get("/reviews")
def reviews(user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); return {"reviews":[{"id":r.id,"productId":r.product_id,"orderId":r.order_id,"rating":float(r.rating),"content":r.content,"createdAt":int(r.created_at.timestamp()*1000)} for r in s.scalars(select(Review).where(Review.user_id==uid).order_by(Review.created_at.desc()))]}
@router.post("/reviews")
def add_review(data:ReviewBody,user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); row=Review(id=token_hex(12),user_id=uid,product_id=data.product_id,order_id=data.order_id,rating=data.rating,content=data.content); s.add(row); s.flush(); return {"id":row.id,"productId":row.product_id}
@router.delete("/reviews/{review_id}")
def delete_review(review_id:str,user_id:int|None=Depends(request_user_id)):
    with session_scope() as s: uid=resolve_user_id(s,user_id); s.execute(delete(Review).where(Review.id==review_id,Review.user_id==uid)); return {"id":review_id,"deleted":True}

@router.get("/coupons")
def coupons(user_id: int | None = Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); return {"coupons":[{"id":c.id,"title":c.title,"value":float(c.value),"threshold":float(c.threshold),"scope":c.scope,"desc":c.desc,"claimedAt":int(c.start_at.timestamp()*1000),"startAt":int(c.start_at.timestamp()*1000),"endAt":int(c.end_at.timestamp()*1000),"usedAt":int(c.used_at.timestamp()*1000) if c.used_at else None} for c in s.scalars(select(Coupon).where(Coupon.user_id==uid).order_by(Coupon.end_at))]}
@router.post("/coupons")
def claim_coupon(data: CouponBody, user_id: int | None = Depends(request_user_id)):
    now=datetime.now(timezone.utc)
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); row=Coupon(id=token_hex(12),user_id=uid,title=data.title,value=data.value,threshold=data.threshold,scope=data.scope,desc=data.desc,start_at=now,end_at=now+timedelta(days=data.duration_days)); s.add(row); s.flush(); return {"id":row.id,"title":row.title,"value":float(row.value)}
@router.post("/coupons/{coupon_id}/use")
def use_coupon(coupon_id:str,user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); row=s.scalar(select(Coupon).where(Coupon.id==coupon_id,Coupon.user_id==uid).with_for_update())
        if row is None: raise HTTPException(status_code=404, detail="优惠券不存在")
        if row.used_at is not None: raise HTTPException(status_code=400, detail="优惠券已使用")
        row.used_at=datetime.now(timezone.utc); return {"id":row.id,"usedAt":int(row.used_at.timestamp()*1000)}
@router.post("/favorites/shops")
def follow_shop(data: ShopBody, user_id: int | None = Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); s.merge(FollowedShop(user_id=uid,shop_id=data.shop_id)); return {"shop_id":data.shop_id,"followed":True}
@router.get("/favorites/shops")
def followed_shops(user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); return {"items":[{"shop_id":r.shop_id} for r in s.scalars(select(FollowedShop).where(FollowedShop.user_id==uid))]}
@router.delete("/favorites/shops/{shop_id}")
def unfollow_shop(shop_id:int,user_id:int|None=Depends(request_user_id)):
    with session_scope() as s: uid=resolve_user_id(s,user_id); s.execute(delete(FollowedShop).where(FollowedShop.user_id==uid,FollowedShop.shop_id==shop_id)); return {"shop_id":shop_id,"followed":False}
@router.get("/history")
def history(user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); return {"items":[{"product_id":r.product_id,"viewed_at":r.viewed_at.isoformat()} for r in s.scalars(select(BrowsingHistory).where(BrowsingHistory.user_id==uid).order_by(BrowsingHistory.viewed_at.desc()).limit(50))]}
@router.post("/history")
def record_history(data:HistoryBody,user_id:int|None=Depends(request_user_id)):
    with session_scope() as s:
        uid=resolve_user_id(s,user_id); s.merge(BrowsingHistory(user_id=uid,product_id=data.product_id,viewed_at=datetime.now(timezone.utc))); return {"product_id":data.product_id}
@router.delete("/history")
def clear_history(user_id:int|None=Depends(request_user_id)):
    with session_scope() as s: uid=resolve_user_id(s,user_id); s.execute(delete(BrowsingHistory).where(BrowsingHistory.user_id==uid)); return {"message":"浏览历史已清空"}
