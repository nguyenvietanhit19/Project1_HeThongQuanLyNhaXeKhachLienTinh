/* bieu-do.js — vẽ biểu đồ SVG tay cho tab Thống kê (không thư viện).
   Mọi hàm vẽ nhận `rong` tùy chọn: bỏ trống = theo chiều rộng thật của khung (màn hình),
   truyền số = vẽ cố định (bản in). */

/** Nhãn ngắn của mốc trên trục X: giờ "14h", ngày "05/11", tháng "Th11". */
function nhanMoc(moc, donVi) {
  const [ngay, gio] = String(moc).split("T");
  const [, m, d] = ngay.split("-");
  if (donVi === "gio") return `${Number(gio.slice(0, 2))}h`;
  if (donVi === "thang") return `Th${Number(m)}`;
  return `${d}/${m}`;
}

/** Nhãn đầy đủ của mốc (tooltip, Excel): "14h 05/11/2026", "05/11/2026", "11/2026". */
function nhanMocDayDu(moc, donVi) {
  const [ngay, gio] = String(moc).split("T");
  const [y, m, d] = ngay.split("-");
  if (donVi === "gio") return `${Number(gio.slice(0, 2))}h ${d}/${m}/${y}`;
  if (donVi === "thang") return `${m}/${y}`;
  return `${d}/${m}/${y}`;
}

/** Tiền rút gọn cho trục: 1250000 → "1,3tr", 500000 → "500k", -95000 → "−95k", 0 → "0". */
function rutGonTien(n) {
  const so = Number(n) || 0;
  const dau = so < 0 ? "−" : "";
  const a = Math.abs(so);
  if (a >= 1e6) return `${dau}${(a / 1e6).toFixed(1).replace(/\.0$/, "").replace(".", ",")}tr`;
  if (a >= 1e3) return `${dau}${Math.round(a / 1e3)}k`;
  return `${dau}${a}`;
}

/** Bước chia trục dọc là số "tròn" (1, 2, 5, 10, 20, 50...) để các vạch luôn cách đều và đủ số. */
function buocTrucDoc(khoang, soKhoang) {
  const tho = khoang / soKhoang;
  const muoiMu = 10 ** Math.floor(Math.log10(tho));
  return [1, 2, 5, 10].map(h => h * muoiMu).find(b => b >= tho);
}

function khungTrong(container, chu) {
  container.innerHTML = `<div class="chart-trong-khung">${escapeHtml(chu)}</div>`;
}

/**
 * Biểu đồ cột theo mốc thời gian (cột đôi, hoặc cột chồng + đường).
 * cauHinh = { nhan[], moc[], soMocDaQua, cot: [{ten, lop, giaTri[]}], chong, duong?: {ten, lop, giaTri[]},
 *             dinhDangTruc(n), tieuDeMoc(i), chuTrong }
 * Mốc có chỉ số >= soMocDaQua là tương lai: giữ chỗ trên trục nhưng không vẽ cột / điểm.
 */
function veBieuDoCot(container, cauHinh, rong) {
  if (!container) return;
  const W = rong || container.clientWidth;
  if (!W) return;
  container.dataset.rongDaVe = rong ? "" : String(W);
  const { nhan, moc, cot, chong, duong, dinhDangTruc, tieuDeMoc, chuTrong } = cauHinh;
  const n = nhan.length;
  const daQua = Math.min(n, cauHinh.soMocDaQua ?? n);
  const giaTriDaQua = [...cot.map(c => c.giaTri), ...(duong ? [duong.giaTri] : [])].flatMap(g => g.slice(0, daQua));
  if (!n || !giaTriDaQua.some(v => Number(v))) {
    khungTrong(container, chuTrong);
    return;
  }

  // Miền giá trị: cột chồng cộng dồn phần dương; đường và cột âm kéo trục xuống dưới 0.
  const tongChong = i => cot.reduce((s, c) => s + Math.max(0, Number(c.giaTri[i]) || 0), 0);
  const cacGiaTri = [0, ...giaTriDaQua.map(Number), ...(chong ? nhan.map((_, i) => tongChong(i)) : [])];
  const lonNhat = Math.max(...cacGiaTri), nhoNhat = Math.min(...cacGiaTri);
  const soKhoang = 4;
  const buoc = buocTrucDoc(Math.max(lonNhat - nhoNhat, soKhoang), soKhoang);
  const tran = Math.max(buoc, Math.ceil(lonNhat / buoc) * buoc);
  const day = Math.floor(nhoNhat / buoc) * buoc;

  const vachTruc = [];
  for (let v = day; v <= tran + buoc / 2; v += buoc) vachTruc.push(v);
  const doRongNhan = Math.max(...vachTruc.map(v => dinhDangTruc(v).length));
  const H = W < 480 ? 220 : 260;
  const L = 14 + doRongNhan * 7, R = 8, T = 24, B = 32;
  const cw = W - L - R, ch = H - T - B;
  const y = v => T + ch * (tran - v) / (tran - day);

  const luoi = vachTruc.map(v => `<line x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}" class="chart-grid${v === 0 ? " chart-grid--goc" : ""}"/>
      <text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" class="chart-truc">${escapeHtml(dinhDangTruc(v))}</text>`).join("");

  const groupW = cw / n;
  const moiNhan = Math.max(1, Math.ceil(48 / groupW));            // nhãn trục X cách nhau tối thiểu ~48px
  const soCot = chong ? 1 : cot.length;
  const barW = chong ? Math.max(6, Math.min(34, groupW * 0.6)) : Math.max(4, Math.min(26, (groupW * 0.62) / soCot));
  const hienSo = !chong && groupW >= 30;                           // đủ chỗ ghi số trên đầu cột
  const hcn = (x, a, b, lop) => {
    const tren = y(Math.max(a, b)), duoi = y(Math.min(a, b));
    return duoi - tren < 0.5 ? "" : `<rect x="${x}" y="${tren}" width="${barW}" height="${duoi - tren}" rx="${Math.min(4, barW / 2)}" class="${lop}"/>`;
  };

  const nhom = nhan.map((ten, i) => {
    const cx = L + i * groupW + groupW / 2;
    const tuongLai = i >= daQua;
    let ve = "";
    if (!tuongLai) {
      if (chong) {
        let day0 = 0;
        cot.forEach(c => {
          const v = Math.max(0, Number(c.giaTri[i]) || 0);
          ve += hcn(cx - barW / 2, day0, day0 + v, `chart-cot ${c.lop}`);
          day0 += v;
        });
      } else {
        const x0 = cx - (soCot * barW + (soCot - 1) * 4) / 2;
        cot.forEach((c, k) => {
          const v = Number(c.giaTri[i]) || 0;
          const x = x0 + k * (barW + 4);
          ve += hcn(x, 0, v, `chart-cot ${c.lop}`);
          if (hienSo && v) ve += `<text x="${x + barW / 2}" y="${y(Math.max(v, 0)) - 6}" text-anchor="middle" class="chart-so">${v}</text>`;
        });
      }
      if (duong) ve += `<circle cx="${cx}" cy="${y(Number(duong.giaTri[i]) || 0)}" r="3.5" class="chart-diem ${duong.lop}"/>`;
    }
    const hienNhan = i % moiNhan === 0;
    return `<g data-moc="${escapeHtml(moc[i])}"${tuongLai ? " data-tuong-lai" : ""}>
        <title>${escapeHtml(tieuDeMoc(i))}</title>
        <rect x="${cx - groupW / 2}" y="${T}" width="${groupW}" height="${ch}" class="chart-vung"/>
        ${ve}
        ${hienNhan ? `<text x="${cx}" y="${H - 10}" text-anchor="middle" class="chart-ngay${tuongLai ? " chart-ngay--tuong-lai" : ""}">${escapeHtml(ten)}</text>` : ""}
      </g>`;
  }).join("");

  const duongVe = duong && daQua > 1
    ? `<polyline class="chart-duong ${duong.lop}" points="${duong.giaTri.slice(0, daQua)
      .map((v, i) => `${L + i * groupW + groupW / 2},${y(Number(v) || 0)}`).join(" ")}"/>`
    : "";
  container.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="chart-svg-wrap" role="img">${luoi}${nhom}${duongVe}</svg>`;
}

/**
 * Biểu đồ tròn dạng vành khuyên + chú thích bên cạnh.
 * cauHinh = { phan: [{ten, lop, giaTri, phu}], giua, chuTrong } — `lop` tô cả phần vành lẫn ô màu chú thích.
 */
function veBieuDoTron(container, cauHinh, rong) {
  if (!container) return;
  const W = rong || container.clientWidth;
  if (!W) return;
  container.dataset.rongDaVe = rong ? "" : String(W);
  const phan = cauHinh.phan.filter(p => Number(p.giaTri) > 0);
  const tong = phan.reduce((s, p) => s + Number(p.giaTri), 0);
  if (!tong) {
    khungTrong(container, cauHinh.chuTrong);
    return;
  }
  const S = Math.min(200, Math.max(150, W * 0.42));
  const c = S / 2, R = S / 2 - 4, r = R * 0.62;
  const diem = (ban, goc) => `${(c + ban * Math.cos(goc)).toFixed(2)},${(c + ban * Math.sin(goc)).toFixed(2)}`;
  let goc = -Math.PI / 2;
  const vanh = phan.length === 1
    ? `<circle cx="${c}" cy="${c}" r="${(R + r) / 2}" stroke-width="${R - r}" style="fill:none" class="chart-vanh ${phan[0].lop}"><title>${escapeHtml(phan[0].ten)}: 100%</title></circle>`
    : phan.map(p => {
      const goc2 = goc + (Number(p.giaTri) / tong) * 2 * Math.PI;
      const lon = goc2 - goc > Math.PI ? 1 : 0;
      const d = `M${diem(R, goc)} A${R},${R} 0 ${lon} 1 ${diem(R, goc2)} L${diem(r, goc2)} A${r},${r} 0 ${lon} 0 ${diem(r, goc)} Z`;
      goc = goc2;
      return `<path d="${d}" class="chart-vanh ${p.lop}"><title>${escapeHtml(p.ten)}: ${escapeHtml(p.phu)}</title></path>`;
    }).join("");
  const chuThich = cauHinh.phan.map(p => `<li>
      <span class="legend-color-box chart-mau ${p.lop}"></span>
      <span class="chart-tron__ten">${escapeHtml(p.ten)}</span>
      <span class="chart-tron__phu">${escapeHtml(p.phu)}</span>
    </li>`).join("");
  container.innerHTML = `<div class="chart-tron">
      <svg width="${S}" height="${S}" viewBox="0 0 ${S} ${S}" class="chart-svg-wrap" role="img">${vanh}
        <text x="${c}" y="${c - 4}" text-anchor="middle" class="chart-tron__giua-nhan">Tổng thu</text>
        <text x="${c}" y="${c + 16}" text-anchor="middle" class="chart-tron__giua">${escapeHtml(cauHinh.giua)}</text>
      </svg>
      <ul class="chart-tron__chu-thich">${chuThich}</ul>
    </div>`;
}

/**
 * Cột ngang theo tên (vd tiền mặt theo nhân viên). Giá trị âm vẽ sang trái trục 0, màu riêng.
 * cauHinh = { hang: [{ten, giaTri}], dinhDang(n), chuTrong }
 */
function veBieuDoNgang(container, cauHinh, rong) {
  if (!container) return;
  const W = rong || container.clientWidth;
  if (!W) return;
  container.dataset.rongDaVe = rong ? "" : String(W);
  const { hang, dinhDang } = cauHinh;
  if (!hang.length) {
    khungTrong(container, cauHinh.chuTrong);
    return;
  }
  const DONG = 30, T = 6;
  const rongTen = Math.min(150, Math.round(W * 0.3)), rongSo = 96;
  const x0 = rongTen, x1 = W - rongSo;
  const lon = Math.max(0, ...hang.map(h => Number(h.giaTri))), nho = Math.min(0, ...hang.map(h => Number(h.giaTri)));
  const mien = lon - nho || 1;
  const x = v => x0 + (x1 - x0) * (v - nho) / mien;
  const H = T * 2 + hang.length * DONG;
  const catTen = s => (s.length > 18 ? `${s.slice(0, 17)}…` : s);
  const dong = hang.map((h, i) => {
    const v = Number(h.giaTri) || 0;
    const y = T + i * DONG;
    const a = x(Math.min(v, 0)), b = x(Math.max(v, 0));
    return `<g>
        <title>${escapeHtml(h.ten)}: ${escapeHtml(dinhDang(v))}</title>
        <text x="${x0 - 8}" y="${y + DONG / 2 + 4}" text-anchor="end" class="chart-ngay">${escapeHtml(catTen(h.ten))}</text>
        ${b - a >= 0.5 ? `<rect x="${a}" y="${y + 6}" width="${b - a}" height="${DONG - 12}" rx="4" class="chart-cot ${v < 0 ? "chart-cot--am" : "chart-cot--nhan-vien"}"/>` : ""}
        <text x="${W - 4}" y="${y + DONG / 2 + 4}" text-anchor="end" class="chart-so">${escapeHtml(dinhDang(v))}</text>
      </g>`;
  }).join("");
  const truc0 = nho < 0 ? `<line x1="${x(0)}" y1="${T}" x2="${x(0)}" y2="${H - T}" class="chart-grid chart-grid--goc"/>` : "";
  container.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="chart-svg-wrap" role="img">${dong}${truc0}</svg>`;
}

/** Khung đổi rộng (xoay máy, thu nhỏ cửa sổ, thanh bên thu gọn) thì vẽ lại — chỉ khi chiều rộng thật sự đổi. */
function theoDoiKichThuoc(container, ve) {
  if (!container || container.dataset.theoDoi || !window.ResizeObserver) return;
  container.dataset.theoDoi = "1";
  let cho = null;
  new ResizeObserver(() => {
    cancelAnimationFrame(cho);
    cho = requestAnimationFrame(() => {
      if (container.clientWidth && String(container.clientWidth) !== container.dataset.rongDaVe) ve();
    });
  }).observe(container);
}
