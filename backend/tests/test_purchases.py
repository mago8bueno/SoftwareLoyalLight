# test_purchases.py - Pruebas unitarias para API /purchases

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def setup_item_and_client():
    # Asumir que endpoints previos funcionan correctamente
    client_data = client.post("/clients/", json={"name": "Buyer"}).json()
    item_data = client.post("/items/", json={"name":"Hat","description":"A hat","price":10,"stock":5}).json()
    return client_data["id"], item_data["id"]

def test_create_purchase_and_stock_update(setup_item_and_client):
    client_id, item_id = setup_item_and_client
    res_purchase = client.post("/purchases/", json={"client_id": client_id, "item_id": item_id, "quantity": 2})
    assert res_purchase.status_code == 201
    purchase = res_purchase.json()
    assert float(purchase["total_price"]) == 20.0

    # Verificar stock actualizado
    res_item = client.get(f"/items/{item_id}")
    assert res_item.json()["stock"] == 3