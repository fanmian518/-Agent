"""LangGraph 购物 Agent 的最小可运行流程骨架。"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from evaluation_runtime import task

from backend.app.agent.llm_intent_parser import parse_intent
from backend.app.agent.state import ShoppingState
from backend.app.services.product_service import search_products
from backend.app.services.address_service import find_by_area, list_addresses, create_address


def _resolve_order_address(intent: dict[str, Any], user_id: int | None) -> tuple[int | None, dict[str, Any] | None]:
    """解析下单地址；已有地址可复用，新地址必须补齐必填字段。

    :param intent: 已解析的下单意图。
    :param user_id: 当前用户 ID。
    :return: `(address_id, required_payload)`；地址缺失时返回提示数据。
    """
    core_fields = ("province", "city", "district", "community")
    required_fields = core_fields + ("contact_name", "phone")
    labels = {
        "province": "省",
        "city": "市",
        "district": "区",
        "community": "小区",
        "contact_name": "联系人名称",
        "phone": "手机号",
    }
    address_index = intent.get("address_index")
    if address_index is not None:
        addresses = list_addresses(user_id)
        if 1 <= address_index <= len(addresses):
            return addresses[address_index - 1]["id"], None
        return None, {
            "message": f"没有第 {address_index} 个地址，请选择弹窗中的有效地址。",
            "addresses": addresses,
            "can_create": True,
            "missing_fields": ["address_index"],
        }
    supplied_any = any(intent.get(field) for field in required_fields)
    if all(intent.get(field) for field in core_fields):
        existing = find_by_area(
            {field: intent[field] for field in core_fields},
            user_id,
        )
        if existing:
            return existing["id"], None

    missing = [field for field in required_fields if not intent.get(field)]
    if supplied_any:
        names = "、".join(labels[field] for field in missing)
        message = f"创建新地址还缺少：{names}。请补充完整后再下单。"
    else:
        message = "请选择已有收货地址，或提供省、市、区、小区、联系人名称和手机号后新建地址。"
    return None, {
        "message": message,
        "addresses": list_addresses(user_id),
        "can_create": True,
        "missing_fields": missing,
    }


def execute_tool_node(state: ShoppingState, tools: dict[str, Any]) -> dict[str, Any]:
    """根据搜索后的动作调用已注册工具。

    :param state: 当前 Agent 状态。
    :param tools: 以工具名称为键的 LangChain 工具映射。
    :return: 工具执行结果状态更新。
    """
    action = state["intent"]["action"]
    intent = state["intent"]
    if action == "knowledge_question":
        result = tools["answer_knowledge"].invoke({"query": intent.get("knowledge_query") or state["user_message"]})
        return {"knowledge_result": result}
    if action == "pay_order":
        raise ValueError("请在订单页面确认支付，Agent 不执行支付")
    selected = state.get("selected_products", [])
    operation_actions = {
        "search_and_add_to_cart", "search_and_add_to_favorites",
        "search_and_remove_from_cart", "search_and_remove_from_favorites",
    }
    if action in operation_actions and not selected and intent.get("product_id") is None:
        return {"error": "没有找到符合条件的商品，未执行操作。"}
    address_id = intent.get("address_id")
    if action in {"search_and_buy", "create_order"} and not address_id:
        address_id, required_payload = _resolve_order_address(intent, state.get("user_id"))
        if required_payload:
            # 只有必填地址字段齐全且小区地址不存在时才创建新地址。
            if not required_payload.get("missing_fields"):
                address = create_address({
                    "contact_name": intent["contact_name"],
                    "phone": intent["phone"],
                    "province": intent["province"],
                    "city": intent["city"],
                    "district": intent["district"],
                    "street": intent.get("street"),
                    "community": intent["community"],
                    "note": intent.get("address_note"),
                }, state.get("user_id"))
                address_id = address["id"]
            else:
                return {"address_required": required_payload}
    direct = {
        "product_detail": ("get_product_detail", {"product_id": intent["product_id"]}),
        "pay_order": ("pay_order", {"order_id": intent["order_id"], "payment_method": intent["payment_method"]}),
        "create_order": ("create_order", {"address_id": address_id} if address_id else {}),
        "cart_list": ("list_cart", {}),
        "cart_clear": ("clear_cart", {}),
        "cart_remove": ("remove_from_cart", {"product_id": intent["product_id"]}),
        "cart_update": ("update_cart", {"product_id": intent["product_id"], "quantity": intent["quantity"]}),
        "favorites_list": ("list_favorites", {}),
        "favorites_clear": ("clear_favorites", {}),
        "favorites_remove": ("remove_from_favorites", {"product_id": intent["product_id"]}),
    }
    if intent["product_id"] is not None:
        direct.update({
            "search_and_add_to_cart": (
                "add_to_cart",
                {
                    "product_id": intent["product_id"],
                    "quantity": intent.get("quantity") or 1,
                },
            ),
            "search_and_add_to_favorites": ("add_to_favorites", {"product_id": intent["product_id"]}),
        })
        if action == "search_and_buy":
            tools["add_to_cart"].invoke({
                "product_id": intent["product_id"],
                "quantity": intent.get("quantity") or 1,
            })
            return {"order_result": tools["create_order"].invoke({"product_ids": [intent["product_id"]], "address_id": address_id})}
    if action in direct:
        tool_name, arguments = direct[action]
        if action in {"cart_remove", "cart_update", "favorites_remove"} and arguments.get("product_id") is None:
            raise ValueError("操作商品需要提供商品 ID")
        if action == "cart_update" and arguments.get("quantity") is None:
            raise ValueError("修改购物车数量需要提供商品 ID 和数量")
        if action == "pay_order" and arguments.get("order_id") is None:
            raise ValueError("支付订单需要提供订单号")
        if action == "pay_order" and arguments.get("payment_method") is None:
            raise ValueError("支付订单需要提供支付方式")
    else:
        if not selected:
            return {}
        tool_name = {
            "product_detail": "get_product_detail",
            "search_and_add_to_cart": "add_to_cart",
            "search_and_add_to_favorites": "add_to_favorites",
            "search_and_remove_from_cart": "remove_from_cart",
            "search_and_remove_from_favorites": "remove_from_favorites",
            "search_and_buy": "create_order",
        }.get(action)
        if tool_name is None:
            return {}
        if intent.get("target_scope") == "all" and action in {"search_and_add_to_cart", "search_and_add_to_favorites", "search_and_remove_from_cart", "search_and_remove_from_favorites"}:
            tool_name = {"search_and_add_to_cart": "add_to_cart", "search_and_add_to_favorites": "add_to_favorites", "search_and_remove_from_cart": "remove_from_cart", "search_and_remove_from_favorites": "remove_from_favorites"}[action]
            results = []
            skipped = []
            for product in selected:
                arguments = {"product_id": product["id"]}
                if tool_name == "add_to_cart":
                    arguments["quantity"] = intent.get("quantity") or 1
                try:
                    results.append(tools[tool_name].invoke(arguments))
                except ValueError as error:
                    skipped.append({"product_id": product["id"], "reason": str(error)})
            key = "cart_result" if tool_name in {"add_to_cart", "remove_from_cart"} else "favorites_result"
            return {key: {"items": results, "count": len(results), "skipped": skipped, "scope": "all"}}
        if action == "search_and_buy":
            tools["add_to_cart"].invoke({"product_id": selected[0]["id"], "quantity": intent.get("quantity") or 1})
            arguments = {"product_ids": [selected[0]["id"]], "address_id": address_id}
        else:
            arguments = {"product_id": selected[0]["id"]}
            if action == "search_and_add_to_cart":
                arguments["quantity"] = intent.get("quantity") or 1
    result = tools[tool_name].invoke(arguments)
    if tool_name == "get_product_detail":
        return {"product_detail": result, "products": [result], "selected_products": [result]}
    if tool_name in {"add_to_cart", "list_cart", "update_cart", "remove_from_cart", "clear_cart"}:
        return {"cart_result": result}
    if tool_name in {"create_order", "pay_order"}:
        return {"order_result": result}
    return {"favorites_result": result}


def route_after_intent(state: ShoppingState) -> str:
    """决定意图是直接调用工具还是先搜索商品。

    :param state: 已完成意图解析的状态。
    :return: 下一个图节点名称。
    """
    direct_actions = {"knowledge_question", "product_detail", "create_order", "pay_order", "cart_list", "cart_clear", "cart_remove", "cart_update", "favorites_list", "favorites_clear", "favorites_remove"}
    intent = state["intent"]
    if intent["action"] == "clarify":
        return END
    if intent["action"] in direct_actions:
        return "execute_tool"
    if intent.get("product_id") is not None and intent["action"] in {"search_and_add_to_cart", "search_and_add_to_favorites", "search_and_buy"}:
        return "execute_tool"
    return "search_products"


def parse_intent_node(state: ShoppingState) -> dict[str, Any]:
    """解析用户购物指令。

    :param state: 当前购物 Agent 状态。
    :return: 写入结构化意图的状态更新。
    """
    context = state.get("context")
    intent = parse_intent(state["user_message"], context=context) if context else parse_intent(state["user_message"])
    task(intent['action'], intent)
    return {"intent": intent, "error": (intent.get("clarification") or "请补充明确的购物需求；支付请在订单页面确认。") if intent["action"] == "clarify" else None}


def search_products_node(
    state: ShoppingState,
    product_search: Any = search_products,
    collection_ids: list[int] | None = None,
) -> dict[str, Any]:
    """根据解析后的意图查询商品。

    :param state: 包含 intent 的购物 Agent 状态。
    :return: 写入商品列表和错误信息的状态更新。
    """
    intent = state["intent"]
    result = product_search(
        exact_no_or_yes=intent["exact_no_or_yes"],
        category=intent["category"],
        brand=intent["brand"],
        color=intent["color"],
        min_price=intent["min_price"],
        max_price=intent["max_price"],
        keyword_parts=intent["keyword_parts"],
        tags=intent["tags"],
        activity=intent["activity"],
        sort_by=intent["sort_by"],
    )
    if collection_ids is not None:
        allowed = set(collection_ids)
        result["products"] = [p for p in result["products"] if p["id"] in allowed]
        result["found"] = bool(result["products"])
    # 推荐结果只用于展示，只有精确匹配成功时才允许后续交易动作使用
    # selected_products。这样“找不到商品并推荐类似商品”不会误加购或下单。
    return {
        "products": result["products"][:1] if intent.get("single_best") else result["products"],
        "selected_products": (result["products"][:1] if intent.get("single_best") or intent.get("target_scope") != "all" else result["products"]) if result["found"] else [],
        "error": None if result["found"] else result["message"],
    }


def build_shopping_graph(tools: list[Any] | None = None):
    """构建最小购物 Agent 状态图。

    :return: 编译后的 LangGraph 图，可通过 `.invoke()` 执行。
    """
    graph = StateGraph(ShoppingState)
    graph.add_node("parse_intent", parse_intent_node)
    if tools:
        tool_map = {tool.name: tool for tool in tools}
        def scoped_search(state: ShoppingState):
            collection = state["intent"].get("target_collection", "none")
            ids = None
            if collection == "cart":
                ids = [item["product_id"] for item in tool_map["list_cart"].invoke({}).get("items", [])]
            elif collection == "favorites":
                ids = [item["product_id"] for item in tool_map["list_favorites"].invoke({}).get("items", [])]
            return search_products_node(state, lambda **filters: tool_map["search_products"].invoke(filters), ids)
        graph.add_node(
            "search_products",
            scoped_search,
        )
    else:
        graph.add_node("search_products", search_products_node)
    if tools:
        graph.add_node("execute_tool", lambda state: execute_tool_node(state, tool_map))
    else:
        # 基础图只提供商品搜索；直接操作需要执行器注入工具后才能完成。
        graph.add_node(
            "execute_tool",
            lambda state: {"error": "当前图未配置购物车、收藏夹或订单工具。"},
        )
    graph.add_edge(START, "parse_intent")
    graph.add_conditional_edges("parse_intent", route_after_intent)
    if tools:
        graph.add_edge("search_products", "execute_tool")
    else:
        graph.add_edge("search_products", END)
    graph.add_edge("execute_tool", END)
    return graph.compile()


shopping_graph = build_shopping_graph()
