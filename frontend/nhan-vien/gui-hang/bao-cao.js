/* bao-cao.js — xuất Excel và in báo cáo của tab Thống kê.
   Cả hai dùng lại đúng dữ liệu đang hiện trên tab (state.thongKe), không gọi API lại. */

const DUONG_DAN_THU_VIEN_EXCEL = "vendor/xlsx.mini.min.js"; // SheetJS CE 0.20.3, chỉ nạp khi bấm Xuất Excel
const RONG_BIEU_DO_IN = 680;                                 // vừa khổ A4 dọc (lề 12mm)
const DINH_DANG_TIEN_EXCEL = "#,##0";

// Nhãn giống hệt trên tab. (*) = chỉ số tồn, tính tại thời điểm xem / xuất, không theo kỳ.
const CHI_SO_GUI_DI = [
  ["tong_don_gui_di", "Đơn tiếp nhận trong kỳ"],
  ["so_don_huy", "Hủy trong kỳ"],
  ["so_don_cho_xep_xe", "Đang chờ xếp xe (*)"],
  ["so_don_gui_dang_tren_xe", "Đang trên xe (*)"],
];
const CHI_SO_NHAN_VE = [
  ["tong_don_nhan_den", "Tới văn phòng trong kỳ"],
  ["so_don_da_giao", "Đã giao trong kỳ"],
  ["so_don_sap_den", "Sắp đến (*)"],
  ["so_don_cho_lay", "Chờ người nhận lấy (*)"],
  ["so_don_chua_bao_nguoi_nhan", "Chưa gọi báo được (*)"],
  ["so_don_canh_bao_7_ngay", "Chờ quá 7 ngày (*)"],
  ["so_don_ton_kho", "Hàng tồn (>14 ngày) (*)"],
];
const CHI_SO_TIEN = [
  ["tien_cuoc_gui_tra_truoc", "Cước người gửi trả trước"],
  ["tien_cod_da_thu", "Cước người nhận trả (thu khi giao)"],
  ["tien_da_hoan", "Đã hoàn khi hủy đơn"],
  ["tong_doanh_thu", "Tiền mặt còn lại"],
];
const COT_CHUOI = ["tiep_nhan", "da_giao", "so_huy", "tien_tra_truoc", "tien_cod", "tien_hoan", "doanh_thu"];
const TIEU_DE_CHUOI = ["Mốc", "Tiếp nhận", "Đã giao", "Hủy", "Trả trước (VNĐ)", "Thu khi giao (VNĐ)", "Hoàn (VNĐ)", "Còn lại (VNĐ)"];
const COT_DOI_SOAT = ["so_don_tra_truoc", "tien_tra_truoc", "so_don_cod", "tien_cod", "so_don_hoan", "tien_hoan", "tong_tien"];
const TIEU_DE_DOI_SOAT = ["Nhân viên", "Số đơn trả trước", "Tiền trả trước (VNĐ)", "Số đơn thu khi giao", "Tiền thu khi giao (VNĐ)",
  "Số đơn hoàn", "Tiền hoàn (VNĐ)", "Tiền mặt còn lại (VNĐ)"];
const GHI_CHU_CHI_SO_TON = "(*) Đang chờ / trên xe / sắp đến / chờ lấy / chưa báo / chờ quá 7 ngày / tồn: tính tại thời điểm xuất, không theo kỳ.";
const TEN_TRANG_CHUOI = { gio: "Theo giờ", ngay: "Theo ngày", thang: "Theo tháng" };

function duDuLieuBaoCao() {
  const s = state.thongKe;
  if (s && s.tk && s.chuoi && s.doiSoat) return true;
  showToast("warning", "Chưa đủ dữ liệu", "Chưa đủ dữ liệu của kỳ để xuất — tải lại thống kê.");
  return false;
}

function thoiDiemHienTai() {
  const d = new Date();
  return `${_dmy(ngayISO(d))} ${_so2(d.getHours())}:${_so2(d.getMinutes())}`;
}

// ---------------------------------------------------------------- Excel
let _huaThuVienExcel = null;

function taiThuVienExcel() {
  if (window.XLSX) return Promise.resolve(window.XLSX);
  if (!_huaThuVienExcel) {
    _huaThuVienExcel = new Promise((xong, loi) => {
      const the = document.createElement("script");
      the.src = DUONG_DAN_THU_VIEN_EXCEL;
      the.onload = () => (window.XLSX ? xong(window.XLSX) : loi(new Error("thư viện không khởi tạo")));
      the.onerror = () => loi(new Error("không tải được file thư viện"));
      document.head.appendChild(the);
    }).catch(err => { _huaThuVienExcel = null; throw err; });
  }
  return _huaThuVienExcel;
}

/** Ô tiền: số thật, định dạng phân cách nghìn. Chuỗi luôn là ô chữ (t: "s") — không bao giờ thành công thức. */
const _oTien = v => ({ t: "n", v: Number(v) || 0, z: DINH_DANG_TIEN_EXCEL });
const _oChu = v => ({ t: "s", v: String(v ?? "") });
const _laTien = k => k.startsWith("tien") || k === "doanh_thu" || k === "tong_doanh_thu" || k === "tong_tien";
const _o = (k, v) => (_laTien(k) ? _oTien(v) : { t: "n", v: Number(v) || 0 });

function _trangTinh(XLSX, dong, rongCot) {
  const ws = XLSX.utils.aoa_to_sheet(dong.map(d => d.map(o => (o && typeof o === "object" ? o : (typeof o === "number" ? { t: "n", v: o } : _oChu(o))))));
  ws["!cols"] = rongCot.map(wch => ({ wch }));
  return ws;
}

/** Dựng workbook 3 trang tính từ dữ liệu đang hiện. Tách khỏi việc tải file để kiểm thử được. */
function taoWorkbookThongKe(XLSX, s, nguoiXuat, thoiDiem) {
  const { ky, tk, chuoi, doiSoat } = s;
  const wb = XLSX.utils.book_new();

  const nhom = (ten, ds) => [[_oChu(ten)], ...ds.map(([k, nhan]) => [_oChu(nhan), _o(k, tk[k])])];
  XLSX.utils.book_append_sheet(wb, _trangTinh(XLSX, [
    ["BÁO CÁO GỬI HÀNG"],
    ["Văn phòng", s.vanPhong],
    ["Kỳ", ky.nhan],
    ["Từ ngày", _dmy(ky.tu)],
    ["Đến ngày", _dmy(ky.den)],
    ["Người xuất", nguoiXuat],
    ["Thời điểm xuất", thoiDiem],
    [],
    ...nhom("HÀNG GỬI ĐI", CHI_SO_GUI_DI),
    ...nhom("HÀNG NHẬN VỀ", CHI_SO_NHAN_VE),
    ...nhom("TIỀN MẶT THU TẠI QUẦY (VNĐ)", CHI_SO_TIEN),
    [],
    [GHI_CHU_CHI_SO_TON],
  ], [38, 30]), "Tổng quan");

  const tongChuoi = COT_CHUOI.map(k => chuoi.reduce((t, x) => t + (Number(x[k]) || 0), 0));
  XLSX.utils.book_append_sheet(wb, _trangTinh(XLSX, [
    TIEU_DE_CHUOI,
    ...chuoi.map(x => [_oChu(nhanMocDayDu(x.moc, ky.donVi)), ...COT_CHUOI.map(k => _o(k, x[k]))]),
    [_oChu("TỔNG"), ...COT_CHUOI.map((k, i) => _o(k, tongChuoi[i]))],
  ], [16, 11, 10, 8, 16, 18, 14, 16]), TEN_TRANG_CHUOI[ky.donVi]);

  const tongNv = COT_DOI_SOAT.map(k => doiSoat.nhan_vien.reduce((t, nv) => t + (Number(nv[k]) || 0), 0));
  XLSX.utils.book_append_sheet(wb, _trangTinh(XLSX, [
    TIEU_DE_DOI_SOAT,
    ...doiSoat.nhan_vien.map(nv => [_oChu(nv.ho_ten || "(không rõ)"), ...COT_DOI_SOAT.map(k => _o(k, nv[k]))]),
    [_oChu("TỔNG"), ...COT_DOI_SOAT.map((k, i) => _o(k, tongNv[i]))],
  ], [28, 16, 20, 18, 22, 12, 16, 22]), "Đối soát nhân viên");

  return { wb, tenFile: `thong-ke-gui-hang_${ky.slug}.xlsx` };
}

async function xuatExcelThongKe() {
  if (!duDuLieuBaoCao()) return;
  const s = state.thongKe; // chụp lại trước khi chờ thư viện — đổi kỳ giữa chừng vẫn xuất đúng kỳ đã bấm
  const nut = $("btnXuatExcelThongKe");
  nut.disabled = true;
  try {
    const XLSX = await taiThuVienExcel();
    const { wb, tenFile } = taoWorkbookThongKe(XLSX, s, nguoiDungHienTai?.hoTen || "", thoiDiemHienTai());
    XLSX.writeFile(wb, tenFile, { compression: true });
  } catch (err) {
    showToast("error", "Không tải được thư viện xuất Excel", err.message);
  } finally {
    nut.disabled = false;
  }
}

// ---------------------------------------------------------------- In báo cáo
const _bangChiSo = (tieuDe, ds, tk, dinhDang) => `
  <table class="bc-bang">
    <thead><tr><th colspan="2">${escapeHtml(tieuDe)}</th></tr></thead>
    <tbody>${ds.map(([k, nhan]) => `<tr><td>${escapeHtml(nhan)}</td><td class="text-right">${escapeHtml(dinhDang(tk[k]))}</td></tr>`).join("")}</tbody>
  </table>`;

/** Dựng nội dung #baoCaoThongKe từ dữ liệu đang hiện. false nếu thiếu dữ liệu (đã báo toast). */
function dungBaoCaoThongKe() {
  if (!duDuLieuBaoCao()) return false;
  const s = state.thongKe;
  const { ky, tk, doiSoat } = s;
  const vung = $("baoCaoThongKe");
  const khoangNgay = ky.tu === ky.den ? _dmy(ky.tu) : `${_dmy(ky.tu)} – ${_dmy(ky.den)}`;
  const tien = v => dinhDangTien(v);
  vung.innerHTML = `
    <header class="bc-dau">
      <h1>BÁO CÁO GỬI HÀNG — ${escapeHtml(ky.nhan.toUpperCase())}</h1>
      <div class="bc-thong-tin">
        <div><span>Văn phòng:</span> ${escapeHtml(s.vanPhong)}</div>
        <div><span>Kỳ:</span> ${escapeHtml(khoangNgay)}</div>
        <div><span>Người in:</span> ${escapeHtml(nguoiDungHienTai?.hoTen || "")}</div>
        <div><span>Thời điểm in:</span> ${escapeHtml(thoiDiemHienTai())}</div>
      </div>
    </header>
    <section class="bc-hai-cot">
      ${_bangChiSo("Hàng gửi đi", CHI_SO_GUI_DI, tk, String)}
      ${_bangChiSo("Hàng nhận về", CHI_SO_NHAN_VE, tk, String)}
    </section>
    ${_bangChiSo("Tiền mặt thu tại quầy", CHI_SO_TIEN, tk, tien)}
    <p class="bc-ghi-chu">${escapeHtml(GHI_CHU_CHI_SO_TON.replace("xuất", "in"))}</p>
    <section class="bc-bieu-do"><h2>Sản lượng (tiếp nhận / đã giao)</h2><div id="bcSanLuong"></div></section>
    <section class="bc-bieu-do"><h2>Tiền mặt theo thời gian (trả trước + thu khi giao; đường: còn lại)</h2><div id="bcTienMat"></div></section>
    <section class="bc-bieu-do"><h2>Cách trả cước</h2><div id="bcCoCauTien"></div></section>
    <section class="bc-bieu-do"><h2>Tiền mặt theo nhân viên</h2><div id="bcTienNhanVien"></div></section>
    <section class="bc-doi-soat">
      <h2>Đối soát tiền mặt theo nhân viên</h2>
      <table class="bc-bang">
        <thead><tr><th>Nhân viên</th><th class="text-right">Trả trước</th><th class="text-right">Thu khi giao</th>
          <th class="text-right">Hoàn</th><th class="text-right">Còn trong két</th></tr></thead>
        <tbody>${doiSoat.nhan_vien.length ? doiSoat.nhan_vien.map(nv => `<tr>
          <td>${escapeHtml(nv.ho_ten || "(không rõ)")}</td>
          <td class="text-right">${escapeHtml(tien(nv.tien_tra_truoc))} (${escapeHtml(nv.so_don_tra_truoc)} đơn)</td>
          <td class="text-right">${escapeHtml(tien(nv.tien_cod))} (${escapeHtml(nv.so_don_cod)} đơn)</td>
          <td class="text-right">${nv.tien_hoan ? `− ${escapeHtml(tien(nv.tien_hoan))}` : "0 đ"}</td>
          <td class="text-right"><strong>${escapeHtml(tien(nv.tong_tien))}</strong></td></tr>`).join("")
          : `<tr><td colspan="5">Không có khoản thu / hoàn nào trong kỳ.</td></tr>`}</tbody>
        <tfoot><tr><th>Tổng cộng</th><th></th><th></th>
          <th class="text-right">${doiSoat.tong_tien_hoan ? `− ${escapeHtml(tien(doiSoat.tong_tien_hoan))}` : "0 đ"}</th>
          <th class="text-right">${escapeHtml(tien(doiSoat.tong_tien))}</th></tr></tfoot>
      </table>
    </section>
    <section class="bc-ky">
      <div><strong>Người lập</strong><span>(Ký, ghi rõ họ tên)</span></div>
      <div><strong>Người nhận tiền</strong><span>(Ký, ghi rõ họ tên)</span></div>
    </section>`;
  veBieuDoSanLuong(RONG_BIEU_DO_IN, $("bcSanLuong"));
  veBieuDoTienMat(RONG_BIEU_DO_IN, $("bcTienMat"));
  veBieuDoCoCau(RONG_BIEU_DO_IN, $("bcCoCauTien"));
  veBieuDoTienNhanVien(RONG_BIEU_DO_IN, $("bcTienNhanVien"));
  return true;
}

function inBaoCaoThongKe() {
  if (dungBaoCaoThongKe()) inPhanTu($("baoCaoThongKe"));
}
