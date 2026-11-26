/*
 * Biểu đồ cho trang Thống kê của quản lý — SVG/HTML vẽ tay, không thư viện ngoài.
 * Quy ước: màu theo VAI TRÒ (biến CSS --tkq-s1.. ở thong-ke.css), một trục dọc duy nhất, nét mảnh, đầu cột bo 4px, khe 2px giữa các phần chồng,
 * di chuột lên cột / điểm / ô hiện bảng số (thẻ nổi .tkq-tip). Mỗi biểu đồ ≥ 2 dãy đều có chú thích; số liệu đầy đủ nằm ở bảng ngay dưới.
 * Hàm vẽ nhận phần tử khung + cấu hình; tự vẽ lại khi khung đổi rộng.
 */

const BD = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- Thẻ nổi khi di chuột (dùng chung cả trang) ----------
  let tip = null;
  function layTip() {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "tkq-tip";
      tip.hidden = true;
      document.body.appendChild(tip);
    }
    return tip;
  }
  function hienTip(html, x, y) {
    const t = layTip();
    t.innerHTML = html;
    t.hidden = false;
    const r = t.getBoundingClientRect();
    const trai = Math.min(window.innerWidth - r.width - 8, x + 14);
    const tren = y + 16 + r.height > window.innerHeight ? y - r.height - 12 : y + 16;
    t.style.left = `${Math.max(8, trai)}px`;
    t.style.top = `${Math.max(8, tren)}px`;
  }
  function anTip() {
    if (tip) tip.hidden = true;
  }
  /** Khung có các phần tử [data-tip] (nội dung HTML đã escape) → hiện thẻ nổi khi di chuột/chạm; [data-moc] tô sáng cả cột. */
  function ganTip(khung) {
    if (khung.dataset.coTip) return;
    khung.dataset.coTip = "1";
    khung.addEventListener("mousemove", (e) => {
      const muc = e.target.closest("[data-tip]");
      khung.querySelectorAll(".is-hover").forEach((el) => el !== muc && el.classList.remove("is-hover"));
      if (!muc || !khung.contains(muc)) return anTip();
      muc.classList.add("is-hover");
      hienTip(muc.dataset.tip, e.clientX, e.clientY);
    });
    khung.addEventListener("mouseleave", () => {
      anTip();
      khung.querySelectorAll(".is-hover").forEach((el) => el.classList.remove("is-hover"));
    });
  }

  // ---------- Tiện ích ----------
  function buocTron(khoang, soKhoang) {
    const tho = khoang / soKhoang || 1;
    const mu = 10 ** Math.floor(Math.log10(tho));
    return [1, 2, 2.5, 5, 10].map((h) => h * mu).find((b) => b >= tho);
  }

  function chuThich(chuoi) {
    if (chuoi.length < 2) return "";
    return `<div class="tkq-chu-thich">${chuoi.map((c) => `<span><i class="tkq-o-mau" style="background:${c.mau}"></i>${esc(c.ten)}</span>`).join("")}</div>`;
  }

  function trong(khung, chu) {
    khung.innerHTML = `<div class="tkq-bd-trong">${esc(chu || "Chưa có số liệu trong kỳ này")}</div>`;
  }

  function theoDoi(khung, ve) {
    if (khung._ve) {
      khung._ve = ve;
      return;
    }
    khung._ve = ve;
    if (!window.ResizeObserver) return;
    let cho = null;
    new ResizeObserver(() => {
      cancelAnimationFrame(cho);
      cho = requestAnimationFrame(() => {
        if (khung.clientWidth && String(khung.clientWidth) !== khung.dataset.rongDaVe) khung._ve();
      });
    }).observe(khung);
  }

  function dongTip(tieuDe, hang) {
    return esc(`<strong>${esc(tieuDe)}</strong>`) + hang
      .map((h) => esc(`<div class="tkq-tip__dong">${h.mau ? `<i class="tkq-o-mau" style="background:${h.mau}"></i>` : ""}<span>${esc(h.ten)}</span><b>${esc(h.gt)}</b></div>`))
      .join("");
  }

  /**
   * Cột theo mốc thời gian — chồng (`chong: true`) hoặc cạnh nhau; hoặc đường (`kieu: "duong"`).
   * cfg = { nhan[], tieuDeMoc[], chuoi: [{ten, mau, giaTri[]}], chong, kieu, dinhDang(n), dinhDangTruc(n), soMocDaQua, tran?, them?: (i) => [{ten, gt}] }
   */
  function thoiGian(khung, cfg) {
    if (!khung) return;
    const ve = () => {
      const W = khung.clientWidth;
      if (!W) return;
      khung.dataset.rongDaVe = String(W);
      const { nhan, chuoi } = cfg;
      const n = nhan.length;
      const daQua = Math.min(n, cfg.soMocDaQua ?? n);
      const laDuong = cfg.kieu === "duong";
      const coSo = chuoi.some((c) => c.giaTri.slice(0, daQua).some((v) => Number(v)));
      if (!n || !coSo) return trong(khung, cfg.chuTrong);

      const tong = (i) => chuoi.reduce((s, c) => s + Math.max(0, Number(c.giaTri[i]) || 0), 0);
      const lon = cfg.tran ?? Math.max(1, ...(cfg.chong ? nhan.map((_, i) => tong(i)) : chuoi.flatMap((c) => c.giaTri.map(Number))));
      const buoc = cfg.tran ? cfg.tran / 4 : buocTron(lon, 4);
      const tran = cfg.tran ?? Math.ceil(lon / buoc) * buoc;
      const vach = [];
      for (let v = 0; v <= tran + buoc / 2; v += buoc) vach.push(v);
      const dinhDangTruc = cfg.dinhDangTruc || cfg.dinhDang;
      const L = 12 + Math.max(...vach.map((v) => dinhDangTruc(v).length)) * 7;
      const R = 10, T = 12, B = 28, H = W < 520 ? 210 : 250;
      const cw = W - L - R, ch = H - T - B;
      const y = (v) => T + ch * (1 - v / tran);
      const nhom = cw / n;
      const moiNhan = Math.max(1, Math.ceil(52 / nhom));

      let svg = vach.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="tkq-ke${v === 0 ? " tkq-ke--goc" : ""}"/>
        <text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" class="tkq-truc">${esc(dinhDangTruc(v))}</text>`).join("");

      const soCot = cfg.chong ? 1 : chuoi.length;
      const rongCot = cfg.chong ? Math.max(4, Math.min(30, nhom * 0.6)) : Math.max(3, Math.min(20, (nhom * 0.7 - (soCot - 1) * 2) / soCot));
      const hcn = (x, a, b, mau, boTren) => {
        const tren = y(b), duoi = y(a);
        const h = duoi - tren;
        if (h < 0.5) return "";
        const r = boTren ? Math.min(4, rongCot / 2, h) : 0;
        // Đầu cột bo tròn, chân cột vuông (bám đường gốc)
        return `<path d="M${x},${duoi} V${tren + r} Q${x},${tren} ${x + r},${tren} H${x + rongCot - r} Q${x + rongCot},${tren} ${x + rongCot},${tren + r} V${duoi} Z" fill="${mau}"/>`;
      };

      nhan.forEach((ten, i) => {
        const cx = L + i * nhom + nhom / 2;
        const tuongLai = i >= daQua;
        let marks = "";
        if (!tuongLai && !laDuong) {
          if (cfg.chong) {
            let day = 0;
            const coGiaTri = chuoi.map((c) => Math.max(0, Number(c.giaTri[i]) || 0));
            const cuoi = coGiaTri.map((v, k) => (v > 0 ? k : -1)).reduce((a, b) => Math.max(a, b), -1);
            chuoi.forEach((c, k) => {
              const v = coGiaTri[k];
              if (!v) return;
              // khe 2px giữa các phần chồng
              const a = day === 0 ? day : day + (2 * tran) / ch;
              marks += hcn(cx - rongCot / 2, Math.min(a, day + v), day + v, c.mau, k === cuoi);
              day += v;
            });
          } else {
            const x0 = cx - (soCot * rongCot + (soCot - 1) * 2) / 2;
            chuoi.forEach((c, k) => {
              const v = Math.max(0, Number(c.giaTri[i]) || 0);
              marks += hcn(x0 + k * (rongCot + 2), 0, v, c.mau, true);
            });
          }
        }
        const hangTip = chuoi.map((c) => ({ ten: c.ten, mau: c.mau, gt: cfg.dinhDang(Number(c.giaTri[i]) || 0) }))
          .concat(cfg.them ? cfg.them(i) : []);
        svg += `<g class="tkq-moc">
          <rect x="${cx - nhom / 2}" y="${T}" width="${nhom}" height="${ch}" class="tkq-vung" data-tip="${tuongLai ? esc(`<strong>${esc(cfg.tieuDeMoc[i])}</strong><div>Chưa tới</div>`) : dongTip(cfg.tieuDeMoc[i], hangTip)}"/>
          ${marks}
          ${i % moiNhan === 0 ? `<text x="${cx}" y="${H - 9}" text-anchor="middle" class="tkq-truc${tuongLai ? " tkq-truc--mo" : ""}">${esc(ten)}</text>` : ""}
        </g>`;
      });

      if (laDuong) {
        chuoi.forEach((c) => {
          const diem = c.giaTri.slice(0, daQua).map((v, i) => (v == null ? null : [L + i * nhom + nhom / 2, y(Math.min(tran, Number(v) || 0))]));
          const doan = [];
          let hien = [];
          diem.forEach((d) => {
            if (d) hien.push(d);
            else if (hien.length) { doan.push(hien); hien = []; }
          });
          if (hien.length) doan.push(hien);
          svg += doan.map((d) => `<polyline points="${d.map((p) => p.join(",")).join(" ")}" fill="none" stroke="${c.mau}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" pointer-events="none"/>`).join("");
          if (n <= 40) svg += diem.filter(Boolean).map((p) => `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="${c.mau}" stroke="var(--tkq-mat)" stroke-width="2" pointer-events="none"/>`).join("");
        });
      }

      khung.innerHTML = `${chuThich(chuoi)}<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" class="tkq-svg" role="img" aria-label="${esc(cfg.moTa || "")}">${svg}</svg>`;
      ganTip(khung);
    };
    theoDoi(khung, ve);
    ve();
  }

  /** Vành khuyên + chú thích có số và %. cfg = { phan: [{ten, mau, giaTri}], giua: {so, nhan}, dinhDang } */
  function tron(khung, cfg) {
    if (!khung) return;
    const phan = cfg.phan.filter((p) => Number(p.giaTri) > 0);
    const tong = phan.reduce((s, p) => s + Number(p.giaTri), 0);
    if (!tong) return trong(khung, cfg.chuTrong);
    const S = 168, c = S / 2, R = c - 2, r = R * 0.64;
    const toaDo = (ban, goc) => `${(c + ban * Math.cos(goc)).toFixed(2)},${(c + ban * Math.sin(goc)).toFixed(2)}`;
    const khe = phan.length > 1 ? 0.012 : 0; // khe nhỏ giữa các phần
    let goc = -Math.PI / 2;
    const pt = (v) => `${Math.round((v / tong) * 1000) / 10}%`.replace(".", ",");
    const vanh = phan.map((p) => {
      const g2 = goc + (Number(p.giaTri) / tong) * 2 * Math.PI;
      const a = goc + khe, b = Math.max(a + 0.001, g2 - khe);
      const lon = b - a > Math.PI ? 1 : 0;
      goc = g2;
      const tipHtml = dongTip(p.ten, [{ ten: "Giá trị", gt: cfg.dinhDang(p.giaTri) }, { ten: "Tỷ trọng", gt: pt(p.giaTri) }]);
      if (phan.length === 1) return `<circle cx="${c}" cy="${c}" r="${(R + r) / 2}" fill="none" stroke="${p.mau}" stroke-width="${R - r}" data-tip="${tipHtml}"/>`;
      return `<path d="M${toaDo(R, a)} A${R},${R} 0 ${lon} 1 ${toaDo(R, b)} L${toaDo(r, b)} A${r},${r} 0 ${lon} 0 ${toaDo(r, a)} Z" fill="${p.mau}" data-tip="${tipHtml}"/>`;
    }).join("");
    const ds = cfg.phan.map((p) => `<li>
        <i class="tkq-o-mau" style="background:${p.mau}"></i>
        <span class="tkq-tron__ten">${esc(p.ten)}</span>
        <b>${esc(cfg.dinhDang(Number(p.giaTri) || 0))}</b>
        <em>${Number(p.giaTri) > 0 ? pt(Number(p.giaTri)) : "0%"}</em>
      </li>`).join("");
    khung.innerHTML = `<div class="tkq-tron">
        <svg width="${S}" height="${S}" viewBox="0 0 ${S} ${S}" class="tkq-svg" role="img">${vanh}
          <text x="${c}" y="${c - 2}" text-anchor="middle" class="tkq-tron__so">${esc(cfg.giua?.so ?? "")}</text>
          <text x="${c}" y="${c + 16}" text-anchor="middle" class="tkq-tron__nhan">${esc(cfg.giua?.nhan ?? "")}</text>
        </svg>
        <ul class="tkq-tron__ds">${ds}</ul>
      </div>`;
    ganTip(khung);
  }

  /**
   * Thanh ngang (HTML) — xếp hạng theo tên. Nhiều đoạn chồng: `doan: [{ten, mau}]` + mỗi hàng `giaTri: [..]`.
   * cfg = { hang: [{ten, phu?, giaTri: number | number[]}], doan?: [{ten, mau}], mau?, dinhDang, gioiHan? }
   */
  function ngang(khung, cfg) {
    if (!khung) return;
    const doan = cfg.doan || [{ ten: cfg.tenGiaTri || "Giá trị", mau: cfg.mau }];
    const hang = cfg.hang.map((h) => ({ ...h, ds: Array.isArray(h.giaTri) ? h.giaTri.map(Number) : [Number(h.giaTri)] }));
    const tongHang = (h) => h.ds.reduce((s, v) => s + Math.max(0, v || 0), 0);
    const lon = Math.max(0, ...hang.map(tongHang));
    if (!hang.length || !lon) return trong(khung, cfg.chuTrong);
    const dong = hang.map((h) => {
      const t = tongHang(h);
      const thanh = h.ds.map((v, k) => (v > 0 ? `<span style="width:${(v / lon) * 100}%;background:${doan[k].mau}"></span>` : "")).join("");
      const tipHtml = dongTip(h.ten, doan.map((d, k) => ({ ten: d.ten, mau: doan.length > 1 ? d.mau : null, gt: cfg.dinhDang(h.ds[k] || 0) }))
        .concat(doan.length > 1 ? [{ ten: "Tổng", gt: cfg.dinhDang(t) }] : []).concat(h.them || []));
      return `<div class="tkq-ngang__hang" data-tip="${tipHtml}">
          <span class="tkq-ngang__ten" title="${esc(h.ten)}">${esc(h.ten)}${h.phu ? `<small>${esc(h.phu)}</small>` : ""}</span>
          <span class="tkq-ngang__thanh">${thanh}</span>
          <b class="tkq-ngang__so">${esc(cfg.dinhDangNhan ? cfg.dinhDangNhan(h) : cfg.dinhDang(t))}</b>
        </div>`;
    }).join("");
    khung.innerHTML = `${chuThich(doan)}<div class="tkq-ngang">${dong}</div>`;
    ganTip(khung);
  }

  /**
   * Bảng nhiệt (HTML): hàng × cột, ô tô theo dải 1 màu nhạt → đậm (0..1). cfg = { hang[], cot[], o(i, j) → {ty: 0..1 | null, nhan, tip[]} }
   */
  function nhiet(khung, cfg) {
    if (!khung) return;
    if (!cfg.cot.length) return trong(khung, cfg.chuTrong);
    const DAI = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
    const mau = (ty) => DAI[Math.min(DAI.length - 1, Math.floor(ty * DAI.length))];
    const dau = `<tr><th></th>${cfg.cot.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>`;
    const than = cfg.hang.map((h, i) => `<tr><th>${esc(h)}</th>${cfg.cot.map((c, j) => {
      const o = cfg.o(i, j);
      if (!o || o.ty == null) return '<td class="tkq-nhiet__rong"></td>';
      const toi = o.ty >= 0.5;
      return `<td style="background:${mau(o.ty)};color:${toi ? "#fff" : "var(--color-text-primary)"}" data-tip="${dongTip(`${h} · ${c}`, o.tip)}">${esc(o.nhan)}</td>`;
    }).join("")}</tr>`).join("");
    const thang = `<div class="tkq-nhiet__thang"><span>0%</span>${DAI.map((m) => `<i style="background:${m}"></i>`).join("")}<span>100%</span></div>`;
    khung.innerHTML = `<div class="tkq-nhiet-cuon"><table class="tkq-nhiet">${dau}${than}</table></div>${thang}`;
    ganTip(khung);
  }

  return { thoiGian, tron, ngang, nhiet, esc };
})();
