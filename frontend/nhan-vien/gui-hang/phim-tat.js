/* phim-tat.js — Phím tắt cho thao tác tại quầy (tay vẫn trên bàn phím/máy quét).
 *   F2      Tạo đơn mới (chỉ nhân viên quầy)
 *   F4      Sang "Hàng đến" và đặt con trỏ vào ô quét mã / nhập SĐT
 *   Ctrl+P  Khi đang mở biên nhận / nhãn dán / phiếu bàn giao: in đúng vùng đó
 *   Esc     Đóng cửa sổ */

function khoiTaoPhimTat() {
  const goiY = $("phimTatGoiY");
  if (goiY) {
    goiY.textContent = laQuanLyXem()
      ? "⌨️ Phím tắt: F4 Hàng đến · Esc đóng cửa sổ"
      : "⌨️ Phím tắt: F2 Tạo đơn mới · F4 Quét mã / giao hàng · Ctrl+P in (khi đang mở biên nhận, nhãn) · Esc đóng cửa sổ";
  }
  document.addEventListener("keydown", xuLyPhimTat);
}

function xuLyPhimTat(e) {
  const modal = document.querySelector(".modal-overlay.active");

  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "p") {
    const nutIn = modal && modal.querySelector("[data-in]");
    if (nutIn) {
      e.preventDefault(); // chỉ chặn hộp thoại in mặc định của trình duyệt khi có vùng cần in
      nutIn.click();
    }
    return;
  }

  if (modal || e.ctrlKey || e.altKey || e.metaKey) return;

  if (e.key === "F2" && !laQuanLyXem()) {
    e.preventDefault();
    chuyenTab("tao-don");
    $("ten_nguoi_gui").focus();
  } else if (e.key === "F4") {
    e.preventDefault();
    chuyenTab("hang-den");
    $("inputTraCuuGiao").focus();
  }
}
