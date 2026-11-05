/* thong-ke.js — tab Thống kê & đối soát tiền mặt: chọn kỳ (Ngày / Tháng / Năm / Tùy chọn), tải số liệu, vẽ. */

const SO_NGAY_CHUOI_THEO_NGAY_TOI_DA = 62; // khớp backend: dài hơn thì chia theo tháng
const SO_NAM_CHON = 5;                     // ô Năm: năm nay và 4 năm trước

// ---------------------------------------------------------------- kỳ thống kê (hàm thuần)
const _so2 = n => String(n).padStart(2, "0");
const _utc = iso => { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); };
const _iso = ms => { const t = new Date(ms); return `${t.getUTCFullYear()}-${_so2(t.getUTCMonth() + 1)}-${_so2(t.getUTCDate())}`; };
const _dmy = iso => iso.split("-").reverse().join("/");
const _ngayCuoiThang = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate(); // m: 1..12

function soNgayGiua(tu, den) {
  return Math.round((_utc(den) - _utc(tu)) / 86400000);
}

/** Kỳ từ chế độ + mốc. Tháng/Năm chuẩn hóa theo `tu` (chỉ cần năm/tháng của nó). */
function taoKy(cheDo, tu, den) {
  const [y, m] = tu.split("-").map(Number);
  if (cheDo === "ngay") {
    return { cheDo, tu, den: tu, donVi: "gio", nhan: `Ngày ${_dmy(tu)}`, slug: tu };
  }
  if (cheDo === "thang") {
    const dau = `${y}-${_so2(m)}-01`;
    return { cheDo, tu: dau, den: `${y}-${_so2(m)}-${_so2(_ngayCuoiThang(y, m))}`, donVi: "ngay",
      nhan: `Tháng ${_so2(m)}/${y}`, slug: `${y}-${_so2(m)}` };
  }
  if (cheDo === "nam") {
    return { cheDo, tu: `${y}-01-01`, den: `${y}-12-31`, donVi: "thang", nhan: `Năm ${y}`, slug: String(y) };
  }
  return { cheDo: "tuy_chon", tu, den, donVi: soNgayGiua(tu, den) < SO_NGAY_CHUOI_THEO_NGAY_TOI_DA ? "ngay" : "thang",
    nhan: `${_dmy(tu)} – ${_dmy(den)}`, slug: `${tu}_${den}` };
}

/** Lùi (-1) / tiến (1) một kỳ cùng loại. Tùy chọn thì giữ nguyên. */
function dichKy(ky, buoc) {
  const [y, m] = ky.tu.split("-").map(Number);
  if (ky.cheDo === "ngay") {
    const d = _iso(_utc(ky.tu) + buoc * 86400000);
    return taoKy("ngay", d, d);
  }
  if (ky.cheDo === "thang") {
    const t = new Date(Date.UTC(y, m - 1 + buoc, 1));
    return taoKy("thang", _iso(t.getTime()));
  }
  if (ky.cheDo === "nam") return taoKy("nam", `${y + buoc}-01-01`);
  return ky;
}

/** Kỳ đã chạm tới hôm nay → không cho tiến thêm. */
function kyChuaHomNay(ky) {
  return ky.den >= ngayISO(new Date());
}

/** Mốc (định dạng như API) đang diễn ra lúc này — mốc lớn hơn là tương lai. */
function mocHienTai(donVi) {
  const bay = new Date();
  const ngay = ngayISO(bay);
  if (donVi === "gio") return `${ngay}T${_so2(bay.getHours())}:00`;
  if (donVi === "thang") return `${ngay.slice(0, 7)}-01`;
  return ngay;
}

// ---------------------------------------------------------------- bộ chọn kỳ (giao diện)
function khoiTaoBoChonKy() {
  const namNay = new Date().getFullYear();
  $("tkNam").innerHTML = Array.from({ length: SO_NAM_CHON }, (_, i) => namNay - i)
    .map(n => `<option value="${n}">${n}</option>`).join("");
  datKy(taoKy("thang", ngayISO(new Date())));
}

function datKy(ky) {
  state.ky = ky;
  const homNay = ngayISO(new Date());
  document.querySelectorAll("#tkCheDo [data-che-do]").forEach(b => b.classList.toggle("active", b.dataset.cheDo === ky.cheDo));
  document.querySelectorAll("#tkChonKy [data-o-ky]").forEach(el => { el.hidden = el.dataset.oKy !== ky.cheDo; });
  $("tkNgay").value = ky.tu;
  $("tkNgay").max = homNay;
  $("tkThang").value = ky.tu.slice(0, 7);
  $("tkThang").max = homNay.slice(0, 7);
  $("tkNam").value = ky.tu.slice(0, 4);
  $("tkTuNgay").value = ky.tu;
  $("tkDenNgay").value = ky.den;
  $("tkTuNgay").max = $("tkDenNgay").max = homNay;
  $("tkLui").hidden = $("tkToi").hidden = ky.cheDo === "tuy_chon";
  $("tkToi").disabled = kyChuaHomNay(ky);
}

/** Đổi chế độ: neo vào hôm nay nếu kỳ đang xem chứa hôm nay, không thì neo vào ngày đầu kỳ. */
function doiCheDoKy(cheDo) {
  const ky = state.ky;
  const homNay = ngayISO(new Date());
  const neo = ky.tu <= homNay && homNay <= ky.den ? homNay : ky.tu;
  if (cheDo === "tuy_chon") return taoKy("tuy_chon", ky.tu, ky.den < homNay ? ky.den : homNay);
  return taoKy(cheDo, neo, neo);
}

function chonKy(ky) {
  datKy(ky);
  taiThongKe();
}

// ---------------------------------------------------------------- tải + vẽ
function tenVanPhongDangXem() {
  if (!laQuanLyXem()) return state.vanPhong?.ten || "";
  if (!state.vanPhongXemId) return "Toàn hệ thống";
  const o = $("selectVanPhongXem").selectedOptions[0];
  return o ? o.textContent.trim() : "";
}

async function taiThongKe() {
  const ky = state.ky;
  if (!ky) return;
  if (ky.tu > ky.den) {
    showToast("warning", "Khoảng ngày không hợp lệ", "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
    return;
  }
  const phien = ++state.phienThongKe;
  const q = { tu_ngay: ky.tu, den_ngay: ky.den, ...phamViQuery() };
  const [tk, chuoi, doiSoat] = await Promise.allSettled([
    apiGet(`/gui-hang/thong-ke${taoQuery(q)}`),
    apiGet(`/gui-hang/thong-ke-chuoi${taoQuery({ ...q, don_vi: ky.donVi })}`),
    apiGet(`/gui-hang/doi-soat${taoQuery(q)}`),
  ]);
  if (phien !== state.phienThongKe) return; // đã chọn kỳ khác trong lúc chờ — bỏ kết quả cũ
  const giaTri = r => (r.status === "fulfilled" ? r.value : null);
  const loi = r => (r.status === "rejected" ? r.reason?.message || "Lỗi không xác định" : "");
  state.thongKe = {
    ky,
    tk: giaTri(tk), chuoi: giaTri(chuoi), doiSoat: giaTri(doiSoat),
    loi: { tk: loi(tk), chuoi: loi(chuoi), doiSoat: loi(doiSoat) },
    vanPhong: tenVanPhongDangXem(),
  };
  renderThongKe();
}

function renderThongKe() {
  const s = state.thongKe;
  if (!s) return;
  datText("tkNhanKy", s.ky.nhan);
  datText("tkNhanKyBieuDo", s.ky.nhan);
  if (s.tk) renderSoLieu(s.tk);
  else showToast("error", "Lỗi tải thống kê", s.loi.tk);
  if (s.doiSoat) renderDoiSoat(s.doiSoat);
  else hienTrangThaiBang("tbodyDoiSoat", 5, `Không tải được đối soát: ${s.loi.doiSoat}`);
  veTatCaBieuDo();
}

/** Các biểu đồ của tab: [id khung, hàm vẽ(rong?, container?)] — bản in dùng lại đúng danh sách này. */
const BIEU_DO_THONG_KE = [
  ["bdSanLuong", (...a) => veBieuDoSanLuong(...a)],
  ["bdTienMat", (...a) => veBieuDoTienMat(...a)],
  ["bdCoCauTien", (...a) => veBieuDoCoCau(...a)],
  ["bdTienNhanVien", (...a) => veBieuDoTienNhanVien(...a)],
];

function veTatCaBieuDo() {
  BIEU_DO_THONG_KE.forEach(([id, ve]) => {
    ve();
    theoDoiKichThuoc($(id), () => ve());
  });
}

function renderSoLieu(tk) {
  datText("tkTongGuiDi", tk.tong_don_gui_di);
  datText("tkChoXepXe", tk.so_don_cho_xep_xe);
  datText("tkGuiTrenXe", tk.so_don_gui_dang_tren_xe);
  datText("tkDaHuy", tk.so_don_huy);
  datText("tkTienHoan", dinhDangTien(tk.tien_da_hoan));
  datText("tkTongNhanDen", tk.tong_don_nhan_den);
  datText("tkDaGiao", tk.so_don_da_giao);
  datText("tkSapDen", tk.so_don_sap_den);
  datText("tkChoLay", tk.so_don_cho_lay);
  datText("tkChuaBao", tk.so_don_chua_bao_nguoi_nhan);
  datText("tkCanhBao7", tk.so_don_canh_bao_7_ngay);
  datText("tkTonKho", tk.so_don_ton_kho);
  datText("tkDoanhThu", dinhDangTien(tk.tong_doanh_thu));
  datText("tkTienTraTruoc", dinhDangTien(tk.tien_cuoc_gui_tra_truoc));
  datText("tkTienCod", dinhDangTien(tk.tien_cod_da_thu));
  datText("stat-thong-ke-count", tk.tong_don_gui_di);
}

/** Cấu hình chung cho các biểu đồ theo mốc của kỳ đang xem (null nếu chưa có / lỗi chuỗi). */
function cauHinhMoc() {
  const s = state.thongKe;
  if (!s?.chuoi) return null;
  const hienTai = mocHienTai(s.ky.donVi);
  return {
    chuoi: s.chuoi,
    nhan: s.chuoi.map(x => nhanMoc(x.moc, s.ky.donVi)),
    moc: s.chuoi.map(x => x.moc),
    soMocDaQua: s.chuoi.filter(x => x.moc <= hienTai).length,
    donVi: s.ky.donVi,
  };
}

function veBieuDoSanLuong(rong, container = $("bdSanLuong")) {
  const s = state.thongKe;
  if (!s || !container) return;
  const c = cauHinhMoc();
  if (!c) { khungTrong(container, `Không tải được biểu đồ: ${s.loi.chuoi}`); return; }
  veBieuDoCot(container, {
    nhan: c.nhan, moc: c.moc, soMocDaQua: c.soMocDaQua, chong: false,
    cot: [
      { ten: "Tiếp nhận", lop: "chart-cot--tiep-nhan", giaTri: c.chuoi.map(x => x.tiep_nhan) },
      { ten: "Đã giao", lop: "chart-cot--da-giao", giaTri: c.chuoi.map(x => x.da_giao) },
    ],
    dinhDangTruc: v => String(v),
    tieuDeMoc: i => `${nhanMocDayDu(c.moc[i], c.donVi)}: tiếp nhận ${c.chuoi[i].tiep_nhan}, đã giao ${c.chuoi[i].da_giao}`,
    chuTrong: "Chưa có đơn nào trong kỳ",
  }, typeof rong === "number" ? rong : undefined);
}

function veBieuDoTienMat(rong, container = $("bdTienMat")) {
  const s = state.thongKe;
  if (!s || !container) return;
  const c = cauHinhMoc();
  if (!c) { khungTrong(container, `Không tải được biểu đồ: ${s.loi.chuoi}`); return; }
  veBieuDoCot(container, {
    nhan: c.nhan, moc: c.moc, soMocDaQua: c.soMocDaQua, chong: true,
    cot: [
      { ten: "Trả trước", lop: "chart-cot--tra-truoc", giaTri: c.chuoi.map(x => x.tien_tra_truoc) },
      { ten: "Thu khi giao", lop: "chart-cot--thu-khi-giao", giaTri: c.chuoi.map(x => x.tien_cod) },
    ],
    duong: { ten: "Còn lại", lop: "chart-duong--con-lai", giaTri: c.chuoi.map(x => x.doanh_thu) },
    dinhDangTruc: rutGonTien,
    tieuDeMoc: i => {
      const x = c.chuoi[i];
      return `${nhanMocDayDu(x.moc, c.donVi)}: trả trước ${dinhDangTien(x.tien_tra_truoc)}, thu khi giao ${dinhDangTien(x.tien_cod)}, `
        + `hoàn ${dinhDangTien(x.tien_hoan)}, còn lại ${dinhDangTien(x.doanh_thu)}`;
    },
    chuTrong: "Chưa có khoản thu / hoàn nào trong kỳ",
  }, typeof rong === "number" ? rong : undefined);
}

function veBieuDoCoCau(rong, container = $("bdCoCauTien")) {
  const s = state.thongKe;
  if (!s || !container) return;
  if (!s.tk) { khungTrong(container, `Không tải được biểu đồ: ${s.loi.tk}`); return; }
  const traTruoc = Number(s.tk.tien_cuoc_gui_tra_truoc) || 0, cod = Number(s.tk.tien_cod_da_thu) || 0;
  const tong = traTruoc + cod;
  const nv = s.doiSoat?.nhan_vien || [];
  const soDon = k => nv.reduce((t, x) => t + (Number(x[k]) || 0), 0);
  const phu = (tien, k) => `${dinhDangTien(tien)} · ${tong ? Math.round((tien / tong) * 100) : 0}%`
    + (s.doiSoat ? ` · ${soDon(k)} đơn` : "");
  veBieuDoTron(container, {
    phan: [
      { ten: "Người gửi trả trước", lop: "chart-mau--tra-truoc", giaTri: traTruoc, phu: phu(traTruoc, "so_don_tra_truoc") },
      { ten: "Người nhận trả (thu khi giao)", lop: "chart-mau--thu-khi-giao", giaTri: cod, phu: phu(cod, "so_don_cod") },
    ],
    giua: rutGonTien(tong),
    chuTrong: "Chưa có khoản thu trong kỳ",
  }, typeof rong === "number" ? rong : undefined);
}

const SO_NHAN_VIEN_BIEU_DO_TOI_DA = 10;

/** Hàng của biểu đồ tiền theo nhân viên: giảm dần; quá 10 người thì 9 người đầu + "Khác (n người)". */
function hangTienNhanVien(doiSoat) {
  const hang = doiSoat.nhan_vien
    .map(nv => ({ ten: nv.ho_ten || "(không rõ)", giaTri: Number(nv.tong_tien) || 0 }))
    .sort((a, b) => b.giaTri - a.giaTri);
  if (hang.length <= SO_NHAN_VIEN_BIEU_DO_TOI_DA) return hang;
  const con = hang.slice(SO_NHAN_VIEN_BIEU_DO_TOI_DA - 1);
  return [...hang.slice(0, SO_NHAN_VIEN_BIEU_DO_TOI_DA - 1),
    { ten: `Khác (${con.length} người)`, giaTri: con.reduce((t, h) => t + h.giaTri, 0) }];
}

function veBieuDoTienNhanVien(rong, container = $("bdTienNhanVien")) {
  const s = state.thongKe;
  if (!s || !container) return;
  if (!s.doiSoat) { khungTrong(container, `Không tải được biểu đồ: ${s.loi.doiSoat}`); return; }
  veBieuDoNgang(container, {
    hang: hangTienNhanVien(s.doiSoat),
    dinhDang: dinhDangTien,
    chuTrong: "Không có khoản thu / hoàn nào trong kỳ",
  }, typeof rong === "number" ? rong : undefined);
}

// ---------------------------------------------------------------- đối soát
function xuatCsvDoiSoat() {
  const ds = state.thongKe?.doiSoat;
  if (!ds || !ds.nhan_vien.length) {
    showToast("warning", "Không có dữ liệu", "Không có khoản thu nào trong kỳ để xuất.");
    return;
  }
  xuatCsv(`doi-soat-${ds.tu_ngay}_${ds.den_ngay}.csv`,
    ["Nhân viên", "Số đơn trả trước", "Tiền trả trước (VNĐ)", "Số đơn thu khi giao", "Tiền thu khi giao (VNĐ)",
      "Số đơn hoàn", "Tiền hoàn (VNĐ)", "Tiền mặt còn lại (VNĐ)"],
    [...ds.nhan_vien.map(nv => [nv.ho_ten || "(không rõ)", nv.so_don_tra_truoc, nv.tien_tra_truoc, nv.so_don_cod, nv.tien_cod,
      nv.so_don_hoan, nv.tien_hoan, nv.tong_tien]),
      ["TỔNG", "", "", "", "", "", ds.tong_tien_hoan, ds.tong_tien]]);
}

function renderDoiSoat(doiSoat) {
  const tbody = $("tbodyDoiSoat");
  if (!doiSoat.nhan_vien.length) {
    hienTrangThaiBang("tbodyDoiSoat", 5, "Không có khoản thu / hoàn nào trong kỳ.");
  } else {
    tbody.innerHTML = doiSoat.nhan_vien.map(nv => `
      <tr>
        <td>${escapeHtml(nv.ho_ten || "(không rõ)")}</td>
        <td class="text-right">${escapeHtml(dinhDangTien(nv.tien_tra_truoc))}<div class="cell-sub">${escapeHtml(nv.so_don_tra_truoc)} đơn</div></td>
        <td class="text-right">${escapeHtml(dinhDangTien(nv.tien_cod))}<div class="cell-sub">${escapeHtml(nv.so_don_cod)} đơn</div></td>
        <td class="text-right">${nv.tien_hoan ? `− ${escapeHtml(dinhDangTien(nv.tien_hoan))}` : "0 đ"}<div class="cell-sub">${escapeHtml(nv.so_don_hoan)} đơn</div></td>
        <td class="text-right"><strong>${escapeHtml(dinhDangTien(nv.tong_tien))}</strong></td>
      </tr>`).join("");
  }
  datText("tkDoiSoatHoan", doiSoat.tong_tien_hoan ? `− ${dinhDangTien(doiSoat.tong_tien_hoan)}` : "0 đ");
  datText("tkDoiSoatTong", dinhDangTien(doiSoat.tong_tien));
}
