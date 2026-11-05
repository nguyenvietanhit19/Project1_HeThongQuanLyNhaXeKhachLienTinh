/*
 * Trang "Gán xe" của điều độ viên (UC-44, DIEU_DO_VIEN_THIET_KE_MOI.md): danh sách chu trình (chuyến đi + chuyến về) sắp khởi hành
 * theo ngày, bấm "Gán xe" / "Đổi xe" để chọn xe cho cả chu trình. Dùng chung khung sidebar/CSS/api-client với trang Quản lý.
 * Cần nạp SAU api-client.js, auth-check.js, nav.js, tai-khoan.js.
 */

const MENU_DIEU_DO = [
  {
    label: "Gán xe",
    href: "/nhan-vien/dieu-do/gan-xe.html",
    icon: '<rect x="3" y="5" width="18" height="11" rx="2.5"/><path d="M3 11h18M7 16v3M17 16v3"/><circle cx="7.5" cy="13.5" r="0.8"/><circle cx="16.5" cy="13.5" r="0.8"/>',
  },
];

const MUI_GIO = "Asia/Ho_Chi_Minh";
const TEN_THU_DAY_DU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
const NHAN_TRANG_THAI_GAN = { chua_gan: "Chưa gán xe", mot_phan: "Gán một phần", da_gan: "Đã gán xe" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pad2 = (n) => String(n).padStart(2, "0");

// ---------- Giờ theo múi giờ Việt Nam (không phụ thuộc múi giờ của máy đang mở trang) ----------
function phanGioVN(iso) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", { timeZone: MUI_GIO, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
      .formatToParts(new Date(iso))
      .map((x) => [x.type, x.value])
  );
  return { nam: Number(p.year), thang: Number(p.month), ngay: Number(p.day), gio: Number(p.hour), phut: Number(p.minute) };
}
const gioPhut = (iso) => { const p = phanGioVN(iso); return `${pad2(p.gio)}:${pad2(p.phut)}`; };
// Số ngày giờ kết thúc dự kiến lệch sau ngày khởi hành (0 = cùng ngày), theo giờ Việt Nam
function soNgayLech(batDau, ketThuc) {
  const [y1, m1, d1] = khoaNgay(batDau).split("-").map(Number);
  const [y2, m2, d2] = khoaNgay(ketThuc).split("-").map(Number);
  return Math.round((Date.UTC(y2, m2 - 1, d2) - Date.UTC(y1, m1 - 1, d1)) / 86400000);
}
// "08:00 → 14:00" hoặc "20:00 → 02:00⁺¹" (dấu +1 dạng mũ như trang Lịch chạy, lớp .qua-ngay của style.css); chưa có giờ kết thúc thì chỉ giờ khởi hành
function khoangGio(c) {
  if (!c.gio_ket_thuc) return gioPhut(c.gio_khoi_hanh);
  const lech = soNgayLech(c.gio_khoi_hanh, c.gio_ket_thuc);
  return `${gioPhut(c.gio_khoi_hanh)} → ${gioPhut(c.gio_ket_thuc)}${lech > 0 ? `<em class="qua-ngay">+${lech}</em>` : ""}`;
}
const ngayThang = (iso) => { const p = phanGioVN(iso); return `${pad2(p.ngay)}/${pad2(p.thang)}`; };
const khoaNgay = (iso) => { const p = phanGioVN(iso); return `${p.nam}-${pad2(p.thang)}-${pad2(p.ngay)}`; };

// ---------- Trạng thái trang ----------
let dsChuTrinh = [];
let dsTuyen = []; // tuyến người đăng nhập làm việc được (điều độ viên: tuyến được phân công; quản lý: mọi tuyến)
let locTuyen = ""; // "" = tất cả tuyến của tôi
let locChiChuaGan = false;
const ttTrang = TrangThaiTrang.doc();
let soNgay = ["3", "5", "7"].includes(String(ttTrang.soNgay)) ? String(ttTrang.soNgay) : "3";
locChiChuaGan = ttTrang.chiChuaGan === true;
locTuyen = typeof ttTrang.tuyen === "string" ? ttTrang.tuyen : "";

const gxDs = document.getElementById("gx-ds");

function hienThongBao(noiDung) {
  const el = document.getElementById("gx-thong-bao");
  el.textContent = noiDung;
  el.hidden = false;
  clearTimeout(hienThongBao.hen);
  hienThongBao.hen = setTimeout(() => (el.hidden = true), 5000);
}

// ---------- Danh sách ----------
// Chu trình đang xem sau khi lọc theo tuyến (chưa tính ô "Chưa gán xe")
function chuTrinhTheoTuyen() {
  return locTuyen ? dsChuTrinh.filter((c) => String(c.tuyen_id) === locTuyen) : dsChuTrinh;
}

function renderChips() {
  const theoTuyen = chuTrinhTheoTuyen();
  const chuaGan = theoTuyen.filter((c) => c.trang_thai_gan !== "da_gan").length;
  const o = document.getElementById("loc-chips");
  o.innerHTML = [
    [false, "Tất cả", theoTuyen.length],
    [true, "Chưa gán xe", chuaGan],
  ]
    .map(([gt, nhan, so]) => `<button type="button" class="dd-chip${locChiChuaGan === gt ? " is-active" : ""}" data-chi-chua-gan="${gt}">${nhan} <span>${so}</span></button>`)
    .join("");
  o.querySelectorAll("[data-chi-chua-gan]").forEach((b) =>
    b.addEventListener("click", () => {
      locChiChuaGan = b.dataset.chiChuaGan === "true";
      TrangThaiTrang.luu({ chiChuaGan: locChiChuaGan });
      hienThiDanhSach();
    })
  );
  document.getElementById("stat-chua-gan").textContent = chuaGan;
}

function tieuDeNgay(khoa, soChuTrinh, soChuaGan) {
  const [y, m, d] = khoa.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const homNay = phanGioVN(new Date().toISOString());
  const chenh = Math.round((dt - Date.UTC(homNay.nam, homNay.thang - 1, homNay.ngay)) / 86400000);
  const nhanPhu = chenh === 0 ? "Hôm nay" : chenh === 1 ? "Ngày mai" : "";
  return `
    <div class="cyn-ngay__dau${chenh === 0 ? " cyn-ngay__dau--nay" : ""}">
      <span class="cyn-ngay__so"><b>${pad2(d)}</b><small>Th${m}</small></span>
      <span class="cyn-ngay__ten"><strong>${TEN_THU_DAY_DU[dt.getUTCDay()]}</strong><span>${nhanPhu ? nhanPhu + " · " : ""}${pad2(d)}/${pad2(m)}/${y}</span></span>
      <span class="cyn-ngay__dem">${soChuTrinh} chu trình</span>
      ${soChuaGan ? `<span class="pill pill--nho pill--gia-thoi-han">${soChuaGan} chờ gán xe</span>` : ""}
    </div>`;
}

function dongChuyen(c) {
  const laDi = c.chieu === "xuoi";
  return `
    <div class="gx-chuyen">
      <span class="gx-chieu ${laDi ? "gx-chieu--di" : "gx-chieu--ve"}">${laDi ? "Đi" : "Về"}</span>
      <span class="gx-chuyen__gio"><b>${khoangGio(c)}</b><small>${ngayThang(c.gio_khoi_hanh)}</small></span>
      <span class="gx-chuyen__hanh-trinh">${esc(c.ten_diem_di)} <i aria-hidden="true">→</i> ${esc(c.ten_diem_den)}</span>
      <span class="gx-chuyen__xe">${c.bien_so_xe ? `<span class="xe-bien-so gx-bien-so">${esc(c.bien_so_xe)}</span>` : '<span class="cyn-chua-gan">Chưa gán xe</span>'}</span>
    </div>`;
}

function theChuTrinh(ct) {
  const daGan = ct.trang_thai_gan !== "chua_gan";
  return `
    <article class="gx-ct gx-ct--${ct.trang_thai_gan}">
      <header class="gx-ct__dau">
        <span class="gx-ct__tuyen"><strong>${esc(ct.ten_tuyen)}</strong>${htmlMa(esc(ct.ma_tuyen))}<span class="gx-ct__loai">${esc(ct.ten_loai_xe)}</span></span>
        <span class="pill pill--nho ${ct.trang_thai_gan === "da_gan" ? "pill--gia-vinh-vien" : "pill--gia-thoi-han"}">${NHAN_TRANG_THAI_GAN[ct.trang_thai_gan]}</span>
      </header>
      <div class="gx-ct__chuyen">${ct.cac_chuyen.map(dongChuyen).join("")}</div>
      <footer class="gx-ct__chan">
        <button type="button" class="${daGan ? "nv-btn-secondary" : "btn-primary"} gx-nut-gan" data-chu-trinh="${esc(ct.chu_trinh_id)}">${daGan ? "Đổi xe" : "Gán xe"}</button>
      </footer>
    </article>`;
}

function hienThiDanhSach() {
  renderChips();
  const theoTuyen = chuTrinhTheoTuyen();
  const ds = locChiChuaGan ? theoTuyen.filter((c) => c.trang_thai_gan !== "da_gan") : theoTuyen;
  if (!ds.length) {
    let thongDiep = theoTuyen.length ? "Mọi chu trình đã có xe." : "Không có chu trình nào khởi hành trong khoảng này.";
    if (!dsTuyen.length) {
      thongDiep = nguoiDung.vaiTro === "quan_ly" ? "Chưa có tuyến nào." : "Bạn chưa được phân công phụ trách tuyến nào — hãy liên hệ quản lý để được phân công.";
    }
    gxDs.innerHTML = `<div class="kv-trong">${thongDiep}</div>`;
    return;
  }
  const theoNgay = new Map(); // giữ đúng thứ tự API (đã theo giờ khởi hành)
  ds.forEach((ct) => {
    const khoa = khoaNgay(ct.cac_chuyen[0].gio_khoi_hanh);
    if (!theoNgay.has(khoa)) theoNgay.set(khoa, []);
    theoNgay.get(khoa).push(ct);
  });
  gxDs.innerHTML = [...theoNgay.entries()]
    .map(
      ([khoa, list]) => `
        <section class="cyn-ngay">
          ${tieuDeNgay(khoa, list.length, list.filter((c) => c.trang_thai_gan !== "da_gan").length)}
          <div class="gx-ct-luoi">${list.map(theChuTrinh).join("")}</div>
        </section>`
    )
    .join("");
  gxDs.querySelectorAll("[data-chu-trinh]").forEach((btn) => btn.addEventListener("click", () => moModalGanXe(btn.dataset.chuTrinh)));
}

// Nạp danh sách tuyến cho ô lọc; chỉ hiện ô lọc khi có từ 2 tuyến trở lên
async function taiTuyen() {
  const o = document.getElementById("loc-tuyen");
  try {
    dsTuyen = await apiGet("/dieu-do/tuyen");
  } catch (err) {
    dsTuyen = [];
    console.error("Không tải được danh sách tuyến:", err);
  }
  if (locTuyen && !dsTuyen.some((t) => String(t.id) === locTuyen)) locTuyen = "";
  o.innerHTML = '<option value="">Tất cả tuyến</option>' + dsTuyen.map((t) => `<option value="${esc(t.id)}">${esc(t.ma)} · ${esc(t.ten)}</option>`).join("");
  o.value = locTuyen;
  o.hidden = dsTuyen.length < 2;
}

async function taiDanhSach() {
  gxDs.innerHTML = '<div class="kv-trong">Đang tải...</div>';
  try {
    dsChuTrinh = await apiGet(`/dieu-do/chu-trinh?so_ngay=${soNgay}`);
    hienThiDanhSach();
  } catch (err) {
    gxDs.innerHTML = `<div class="text-error">${esc(err.message)}</div>`;
  }
}

// ---------- Modal chọn xe (gan-xe-modal.js) ----------
function moModalGanXe(chuTrinhId) {
  const ct = dsChuTrinh.find((c) => String(c.chu_trinh_id) === String(chuTrinhId));
  if (!ct) return;
  GanXeModal.mo(ct, {
    khiXong: async (kq) => {
      hienThongBao(`Đã gán xe ${kq.cac_chuyen[0].bien_so_xe || ""} cho cả chuyến đi và chuyến về.`);
      await taiDanhSach();
    },
  });
}

// ---------- Khởi động ----------
const nguoiDung = yeuCauVaiTro("dieu_do_vien", "quan_ly");
if (nguoiDung) {
  const menu = nguoiDung.vaiTro === "quan_ly" ? [...MENU_DIEU_DO, { label: "Về trang quản lý", href: "/nhan-vien/quan-ly/chuyen.html", icon: '<path d="M15 6l-6 6 6 6"/>' }] : MENU_DIEU_DO;
  renderSidebar(document.getElementById("nv-sidebar"), "/nhan-vien/dieu-do/gan-xe.html", menu, "Điều độ");
  const selectCuaSo = document.getElementById("loc-cua-so");
  selectCuaSo.value = soNgay;
  selectCuaSo.addEventListener("change", () => {
    soNgay = selectCuaSo.value;
    TrangThaiTrang.luu({ soNgay });
    taiDanhSach();
  });
  document.getElementById("loc-tuyen").addEventListener("change", (e) => {
    locTuyen = e.target.value;
    TrangThaiTrang.luu({ tuyen: locTuyen });
    hienThiDanhSach();
  });
  taiTuyen().then(taiDanhSach);
}
