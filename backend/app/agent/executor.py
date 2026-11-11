"""LangGraph 购物 Agent 执行入口。"""

from typing import Any
from backend.app.agent.conversation import conversations, remember

from backend.app.agent.graph import build_shopping_graph
from backend.app.agent.tools.cart_tools import CartTools
from backend.app.agent.tools.favorites_tools import FavoritesTools
from backend.app.agent.tools.product_tools import ProductTools
from backend.app.agent.tools.registry import build_agent_tools
from backend.app.agent.tools.order_tools import OrderTools
from backend.app.services.cart_service import Cart
from backend.app.services.favorites_service import Favorites
from backend.app.services.order_service import OrderService

class AgentExecutor:
    """LangGraph 购物 Agent 的统一执行入口。"""

    def __init__(
        self,
        cart: Cart | None = None,
        favorites: Favorites | None = None,
        orders: OrderService | None = None,
    ) -> None:
        """创建统一 Agent 执行器。

        :param cart: Agent 使用的购物车实例。
        :param favorites: Agent 使用的收藏夹实例。
        :param orders: Agent 使用的订单服务实例；未传入时创建一个新实例。
        :return: 无返回值。
        """
        self.cart = cart or Cart()
        self.favorites = favorites or Favorites(user_id=self.cart.user_id, engine=self.cart.engine)
        self.cart_tools = CartTools(self.cart)
        self.favorites_tools = FavoritesTools(self.favorites)
        self.product_tools = ProductTools()
        self.orders = orders or OrderService(self.cart)
        self.order_tools = OrderTools(self.orders)
        self.tools = build_agent_tools(
            cart_tools=self.cart_tools,
            favorites_tools=self.favorites_tools,
            product_tools=self.product_tools,
            order_tools=self.order_tools,
        )
        self.shopping_graph = build_shopping_graph(self.tools)

    def execute(
        self,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """执行用户购物指令。

        :param message: 用户输入的中文购物指令。
        :param session_id: 服务器返回的会话 ID；省略时开启新会话。
        :return: LangGraph 执行完成后的最终状态。
        """

        if not message or not message.strip():
            raise ValueError("购物指令不能为空")

        if len(message) > 8000:
            raise ValueError("购物指令过长")
        owner = self.cart.user_id if self.cart.user_id is not None else "development"
        from evaluation_runtime import run
        from evaluation_runtime.callbacks import EvaluationCallback
        from backend.app.infrastructure.telemetry import agent_span
        import os
        with run('shopping-langgraph', mode=os.getenv('EVALUATION_MODE','live')), agent_span(), conversations.turn(owner, session_id) as (current_id, record):
            result = self.shopping_graph.invoke({"user_message": message, "context": record.context, "user_id": self.cart.user_id}, config={'callbacks': [EvaluationCallback()]})
            record.context = remember(record.context, message, result)
            result.pop("context", None)
            result["session_id"] = current_id
        action = result["intent"]["action"]
        result["action"] = action
        result["success"] = not result.get("error") and bool(
            result.get("products")
            or result.get("cart_result")
            or result.get("favorites_result")
            or result.get("order_result")
            or result.get("product_detail")
            or result.get("knowledge_result")
            or result.get("address_required")
        )
        return result
