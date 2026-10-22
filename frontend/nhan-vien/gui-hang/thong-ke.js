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

let duLieuBieuDo = [];
let rongBieuDoDaVe = 0;

async function taiBieuDo() {
  const container = $("columnChartContainer");
  try {
    duLieuBieuDo = await apiGet(`/gui-hang/thong-ke-theo-ngay${taoQuery({ so_ngay: state.bieuDoSoNgay, ...phamViQuery() })}`);
  } catch (err) {
    duLieuBieuDo = [];
    container.textContent = `Không tải được biểu đồ: ${err.message}`;
    return;
  }
  veBieuDo();
  theoDoiKichThuocBieuDo();
}

/** Bước chia trục dọc là số "tròn" (1, 2, 5, 10, 20, 50...) để 5 vạch luôn cách đều và đủ số. */
function buocTrucDoc(giaTriLonNhat, soKhoang) {
  const tho = giaTriLonNhat / soKhoang;
  const muoiMu = 10 ** Math.floor(Math.log10(tho));
  return [1, 2, 5, 10].map(h => h * muoiMu).find(b => b >= tho);
}

/** Vẽ theo đúng chiều rộng thật của khung (không kéo giãn SVG) — chữ và cột giữ đúng tỉ lệ ở mọi màn hình. */
function veBieuDo() {
  const container = $("columnChartContainer");
  const ds = duLieuBieuDo;
  if (!container || !container.clientWidth) return;
  const W = container.clientWidth;
  rongBieuDoDaVe = W;
  const H = W < 480 ? 220 : 260;
  const L = 36, R = 8, T = 24, B = 32;
  const cw = W - L - R, ch = H - T - B;
  const soKhoang = 4;
  const lonNhat = Math.max(0, ...ds.map(d => Math.max(Number(d.tiep_nhan), Number(d.da_giao))));
  const buoc = buocTrucDoc(Math.max(lonNhat, soKhoang), soKhoang);
  const tran = buoc * soKhoang;
  const groupW = cw / Math.max(1, ds.length);
  const barW = Math.max(4, Math.min(26, (groupW * 0.62) / 2));
  const hienSo = groupW >= 30;                                   // đủ chỗ ghi số trên đầu cột
  const moiNhan = Math.max(1, Math.ceil(48 / groupW));           // nhãn ngày cách nhau tối thiểu ~48px

  let luoi = "";
  for (let s = 0; s <= soKhoang; s++) {
    const y = T + ch - (s / soKhoang) * ch;
    luoi += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" class="chart-grid${s === 0 ? " chart-grid--goc" : ""}"/>
      <text x="${L - 8}" y="${y + 4}" text-anchor="end" class="chart-truc">${buoc * s}</text>`;
  }
  const cot1 = (x, giaTri, lop) => {
    if (!giaTri) return "";
    const h = (giaTri / tran) * ch;
    return `<rect x="${x}" y="${T + ch - h}" width="${barW}" height="${h}" rx="${Math.min(5, barW / 2)}" class="${lop}"/>
      ${hienSo ? `<text x="${x + barW / 2}" y="${T + ch - h - 6}" text-anchor="middle" class="chart-so">${giaTri}</text>` : ""}`;
  };
  const cot = ds.map((d, i) => {
    const [, m, ngay] = String(d.ngay).slice(0, 10).split("-");
    const nhan = `${ngay}/${m}`;
    const cx = L + i * groupW + groupW / 2;
    const tiepNhan = Number(d.tiep_nhan), daGiao = Number(d.da_giao);
    const hienNhan = (ds.length - 1 - i) % moiNhan === 0;          // luôn giữ nhãn ngày gần nhất
    return `<g>
        <title>${nhan}: tiếp nhận ${tiepNhan}, đã giao ${daGiao}</title>
        <rect x="${cx - groupW / 2}" y="${T}" width="${groupW}" height="${ch}" class="chart-vung"/>
        ${cot1(cx - barW - 2, tiepNhan, "chart-cot chart-cot--tiep-nhan")}
        ${cot1(cx + 2, daGiao, "chart-cot chart-cot--da-giao")}
        ${hienNhan ? `<text x="${cx}" y="${H - 10}" text-anchor="middle" class="chart-ngay">${nhan}</text>` : ""}
      </g>`;
  }).join("");
  const trong = ds.length && !lonNhat
    ? `<text x="${L + cw / 2}" y="${T + ch / 2}" text-anchor="middle" class="chart-trong">Chưa có đơn nào trong ${ds.length} ngày qua</text>`
    : "";
  container.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="chart-svg-wrap" role="img" aria-label="Biểu đồ sản lượng theo ngày">${luoi}${cot}${trong}</svg>`;
}

/** Khung đổi rộng (xoay máy, thu nhỏ cửa sổ, thanh bên thu gọn) thì vẽ lại — chỉ khi chiều rộng thật sự đổi. */
function theoDoiKichThuocBieuDo() {
  const container = $("columnChartContainer");
  if (!container || container.dataset.theoDoi || !window.ResizeObserver) return;
  container.dataset.theoDoi = "1";
  let cho = null;
  new ResizeObserver(() => {
    cancelAnimationFrame(cho);
    cho = requestAnimationFrame(() => {
      if (duLieuBieuDo.length && container.clientWidth && container.clientWidth !== rongBieuDoDaVe) veBieuDo();
    });
  }).observe(container);
}

