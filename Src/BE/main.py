import time
import psycopg2
import os

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="CDMS Backend Services (Full Architecture)")

# Lấy cấu hình DB từ Docker Compose
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cdms_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root"), 
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432")
}

# ==========================================
# 1. DATA ACCESS LAYER & DEDUPLICATION (DAL)
# ==========================================
def save_with_deduplication(tenant_id: str, code: str, info: str, qty: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        # Master DB: Chống trùng lặp thông tin chung
        cursor.execute("""
            INSERT INTO master_product_database (product_code, basic_information)
            VALUES (%s, %s) ON CONFLICT (product_code) DO NOTHING;
        """, (code, info))

        # Tenant Table: Tách biệt dữ liệu Tenant
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
# 2. CONNECTORS & WORKERS
# ==========================================
class VietfulConnector:
    """Connector kết nối với Messaging System của Vietful theo cấu hình của Tenant"""
    def __init__(self, broker_url: str, topic_name: str):
        self.broker_url = broker_url
        self.topic_name = topic_name
        # (Mock) Giả lập việc subscribe vào hệ thống queue của Vietful
        print(f"Subscribed to Vietful Messaging at {self.broker_url}, Topic: {self.topic_name}")

    def consume_message(self, raw_data: dict):
        return raw_data

class ShopifyConnector:
    """Connector chủ động Query dữ liệu từ Shopify API"""
    def query_api(self, tenant_id: str):
        return [{"code": "SHP_101", "name": "Shopify Jacket", "qty": 40}]

# ==========================================
# 3. FASTAPI ENDPOINTS
# ==========================================
class WorkerControlReq(BaseModel):
    action: str 

class DataSourceReq(BaseModel):
    tenant_id: str
    source: str
    broker_url: str = None  # URL kết nối Messaging
    topic_name: str = None  # Topic/Queue riêng của Tenant

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
    if req.source.lower() == 'vietful':
        # (Mock) Khởi tạo Connector dựa trên cấu hình messaging riêng của Tenant
        connector = VietfulConnector(req.broker_url, req.topic_name)
        return {"status": "success", "message": f"Configured Vietful Messaging for {req.tenant_id} on topic '{req.topic_name}'"}
    
    return {"status": "success", "message": f"Configured data source: {req.source}"}

@app.post("/api/tenant/schedule")
def schedule_worker(req: ScheduleReq):
    return {"status": "success", "message": f"Worker scheduled with mode: {req.mode}"}

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

# --- Xử lý nguồn 1: Vietful (Push / Webhook endpoint cho Messaging System) ---
@app.post("/api/sync/vietful")
def vietful_push_sync(payload: VietfulPayload):
    start_time = time.time()
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        save_with_deduplication(payload.tenant_id, payload.item_code, payload.item_name, payload.quantity)
        
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