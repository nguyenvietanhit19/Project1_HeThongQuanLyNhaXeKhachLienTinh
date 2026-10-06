/*
 * Bảo vệ trang cần đăng nhập + kiểm tra vai trò + đăng xuất — riêng cho
 * các trang Điều độ viên (frontend/nhan-vien/dieu-do/).
 * Đồng bộ cơ chế xác thực với các phân hệ cán bộ khác.
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
    alert("Tài khoản của bạn không có quyền truy cập trang Điều độ viên");
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
