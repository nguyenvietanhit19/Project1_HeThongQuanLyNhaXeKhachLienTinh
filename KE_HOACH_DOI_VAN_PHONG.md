# Kế hoạch — Đổi văn phòng của cán bộ (nhánh kèm UC-36)

> Nhánh: `feature/Nghia-doi-van-phong` (từ `integration/gop-nhanh-thanh-vien` sau PR #54).
> Spec: `NGHIEP_VU.md` mục "Nhánh kèm theo — Đổi văn phòng của cán bộ" (đã cập nhật 6/11/2026 theo các quy tắc Nghĩa chốt); sơ đồ `UML_DIAGRAMS.md` (`AD_UC36_DoiVanPhongCanBo`).
> Cách làm: từng bước, xong bước nào báo kết quả và xin xác nhận bước đó.

---

## 1. Quy tắc đã chốt (6/11/2026, Nghĩa)

| # | Quy tắc |
|---|---|
| 1 | **Không chặn khi cán bộ còn đơn đang xử lý** (quầy vé / gửi hàng không có trạng thái xử lý kéo dài; đơn thuộc văn phòng nên người còn lại tiếp nhận) |
| 2 | **Văn phòng cũ phải còn ≥ 1 nhân viên cùng vai trò** (không tính người chuyển; quầy vé đếm riêng, gửi hàng đếm riêng; chỉ tính tài khoản đang hoạt động). VD 2 nhân viên gửi hàng thì chỉ 1 người được chuyển. **Áp dụng cho cả quầy vé và gửi hàng** |
| 3 | **Lý do bắt buộc**, văn bản tự do, 1–200 **từ** (chốt 6/11/2026; đếm từ = tách theo khoảng trắng). Thêm chặn kỹ thuật tối đa 2000 ký tự để tránh một "từ" dài vô hạn |

Quyền: `quan_ly` (bất kỳ) và `quan_ly_nhan_su`. Đối tượng: `nhan_vien_quay_ve`, `nhan_vien_gui_hang`.

## 2. Đã có sẵn

| Cần | Đã có |
|---|---|
| Bảng văn phòng cán bộ | `ho_so_can_bo_diem (nguoi_dung_id PK, van_phong_id)` (chỉ 2 cột) |
| Hàm ghi văn phòng | `nguoi_dung_repository.gan_van_phong` (`INSERT ... ON CONFLICT DO UPDATE`) — **của phần gửi hàng, không sửa**; mình viết hàm riêng trong `tai_khoan_can_bo_repository.py` để chạy chung transaction với kiểm tra |
| Danh sách văn phòng cho ô chọn | `GET /quan-ly-nhan-su/tai-khoan/van-phong` (UC-36) |
| Kiểm tra "điểm là văn phòng" | `dia_diem_repo.tim_diem_don_tra_theo_id` (dùng ở UC-36) |
| Ghi nhật ký theo vai trò | `_ghi_nhat_ky` trong `tai_khoan_can_bo_service.py` (QLNS → bảng riêng, `quan_ly` → `nhat_ky_admin`) |
| Giao diện | `tai-khoan.html` (bảng tài khoản, hộp thoại Khóa / Mở khóa làm mẫu) |

## 3. Quyết định kỹ thuật (đề xuất, mình tự làm trừ khi Nghĩa muốn khác)

| # | Vấn đề | Đề xuất |
|---|---|---|
| 1 | Đếm "còn ≥ 1 người cùng vai trò" | `ho_so_can_bo_diem` ⋈ `nguoi_dung`: cùng `vai_tro`, `dang_hoat_dong = true`, `van_phong_id` = cũ, `nguoi_dung_id <> người chuyển` |
| 2 | Hai người cùng chuyển lúc văn phòng chỉ có 2 người | 1 transaction; `SELECT ... FOR UPDATE` trên dòng **văn phòng cũ** (`diem_don_tra`) để các lần chuyển cùng văn phòng xếp hàng, rồi mới đếm |
| 3 | Người chuyển đang bị khóa tài khoản | Không áp dụng quy tắc 2 (họ vốn không được tính là đang làm) |
| 4 | Chưa có văn phòng cũ (gán lần đầu) | Không có quy tắc 2; vẫn bắt buộc lý do |
| 5 | Văn phòng mới trùng văn phòng cũ / không phải văn phòng | 400, giống spec |
| 6 | API | `PUT /quan-ly-nhan-su/tai-khoan/{id}/van-phong`, body `{van_phong_id, ly_do}`; trả văn phòng cũ + mới (tên) |
| 7 | Nhật ký | 1 dòng `doi_van_phong`, đối tượng `nguoi_dung`; `ghi_chu` = "Văn phòng cũ → mới: lý do". **Cần migration**: `nhat_ky_quan_ly_nhan_su` có `CHECK` chỉ cho 6 hành động → thêm `doi_van_phong`. `nhat_ky_admin` là TEXT tự do nên không cần |
| 8 | Nhãn ở UC-52 | Thêm "Đổi văn phòng" vào bảng nhãn của `nhat_ky_service.py` |

## 4. Các bước

✅ **Bước 0 — Spec (đã xong cùng file này):** `NGHIEP_VU.md` và `UML_DIAGRAMS.md` đã sửa theo 3 quy tắc.

✅ **Bước 1 — Migration:** `backend/migrations/20261106_0900_nhat_ky_qlns_them_doi_van_phong.sql` (đổi `CHECK`, an toàn: chỉ nới thêm 1 giá trị). Thử 2 lần trong transaction rồi hủy, sau đó áp dụng thật; cập nhật `DATABASE.md` mục 6.3.

✅ **Bước 2 — Repository** (`tai_khoan_can_bo_repository.py`, chỉ thêm): `van_phong_hien_tai`, `doi_van_phong` (1 transaction: khóa văn phòng cũ, đếm đồng nghiệp, ghi) — trả mã kết quả như `cho_nghi_viec` của UC-51.

✅ **Bước 3 — Service + Schema + Route:** `doi_van_phong(actor_id, actor_vai_tro, muc_tieu_id, van_phong_id, ly_do)` (quyền: QLNS chỉ quầy vé / gửi hàng — đã nằm trong 4 vai trò QLNS quản lý; kiểm tra vai trò, văn phòng hợp lệ, khác văn phòng cũ, lý do), ghi nhật ký.

✅ **Bước 4 — Unit test:** vai trò sai, không tìm thấy, lý do trống / 201 từ / 200 từ vẫn hợp lệ / quá 2000 ký tự, văn phòng không hợp lệ / trùng, chặn khi chỉ còn một người, cho phép khi còn người khác, người khóa không tính, người chuyển đang khóa, gán lần đầu, nhật ký đúng bảng.

✅ **Bước 5 — Thử trên DB thật** trong 1 transaction rồi rollback (như UC-51/52): văn phòng 2 người, chuyển 1 / chuyển người thứ 2 bị chặn, 2 vai trò đếm riêng, người khóa không tính, ghi `ho_so_can_bo_diem` đúng.

✅ **Bước 6 — Frontend** (`tai-khoan.html`): nút "Đổi văn phòng" ở hàng quầy vé / gửi hàng, hộp thoại chọn văn phòng + lý do (đếm từ /200), hiện lỗi chặn rõ ràng. Xem trên Edge thật.

✅ **Bước 7 — Tài liệu:** `NHAP_QUAN_LY_NHAN_SU.md`, `BAO_CAO_...`, `TAC_DONG_...` (việc #7 → có chốt, thêm migration), `DATABASE.md`, kế hoạch này.

**Bước 8 — Commit → push → PR** (xin xác nhận trước khi push; không đưa file tóm tắt đoạn chat).

## 5. Ảnh hưởng tới người khác

- **1 migration mới** (nới `CHECK` của `nhat_ky_quan_ly_nhan_su`): cả nhóm chạy `yoyo apply ./migrations` sau khi pull; quên thì QLNS đổi văn phòng sẽ lỗi 500.
- **Ghi vào `ho_so_can_bo_diem`** (bảng của phần gửi hàng): chỉ `INSERT ... ON CONFLICT` giống hàm cũ của họ, không đổi cấu trúc.
- **Không xóa chuỗi hàm cũ `gan_van_phong_can_bo`** (route `PUT /quan-ly/ho-so-can-bo-diem`, schema `GanVanPhongCanBoRequest`, `gui_hang_service.gan_van_phong_can_bo`, `nguoi_dung_repository.gan_van_phong`): **không thuộc phần của mình**, để phần gửi hàng tự xử lý (Nghĩa chốt 6/11/2026). Mình chỉ báo cho họ biết khi đổi văn phòng đã merge (`TAC_DONG...` mục 2).

## 6. Rủi ro / chưa chắc

- Văn phòng chỉ có 1 người từ đầu thì không ai chuyển được (đúng ý quy tắc) → muốn đóng / gộp văn phòng phải thêm nhân viên mới trước.
- Khóa tài khoản (UC-37) hay cho nghỉ việc **không** áp dụng quy tắc 2, nên văn phòng vẫn có thể hết người theo cách đó; chưa nằm trong yêu cầu.
