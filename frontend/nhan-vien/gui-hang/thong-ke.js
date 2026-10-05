/* thong-ke.js — tab Thống kê & đối soát tiền mặt. */

function datKhoangNgay(soNgay) {
  const den = new Date();
  const tu = new Date();
  tu.setDate(den.getDate() - (soNgay - 1));
  $("tkTuNgay").value = ngayISO(tu);
  $("tkDenNgay").value = ngayISO(den);
  document.querySelectorAll("#tkPreset .time-tab").forEach(b => b.classList.toggle("active", Number(b.dataset.soNgay) === soNgay));
}

async function taiThongKe() {
  const tu = $("tkTuNgay").value;
  const den = $("tkDenNgay").value;
  if (tu && den && tu > den) {
    showToast("warning", "Khoảng ngày không hợp lệ", "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
    return;
  }
  const khoang = { tu_ngay: tu, den_ngay: den, ...phamViQuery() };
  taiBieuDo(); // biểu đồ độc lập với khoảng ngày — tải song song, tự báo lỗi riêng
  try {
    const [tk, doiSoat] = await Promise.all([
      apiGet(`/gui-hang/thong-ke${taoQuery(khoang)}`),
      apiGet(`/gui-hang/doi-soat${taoQuery(khoang)}`),
    ]);
    datText("tkTongGuiDi", tk.tong_don_gui_di);
    datText("tkChoXepXe", tk.so_don_cho_xep_xe);
    datText("tkGuiTrenXe", tk.so_don_gui_dang_tren_xe);
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
    state.doiSoat = doiSoat;
    renderDoiSoat(doiSoat);
  } catch (err) {
    showToast("error", "Lỗi tải thống kê", err.message);
  }
}

function xuatCsvDoiSoat() {
  const ds = state.doiSoat;
  if (!ds || !ds.nhan_vien.length) {
    showToast("warning", "Không có dữ liệu", "Không có khoản thu nào trong kỳ để xuất.");
    return;
  }
  xuatCsv(`doi-soat-${ds.tu_ngay}_${ds.den_ngay}.csv`,
    ["Nhân viên", "Số đơn trả trước", "Tiền trả trước (VNĐ)", "Số đơn COD", "Tiền COD (VNĐ)", "Tổng thu (VNĐ)"],
    [...ds.nhan_vien.map(nv => [nv.ho_ten || "(không rõ)", nv.so_don_tra_truoc, nv.tien_tra_truoc, nv.so_don_cod, nv.tien_cod, nv.tong_tien]),
      ["TỔNG", "", "", "", "", ds.tong_tien]]);
}

function renderDoiSoat(doiSoat) {
  const tbody = $("tbodyDoiSoat");
  if (!doiSoat.nhan_vien.length) {
    hienTrangThaiBang("tbodyDoiSoat", 4, "Không có khoản thu nào trong kỳ.");
  } else {
    tbody.innerHTML = doiSoat.nhan_vien.map(nv => `
      <tr>
        <td>${escapeHtml(nv.ho_ten || "(không rõ)")}</td>
        <td class="text-right">${escapeHtml(dinhDangTien(nv.tien_tra_truoc))}<div class="cell-sub">${escapeHtml(nv.so_don_tra_truoc)} đơn</div></td>
        <td class="text-right">${escapeHtml(dinhDangTien(nv.tien_cod))}<div class="cell-sub">${escapeHtml(nv.so_don_cod)} đơn</div></td>
        <td class="text-right"><strong>${escapeHtml(dinhDangTien(nv.tong_tien))}</strong></td>
      </tr>`).join("");
  }
  datText("tkDoiSoatTong", dinhDangTien(doiSoat.tong_tien));
}

async function taiBieuDo() {
  const container = $("columnChartContainer");
  let ds = [];
  try {
    ds = await apiGet(`/gui-hang/thong-ke-theo-ngay${taoQuery({ so_ngay: state.bieuDoSoNgay, ...phamViQuery() })}`);
  } catch (err) {
    container.textContent = `Không tải được biểu đồ: ${err.message}`;
    return;
  }
  const W = 650, H = 250, L = 40, R = 16, T = 20, B = 36;
  const cw = W - L - R, ch = H - T - B;
  const maxVal = Math.max(4, ...ds.map(d => Math.max(Number(d.tiep_nhan), Number(d.da_giao))));
  const tran = Math.ceil(maxVal * 1.2);
  const groupW = cw / Math.max(1, ds.length);
  const barW = Math.max(3, Math.min(16, (groupW - 8) / 2));

  let luoi = "";
  for (let s = 0; s <= 4; s++) {
    const y = T + ch - (s / 4) * ch;
    luoi += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" stroke="#E5E7EB" stroke-dasharray="3 3"/>
      <text x="${L - 8}" y="${y + 4}" text-anchor="end" font-size="11" fill="#9CA3AF">${Math.round((tran / 4) * s)}</text>`;
  }
  const cot = ds.map((d, i) => {
    const [, m, ngay] = String(d.ngay).slice(0, 10).split("-");
    const nhan = `${ngay}/${m}`;
    const cx = L + i * groupW + groupW / 2;
    const h1 = Math.max(1, (Number(d.tiep_nhan) / tran) * ch);
    const h2 = Math.max(1, (Number(d.da_giao) / tran) * ch);
    const hienNhan = ds.length <= 14 || i % 3 === 0 || i === ds.length - 1;
    return `<g>
        <title>${nhan}: tiếp nhận ${Number(d.tiep_nhan)}, đã giao ${Number(d.da_giao)}</title>
        <rect x="${cx - barW - 1}" y="${T + ch - h1}" width="${barW}" height="${h1}" rx="3" fill="#3B82F6"/>
        <rect x="${cx + 1}" y="${T + ch - h2}" width="${barW}" height="${h2}" rx="3" fill="#10B981"/>
        ${hienNhan ? `<text x="${cx}" y="${H - 12}" text-anchor="middle" font-size="10.5" fill="#6B7280">${nhan}</text>` : ""}
      </g>`;
  }).join("");
  container.innerHTML = `<svg viewBox="0 0 ${W} ${H}" class="chart-svg-wrap" preserveAspectRatio="none" role="img" aria-label="Biểu đồ sản lượng theo ngày">${luoi}${cot}</svg>`;
}

