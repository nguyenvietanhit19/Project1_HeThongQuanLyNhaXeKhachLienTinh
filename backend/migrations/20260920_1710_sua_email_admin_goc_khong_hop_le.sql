-- Sửa email tài khoản quan_ly gốc seed ở 20260917_0900_tao_bang_nguoi_dung.sql
-- (KHÔNG sửa lại file migration cũ — HUONG_DAN_LAM_VIEC.md mục 4).
--
-- "admin@nhaxekhach.local" dùng domain .local — dành riêng cho mDNS
-- (RFC 6762), bị EmailStr (pydantic/email-validator) từ chối là "special-use
-- or reserved name". Hậu quả: tài khoản quan_ly gốc KHÔNG BAO GIỜ đăng nhập
-- được qua /auth/dang-nhap thật (dù đặt đúng mật khẩu), chặn toàn bộ UC cần
-- vai_tro = quan_ly (UC-29..39) vì không ai bootstrap được tài khoản đầu tiên.
UPDATE nguoi_dung
SET email = 'admin@nhaxekhach.com'
WHERE email = 'admin@nhaxekhach.local' AND la_tai_khoan_goc = true;
