-- 1. Bảng Master Product (Dữ liệu chung, chống trùng mã)
CREATE TABLE IF NOT EXISTS master_product_database (
    product_code VARCHAR(100) PRIMARY KEY,
    basic_information VARCHAR(255)
);

-- 2. Bảng Tenant cách ly (Tenant A và Tenant B)
CREATE TABLE IF NOT EXISTS tenant_a_data (
    product_code VARCHAR(100) PRIMARY KEY REFERENCES master_product_database(product_code),
    inventory_qty INT
);

CREATE TABLE IF NOT EXISTS tenant_b_data (
    product_code VARCHAR(100) PRIMARY KEY REFERENCES master_product_database(product_code),
    inventory_qty INT
);

-- 3. Bảng quản lý Worker & Checkpoints (Theo yêu cầu: "start from last checkpoints")
CREATE TABLE IF NOT EXISTS worker_status_registry (
    worker_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'stopped', -- 'running', 'deployed', 'configured'
    last_checkpoint TIMESTAMP
);

-- 4. Bảng Metrics hiệu năng (Throughput, Latency, Wrong records)[cite: 15]
CREATE TABLE IF NOT EXISTS system_performance_metrics (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50),
    latency_ms INT,
    throughput INT,
    wrong_records INT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);