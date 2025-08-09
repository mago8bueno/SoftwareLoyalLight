# test_items.py - Pruebas unitarias para API /items

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def new_item_data():
    return {"name": "Test Shirt", "description": "A shirt", "price": 19.99, "stock": 10}

def test_create_and_list_item(new_item_data):
    res_create = client.post("/items/", json=new_item_data)
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["name"] == new_item_data["name"]

    res_list = client.get("/items/")
    assert res_list.status_code == 200
    assert any(item["id"] == data["id"] for item in res_list.json())