/*
 * core.js — state, tiện ích hiển thị và điều hướng tab dùng chung cho phân hệ Nhân viên gửi hàng.
 * Các file gui-hang/*.js nạp bằng thẻ <script> thường nên dùng chung phạm vi toàn cục
 * (thứ tự nạp xem cuối index.html).
 *
 * Quy ước an toàn: mọi dữ liệu lấy từ server/người dùng chỉ được đưa vào DOM
 * qua textContent hoặc escapeHtml() — không nối chuỗi thô vào innerHTML.
 * Nút trong các dòng bảng dùng data-* + event delegation, không onclick nối chuỗi.
 */

const $ = id => document.getElementById(id);

const TRANG_THAI = {
  cho_van_chuyen: { ten: "Chờ xếp xe", cls: "badge-cho_van_chuyen" },
  da_len_xe: { ten: "Đang trên xe", cls: "badge-da_len_xe" },
  cho_lay: { ten: "Chờ người nhận lấy", cls: "badge-cho_lay" },
  da_giao: { ten: "Đã giao", cls: "badge-da_giao" },
  qua_han_luu_kho: { ten: "Hàng tồn", cls: "badge-qua_han_luu_kho" },
};

const TAB_HOP_LE = ["tao-don", "hang-den", "don-gui", "hang-ton", "thong-ke"];
const SO_DONG_MOI_TRANG = 10;

const state = {
  tab: null,
  vaiTro: localStorage.getItem("vai_tro"),
  vanPhong: null,          // văn phòng của nhân viên {id, ten, dia_chi}
  vanPhongXemId: "",       // quản lý: văn phòng đang xem ("" = toàn hệ thống)
  loaiHang: [],
  diemNhan: [],            // [{khu_vuc_id, ten_khu_vuc, van_phong: [...]}]
  hangDen: [],
  nhomHangDen: "",
  ketQuaSdt: [],           // kết quả tra cứu theo SĐT đang hiện trong modal
  luaChonLienHe: [],       // các lựa chọn kết quả liên hệ đang hiện trong modal
  donGui: { offset: 0, total: 0, items: [] },
  hangDenOffset: 0,        // vị trí dòng đầu của trang đang xem ở tab Hàng đến (phân trang phía client)
  donDangGiao: null,
  donDangLienHe: null,
  donDangSua: null,
  dangSua: false,
  duLieuTaoDon: null,
  dangTaoDon: false,
  phienTuyen: 0,
  bieuDoSoNgay: 7,
  khoaTaoDon: null,        // {json, khoa}: khóa chống trùng gắn với đúng nội dung đã xác nhận
  phienGoiY: { gui: 0, nhan: 0 },
  doiSoat: null,           // kết quả đối soát lần tải gần nhất (xuất CSV)
};

const laQuanLyXem = () => state.vaiTro === "quan_ly";

// ====================================================================
// Tiện ích hiển thị
// ====================================================================

function showToast(type, title, message, duration = 4500) {
  const container = $("toastContainer");
  if (!container) return;
  const icon = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" }[type] || "ℹ️";

  const toast = document.createElement("div");
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div class="toast-content"><div class="toast-title"></div><div class="toast-message"></div></div>
    <button type="button" class="toast-close" title="Đóng">✕</button>`;
  toast.querySelector(".toast-title").textContent = title;
  toast.querySelector(".toast-message").textContent = message;
  toast.querySelector(".toast-close").addEventListener("click", () => toast.remove());
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast-hiding");
    setTimeout(() => toast.remove(), 260);
  }, duration);
}

function dinhDangThoiGian(iso) {
  if (!iso) return "--";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "--";
  const p = n => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function dinhDangNgay(iso) {
  if (!iso) return "--";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "--" : d.toLocaleDateString("vi-VN");
}

function dinhDangTien(so) {
  return `${Number(so || 0).toLocaleString("vi-VN")} đ`;
}

function dinhDangKg(so) {
  return `${Number(so || 0).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} kg`;
}

function soNgayTu(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return isNaN(t) ? null : Math.floor(Math.max(0, Date.now() - t) / 86400000);
}

function ngayISO(d) {
  const p = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function badgeTrangThai(trangThai) {
  const tt = TRANG_THAI[trangThai] || { ten: trangThai, cls: "" };
  return `<span class="badge-status ${tt.cls}">${escapeHtml(tt.ten)}</span>`;
}

function badgeThanhToan(d) {
  return laCod(d)
    ? `<span class="badge-payment cod">🚚 COD${d.da_thu_tien ? " · đã thu" : ""}</span>`
    : '<span class="badge-payment prepaid">💵 Đã trả trước</span>';
}

function telLink(sdt) {
  const s = escapeHtml(sdt || "");
  return s ? `<a class="tel-link" href="tel:${s}">📞 ${s}</a>` : "--";
}

function laCod(d) {
  return d.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra";
}

/** " (D×R×C cm)" khi đủ 3 kích thước, ngược lại chuỗi rỗng. */
function kichThuocHang(d) {
  return d.dai_cm && d.rong_cm && d.cao_cm ? ` (${d.dai_cm}×${d.rong_cm}×${d.cao_cm} cm)` : "";
}

function moTaHang(d) {
  return `${d.ten_loai_hang || "Hàng hóa"} — ${dinhDangKg(d.can_nang_kg)}${kichThuocHang(d)}`;
}

/** Khóa ngẫu nhiên 8–64 ký tự [A-Za-z0-9_-] cho header Idempotency-Key. */
function taoKhoaNgauNhien() {
  if (window.crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = new Uint8Array(16);
  if (window.crypto && crypto.getRandomValues) crypto.getRandomValues(b);
  else b.forEach((_, i) => { b[i] = Math.floor(Math.random() * 256); });
  return Array.from(b, x => x.toString(16).padStart(2, "0")).join("");
}

/** Tải file CSV (UTF-8 có BOM để Excel đọc đúng tiếng Việt). dong: mảng các mảng ô. */
function xuatCsv(tenFile, tieuDe, dong) {
  const thoat = v => {
    let s = v === null || v === undefined ? "" : String(v);
    // SĐT bắt đầu bằng 0: ép Excel giữ nguyên dạng chữ (chuỗi chỉ gồm chữ số nên an toàn).
    if (/^0[0-9]{9,10}$/.test(s)) return `="${s}"`;
    // Chặn CSV/formula injection: ô bắt đầu bằng = + - @ bị Excel hiểu là công thức.
    if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const noiDung = [tieuDe, ...dong].map(r => r.map(thoat).join(",")).join("\r\n");
  const blob = new Blob(["\uFEFF" + noiDung], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = tenFile;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function datText(id, text) {
  const el = $(id);
  if (el) el.textContent = text ?? "";
}

function moModal(id) {
  $(id)?.classList.add("active");
}

function dongModal(id) {
  $(id)?.classList.remove("active");
}

/** In đúng 1 vùng: các phần khác bị ẩn bằng CSS @media print (body.dang-in). */
function inPhanTu(el) {
  if (!el) return;
  document.querySelectorAll(".print-target").forEach(x => x.classList.remove("print-target"));
  el.classList.add("print-target");
  document.body.classList.add("dang-in");
  window.print();
}

window.addEventListener("afterprint", () => {
  document.body.classList.remove("dang-in");
  document.querySelectorAll(".print-target").forEach(x => x.classList.remove("print-target"));
});

/** Thanh phân trang dùng chung (Đơn gửi đi, Hàng đến). Nút mang data-trang — người gọi tự bắt sự kiện click. */
function veThanhPhanTrang(containerId, total, offset) {
  const tongTrang = Math.max(1, Math.ceil(total / SO_DONG_MOI_TRANG));
  const trang = Math.floor(offset / SO_DONG_MOI_TRANG) + 1;
  $(containerId).innerHTML = `
    <div class="pagination-left"><div class="pagination-info">${total ? `Hiển thị <strong>${offset + 1} - ${Math.min(offset + SO_DONG_MOI_TRANG, total)}</strong> / <strong>${total}</strong> đơn` : "0 đơn"}</div></div>
    <div class="pagination-controls">
      <button type="button" class="pagination-btn" data-trang="${trang - 1}" ${trang <= 1 ? "disabled" : ""}>❮ Trước</button>
      <span class="pagination-info">Trang ${trang}/${tongTrang}</span>
      <button type="button" class="pagination-btn" data-trang="${trang + 1}" ${trang >= tongTrang ? "disabled" : ""}>Tiếp ❯</button>
    </div>`;
}

/** Bắt click nút phân trang trong containerId, gọi chonTrang(offsetMoi). */
function ganPhanTrang(containerId, chonTrang) {
  $(containerId).addEventListener("click", e => {
    const btn = e.target.closest("[data-trang]");
    if (!btn || btn.disabled) return;
    chonTrang((Number(btn.dataset.trang) - 1) * SO_DONG_MOI_TRANG);
  });
}

function taoEl(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}

/** Vẽ timeline (hành trình, liên hệ, chỉnh sửa) bằng textContent.
 * chuyenDoi(m) → {gio, ghiChu, tieuDe?}; có tieuDe thì hiện in đậm phía trên ghi chú. */
function veTimeline(ul, ds, chuyenDoi) {
  ul.replaceChildren(...ds.map(m => {
    const { gio, tieuDe, ghiChu } = chuyenDoi(m);
    const li = taoEl("li", "timeline__item");
    const than = tieuDe
      ? taoEl("div", "timeline__body")
      : taoEl("div", "timeline__note", ghiChu);
    if (tieuDe) than.append(taoEl("strong", "", tieuDe), taoEl("div", "timeline__note", ghiChu || ""));
    li.append(taoEl("div", "timeline__time", gio), than);
    return li;
  }));
}

function timelineTrong(ul, thongDiep) {
  ul.replaceChildren(taoEl("li", "timeline__empty", thongDiep));
}

function hienTrangThaiBang(tbodyId, soCot, noiDung, cls = "table-empty") {
  const tbody = $(tbodyId);
  if (tbody) tbody.innerHTML = `<tr><td colspan="${soCot}" class="${cls}">${escapeHtml(noiDung)}</td></tr>`;
}

function phamViQuery() {
  return laQuanLyXem() && state.vanPhongXemId ? { diem_id: state.vanPhongXemId } : {};
}

// ====================================================================
// Điều hướng tab
// ====================================================================

function tabMacDinh() {
  return laQuanLyXem() ? "hang-den" : "tao-don";
}

function chuyenTab(tab) {
  if (!TAB_HOP_LE.includes(tab) || (tab === "tao-don" && laQuanLyXem())) tab = tabMacDinh();
  state.tab = tab;
  try { localStorage.setItem("nhan_vien_gui_hang_active_tab", tab); } catch (_) {}

  document.querySelectorAll(".tab-pane").forEach(p => p.classList.toggle("active", p.id === `tab-${tab}`));
  khoiTaoNav(tab);
  lamMoiTabHienTai();
}

function lamMoiTabHienTai() {
  switch (state.tab) {
    case "tao-don": capNhatSoDonHomNay(); break;
    case "hang-den":
    case "hang-ton": taiHangDen(); break;
    case "don-gui": taiDonGui(); break;
    case "thong-ke": taiThongKe(); break;
  }
}

