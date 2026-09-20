/*
 * Bảo vệ trang cần đăng nhập + đăng xuất — dùng chung cho mọi trang khách hàng.
 * (Trang nhân viên sau này cần bản tương tự riêng, vì trang đăng nhập khác nhau.)
 */

function yeuCauDangNhap() {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/khach-hang/dang-nhap.html";
    return null;
  }
  return token;
}

function dangXuat() {
  localStorage.removeItem("token");
  localStorage.removeItem("vai_tro");
  localStorage.removeItem("ho_ten");
  window.location.href = "/khach-hang/dang-nhap.html";
}
