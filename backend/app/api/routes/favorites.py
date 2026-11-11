"""收藏夹直接操作接口。"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.services.favorites_service import Favorites
from backend.app.api.dependencies import request_user_id

router = APIRouter(prefix="/favorites", tags=["收藏夹"])
favorites = Favorites()


class FavoriteItemRequest(BaseModel):
    """收藏商品请求。"""

    product_id: int


@router.get("")
def get_favorites(user_id: int | None = Depends(request_user_id)) -> dict:
    """获取收藏夹内容。

    :return: 收藏商品 ID 列表。
    """
    return {"items": Favorites(user_id=user_id).get_items}


@router.post("/items")
def add_favorite(request: FavoriteItemRequest, user_id: int | None = Depends(request_user_id)) -> dict:
    """添加收藏商品。

    :param request: 包含商品 ID 的请求体。
    :return: 收藏结果。
    """
    try:
        return Favorites(user_id=user_id).add(request.product_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/items/{product_id}")
def remove_favorite(product_id: int, user_id: int | None = Depends(request_user_id)) -> dict:
    """删除收藏商品。

    :param product_id: 要删除的商品 ID。
    :return: 删除结果。
    """
    return Favorites(user_id=user_id).remove(product_id)


@router.delete("")
def clear_favorites(user_id: int | None = Depends(request_user_id)) -> dict[str, str]:
    """清空收藏夹。

    :return: 清空结果。
    """
    Favorites(user_id=user_id).clear()
    return {"message": "收藏夹已清空"}
