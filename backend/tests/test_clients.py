# test_clients.py - Pruebas unitarias para API /clients

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def new_client_data():
    return {"name": "Test User", "email": "test@example.com"}

def test_create_and_get_client(new_client_data):
    # Crear cliente
    res_create = client.post("/clients/", json=new_client_data)
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["name"] == new_client_data["name"]

    # Obtener cliente por ID
    client_id = data["id"]
    res_get = client.get(f"/clients/{client_id}")
    assert res_get.status_code == 200
    assert res_get.json()["email"] == new_client_data["email"]