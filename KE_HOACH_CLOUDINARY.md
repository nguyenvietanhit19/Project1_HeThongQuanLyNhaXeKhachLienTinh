# Kế hoạch — Hoàn thiện lưu ảnh hồ sơ nhân sự bằng Cloudinary (UC-49)

> Nhánh dự kiến: `feature/Nghia-cloudinary` (từ `integration/gop-nhanh-thanh-vien`, **sau khi PR tách quyền được merge** — cả hai cùng sửa `ho_so_nhan_su_service.py`).
> Cách làm: từng bước, xong bước nào báo kết quả và xin xác nhận bước đó.

---

## 1. Vấn đề đã rà (6/11/2026)

| # | Vấn đề | Chi tiết |
|---|---|---|
| 1 | **Chưa có khóa thật** | `backend/.env` đang là `cloudinary://<api_key>:<api_secret>@<cloud_name>` (chữ giữ chỗ) nên tải / xem ảnh chưa chạy thật bao giờ; `backend/.env.example` **không có dòng Cloudinary** nào |
| 2 | **Ảnh cũ không bị xóa** | Hàm `luu_tru_anh_service.xoa_anh` đã có (chú thích ghi "gọi khi thay ảnh mới") nhưng **không chỗ nào gọi** → đổi ảnh thì ảnh cũ (CCCD, bằng lái...) nằm lại trên Cloudinary |
| 3 | **Khóa bí mật** | `.env` đã nằm trong `.gitignore` (không bị đẩy lên); chưa có quy ước dùng tài khoản trong nhóm |
| 4 | **Không giới hạn file tải lên** (mới thấy) | Route `POST /ho-so/{id}/anh` và `/giay-to/{loai}/anh` làm `await file.read()` không giới hạn kích thước / định dạng |
| 5 | **Link xem ảnh không hết hạn** (mới thấy) | `lay_url_xem` ký URL nhưng chữ ký **không tự hết hạn** (đã ghi trong chú thích của code) |

## 2. Quyết định đã chốt (Nghĩa, 6/11/2026)

| # | Quyết định |
|---|---|
| 1 | **Tài khoản Cloudinary:** khi phát triển, mỗi người tự dùng tài khoản miễn phí riêng; bản triển khai (Render) dùng tài khoản của nhóm. Ảnh nằm trong thư mục theo môi trường (`dev` / `production`) để ảnh thử không lẫn ảnh thật |
| 2 | **Ảnh cũ:** đổi ảnh thì xóa ảnh cũ (tải ảnh mới → lưu DB → mới xóa ảnh cũ; xóa lỗi chỉ ghi log). Gia hạn giấy tờ (đổi ngày hết hạn) thì giữ ảnh cũ cho tới khi có ảnh mới thay vào |
| 3 | **Cho nghỉ việc: giữ ảnh** (hồ sơ nghỉ việc vẫn giữ lịch sử, không xóa) |
| 4 | **Giới hạn tải lên:** tối đa 5MB, chỉ JPEG / PNG / WebP, kiểm tra theo **nội dung thật** (magic bytes) chứ không tin đuôi file; vi phạm → 400 kèm thông báo rõ |
| 5 | **Link xem ảnh: chấp nhận phương án A** — giữ chữ ký không hết hạn như hiện tại, chỉ ghi rõ rủi ro vào tài liệu (đủ cho quy mô bài tập lớn). Nếu sau này cần an toàn hơn: cho ảnh đi qua backend (phương án B) |

## 3. Các bước

✅ **Bước 1 — Cấu hình:** thêm `CLOUDINARY_URL` (placeholder + hướng dẫn lấy ở Dashboard) vào `backend/.env.example`; thư mục ảnh theo `APP_ENV` (`nha_xe/<APP_ENV>/nhan_su/ho_so`, `.../giay_to`) trong `luu_tru_anh_service.py`.

✅ **Bước 2 — Kiểm tra file tải lên:** hàm kiểm tra (≤ 5MB, JPEG / PNG / WebP theo magic bytes) đặt ở `app/utils/`; route đọc tối đa 5MB + 1 byte (không đọc cả file khổng lồ vào bộ nhớ) rồi báo 400 nếu vượt hoặc sai định dạng.

✅ **Bước 3 — Xóa ảnh cũ:** `cap_nhat_anh_ho_so` và `cap_nhat_anh_giay_to`: lấy `public_id` cũ trước, sau khi **tải mới + lưu DB thành công** mới gọi `xoa_anh(cũ)` (bỏ qua nếu cũ trống hoặc trùng mới; xóa lỗi chỉ ghi log). Cho nghỉ việc **không** đụng tới ảnh.

✅ **Bước 4 — Unit test:** ma trận kiểm tra file (kích thước biên, định dạng đúng / sai, đuôi giả), thứ tự tải → lưu → xóa cũ, upload lỗi thì không xóa cũ và không đổi DB, xóa lỗi không làm hỏng, thư mục theo môi trường, nghỉ việc không xóa ảnh.

✅ **Bước 5 — Thử với Cloudinary thật:** Nghĩa tạo tài khoản miễn phí và điền `CLOUDINARY_URL` vào `backend/.env` (mình **không cần xem khóa**); mình chạy thử tải ảnh thật, lấy link xem, đổi ảnh và xác nhận ảnh cũ biến mất, rồi **dọn sạch ảnh thử** trên Cloudinary.

✅ **Bước 6 — Frontend** (`ho-so.html`): kiểm tra kích thước / định dạng ngay ở trình duyệt, hiện thông báo của server khi bị từ chối. Xem trên Edge thật.

✅ **Bước 7 — Tài liệu (thu hẹp theo Nghĩa, 6/11/2026: chỉ cập nhật `ARCHITECTURE.md` dòng "File/ảnh" + ghi rủi ro link không hết hạn; bỏ qua hướng dẫn tạo tài khoản và các file NHAP / BAO_CAO / TAC_DONG vì sẽ viết lại thành một file chung):** `HUONG_DAN_LAM_VIEC.md` (cách tạo tài khoản Cloudinary và điền `.env`, quy ước mỗi người một tài khoản), `ARCHITECTURE.md` (dòng "File/ảnh": thư mục theo môi trường, giới hạn), ghi rõ **rủi ro link không hết hạn** (phương án A), `NHAP_...`, `BAO_CAO_...`, `TAC_DONG_...`, kế hoạch này.

**Bước 8 — Commit → push → PR** (xin xác nhận trước khi push; không đưa file tóm tắt đoạn chat).

## 4. Ảnh hưởng tới người khác

- `backend/.env.example` có thêm dòng Cloudinary: ai chạy tính năng ảnh cần điền khóa của mình (tạo tài khoản miễn phí).
- Ảnh mới nằm trong thư mục theo môi trường (thư mục cũ `nha_xe/nhan_su/...` không còn dùng; do chưa từng có khóa thật nên chưa có ảnh nào cần chuyển).
- Route tải ảnh từ chối file > 5MB hoặc không phải JPEG / PNG / WebP.
- Không migration.

## 5. Rủi ro / chưa chắc

- **Link xem ảnh không hết hạn** (chấp nhận, ghi trong tài liệu): ai có link thì xem được lâu dài.
- Gói miễn phí Cloudinary có giới hạn dung lượng / băng thông; việc xóa ảnh cũ giúp không tốn chỗ, nhưng ảnh của người đã nghỉ việc vẫn được giữ (quyết định 3).
- Cần Nghĩa điền khóa thật thì bước 5 mới làm được.

## 6. Kết quả thử thật và lỗi phát hiện (6/11/2026)

- Thử với Cloudinary thật (thư mục `nha_xe/development/`): tải ảnh, link có chữ ký xem được, link không chữ ký bị từ chối, đổi ảnh chân dung và ảnh giấy tờ thì ảnh cũ bị xóa; dọn sạch ảnh thử (0 ảnh còn sót).
- **Lỗi bắt được nhờ thử thật:** xóa ảnh xong nhưng link cũ vẫn xem được vì CDN giữ bản lưu tạm → đã thêm `invalidate=True` khi xóa.
- **Lỗi có sẵn từ UC-49:** khối tải ảnh giấy tờ trong `ho-so.html` không bao giờ hiện ra do luật `[hidden] { display: none !important }` trong `design-tokens.css` → đã sửa (bỏ thuộc tính `hidden` khi có giấy tờ).
- **Chưa thử:** hai kết nối chạy song song trên hồ sơ thật (cần ghi tạm dữ liệu thật); tải ảnh từ trình duyệt qua backend thật (cần đăng nhập quản lý nhân sự thật).

