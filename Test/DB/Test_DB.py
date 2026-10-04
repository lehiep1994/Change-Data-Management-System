import psycopg2

# Sử dụng chung cấu hình Database từ Backend của bạn[cite: 16]
DB_CONFIG = {
    "dbname": "cdms_db",
    "user": "postgres",
    "password": "root",  # Đổi lại mật khẩu pgAdmin của bạn nếu khác
    "host": "localhost",
    "port": "5432"
}

def test_db_connection():
    """Test 1: Kiểm tra Python có kết nối trực tiếp được với PostgreSQL hay không"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        assert conn is not None
        conn.close()
        print("✅ [DB Test] Kết nối PostgreSQL thành công!")
    except Exception as e:
        assert False, f"Kết nối Database thất bại: {e}"

def test_db_deduplication_master():
    """Test 2: Kiểm tra cơ chế chống trùng lặp trên Master Product Database[cite: 16]"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        test_code = "TEST_UNIQUE_CODE_123"
        
        # Thêm bản ghi lần 1 vào bảng master[cite: 16]
        cursor.execute("""
            INSERT INTO master_product_database (product_code, basic_information) 
            VALUES (%s, %s) 
            ON CONFLICT (product_code) DO NOTHING;
        """, (test_code, "Test Info Product"))
        
        # Thêm bản ghi lần 2 với cùng mã product_code (phải được bỏ qua nhờ ON CONFLICT)[cite: 16]
        cursor.execute("""
            INSERT INTO master_product_database (product_code, basic_information) 
            VALUES (%s, %s) 
            ON CONFLICT (product_code) DO NOTHING;
        """, (test_code, "Test Info Product Duplicate"))
        
        conn.commit()
        
        # Truy vấn kiểm tra xem trong bảng chỉ tồn tại đúng 1 dòng duy nhất cho mã này
        cursor.execute("SELECT count(*) FROM master_product_database WHERE product_code = %s;", (test_code,))
        count = cursor.fetchone()[0]
        assert count == 1
        print("✅ [DB Test] Cơ chế chống trùng lặp dữ liệu (Deduplication) hoạt động chính xác!")
    finally:
        cursor.close()
        conn.close()

def test_db_tenant_isolation():
    """Test 3: Kiểm tra xem dữ liệu của Tenant A và Tenant B có được lưu ở 2 bảng độc lập không[cite: 16]"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        # Truy vấn kiểm tra sự tồn tại của 2 bảng cách ly tenant[cite: 16]
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name IN ('tenant_a_data', 'tenant_b_data');
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "tenant_a_data" in tables
        assert "tenant_b_data" in tables
        print("✅ [DB Test] Dữ liệu các Tenant được phân tách vào các bảng độc lập thành công!")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("--- Đang chạy Test Suite cho Database ---")
    test_db_connection()
    test_db_deduplication_master()
    test_db_tenant_isolation()
    print("--- Tất cả các Database Tests đã vượt qua! ---")