/*
 * Bảo vệ trang cần đăng nhập + kiểm tra vai trò + đăng xuất — riêng cho
 * các trang Quản lý. Trang đăng nhập cán bộ (frontend/nhan-vien/dang-nhap.html)
 * là trang chung duy nhất giữa các vai trò (điểm vào hệ thống), tự viết
 * script riêng của nó, không phụ thuộc file này.
 */

function yeuCauDangNhap() {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/nhan-vien/dang-nhap.html";
    return null;
  }
  return token;
}

/** Chặn phía client cho tiện UX (ẩn/chuyển hướng ngay, đỡ chờ API trả lỗi
 * 403) — quyền THẬT SỰ vẫn do backend kiểm tra lại qua yeu_cau_vai_tro()
 * (auth_middleware.py), không tin tưởng riêng localStorage. */
function yeuCauVaiTro(...vaiTroChoPhep) {
  const token = yeuCauDangNhap();
  if (!token) return null;

  const vaiTro = localStorage.getItem("vai_tro");
  if (!vaiTroChoPhep.includes(vaiTro)) {
    alert("Tài khoản của bạn không có quyền truy cập trang này");
    window.location.href = "/nhan-vien/dang-nhap.html";
    return null;
  }
  return { token, vaiTro };
}

function dangXuat() {
  localStorage.removeItem("token");
  localStorage.removeItem("vai_tro");
  localStorage.removeItem("ho_ten");
  window.location.href = "/nhan-vien/dang-nhap.html";
}
