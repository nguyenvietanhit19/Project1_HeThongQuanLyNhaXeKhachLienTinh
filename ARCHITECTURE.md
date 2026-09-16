# Chiến lược kiến trúc — Hệ thống Quản lý Nhà xe Khách (bản viết lại)

Tài liệu này mô tả toàn bộ chiến lược kỹ thuật cho bản viết lại của dự án, để bất kỳ thành viên nào trong nhóm đọc cũng nắm được: dùng công nghệ gì, tổ chức thư mục ra sao, vì sao chọn như vậy, và cách chạy dự án ở máy local lẫn khi deploy thật. Đọc cùng `NGHIEP_VU.md` (nghiệp vụ chi tiết) — file này chỉ nói về **kỹ thuật**, không lặp lại nghiệp vụ.

> Đổi đề tài từ "Báo cáo sự cố giao thông cộng đồng" sang **quản lý nhà xe khách liên tỉnh** (xem `NGHIEP_VU.md`). Bản v1 (thư mục `GiaoThongAnToan_API/`) dùng Flask + SQL Server + raw SQL không tách lớp — bản viết lại đổi framework, đổi DB, tổ chức lại kiến trúc theo hướng tách lớp rõ ràng, nhưng **giữ nguyên gần như 100% cơ chế đăng ký/đăng nhập bằng email + OTP** của bản v1 (`routes/auth.py` + `routes/quen_mat_khau.py`) vì đã chạy ổn định — xem `NGHIEP_VU.md` mục 2.1.

---

## 1. Công nghệ sử dụng

| Thành phần | Công nghệ | Lý do chọn |
|---|---|---|
| Backend framework | **FastAPI** | Validate input/output có sẵn (Pydantic), tự sinh API docs (Swagger), WebSocket có sẵn trong core — không cần vá thêm như Flask-SocketIO |
| Truy vấn database | **Raw SQL** qua `psycopg2` (hoặc `asyncpg` cho phần async) | Đội đã quen SQL, không tốn thời gian học ORM giữa lúc viết lại toàn bộ; SQL injection không phải rủi ro nếu luôn dùng parameterized query (`%s`, không nối chuỗi) — **đặc biệt quan trọng với cơ chế giữ ghế (mục 5)**, vốn cần transaction + khóa dòng tường minh mà ORM thường che giấu |
| Database | **PostgreSQL** (host: Supabase free tier) | Free tier tốt, driver thuần Python (không cần cài ODBC driver như SQL Server) → dễ Docker hóa; hỗ trợ `SELECT ... FOR UPDATE` cần cho cơ chế chống trùng ghế |
| Gửi email (OTP đăng ký/quên mật khẩu) | **Gmail SMTP** (giữ nguyên từ bản v1, `email_service.py`) | Đã có sẵn cơ chế chạy ổn định, miễn phí, không cần đổi gì — xem `NGHIEP_VU.md` mục 2.1 |
| Thanh toán online | **VNPay** (môi trường sandbox cho demo/BTL) | Có sẵn merchant sandbox miễn phí, không cần mã số thuế/doanh nghiệp thật, luồng kỹ thuật giống hệt production (chỉ khác `vnp_TmnCode`/`vnp_HashSecret`/domain) — dùng chung cho cả thanh toán online lẫn quét QR tại quầy (`NGHIEP_VU.md` mục 6) |
| Biên nhận/vé PDF | Sinh **theo yêu cầu** từ dữ liệu `ve`/`don_hang` trong DB (VD ReportLab/WeasyPrint), **không lưu file** | Không phải hóa đơn điện tử hợp lệ thuế (ngoài phạm vi BTL — đòi hỏi MST doanh nghiệp + tích hợp nhà cung cấp hóa đơn điện tử được công nhận), chỉ là biên nhận nội bộ; sinh lại mỗi lần tải tránh phát sinh thêm dịch vụ lưu file |
| File/ảnh | **Không dùng** — bỏ Cloudinary so với bản v1 | Domain mới không có nhu cầu khách/nhân viên upload ảnh (vé cứng và biên nhận gửi hàng đều in trực tiếp tại quầy, không phải file lưu trữ) |
| Real-time | **WebSocket built-in của FastAPI** | Báo khách hàng khi chuyến đổi giờ/đổi xe/gặp sự cố, báo điều độ viên khi phụ xe báo sự cố — không cần polling |
| Tác vụ định kỳ (giữ ghế hết hạn, no-show) | **APScheduler** chạy trong tiến trình backend | Xem mục 5 — cần 1 nơi quét định kỳ các `ve`/`don_hang` quá hạn để chuyển trạng thái, không thể chỉ dựa vào lazy-check như OTP ở bản v1 |
| Containerize | **Docker** (backend), docker-compose cho local dev | Đồng bộ môi trường giữa các thành viên, tránh "chạy được ở máy tôi" |
| Deploy backend | **Render** hoặc **Fly.io** (free tier) | Cần host giữ kết nối lâu dài cho WebSocket — Vercel (serverless) không phù hợp cho việc này |
| Deploy frontend | **Vercel** (hoặc Netlify/Cloudflare Pages) | Frontend là HTML/CSS/JS tĩnh (khách hàng) + giao diện di động riêng cho phụ xe (mục `NGHIEP_VU.md` 8.2), tách riêng khỏi backend, deploy free, có CDN |
| Migration DB | File `.sql` đánh số + `yoyo-migrations` (hoặc script tự viết) | Không dùng Alembic vì không có ORM model để tự sinh diff |

---

## 2. Nguyên tắc kiến trúc: 3 lớp (Layering)

Mọi tính năng backend đi qua đúng 3 lớp theo một chiều duy nhất:

```
Route  →  Service  →  Repository  →  PostgreSQL
```

| Lớp | Biết gì | Không được biết gì | Ví dụ |
|---|---|---|---|
| **Route** | HTTP request/response, gọi đúng Service cần dùng | Không viết SQL, không tự quyết định quy tắc nghiệp vụ | `POST /ve/giu-cho` nhận danh sách ghế, gọi `dat_ve_service.giu_cho(...)` |
| **Service** | Quy tắc nghiệp vụ (khi nào làm gì, điều kiện gì thì chặn), điều phối nhiều Repository, quản lý transaction | Không biết gì về HTTP (không có `Request`, không trả JSON response), không tự viết SQL | "Ghế hợp lệ khi 2 khoảng `[thu_tu(đón), thu_tu(trả))` không giao nhau" (`NGHIEP_VU.md` mục 6) nằm ở đây |
| **Repository** | Cách đọc/ghi **một bảng cụ thể** bằng SQL | Không biết quy tắc nghiệp vụ, không biết gì về HTTP | `VeRepository.khoa_va_kiem_tra_trung_ghe(chuyen_id, so_ghe)` chỉ chạy đúng câu `SELECT ... FOR UPDATE` |

**Quy tắc chia Repository: theo bảng dữ liệu, không theo route file.** Nhiều route/service khác nhau dùng chung một Repository nếu chúng đụng cùng bảng — ví dụ `NguoiDungRepository` dùng lại bởi cả luồng đăng nhập, quên mật khẩu, và quản lý tài khoản của `quan_ly`.

**Việc gọi dịch vụ ngoài (SMTP) không thuộc Repository** (Repository chỉ lo DB) — đặt trong `services/` dưới dạng service hạ tầng riêng (`email_service.py`), Service nghiệp vụ gọi tới khi cần.

---

## 3. Cấu trúc thư mục

```
project-root/
├── backend/
│   ├── app/
│   │   ├── main.py                        # khởi tạo FastAPI app, đăng ký router, khởi động scheduler
│   │   ├── config.py                      # đọc biến môi trường theo từng env (dev/prod)
│   │   ├── db.py                          # connection pool tới Postgres (psycopg2/asyncpg)
│   │   │
│   │   ├── schemas/                       # Pydantic models — định nghĩa hình dạng request/response
│   │   │   ├── nguoi_dung_schema.py
│   │   │   ├── ve_schema.py
│   │   │   ├── chuyen_xe_schema.py
│   │   │   ├── don_hang_schema.py
│   │   │   └── ...
│   │   │
│   │   ├── repositories/                  # raw SQL, 1 file = 1 bảng/entity dữ liệu
│   │   │   ├── nguoi_dung_repository.py       # tài khoản đăng nhập được: khách hàng + cán bộ (NGHIEP_VU mục 2)
│   │   │   ├── nhan_vien_van_hanh_repository.py  # hồ sơ tài xế/phụ xe + xe_nhan_su (mục 3.2)
│   │   │   ├── khu_vuc_repository.py
│   │   │   ├── diem_don_tra_repository.py
│   │   │   ├── tuyen_repository.py            # tuyen + tuyen_diem_don_tra + nhom_tuyen
│   │   │   ├── gia_ve_repository.py
│   │   │   ├── xe_repository.py
│   │   │   ├── chuyen_xe_repository.py
│   │   │   ├── ve_repository.py               # trung tâm: khóa ghế, kiểm tra overlap (mục 6)
│   │   │   └── don_hang_repository.py         # gửi hàng (mục 10)
│   │   │
│   │   ├── services/                      # quy tắc nghiệp vụ + service hạ tầng
│   │   │   ├── mat_khau_service.py            # đăng ký/đăng nhập/quên mật khẩu — kế thừa bản v1
│   │   │   ├── tai_khoan_can_bo_service.py    # tạo/khóa/mở khóa tài khoản cán bộ (UC-36/37/38) — kiểm tra quyền actor vs vai trò mục tiêu, chặn khóa quan_ly gốc (mục 8.9 NGHIEP_VU.md)
│   │   │   ├── email_service.py               # gửi mail OTP (SMTP) — hạ tầng, không đổi từ bản v1
│   │   │   ├── tim_kiem_chuyen_service.py     # tìm theo điểm đi/đến (mục 3.4 bước 1-2)
│   │   │   ├── dat_ve_service.py              # giữ ghế, chống trùng ghế, đặt cọc (mục 3.4, 6)
│   │   │   ├── thanh_toan_service.py          # thanh toán ngay / tại quầy
│   │   │   ├── hoan_tien_service.py            # tạo/quản lý hàng đợi lich_su_hoan_tien; gọi API hoàn tiền VNPay khi có mã giao dịch (mục 7 NGHIEP_VU.md)
│   │   │   ├── lich_chay_dinh_ky_service.py    # CRUD lich_chay_dinh_ky, sinh chuyen_xe theo cửa sổ N ngày (mục 3.5 NGHIEP_VU.md, UC-18) — gọi bởi cả route quan_ly.py lẫn job định kỳ
│   │   │   ├── chuyen_xe_service.py           # vòng đời chuyến, gán xe (UC-44), đổi xe, sự cố (mục 3.3, 4)
│   │   │   ├── xe_nhan_su_service.py          # biên chế cố định/tạm thời (mục 3.2)
│   │   │   ├── gui_hang_service.py            # tạo đơn theo tuyến, phụ xe chọn xếp lên chuyến cụ thể (mục 10.2) — không còn tính sức chứa tự động
│   │   │   └── websocket_manager.py           # broadcast sự kiện real-time
│   │   │
│   │   ├── routes/                        # APIRouter của FastAPI, mỏng — chỉ gọi service
│   │   │   ├── auth.py                        # đăng ký/đăng nhập/quên mật khẩu (khách hàng)
│   │   │   ├── chuyen.py                      # tìm kiếm chuyến công khai
│   │   │   ├── ve.py                          # giữ ghế, chọn điểm đón/trả, thanh toán, lịch sử vé
│   │   │   ├── thanh_toan_callback.py         # webhook nhận kết quả từ cổng thanh toán (mục 5) — không phải action của người dùng, không cần JWT thường mà xác thực bằng chữ ký/secret riêng của cổng
│   │   │   ├── quay_ve.py                     # nhân viên quầy vé: bán vé, in vé cứng (không xử lý hoàn tiền)
│   │   │   ├── gui_hang.py                    # nhân viên gửi hàng: tạo đơn, giao hàng
│   │   │   ├── phu_xe.py                      # giao diện di động: soát vé, xác nhận trạng thái chuyến
│   │   │   ├── dieu_do.py                     # điều độ viên: gán xe cho chuyến (UC-44), đổi xe, xử lý sự cố/nhân sự
│   │   │   ├── ke_toan.py                     # kế toán: danh sách hoàn tiền chờ xử lý, đánh dấu đã chuyển khoản thủ công (mục 8.8 NGHIEP_VU.md) — toàn hệ thống
│   │   │   ├── tai_khoan_can_bo.py            # tạo/khóa/mở khóa tài khoản cán bộ (UC-36/37/38) — dùng chung cho quan_ly và quan_ly_nhan_su (mục 8.9 NGHIEP_VU.md), Service phân quyền theo vai_tro + la_tai_khoan_goc của actor lẫn tài khoản mục tiêu
│   │   │   ├── quan_ly.py                     # quản lý: danh mục, lịch chạy định kỳ (UC-18), cấu hình, thống kê
│   │   │   └── websocket.py                   # điểm kết nối real-time
│   │   │
│   │   ├── jobs/                          # tác vụ chạy định kỳ (không phải request-response)
│   │   │   ├── quet_het_han.py                # quét ve quá hạn → het_han/khong_den; chuyen_xe chưa gán xe khi tới giờ chạy → dang_hoan (UC-45); don_hang cho_lay quá 7/14 ngày → cảnh báo/hàng tồn (UC-46, mục 5)
│   │   │   └── sinh_chuyen_dinh_ky.py          # sinh chuyen_xe từ lich_chay_dinh_ky theo cửa sổ N ngày (mục 3.5 NGHIEP_VU.md)
│   │   │
│   │   ├── middleware/
│   │   │   └── auth_middleware.py         # xác thực JWT, phân quyền theo vai_tro (kể cả kiểm tra la_tai_khoan_goc khi thao tác lên tài khoản quan_ly/quan_ly_nhan_su, DATABASE.md mục 1.1)
│   │   │
│   │   └── utils/
│   │       └── db_helpers.py              # helper dùng chung (map row → dict...)
│   │
│   ├── migrations/                        # file .sql đánh số thứ tự, version hóa schema
│   │   ├── 0001_init_schema.sql
│   │   ├── 0002_xxx.sql
│   │   └── ...
│   │
│   ├── tests/
│   │   ├── unit/                          # test Service, giả lập (mock) Repository — không cần DB thật
│   │   └── integration/                   # test Repository thật, chạy trên Postgres (docker)
│   │
│   ├── .env.example                       # mẫu biến môi trường, KHÔNG chứa giá trị thật
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
│
├── frontend/                              # HTML/CSS/JS tĩnh — 2 giao diện tách biệt
│   ├── khach-hang/                        # tìm chuyến, đặt vé, thanh toán, lịch sử vé
│   └── nhan-vien/                         # phụ xe (di động) + quầy vé + gửi hàng + điều độ + quản lý
│
├── docker-compose.yml                     # dev local: backend + Postgres
├── .github/
│   └── workflows/
│       ├── backend-ci.yml                 # chạy test + lint mỗi khi có PR
│       └── deploy.yml                     # tự deploy khi merge vào main
│
├── docs/
│   └── ERD.png                            # sơ đồ quan hệ các bảng
│
├── .gitignore
├── NGHIEP_VU.md                           # nghiệp vụ chi tiết — đọc cùng file này
└── ARCHITECTURE.md                        # chính là file này
```

### Giải thích lý do từng thư mục tồn tại

- **`schemas/`** — nơi khai báo "request này cần field gì, kiểu gì, bắt buộc hay không" bằng Pydantic. FastAPI tự đọc các model này để validate và sinh docs.
- **`repositories/`** — nơi duy nhất được phép viết câu SQL. Nếu sau này cần đổi DB hoặc tối ưu 1 câu query, chỉ cần sửa đúng 1 file ở đây, không đụng gì tới `services/` hay `routes/`. `ve_repository.py` là file quan trọng nhất hệ thống — chứa câu `SELECT ... FOR UPDATE` cho cơ chế chống trùng ghế.
- **`services/`** — nơi chứa "luật chơi" của hệ thống. Đọc thư mục này là hiểu được toàn bộ nghiệp vụ của app mà không cần biết SQL hay HTTP là gì. `dat_ve_service.py` là service phức tạp nhất, đối chiếu trực tiếp với `NGHIEP_VU.md` mục 3.4 + 6.
- **`routes/`** — chỉ là lớp giao tiếp HTTP, cực mỏng, hầu như chỉ có 3-5 dòng mỗi endpoint. Tách riêng `phu_xe.py` khỏi `quay_ve.py`/`dieu_do.py` vì phụ xe dùng giao diện di động riêng (`NGHIEP_VU.md` mục 8.2), không phải dashboard desktop như các vai trò cán bộ khác.
- **`jobs/`** — khác hẳn `routes/`: không được HTTP request gọi tới, mà chạy tự động theo lịch (APScheduler). Cần vì `NGHIEP_VU.md` mục 5/9 yêu cầu **ghi nhận vĩnh viễn** trạng thái `het_han`/`khong_den` (dùng để đếm vi phạm no-show) — không thể chỉ tính toán "ảo" mỗi lần có người hỏi, phải có thời điểm thực sự ghi vào DB.
- **`migrations/`** — lịch sử thay đổi cấu trúc database, thay cho việc chỉnh tay trực tiếp trên Postgres.
- **`tests/unit/` vs `tests/integration/`** — unit test kiểm tra logic nghiệp vụ (Service) bằng cách giả lập Repository, chạy cực nhanh, không cần DB. Integration test kiểm tra Repository có chạy đúng với Postgres thật hay không — **đặc biệt quan trọng cho `ve_repository.py`**, vì logic khóa dòng/overlap chỉ có thể kiểm chứng đúng trên Postgres thật, không mock được.
- **`frontend/`** tách khỏi `backend/` hoàn toàn, và tách làm 2 thư mục con vì 2 nhóm người dùng có nhu cầu giao diện khác hẳn nhau (khách hàng dùng trình duyệt thường; phụ xe dùng điện thoại di động, thao tác nhanh trên danh sách khách lên/xuống từng điểm — không quét mã gì cả, chỉ cần màn hình cảm ứng bình thường, xem `NGHIEP_VU.md` mục 8.2).

---

## 4. Chiến lược Database & Migration

- Mỗi thay đổi cấu trúc DB (tạo bảng, thêm cột, thêm index) viết thành 1 file `.sql` trong `migrations/`, đặt tên theo thứ tự: `0001_init_schema.sql`, `0002_them_cot_xxx.sql`...
- Dùng thư viện `yoyo-migrations` (nhẹ, hoạt động trực tiếp với raw SQL, không cần ORM) để chạy migration tự động và track file nào đã chạy.
- **Tuyệt đối không sửa trực tiếp trên Postgres production** mà không ghi lại thành file migration.
- Không trộn lẫn các câu query thử/debug vào chung file với migration — migration chỉ chứa DDL (CREATE/ALTER TABLE) và seed data cần thiết (VD tài khoản `quan_ly` gốc, danh mục `loai_hang` mặc định).
- **Index bắt buộc ngay từ migration đầu tiên**: `ve(chuyen_id, so_ghe)` — bị `SELECT ... FOR UPDATE` quét thường xuyên (`NGHIEP_VU.md` mục 6), thiếu index sẽ khóa toàn bảng thay vì đúng vài dòng. `don_hang` không còn cơ chế khóa dòng tương tự (đã bỏ chống quá tải tự động, `NGHIEP_VU.md` mục 10.2) — chỉ cần index thường `don_hang(tuyen_id) WHERE chuyen_id IS NULL` (`DATABASE.md` mục 5.2).

---

## 5. Chiến lược xử lý "hết hạn" — giữ ghế & no-show

Đây là mảng kỹ thuật mới so với bản v1 (bản v1 chỉ có OTP hết hạn, kiểm tra lazy lúc xác thực là đủ). Domain nhà xe có nhiều mốc thời gian cần **tự chuyển trạng thái dù không ai gọi API** (`NGHIEP_VU.md` mục 5, 8.2, 9):

| Việc cần làm | Khi nào | Cơ chế |
|---|---|---|
| `giu_cho` → `da_thanh_toan` (thanh toán ngay) | VNPay báo giao dịch thành công | **Webhook/IPN**: VNPay gọi ngược 1 endpoint riêng (`POST /thanh-toan/callback`) kèm chữ ký `vnp_SecureHash`, ngay khi có kết quả — xử lý **tức thời**, không đợi job định kỳ. Đây là đường đi chính, nhanh hơn hẳn lazy-check/job. Dùng chung đúng cơ chế này cho cả thanh toán online (khách tự redirect) lẫn QR hiện tại quầy (nhân viên tạo hộ giao dịch) |
| `giu_cho` → `het_han` (thanh toán ngay) | Quá 5 phút kể từ lúc khách tới màn thanh toán **mà không có webhook nào báo về** | **Lazy-check** (mọi truy vấn "ghế còn trống"/"trạng thái vé" so `now() > han_giu_cho_den` ngay trong câu SQL) **+ job định kỳ** (mục dưới) làm lưới an toàn — webhook là đường đi chính, 2 cơ chế này chỉ xử lý trường hợp khách bỏ dở không có tín hiệu gì (đóng tab, mất mạng) |
| `giu_cho` → `khong_den` (thanh toán tại quầy, `han_giu_cho_den IS NULL`) | Đến giờ khởi hành tại điểm đón mà khách chưa ra quầy trả tiền — **không có `het_han` cho trường hợp này** (`NGHIEP_VU.md` mục 3.4/5/6, không còn mốc chốt danh sách) | **Bắt buộc job định kỳ** — cần ghi vĩnh viễn để đếm vi phạm no-show (mục 9), lazy-check không tự ghi log vi phạm |
| `da_thanh_toan` → `khong_den` | Đến giờ khởi hành tại điểm đón mà chưa `da_len_xe` | **Bắt buộc job định kỳ**, không thể lazy-check thuần túy — đây là trạng thái cần **ghi vĩnh viễn** để đếm vi phạm (mục 9), không phải chỉ hiển thị tạm thời |
| Cảnh báo `quan_ly` khi chuyến `dang_hoan` quá lâu | Chuyến `chuyen_xe.dang_hoan = true` (`NGHIEP_VU.md` mục 3.3) chưa tìm được xe thay thế quá ngưỡng cấu hình (mặc định 6 tiếng) | **Job định kỳ** — chỉ gửi thông báo/nhắc `quan_ly` hỗ trợ tìm thêm nguồn xe, **không** tự động đổi trạng thái hay hủy chuyến gì cả (chuyến không bao giờ bị hủy vì lý do này) |
| Tự động hoàn 100% cho vé khi `gap_su_co` do lỗi nhà xe kéo dài ≥3 tiếng (UC-43) | Chuyến `gap_su_co` với `loai_su_co = 'loi_nha_xe'` chưa quay lại `dang_chay` sau ngưỡng cấu hình (mặc định 3 tiếng kể từ lúc báo sự cố) | **Job định kỳ** — chỉ tạo `lich_su_hoan_tien` cho các vé `da_thanh_toan` chưa có dòng nào (tránh hoàn trùng), **không đổi `ve.trang_thai`** — vé vẫn tiếp tục được phục vụ bình thường, chỉ khác là miễn phí |
| Cảnh báo `dieu_do_vien` khi chuyến sắp chạy mà chưa gán xe (UC-44) | Chuyến `chua_khoi_hanh` có `xe_id IS NULL` còn ≤ ngưỡng cấu hình (mặc định 48 tiếng) tới `gio_khoi_hanh` (`NGHIEP_VU.md` mục 3.5) | **Job định kỳ** — chỉ gửi thông báo/nhắc, **không** tự động gán xe hay đổi trạng thái gì cả |
| Tự động chuyển "đang hoãn" khi tới giờ chạy mà chưa gán được xe (UC-45) | Chuyến `chua_khoi_hanh` có `xe_id IS NULL` và `gio_khoi_hanh <= now()` (`NGHIEP_VU.md` mục 3.3) | **Job định kỳ** — bật `dang_hoan = true`, dời `gio_khoi_hanh` tạm thời, báo khách qua WebSocket. Dùng chung đúng cơ chế "đang hoãn" của UC-20 (kể cả cảnh báo 6 tiếng, quyền hủy nhận hoàn UC-41) — chỉ khác lúc điều độ viên tìm được xe thì gán thẳng `xe_id`, không qua `xe_thuc_te_id` |
| Cảnh báo (7 ngày) rồi chuyển "hàng tồn" (14 ngày) khi hàng chờ quá lâu tại điểm nhận (UC-46) | `don_hang.trang_thai = 'cho_lay'` đã đủ 7 hoặc 14 ngày kể từ `thoi_gian_den_diem_nhan` (`NGHIEP_VU.md` mục 10.3.1) | **Job định kỳ** — mốc 7 ngày chỉ bật `co_canh_bao_cho_lau = true` (nhắc nhân viên gửi hàng xử lý, UC-25); mốc 14 ngày chuyển `trang_thai = 'qua_han_luu_kho'`. Cả 2 mốc đều **không tự hủy/thanh lý** gì cả, chỉ nhắc con người xử lý |

- **Vì sao không dùng lazy-check cho tất cả**: lazy-check chỉ hoạt động nếu có người/hệ thống chủ động hỏi lại đúng lúc. `khong_den` cần chính xác 1 lần ghi nhận tại đúng thời điểm chốt (dùng để cộng dồn vi phạm) — nếu không ai truy vấn đúng lúc đó, sự kiện "trễ" sẽ bị bỏ sót.
- **Webhook không thay thế được job/lazy-check hoàn toàn**: cổng thanh toán có thể không gọi được (mất mạng phía khách, khách đóng tab giữa chừng) — luôn cần 1 "lưới an toàn" cuối cùng để không giữ ghế vô thời hạn.
- **`jobs/quet_het_han.py`** chạy bằng APScheduler ngay trong tiến trình FastAPI (không cần service riêng, không cần Celery/Redis — quy mô BTL không cần hàng đợi phức tạp): mỗi 1 phút, quét `ve` có `trang_thai IN (giu_cho, da_thanh_toan)` và mốc thời gian tương ứng đã qua (`han_giu_cho_den` cho "thanh toán ngay"; giờ khởi hành tại điểm đón cho no-show, áp dụng cả `giu_cho` "tại quầy" lẫn `da_thanh_toan`) → cập nhật `het_han`/`khong_den`, ghi vi phạm no-show nếu cần, gọi `websocket_manager` báo khách hàng nếu vé bị `het_han` do lỗi hệ thống (không phải hết hạn thường).
- Chu kỳ quét 1 phút là đủ chính xác cho cả 2 mốc thời gian (5 phút của "thanh toán ngay" và giờ khởi hành cho no-show) — không cần quét nhanh hơn, vì trường hợp cần phản hồi tức thời (thanh toán thành công) đã có webhook lo, job chỉ là lưới an toàn.

---

## 6. Chiến lược Real-time

Dùng WebSocket có sẵn trong FastAPI, không polling:

- Khách hàng mở kết nối WebSocket tới `/ws` kèm token xác thực khi đang xem lịch sử vé/theo dõi chuyến sắp đi.
- Phụ xe (giao diện di động) mở kết nối riêng để nhận cập nhật khi điều độ viên đổi xe/hủy chuyến sự cố.
- Khi 1 Service hoàn tất hành động cần thông báo, gọi tới `websocket_manager` để **broadcast** tới đúng client liên quan:
  - Đổi xe trước giờ khởi hành / đổi ghế (`NGHIEP_VU.md` mục 3.3) → báo khách có vé trên chuyến đó.
  - Chuyến chuyển `gap_su_co` → báo điều độ viên phụ trách điểm xuất phát ngay lập tức.
  - Phụ xe xác nhận đến từng điểm trung gian → cập nhật ETA cho khách đang chờ đón ở điểm phía sau (`NGHIEP_VU.md` mục 8.2 điểm 5).
- Route `routes/websocket.py` chỉ lo việc nhận/giữ kết nối, xác thực token lúc connect — không chứa nghiệp vụ.

---

## 7. Docker

**`backend/Dockerfile`** — ý chính:
- Base image `python:3.x-slim`.
- Copy `requirements.txt` và cài dependency **trước** khi copy code — tận dụng cache của Docker.
- Dùng `psycopg2-binary` (không cần compiler trong image).
- Chạy bằng **Uvicorn**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

**`.dockerignore`** — loại `__pycache__/`, `.git/`, `venv/`, `.env*` ra khỏi image.

**`docker-compose.yml`** — dựng backend + Postgres local giống hệt production:
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db]
    volumes: ["./backend:/app"]
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: nha_xe
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: ["pgdata:/var/lib/postgresql/data"]
    ports: ["5432:5432"]
volumes:
  pgdata:
```
Thành viên mới chỉ cần `docker-compose up` là có đủ backend + database chạy local, không cần cài Postgres tay trên máy.

**Frontend không cần Docker** — Vercel build/serve trực tiếp từ source.

---

## 8. Chiến lược Deploy Production (Free)

| Thành phần | Nơi deploy | Lưu ý |
|---|---|---|
| Frontend (khách hàng + nhân viên) | Vercel | Deploy tự động mỗi khi push nhánh `main`, có CDN sẵn |
| Backend | Render (Free Web Service) hoặc Fly.io | Deploy trực tiếp từ Dockerfile. Render free **ngủ sau ~15 phút không có traffic** — job định kỳ (mục 5) sẽ không chạy trong lúc ngủ, cần biết trước khi demo/bảo vệ đồ án |
| Database | Supabase (Postgres free tier) | Connection string đưa vào biến môi trường, không hardcode |
| Migration khi deploy | Chạy `yoyo apply` như một bước trong CI/CD trước khi khởi động backend mới | Đảm bảo Postgres production luôn khớp với migration mới nhất trong git |

Biến môi trường (JWT secret, DB connection string, mail password) cấu hình trực tiếp trên dashboard của Render/Vercel/Supabase — **không commit vào git dưới bất kỳ hình thức nào**, kể cả file tên lạ như `.env.py` (bài học từ bản v1: file này đã bị lộ vì `.gitignore` chỉ có pattern `*.env`, không khớp `.env.py`).

---

## 9. Checklist bảo mật (rút kinh nghiệm từ bản v1)

- [ ] `.gitignore` chặn đúng mọi biến thể file env: `.env`, `.env.*`, `*.env` — kiểm tra bằng `git status` trước khi commit lần đầu.
- [ ] Không có secret nào (JWT key, mật khẩu mail) nằm trong code hay file đã commit — chỉ đọc từ biến môi trường.
- [ ] CORS chỉ cho phép đúng domain frontend thật (không dùng `origins: "*"` ở production).
- [ ] Không bật chế độ debug của framework khi chạy production.
- [ ] JWT secret đủ dài, sinh ngẫu nhiên.
- [ ] Rate limiting cho các endpoint nhạy cảm: đăng nhập, gửi/xác nhận OTP (đăng ký + quên mật khẩu), **giữ ghế** (chặn spam tạo `giu_cho` hàng loạt làm nghẽn ghế thật).
- [ ] Mọi câu SQL đều dùng parameterized query (`%s`), tuyệt đối không nối chuỗi trực tiếp giá trị người dùng nhập vào câu SQL.
- [ ] Endpoint quên mật khẩu không tiết lộ email có tồn tại trong hệ thống hay không (giữ nguyên hành vi bản v1, `NGHIEP_VU.md` mục 2.1).
- [ ] Endpoint quét/xem chuyến, danh sách ghế không lộ thông tin cá nhân của khách khác (chỉ trả trạng thái ghế trống/đã giữ, không trả tên/SĐT người đang giữ).
- [ ] `thanh_toan_callback.py` (mục 5) xác thực **chữ ký/secret riêng của cổng thanh toán**, không tin tưởng bất kỳ request nào tự xưng "tôi là cổng thanh toán" — nếu không xác thực, ai cũng có thể gọi endpoint này để tự đánh dấu vé của mình là `da_thanh_toan` mà không trả tiền thật.
- [ ] Các cột `so_tai_khoan_nhan`/`ten_ngan_hang_nhan`/`ten_chu_tai_khoan_nhan` trong `lich_su_hoan_tien` (`DATABASE.md` mục 4.1) chỉ `ke_toan`/`quan_ly` đọc được — endpoint `ke_toan.py` phải kiểm tra `vai_tro` trước khi trả các trường này, không để lộ qua endpoint tra cứu tình trạng hoàn tiền dùng chung với nhân viên quầy vé (`NGHIEP_VU.md` mục 8.4).

---

## 10. Hướng dẫn bắt đầu cho thành viên mới

```bash
git clone <repo-url>
cd project-root
cp backend/.env.example backend/.env   # điền giá trị thật (xin từ trưởng nhóm, không tự bịa)
docker-compose up                      # dựng backend + Postgres local
# chạy migration lần đầu:
docker-compose exec backend yoyo apply
```
Sau đó backend chạy tại `http://localhost:8000/docs` (Swagger UI tự sinh — dùng luôn để test API thay vì Postman thủ công).

Frontend chạy độc lập — mở trực tiếp file HTML hoặc dùng 1 static server nhẹ, trỏ file cấu hình về `http://localhost:8000`. Nhớ test **cả 2 thư mục** `frontend/khach-hang/` và `frontend/nhan-vien/`.

---

## 11. Quy ước đặt tên

- Tên bảng, cột, biến trong Python: `snake_case` không dấu tiếng Việt trong tên (dữ liệu bên trong vẫn lưu tiếng Việt có dấu bình thường).
- Tên file/thư mục: nhất quán `snake_case`.
- Mỗi Repository/Service đặt tên theo entity số ít: `VeRepository`, không phải `VesRepository`.
