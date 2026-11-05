# Kế hoạch — Tách quyền: quản lý chỉ quản lý 3 vai trò cấp cao, quản lý nhân sự lo các vai trò nhỏ

> Nhánh: `feature/Nghia-phan-quyen-quan-ly` (từ `integration/gop-nhanh-thanh-vien` sau PR #56).
> Cách làm: từng bước, xong bước nào báo kết quả và xin xác nhận bước đó.
> Phần chức năng quản lý giống quản lý nhân sự **đã được giao lại cho Nghĩa** (6/11/2026) nên việc sửa ở phía quản lý nằm trong phạm vi của Nghĩa.

---

## 1. Quyết định đã chốt (6/11/2026, Nghĩa)

| # | Quyết định |
|---|---|
| 1 | `quan_ly` (gốc và thường) **chỉ tương tác với tài khoản `quan_ly`, `quan_ly_nhan_su`, `ke_toan`** cho "đỡ phải quản lý nhiều" |
| 2 | Các vai trò nhỏ (`phu_xe`, `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien`) và hồ sơ tài xế / phụ xe do **`quan_ly_nhan_su` quản lý** |
| 3 | **Hồ sơ nhân sự trong hệ thống chỉ có tài xế và phụ xe** (chủ yếu để nhắc hạn giấy tờ). Hồ sơ của `quan_ly` / `quan_ly_nhan_su` / `ke_toan` do bộ phận nhân sự bên ngoài quản lý, **không đưa vào hệ thống** |
| 4 | **Nhật ký thao tác (UC-52): `quan_ly` vẫn xem toàn bộ** (kể cả việc của QLNS), vì là việc giám sát |
| 5 | Menu giao diện của `quan_ly`: **thêm mục vào cuối `quan-ly/nav.js`** (cách A, Nghĩa tự thêm), không sửa mục cũ |
| 6 | **Dùng lại tối đa** trang / code của quản lý nhân sự |

## 2. Ma trận quyền sau khi đổi

**Tạo tài khoản (UC-36)** — người gọi × vai trò được tạo:

| Người gọi | phụ xe, quầy vé, gửi hàng, điều độ viên | `ke_toan` | `quan_ly` | `quan_ly_nhan_su` |
|---|---|---|---|---|
| `quan_ly_nhan_su` | ✅ (như cũ) | ❌ | ❌ | ❌ |
| `quan_ly` thường | **❌ (mới)** | ✅ | ❌ chỉ gốc | ❌ chỉ gốc |
| `quan_ly` gốc | **❌ (mới)** | ✅ | ✅ | ✅ |

**Khóa / mở khóa (UC-37)** — chỉ khóa bậc thấp hơn mình (bậc: gốc > quản lý thường = kế toán > QLNS > 4 vai trò nhỏ):

| Người gọi | Khóa được |
|---|---|
| `quan_ly_nhan_su` | 4 vai trò nhỏ (như cũ) |
| `quan_ly` thường | **chỉ `quan_ly_nhan_su`** (bỏ 4 vai trò nhỏ) |
| `quan_ly` gốc | **`quan_ly_nhan_su`, `ke_toan`, `quan_ly`** (bỏ 4 vai trò nhỏ) |

**Các chức năng khác:**

| Chức năng | `quan_ly_nhan_su` | `quan_ly` |
|---|---|---|
| Danh sách tài khoản (UC-36/37) | 4 vai trò nhỏ | **chỉ 3 vai trò: `ke_toan`, `quan_ly`, `quan_ly_nhan_su`** |
| Hồ sơ tài xế / phụ xe (UC-49), giấy tờ, ảnh | ✅ | **❌ (mới)** |
| Cho nghỉ việc (UC-51) | ✅ | **❌ (mới)** |
| Đổi văn phòng (quầy vé / gửi hàng) | ✅ | **❌ (mới)** |
| Nhật ký thao tác (UC-52) | của mình | toàn bộ (giữ nguyên) |

**Giữ nguyên:** quy tắc "chỉ gốc tạo `quan_ly` / `quan_ly_nhan_su`", gốc không bị khóa, không tự khóa mình; nhật ký ghi `quan_ly` → `nhat_ky_admin`, QLNS → bảng riêng; `quan_ly` vẫn **nhận thông báo** (phụ xe bị khóa, xe thiếu người) và vẫn làm **biên chế xe (UC-35)**.

## 3. Đã kiểm tra: ít rủi ro

- Giao diện `quan-ly/` **không gọi** endpoint `/quan-ly-nhan-su/*` nào; không module backend nào khác import ba service này → bỏ quyền `quan_ly` ở đây không làm hỏng phần khác.
- Không migration, không đổi DB.
- Nếu hệ thống không còn QLNS hoạt động: `quan_ly` gốc vẫn tạo được QLNS mới, `quan_ly` thường vẫn mở khóa được QLNS → không bị kẹt.

## 4. Các bước

✅ **Bước 0 — Spec:** sửa `NGHIEP_VU.md` (mục 2 bảng vai trò, 8.7 điểm 2 và 5, 8.9 "Ranh giới với `quan_ly`", UC-36 / 37 / 49 / 51 / đổi văn phòng phần actor và ma trận quyền ở mục 11–12), `UML_DIAGRAMS.md` (actor các sơ đồ liên quan), `DATABASE.md` nếu có chỗ ghi quyền.

✅ **Bước 1 — Backend phân quyền:**
- `tai_khoan_can_bo_service.py`: `_QUYEN_TAO`, `_QUYEN_XEM`, `_QUYEN_KHOA` theo ma trận trên; `doi_van_phong` chỉ cho `quan_ly_nhan_su`.
- `routes/nhan_su.py` (hồ sơ, nghỉ việc): chỉ `quan_ly_nhan_su` (chặn 403 ở middleware).
- `routes/tai_khoan_can_bo.py` và `routes/nhat_ky.py` giữ cho cả hai vai trò (quản lý vẫn dùng).
- `ho_so_nhan_su_service.py`: bỏ nhánh ghi `nhat_ky_admin` không còn đường tới (hoặc giữ làm phòng thủ; chốt khi làm).

✅ **Bước 2 — Unit test:** sửa các test đang khẳng định `quan_ly` tạo / khóa 4 vai trò nhỏ (đổi thành bị chặn 403), thêm test cho ma trận mới, danh sách chỉ 3 vai trò, hồ sơ / nghỉ việc / đổi văn phòng chặn `quan_ly`.

✅ **Bước 3 — Thử trên DB thật** trong 1 transaction rồi rollback, và một vòng qua HTTP bằng tài khoản `quan_ly` gốc (đã biết mật khẩu): tạo / khóa vai trò nhỏ bị 403; tạo kế toán OK; danh sách chỉ 3 vai trò; gọi `/quan-ly-nhan-su/ho-so` bị 403.

✅ **Bước 4 — Frontend:**
- `quan-ly/nav.js`: thêm **cuối mảng** 2 mục "Tài khoản cán bộ" và "Nhật ký thao tác" (Nghĩa tự thêm, báo nhóm).
- `tai-khoan.html`, `nhat-ky.html`: khi người đăng nhập là `quan_ly` thì dùng **khung / menu của quản lý** (hàm `renderSidebar` của `quan-ly/nav.js` đã nhận tham số menu); khi là QLNS vẫn như cũ. Cách nạp 2 file nav (trùng tên hàm `renderSidebar`) sẽ chốt khi làm, ưu tiên không nhân đôi trang.
- `ho-so.html`: chỉ QLNS (quản lý bị đưa về trang chủ của họ).
- Trang tài khoản với `quan_ly`: chỉ hiện chip 3 vai trò, ô tạo chỉ liệt kê vai trò được tạo (API `vai-tro-duoc-tao` đã trả theo người gọi).
- Xem trên Edge thật (server tạm, API giả).

✅ **Bước 5 — Tài liệu:** `NHAP_QUAN_LY_NHAN_SU.md`, `BAO_CAO_...`, `TAC_DONG_...` (thêm: sửa `quan-ly/nav.js` của nhóm quản lý, đổi quyền quản lý), kế hoạch này.

**Bước 6 — Commit → push → PR** (xin xác nhận trước khi push; không đưa file tóm tắt đoạn chat).

## 5. Ảnh hưởng tới người khác

- **Nhóm làm phần quản lý:** `quan-ly/nav.js` bị thêm 2 mục cuối mảng (không sửa mục cũ); `quan_ly` mất quyền quản lý 4 vai trò nhỏ (đã bàn, Nghĩa nhận phần này).
- Không migration, không đổi bảng; không ảnh hưởng nhóm khác.

## 6. Rủi ro / chưa chắc

- **Tài khoản vai trò nhỏ tạo trước đây bởi `quan_ly`** vẫn nguyên; chỉ đổi người được quản lý từ nay.
- Quản lý đang quen tạo vai trò nhỏ sẽ gặp 403: giao diện chỉ liệt kê vai trò được tạo nên không thấy tùy chọn, nhưng nên báo cho người dùng.
- Cách dùng chung giao diện giữa hai vai trò (trùng tên hàm `renderSidebar`) cần thử kỹ ở bước 4.
