Giao diện khách hàng: tra cứu chuyến, đặt vé online, xem lịch sử vé (`NGHIEP_VU.md` mục 8.1). HTML/CSS/JS tĩnh, chưa cần framework — xem `ARCHITECTURE.md` mục 3.

- **Trang chủ công khai** nằm ở `frontend/index.html` (đường dẫn gốc `/` khi deploy) — tra cứu chuyến + xem sơ đồ ghế, không cần đăng nhập (UC-04). CSS/JS riêng: `trang-chu.css`, `trang-chu.js` (tiền tố class `.tc-*`).
- `dang-nhap.html`, `dang-ky.html`, `quen-mat-khau.html` + `auth.css` (tiền tố `.kh-*`): UC-01/02/03.
- `khung-trang.js` (thanh trên + footer + tiện ích dùng chung), `ho-so.js` (cửa sổ "Tài khoản của tôi": xem/sửa họ tên, số điện thoại, đổi mật khẩu, đăng xuất — mở ngay tại trang, không có trang riêng).
