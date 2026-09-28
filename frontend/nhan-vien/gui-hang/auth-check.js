/*
 * auth-check.js — Kiểm tra phiên đăng nhập và phân quyền cho Nhân viên gửi hàng (UC-23 -> 27, 39).
 * Quyền hợp lệ: 'nhan_vien_gui_hang' hoặc 'quan_ly'.
 */

function kiemTraQuyenGuiHang() {
  const token = localStorage.getItem("token");
  const vaiTro = localStorage.getItem("vai_tro");

  if (!token) {
    window.location.href = "../dang-nhap.html";
    return null;
  }

  // Cho phép nhân viên gửi hàng hoặc quản lý
  if (vaiTro !== "nhan_vien_gui_hang" && vaiTro !== "quan_ly") {
    alert("Bạn không có quyền truy cập vào phân hệ Nhân viên gửi hàng!");
    window.location.href = "../dang-nhap.html";
    return null;
  }

  return {
    token,
    vaiTro,
    hoTen: localStorage.getItem("ho_ten") || "Nhân viên gửi hàng",
    email: localStorage.getItem("email") || "",
  };
}

function dangXuatNhanVien() {
  localStorage.removeItem("token");
  localStorage.removeItem("vai_tro");
  localStorage.removeItem("ho_ten");
  localStorage.removeItem("email");
  window.location.href = "../dang-nhap.html";
}

// Thực thi kiểm tra ngay khi nạp trang
const nguoiDungHienTai = kiemTraQuyenGuiHang();

