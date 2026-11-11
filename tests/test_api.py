"""FastAPI 接口测试。"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    """测试健康检查接口。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_products_endpoint():
    """测试商品查询接口。"""
    response = client.get("/api/products", params={"category": "耳机"})
    assert response.status_code == 200
    assert response.json()["found"] is True


def test_agent_endpoint_adds_to_cart():
    """测试 Agent 接口可以执行加购。"""
    response = client.post(
        "/api/agent/execute",
        json={"message": "找5000元以下的黑色手机，选择最低价加入购物车"},
    )
    assert response.status_code == 200
    assert response.json()["intent"]["category"] == "手机"
    assert response.json()["products"]

    cart_response = client.get("/api/cart")
    assert cart_response.status_code == 200
    assert cart_response.json()["items"]


def test_cart_update_remove_and_clear_endpoints():
    """测试购物车修改、删除和清空接口。"""
    client.delete("/api/cart")
    assert client.post("/api/cart/items", json={"product_id": 1, "quantity": 1}).status_code == 200
    update = client.put("/api/cart/items/1", json={"quantity": 2})
    assert update.status_code == 200
    assert update.json()["quantity"] == 2
    remove = client.delete("/api/cart/items/1")
    assert remove.status_code == 200
    assert remove.json() == {"product_id": 1, "removed": True}
    clear = client.delete("/api/cart")
    assert clear.json() == {"message": "购物车已清空"}


def test_favorites_direct_endpoints_share_agent_state():
    """测试收藏夹直接接口与 Agent 共用收藏夹实例。"""
    client.delete("/api/favorites")
    response = client.post(
        "/api/agent/execute",
        json={"message": "收藏商品编号1"},
    )
    assert response.status_code == 200
    selected_id = response.json()["favorites_result"]["product_id"]

    listed = client.get("/api/favorites")
    assert listed.status_code == 200
    assert listed.json()["items"] == [{"product_id": selected_id}]

    removed = client.delete(f"/api/favorites/items/{selected_id}")
    assert removed.json() == {"product_id": selected_id, "removed": True}
    assert client.get("/api/favorites").json()["items"] == []


def test_order_create_and_pay_endpoint():
    """测试订单页面可以创建订单并确认支付方式。"""
    client.delete("/api/cart")
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 1})
    created = client.post("/api/orders")
    assert created.status_code == 200
    order = created.json()
    assert order["status"] == "pending_payment"

    paid = client.post(
        f"/api/orders/{order['order_id']}/pay",
        json={"payment_method": "支付宝"},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["payment_method"] == "支付宝"


def test_agent_invalid_cart_operation_returns_bad_request():
    """测试 Agent 业务参数错误返回 400。"""
    response = client.post(
        "/api/agent/execute",
        json={"message": "删除购物车商品"},
    )

    assert response.status_code == 400
    assert "商品 ID" in response.json()["detail"]
