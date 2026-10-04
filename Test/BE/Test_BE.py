import sys
import os

# Thêm thư mục Src/BE vào đường dẫn hệ thống để Python tìm thấy file main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../Src/BE"))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app  # Import app từ file main.py trong Src/BE

client = TestClient(app)

def test_be_auth():
    """Test API xác thực Tenant"""
    response = client.post("/api/auth/validate")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_be_worker_control():
    """Test API bật/tắt Worker (Start/Stop)"""
    response = client.post("/api/worker/control", json={"action": "start"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

def test_be_vietful_sync_and_deduplication():
    """Test luồng Vietful Push và chống trùng lặp dữ liệu"""
    payload = {
        "tenant_id": "Tenant_A",
        "item_code": "PROD_TEST_01",
        "item_name": "Test Item",
        "quantity": 50
    }
    # Gửi lần 1 (Thêm mới)
    res1 = client.post("/api/sync/vietful", json=payload)
    assert res1.status_code == 200
    
    # Gửi lần 2 (Trùng lặp mã để kiểm tra cơ chế chống trùng lặp ở DB)
    res2 = client.post("/api/sync/vietful", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "success"

def test_be_shopify_pull():
    """Test luồng Shopify Pull"""
    response = client.post("/api/sync/shopify?tenant_id=Tenant_B")
    assert response.status_code == 200
    assert response.json()["status"] == "success"