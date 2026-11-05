/*
 * auth-check.js — Kiểm tra phiên đăng nhập và phân quyền cho phân hệ Gửi hàng.
 * - nhan_vien_gui_hang: thao tác đầy đủ tại văn phòng được gán.
 * - quan_ly: chỉ xem (hàng đến, hàng tồn, đơn, thống kê) — không tạo đơn/giao hàng.
 * Kiểm tra quyền THẬT SỰ luôn ở backend; ở đây chỉ để điều hướng giao diện.
 */

const VAI_TRO_GUI_HANG = ["nhan_vien_gui_hang", "quan_ly"];
const KHOA_LOCAL_STORAGE = ["token", "vai_tro", "ho_ten", "email", "van_phong_truc_id", "nhan_vien_gui_hang_active_tab"];

function tokenDaHetHan(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now();
  } catch (_) {
    return true;
  }
}

function dangXuatNhanVien() {
  KHOA_LOCAL_STORAGE.forEach(k => {
    try { localStorage.removeItem(k); } catch (_) {}
  });
  window.location.href = "../dang-nhap.html";
}

function kiemTraQuyenGuiHang() {
  const token = localStorage.getItem("token");
  const vaiTro = localStorage.getItem("vai_tro");

  if (!token || tokenDaHetHan(token)) {
    dangXuatNhanVien();
    return null;
  }

  if (!VAI_TRO_GUI_HANG.includes(vaiTro)) {
    alert("Bạn không có quyền truy cập vào phân hệ Nhân viên gửi hàng!");
    dangXuatNhanVien();
    return null;
  }

  return {
    token,
    vaiTro,
    laQuanLy: vaiTro === "quan_ly",
    hoTen: localStorage.getItem("ho_ten") || "Nhân viên gửi hàng",
  };
}

window.dangXuat = dangXuatNhanVien;
window.dangXuatNhanVien = dangXuatNhanVien;

// Thực thi kiểm tra ngay khi nạp trang
const nguoiDungHienTai = kiemTraQuyenGuiHang();
