# Change-Data-Management-System (CDMS)

Hệ thống quản lý dữ liệu thay đổi (CDMS) hỗ trợ đồng bộ hóa dữ liệu từ các nguồn (Vietful Inventory Service và Shopify), cung cấp cơ chế chống trùng lặp dữ liệu, phân tách quyền truy cập theo từng tenant, cùng hệ thống quản lý vòng đời worker và đo lường hiệu năng telemetry.

---

## 🚀 Phương pháp Triển khai Hệ thống (Deployment Methods)

### 1) Triển khai thủ công:
* **Database (PostgreSQL):** 
  * Cài đặt và cấu hình cơ sở dữ liệu trên pgAdmin 4 với tên database là `cdms_db`.
  * Mở Query Tool và chạy tập lệnh SQL khởi tạo các bảng từ file `Database/CDMS.sql`.
* **Backend (FastAPI):** 
  ```bash
  cd Src/BE
  python -m venv venv
  venv\Scripts\Activate
  pip install fastapi uvicorn psycopg2-binary pydantic
  uvicorn main:app --reload --port 8000
* **Frontend:**
  ```bash
  cd Src/FE
  npm install
  node server.js
* **Testing FE:**
  Chỉnh lại nội dung trong file "package.json" với:
  *"test": "jest --rootDir ../.. --moduleDirectories Src/FE/node_modules Test/FE/fe.test.js*"
  để có thể tiến hành kiểm thử cho FE. 
  ```bash
  cd Test/FE
  npm test
* **Testing BE:**
  khởi tạo môi trường ảo *"venv"* và sau đó cài đặt những gói sau:
  *"pip install pytest httpx"*

   và dùng câu lệnh sau:
   *"pytest Test/BE/Test_BE.py -v"*
* **Testing DB:**
  Tương tự như với BE thì dùng câu lệnh sau:
   *"pytest Test/BE/Test_DB.py -v"*

### 2) Triển khai bằng docker:
   Tạo file *"docker-compose.yaml"*
   Chạy lệnh sau:
   ```bash
   docker-compose up --build