/*
 * Bảo vệ trang nhân viên theo vai trò — dùng chung cho mọi khu vực trong
 * frontend/nhan-vien/ (CONTRIBUTING.md mục 4/6). Gọi requireRole() ngay
 * đầu mỗi trang cần đăng nhập; không tự viết lại logic đọc localStorage
 * ở nơi khác.
 */

function requireRole(vaiTroYeuCau) {
  const token = localStorage.getItem("token");
  const vaiTro = localStorage.getItem("vai_tro");

  if (!token || vaiTro !== vaiTroYeuCau) {
    window.location.href = "/nhan-vien/dang-nhap.html";
    throw new Error("Chưa đăng nhập đúng vai trò, đang chuyển hướng");
  }

  return { hoTen: localStorage.getItem("ho_ten") };
}

function dangXuat() {
  localStorage.removeItem("token");
  localStorage.removeItem("vai_tro");
  localStorage.removeItem("ho_ten");
  window.location.href = "/nhan-vien/dang-nhap.html";
}
