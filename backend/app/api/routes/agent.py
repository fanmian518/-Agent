"""购物 Agent 接口。"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.app.agent.executor import AgentExecutor
from backend.app.agent.llm_intent_parser import ModelUnavailableError
from backend.app.api.routes.cart import cart
from backend.app.api.routes.favorites import favorites
from backend.app.api.routes.orders import order_service
from backend.app.api.dependencies import request_user_id
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites
from backend.app.services.order_service import OrderService

router = APIRouter(prefix="/agent", tags=["Agent"])
executor = AgentExecutor(cart=cart, favorites=favorites, orders=order_service)


class AgentRequest(BaseModel):
    """Agent 指令请求。"""

    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


@router.post("/execute")
def execute_agent(request: AgentRequest, user_id: int | None = Depends(request_user_id)) -> dict:
    """解析并执行用户购物指令。

    :param request: 包含自然语言购物指令的请求体。
    :return: Agent 执行结果。
    """
    try:
        current_cart = Cart(user_id=user_id)
        current_favorites = Favorites(user_id=user_id)
        current_orders = OrderService(current_cart)
        return AgentExecutor(cart=current_cart, favorites=current_favorites, orders=current_orders).execute(request.message, session_id=request.session_id)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
