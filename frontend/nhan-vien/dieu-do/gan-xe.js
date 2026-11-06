/*
 * Trang "Gán xe" của điều độ viên (UC-44, DIEU_DO_VIEN_THIET_KE_MOI.md): danh sách chu trình (chuyến đi + chuyến về) sắp khởi hành
 * theo ngày, bấm "Gán xe" / "Đổi xe" để chọn xe cho cả chu trình. Dùng chung khung sidebar/CSS/api-client với trang Quản lý.
 * Cần nạp SAU api-client.js, auth-check.js, nav.js, tai-khoan.js, menu.js (MENU_DIEU_DO dùng chung với trang Tổng quan).
 */

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
let dsSuCo = []; // chuyến đang gặp sự cố thuộc phạm vi của tôi (GET /dieu-do/su-co)
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
      <span class="gx-chuyen__hanh-trinh">${esc(c.ten_diem_di)} <i aria-hidden="true">→</i> ${esc(c.ten_diem_den)}<small class="gx-chuyen__ma">${htmlMa(esc(c.ma))}</small></span>
      <span class="gx-chuyen__xe">${htmlXeCuaChuyen(c)}</span>
    </div>`;
}

// Biển số xe của chuyến: có xe chạy thay thì hiện xe thay (kèm xe gốc mờ bên dưới), không thì xe gốc, chưa có thì "Chưa gán xe"
function htmlXeCuaChuyen(c) {
  if (c.bien_so_xe_thuc_te) {
    return `<span class="gx-xe-thay"><span class="xe-bien-so gx-bien-so">${esc(c.bien_so_xe_thuc_te)}</span><small>chạy thay ${esc(c.bien_so_xe || "xe gốc")}</small></span>`;
  }
  if (c.bien_so_xe) return `<span class="xe-bien-so gx-bien-so">${esc(c.bien_so_xe)}</span>`;
  return `<span class="cyn-chua-gan${c.dang_hoan ? " cyn-chua-gan--hoan" : ""}">${c.dang_hoan ? "Đang hoãn" : "Chưa gán xe"}</span>`;
}

const NHAN_MUC_DO = { khan: "Khẩn", canh_bao: "Cảnh báo", thong_tin: "Gợi ý" };

// Thời gian còn lại tới giờ khởi hành, dễ đọc: từ 1 ngày trở lên tính theo ngày ("1 ngày 13 giờ"), dưới 1 ngày theo giờ phút ("17 giờ 21 phút").
// Đã quá giờ thì trả { qua: true, chu: "1 giờ 20 phút" } (khoảng đã quá).
function thoiGianConLai(iso) {
  const phutTong = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
  const phut = Math.abs(phutTong);
  const ngay = Math.floor(phut / 1440);
  const gio = Math.floor((phut % 1440) / 60);
  const le = phut % 60;
  let chu;
  if (ngay) chu = `${ngay} ngày${gio ? ` ${gio} giờ` : ""}`;
  else if (gio) chu = `${gio} giờ${le ? ` ${pad2(le)} phút` : ""}`;
  else chu = `${le} phút`;
  return { qua: phutTong < 0, chu };
}

// Dấu đếm nổi bật: "còn 17 giờ 21 phút" / "đã quá 1 giờ 20 phút". Phần tử mang data-han để bộ đếm tự cập nhật không cần tải lại.
function htmlConLai(iso, lop = "") {
  const t = thoiGianConLai(iso);
  return `<span class="gx-han ${t.qua ? "gx-han--qua" : ""} ${lop}" data-han="${esc(iso)}"><small>${t.qua ? "đã quá" : "còn"}</small><b>${t.chu}</b></span>`;
}

function capNhatDemNguoc() {
  document.querySelectorAll("[data-han]").forEach((el) => {
    const t = thoiGianConLai(el.dataset.han);
    el.classList.toggle("gx-han--qua", t.qua);
    el.innerHTML = `<small>${t.qua ? "đã quá" : "còn"}</small><b>${t.chu}</b>`;
  });
}

function htmlCanChuYTrongThe(ct) {
  if (!ct.can_chu_y.length) return "";
  return `<ul class="gx-cc-the">${ct.can_chu_y
    .map((v) => `<li class="gx-cc-the__dong gx-cc-the__dong--${v.muc_do}">${v.gio_khoi_hanh ? htmlConLai(v.gio_khoi_hanh, "gx-han--nho") : ""}<span>${esc(v.noi_dung)}</span></li>`)
    .join("")}</ul>`;
}

// Nút ở chân thẻ theo tình trạng xe của chu trình: chưa gán → Gán xe; có xe gốc → Đổi xe + Thay xe hỏng; đang có xe chạy thay → Đổi xe chạy thay + Trả xe gốc
function htmlNutChuTrinh(ct) {
  const id = esc(ct.chu_trinh_id);
  const coXeGoc = ct.cac_chuyen.some((c) => c.xe_id);
  const coXeThay = ct.cac_chuyen.some((c) => c.xe_thuc_te_id);
  const nut = (hanhDong, nhan, lop) => `<button type="button" class="${lop} gx-nut-gan" data-chu-trinh="${id}" data-hanh-dong="${hanhDong}">${nhan}</button>`;
  if (ct.trang_thai_gan !== "da_gan") return nut("gan", "Gán xe", "btn-primary");
  if (coXeThay) return nut("tra", "Trả về xe gốc", "nv-btn-secondary") + nut("thay", "Đổi xe chạy thay", "nv-btn-secondary");
  return nut("thay", coXeGoc ? "Xe hỏng — xe khác chạy thay" : "Thay xe", "nv-btn-secondary") + nut("gan", "Đổi xe", "nv-btn-secondary");
}

function theChuTrinh(ct) {
  return `
    <article class="gx-ct gx-ct--${ct.trang_thai_gan}${ct.can_chu_y.some((v) => v.muc_do === "khan") ? " gx-ct--khan" : ""}" data-the="${esc(ct.chu_trinh_id)}">
      <header class="gx-ct__dau">
        <span class="gx-ct__tuyen"><strong>${esc(ct.ten_tuyen)}</strong>${htmlMa(esc(ct.ma_tuyen))}<span class="gx-ct__loai">${esc(ct.ten_loai_xe)}</span></span>
        <span class="pill pill--nho ${ct.trang_thai_gan === "da_gan" ? "pill--gia-vinh-vien" : "pill--gia-thoi-han"}">${NHAN_TRANG_THAI_GAN[ct.trang_thai_gan]}</span>
      </header>
      ${htmlCanChuYTrongThe(ct)}
      <div class="gx-ct__chuyen">${ct.cac_chuyen.map(dongChuyen).join("")}</div>
      <footer class="gx-ct__chan">${htmlNutChuTrinh(ct)}</footer>
    </article>`;
}

// ---------- Cần chú ý ----------
// Gom việc cần xử lý của mọi chu trình đang xem (theo bộ lọc tuyến) + sự cố đang xảy ra, khẩn nhất trước.
// Mỗi việc kèm nút hành động ứng với việc đó: thiếu xe → Gán xe; xe hỏng/cảnh báo vị trí → xe khác chạy thay; xe gốc đã sửa → trả về xe gốc.
const HANH_DONG_THEO_VIEC = {
  dang_hoan: ["gan", "Gán xe"],
  chua_gan_sap_toi: ["gan", "Gán xe"],
  xe_hong: ["thay", "Chọn xe thay"],
  xe_thieu_nhan_su: ["thay", "Chọn xe thay"],
  canh_bao_vi_tri: ["thay", "Xem và đổi xe"],
  xe_goc_san_sang: ["tra", "Trả về xe gốc"],
};
const THU_TU_MUC_DO = { khan: 0, canh_bao: 1, thong_tin: 2 };

function gomViecCanChuY() {
  const viec = [];
  chuTrinhTheoTuyen().forEach((ct) => {
    ct.can_chu_y.forEach((v) =>
      viec.push({ muc_do: v.muc_do, ma: v.ma, noi_dung: v.noi_dung, chu_trinh_id: ct.chu_trinh_id, tuyen: ct.ten_tuyen, gio: v.gio_khoi_hanh || ct.cac_chuyen[0].gio_khoi_hanh, ma_chuyen: v.ma_chuyen ? [v.ma_chuyen] : ct.cac_chuyen.map((c) => c.ma) })
    );
  });
  const trongHienTai = new Set(chuTrinhTheoTuyen().map((c) => String(c.chu_trinh_id)));
  dsSuCo
    .filter((s) => !locTuyen || dsChuTrinh.some((c) => String(c.chu_trinh_id) === String(s.chu_trinh_id)) || !s.chu_trinh_id)
    .forEach((s) =>
      viec.push({
        muc_do: "khan",
        ma: "su_co",
        noi_dung: `Chuyến ${s.ma}${s.bien_so_xe ? ` (xe ${s.bien_so_xe})` : ""} đang gặp sự cố${s.loai_su_co === "loi_nha_xe" ? " — lỗi nhà xe" : s.loai_su_co === "loi_khach_quan" ? " — lỗi khách quan" : ""}${s.ly_do_su_co ? `: ${s.ly_do_su_co}` : ""}`,
        chu_trinh_id: s.chu_trinh_id && trongHienTai.has(String(s.chu_trinh_id)) ? s.chu_trinh_id : null,
        tuyen: s.ten_tuyen,
        gio: s.gio_khoi_hanh,
        ma_chuyen: [s.ma],
      })
    );
  return viec.sort((a, b) => THU_TU_MUC_DO[a.muc_do] - THU_TU_MUC_DO[b.muc_do] || new Date(a.gio) - new Date(b.gio));
}

function renderCanChuY() {
  const o = document.getElementById("gx-can-chu-y");
  const viec = gomViecCanChuY();
  o.hidden = !viec.length;
  if (!viec.length) {
    o.innerHTML = "";
    return;
  }
  const soKhan = viec.filter((v) => v.muc_do === "khan").length;
  o.innerHTML = `
    <div class="gx-cc__dau"><strong>Cần chú ý</strong><span class="pill pill--nho ${soKhan ? "pill--gia-het-han" : "pill--gia-thoi-han"}">${viec.length} việc${soKhan ? ` · ${soKhan} khẩn` : ""}</span></div>
    <ul class="gx-cc__ds">
      ${viec
        .map((v) => {
          const hd = v.chu_trinh_id && HANH_DONG_THEO_VIEC[v.ma];
          return `<li class="gx-cc__muc gx-cc__muc--${v.muc_do}${v.chu_trinh_id ? " gx-cc__muc--bam-duoc" : ""}"${v.chu_trinh_id ? ` data-nhay="${esc(v.chu_trinh_id)}" tabindex="0" role="link" title="Bấm để chuyển tới chu trình này"` : ""}>
            <span class="gx-cc__nhan">${NHAN_MUC_DO[v.muc_do]}</span>
            <span class="gx-cc__nd">${esc(v.noi_dung)}<small>${esc(v.tuyen)} · khởi hành ${gioPhut(v.gio)} ${ngayThang(v.gio)} · mã chuyến ${v.ma_chuyen.map((m) => htmlMa(esc(m))).join(" ")}</small></span>
            ${v.ma === "su_co" ? "" : htmlConLai(v.gio, `gx-han--${v.muc_do}`)}
            ${hd ? `<button type="button" class="nv-btn-secondary gx-cc__nut" data-chu-trinh="${esc(v.chu_trinh_id)}" data-hanh-dong="${hd[0]}">${hd[1]}</button>` : ""}
          </li>`;
        })
        .join("")}
    </ul>`;
  o.querySelectorAll("[data-chu-trinh]").forEach((b) =>
    b.addEventListener("click", (e) => {
      e.stopPropagation(); // nút hành động không kích hoạt cả hàng (nhảy tới chu trình)
      lamHanhDong(b.dataset.chuTrinh, b.dataset.hanhDong);
    })
  );
  o.querySelectorAll("[data-nhay]").forEach((hang) => {
    hang.addEventListener("click", () => nhayToiChuTrinh(hang.dataset.nhay));
    hang.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); nhayToiChuTrinh(hang.dataset.nhay); }
    });
  });
}

function hienThiDanhSach() {
  renderChips();
  renderCanChuY();
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
  gxDs.querySelectorAll("[data-chu-trinh]").forEach((btn) => btn.addEventListener("click", () => lamHanhDong(btn.dataset.chuTrinh, btn.dataset.hanhDong || "gan")));
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

// imLang = true: tải lại ngầm (định kỳ) — không hiện "Đang tải...", lỗi thì giữ nguyên màn hình cũ
async function taiDanhSach(imLang = false) {
  if (!imLang) gxDs.innerHTML = '<div class="kv-trong">Đang tải...</div>';
  try {
    const [chuTrinh, suCo] = await Promise.all([
      apiGet(`/dieu-do/chu-trinh?so_ngay=${soNgay}`),
      apiGet("/dieu-do/su-co").catch(() => []), // sự cố chỉ là phần thêm: lỗi thì vẫn hiện danh sách chu trình
    ]);
    dsChuTrinh = chuTrinh;
    dsSuCo = suCo;
    hienThiDanhSach();
  } catch (err) {
    if (!imLang) gxDs.innerHTML = `<div class="text-error">${esc(err.message)}</div>`;
  }
}

// ---------- Modal chọn xe (gan-xe-modal.js) ----------
function lamHanhDong(chuTrinhId, hanhDong) {
  const ct = dsChuTrinh.find((c) => String(c.chu_trinh_id) === String(chuTrinhId));
  if (!ct) return;
  if (hanhDong === "tra") return traXeGoc(ct);
  const cheDo = hanhDong === "thay" ? "thay" : "gan";
  GanXeModal.mo(ct, {
    cheDo,
    khiXong: async (kq) => {
      const c = kq.cac_chuyen.find((x) => x.xe_id) || kq.cac_chuyen[0];
      hienThongBao(
        cheDo === "thay"
          ? `Đã cho xe ${c.bien_so_xe_thuc_te || ""} chạy thay các chuyến chưa khởi hành của chu trình; khách có vé đã được báo.`
          : `Đã gán xe ${c.bien_so_xe || ""} cho cả chuyến đi và chuyến về.`
      );
      await taiDanhSach(true);
    },
  });
}

// UC-20 nửa sau: xe gốc đã sửa xong → các chuyến chưa khởi hành chạy lại bằng xe gốc
async function traXeGoc(ct) {
  const goc = ct.cac_chuyen.find((c) => c.xe_thuc_te_id);
  if (!goc || !confirm(`Trả chu trình này về xe gốc ${goc.bien_so_xe || ""}? Xe ${goc.bien_so_xe_thuc_te || "đang chạy thay"} sẽ thôi chạy thay các chuyến chưa khởi hành.`)) return;
  try {
    await apiDelete(`/dieu-do/chu-trinh/${encodeURIComponent(ct.chu_trinh_id)}/xe-thay-the`);
    hienThongBao(`Đã trả chu trình về xe gốc ${goc.bien_so_xe || ""}.`);
    await taiDanhSach(true);
  } catch (err) {
    hienThongBao(err.message);
  }
}

// ---------- Nhảy tới một chu trình (bấm thông báo: /gan-xe.html?chu_trinh=<id>) ----------
// Cuộn tới thẻ và làm nổi bật vài giây. Thẻ đang bị bộ lọc ẩn thì bỏ lọc; ngoài cửa sổ đang xem thì mở rộng lên 7 ngày rồi thử lại.
function idChuTrinhTuUrl(search) {
  return new URLSearchParams(search).get("chu_trinh");
}

async function nhayToiChuTrinh(id) {
  if (!id) return;
  const tim = () => [...gxDs.querySelectorAll("[data-the]")].find((e) => e.dataset.the === id);
  if (!dsChuTrinh.some((c) => String(c.chu_trinh_id) === id) && soNgay !== String(CUA_SO_TOI_DA_NGAY)) {
    soNgay = String(CUA_SO_TOI_DA_NGAY);
    document.getElementById("loc-cua-so").value = soNgay;
    TrangThaiTrang.luu({ soNgay });
    await taiDanhSach(true);
  }
  const ct = dsChuTrinh.find((c) => String(c.chu_trinh_id) === id);
  if (!ct) {
    hienThongBao("Chu trình trong thông báo không còn trong danh sách (đã khởi hành, hoặc không thuộc tuyến bạn phụ trách).");
    return;
  }
  if (!tim()) {
    // bị lọc ẩn: bỏ lọc tuyến/"chưa gán xe" để thẻ hiện ra
    locTuyen = "";
    locChiChuaGan = false;
    document.getElementById("loc-tuyen").value = "";
    hienThiDanhSach();
  }
  const the = tim();
  if (!the) return;
  the.scrollIntoView({ block: "center", behavior: "smooth" });
  the.classList.remove("gx-ct--chon");
  void the.offsetWidth; // chạy lại hiệu ứng nếu đang nổi bật
  the.classList.add("gx-ct--chon");
  setTimeout(() => the.classList.remove("gx-ct--chon"), 4000);
}

// ---------- Khởi động ----------
const CUA_SO_TOI_DA_NGAY = 7;
const nguoiDung = yeuCauVaiTro("dieu_do_vien", "quan_ly");
if (nguoiDung) {
  renderSidebar(document.getElementById("nv-sidebar"), "/nhan-vien/dieu-do/gan-xe.html", menuDieuDoCho(nguoiDung.vaiTro), "Điều độ");
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
  taiTuyen().then(() => taiDanhSach()).then(() => {
    const id = idChuTrinhTuUrl(location.search);
    if (id) {
      nhayToiChuTrinh(id);
      history.replaceState(null, "", location.pathname); // tải lại trang không nhảy lần nữa
    }
  });
  // Bấm thông báo của chính trang này (chuông gọi pushState rồi phát sự kiện) — không tải lại trang
  window.addEventListener("nv-duong-dan-doi", (e) => {
    const id = idChuTrinhTuUrl(e.detail.search);
    if (id) {
      nhayToiChuTrinh(id);
      history.replaceState(null, "", location.pathname);
    }
  });
  // Làm mới ngầm mỗi phút và khi quay lại tab: việc "Cần chú ý" đổi theo thời gian (còn ≤48/6 giờ, quá giờ → đang hoãn) và theo người khác thao tác
  setInterval(() => { if (!document.hidden) taiDanhSach(true); }, 60000);
  setInterval(capNhatDemNguoc, 20000); // đếm lùi giữa hai lần tải lại
  document.addEventListener("visibilitychange", () => { if (!document.hidden) taiDanhSach(true); });
}
