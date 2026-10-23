# Kế hoạch làm UC-36 — Tạo tài khoản cán bộ

> **File này là kế hoạch, chưa có code.** Nhánh làm: `feature/Nghia-uc36-tao-tai-khoan-can-bo` (tạo từ `integration/gop-nhanh-thanh-vien`, ngày 21/10/2026).
> Nguồn: `NGHIEP_VU.md` mục 2, 8.7 điểm 2, 8.9, UC-36; `ARCHITECTURE.md`; `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` mục 6; thiết kế chi tiết ở `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1.

---

## 1. Mục tiêu và ranh giới

**Mục tiêu**: `quan_ly_nhan_su` và `quan_ly` cùng dùng **một chức năng** để tạo tài khoản đăng nhập cho cán bộ; hệ thống quyết định ai được tạo vai trò nào.

| Trong phạm vi | Ngoài phạm vi (làm riêng) |
|---|---|
| Tạo tài khoản cán bộ + gán văn phòng (nếu vai trò cần) + sinh mật khẩu ban đầu (không gửi email/OTP) | Khóa / mở khóa tài khoản (UC-37) |
| Danh sách tài khoản cán bộ, danh sách văn phòng cho ô chọn | Hồ sơ nhân sự tài xế/phụ xe (UC-49, đã xong) |
| Ghi nhật ký khi người tạo là `quan_ly_nhan_su` | Cho nghỉ việc (UC-51), xem nhật ký (UC-52) |
| Trang giao diện tạo + xem danh sách | Gán điều độ viên ↔ tuyến (thuộc trang Tuyến của `quan_ly`) |

---

## 2. Quy tắc nghiệp vụ đã chốt

### 2.1. Ai được tạo vai trò nào

Theo `NGHIEP_VU.md` hiện tại (không đổi):

| Người thao tác | Phụ xe, quầy vé, gửi hàng, điều độ viên | `ke_toan` | `quan_ly` | `quan_ly_nhan_su` |
|---|---|---|---|---|
| `quan_ly_nhan_su` | ✅ | ❌ không đủ quyền | ❌ không đủ quyền | ❌ không đủ quyền |
| `quan_ly` (không phải gốc) | ✅ | ✅ | ❌ chỉ tài khoản gốc | ❌ chỉ tài khoản gốc |
| `quan_ly` gốc (`la_tai_khoan_goc = true`) | ✅ | ✅ | ✅ | ✅ |

`khach_hang` không tạo ở đây (tự đăng ký công khai).

### 2.2. Ai gắn văn phòng

| Vai trò | Văn phòng |
|---|---|
| Quầy vé, gửi hàng | **Bắt buộc** — ghi vào `ho_so_can_bo_diem` |
| Điều độ viên | **Không** (theo `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` mục 6; không tạo dòng `ho_so_can_bo_diem`) |
| Phụ xe, kế toán, quản lý, QLNS | Không |

> ⚠ **Điều độ viên không gắn văn phòng là quy tắc từ một đề xuất CHƯA được nhóm duyệt.** Cách giữ an toàn: đặt danh sách "vai trò cần văn phòng" thành **một hằng số duy nhất** trong service. Nếu nhóm bác đề xuất thì thêm `dieu_do_vien` vào hằng số, sửa đúng một dòng. Điều độ viên không có văn phòng thì `danh_sach_dieu_do_vien_tai_diem` (báo sự cố, code của người khác) sẽ không tìm thấy họ — việc đó thuộc phần điều độ viên, không phải UC-36.

### 2.3. Dữ liệu nhập (làm rõ so với bản gốc, đã ghi vào `NGHIEP_VU.md`)

Email, **họ tên, SĐT** (bắt buộc vì cột `NOT NULL`), vai trò, văn phòng (nếu cần). SĐT chuẩn hóa bằng `chuan_hoa_so_dien_thoai`. Email phải hợp lệ thật: đuôi `.local` bị từ chối (đã gặp khi tạo tài khoản test).

### 2.4. Mật khẩu ban đầu (đổi 23/10/2026: bỏ cơ chế "mời" bằng OTP)

Email cán bộ do **công ty cấp** nên không cần xác minh qua OTP. Mọi tài khoản mới có **mật khẩu mặc định chung `12345678`** (hằng số `MAT_KHAU_MAC_DINH` trong service; cố ý đơn giản vì chỉ dùng đến lần đổi đầu tiên). Tạo `nguoi_dung` với `mat_khau` = bản băm bcrypt và `da_xac_nhan = true`; response vẫn có `mat_khau_ban_dau` để giao diện nhắc người tạo báo cho cán bộ. Người tạo báo cho cán bộ ngoài hệ thống; cán bộ đổi mật khẩu sau khi đăng nhập (`PUT /auth/doi-mat-khau`). OTP chỉ còn dùng khi quên mật khẩu. Không gửi email lúc tạo, nên không còn `da_gui_email` và không còn nhánh "gửi mail lỗi".

Bản rõ **không** ghi vào nhật ký. Chưa có cờ "bắt buộc đổi mật khẩu lần đầu" (cần cột mới ở bảng dùng chung `nguoi_dung`) — hiện chỉ khuyến nghị đổi trong nghiệp vụ.

---

## 3. Đã có sẵn — tái dùng, không viết lại

| Cần | Dùng | Vị trí |
|---|---|---|
| Bảng tài khoản (đã cho `mat_khau` NULL) | `nguoi_dung` | migration `20260917_0900` |
| Băm mật khẩu | `passlib` bcrypt (cùng cấu hình với `mat_khau_service`), tự dựng `CryptContext` trong service để không import hàm private | `services/tai_khoan_can_bo_service.py` |
| Chuẩn hóa SĐT | `chuan_hoa_so_dien_thoai` | `utils/so_dien_thoai.py` |
| Tìm văn phòng hợp lệ | `dia_diem_repo.tim_diem_don_tra_theo_id` (`loai == 'van_phong'`) | `repositories/dia_diem_repository.py` |
| Ghi nhật ký | `nhat_ky_quan_ly_nhan_su_repository.ghi` (đã có `tao_tai_khoan`, `nguoi_dung` trong CHECK) | repo của UC-49 |
| Phân quyền theo vai trò | `yeu_cau_vai_tro("quan_ly_nhan_su", "quan_ly")` | `middleware/auth_middleware.py` |
| Báo lỗi nghiệp vụ | `GiaTriLoi`, `CamTruyCap`, `KhongTimThay`, `LoiHeThong` | `utils/loi.py` |

**Không cần migration**: mọi cột và ràng buộc UC-36 cần đều đã có.

---

## 4. Chuỗi hàm gán văn phòng của phần gửi hàng (đã có, không phải thiết kế chính thức)

| Tầng | Vị trí | Ghi chú |
|---|---|---|
| Route | `routes/quan_ly.py:62` `PUT /quan-ly/ho-so-can-bo-diem/{id}` | Chỉ `quan_ly` gọi được |
| Service | `services/gui_hang_service.py:86` `gan_van_phong_can_bo` | Cho phép quầy vé, gửi hàng, điều độ viên |
| Schema | `schemas/don_hang_schema.py:190` `GanVanPhongCanBoRequest` | |
| Repository | `repositories/nguoi_dung_repository.py:55` `gan_van_phong` | `INSERT ... ON CONFLICT DO UPDATE` vào `ho_so_can_bo_diem` |

Chỉ có **một nơi gọi** (route trên); không frontend, không test. Do một thành viên phần gửi hàng viết để test trước. **Bảng `ho_so_can_bo_diem` vẫn được đọc** ở middleware, `gui_hang.py`, `chuyen_xe_repository`, `don_hang_repository` → **không được xóa bảng**, chỉ có thể thay chuỗi hàm *ghi*.

**Hướng xử lý (đề xuất, chờ chốt):**
1. **Giai đoạn 1 (đợt UC-36):** viết service mới tự ghi `ho_so_can_bo_diem` bằng SQL của mình; **không đụng** chuỗi cũ.
2. **Giai đoạn 2 (PR nhỏ riêng):** sau khi route mới chạy ổn và người làm phần gửi hàng xác nhận, xóa chuỗi cũ ở 4 file trên. Phía gửi hàng chuyển sang gọi route mới.
3. Route cũ còn gán được cho điều độ viên → lệch quy tắc mới; xóa ở giai đoạn 2 giải quyết luôn.

---

## 5. Thiết kế

### 5.1. File (toàn bộ **thêm mới**)

| Lớp | File | Việc |
|---|---|---|
| Route | `routes/tai_khoan_can_bo.py` | Các route ở 5.2; mở cho `quan_ly_nhan_su` và `quan_ly` |
| Service | `services/tai_khoan_can_bo_service.py` | Quy tắc nghiệp vụ, kiểm tra, điều phối |
| Repository | `repositories/tai_khoan_can_bo_repository.py` | SQL: tạo tài khoản + gán văn phòng, danh sách, văn phòng |
| Schema | `schemas/tai_khoan_can_bo_schema.py` | Request/response |
| `main.py` | thêm 2 dòng | `import` router + `include_router` |

Tên file khớp `ARCHITECTURE.md` (đã dự kiến sẵn `tai_khoan_can_bo_service.py` và `tai_khoan_can_bo.py`).

### 5.2. API

```
GET   /quan-ly-nhan-su/tai-khoan?vai_tro=&tu_khoa=   danh sách tài khoản cán bộ
GET   /quan-ly-nhan-su/tai-khoan/van-phong           danh sách văn phòng cho ô chọn
POST  /quan-ly-nhan-su/tai-khoan                     tạo tài khoản (UC-36)
```

**Request tạo**: `email` (EmailStr), `ho_ten`, `so_dien_thoai`, `vai_tro`, `van_phong_id` (tùy vai trò).
**Response**: `id`, `email`, `ho_ten`, `vai_tro`, `van_phong_id`, `mat_khau_ban_dau` (nhắc người tạo báo cho cán bộ).

### 5.3. Phân quyền kiểu bảng tra cứu

Một dict `{vai_tro_người_gọi: {vai_tro_được_tạo}}` cho phần "ai tạo được gì", cộng một điều kiện riêng cho luật "chỉ tài khoản **gốc** tạo `quan_ly`/`quan_ly_nhan_su`" (phải tra `la_tai_khoan_goc` trong DB). Không rải `if` khắp nơi → đổi quy tắc chỉ sửa một chỗ.

### 5.4. Luồng trong service (kiểm tra hết trước khi ghi)

1. Tra người đang thao tác (vai trò, có phải gốc không).
2. Kiểm tra quyền tạo đúng vai trò được chọn → sai: `CamTruyCap` ("không đủ quyền" hoặc "chỉ tài khoản quản lý gốc mới tạo được").
3. Chuẩn hóa SĐT → sai: `GiaTriLoi`.
4. Email chưa tồn tại → trùng: `GiaTriLoi`.
5. Nếu vai trò cần văn phòng: có `van_phong_id` và điểm đó là `van_phong` → sai: `GiaTriLoi`.
6. **Tạo tài khoản và gán văn phòng trong cùng một transaction** (một hàm repository làm cả hai) — không để lại tài khoản thiếu văn phòng.
7. Trả kèm mật khẩu ban đầu mặc định cho người tạo.
8. Ghi nhật ký `tao_tai_khoan` (chỉ khi người gọi là `quan_ly_nhan_su`).

Trùng email do hai người tạo cùng lúc: bắt lỗi vi phạm `UNIQUE` ở repository và đổi thành thông báo "email đã tồn tại".

### 5.5. Frontend (`frontend/nhan-vien/quan-li-nhan-su/`)

- Trang `tai-khoan.html`: bảng danh sách (lọc vai trò, tìm) + nút "Tạo tài khoản" mở modal (email, họ tên, SĐT, vai trò, văn phòng).
- Ô vai trò chỉ liệt kê những vai trò **người đang đăng nhập được tạo** (QLNS: 4 vai trò; `quan_ly` thường: thêm kế toán; gốc: thêm quản lý, QLNS). Quyền thật vẫn kiểm ở backend.
- Ô văn phòng chỉ hiện khi vai trò là quầy vé hoặc gửi hàng.
- Sau khi tạo: hộp thoại hiển thị mật khẩu ban đầu mặc định kèm nhắc "báo cho cán bộ và đổi mật khẩu ngay sau khi đăng nhập".
- Thêm một mục vào `nav.js`.

---

## 6. Việc phải làm trước khi code

- [ ] **Chốt với nhóm**: UC-36/37 được giao cho **Người 1 (Trưởng nhóm)** trong `CONTRIBUTING.md` — xác nhận ai làm, tránh trùng. - nhiem vu cua quan li nhan su
- [ ] **Chốt** hai giai đoạn cho chuỗi hàm cũ (mục 4) và có thêm chức năng "đổi văn phòng" trong đợt này không.
- [ ] **Chốt** điều độ viên không gắn văn phòng (mục 2.2): đề xuất đó nhóm đã duyệt chưa. - da duyet
- [ ] **Sửa tài liệu cho khớp** (nếu điều độ viên không còn văn phòng): `NGHIEP_VU.md` mục 2 (dòng `dieu_do_vien`) và UC-36 bước 1; `UML_DIAGRAMS.md` sơ đồ UC-36; `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1. Hiện tài liệu vẫn ghi điều độ viên "gắn cố định 1 văn phòng".
- [ ] Bật Docker, `docker-compose up -d --build` và `yoyo apply` để DB khớp code mới.

---

## 7. Thứ tự làm

1. Schema → repository → service (kèm unit test) → route → đăng ký `main.py`.
2. Test tay qua Swagger / PowerShell (mục 8).
3. Frontend `tai-khoan.html` + menu.
4. Cập nhật tài liệu, commit, PR.

---

## 8. Kiểm thử

**Unit test** (`backend/tests/unit/test_tai_khoan_can_bo_service.py`, giả repository bằng `monkeypatch`, không cần DB):

| Nhóm | Ca |
|---|---|
| Ma trận quyền | Từng ô của bảng 2.1 (3 người thao tác × 4 nhóm vai trò) |
| Dữ liệu | Email trùng; SĐT sai; thiếu họ tên |
| Văn phòng | Quầy vé/gửi hàng thiếu văn phòng; điểm không phải văn phòng; điều độ viên **không** bị đòi văn phòng; phụ xe/kế toán không gán văn phòng |
| Mật khẩu ban đầu | Mật khẩu ban đầu là `12345678`, DB chỉ nhận bản băm khớp; không vào nhật ký |
| Nhật ký | Chỉ ghi khi người gọi là `quan_ly_nhan_su` |
| Schema | Quầy vé/gửi hàng không có `van_phong_id` bị chặn ngay ở schema |

**Test tay**: đăng nhập `quanlynhansu@gmail.com` → tạo một tài khoản quầy vé → kiểm tra có dòng ở `nguoi_dung` và `ho_so_can_bo_diem`, đăng nhập được bằng `mat_khau_ban_dau` trả về. Rồi thử tạo `ke_toan` bằng QLNS → phải bị chặn.

---

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Trùng việc với Trưởng nhóm (UC được giao cho họ) | Nhắn xác nhận trước khi code |
| Quy tắc điều độ viên đổi theo đề xuất chưa duyệt | Hằng số duy nhất (2.2) |
| Người tạo biết mật khẩu ban đầu của cán bộ | Mật khẩu mặc định chung nên ai biết email công ty đều đăng nhập được cho đến khi cán bộ đổi → nhắc đổi ngay; cờ bắt buộc đổi lần đầu là việc sau (cần cột mới ở bảng `nguoi_dung`) |
| Xóa chuỗi hàm cũ ảnh hưởng người test phần gửi hàng | Làm hai giai đoạn, báo người viết |
| Khóa/mở khóa (UC-37) chưa có → tạo nhầm tài khoản không có cách khóa | Làm UC-37 ngay sau UC-36 |
| `nhat_ky_admin` chưa có migration → `quan_ly` tạo tài khoản không có nơi ghi nhật ký | Đã nêu ở `NHAP_QUAN_LY_NHAN_SU.md` 11.1f; hỏi nhóm |
