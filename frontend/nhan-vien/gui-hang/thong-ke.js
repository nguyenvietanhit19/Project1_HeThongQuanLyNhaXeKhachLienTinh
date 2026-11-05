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
  veBieuDoSanLuong();
  theoDoiKichThuoc($("bdSanLuong"), veBieuDoSanLuong);
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
