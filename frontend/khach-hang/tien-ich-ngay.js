/*
 * Tiện ích ngày giờ theo múi giờ Việt Nam + định dạng tiền — dùng chung cho trang chủ và trang kết quả tìm chuyến.
 * Cần khach-hang/khung-trang.js (pad2) nạp trước.
 */

const MUI_GIO = "Asia/Ho_Chi_Minh";
const TEN_THU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

// ---------- Ngày giờ theo múi giờ Việt Nam ----------
const homNayVN = () => new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO }).format(new Date()); // "YYYY-MM-DD"
const ngayVN = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO }).format(new Date(iso));
const gioVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));

function congNgay(ngayIso, n) {
  const d = new Date(`${ngayIso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function nhanNgay(ngayIso, ngan = false) {
  const d = new Date(`${ngayIso}T00:00:00Z`);
  const [y, m, ngay] = ngayIso.split("-");
  return ngan ? `${TEN_THU[d.getUTCDay()]} ${ngay}/${m}` : `${TEN_THU[d.getUTCDay()]}, ${ngay}/${m}/${y}`;
}

function thoiLuong(phut) {
  const h = Math.floor(phut / 60);
  const m = phut % 60;
  return m ? `${h}g${pad2(m)}` : `${h} giờ`;
}

const tien = (so) => `${Number(so).toLocaleString("vi-VN")}đ`;
