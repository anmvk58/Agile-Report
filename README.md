# DailyFlow — Agile Daily Report

Ứng dụng nội bộ quản lý Daily Report cho team 6–10 người. Thành viên cập nhật công việc theo User Story; Admin theo dõi tiến độ, blocker, người chưa báo cáo và tạo báo cáo tuần dạng snapshot.

## Chạy nhanh bằng Docker

Yêu cầu Docker Desktop và Docker Compose.

```bash
cp .env.example .env
# Sửa ADMIN_INITIAL_PASSWORD và JWT_SECRET_KEY trong .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Swagger API: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Migration và seed được chạy tự động khi backend khởi động. SQLite nằm trong named volume `agile_data`, vì vậy dữ liệu không mất khi container được tạo lại.

> Sau lần đăng nhập đầu tiên, Admin phải đổi mật khẩu mặc định tại trang **Đổi mật khẩu** (có thể mở trực tiếp `/password`). Không dùng mật khẩu mẫu trong môi trường thật.

## Tài khoản seed

| Vai trò | Username | Mật khẩu |
|---|---|---|
| Admin | `admin` | Giá trị `ADMIN_INITIAL_PASSWORD` trong `.env` |
| Member | `an.nguyen`, `binh.tran`, `chi.le`, `dung.pham`, `ha.vo`, `khanh.do` | `Member123!` |

Seed chỉ chạy khi bảng users chưa có dữ liệu. Hãy đổi toàn bộ mật khẩu mẫu khi triển khai thật.

## Chạy local

Backend yêu cầu Python 3.12+:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend yêu cầu Node.js 22+:

```bash
cd frontend
npm install
npm run dev
```

Vite chạy ở http://localhost:5173 và proxy `/api` đến backend port 8000.

## Biến môi trường

| Biến | Ý nghĩa |
|---|---|
| `ADMIN_INITIAL_PASSWORD` | Mật khẩu Admin chỉ dùng lúc seed |
| `JWT_SECRET_KEY` | Secret ký JWT; phải là chuỗi ngẫu nhiên dài ở production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Thời hạn access token, mặc định 480 phút |
| `DATABASE_URL` | SQLAlchemy URL; Docker dùng `sqlite:////data/agile_report.db` |
| `VITE_API_URL` | API base của frontend, mặc định `/api` |

## Migration và seed

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
python -m app.seed
```

Migration đầu tiên tạo đầy đủ foreign key, unique constraint và index. Các bảng quan trọng không có endpoint hard-delete ngoài Daily Report do Admin xác nhận.

## Kiểm thử và build

```bash
cd backend
python -m pytest -q

cd ../frontend
npm run typecheck
npm run build

cd ..
docker compose build
```

Backend test bao phủ login đúng/sai, tài khoản inactive, RBAC, Daily duy nhất theo ngày, validation blocker, ngày tương lai, quyền sửa báo cáo và snapshot báo cáo tuần.

## Backup và restore SQLite

Nên dừng ghi dữ liệu trước khi backup để có snapshot nhất quán.

```bash
docker compose stop backend
docker run --rm -v agilereport_agile_data:/data -v "$PWD/backup:/backup" alpine cp /data/agile_report.db /backup/agile_report.db
docker compose start backend
```

Restore:

```bash
docker compose stop backend
docker run --rm -v agilereport_agile_data:/data -v "$PWD/backup:/backup:ro" alpine cp /backup/agile_report.db /data/agile_report.db
docker compose start backend
```

Tên volume thực tế có thể khác theo tên thư mục/Compose project; kiểm tra bằng `docker volume ls`.

## Kiến trúc thư mục

```text
.
├── backend/
│   ├── alembic/versions/       # Database migrations
│   ├── app/
│   │   ├── api/                # REST routes
│   │   ├── core/               # Config, JWT, password, RBAC
│   │   ├── db/                 # Engine và session DI
│   │   ├── models/             # SQLAlchemy entities
│   │   ├── schemas/            # Pydantic request/response
│   │   ├── services/           # Daily rules và weekly aggregation
│   │   ├── main.py
│   │   └── seed.py
│   └── tests/
├── frontend/src/
│   ├── api/                    # Typed API client
│   ├── components/             # Layout và UI primitives
│   ├── pages/                  # Member/Admin screens
│   └── types/                  # TypeScript domain types
├── docker-compose.yml
└── .env.example
```

## Quyết định thiết kế và giả định

- Tất cả timestamp được tạo theo UTC; ngày nghiệp vụ hiện tại được tính với `Asia/Ho_Chi_Minh`.
- Access token được lưu ở localStorage cho MVP. Production nên chuyển sang short-lived token + HttpOnly refresh cookie nếu ứng dụng mở ra Internet.
- Member nhìn thấy và có thể log task vào mọi User Story chưa `CLOSED`; assignment chỉ dùng để theo dõi người phụ trách, không phải điều kiện truy cập. Lựa chọn “không thuộc User Story” luôn có sẵn.
- User Story `CLOSED` chỉ được giữ khi sửa item cũ đã liên kết, không xuất hiện cho task mới.
- Ngày làm việc được cấu hình trong Settings, mặc định Thứ Hai–Thứ Sáu. Chưa tích hợp lịch nghỉ lễ.
- Báo cáo tuần chỉ lấy Daily `SUBMITTED`, loại trùng chuỗi chính xác nhưng không dùng LLM. Khi finalized, JSON snapshot không được tái tổng hợp.
- Endpoint export PDF chưa có trong MVP để tránh thêm native dependency; Markdown và CSV đã hoàn chỉnh.
- API danh sách users, stories và weekly reports có pagination. Lịch sử Daily ưu tiên khoảng ngày của một user nên trả danh sách trực tiếp.

## API chính

Các endpoint bám theo đặc tả tại `/api/auth`, `/api/users`, `/api/user-stories`, `/api/daily-reports`, `/api/admin/daily-reports`, `/api/dashboard` và `/api/weekly-reports`. Ngoài ra có `/api/settings/workdays` để cấu hình ngày làm việc. Lỗi dùng status 401/403/404/409/422 với `detail` tiếng Việt; OpenAPI đầy đủ tại `/docs`.

## Gợi ý phiên bản tiếp theo

- Refresh token HttpOnly, audit log cho thao tác Admin và bắt buộc đổi mật khẩu lần đầu.
- Lịch nghỉ lễ, notification nhắc Daily và tích hợp SSO.
- Biểu đồ tiến độ theo snapshot hằng ngày, comment/mention trên blocker.
- Export PDF theo template thương hiệu và gửi báo cáo tự động.
- E2E test bằng Playwright và accessibility audit tự động.
