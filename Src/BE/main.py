import time
import psycopg2
import os

from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
import time
from datetime import datetime

app = FastAPI(title="CDMS Backend Services (Full Architecture)")

# Thay thế toàn bộ khối DB_CONFIG cũ bằng khối này:
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cdms_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root"), 
    "host": os.getenv("DB_HOST", "db"), # Lấy tên service 'db' từ docker-compose
    "port": os.getenv("DB_PORT", "5432")
}

# ==========================================
# 1. DATA ACCESS LAYER & DEDUPLICATION (DAL)
# ==========================================
def save_with_deduplication(tenant_id: str, code: str, info: str, qty: int):
    """
    Thực hiện chống trùng lặp (Deduplication) và lưu vào Single Database.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        # Master DB: ON CONFLICT DO NOTHING đảm bảo không bao giờ trùng lặp dữ liệu[cite: 17]
        cursor.execute("""
            INSERT INTO master_product_database (product_code, basic_information)
            VALUES (%s, %s) ON CONFLICT (product_code) DO NOTHING;
        """, (code, info))

        # Tenant Table: Tách biệt hoàn toàn bảng của các tenant[cite: 17]
        table_name = "tenant_a_data" if tenant_id == "Tenant_A" else "tenant_b_data"
        cursor.execute(f"""
            INSERT INTO {table_name} (product_code, inventory_qty)
            VALUES (%s, %s)
            ON CONFLICT (product_code) DO UPDATE SET inventory_qty = EXCLUDED.inventory_qty;
        """, (code, qty))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 2. CONNECTORS & WORKERS (Vietful Push & Shopify Pull)
# ==========================================
class VietfulConnector:
    """Connector kết nối với Messaging System của Vietful[cite: 17]"""
    def consume_message(self, raw_data: dict):
        return raw_data

class ShopifyConnector:
    """Connector chủ động Query dữ liệu từ Shopify API[cite: 17]"""
    def query_api(self, tenant_id: str):
        # Mô phỏng dữ liệu lấy từ Shopify
        return [{"code": "SHP_101", "name": "Shopify Jacket", "qty": 40}]

# ==========================================
# 3. FASTAPI ENDPOINTS (Tương thích với FE & Quản lý Worker)
# ==========================================
class WorkerControlReq(BaseModel):
    action: str # start / stop

class DataSourceReq(BaseModel):
    source: str

class ScheduleReq(BaseModel):
    mode: str

class VietfulPayload(BaseModel):
    tenant_id: str
    item_code: str
    item_name: str
    quantity: int

@app.post("/api/auth/validate")
def validate_token():
    return {"status": "success", "message": "[Python BE] Token valid."}

@app.post("/api/tenant/datasource")
def config_datasource(req: DataSourceReq):
    return {"status": "success", "message": f"Configured data source: {req.source}"}

@app.post("/api/tenant/schedule")
def schedule_worker(req: ScheduleReq):
    return {"status": "success", "message": f"Worker scheduled with mode: {req.mode}"}

# --- Quản lý Worker Lifecycle (Start/Stop & Checkpoints) ---
@app.post("/api/worker/control")
def control_worker(req: WorkerControlReq):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        new_status = "running" if req.action.lower() == "start" else "stopped"
        cursor.execute("""
            INSERT INTO worker_status_registry (worker_id, status, last_checkpoint)
            VALUES ('default_worker', %s, %s)
            ON CONFLICT (worker_id) DO UPDATE SET status = EXCLUDED.status, last_checkpoint = EXCLUDED.last_checkpoint;
        """, (new_status, datetime.now()))
        conn.commit()
        return {"status": "success", "message": f"Worker command '{req.action}' executed successfully."}
    finally:
        cursor.close()
        conn.close()

# --- Trạng thái Worker (Biết chính xác số lượng active) ---
@app.get("/api/worker/status")
def get_worker_status():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT count(*) FROM worker_status_registry WHERE status = 'running';")
        running_count = cursor.fetchone()[0]
        return {"running": running_count, "deployed": 3, "configured": 5}
    finally:
        cursor.close()
        conn.close()

# --- Telemetry & Performance Metrics ---
@app.get("/api/worker/metrics")
def get_performance_metrics():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT AVG(latency_ms), SUM(throughput), SUM(wrong_records) FROM system_performance_metrics;")
        row = cursor.fetchone()
        return {
            "throughput": f"{row[1] or 0} records/sec",
            "latency": f"{int(row[0] or 0)}ms",
            "errors": row[2] or 0
        }
    finally:
        cursor.close()
        conn.close()

# --- Xử lý nguồn 1: Vietful (Push / Webhook) ---
@app.post("/api/sync/vietful")
def vietful_push_sync(payload: VietfulPayload):
    start_time = time.time()
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        # Lưu qua bộ lọc chống trùng lặp và phân tách bảng tenant[cite: 17]
        save_with_deduplication(payload.tenant_id, payload.item_code, payload.item_name, payload.quantity)
        
        # Ghi nhận Metrics và Checkpoint[cite: 15]
        latency = int((time.time() - start_time) * 1000)
        cursor.execute("INSERT INTO system_performance_metrics (worker_id, latency_ms, throughput, wrong_records) VALUES ('vietful_worker', %s, 1, 0)", (latency,))
        conn.commit()
        return {"status": "success", "message": f"Vietful Push synced for {payload.item_code}"}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cursor.close()
        conn.close()

# --- Xử lý nguồn 2: Shopify (Pull / Query) ---
@app.post("/api/sync/shopify")
def shopify_pull_sync(tenant_id: str):
    start_time = time.time()
    connector = ShopifyConnector()
    products = connector.query_api(tenant_id)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        success_count = 0
        for p in products:
            save_with_deduplication(tenant_id, p["code"], p["name"], p["qty"])
            success_count += 1
            
        latency = int((time.time() - start_time) * 1000)
        cursor.execute("INSERT INTO system_performance_metrics (worker_id, latency_ms, throughput, wrong_records) VALUES ('shopify_worker', %s, %s, 0)", (latency, success_count))
        conn.commit()
        return {"status": "success", "message": f"Shopify Pull synced {success_count} items."}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cursor.close()
        conn.close()