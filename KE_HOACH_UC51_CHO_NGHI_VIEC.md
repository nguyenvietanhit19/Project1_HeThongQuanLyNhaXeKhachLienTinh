# Kế hoạch UC-51 — Cho nghỉ việc nhân sự vận hành

> Nhánh: `feature/Nghia-uc51-cho-nghi-viec` (từ `integration/gop-nhanh-thanh-vien` sau PR #50).
> Spec gốc: `NGHIEP_VU.md` UC-51 (dòng ~858), mục 8.9 điểm 6; thiết kế `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1 (quyết định 9–13).
> Cách làm: từng bước, xong bước nào báo kết quả và xin xác nhận bước đó.

---

## 1. Việc UC-51 làm (tóm tắt)

Chọn hồ sơ tài xế/phụ xe đang `dang_lam` → nhập ngày nghỉ + lý do → **xem trước** xe nào thiếu người → xác nhận → 1 transaction:
1. Hồ sơ → `da_nghi_viec` (kèm ngày, lý do). Không xóa.
2. Nếu là phụ xe có tài khoản: `nguoi_dung.dang_hoat_dong = false`.
3. Mọi dòng `xe_nhan_su` của người này → `tam_nghi` (**không** xóa/gỡ — gỡ hẳn là việc `quan_ly`, UC-35).
4. Ghi nhật ký `cho_nghi_viec` (QLNS → `nhat_ky_quan_ly_nhan_su`, `quan_ly` → `nhat_ky_admin`).

Sau transaction: gửi thông báo cho mọi `quan_ly` + `dieu_do_vien` đang hoạt động, mỗi xe thiếu người một thông báo (thông báo lỗi thì nuốt, không làm hỏng việc nghỉ).

## 2. Đã có sẵn, không cần làm lại

| Cần | Đã có |
|---|---|
| Cột `trang_thai`, `ngay_nghi_viec`, `ly_do_nghi_viec` + `CHECK` hai chiều | `nhan_su_van_hanh` (DATABASE.md 1.4) |
| `cho_nghi_viec` trong `CHECK` của `nhat_ky_quan_ly_nhan_su` | Có từ migration `20260927_1000` → **không cần migration mới** |
| `nhat_ky_admin` (TEXT tự do) | Có |
| Thông báo nội bộ + danh sách người nhận | `thong_bao_khach_service.gui`, `nguoi_dung_repo.danh_sach_id_theo_vai_tro` (dùng ở UC-37) |
| Mẫu "xe thiếu phụ xe" | `tai_khoan_can_bo_repository.xe_thieu_phu_xe` (UC-37) |
| Biên chế đã loại hồ sơ `da_nghi_viec` | UC-35 chỉ nhận `dang_lam` |
| Hiển thị trạng thái `da_nghi_viec` ở giao diện | `ho-so.html` (pill "Đã nghỉ việc") |

## 3. Quyết định cần chốt trước khi code

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | "Thiếu người" ✅ **đã chốt: 2 tài xế + 1 phụ xe** | Xe **cố định** đang hoạt động, không tính người này: **< 2 tài xế** hoặc **0 phụ xe** (phụ xe phải còn hồ sơ `dang_lam` + tài khoản đang hoạt động). Biên chế tạm thời chuyển `tam_nghi` nhưng không tạo cảnh báo | Đúng spec UC-51, quyết định 11 |
| 2 | Chặn khi xe đang chạy | ✅ **Đã chốt (Nghĩa, 5/11): chọn B.** Xe của dòng biên chế (`xe_id` **hoặc** `xe_thuc_te_id` của chuyến) có chuyến `dang_chay` **hoặc `gap_su_co`** → 400 "chờ chuyến kết thúc / xử lý xong sự cố rồi thực hiện lại". Mở rộng hơn spec (spec chỉ ghi `dang_chay`) vì chuyến gặp sự cố vẫn có thể quay lại `dang_chay`; phải ghi vào `NGHIEP_VU.md` UC-51 | Xe gặp sự cố vẫn ở ngoài đường |
| 3 | Ngày nghỉ | Mặc định hôm nay (giờ VN), không tương lai, không trước `ngay_vao_lam`; lý do bắt buộc, `strip`, 1–500 ký tự | Giống UC-37 |
| 4 | Số dòng nhật ký | **1 dòng** `cho_nghi_viec` (đối tượng = hồ sơ), `ghi_chu` = lý do + "đã khóa tài khoản" nếu có. Không ghi thêm `khoa_tai_khoan` | Một thao tác nghiệp vụ = một dòng; khỏi lệch giữa hai bảng nhật ký |
| 5 | Hai API | `GET /quan-ly-nhan-su/ho-so/{id}/xem-truoc-nghi-viec` (không ghi gì; trả danh sách biên chế + xe thiếu + cờ bị chặn) và `POST /quan-ly-nhan-su/ho-so/{id}/nghi-viec` | Đúng bước 2–3 của spec, quyết định 10 |
| 6 | Xem trước và POST có thể lệch nhau | POST **tự tính lại** trong transaction (khóa dòng hồ sơ `FOR UPDATE`), không tin kết quả xem trước | Tránh hai người thao tác cùng lúc |
| 7 | Ca đặc biệt | Người không thuộc biên chế: bỏ bước thông báo. Tài xế: không có tài khoản nên không khóa gì. Hồ sơ đã nghỉ: 400 "hồ sơ này đã nghỉ việc" | Spec rẽ nhánh |

## 4. Các bước thực hiện

✅ **Bước 1 — Repository** (`nhan_su_van_hanh_repository.py`, chỉ **thêm** hàm cuối file, không sửa hàm cũ của người khác):
- `danh_sach_bien_che_cua_nhan_su(nhan_su_id)` — các dòng `xe_nhan_su` (kèm biển số, loại, trạng thái).
- `xe_dang_chay_cua_nhan_su(nhan_su_id)` — xe có chuyến `dang_chay`.
- `xe_thieu_nguoi_neu_nghi(nhan_su_id)` — theo quyết định 1, trả `[{xe_id, bien_so, thieu_tai_xe, thieu_phu_xe}]`.
- `dong_ho_so_nghi_viec(cur, nhan_su_id, ngay, ly_do)`, `khoa_tai_khoan(cur, …)`, `chuyen_bien_che_tam_nghi(cur, nhan_su_id)` — chạy chung một transaction.

✅ **Bước 2 — Service** (`ho_so_nhan_su_service.py`): `xem_truoc_nghi_viec`, `cho_nghi_viec` (kiểm tra → transaction → nhật ký → thông báo). Dùng lại `_ghi_nhat_ky` (đã ghi đúng bảng theo vai trò).

✅ **Bước 3 — Schema + Route**: `ChoNghiViecRequest(ngay_nghi, ly_do)`, `XemTruocNghiViecResponse`, `ChoNghiViecResponse`; hai route trong `routes/nhan_su.py`.

✅ **Bước 4 — Unit test**: ngày (tương lai / trước ngày vào làm), lý do trống, đã nghỉ rồi, xe đang chạy, thiếu tài xế / thiếu phụ xe / tạm thời không tính, tài xế không khóa gì, nhật ký đúng bảng không ghi chéo, thông báo đúng người, lỗi thông báo không làm hỏng.

✅ **Bước 5 — Thử API thật** (làm bằng 27 ca trong 1 transaction rồi rollback, DB sạch): tạo dữ liệu thử (tài xế + phụ xe + xe + biên chế), thử đủ ca, rồi **dọn dữ liệu và khôi phục sequence** (như các lần trước). Hỏi trước khi chèn xe / biên chế.

✅ **Bước 6 — Frontend** (`ho-so.html`): nút "Cho nghỉ việc" ở hàng hồ sơ `dang_lam`; hộp thoại nhập ngày + lý do → hiện xem trước (biên chế, xe thiếu người, cảnh báo bị chặn) → xác nhận. Xem trên Edge thật.

✅ **Bước 7 — Tài liệu**: cập nhật `NHAP_QUAN_LY_NHAN_SU.md`, `TOM_TAT_QUAN_LY_NHAN_SU.md`, `BAO_CAO_...`, `TAC_DONG_DEN_NGUOI_KHAC_...` (UC-51 chỉ **đọc/ghi** `xe_nhan_su` và gửi thông báo, không sửa code nhóm).

**Bước 8 — Commit → push → PR** vào `integration/gop-nhanh-thanh-vien` (xin xác nhận trước khi push; không đưa file tóm tắt đoạn chat vào commit).

## 5. Ảnh hưởng tới người khác (ghi vào `TAC_DONG_...`)

- Không có migration mới, không sửa hàm cũ của nhóm.
- Ghi `xe_nhan_su.trang_thai = 'tam_nghi'`: phần UC-35/điều độ cần hiểu dòng này là "người đã nghỉ". Nhóm cần biết để không tự đổi lại `dang_hoat_dong`.
- Gửi thông báo cho `quan_ly` và `dieu_do_vien`.

## 6. Rủi ro / chưa chắc

- Quy tắc "đủ người" (2 tài xế + ≥1 phụ xe) lấy từ spec; cần kiểm tra code UC-35 đang dùng đúng quy tắc đó để hai bên không lệch.
- Chặn cả `gap_su_co` (mục 3.2) là mở rộng so với spec: cần sửa `NGHIEP_VU.md` UC-51 cho khớp (bước 7).
