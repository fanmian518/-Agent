"""将中文购物指令解析为商品服务可使用的结构化条件。"""

import re
from typing import Any


BRANDS = ["Apple", "小米", "华为", "OPPO", "vivo", "Sony", "联想", "罗技", "雷蛇", "Nike", "Adidas", "海尔", "美的", "苏泊尔"]
CATEGORIES = ["手机", "耳机", "笔记本电脑", "鼠标", "智能手表", "冰箱", "电视", "运动鞋", "护肤品", "保温杯", "厨房电器"]
COLORS = ["黑色", "白色", "蓝色", "银色", "灰色", "红色", "透明"]
ACTIVITIES = ["百亿补贴", "以旧换新", "限时直降", "满减", "教育优惠", "分期免息", "店铺优惠券", "家电补贴", "跨店满减"]
TAGS = ["5G", "旗舰手机", "快速充电", "鸿蒙系统", "人像摄影", "无线耳机", "主动降噪", "空间音频", "办公", "轻薄本", "游戏本", "运动健康", "智能穿戴", "跑步鞋", "缓震", "保湿"]


def _find_values(message: str, choices: list[str]) -> list[str]:
    """从文本中提取词典内出现的值。

    :param message: 用户原始购物指令。
    :param choices: 可识别值列表。
    :return: 按词典顺序返回匹配到的值。
    """
    lowered = message.casefold()
    return [choice for choice in choices if choice.casefold() in lowered]


def _parse_price_range(message: str) -> tuple[float | None, float | None]:
    """从用户输入提取价格上下限。

    :param message: 用户原始购物指令。
    :return: `(最低价格, 最高价格)`，未提及时对应值为 None。
    """
    max_match = re.search(r"(?:不超过|低于|少于|以内|以下)\s*(\d+(?:\.\d+)?)\s*元?|(?P<max_value>\d+(?:\.\d+)?)\s*元?\s*(?:以下|以内|以内)", message)
    min_match = re.search(r"(?:不少于|高于|超过|以上)\s*(\d+(?:\.\d+)?)\s*元?|(?P<min_value>\d+(?:\.\d+)?)\s*元?\s*(?:以上|起)", message)
    between_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:到|至|-)\s*(\d+(?:\.\d+)?)\s*元", message)
    if between_match:
        return float(between_match.group(1)), float(between_match.group(2))
    return (
        float(min_match.group(1) or min_match.group("min_value")) if min_match else None,
        float(max_match.group(1) or max_match.group("max_value")) if max_match else None,
    )


def parse_intent(message: str) -> dict[str, Any]:
    """解析用户购物指令，生成商品搜索所需的结构化意图。

    :param message: 用户输入的中文购物指令。
    :return: 包含动作、商品关键词、筛选条件和排序方式的字典。
    """
    if not message or not message.strip():
        raise ValueError("购物指令不能为空")

    text = message.strip()
    categories = _find_values(text, CATEGORIES)
    brands = _find_values(text, BRANDS)
    colors = _find_values(text, COLORS)
    activities = _find_values(text, ACTIVITIES)
    tags = _find_values(text, TAGS)
    min_price, max_price = _parse_price_range(text)
    product_id_match = re.search(r"(?:商品|编号|id)\s*[：:#]?\s*(\d+)", text, re.IGNORECASE)
    order_id_match = re.search(r"(?:订单(?:号|编号)?|order[_ ]?id)\s*[：:#]?\s*([A-Za-z0-9]+)", text, re.IGNORECASE)
    quantity_match = re.search(r"(?:数量|改成|改为)\s*(\d+)", text)
    payment_match = re.search(r"(支付宝|微信支付|银行卡|云闪付)", text)

    action = "search"
    if "购物车" in text and any(word in text for word in ("创建订单", "提交订单", "结算")):
        action = "create_order"
    elif order_id_match and any(word in text for word in ("支付", "付款")):
        action = "pay_order"
    elif product_id_match and any(word in text for word in ("详情", "详细信息")):
        action = "product_detail"
    elif "购物车" in text and any(word in text for word in ("清空", "清除")):
        action = "cart_clear"
    elif "购物车" in text and any(word in text for word in ("查看", "有哪些", "列出")):
        action = "cart_list"
    elif "购物车" in text and any(word in text for word in ("修改数量", "改成", "改为")):
        action = "cart_update"
    elif "购物车" in text and any(word in text for word in ("删除", "移除")):
        action = "cart_remove"
    elif "购物车" in text and any(word in text for word in ("加入", "添加", "放入")):
        action = "search_and_add_to_cart"
    elif "收藏夹" in text and any(word in text for word in ("清空", "清除")):
        action = "favorites_clear"
    elif "收藏夹" in text and any(word in text for word in ("查看", "有哪些", "列出")):
        action = "favorites_list"
    elif "收藏夹" in text and any(word in text for word in ("删除", "移除")):
        action = "favorites_remove"
    elif any(word in text for word in ("收藏", "收藏夹")):
        action = "search_and_add_to_favorites"
    elif any(word in text for word in ("购买", "买", "下单")):
        action = "search_and_buy"

    if any(word in text for word in ("最便宜", "最低价", "价格最低", "便宜")):
        sort_by = "price_asc"
    elif any(word in text for word in ("最贵", "价格最高")):
        sort_by = "price_desc"
    else:
        sort_by = "relevance"

    # 具体型号或名称交给后续大模型/商品匹配层处理，这里只保留已知字段词。
    known_words = set(categories + brands + colors + activities + tags)
    ignored_words = {
        "我想", "帮我", "找一部", "找一台", "加入", "购物车", "收藏夹", "购买",
        "商品", "编号", "查看", "详情", "详细信息", "选择", "最低价", "最高价",
        "推荐", "根据购物车创建订单", "收藏",
    }
    keyword_parts = [
        word for word in re.findall(r"[A-Za-z][A-Za-z0-9+.-]*|[一-龥]{2,}", text)
        if word not in known_words
        and not any(ignored and ignored in word for ignored in ignored_words)
        and not any(known and known in word for known in known_words)
    ]

    exact_no_or_yes = bool(keyword_parts or brands or colors) and not any(word in text for word in ("类似", "推荐", "适合", "附近"))

    return {
        "action": action,
        "exact_no_or_yes": exact_no_or_yes,
        "keyword_parts": keyword_parts,
        "category": categories[0] if categories else None,
        "brand": brands[0] if brands else None,
        "color": colors[0] if colors else None,
        "min_price": min_price,
        "max_price": max_price,
        "tags": tags,
        "activity": activities[0] if activities else None,
        "sort_by": sort_by,
        "product_id": int(product_id_match.group(1)) if product_id_match else None,
        "quantity": int(quantity_match.group(1)) if quantity_match else None,
        "order_id": order_id_match.group(1) if order_id_match else None,
        "payment_method": payment_match.group(1) if payment_match else None,
    }
