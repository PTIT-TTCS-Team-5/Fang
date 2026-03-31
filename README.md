# Fang - AI Core (miCareer)

AI Layer cho hệ thống miCareer, xây dựng dựa trên kiến trúc RAG

## API Contract
- **POST** `/v1/ingestion/jobs`
  - Request JSON: `{ "jobAppId": 123, "cvSnapUrl": "https://..." }`
  - Response 202: `{ "indexJobId": 1, "status": "QUEUED" }`
  - Error: 400 (validation), 422 (URL fetch failed), 500 (unexpected)
- **GET** `/v1/ingestion/jobs/{indexJobId}`
  - Response 200: `{ "status": "QUEUED|PROCESSING|SUCCESS|FAILED", "errorMsg": null }`
- **GET** `/healthz`
  - Response 200: `{ "ok": true }`

## Cài đặt
1. Tạo virtual environment: `python -m venv venv`
2. Kích hoạt venv: `source venv/bin/activate` (Linux/Mac) hoặc `venv\Scripts\activate` (Windows)
3. Cài đặt thư viện: `python -m pip install -r requirements.txt`
4. Chạy `python -m pre_commit autoupdate`
5. Cài đặt pre-commit: `python -m pre_commit install`

## Cấu hình
Copy `.env.example` thành `.env` và điền các thông tin kết nối DB.

## Migrate DB
Tạo cơ sở dữ liệu PostgreSQL và chạy script migration tại `migrations/001_initial_schema.sql`. Đảm bảo đã cài đặt extension `pgvector`.

## Chạy
```bash
uvicorn app.main:app --reload.
```

## Trick show all thay đổi
```bash
git add -N.
git diff
```
## Hướng dẫn Test nhanh
Hiện tại, module **CV Parser (Bóc tách CV bằng Gemini)** đã hoàn thiện. Có thể test độc lập module này mà chưa cần kết nối Database hay chạy Server FastAPI.

**Bước 1: Chuẩn bị môi trường**
1. Làm theo phần "Cài đặt" bên trên.
2. Copy file `.env.example` thành `.env`. Mở file `.env` và điền key thật vào biến `GOOGLE_API_KEY`. (Key này ae lấy free bằng Google AI studio rất dễ)

**Bước 2: Chạy script test Parser**
1. Đảm bảo trong thư mục gốc đã có một file PDF CV mẫu, đặt tên là `sample.pdf`.
2. Chạy lệnh sau trong terminal:
   ```bash
   python test_parser.py
3. Quan sát log trên màn hình console. Nếu hiện ra chữ "🎉 PARSE THÀNH CÔNG!" kèm raw text và khối JSON được format đẹp đẽ là hệ thống đã hoạt động đúng.
