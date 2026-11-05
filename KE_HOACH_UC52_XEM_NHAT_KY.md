# Kế hoạch UC-52 — Xem nhật ký thao tác

> Nhánh: `feature/Nghia-uc52-nhat-ky` (từ `integration/gop-nhanh-thanh-vien` sau PR #52).
> Spec gốc: `NGHIEP_VU.md` UC-52 (dòng ~878), mục 8.9 điểm 7; thiết kế `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1 (quyết định 14, 15).
> Cách làm: từng bước, xong bước nào báo kết quả và xin xác nhận bước đó.

---

## 1. UC-52 làm gì

Màn hình **chỉ xem** nhật ký thao tác, mới nhất ở trên, chia trang.

| Người xem | Thấy gì |
|---|---|
| `quan_ly_nhan_su` | **Chỉ dòng do chính mình thực hiện** (bảng `nhat_ky_quan_ly_nhan_su`) — backend ép, dù client gửi tham số gì |
| `quan_ly` | **Toàn bộ** = gộp `nhat_ky_quan_ly_nhan_su` + `nhat_ky_admin`; lọc thêm được theo người thực hiện |

Lọc: từ ngày, đến ngày (giờ VN), loại hành động, loại đối tượng (+ người thực hiện, chỉ `quan_ly`). Phân trang 50 dòng/lần, tối đa 200. Mỗi dòng hiện: thời gian, người thực hiện (tên + mã), hành động (nhãn tiếng Việt), đối tượng (tên + mã), ghi chú (lý do...).

## 2. Đã có sẵn, không cần làm lại

| Cần | Đã có |
|---|---|
| Hai bảng nhật ký + chỉ mục theo người thực hiện, theo đối tượng | Có (`nhat_ky_quan_ly_nhan_su`, `nhat_ky_admin`) → **không cần migration** |
| Mọi hành động của UC-36/37/49/51 đã ghi đúng bảng theo vai trò | Có (đã kiểm tra thật) |
| Mã nhân viên để hiện kèm tên | `nguoi_dung.ma`, `nhan_su_van_hanh.ma` (phụ xe lấy mã tài khoản) |
| Khung trang + menu + bảng | `nav.js`, `data-table.js`, các trang `ho-so.html` / `tai-khoan.html` |
| Hàm đọc nhật ký | **Chưa có** — cả hai repository nhật ký mới chỉ có hàm `ghi` (bảng chỉ `INSERT`) |

## 3. Quyết định cần chốt trước khi code

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Cách gộp hai bảng cho `quan_ly` | Một câu `UNION ALL` trong repository, sắp `thoi_gian DESC`, `LIMIT/OFFSET` ở DB; kèm tổng số dòng để chia trang | Hai bảng cùng cấu trúc; dữ liệu nhật ký nhỏ nên không cần phân trang kiểu khác |
| 2 ✅ | `quan_ly` thấy **cả hành động của nhóm khác** ghi vào `nhat_ky_admin` sau này (tuyến, giá, xe...) | **Có**, vì spec ghi "thấy toàn bộ" và `nhat_ky_admin` vốn dùng chung (`hanh_dong` TEXT tự do). Hiện chỉ có dòng của phần nhân sự | Đúng spec; nhãn lạ hiện nguyên giá trị thô |
| 3 ✅ | Đối tượng không phải người / hồ sơ (nhóm khác ghi `doi_tuong_loai = 'tuyen'`...) | Hiện loại + 8 ký tự đầu của id, không tra tên | Không biết bảng nào để tra; tránh đoán |
| 4 | Lọc "loại hành động" của `quan_ly_nhan_su` | Chỉ 6 hành động của bảng riêng (CHECK ở DB); `quan_ly` lọc theo giá trị bất kỳ | Khớp dữ liệu thật |
| 5 | Lọc theo người thực hiện | Chỉ `quan_ly`; API thêm danh sách người đã từng thao tác (để đổ ô chọn); QLNS gửi tham số này vẫn bị **bỏ qua** | Quyết định 14 |
| 6 | Quyền | Route cho `quan_ly_nhan_su` + `quan_ly`; vai trò khác 403 | UC-52 trong ma trận quyền |
| 7 | Ngày lọc | `tu_ngay` từ 00:00:00, `den_ngay` đến hết ngày, giờ VN (`Asia/Ho_Chi_Minh`); `tu_ngay > den_ngay` → 400 | Spec: giờ VN |
| 8 | Tham số phân trang | `trang` ≥ 1, `so_dong` 1–200 (mặc định 50); vượt → 422 | Spec |
| 9 | Bảo mật | Mọi tham số truyền qua `%s` (không nối chuỗi); `ghi_chu` hiển thị qua `esc()`; không trả mật khẩu / dữ liệu nhạy cảm (nhật ký vốn không lưu) | — |

## 4. Các bước thực hiện

✅ **Bước 1 — Repository:** thêm hàm **đọc** vào `nhat_ky_quan_ly_nhan_su_repository.py` và `nhat_ky_admin_repository.py` (không sửa `ghi`), hoặc một `nhat_ky_doc_repository.py` mới gộp hai bảng. Đề xuất file mới, vì câu `UNION` thuộc cả hai bảng. Hàm: `tim(pham_vi, tu, den, hanh_dong, doi_tuong_loai, nguoi_id, trang, so_dong)` → `(dòng, tổng)`; `danh_sach_nguoi_thuc_hien()`.
  Tên người / mã: `JOIN nguoi_dung` (người thực hiện); đối tượng: `LEFT JOIN nguoi_dung` hoặc `nhan_su_van_hanh` theo `doi_tuong_loai`.

✅ **Bước 2 — Service** (`nhat_ky_service.py` mới): ép phạm vi theo vai trò, kiểm tra tham số, đổi ngày VN sang khoảng thời gian, gắn nhãn tiếng Việt.

✅ **Bước 3 — Schema + Route:** `GET /quan-ly-nhan-su/nhat-ky` (+ `GET /quan-ly-nhan-su/nhat-ky/nguoi-thuc-hien` cho `quan_ly`).

✅ **Bước 4 — Unit test:** phạm vi theo vai trò (QLNS bị ép dù gửi `nguoi_id` người khác), lọc ngày / hành động, phân trang và giới hạn, `tu_ngay > den_ngay`, đối tượng không tra được tên, SQL chỉ dùng tham số.

✅ **Bước 5 — Thử trên DB thật:** dữ liệu thử trong **một transaction rồi rollback** (như UC-51), kiểm tra cả hai bảng, thứ tự, phân trang, lọc.

✅ **Bước 6 — Frontend:** trang `nhat-ky.html` + mục menu "Nhật ký thao tác" trong `nav.js` (+ cập nhật chú thích đầu file); bộ lọc, bảng, phân trang. Xem trên Edge thật.

✅ **Bước 7 — Tài liệu:** `NHAP_QUAN_LY_NHAN_SU.md`, `BAO_CAO_...`, `TAC_DONG_...` (UC-52 chỉ **đọc** hai bảng nhật ký, không migration), kế hoạch này.

**Bước 8 — Commit → push → PR** vào `integration/gop-nhanh-thanh-vien` (xin xác nhận trước khi push; không đưa file tóm tắt đoạn chat).

## 5. Ảnh hưởng tới người khác

- **Không migration**, không sửa hàm cũ của ai; chỉ thêm file mới (repository đọc, service, schema, route, trang `nhat-ky.html`) và 1 mục menu.
- `quan_ly` sẽ thấy trong màn nhật ký **mọi dòng nhóm khác ghi vào `nhat_ky_admin`** (nếu có sau này). Nhóm khác nên ghi `hanh_dong` / `ghi_chu` không chứa dữ liệu nhạy cảm.

## 6. Rủi ro / chưa chắc

- `nhat_ky_admin` có thể có `doi_tuong_loai` lạ do nhóm khác thêm: đã xử lý theo quyết định 3 (hiện thô, không lỗi).
- Số dòng lớn về sau: chỉ mục sẵn có theo người / đối tượng, nhưng chưa có chỉ mục theo `thoi_gian` riêng. Dữ liệu hiện nhỏ nên chưa cần; ghi lại để thêm nếu chậm.
