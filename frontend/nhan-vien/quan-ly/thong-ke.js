/*
 * Trang Thống kê của quản lý (UC-39, NGHIEP_VU.md mục 8.7 điểm 4) — 7 tab, mỗi tab 1 lần gọi GET /quan-ly/thong-ke/{tab}.
 * Thanh lọc chung: kỳ (Ngày / Tuần / Tháng / Năm / Tùy chọn, ◀ ▶ lùi tiến 1 kỳ) + tuyến. Mỗi số chính so với KỲ TRƯỚC cùng loại
 * (kỳ đang dở thì so với cùng số ngày đã qua của kỳ trước). Tiền tính theo ngày thu, chuyến theo ngày khởi hành — xem
 * backend/app/repositories/thong_ke_quan_ly_repository.py. Mọi bảng trên tab được xuất ra Excel (mỗi bảng 1 trang tính).
 * Cần nạp SAU api-client.js, auth-check.js, nav.js, tai-khoan.js, thong-bao.js, thong-ke-bieu-do.js.
 */

const MUI_GIO = "Asia/Ho_Chi_Minh";
const MAU = {
  s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a", s4: "#eda100",
  tot: "#0ca30c", canh: "#fab219", nghiem: "#ec835a", nguy: "#d03b3b", xam: "#b9b7c4",
};
const esc = BD.esc;
const TAB = [
  { khoa: "tong-quan", ten: "Tổng quan" },
  { khoa: "doanh-thu", ten: "Doanh thu" },
  { khoa: "chuyen", ten: "Chuyến & lấp đầy" },
  { khoa: "ve", ten: "Vé & khách hàng" },
  { khoa: "gui-hang", ten: "Gửi hàng" },
  { khoa: "hoan-tien", ten: "Hoàn tiền" },
  { khoa: "xe-nhan-su", ten: "Xe & nhân sự" },
];
const KIEU_KY = [
  { khoa: "ngay", ten: "Ngày" }, { khoa: "tuan", ten: "Tuần" }, { khoa: "thang", ten: "Tháng" },
  { khoa: "nam", ten: "Năm" }, { khoa: "tuy_chon", ten: "Tùy chọn" },
];
const TEN_THU = ["", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"];
const LY_DO_HOAN = {
  bat_kha_khang_khong_hoan_thanh: "Bất khả kháng, chuyến không hoàn thành",
  loi_nha_xe_giua_duong: "Lỗi nhà xe giữa đường",
  hoan_truoc_gio_chay: "Khách hủy trước giờ chạy",
  tu_dong_hoan_qua_3_tieng: "Tự động hoàn (hoãn quá 3 tiếng)",
};
const TRANG_THAI_CHUYEN = {
  chua_khoi_hanh: "Chưa khởi hành", dang_chay: "Đang chạy", gap_su_co: "Gặp sự cố", hoan_thanh: "Hoàn thành", da_huy: "Đã hủy",
};
const TRANG_THAI_DON = {
  cho_van_chuyen: "Chờ xếp xe", da_len_xe: "Đang trên xe", cho_lay: "Chờ lấy", da_giao: "Đã giao", qua_han_luu_kho: "Quá hạn lưu kho", da_huy: "Đã hủy",
};
const LOAI_SU_CO = { loi_nha_xe: "Lỗi nhà xe", loi_khach_quan: "Khách quan" };
const SU_CO_HANG = { hu_hong: "Hư hỏng", that_lac: "Thất lạc" };
const GIAY_TO = { bang_lai: "Bằng lái", giay_kham_suc_khoe: "Giấy khám sức khỏe" };

// ===================================================================================================================
// Định dạng
// ===================================================================================================================
const so = (n) => Number(n || 0).toLocaleString("vi-VN");
const tien = (n) => `${so(Math.round(Number(n) || 0))} đ`;
function rutGon(n) {
  const v = Number(n) || 0, a = Math.abs(v), dau = v < 0 ? "−" : "";
  if (a >= 1e9) return `${dau}${(a / 1e9).toFixed(1).replace(/\.0$/, "").replace(".", ",")} tỷ`;
  if (a >= 1e6) return `${dau}${(a / 1e6).toFixed(1).replace(/\.0$/, "").replace(".", ",")} tr`;
  if (a >= 1e3) return `${dau}${Math.round(a / 1e3)}k`;
  return `${dau}${a}`;
}
const tyLe = (a, b) => (b ? a / b : null);
const phanTram = (t) => (t == null ? "—" : `${(Math.round(t * 1000) / 10).toLocaleString("vi-VN")}%`);
const pad2 = (n) => String(n).padStart(2, "0");

// ===================================================================================================================
// Ngày (chuỗi ISO "YYYY-MM-DD", tính bằng UTC để không lệch múi giờ máy)
// ===================================================================================================================
const isoTu = (d) => `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}`;
const dateTu = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
const congNgay = (iso, n) => { const d = dateTu(iso); d.setUTCDate(d.getUTCDate() + n); return isoTu(d); };
const soNgayGiua = (a, b) => Math.round((dateTu(b) - dateTu(a)) / 86400000);
const ddmm = (iso) => { const [, m, d] = iso.split("-"); return `${d}/${m}`; };
const ddmmyyyy = (iso) => { const [y, m, d] = iso.split("-"); return `${d}/${m}/${y}`; };
function homNay() {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23" })
    .formatToParts(new Date()).map((x) => [x.type, x.value]));
  return { ngay: `${p.year}-${p.month}-${p.day}`, gio: Number(p.hour) };
}
function gioVN(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("vi-VN", { timeZone: MUI_GIO, hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric" });
}

function tinhKy(kieu, moc) {
  const d = dateTu(moc);
  if (kieu === "ngay") {
    const thu = d.getUTCDay() || 7;
    return { tu: moc, den: moc, nhan: `${TEN_THU[thu]}, ${ddmmyyyy(moc)}` };
  }
  if (kieu === "tuan") {
    const tu = congNgay(moc, -((d.getUTCDay() || 7) - 1));
    const den = congNgay(tu, 6);
    return { tu, den, nhan: `Tuần ${ddmm(tu)} – ${ddmmyyyy(den)}` };
  }
  if (kieu === "thang") {
    const y = d.getUTCFullYear(), m = d.getUTCMonth();
    return { tu: isoTu(new Date(Date.UTC(y, m, 1))), den: isoTu(new Date(Date.UTC(y, m + 1, 0))), nhan: `Tháng ${m + 1}/${y}` };
  }
  const y = d.getUTCFullYear();
  return { tu: `${y}-01-01`, den: `${y}-12-31`, nhan: `Năm ${y}` };
}

function dichMoc(kieu, moc, buoc) {
  const d = dateTu(moc);
  if (kieu === "ngay") return congNgay(moc, buoc);
  if (kieu === "tuan") return congNgay(moc, 7 * buoc);
  if (kieu === "thang") return isoTu(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + buoc, 1)));
  return `${d.getUTCFullYear() + buoc}-01-01`;
}

// ===================================================================================================================
// Trạng thái trang (nhớ trong phiên — TrangThaiTrang ở nav.js)
// ===================================================================================================================
const daLuu = TrangThaiTrang.doc();
const tt = {
  tab: TAB.some((t) => t.khoa === daLuu.tab) ? daLuu.tab : "tong-quan",
  kieu: KIEU_KY.some((k) => k.khoa === daLuu.kieu) ? daLuu.kieu : "thang",
  moc: /^\d{4}-\d{2}-\d{2}$/.test(daLuu.moc || "") ? daLuu.moc : homNay().ngay,
  tuTuyChon: daLuu.tuTuyChon || congNgay(homNay().ngay, -29),
  denTuyChon: daLuu.denTuyChon || homNay().ngay,
  tuyen: daLuu.tuyen || "",
};
let duLieu = null; // dữ liệu tab đang xem (cho xuất Excel)
let BANG = []; // các bảng đang hiển thị — xuất Excel
let lanTai = 0;

function kyDangXem() {
  if (tt.kieu === "tuy_chon") {
    const tu = tt.tuTuyChon <= tt.denTuyChon ? tt.tuTuyChon : tt.denTuyChon;
    const den = tt.tuTuyChon <= tt.denTuyChon ? tt.denTuyChon : tt.tuTuyChon;
    return { tu, den, nhan: `${ddmmyyyy(tu)} – ${ddmmyyyy(den)}`, soSanh: null };
  }
  const ky = tinhKy(tt.kieu, tt.moc);
  const truoc = tinhKy(tt.kieu, dichMoc(tt.kieu, tt.moc, -1));
  const hn = homNay().ngay;
  let denTruoc = truoc.den;
  // Kỳ đang dở: so với đúng số ngày đã qua của kỳ trước (tháng này tới hôm nay ↔ cùng số ngày đầu tháng trước)
  if (ky.tu <= hn && hn <= ky.den) {
    const daQua = congNgay(truoc.tu, soNgayGiua(ky.tu, hn));
    if (daQua < denTruoc) denTruoc = daQua;
  }
  return { ...ky, soSanh: { tu: truoc.tu, den: denTruoc } };
}

// ===================================================================================================================
// Khối giao diện dùng chung
// ===================================================================================================================
/** Thẻ số chính. tot = "tang" (tăng là tốt) | "giam" (giảm là tốt) | null (không đánh giá). laTyLe: so chênh bằng điểm %. */
function theSo({ nhan, gt, cu, hienThi, tot = "tang", phu = "", laTyLe = false, nhanCu, lop = "" }) {
  let delta = "";
  if (cu !== undefined && cu !== null && gt !== null && gt !== undefined) {
    const ky = duLieu?.ky;
    const nhanKyTruoc = ky ? `${ddmm(ky.so_sanh_tu)} – ${ddmmyyyy(ky.so_sanh_den)}` : "";
    const tip = `Kỳ so sánh ${nhanKyTruoc}: ${nhanCu ?? hienThi(cu)}`;
    let chu = "", huong = 0;
    if (laTyLe) {
      const chenh = Math.round((gt - cu) * 1000) / 10;
      huong = Math.sign(chenh);
      chu = chenh === 0 ? "0 điểm %" : `${Math.abs(chenh).toLocaleString("vi-VN")} điểm %`;
    } else if (!cu) {
      huong = gt ? 1 : 0;
      chu = gt ? "mới phát sinh" : "không đổi";
    } else {
      const p = Math.round(((gt - cu) / Math.abs(cu)) * 1000) / 10;
      huong = Math.sign(p);
      chu = `${Math.abs(p).toLocaleString("vi-VN")}%`;
    }
    const danhGia = !tot || huong === 0 ? "trung" : (huong > 0) === (tot === "tang") ? "tot" : "xau";
    const mui = huong > 0 ? "▲" : huong < 0 ? "▼" : "■";
    delta = `<span class="tkq-the__delta tkq-the__delta--${danhGia}" title="${esc(tip)}">${mui} ${esc(chu)}</span>`;
  }
  return `<div class="tkq-the ${lop}">
      <span class="tkq-the__nhan">${esc(nhan)}</span>
      <strong class="tkq-the__so">${gt === null || gt === undefined ? "—" : esc(hienThi(gt))}</strong>
      <span class="tkq-the__duoi">${delta}${phu ? `<small>${esc(phu)}</small>` : ""}</span>
    </div>`;
}

function khoi(tieuDe, noiDung, { rong = false, id = "", phai = "" } = {}) {
  return `<section class="tkq-khoi${rong ? " tkq-khoi--rong" : ""}"${id ? ` id="${id}"` : ""}>
      <header class="tkq-khoi__dau"><h2>${esc(tieuDe)}</h2>${phai}</header>
      ${noiDung}
    </section>`;
}

/**
 * Bảng số liệu + đăng ký để xuất Excel. cot: [{ten, k | fn(r), kieu: "chu" | "so" | "tien" | "pt" | "gio", html?(r)}]
 * kieu "pt": giá trị là tỷ lệ 0..1 (hoặc null).
 */
function bang(ten, cot, dong, { tong = null, gioiHan = 0, trong = "Không có dữ liệu" } = {}) {
  const lay = (c, r) => (c.fn ? c.fn(r) : r[c.k]);
  BANG.push({ ten, cot, dong, tong, lay });
  if (!dong.length) return `<div class="tkq-trong">${esc(trong)}</div>`;
  const oHtml = (c, r) => {
    if (c.html) return c.html(r);
    const v = lay(c, r);
    if (c.kieu === "tien") return esc(tien(v));
    if (c.kieu === "so") return esc(so(v));
    if (c.kieu === "pt") return esc(phanTram(v));
    if (c.kieu === "gio") return esc(gioVN(v));
    return esc(v ?? "—");
  };
  const laSo = (c) => ["tien", "so", "pt"].includes(c.kieu);
  const hien = gioiHan ? dong.slice(0, gioiHan) : dong;
  return `<div class="tkq-bang-cuon"><table class="tkq-bang">
      <thead><tr>${cot.map((c) => `<th class="${laSo(c) ? "so" : ""}">${esc(c.ten)}</th>`).join("")}</tr></thead>
      <tbody>${hien.map((r) => `<tr>${cot.map((c) => `<td class="${laSo(c) ? "so" : ""}">${oHtml(c, r)}</td>`).join("")}</tr>`).join("")}</tbody>
      ${tong ? `<tfoot><tr>${cot.map((c, i) => `<td class="${laSo(c) ? "so" : ""}">${i === 0 ? "Tổng" : tong[c.k] === undefined ? "" : oHtml(c, tong)}</td>`).join("")}</tr></tfoot>` : ""}
    </table></div>${gioiHan && dong.length > gioiHan ? `<div class="tkq-con-nua">và ${so(dong.length - gioiHan)} dòng nữa (có đủ khi xuất Excel)</div>` : ""}`;
}

/** Bảng số liệu của 1 biểu đồ theo thời gian — gập lại, mở khi cần (bản chữ của biểu đồ). */
function bangChuoi(ten, chuoi, cot) {
  const ky = duLieu.ky;
  const dong = chuoi.map((r) => ({ ...r, _moc: nhanMocDayDu(r.moc, ky.don_vi) }));
  return `<details class="tkq-chi-tiet"><summary>Bảng số liệu</summary>${bang(ten, [{ ten: "Thời điểm", k: "_moc" }, ...cot], dong)}</details>`;
}

function chip(nhan, giaTri, muc) {
  const bieuTuong = { nguy: "!", canh: "!", tot: "✓", trung: "•" }[muc] || "•";
  return `<span class="tkq-trang-thai tkq-trang-thai--${muc}"><i>${bieuTuong}</i>${esc(nhan)}: <b>${esc(giaTri)}</b></span>`;
}

// Nhãn mốc trên trục và trong thẻ nổi
function nhanMoc(moc, donVi) {
  const [ngay, gio] = String(moc).split("T");
  const [y, m, d] = ngay.split("-");
  if (donVi === "gio") return `${Number(gio.slice(0, 2))}h`;
  if (donVi === "thang") return `T${Number(m)}`;
  return `${d}/${m}`;
}
function nhanMocDayDu(moc, donVi) {
  const [ngay, gio] = String(moc).split("T");
  const [y, m, d] = ngay.split("-");
  if (donVi === "gio") return `${Number(gio.slice(0, 2))}h ${d}/${m}/${y}`;
  if (donVi === "thang") return `Tháng ${Number(m)}/${y}`;
  const thu = dateTu(ngay).getUTCDay() || 7;
  return `${TEN_THU[thu]}, ${d}/${m}/${y}`;
}
/** Số mốc đã bắt đầu (mốc tương lai để trống trên biểu đồ tiền / vé / hàng). */
function soMocDaQua(chuoi, donVi) {
  const { ngay, gio } = homNay();
  return chuoi.filter((r) => {
    const [d, h] = String(r.moc).split("T");
    if (donVi === "gio") return d < ngay || (d === ngay && Number(h.slice(0, 2)) <= gio);
    return d <= ngay;
  }).length;
}
function cauHinhChuoi(chuoi, rieng) {
  const dv = duLieu.ky.don_vi;
  return {
    nhan: chuoi.map((r) => nhanMoc(r.moc, dv)),
    tieuDeMoc: chuoi.map((r) => nhanMocDayDu(r.moc, dv)),
    soMocDaQua: soMocDaQua(chuoi, dv),
    ...rieng,
  };
}

// ===================================================================================================================
// Tab 1 — Tổng quan
// ===================================================================================================================
function veTongQuan(d) {
  const t = d.tien.hien_tai, tc = d.tien.truoc, c = d.chuyen.hien_tai, cc = d.chuyen.truoc;
  const lapDay = tyLe(c.ghe_ban, c.tong_ghe), lapDayCu = tyLe(cc.ghe_ban, cc.tong_ghe);
  const v = d.viec_can_xu_ly;
  const viec = [
    { so: v.hoan_dang_cho, nhan: "Khoản hoàn tiền đang chờ chuyển", phu: v.hoan_dang_cho ? tien(v.tien_hoan_dang_cho) : "", muc: "nguy", tab: "hoan-tien" },
    { so: v.chuyen_dang_hoan, nhan: "Chuyến đang hoãn (quá giờ chưa có xe)", muc: "nguy", href: "/nhan-vien/dieu-do/gan-xe.html" },
    { so: v.chuyen_gap_su_co, nhan: "Chuyến đang gặp sự cố", muc: "nguy", href: "/nhan-vien/dieu-do/gan-xe.html" },
    { so: v.chuyen_chua_gan_xe, nhan: "Chuyến trong 48 giờ tới chưa gán xe", muc: "canh", href: "/nhan-vien/dieu-do/gan-xe.html" },
    { so: v.hang_qua_han, nhan: "Đơn hàng quá hạn lưu kho", muc: "nguy", href: "/nhan-vien/gui-hang/index.html" },
    { so: v.hang_cho_lau, nhan: "Đơn hàng chờ lấy quá lâu", muc: "canh", href: "/nhan-vien/gui-hang/index.html" },
    { so: v.xe_thieu_nhan_su, nhan: "Xe cố định tuyến thiếu nhân sự", muc: "canh", href: "/nhan-vien/quan-ly/xe.html" },
    { so: v.giay_to_can_gia_han, nhan: "Giấy tờ nhân sự hết / sắp hết hạn", muc: "canh", tab: "xe-nhan-su" },
  ];
  const tongViec = viec.reduce((s, x) => s + (x.so ? 1 : 0), 0);
  const htmlViec = `<ul class="tkq-viec">${viec.map((x) => {
    const muc = x.so ? x.muc : "tot";
    const dich = x.tab ? `data-tab="${x.tab}" href="#"` : `href="${x.href}"`;
    return `<li><a class="tkq-viec__muc tkq-viec__muc--${muc}" ${dich}>
        <i>${x.so ? "!" : "✓"}</i><span>${esc(x.nhan)}${x.phu ? `<small>${esc(x.phu)}</small>` : ""}</span><b>${so(x.so)}</b>
      </a></li>`;
  }).join("")}</ul>`;

  const the = [
    theSo({ nhan: "Doanh thu thuần", gt: t.thuan, cu: tc.thuan, hienThi: rutGon, nhanCu: tien(tc.thuan), phu: tien(t.thuan), lop: "tkq-the--chinh" }),
    theSo({ nhan: "Tiền vé", gt: t.tien_ve, cu: tc.tien_ve, hienThi: rutGon, nhanCu: tien(tc.tien_ve), phu: `${so(t.so_ve_thu)} vé đã thu tiền` }),
    theSo({ nhan: "Cước gửi hàng", gt: t.tien_hang, cu: tc.tien_hang, hienThi: rutGon, nhanCu: tien(tc.tien_hang), phu: `${so(d.hang.hien_tai.don_tao)} đơn nhận gửi` }),
    theSo({ nhan: "Tỷ lệ lấp đầy", gt: lapDay, cu: lapDayCu, hienThi: phanTram, laTyLe: true, phu: `${so(c.ghe_ban)}/${so(c.tong_ghe)} ghế` }),
    theSo({ nhan: "Chuyến đã chạy", gt: c.da_chay, cu: cc.da_chay, hienThi: so, phu: `${so(c.da_huy)} hủy · ${so(c.co_su_co)} sự cố` }),
    theSo({ nhan: "Tiền hoàn", gt: t.tien_hoan, cu: tc.tien_hoan, hienThi: rutGon, nhanCu: tien(tc.tien_hoan), tot: "giam", phu: tien(t.tien_hoan) }),
  ].join("");

  const tuyen = d.theo_tuyen;
  return `
    <div class="tkq-the-luoi">${the}</div>
    <div class="tkq-luoi tkq-luoi--2-1">
      ${khoi("Doanh thu theo thời gian", `<div class="tkq-bd" id="bd-tq-tien"></div>${bangChuoi("Doanh thu theo thời gian", d.chuoi_tien, COT_CHUOI_TIEN)}`)}
      ${khoi("Cần xử lý", htmlViec, { phai: `<span class="tkq-dem${tongViec ? " tkq-dem--nguy" : ""}">${tongViec ? `${tongViec} việc` : "Không có"}</span>` })}
    </div>
    ${khoi("Doanh thu theo tuyến", `<div class="tkq-bd" id="bd-tq-tuyen"></div>
      ${bang("Theo tuyến", [
        { ten: "Tuyến", fn: (r) => `${r.ma} · ${r.ten}` },
        { ten: "Doanh thu thuần", k: "thuan", kieu: "tien" },
        { ten: "Tiền vé", k: "tien_ve", kieu: "tien" },
        { ten: "Cước hàng", k: "tien_hang", kieu: "tien" },
        { ten: "Hoàn", k: "tien_hoan", kieu: "tien" },
        { ten: "Chuyến đã chạy", k: "da_chay", kieu: "so" },
        { ten: "Lấp đầy", fn: (r) => tyLe(r.ghe_ban, r.tong_ghe), kieu: "pt" },
        { ten: "Hủy", k: "da_huy", kieu: "so" },
        { ten: "Sự cố", k: "co_su_co", kieu: "so" },
        { ten: "Đúng giờ", fn: (r) => tyLe(r.dung_gio, r.co_gio_xuat_phat), kieu: "pt" },
      ], tuyen, { tong: tongCot(tuyen, ["thuan", "tien_ve", "tien_hang", "tien_hoan", "da_chay", "da_huy", "co_su_co"]) })}`, { rong: true })}`;
}

const COT_CHUOI_TIEN = [
  { ten: "Tiền vé", k: "tien_ve", kieu: "tien" }, { ten: "Cước hàng", k: "tien_hang", kieu: "tien" },
  { ten: "Tiền hoàn", k: "tien_hoan", kieu: "tien" }, { ten: "Doanh thu thuần", k: "thuan", kieu: "tien" },
];

function tongCot(dong, khoa) {
  return Object.fromEntries(khoa.map((k) => [k, dong.reduce((s, r) => s + (Number(r[k]) || 0), 0)]));
}

function veBieuDoTien(id, chuoi) {
  BD.thoiGian(document.getElementById(id), cauHinhChuoi(chuoi, {
    chong: true,
    chuoi: [
      { ten: "Tiền vé", mau: MAU.s1, giaTri: chuoi.map((r) => r.tien_ve) },
      { ten: "Cước hàng", mau: MAU.s2, giaTri: chuoi.map((r) => r.tien_hang) },
    ],
    dinhDang: tien, dinhDangTruc: rutGon,
    them: (i) => [{ ten: "Tiền hoàn", gt: `− ${tien(chuoi[i].tien_hoan)}` }, { ten: "Doanh thu thuần", gt: tien(chuoi[i].thuan) }],
    chuTrong: "Chưa thu được đồng nào trong kỳ này",
  }));
}

function veSauTongQuan(d) {
  veBieuDoTien("bd-tq-tien", d.chuoi_tien);
  BD.ngang(document.getElementById("bd-tq-tuyen"), {
    hang: d.theo_tuyen.map((r) => ({ ten: `${r.ma} · ${r.ten}`, giaTri: [r.tien_ve, r.tien_hang], them: [{ ten: "Hoàn", gt: tien(r.tien_hoan) }, { ten: "Thuần", gt: tien(r.thuan) }] })),
    doan: [{ ten: "Tiền vé", mau: MAU.s1 }, { ten: "Cước hàng", mau: MAU.s2 }],
    dinhDang: tien, dinhDangNhan: (h) => rutGon(h.ds[0] + h.ds[1]),
  });
}

// ===================================================================================================================
// Tab 2 — Doanh thu
// ===================================================================================================================
function veDoanhThu(d) {
  const t = d.tien.hien_tai, tc = d.tien.truoc;
  const giaTb = t.so_ve_thu ? t.tien_ve / t.so_ve_thu : null;
  const giaTbCu = tc.so_ve_thu ? tc.tien_ve / tc.so_ve_thu : null;
  const the = [
    theSo({ nhan: "Doanh thu thuần", gt: t.thuan, cu: tc.thuan, hienThi: rutGon, nhanCu: tien(tc.thuan), phu: tien(t.thuan), lop: "tkq-the--chinh" }),
    theSo({ nhan: "Tiền vé", gt: t.tien_ve, cu: tc.tien_ve, hienThi: rutGon, nhanCu: tien(tc.tien_ve), phu: tien(t.tien_ve) }),
    theSo({ nhan: "Cước gửi hàng", gt: t.tien_hang, cu: tc.tien_hang, hienThi: rutGon, nhanCu: tien(tc.tien_hang), phu: tien(t.tien_hang) }),
    theSo({ nhan: "Tiền hoàn", gt: t.tien_hoan, cu: tc.tien_hoan, hienThi: rutGon, nhanCu: tien(tc.tien_hoan), tot: "giam", phu: `vé ${tien(t.hoan_ve)} · hàng ${tien(t.hoan_hang)}` }),
    theSo({ nhan: "Giá vé trung bình", gt: giaTb, cu: giaTbCu, hienThi: tien, tot: null, phu: `${so(t.so_ve_thu)} vé` }),
  ].join("");
  return `
    <div class="tkq-the-luoi">${the}</div>
    ${khoi("Doanh thu theo thời gian", `<div class="tkq-bd" id="bd-dt-tien"></div>${bangChuoi("Doanh thu theo thời gian", d.chuoi_tien, COT_CHUOI_TIEN)}`, { rong: true })}
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Nguồn thu", '<div id="bd-dt-nguon"></div>')}
      ${khoi("Phương thức thanh toán", '<div id="bd-dt-pt"></div>')}
    </div>
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Theo tuyến", `<div class="tkq-bd" id="bd-dt-tuyen"></div>${bang("Doanh thu theo tuyến", [
        { ten: "Tuyến", fn: (r) => `${r.ma} · ${r.ten}` }, { ten: "Số vé", k: "so_ve", kieu: "so" },
        { ten: "Tiền vé", k: "tien_ve", kieu: "tien" }, { ten: "Cước hàng", k: "tien_hang", kieu: "tien" },
        { ten: "Hoàn", k: "tien_hoan", kieu: "tien" }, { ten: "Thuần", k: "thuan", kieu: "tien" },
      ], [...d.theo_tuyen].sort((a, b) => b.thuan - a.thuan), { tong: tongCot(d.theo_tuyen, ["so_ve", "tien_ve", "tien_hang", "tien_hoan", "thuan"]) })}`)}
      ${khoi("Theo điểm / văn phòng", `<div class="tkq-bd" id="bd-dt-diem"></div>${bang("Doanh thu theo điểm", [
        { ten: "Điểm", fn: (r) => r.ten }, { ten: "Loại", fn: (r) => (r.loai_diem === "van_phong" ? "Văn phòng" : "Điểm dừng") },
        { ten: "Tiền vé", k: "tien_ve", kieu: "tien" }, { ten: "Cước hàng", k: "tien_hang", kieu: "tien" },
        { ten: "Hoàn", k: "tien_hoan", kieu: "tien" }, { ten: "Thuần", k: "thuan", kieu: "tien" },
      ], [...d.theo_diem].sort((a, b) => b.thuan - a.thuan), { gioiHan: 10 })}`)}
    </div>`;
}

function veSauDoanhThu(d) {
  veBieuDoTien("bd-dt-tien", d.chuoi_tien);
  const kp = d.theo_kenh_pt;
  const cong = (dk) => kp.filter(dk).reduce((s, r) => s + r.so_tien, 0);
  BD.tron(document.getElementById("bd-dt-nguon"), {
    phan: [
      { ten: "Vé trực tuyến", mau: MAU.s1, giaTri: cong((r) => r.loai === "ve" && r.kenh === "truc_tuyen") },
      { ten: "Vé tại quầy", mau: MAU.s2, giaTri: cong((r) => r.loai === "ve" && r.kenh === "tai_quay") },
      { ten: "Vé qua hotline", mau: MAU.s3, giaTri: cong((r) => r.loai === "ve" && r.kenh === "hotline") },
      { ten: "Cước gửi hàng", mau: MAU.s4, giaTri: cong((r) => r.loai === "hang") },
    ],
    giua: { so: rutGon(d.tien.hien_tai.tien_ve + d.tien.hien_tai.tien_hang), nhan: "tổng thu" }, dinhDang: tien,
  });
  BD.tron(document.getElementById("bd-dt-pt"), {
    phan: [
      { ten: "Vé · chuyển khoản", mau: MAU.s1, giaTri: cong((r) => r.loai === "ve" && r.pt === "chuyen_khoan") },
      { ten: "Vé · tiền mặt", mau: MAU.s2, giaTri: cong((r) => r.loai === "ve" && r.pt !== "chuyen_khoan") },
      { ten: "Hàng · người gửi trả trước", mau: MAU.s3, giaTri: cong((r) => r.loai === "hang" && r.pt === "nguoi_gui_tra_truoc") },
      { ten: "Hàng · thu hộ (COD)", mau: MAU.s4, giaTri: cong((r) => r.loai === "hang" && r.pt === "cod_nguoi_nhan_tra") },
    ],
    giua: { so: rutGon(d.tien.hien_tai.tien_ve + d.tien.hien_tai.tien_hang), nhan: "tổng thu" }, dinhDang: tien,
  });
  BD.ngang(document.getElementById("bd-dt-tuyen"), {
    hang: [...d.theo_tuyen].sort((a, b) => b.thuan - a.thuan).map((r) => ({ ten: `${r.ma} · ${r.ten}`, giaTri: [r.tien_ve, r.tien_hang] })),
    doan: [{ ten: "Tiền vé", mau: MAU.s1 }, { ten: "Cước hàng", mau: MAU.s2 }], dinhDang: tien, dinhDangNhan: (h) => rutGon(h.ds[0] + h.ds[1]),
  });
  BD.ngang(document.getElementById("bd-dt-diem"), {
    hang: [...d.theo_diem].sort((a, b) => (b.tien_ve + b.tien_hang) - (a.tien_ve + a.tien_hang)).slice(0, 8)
      .map((r) => ({ ten: r.ten, giaTri: [r.tien_ve, r.tien_hang] })),
    doan: [{ ten: "Tiền vé", mau: MAU.s1 }, { ten: "Cước hàng", mau: MAU.s2 }], dinhDang: tien, dinhDangNhan: (h) => rutGon(h.ds[0] + h.ds[1]),
  });
}

// ===================================================================================================================
// Tab 3 — Chuyến & lấp đầy
// ===================================================================================================================
function veChuyen(d) {
  const c = d.chuyen.hien_tai, cc = d.chuyen.truoc;
  const the = [
    theSo({ nhan: "Tổng số chuyến", gt: c.tong_chuyen, cu: cc.tong_chuyen, hienThi: so, tot: null, phu: `${so(c.chua_khoi_hanh)} chưa khởi hành` }),
    theSo({ nhan: "Đã chạy", gt: c.da_chay, cu: cc.da_chay, hienThi: so, phu: `${so(c.hoan_thanh)} hoàn thành · ${so(c.dang_chay)} đang chạy` }),
    theSo({ nhan: "Tỷ lệ lấp đầy", gt: tyLe(c.ghe_ban, c.tong_ghe), cu: tyLe(cc.ghe_ban, cc.tong_ghe), hienThi: phanTram, laTyLe: true, phu: `${so(c.ghe_ban)}/${so(c.tong_ghe)} ghế`, lop: "tkq-the--chinh" }),
    theSo({ nhan: "Xuất phát đúng giờ", gt: tyLe(c.dung_gio, c.co_gio_xuat_phat), cu: tyLe(cc.dung_gio, cc.co_gio_xuat_phat), hienThi: phanTram, laTyLe: true, phu: `trễ trung bình ${so(c.tre_tb_phut)} phút` }),
    theSo({ nhan: "Bị hủy", gt: c.da_huy, cu: cc.da_huy, hienThi: so, tot: "giam", phu: c.tong_chuyen ? `${phanTram(c.da_huy / c.tong_chuyen)} số chuyến` : "" }),
    theSo({ nhan: "Gặp sự cố", gt: c.co_su_co, cu: cc.co_su_co, hienThi: so, tot: "giam", phu: `${so(c.su_co_nha_xe)} lỗi nhà xe · ${so(c.su_co_khach_quan)} khách quan` }),
  ].join("");
  const dongNhom = (ten) => [
    { ten, fn: (r) => `${r.ma} · ${r.ten}` }, { ten: "Chuyến", k: "tong_chuyen", kieu: "so" }, { ten: "Đã chạy", k: "da_chay", kieu: "so" },
    { ten: "Hủy", k: "da_huy", kieu: "so" }, { ten: "Sự cố", k: "co_su_co", kieu: "so" },
    { ten: "Lấp đầy", fn: (r) => tyLe(r.ghe_ban, r.tong_ghe), kieu: "pt" }, { ten: "Đúng giờ", fn: (r) => tyLe(r.dung_gio, r.co_gio_xuat_phat), kieu: "pt" },
    { ten: "Vé bán (chuyến đã chạy)", k: "so_ve", kieu: "so" }, { ten: "Doanh thu vé", k: "doanh_thu_ve", kieu: "tien" }, { ten: "Đơn hàng chở", k: "so_don_hang", kieu: "so" },
  ];
  const coHoan = c.dang_hoan ? `<div class="tkq-bao">${chip("Chuyến đang hoãn vì quá giờ chưa có xe", so(c.dang_hoan), "nguy")}</div>` : "";
  return `
    <div class="tkq-the-luoi">${the}</div>${coHoan}
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Số chuyến theo thời gian", `<div class="tkq-bd" id="bd-ch-so"></div>`)}
      ${khoi("Tỷ lệ lấp đầy theo thời gian", `<div class="tkq-bd" id="bd-ch-lap-day"></div>`)}
    </div>
    ${bangChuoi("Chuyến theo thời gian", d.chuoi_chuyen.map((r) => ({ ...r, lap_day: tyLe(r.ghe_ban, r.tong_ghe) })), [
      { ten: "Đã chạy", k: "da_chay", kieu: "so" }, { ten: "Có sự cố", k: "chay_co_su_co", kieu: "so" }, { ten: "Bị hủy", k: "da_huy", kieu: "so" },
      { ten: "Chưa khởi hành", k: "chua_khoi_hanh", kieu: "so" }, { ten: "Ghế bán", k: "ghe_ban", kieu: "so" }, { ten: "Tổng ghế", k: "tong_ghe", kieu: "so" },
      { ten: "Lấp đầy", k: "lap_day", kieu: "pt" },
    ])}
    ${khoi("Lấp đầy theo thứ và giờ khởi hành", '<div id="bd-ch-nhiet"></div>', { rong: true })}
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Lấp đầy theo tuyến", '<div class="tkq-bd" id="bd-ch-tuyen"></div>')}
      ${khoi("Lấp đầy theo loại xe", '<div class="tkq-bd" id="bd-ch-loai-xe"></div>')}
    </div>
    ${khoi("Chi tiết theo tuyến", bang("Chuyến theo tuyến", dongNhom("Tuyến"), d.theo_tuyen), { rong: true })}
    ${khoi("Chi tiết theo loại xe", bang("Chuyến theo loại xe", dongNhom("Loại xe"), d.theo_loai_xe), { rong: true })}
    ${khoi("Chuyến bị hủy, gặp sự cố hoặc đang hoãn", bang("Chuyến bất thường", [
      { ten: "Mã chuyến", k: "ma", html: (r) => htmlMa(esc(r.ma)) }, { ten: "Tuyến", fn: (r) => `${r.ma_tuyen} · ${r.ten_tuyen}` },
      { ten: "Khởi hành", k: "gio_khoi_hanh", kieu: "gio" }, { ten: "Xe", fn: (r) => r.bien_so || "Chưa gán" },
      { ten: "Tình trạng", fn: (r) => (r.trang_thai === "chua_khoi_hanh" && r.dang_hoan ? "Đang hoãn" : TRANG_THAI_CHUYEN[r.trang_thai] || r.trang_thai) },
      { ten: "Sự cố", fn: (r) => (r.loai_su_co ? `${LOAI_SU_CO[r.loai_su_co] || r.loai_su_co}${r.ly_do_su_co ? `: ${r.ly_do_su_co}` : ""}` : "") },
      { ten: "Vé liên quan", k: "so_ve", kieu: "so" },
    ], d.bat_thuong, { trong: "Không có chuyến bất thường trong kỳ này" }), { rong: true })}`;
}

function veSauChuyen(d) {
  const ch = d.chuoi_chuyen;
  BD.thoiGian(document.getElementById("bd-ch-so"), cauHinhChuoi(ch, {
    chong: true, soMocDaQua: ch.length,
    chuoi: [
      { ten: "Chạy bình thường", mau: MAU.s1, giaTri: ch.map((r) => r.chay_binh_thuong) },
      { ten: "Chạy có sự cố", mau: MAU.nghiem, giaTri: ch.map((r) => r.chay_co_su_co) },
      { ten: "Bị hủy", mau: MAU.nguy, giaTri: ch.map((r) => r.da_huy) },
      { ten: "Chưa khởi hành", mau: MAU.xam, giaTri: ch.map((r) => r.chua_khoi_hanh) },
    ],
    dinhDang: so, chuTrong: "Không có chuyến nào trong kỳ này",
  }));
  BD.thoiGian(document.getElementById("bd-ch-lap-day"), cauHinhChuoi(ch, {
    kieu: "duong", tran: 100, soMocDaQua: ch.length,
    chuoi: [{ ten: "Lấp đầy", mau: MAU.s1, giaTri: ch.map((r) => (r.tong_ghe ? Math.round((r.ghe_ban / r.tong_ghe) * 1000) / 10 : null)) }],
    dinhDang: (v) => `${v.toLocaleString("vi-VN")}%`, dinhDangTruc: (v) => `${v}%`,
    them: (i) => [{ ten: "Ghế bán / tổng ghế", gt: `${so(ch[i].ghe_ban)} / ${so(ch[i].tong_ghe)}` }, { ten: "Chuyến đã chạy", gt: so(ch[i].da_chay) }],
    chuTrong: "Chưa có chuyến nào chạy trong kỳ này",
  }));
  // Bảng nhiệt: chỉ những giờ khởi hành thực sự có chuyến
  const nh = d.nhiet_thu_gio;
  const gioCo = [...new Set(nh.map((r) => r.gio))].sort((a, b) => a - b);
  const theoO = Object.fromEntries(nh.map((r) => [`${r.thu}-${r.gio}`, r]));
  BD.nhiet(document.getElementById("bd-ch-nhiet"), {
    hang: [1, 2, 3, 4, 5, 6, 7].map((t) => TEN_THU[t]),
    cot: gioCo.map((g) => `${pad2(g)}h`),
    o: (i, j) => {
      const r = theoO[`${i + 1}-${gioCo[j]}`];
      if (!r || !r.tong_ghe) return null;
      const ty = r.ghe_ban / r.tong_ghe;
      return { ty, nhan: phanTram(ty), tip: [{ ten: "Lấp đầy", gt: phanTram(ty) }, { ten: "Ghế bán / tổng", gt: `${so(r.ghe_ban)} / ${so(r.tong_ghe)}` }, { ten: "Số chuyến", gt: so(r.so_chuyen) }] };
    },
    chuTrong: "Chưa có chuyến nào chạy trong kỳ này",
  });
  const ngangLapDay = (id, ds) => BD.ngang(document.getElementById(id), {
    hang: ds.filter((r) => r.tong_ghe).map((r) => ({ ten: `${r.ma} · ${r.ten}`, giaTri: Math.round((r.ghe_ban / r.tong_ghe) * 1000) / 10,
      them: [{ ten: "Ghế bán / tổng", gt: `${so(r.ghe_ban)} / ${so(r.tong_ghe)}` }, { ten: "Chuyến đã chạy", gt: so(r.da_chay) }] }))
      .sort((a, b) => b.giaTri - a.giaTri),
    mau: MAU.s1, tenGiaTri: "Lấp đầy", dinhDang: (v) => `${v.toLocaleString("vi-VN")}%`,
    chuTrong: "Chưa có chuyến nào chạy trong kỳ này",
  });
  ngangLapDay("bd-ch-tuyen", d.theo_tuyen);
  ngangLapDay("bd-ch-loai-xe", d.theo_loai_xe);
}

// ===================================================================================================================
// Tab 4 — Vé & khách hàng (theo ngày khách đặt vé)
// ===================================================================================================================
function veVe(d) {
  const v = d.ve.hien_tai, vc = d.ve.truoc;
  const huy = (x) => tyLe(x.da_huy + x.het_han, x.tong_ve);
  const khongDen = (x) => tyLe(x.khong_den, x.da_len_xe + x.da_xuong_xe + x.khong_den);
  const the = [
    theSo({ nhan: "Vé đã đặt", gt: v.tong_ve, cu: vc.tong_ve, hienThi: so, phu: `${so(v.so_luot_dat)} lượt đặt · ${v.so_luot_dat ? (v.tong_ve / v.so_luot_dat).toFixed(1).replace(".", ",") : 0} vé/lượt` }),
    theSo({ nhan: "Vé đã bán", gt: v.da_ban, cu: vc.da_ban, hienThi: so, phu: tien(v.gia_tri_da_ban), lop: "tkq-the--chinh" }),
    theSo({ nhan: "Tỷ lệ hủy / hết hạn", gt: huy(v), cu: huy(vc), hienThi: phanTram, laTyLe: true, tot: "giam", phu: `${so(v.da_huy)} hủy · ${so(v.het_han)} hết hạn` }),
    theSo({ nhan: "Tỷ lệ không đến", gt: khongDen(v), cu: khongDen(vc), hienThi: phanTram, laTyLe: true, tot: "giam", phu: `${so(v.khong_den)} vé` }),
    theSo({ nhan: "Khách đặt vé", gt: v.so_khach, cu: vc.so_khach, hienThi: so, phu: `${so(v.khach_moi)} tài khoản mới đăng ký` }),
  ].join("");
  return `
    <div class="tkq-the-luoi">${the}</div>
    ${khoi("Vé theo ngày đặt", `<div class="tkq-bd" id="bd-ve-chuoi"></div>${bangChuoi("Vé theo ngày đặt", d.chuoi_ve, [
      { ten: "Đã bán", k: "da_ban", kieu: "so" }, { ten: "Đang giữ chỗ", k: "giu_cho", kieu: "so" },
      { ten: "Hủy / hết hạn", k: "huy_het_han", kieu: "so" }, { ten: "Không đến", k: "khong_den", kieu: "so" },
    ])}`, { rong: true })}
    <div class="tkq-luoi tkq-luoi--3">
      ${khoi("Trạng thái vé", '<div id="bd-ve-tt"></div>')}
      ${khoi("Kênh bán", '<div id="bd-ve-kenh"></div>')}
      ${khoi("Khách hàng", '<div id="bd-ve-khach"></div>')}
    </div>
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Khách đặt trước giờ chạy bao lâu", '<div class="tkq-bd" id="bd-ve-truoc"></div>')}
      ${khoi("Hình thức thanh toán", '<div id="bd-ve-tt-tt"></div>')}
    </div>
    ${khoi("Chặng đi đông khách nhất", bang("Chặng đông khách", [
      { ten: "Điểm đón", k: "diem_don" }, { ten: "Điểm trả", k: "diem_tra" }, { ten: "Vé đã bán", k: "so_ve", kieu: "so" }, { ten: "Giá trị", k: "gia_tri", kieu: "tien" },
    ], d.cap_diem), { rong: true })}
    ${bangAn("Chỉ số vé", [
      ["Vé đã đặt", v.tong_ve], ["Lượt đặt", v.so_luot_dat], ["Đã bán", v.da_ban], ["Giá trị đã bán", v.gia_tri_da_ban], ["Đang giữ chỗ", v.giu_cho],
      ["Đã thanh toán (chưa đi)", v.da_thanh_toan], ["Đã lên xe", v.da_len_xe], ["Đã xuống xe", v.da_xuong_xe], ["Không đến", v.khong_den],
      ["Đã hủy", v.da_huy], ["Hết hạn", v.het_han], ["Kênh trực tuyến", v.kenh_truc_tuyen], ["Kênh tại quầy", v.kenh_tai_quay],
      ["Kênh hotline", v.kenh_hotline], ["Khách có tài khoản", v.khach_tai_khoan], ["Khách vãng lai", v.khach_vang_lai],
      ["Trả ngay", v.tra_ngay], ["Trả tại quầy", v.tra_tai_quay], ["Vé đặt cọc", v.ve_dat_coc], ["Khách đặt vé", v.so_khach], ["Tài khoản mới", v.khach_moi],
    ])}`;
}

/** Bảng chỉ số không hiện (đã có ở thẻ / biểu đồ) nhưng vẫn đưa vào file Excel. */
function bangAn(ten, cap) {
  BANG.push({ ten, cot: [{ ten: "Chỉ số", k: "a" }, { ten: "Giá trị", k: "b", kieu: "so" }], dong: cap.map(([a, b]) => ({ a, b })), lay: (c, r) => r[c.k] });
  return "";
}

function veSauVe(d) {
  const v = d.ve.hien_tai, ch = d.chuoi_ve;
  BD.thoiGian(document.getElementById("bd-ve-chuoi"), cauHinhChuoi(ch, {
    chong: true,
    chuoi: [
      { ten: "Đã bán", mau: MAU.s1, giaTri: ch.map((r) => r.da_ban) },
      { ten: "Đang giữ chỗ", mau: MAU.s2, giaTri: ch.map((r) => r.giu_cho) },
      { ten: "Hủy / hết hạn", mau: MAU.s3, giaTri: ch.map((r) => r.huy_het_han) },
    ],
    dinhDang: so, them: (i) => [{ ten: "Trong đó không đến", gt: so(ch[i].khong_den) }],
    chuTrong: "Chưa có vé nào được đặt trong kỳ này",
  }));
  BD.tron(document.getElementById("bd-ve-tt"), {
    phan: [
      { ten: "Đã bán", mau: MAU.s1, giaTri: v.da_ban },
      { ten: "Đang giữ chỗ", mau: MAU.s2, giaTri: v.giu_cho },
      { ten: "Đã hủy", mau: MAU.s3, giaTri: v.da_huy },
      { ten: "Hết hạn / không đến chưa trả", mau: MAU.s4, giaTri: v.tong_ve - v.da_ban - v.giu_cho - v.da_huy },
    ],
    giua: { so: so(v.tong_ve), nhan: "vé" }, dinhDang: so,
  });
  BD.tron(document.getElementById("bd-ve-kenh"), {
    phan: [
      { ten: "Trực tuyến", mau: MAU.s1, giaTri: v.kenh_truc_tuyen },
      { ten: "Tại quầy", mau: MAU.s2, giaTri: v.kenh_tai_quay },
      { ten: "Hotline", mau: MAU.s3, giaTri: v.kenh_hotline },
    ],
    giua: { so: so(v.da_ban), nhan: "vé đã bán" }, dinhDang: so,
  });
  BD.tron(document.getElementById("bd-ve-khach"), {
    phan: [
      { ten: "Có tài khoản", mau: MAU.s1, giaTri: v.khach_tai_khoan },
      { ten: "Khách vãng lai", mau: MAU.s2, giaTri: v.khach_vang_lai },
    ],
    giua: { so: so(v.da_ban), nhan: "vé đã bán" }, dinhDang: so,
  });
  BD.ngang(document.getElementById("bd-ve-truoc"), {
    hang: [
      { ten: "Dưới 1 ngày", giaTri: v.truoc_duoi_1_ngay }, { ten: "1 – 3 ngày", giaTri: v.truoc_1_3_ngay },
      { ten: "3 – 7 ngày", giaTri: v.truoc_3_7_ngay }, { ten: "Trên 7 ngày", giaTri: v.truoc_tren_7_ngay },
    ].map((h) => ({ ...h, them: [{ ten: "Tỷ trọng", gt: phanTram(tyLe(h.giaTri, v.da_ban)) }] })),
    mau: MAU.s1, tenGiaTri: "Vé đã bán", dinhDang: so, chuTrong: "Chưa có vé bán trong kỳ này",
  });
  BD.tron(document.getElementById("bd-ve-tt-tt"), {
    phan: [
      { ten: "Thanh toán ngay", mau: MAU.s1, giaTri: v.tra_ngay },
      { ten: "Thanh toán tại quầy", mau: MAU.s2, giaTri: v.tra_tai_quay },
    ],
    giua: { so: so(v.da_ban), nhan: "vé đã bán" }, dinhDang: so,
  });
}

// ===================================================================================================================
// Tab 5 — Gửi hàng
// ===================================================================================================================
function veGuiHang(d) {
  const h = d.hang.hien_tai, hc = d.hang.truoc, t = d.tien.hien_tai, tc = d.tien.truoc;
  const the = [
    theSo({ nhan: "Đơn nhận gửi", gt: h.don_tao, cu: hc.don_tao, hienThi: so, phu: `${so(h.tong_kg)} kg · ${so(h.don_cod)} đơn thu hộ` }),
    theSo({ nhan: "Cước đã thu", gt: t.tien_hang, cu: tc.tien_hang, hienThi: rutGon, nhanCu: tien(tc.tien_hang), phu: tien(t.tien_hang), lop: "tkq-the--chinh" }),
    theSo({ nhan: "Đã giao", gt: h.da_giao, cu: hc.da_giao, hienThi: so, phu: h.da_giao ? `giao trung bình sau ${so(h.gio_giao_tb)} giờ` : "" }),
    theSo({ nhan: "Đơn bị hủy", gt: h.da_huy, cu: hc.da_huy, hienThi: so, tot: "giam", phu: `hoàn ${tien(t.hoan_hang)}` }),
    theSo({ nhan: "Sự cố hàng", gt: h.su_co_hang, cu: hc.su_co_hang, hienThi: so, tot: "giam" }),
    theSo({ nhan: "Thu hộ chưa thu", gt: h.tien_cod_chua_thu, hienThi: rutGon, tot: null, phu: `${so(h.cod_chua_thu)} đơn, tính tới hiện tại` }),
  ].join("");
  const hienTai = `<div class="tkq-dai">
      ${chip("Chờ xếp xe", so(h.hien_cho_xep_xe), "trung")}
      ${chip("Đang trên xe", so(h.hien_tren_xe), "trung")}
      ${chip("Chờ người nhận lấy", so(h.hien_cho_lay), "trung")}
      ${chip("Chờ lấy quá lâu", so(h.hien_cho_lau), h.hien_cho_lau ? "canh" : "tot")}
      ${chip("Quá hạn lưu kho", so(h.hien_qua_han), h.hien_qua_han ? "nguy" : "tot")}
    </div>`;
  return `
    <div class="tkq-the-luoi">${the}</div>
    ${khoi("Hàng đang nằm ở đâu (hiện tại)", hienTai, { rong: true })}
    ${khoi("Đơn hàng theo thời gian", `<div class="tkq-bd" id="bd-gh-chuoi"></div>${bangChuoi("Đơn hàng theo thời gian", d.chuoi_hang, [
      { ten: "Nhận gửi", k: "tao", kieu: "so" }, { ten: "Đã giao", k: "giao", kieu: "so" }, { ten: "Bị hủy", k: "huy", kieu: "so" },
    ])}`, { rong: true })}
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Theo văn phòng gửi", `<div class="tkq-bd" id="bd-gh-vp"></div>${bang("Theo văn phòng gửi", [
        { ten: "Văn phòng", k: "ten" }, { ten: "Số đơn", k: "so_don", kieu: "so" }, { ten: "Cước", k: "cuoc", kieu: "tien" },
      ], d.theo_vp_gui, { tong: tongCot(d.theo_vp_gui, ["so_don", "cuoc"]) })}`)}
      ${khoi("Theo văn phòng nhận", `<div class="tkq-bd" id="bd-gh-vp-nhan"></div>${bang("Theo văn phòng nhận", [
        { ten: "Văn phòng", k: "ten" }, { ten: "Số đơn", k: "so_don", kieu: "so" },
      ], d.theo_vp_nhan)}`)}
    </div>
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Loại hàng", `<div id="bd-gh-loai"></div>${bangAn("Theo loại hàng", d.theo_loai_hang.map((r) => [r.ten, r.so_don]))}`)}
      ${khoi("Trạng thái hiện tại của đơn nhận trong kỳ", bang("Theo trạng thái", [
        { ten: "Trạng thái", fn: (r) => TRANG_THAI_DON[r.trang_thai] || r.trang_thai }, { ten: "Số đơn", k: "so_don", kieu: "so" },
        { ten: "Tỷ trọng", fn: (r) => tyLe(r.so_don, h.don_tao), kieu: "pt" },
      ], [...d.theo_trang_thai].sort((a, b) => Object.keys(TRANG_THAI_DON).indexOf(a.trang_thai) - Object.keys(TRANG_THAI_DON).indexOf(b.trang_thai)))
        + (d.su_co_theo_loai.length ? `<div class="tkq-dai tkq-dai--duoi">${d.su_co_theo_loai.map((r) => chip(`Sự cố ${(SU_CO_HANG[r.loai] || r.loai).toLowerCase()}`, so(r.so_vu), "nguy")).join("")}</div>` : ""))}
    </div>`;
}

function veSauGuiHang(d) {
  const ch = d.chuoi_hang;
  BD.thoiGian(document.getElementById("bd-gh-chuoi"), cauHinhChuoi(ch, {
    chuoi: [
      { ten: "Nhận gửi", mau: MAU.s1, giaTri: ch.map((r) => r.tao) },
      { ten: "Đã giao", mau: MAU.s2, giaTri: ch.map((r) => r.giao) },
      { ten: "Bị hủy", mau: MAU.s3, giaTri: ch.map((r) => r.huy) },
    ],
    dinhDang: so, chuTrong: "Không có đơn hàng nào trong kỳ này",
  }));
  BD.ngang(document.getElementById("bd-gh-vp"), {
    hang: d.theo_vp_gui.slice(0, 8).map((r) => ({ ten: r.ten, giaTri: r.so_don, them: [{ ten: "Cước", gt: tien(r.cuoc) }] })),
    mau: MAU.s1, tenGiaTri: "Số đơn", dinhDang: so,
  });
  BD.ngang(document.getElementById("bd-gh-vp-nhan"), {
    hang: d.theo_vp_nhan.slice(0, 8).map((r) => ({ ten: r.ten, giaTri: r.so_don })), mau: MAU.s2, tenGiaTri: "Số đơn", dinhDang: so,
  });
  // Tối đa 4 phần, còn lại gộp "Khác"
  const lh = d.theo_loai_hang;
  const phan = lh.slice(0, lh.length > 4 ? 3 : 4).map((r, i) => ({ ten: r.ten, mau: [MAU.s1, MAU.s2, MAU.s3, MAU.s4][i], giaTri: r.so_don }));
  if (lh.length > 4) phan.push({ ten: "Khác", mau: MAU.s4, giaTri: lh.slice(3).reduce((s, r) => s + r.so_don, 0) });
  BD.tron(document.getElementById("bd-gh-loai"), { phan, giua: { so: so(d.hang.hien_tai.don_tao), nhan: "đơn" }, dinhDang: so, chuTrong: "Không có đơn hàng nào trong kỳ này" });
}

// ===================================================================================================================
// Tab 6 — Hoàn tiền
// ===================================================================================================================
function veHoanTien(d) {
  const h = d.hoan.hien_tai, hc = d.hoan.truoc;
  const choTu = h.cho_lau_nhat_tu ? Math.floor((Date.now() - new Date(h.cho_lau_nhat_tu)) / 86400000) : null;
  const the = [
    theSo({ nhan: "Hoàn vé phát sinh", gt: h.tien_phat_sinh, cu: hc.tien_phat_sinh, hienThi: rutGon, nhanCu: tien(hc.tien_phat_sinh), tot: "giam", phu: `${so(h.phat_sinh)} khoản · ${tien(h.tien_phat_sinh)}` }),
    theSo({ nhan: "Đã hoàn xong", gt: h.tien_da_hoan, cu: hc.tien_da_hoan, hienThi: rutGon, nhanCu: tien(hc.tien_da_hoan), tot: null, phu: `${so(h.da_hoan)} khoản · ${so(h.da_hoan_tu_dong)} tự động` }),
    theSo({ nhan: "Đang chờ chuyển", gt: h.tien_dang_cho, hienThi: rutGon, tot: null, phu: h.dang_cho ? `${so(h.dang_cho)} khoản · lâu nhất ${so(choTu)} ngày` : "không còn khoản nào", lop: h.dang_cho ? "tkq-the--nguy" : "" }),
    theSo({ nhan: "Thời gian chuyển khoản", gt: h.gio_xu_ly_tb || null, cu: hc.gio_xu_ly_tb || null, hienThi: (g) => `${so(g)} giờ`, tot: "giam", phu: "trung bình, khoản hoàn thủ công" }),
    theSo({ nhan: "Hoàn cước hàng", gt: h.tien_hoan_hang, cu: hc.tien_hoan_hang, hienThi: rutGon, nhanCu: tien(hc.tien_hoan_hang), tot: "giam", phu: `${so(h.don_hang_hoan)} đơn hủy` }),
  ].join("");
  return `
    <div class="tkq-the-luoi">${the}</div>
    <div class="tkq-luoi tkq-luoi--2-1">
      ${khoi("Hoàn vé theo thời gian", `<div class="tkq-bd" id="bd-ht-chuoi"></div>${bangChuoi("Hoàn vé theo thời gian", d.chuoi_hoan, [
        { ten: "Phát sinh", k: "phat_sinh", kieu: "tien" }, { ten: "Đã hoàn xong", k: "da_hoan", kieu: "tien" },
      ])}`)}
      ${khoi("Theo lý do", `<div class="tkq-bd" id="bd-ht-ly-do"></div>${bang("Hoàn theo lý do", [
        { ten: "Lý do", fn: (r) => LY_DO_HOAN[r.ly_do] || r.ly_do }, { ten: "Số khoản", k: "so_luot", kieu: "so" },
        { ten: "Số tiền", k: "so_tien", kieu: "tien" }, { ten: "Còn chờ", k: "tien_dang_cho", kieu: "tien" },
      ], d.theo_ly_do)}`)}
    </div>
    ${khoi("Khoản hoàn đang chờ chuyển (mọi thời điểm)", bang("Hoàn đang chờ", [
      { ten: "Mã vé", k: "ma_ve", html: (r) => htmlMa(esc(r.ma_ve)) }, { ten: "Khách", k: "ten_khach" }, { ten: "Điện thoại", k: "sdt_khach" },
      { ten: "Chuyến", k: "ma_chuyen" }, { ten: "Lý do", fn: (r) => LY_DO_HOAN[r.ly_do] || r.ly_do },
      { ten: "Số tiền", k: "so_tien", kieu: "tien" }, { ten: "Phát sinh lúc", k: "thoi_gian_xac_dinh", kieu: "gio" },
      { ten: "Chờ", fn: (r) => `${so(Math.floor((Date.now() - new Date(r.thoi_gian_xac_dinh)) / 86400000))} ngày` },
      { ten: "Tài khoản nhận", fn: (r) => (r.co_tai_khoan_nhan ? "Đã có" : "Chưa có") },
    ], d.dang_cho, { trong: "Không còn khoản hoàn nào đang chờ" }), { rong: true })}`;
}

function veSauHoanTien(d) {
  const ch = d.chuoi_hoan;
  BD.thoiGian(document.getElementById("bd-ht-chuoi"), cauHinhChuoi(ch, {
    chuoi: [
      { ten: "Phát sinh", mau: MAU.s1, giaTri: ch.map((r) => r.phat_sinh) },
      { ten: "Đã hoàn xong", mau: MAU.s2, giaTri: ch.map((r) => r.da_hoan) },
    ],
    dinhDang: tien, dinhDangTruc: rutGon, chuTrong: "Không có khoản hoàn nào trong kỳ này",
  }));
  BD.ngang(document.getElementById("bd-ht-ly-do"), {
    hang: d.theo_ly_do.map((r) => ({ ten: LY_DO_HOAN[r.ly_do] || r.ly_do, giaTri: r.so_tien, them: [{ ten: "Số khoản", gt: so(r.so_luot) }] })),
    mau: MAU.s1, tenGiaTri: "Số tiền", dinhDang: tien, dinhDangNhan: (x) => rutGon(x.ds[0]), chuTrong: "Không có khoản hoàn nào trong kỳ này",
  });
}

// ===================================================================================================================
// Tab 7 — Xe & nhân sự
// ===================================================================================================================
function veXeNhanSu(d) {
  const x = d.xe;
  const dem = (chuc, trangThai) => d.theo_chuc_danh.filter((r) => r.chuc_danh === chuc && r.trang_thai === trangThai).reduce((s, r) => s + r.so_nguoi, 0);
  const gt = d.giay_to_can_gia_han;
  const the = [
    theSo({ nhan: "Xe đang hoạt động", gt: x.hoat_dong, hienThi: so, tot: null, phu: `${so(x.co_dinh_tuyen)} cố định tuyến · ${so(x.du_phong)} dự phòng`, lop: "tkq-the--chinh" }),
    theSo({ nhan: "Xe bảo trì", gt: x.bao_tri, hienThi: so, tot: null, phu: x.ngung_su_dung ? `${so(x.ngung_su_dung)} xe ngừng sử dụng` : "" }),
    theSo({ nhan: "Xe thiếu nhân sự", gt: x.thieu_nhan_su, hienThi: so, tot: null, phu: "không gán được chuyến", lop: x.thieu_nhan_su ? "tkq-the--canh" : "" }),
    theSo({ nhan: "Tài xế đang làm", gt: dem("tai_xe", "dang_lam"), hienThi: so, tot: null, phu: `${so(dem("tai_xe", "da_nghi_viec"))} đã nghỉ việc` }),
    theSo({ nhan: "Phụ xe đang làm", gt: dem("phu_xe", "dang_lam"), hienThi: so, tot: null, phu: `${so(dem("phu_xe", "da_nghi_viec"))} đã nghỉ việc` }),
    theSo({ nhan: "Giấy tờ cần gia hạn", gt: gt.length, hienThi: so, tot: null, phu: `${so(gt.filter((g) => g.da_het_han).length)} đã hết hạn`, lop: gt.length ? "tkq-the--canh" : "" }),
  ].join("");
  const xe = d.hieu_suat_xe;
  return `
    <div class="tkq-the-luoi">${the}</div>
    <div class="tkq-luoi tkq-luoi--2">
      ${khoi("Số chuyến đã chạy theo xe", '<div class="tkq-bd" id="bd-xe-chuyen"></div>')}
      ${khoi("Lấp đầy theo xe", '<div class="tkq-bd" id="bd-xe-lap-day"></div>')}
    </div>
    ${khoi("Hiệu suất từng xe trong kỳ", bang("Hiệu suất xe", [
      { ten: "Biển số", k: "bien_so" }, { ten: "Loại xe", fn: (r) => `${r.ma_loai_xe} · ${r.ten_loai_xe}` },
      { ten: "Tuyến cố định", fn: (r) => r.ma_tuyen || "Dự phòng" },
      { ten: "Trạng thái", fn: (r) => ({ hoat_dong: "Hoạt động", bao_tri: "Bảo trì", ngung_su_dung: "Ngừng sử dụng" }[r.trang_thai] || r.trang_thai) },
      { ten: "Biên chế (TX/PX)", fn: (r) => `${r.so_tai_xe_hieu_luc}/${r.so_phu_xe_hieu_luc}`,
        html: (r) => {
          const thieu = r.ma_tuyen && r.trang_thai === "hoat_dong" && (r.so_tai_xe_hieu_luc < 2 || r.so_phu_xe_hieu_luc < 1);
          return thieu ? chip("Thiếu", `${r.so_tai_xe_hieu_luc}/${r.so_phu_xe_hieu_luc}`, "canh") : esc(`${r.so_tai_xe_hieu_luc}/${r.so_phu_xe_hieu_luc}`);
        } },
      { ten: "Đã chạy", k: "da_chay", kieu: "so" }, { ten: "Sự cố", k: "co_su_co", kieu: "so" },
      { ten: "Lấp đầy", fn: (r) => tyLe(r.ghe_ban, r.tong_ghe), kieu: "pt" }, { ten: "Doanh thu vé", k: "doanh_thu_ve", kieu: "tien" },
      { ten: "Sắp chạy", k: "sap_chay", kieu: "so" },
    ], xe, { tong: tongCot(xe, ["da_chay", "co_su_co", "doanh_thu_ve", "sap_chay"]) }), { rong: true })}
    ${khoi("Giấy tờ hết hạn hoặc hết hạn trong 30 ngày tới", bang("Giấy tờ cần gia hạn", [
      { ten: "Nhân sự", fn: (r) => `${r.ho_ten}${r.ma ? ` (${r.ma})` : ""}` },
      { ten: "Chức danh", fn: (r) => (r.chuc_danh === "tai_xe" ? "Tài xế" : "Phụ xe") },
      { ten: "Giấy tờ", fn: (r) => GIAY_TO[r.loai] || r.loai }, { ten: "Số", k: "so_giay_to" },
      { ten: "Hết hạn", fn: (r) => ddmmyyyy(String(r.ngay_het_han).slice(0, 10)),
        html: (r) => (r.da_het_han ? chip("Đã hết", ddmmyyyy(String(r.ngay_het_han).slice(0, 10)), "nguy") : esc(ddmmyyyy(String(r.ngay_het_han).slice(0, 10)))) },
    ], gt, { trong: "Không có giấy tờ nào cần gia hạn" }), { rong: true })}`;
}

function veSauXeNhanSu(d) {
  const xe = d.hieu_suat_xe.filter((r) => r.da_chay);
  BD.ngang(document.getElementById("bd-xe-chuyen"), {
    hang: xe.slice(0, 12).map((r) => ({ ten: r.bien_so, phu: r.ma_tuyen || "Dự phòng", giaTri: [r.da_chay - r.co_su_co, r.co_su_co] })),
    doan: [{ ten: "Bình thường", mau: MAU.s1 }, { ten: "Có sự cố", mau: MAU.nghiem }], dinhDang: so,
    chuTrong: "Chưa có xe nào chạy trong kỳ này",
  });
  BD.ngang(document.getElementById("bd-xe-lap-day"), {
    hang: xe.filter((r) => r.tong_ghe).map((r) => ({ ten: r.bien_so, phu: r.ma_tuyen || "Dự phòng", giaTri: Math.round((r.ghe_ban / r.tong_ghe) * 1000) / 10 }))
      .sort((a, b) => b.giaTri - a.giaTri).slice(0, 12),
    mau: MAU.s1, tenGiaTri: "Lấp đầy", dinhDang: (v) => `${v.toLocaleString("vi-VN")}%`, chuTrong: "Chưa có xe nào chạy trong kỳ này",
  });
}

const VE_TAB = {
  "tong-quan": [veTongQuan, veSauTongQuan], "doanh-thu": [veDoanhThu, veSauDoanhThu], chuyen: [veChuyen, veSauChuyen],
  ve: [veVe, veSauVe], "gui-hang": [veGuiHang, veSauGuiHang], "hoan-tien": [veHoanTien, veSauHoanTien], "xe-nhan-su": [veXeNhanSu, veSauXeNhanSu],
};

// ===================================================================================================================
// Thanh lọc, tab, tải dữ liệu
// ===================================================================================================================
const oNoiDung = document.getElementById("tkq-noi-dung");

function veThanhLoc() {
  document.getElementById("tkq-kieu").innerHTML = KIEU_KY
    .map((k) => `<button type="button" class="tkq-phan${tt.kieu === k.khoa ? " is-active" : ""}" data-kieu="${k.khoa}">${k.ten}</button>`).join("");
  const ky = kyDangXem();
  const laTuyChon = tt.kieu === "tuy_chon";
  document.getElementById("tkq-dieu-huong").hidden = laTuyChon;
  document.getElementById("tkq-tuy-chon").hidden = !laTuyChon;
  document.getElementById("tkq-nhan-ky").textContent = ky.nhan;
  document.getElementById("tkq-sau").disabled = !laTuyChon && ky.den >= homNay().ngay;
  document.getElementById("tkq-tu").value = tt.tuTuyChon;
  document.getElementById("tkq-den").value = tt.denTuyChon;
  document.getElementById("tkq-tabs").innerHTML = TAB
    .map((t) => `<button type="button" role="tab" class="tkq-tab${tt.tab === t.khoa ? " is-active" : ""}" aria-selected="${tt.tab === t.khoa}" data-tab="${t.khoa}">${t.ten}</button>`).join("");
}

function luu() {
  TrangThaiTrang.luu({ tab: tt.tab, kieu: tt.kieu, moc: tt.moc, tuTuyChon: tt.tuTuyChon, denTuyChon: tt.denTuyChon, tuyen: tt.tuyen });
}

async function tai() {
  veThanhLoc();
  luu();
  const ky = kyDangXem();
  if (soNgayGiua(ky.tu, ky.den) >= 366) {
    oNoiDung.innerHTML = '<div class="tkq-loi">Khoảng thống kê tối đa 1 năm. Hãy chọn lại ngày.</div>';
    return;
  }
  const ma = ++lanTai;
  oNoiDung.classList.add("is-dang-tai");
  if (!duLieu || duLieu._tab !== tt.tab) oNoiDung.innerHTML = '<div class="tkq-trong">Đang tải...</div>';
  const q = new URLSearchParams({ tu_ngay: ky.tu, den_ngay: ky.den });
  if (ky.soSanh) { q.set("so_sanh_tu", ky.soSanh.tu); q.set("so_sanh_den", ky.soSanh.den); }
  if (tt.tuyen) q.set("tuyen_id", tt.tuyen);
  try {
    const d = await apiGet(`/quan-ly/thong-ke/${tt.tab}?${q}`);
    if (ma !== lanTai) return;
    duLieu = { ...d, _tab: tt.tab };
    BANG = [];
    const [veHtml, veSau] = VE_TAB[tt.tab];
    oNoiDung.innerHTML = veHtml(d);
    veSau(d);
  } catch (err) {
    if (ma !== lanTai) return;
    duLieu = null;
    oNoiDung.innerHTML = `<div class="tkq-loi">${esc(err.message)}</div>`;
  } finally {
    if (ma === lanTai) oNoiDung.classList.remove("is-dang-tai");
  }
}

async function napTuyen() {
  const chon = document.getElementById("tkq-tuyen");
  try {
    const ds = await apiGet("/quan-ly/tuyen");
    chon.innerHTML = '<option value="">Tất cả tuyến</option>' + ds.map((t) => `<option value="${esc(t.id)}">${esc(t.ma ? `${t.ma} · ${t.ten}` : t.ten)}</option>`).join("");
    TrangThaiTrang.chonLaiSelect(chon, tt.tuyen);
    if (chon.value !== tt.tuyen) tt.tuyen = "";
  } catch (e) {
    /* vẫn xem được toàn hệ thống */
  }
}

// ===================================================================================================================
// Xuất Excel (SheetJS, chỉ nạp khi bấm — dùng chung file thư viện của trang gửi hàng)
// ===================================================================================================================
function napSheetJS() {
  if (window.XLSX) return Promise.resolve(window.XLSX);
  return new Promise((xong, loi) => {
    const the = document.createElement("script");
    the.src = "/nhan-vien/gui-hang/vendor/xlsx.mini.min.js";
    the.onload = () => (window.XLSX ? xong(window.XLSX) : loi(new Error("Không nạp được thư viện Excel")));
    the.onerror = () => loi(new Error("Không nạp được thư viện Excel"));
    document.head.appendChild(the);
  });
}

function giaTriExcel(c, r, lay) {
  const v = lay(c, r);
  if (c.kieu === "pt") return v == null ? "" : Math.round(v * 1000) / 10;
  if (c.kieu === "tien" || c.kieu === "so") return Number(v) || 0;
  if (c.kieu === "gio") return gioVN(v);
  return v ?? "";
}

async function xuatExcel() {
  if (!duLieu) return;
  const nut = document.getElementById("tkq-xuat");
  nut.disabled = true;
  try {
    const XLSX = await napSheetJS();
    const wb = XLSX.utils.book_new();
    const ky = duLieu.ky;
    const chonTuyen = document.getElementById("tkq-tuyen");
    const tenTab = TAB.find((t) => t.khoa === tt.tab).ten;
    const dau = [
      [`Thống kê — ${tenTab}`],
      ["Kỳ", `${ddmmyyyy(ky.tu_ngay)} – ${ddmmyyyy(ky.den_ngay)}`],
      ["Kỳ so sánh", `${ddmmyyyy(ky.so_sanh_tu)} – ${ddmmyyyy(ky.so_sanh_den)}`],
      ["Tuyến", chonTuyen.options[chonTuyen.selectedIndex]?.text || "Tất cả tuyến"],
      ["Người xuất", localStorage.getItem("ho_ten") || ""],
      ["Thời điểm xuất", new Date().toLocaleString("vi-VN", { timeZone: MUI_GIO })],
      [],
      ["Tiền tính theo ngày thu; hoàn tiền theo ngày phát sinh; chuyến theo ngày khởi hành; tỷ lệ (%) ghi bằng số phần trăm."],
    ];
    // Thẻ số chính đang hiện trên tab
    oNoiDung.querySelectorAll(".tkq-the").forEach((el) => {
      dau.push([el.querySelector(".tkq-the__nhan")?.textContent.trim(), el.querySelector(".tkq-the__so")?.textContent.trim(),
        el.querySelector(".tkq-the__delta")?.textContent.trim() || "", el.querySelector(".tkq-the__duoi small")?.textContent.trim() || ""]);
    });
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(dau), "Tóm tắt");
    const daDung = new Set(["Tóm tắt"]);
    BANG.forEach((b) => {
      let ten = b.ten.replace(/[\\/?*[\]:]/g, " ").slice(0, 31);
      for (let i = 2; daDung.has(ten); i++) ten = `${b.ten.slice(0, 27)} (${i})`;
      daDung.add(ten);
      const hang = [b.cot.map((c) => (c.kieu === "pt" ? `${c.ten} (%)` : c.kieu === "tien" ? `${c.ten} (đ)` : c.ten))];
      b.dong.forEach((r) => hang.push(b.cot.map((c) => giaTriExcel(c, r, b.lay))));
      if (b.tong) hang.push(b.cot.map((c, i) => (i === 0 ? "Tổng" : b.tong[c.k] === undefined ? "" : giaTriExcel(c, b.tong, b.lay))));
      const ws = XLSX.utils.aoa_to_sheet(hang);
      ws["!cols"] = b.cot.map((c, i) => ({ wch: Math.min(40, Math.max(10, ...hang.map((h) => String(h[i] ?? "").length + 2))) }));
      XLSX.utils.book_append_sheet(wb, ws, ten);
    });
    const slug = tt.tab + "_" + ky.tu_ngay + "_" + ky.den_ngay;
    XLSX.writeFile(wb, `thong-ke-${slug}.xlsx`, { compression: true });
  } catch (err) {
    alert(err.message);
  } finally {
    nut.disabled = false;
  }
}

// ===================================================================================================================
// Khởi động
// ===================================================================================================================
const nguoiDung = yeuCauVaiTro("quan_ly");
if (nguoiDung) {
  renderSidebar(document.getElementById("nv-sidebar"), "/nhan-vien/quan-ly/thong-ke.html");
  document.getElementById("tkq-kieu").addEventListener("click", (e) => {
    const nut = e.target.closest("[data-kieu]");
    if (!nut || nut.dataset.kieu === tt.kieu) return;
    tt.kieu = nut.dataset.kieu;
    if (tt.kieu !== "tuy_chon") {
      const hn = homNay().ngay;
      if (tt.moc > hn) tt.moc = hn;
    }
    tai();
  });
  document.getElementById("tkq-truoc").addEventListener("click", () => { tt.moc = dichMoc(tt.kieu, tinhKy(tt.kieu, tt.moc).tu, -1); tai(); });
  document.getElementById("tkq-sau").addEventListener("click", () => {
    const moi = dichMoc(tt.kieu, tinhKy(tt.kieu, tt.moc).tu, 1);
    const hn = homNay().ngay;
    tt.moc = moi > hn ? hn : moi;
    tai();
  });
  document.getElementById("tkq-hom-nay").addEventListener("click", () => { tt.moc = homNay().ngay; tai(); });
  const doiNgay = () => {
    tt.tuTuyChon = document.getElementById("tkq-tu").value || tt.tuTuyChon;
    tt.denTuyChon = document.getElementById("tkq-den").value || tt.denTuyChon;
    tai();
  };
  document.getElementById("tkq-tu").addEventListener("change", doiNgay);
  document.getElementById("tkq-den").addEventListener("change", doiNgay);
  document.getElementById("tkq-tuyen").addEventListener("change", (e) => { tt.tuyen = e.target.value; tai(); });
  document.getElementById("tkq-tabs").addEventListener("click", (e) => {
    const nut = e.target.closest("[data-tab]");
    if (!nut || nut.dataset.tab === tt.tab) return;
    tt.tab = nut.dataset.tab;
    tai();
  });
  // Liên kết "Cần xử lý" trỏ sang tab khác của chính trang này
  oNoiDung.addEventListener("click", (e) => {
    const lk = e.target.closest("a[data-tab]");
    if (!lk) return;
    e.preventDefault();
    tt.tab = lk.dataset.tab;
    tai();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.getElementById("tkq-xuat").addEventListener("click", xuatExcel);
  napTuyen().then(tai);
}
