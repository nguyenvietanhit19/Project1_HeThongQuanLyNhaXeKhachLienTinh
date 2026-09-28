# Thay đổi "Tuyến chạy 2 chiều" — việc mỗi người cần làm để khớp

> Áp dụng cho mọi nhánh sẽ merge vào `integration/gop-nhanh-thanh-vien` / `main`.
> Đọc mục 1–3 (ai cũng cần), rồi làm theo mục của mình ở mục 4. Mục 5 là checklist trước khi tạo PR.

## 1. Tóm tắt

| Trước | Sau |
|---|---|
| Có bảng `nhom_tuyen` + `nhom_tuyen_khu_vuc`; 1 nhóm chứa 2 `tuyen` (chiều đi, chiều về) | **Không còn nhóm tuyến.** 1 `tuyen` = 1 hành trình vật lý, **chạy được cả 2 chiều** |
| `tuyen(id, nhom_tuyen_id, ten)` | `tuyen(id, ten, ngay_tao)` |
| `xe.nhom_tuyen_id` | **`xe.tuyen_id`** (NULL = xe dự phòng, không đổi ý nghĩa) |
| Chiều đi/về là 2 bản ghi `tuyen` khác nhau | Chiều là thuộc tính của **1 lần chạy**: cột **`chieu`** (`xuoi` / `nguoc`) nằm ở `lich_chay_dinh_ky` và `chuyen_xe` |
| Điểm dừng chiều về nhập riêng | Chỉ nhập danh sách điểm dừng **1 lần theo chiều xuôi** (`tuyen_diem_don_tra.thu_tu`). Chiều ngược = **đọc ngược lại chính danh sách đó** |

Điều quan trọng nhất với code của mọi người: **`thu_tu` tăng dần không còn luôn là hướng xe đi.** Với chuyến `chieu = 'nguoc'` thì hướng đi là `thu_tu` giảm dần (xem công thức ở mục 3).

Tài liệu gốc đã cập nhật: `NGHIEP_VU.md` mục 3.1, 3.2, 3.4, 3.5, 6 và UC-18/31/34/44; `DATABASE.md` mục 2.3, 2.4, 3.2, 3.3, 3.5, 7, 8.

## 2. Thay đổi ở database và migration

**Migration mới:** `backend/migrations/20260928_1000_bo_nhom_tuyen_gop_vao_tuyen.sql`
- Đổi `xe.nhom_tuyen_id` → `xe.tuyen_id` (FK sang `tuyen`).
- Bỏ cột `tuyen.nhom_tuyen_id`.
- Thêm `chuyen_xe.chieu TEXT NOT NULL CHECK (chieu IN ('xuoi','nguoc'))`.
- Xóa bảng `nhom_tuyen_khu_vuc` và `nhom_tuyen`.

**Đã sửa migration của Nghia** (chưa từng vào `main`, nên sửa được) để khớp với bảng đã có: `20260927_1000` (ALTER `nhan_su_van_hanh` thay vì CREATE), `20260927_1100` (chỉ tạo `lich_chay_dinh_ky`, có cột `chieu`), `20260927_1110` (không tạo lại `chuyen_xe`, chỉ siết `loai_xe_id` NOT NULL + thêm cột + index). File `..._tam_thoi.sql` đã bị xóa.

**Đồng bộ DB local sau khi pull:**
```
docker-compose exec backend sh -c 'yoyo apply --batch --database "$DATABASE_URL" ./migrations'
```
Nếu báo lỗi vì dữ liệu test cũ, reset hẳn (xóa sạch dữ liệu local): `docker-compose down -v` rồi `up -d` và chạy lại lệnh trên.

**Quy tắc viết migration mới** (tránh lỗi "already exists" khi ghép nhánh — yoyo chạy theo thứ tự tên file, mọi migration chưa chạy sẽ được áp dụng):
- **Không sửa** file migration đã merge vào `main`; thay đổi mới luôn là file mới.
- Bảng đã có trong các migration khác → dùng `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, không `CREATE TABLE` lại.
- Bảng mới → `CREATE TABLE IF NOT EXISTS`.
- Trước khi tạo PR, tự chạy toàn bộ migration trên **DB trống** (mục 5).

## 3. Công thức dùng chung: xử lý `thu_tu` theo `chieu`

Mọi chỗ code đang giả định "`thu_tu` lớn hơn = đi sau" cần đổi thành **`thu_tu` hiệu lực theo chiều của chuyến**.

**SQL (dùng khi so sánh thứ tự, đoạn `[đón, trả)`, sắp xếp):**
```sql
CASE WHEN c.chieu = 'xuoi' THEN tdt.thu_tu ELSE -tdt.thu_tu END AS thu_tu_hieu_luc
-- c = chuyen_xe, tdt = tuyen_diem_don_tra của đúng tuyến đó
```
Sau đó dùng `thu_tu_hieu_luc` ở mọi chỗ so sánh `<`, `>`, `ORDER BY`, `MIN/MAX`. Giá trị này chỉ dùng để so sánh thứ tự, **không** hiển thị ra giao diện — muốn hiển thị "điểm thứ mấy" thì dùng `ROW_NUMBER() OVER (ORDER BY thu_tu_hieu_luc)`.

| Cần | Chuyến `xuoi` | Chuyến `nguoc` |
|---|---|---|
| Điểm xuất phát | `thu_tu` nhỏ nhất | `thu_tu` lớn nhất |
| Điểm cuối | `thu_tu` lớn nhất | `thu_tu` nhỏ nhất |
| "Các điểm phía sau điểm X" | `thu_tu > thu_tu(X)` | `thu_tu < thu_tu(X)` |
| Phút từ lúc khởi hành tới điểm P (`thoi_gian_du_kien_phut`) | giá trị lưu sẵn của P | `MAX(thoi_gian_du_kien_phut của tuyến) − giá trị của P` |

Lưu ý `thoi_gian_du_kien_phut` **luôn lưu theo chiều xuôi** (cộng dồn từ điểm đầu tiên), chiều ngược tự suy ra như bảng trên (`DATABASE.md` mục 2.4).

**Giá vé** (`gia_ve`) chỉ lưu **1 dòng cho mỗi cặp (đi, đến) theo thứ tự chiều xuôi** và dùng chung cho cả 2 chiều. Khi tra giá cho chuyến `nguoc`, **đảo cặp** (`diem_di` ↔ `diem_den`) trước khi tra.

## 4. Việc cần làm theo từng người

### 4.1. Người 4 — Điều độ viên / chuyến xe (Nghia)
- [ ] **Sinh chuyến (UC-18, `jobs/sinh_chuyen_dinh_ky.py`):** copy `chieu` từ `lich_chay_dinh_ky` sang `chuyen_xe.chieu`. Cột này `NOT NULL`, không có default.
- [ ] **Gán xe (UC-44):** dùng `xe.tuyen_id` (thay cho `nhom_tuyen_id`). Xe có `tuyen_id` khác NULL chỉ được gán cho chuyến cùng `tuyen_id`, **bất kể chiều**. Xe `tuyen_id = NULL` là xe dự phòng.
- [ ] **Vị trí xe suy luận (mục 3.3 `NGHIEP_VU.md`):** điểm cuối của chuyến xe vừa chạy phụ thuộc chiều (bảng mục 3). Kiểm tra xe có "đúng vị trí" để nhận chuyến kế tiếp.
- [ ] Thống nhất với Dũng về `chuyen_xe_service.py`: Dũng đã có file này (phần phụ xe) từ nhánh phụ xe. Cần chốt **ai giữ file, ai bổ sung hàm** để tránh 2 bản trùng.
- [ ] Các migration của bạn đã được sửa (mục 2). Pull về, chạy `yoyo apply` và đọc lại để biết `nhan_su_van_hanh`, `chuyen_xe` đang ở dạng nào.

### 4.2. Người 3 — Phụ xe (Dũng)
Code hiện tại giả định `thu_tu` tăng = hướng xe chạy. Cần đổi (theo mục 3) ở:
- [ ] `backend/app/services/chuyen_xe_service.py` — dòng ~70 (điểm hiện tại lấy theo `thu_tu DESC`), ~177, **~200 (điểm xuất phát = `thu_tu` nhỏ nhất)**, ~218 (khách chờ ở các điểm phía sau).
- [ ] `backend/app/repositories/chuyen_xe_repository.py` — dòng ~89–94 (`ORDER BY tdt.thu_tu DESC`).
- [ ] `backend/app/repositories/ve_repository.py` — dòng ~144–161 (`tdt.thu_tu > %s`).
- [ ] Cần lấy `chuyen_xe.chieu` vào các truy vấn trên (JOIN `chuyen_xe`).
- [ ] Bổ sung unit test cho **chuyến `nguoc`** (hiện chỉ có kịch bản chiều xuôi).
- [ ] `frontend/shared/api-client.js` và `frontend/nhan-vien/dang-nhap.html` đã giữ bản của `main` khi merge. Nếu muốn chạy thử trên điện thoại qua LAN, dùng bản `API_BASE_URL` gộp: hostname `localhost`/IP thì `http://<hostname>:8000`, còn lại dùng URL Render.

### 4.3. Người 2 — Quầy vé / đặt vé / tìm chuyến (Sơn)
- [ ] **Tìm kiếm chuyến** (`tim_kiem_chuyen_service.py`): điều kiện `tdd_den.thu_tu > tdd_don.thu_tu` và các `MIN/MAX(thu_tu)` chỉ đúng cho chiều xuôi → chuyến `nguoc` sẽ không bao giờ được tìm thấy. Đổi sang `thu_tu_hieu_luc` (mục 3).
- [ ] **Chống trùng ghế** (`ve_lock_repository.py`): đoạn `[thu_tu(đón), thu_tu(trả))` phải dùng `thu_tu_hieu_luc` theo `chieu` của chuyến (`NGHIEP_VU.md` mục 6).
- [ ] **Tra giá vé:** với chuyến `nguoc`, đảo cặp đi/đến khi tra `gia_ve` (mục 3).
- [ ] **Kiểm tra điểm đón/trả hợp lệ** (`NGHIEP_VU.md` mục 3.4): điểm đón phải đứng trước điểm trả theo chiều hiệu lực của chuyến.
- [ ] **Migration `20260920_2200_bo_sung_bang_ve_va_tuyen.sql`:** hiện đã có sẵn trong chuỗi migration (từ nhánh của Nghia, Dũng, `main`): `tuyen_diem_don_tra`, `gia_ve`, `lich_chay_dinh_ky` (bản của bạn **thiếu cột `chieu`** và sẽ chạy trước bản của Nghia), các cột `chuyen_xe`, `lich_su_diem_dung_chuyen`, `ho_so_khach_hang`. **Xóa các phần trùng**, chỉ giữ lại nội dung thật sự chưa có ở nơi nào khác (nếu không còn gì thì xóa cả file). Riêng `lich_chay_dinh_ky` phải tạo bởi migration của Nghia (`20260927_1100`) để có cột `chieu`.
- [ ] **Nhánh cũ `son/feature`:** migration `20260920_1600_tao_bang_ve.sql` tạo lại bảng `ve` đã có → **không merge nhánh này**; dùng `Son/feature1_Nhanvienquayve`.

### 4.4. Người 5 — Gửi hàng / kế toán hoàn tiền (Trinh)
Đơn hàng chỉ gắn `tuyen_id`. Trước đây 1 tuyến = 1 chiều nên `tuyen_id` ngầm cho biết hướng; giờ 1 tuyến gồm cả 2 chiều nên **đơn Hà Nội→Sapa và Sapa→Hà Nội cùng `tuyen_id`**.
- [ ] **UC-26 danh sách chờ xếp** (`don_hang_repository.lay_danh_sach_cho_xep_xe`, route `GET /gui-hang/tuyen/{id}/cho-xep-xe`): hiện chỉ lọc theo `tuyen_id` → phụ xe chuyến xuôi thấy cả đơn ngược. Cần nhận thêm `chuyen_id` và chỉ trả đơn cùng chiều: `thu_tu(diem_gui)` đứng trước `thu_tu(diem_nhan)` theo `thu_tu_hieu_luc` của chuyến. **Không cần thêm cột** vào `don_hang` (chiều suy ra từ 2 điểm).
- [ ] **Tạo đơn** (`gui_hang_service.tao_don_hang`): ngoài việc kiểm tra tuyến tồn tại, cần kiểm tra `diem_gui` và `diem_nhan` đều thuộc `tuyen_diem_don_tra` của tuyến đó.
- [ ] **Chất hàng** (`xac_nhan_chat_hang`): kiểm tra chuyến cùng `tuyen_id` và cùng chiều với đơn.
- [ ] **Giao diện** (`frontend/nhan-vien/gui-hang/app.js` ~dòng 290): đang đoán tuyến bằng cách tìm địa danh trong tên tuyến. Nên đổi thành chọn tuyến chứa cả 2 điểm gửi/nhận (`tuyen_diem_don_tra`). `NGHIEP_VU.md` mục 10.4.1 bước 4 và mục 10.2/UC-26 cần cập nhật câu chữ "cùng tuyến" thành "cùng tuyến và cùng chiều".
- Lưu ý: UC-26 chưa chạy thử thật được vì chưa có code nào sinh `chuyen_xe` (đợi phần của Nghia).

### 4.5. Người 1 — Danh mục (Vanh) — đã làm
Trang **Tuyến** (chọn khu vực trước, lọc theo tỉnh, xem lộ trình thẳng hàng) và trang **Giá vé** (thống kê tuyến đủ/chưa đủ/chưa có giá) đã thiết kế lại. Route `/quan-ly/nhom-tuyen*` đã bị xóa; `TuyenResponse` không còn `nhom_tuyen_id`; body tạo/sửa tuyến không còn `nhom_tuyen_id`.

**Quy tắc kiểm tra khi tạo/sửa tuyến** (`dia_diem_service._validate_tuyen`, `NGHIEP_VU.md` UC-31):
- Điểm đầu và điểm cuối phải là `van_phong`.
- Các điểm cùng 1 khu vực phải nằm **liền nhau** (Hà Nội → Bắc Hà → Hà Nội là **sai**).
- Mỗi tỉnh/thành chỉ được đi qua **đúng 1 khu vực** trong 1 tuyến.

## 5. Checklist trước khi tạo PR

1. `git merge origin/integration/gop-nhanh-thanh-vien` (hoặc `main`) vào nhánh của mình, xử lý xung đột.
2. `grep -rn "nhom_tuyen"` trong `backend/` và `frontend/` — không còn kết quả nào ngoài migration cũ và phần giải thích trong tài liệu.
3. **Test migration trên DB trống:** `docker-compose down -v` → `docker-compose up -d` → `yoyo apply` (lệnh ở mục 2). Không được có lỗi.
4. `docker-compose exec backend python -m pytest tests -q` — toàn bộ test phải đạt.
5. Nếu code của bạn có thao tác theo thứ tự điểm dừng: đã dùng `thu_tu_hieu_luc` (mục 3) và có test cho cả chuyến `xuoi` lẫn `nguoc`.
6. Tài liệu (`NGHIEP_VU.md`, `DATABASE.md`) cập nhật theo đúng nội dung code, nếu bạn có thay đổi nghiệp vụ.
