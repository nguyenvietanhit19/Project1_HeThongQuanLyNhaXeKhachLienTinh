# Hệ thống Quản lý Nhà xe Khách Liên Tỉnh

Đồ án BTL — hệ thống quản lý vận hành cho 1 doanh nghiệp xe khách liên tỉnh duy nhất (kiểu Phương Trang/FUTA, Hà Sơn): quản lý tuyến, chuyến, đặt vé online, bán vé tại quầy, gửi hàng, vận hành đội xe, xử lý sự cố và hoàn tiền.

## Tài liệu — đọc trước khi code

1. [`NGHIEP_VU.md`](./NGHIEP_VU.md) — nghiệp vụ đầy đủ. Mục 11 (ma trận use case) + mục 12 (đặc tả use case) là **nguồn duy nhất** cho use case, mọi thay đổi phải khớp theo đây.
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — chiến lược kỹ thuật, công nghệ, cấu trúc thư mục.
3. [`DATABASE.md`](./DATABASE.md) — thiết kế schema PostgreSQL chi tiết.
4. [`UML_DIAGRAMS.md`](./UML_DIAGRAMS.md) — sơ đồ use case theo từng tác nhân + activity diagram (PlantUML), viết bằng văn nói thường.
5. [`USE_CASE.puml`](./USE_CASE.puml) — sơ đồ use case toàn hệ thống.
6. [`CI_CD_VA_DEPLOY.md`](./CI_CD_VA_DEPLOY.md) — giải thích CI/CD và quy trình deploy, dành cho ai chưa từng làm.
7. [`CONTRIBUTING.md`](./CONTRIBUTING.md) — cách nhóm 5 người chia việc code (theo domain, không theo role/tầng), quy ước Git/migration/PR.
8. [`HUONG_DAN_LAM_VIEC.md`](./HUONG_DAN_LAM_VIEC.md) — hướng dẫn thao tác cụ thể (Git/PR/Docker/migration/xem database), dành cho người mới chưa quen quy trình.
9. [`THIET_KE_UI.md`](./THIET_KE_UI.md) — phong cách thiết kế UI tham khảo (màu sắc, bo góc, đổ bóng) + [`frontend/shared/design-tokens.css`](./frontend/shared/design-tokens.css) chứa biến/class dùng chung cho mọi trang.

## Công nghệ

FastAPI + raw SQL (`psycopg2`) + PostgreSQL (Supabase) + Docker + WebSocket, kiến trúc 3 lớp **Route → Service → Repository**. Chi tiết xem `ARCHITECTURE.md`.

## Bắt đầu (dev local)

```bash
git clone https://github.com/nguyenvietanhit19/Project1_HeThongQuanLyNhaXeKhachLienTinh.git
cd Project1_HeThongQuanLyNhaXeKhachLienTinh
cp backend/.env.example backend/.env   # điền giá trị thật, xin trưởng nhóm — không tự bịa
docker-compose up
docker-compose exec backend sh -c 'yoyo apply --database "$DATABASE_URL" ./migrations'   # chạy migration lần đầu — cú pháp này chạy đúng trên cả PowerShell lẫn Bash
```

Backend chạy tại `http://localhost:8000/docs` (Swagger UI tự sinh — dùng để test API thay vì Postman thủ công).

Frontend chạy độc lập — mở trực tiếp file HTML hoặc dùng 1 static server nhẹ, trỏ config về `http://localhost:8000`. Có 2 thư mục riêng: `frontend/khach-hang/` và `frontend/nhan-vien/`.

## Cấu trúc thư mục

Xem đầy đủ lý do từng thư mục ở `ARCHITECTURE.md` mục 3. Tóm tắt:

```
backend/app/
  ├── schemas/        # Pydantic models (request/response)
  ├── repositories/   # raw SQL, 1 file = 1 bảng/entity
  ├── services/       # quy tắc nghiệp vụ
  ├── routes/         # APIRouter, mỏng, chỉ gọi service
  ├── jobs/           # tác vụ chạy định kỳ (APScheduler)
  ├── middleware/      # xác thực JWT, phân quyền
  └── utils/
backend/migrations/    # file .sql đánh số, chạy qua yoyo-migrations
backend/tests/{unit,integration}/
frontend/khach-hang/   # giao diện khách hàng
frontend/nhan-vien/    # giao diện phụ xe/quầy vé/gửi hàng/điều độ/kế toán/quản lý
```

## Quy ước đặt tên

`snake_case` không dấu cho tên bảng/cột/biến Python (dữ liệu bên trong vẫn lưu tiếng Việt có dấu). Mỗi Repository/Service đặt tên theo entity số ít (`VeRepository`, không phải `VesRepository`).

## Việc còn tồn đọng

- [ ] Vẽ lại ERD (`ERD.md`/`ERD.dbml`) theo đúng `DATABASE.md` hiện tại — **chưa đưa vào repo này** vì bản cũ mô tả sai domain (Báo cáo sự cố giao thông), sẽ làm lại từ đầu.
- [ ] Quyết định cơ chế chạy migration khi deploy production (chạy lúc container khởi động, hay 1 bước riêng trong `.github/workflows/deploy.yml`) — xem `CI_CD_VA_DEPLOY.md` + `ARCHITECTURE.md` mục 8. Repo này mới có `backend-ci.yml` (chạy test), **chưa có `deploy.yml`**.
- [ ] Toàn bộ `backend/app/{schemas,repositories,services,routes,jobs,middleware,utils}/` mới có khung thư mục (`__init__.py` rỗng) — chưa có code nghiệp vụ, viết dần theo `NGHIEP_VU.md`.
