/*
 * Modal "Chi tiết chuyến" dùng chung cho trang Chuyến và trang Lịch chạy — xem sơ đồ ghế kèm giá từng ghế
 * và trạng thái ghế, giá từng chặng, lộ trình + mốc thời gian, sửa giờ, xóa (chỉ chuyến chưa gán xe/chưa khởi hành/
 * chưa có vé). Cần api-client.js (apiGet/apiPut/apiDelete/htmlMa) nạp trước.
 *
 *   ChuyenChiTiet.mo(chuyenId, { onThayDoi })
 *   - onThayDoi(): gọi sau khi chuyến bị sửa giờ hoặc xóa, để trang gọi tải lại dữ liệu
 *
 * Modal tự dựng vào <body> ở lần mở đầu tiên và luôn được đưa xuống cuối body
 * mỗi lần mở, nên hiện đè lên modal khác đang mở (VD lịch các ngày đã sinh chuyến).
 */
const ChuyenChiTiet = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");

  const NHAN_TRANG_THAI = {
    chua_khoi_hanh: "Chưa khởi hành",
    dang_chay: "Đang chạy",
    gap_su_co: "Gặp sự cố",
    hoan_thanh: "Hoàn thành",
    da_huy: "Đã hủy",
  };

  function pillTrangThai(trangThai) {
    if (trangThai === "chua_khoi_hanh") return "pill--gia-vinh-vien";
    if (trangThai === "dang_chay") return "pill--gia-thoi-han";
    if (trangThai === "gap_su_co") return "pill--do";
    return "pill--xam"; // hoan_thanh, da_huy
  }

  function mauTrangThai(trangThai) {
    if (trangThai === "chua_khoi_hanh") return "#16A34A";
    if (trangThai === "dang_chay") return "#D97706";
    if (trangThai === "gap_su_co") return "#DC2626";
    return "#9CA3AF"; // hoan_thanh, da_huy
  }

  // Chiều chuyến: mỗi chiều 1 màu riêng, đậm và khác hẳn các màu trạng thái (xanh lá/cam/đỏ/xám) để nhìn là phân biệt được
  const MAU_CHIEU = { xuoi: "#2563EB", nguoc: "#DB2777" };
  const mauChieu = (chieu) => MAU_CHIEU[chieu] || MAU_CHIEU.xuoi;
  const htmlChieu = (chieu) =>
    `<span class="chieu-huy-hieu chieu-huy-hieu--${chieu === "xuoi" ? "xuoi" : "nguoc"}">${chieu === "xuoi" ? "Xuôi →" : "← Ngược"}</span>`;

  function suaXoaDuoc(chuyen) {
    return !chuyen.xe_id && chuyen.trang_thai === "chua_khoi_hanh" && chuyen.so_ve_dang_hoat_dong === 0;
  }

  function lyDoKhongSuaDuoc(chuyen) {
    if (chuyen.xe_id) return "Đã gán xe — điều độ viên quản lý";
    if (chuyen.trang_thai !== "chua_khoi_hanh") return "Đã/đang khởi hành";
    return "Đã có khách đặt vé";
  }

  // ---------- Lộ trình từng tuyến (nạp theo yêu cầu, có cache) ----------
  const diemTheoTuyen = new Map(); // tuyen_id -> danh sách điểm (sắp theo thu_tu tăng dần)

  async function napDiemTuyen(tuyenId) {
    if (diemTheoTuyen.has(tuyenId)) return;
    const chiTiet = await apiGet(`/quan-ly/tuyen/${tuyenId}`).catch(() => null);
    diemTheoTuyen.set(tuyenId, [...(chiTiet?.danh_sach_diem || [])].sort((a, b) => a.thu_tu - b.thu_tu));
  }

  // Danh sách điểm + số phút cộng dồn TÍNH ĐÚNG THEO CHIỀU của chuyến — chiều
  // ngược đọc ngược danh sách, thời gian giữa 2 điểm liền kề giữ nguyên độ lớn
  // như chiều xuôi (NGHIEP_VU.md mục 3.1/2.4: thời gian di chuyển đối xứng 2 chiều).
  function loTrinhTheoChieu(tuyenId, chieu) {
    const diem = diemTheoTuyen.get(tuyenId);
    if (!diem || !diem.length) return [];
    const tongPhut = diem[diem.length - 1].thoi_gian_du_kien_phut;
    const ds = chieu === "xuoi" ? diem : [...diem].reverse();
    return ds.map((d) => ({
      ten: d.ten,
      ten_khu_vuc: d.ten_khu_vuc,
      loai: d.loai,
      phut: chieu === "xuoi" ? d.thoi_gian_du_kien_phut : tongPhut - d.thoi_gian_du_kien_phut,
    }));
  }

  function renderLoTrinhChuyen(c) {
    const diem = loTrinhTheoChieu(c.tuyen_id, c.chieu);
    if (!diem.length) return "";

    const goc = new Date(c.gio_khoi_hanh);
    const hang = diem
      .map((d, idx) => {
        const gioDiem = new Date(goc.getTime() + d.phut * 60000);
        const quaNgay = gioDiem.getDate() !== goc.getDate() || gioDiem.getMonth() !== goc.getMonth();
        const gioHienThi = `${pad2(gioDiem.getHours())}:${pad2(gioDiem.getMinutes())}`;
        return `
          <div class="nv-lt__hang">
            <span class="nv-chi-tiet-tuyen__thu-tu">${idx + 1}</span>
            <span class="lc-lo-trinh__gio">${gioHienThi}${quaNgay ? "<em>+1</em>" : ""}</span>
            <span class="nv-lt__ten">${esc(d.ten)}</span>
            <span><span class="pill pill--nho pill--khu-vuc">${esc(d.ten_khu_vuc)}</span></span>
            <span>${d.loai === "van_phong" ? '<span class="pill pill--primary">Văn phòng</span>' : '<span class="pill pill--diem-dung">Điểm dừng</span>'}</span>
          </div>`;
      })
      .join("");

    return `
      <div class="cy-ct__tieu-de">Lộ trình &amp; mốc thời gian</div>
      <div class="nv-lt">
        <div class="nv-lt__hang nv-lt__hang--dau">
          <span>#</span><span>Giờ</span><span>Điểm dừng</span><span>Khu vực</span><span>Loại</span>
        </div>
        ${hang}
      </div>`;
  }

  // ---------- Sơ đồ ghế kèm giá + bảng giá chặng ----------
  // Giá = bộ giá áp dụng cho ngày khởi hành × hệ số giá của chuyến × hệ số từng ghế (đều chốt lúc sinh chuyến, server tính).
  // Giá ghế phụ thuộc CHẶNG nên có bộ chọn chặng; mặc định chặng dài nhất (giá gốc cao nhất).
  const tien = (n) => Number(n).toLocaleString("vi-VN") + "đ";
  const soTien = (n) => Number(n).toLocaleString("vi-VN");
  const HE_SO_VE = 1.5; // phóng to sơ đồ so với bản vẽ gốc (ghế gốc 40×30) cho dễ nhìn
  const RONG_GHE = 40 * HE_SO_VE;
  const CAO_GHE = 30 * HE_SO_VE;

  let changDangChon = 0; // chỉ số trong bang_gia.cac_chang
  let gheDangChon = null; // mã ghế đang bấm xem chi tiết

  const NHAN_VE = {
    giu_cho: "Đang giữ chỗ",
    da_thanh_toan: "Đã thanh toán",
    da_len_xe: "Đã lên xe",
    da_xuong_xe: "Đã xuống xe",
  };

  // trống | giu (chỉ có vé giữ chỗ còn hạn) | ban (có vé đã thanh toán/lên/xuống xe — ở ít nhất 1 đoạn)
  function trangThaiGhe(maGhe, cacVe) {
    const ve = cacVe.filter((v) => v.so_ghe === maGhe);
    if (ve.some((v) => v.trang_thai !== "giu_cho")) return "ban";
    return ve.length ? "giu" : "trong";
  }

  const chonChangMacDinh = (bg) => {
    if (!bg || !bg.cac_chang.length) return 0;
    return bg.cac_chang.reduce((tot, ch, i, ds) => (ch.gia_goc > ds[tot].gia_goc ? i : tot), 0);
  };

  function renderTangSoDo(c, tang, chang) {
    const ghe = c.so_do_ghe;
    const minX = Math.min(...ghe.map((g) => g.x));
    const minY = Math.min(...ghe.map((g) => g.y));
    const rong = (Math.max(...ghe.map((g) => g.x)) - minX) * HE_SO_VE + RONG_GHE;
    const cao = (Math.max(...ghe.map((g) => g.y)) - minY) * HE_SO_VE + CAO_GHE;
    const nut = ghe
      .filter((g) => g.tang === tang)
      .map((g) => {
        const tt = trangThaiGhe(g.ma_ghe, c.cac_ve_tren_ghe);
        const heSo = Number(g.he_so);
        const gia = chang ? chang.gia_theo_ghe[g.ma_ghe] ?? chang.gia_ban : null;
        const lop = `ctn-ghe ctn-ghe--${tt}${heSo > 1 ? " ctn-ghe--dat" : heSo < 1 ? " ctn-ghe--re" : ""}${gheDangChon === g.ma_ghe ? " is-chon" : ""}`;
        const veGhe = c.cac_ve_tren_ghe.filter((v) => v.so_ghe === g.ma_ghe);
        const tieuDe = [
          `Ghế ${g.ma_ghe}${heSo !== 1 ? ` — hệ số ×${heSo}` : ""}${gia != null ? ` — ${tien(gia)}` : ""}`,
          ...veGhe.map((v) => `${v.ma_ve}: ${NHAN_VE[v.trang_thai] || v.trang_thai}, ${v.ten_diem_don} → ${v.ten_diem_tra}`),
        ].join("\n");
        return `<button type="button" class="${lop}" data-ghe="${esc(g.ma_ghe)}" title="${esc(tieuDe)}"
                  style="left:${(g.x - minX) * HE_SO_VE}px; top:${(g.y - minY) * HE_SO_VE + 26}px; width:${RONG_GHE}px; height:${CAO_GHE}px">
                  <b>${esc(g.ma_ghe)}</b>${gia != null ? `<span>${soTien(gia)}</span>` : ""}
                </button>`;
      })
      .join("");
    return `
      <div class="ctn-tang">
        ${c.so_tang > 1 ? `<div class="ctn-tang__ten">Tầng ${tang}</div>` : ""}
        <div class="ctn-canvas" style="width:${rong}px; height:${cao + 26}px">
          <div class="ctn-dau-xe">▲ Đầu xe</div>
          ${nut}
        </div>
      </div>`;
  }

  function renderKhuSoDo() {
    const c = chuyenDangXem;
    const box = noiDung.querySelector("#ctn-khu-so-do");
    if (!c.so_do_ghe.length) {
      box.innerHTML = '<div class="ct-khong-gia">Loại xe của chuyến chưa có sơ đồ ghế.</div>';
      return;
    }
    const bg = c.bang_gia;
    const chang = bg ? bg.cac_chang[changDangChon] : null;
    const tong = c.so_do_ghe.length;
    const dem = { ban: 0, giu: 0 };
    c.so_do_ghe.forEach((g) => {
      const tt = trangThaiGhe(g.ma_ghe, c.cac_ve_tren_ghe);
      if (tt !== "trong") dem[tt]++;
    });

    box.innerHTML = `
      ${
        bg
          ? `<div class="ctn-chang-chon" role="tablist" aria-label="Chặng xem giá ghế">
               <span class="nv-text-phu">Giá ghế theo chặng:</span>
               ${bg.cac_chang
                 .map((ch, i) => `<button type="button" class="ctn-chang-nut${i === changDangChon ? " is-active" : ""}" data-chang="${i}" role="tab">${esc(ch.ten_chang)}</button>`)
                 .join("")}
             </div>`
          : '<div class="ct-khong-gia">Chưa có bộ giá vé áp dụng cho ngày này — sơ đồ chưa có giá, khách không thấy chuyến này (mục Giá vé).</div>'
      }
      <div class="ctn-chu-thich">
        <span><i class="ctn-mau ctn-ghe--trong"></i>Trống (${tong - dem.ban - dem.giu})</span>
        <span><i class="ctn-mau ctn-ghe--giu"></i>Đang giữ chỗ (${dem.giu})</span>
        <span><i class="ctn-mau ctn-ghe--ban"></i>Có vé (${dem.ban})</span>
        <span class="ctn-chu-thich__gia"><b class="ctn-gia-dat">Giá cam</b> = đắt hơn ghế thường · <b class="ctn-gia-re">Giá xanh</b> = rẻ hơn</span>
      </div>
      <div class="ctn-so-do">${Array.from({ length: c.so_tang }, (_, i) => renderTangSoDo(c, i + 1, chang)).join("")}</div>
      <div class="ctn-ghe-info" id="ctn-ghe-info"></div>`;

    box.querySelectorAll("[data-chang]").forEach((b) =>
      b.addEventListener("click", () => {
        changDangChon = Number(b.dataset.chang);
        renderKhuSoDo();
        renderBangChang();
      })
    );
    box.querySelectorAll("[data-ghe]").forEach((b) =>
      b.addEventListener("click", () => {
        gheDangChon = gheDangChon === b.dataset.ghe ? null : b.dataset.ghe;
        renderKhuSoDo();
      })
    );
    renderThongTinGhe();
  }

  // Thông tin ghế đang bấm: tầng, hệ số, giá ở từng chặng, các vé đang chiếm ghế
  function renderThongTinGhe() {
    const c = chuyenDangXem;
    const o = noiDung.querySelector("#ctn-ghe-info");
    const g = c.so_do_ghe.find((x) => x.ma_ghe === gheDangChon);
    if (!g) {
      o.innerHTML = '<span class="nv-text-phu">Bấm vào một ghế để xem giá ở từng chặng và các vé đang giữ ghế đó.</span>';
      return;
    }
    const heSo = Number(g.he_so);
    const bg = c.bang_gia;
    const giaTungChang = bg
      ? bg.cac_chang.map((ch) => `<div><span>${esc(ch.ten_chang)}</span><b>${tien(ch.gia_theo_ghe[g.ma_ghe] ?? ch.gia_ban)}</b></div>`).join("")
      : "";
    const ve = c.cac_ve_tren_ghe.filter((v) => v.so_ghe === g.ma_ghe);
    o.innerHTML = `
      <div class="ctn-ghe-info__tieu"><strong>Ghế ${esc(g.ma_ghe)}</strong>${c.so_tang > 1 ? ` · Tầng ${g.tang}` : ""} · ${heSo === 1 ? "giá thường (hệ số 1)" : `hệ số ghế ×${heSo}`}</div>
      ${giaTungChang ? `<div class="ctn-ghe-info__chang">${giaTungChang}</div>` : ""}
      ${
        ve.length
          ? `<div class="ctn-ghe-info__ve">${ve
              .map((v) => `<div>${htmlMa(esc(v.ma_ve))} <span class="pill pill--nho ${v.trang_thai === "giu_cho" ? "pill--gia-thoi-han" : "pill--gia-vinh-vien"}">${NHAN_VE[v.trang_thai] || esc(v.trang_thai)}</span> ${esc(v.ten_diem_don)} → ${esc(v.ten_diem_tra)} · <b>${tien(v.gia)}</b></div>`)
              .join("")}</div>`
          : '<div class="nv-text-phu">Ghế đang trống.</div>'
      }`;
  }

  // Bảng giá từng chặng (giá gốc, giá ghế thường, khoảng giá khi các ghế khác giá) — bấm 1 dòng để xem giá ghế theo chặng đó
  function renderBangChang() {
    const c = chuyenDangXem;
    const bg = c.bang_gia;
    const box = noiDung.querySelector("#ctn-bang-chang");
    if (!bg) {
      box.innerHTML = "";
      return;
    }
    const ngayAp = bg.ap_dung_tu.split("-").reverse().join("/");
    const heSo = Number(bg.he_so_gia);
    const hang = bg.cac_chang
      .map((g, i) => `
        <button type="button" class="ctn-chang-hang${i === changDangChon ? " is-active" : ""}" data-chang="${i}">
          <span class="ctn-chang-hang__ten">${esc(g.ten_chang)}</span>
          <span class="ctn-chang-hang__goc">${heSo !== 1 ? `gốc ${tien(g.gia_goc)}` : ""}</span>
          <strong>${g.gia_thap_nhat === g.gia_cao_nhat ? tien(g.gia_ban) : `${tien(g.gia_thap_nhat)} – ${tien(g.gia_cao_nhat)}`}</strong>
        </button>`)
      .join("");
    const nhom = (bg.cac_nhom_ghe || [])
      .map((n) => `<div class="ct-gia__nhom"><b>×${Number(n.he_so)}</b> <span>${n.cac_ghe.map(esc).join(", ")}</span></div>`)
      .join("");
    box.innerHTML = `
      <div class="cy-ct__tieu-de">Giá vé từng chặng <span class="nv-text-phu">· bộ giá từ ${ngayAp}${heSo !== 1 ? ` · hệ số chuyến ×${heSo}` : ""}</span></div>
      <div class="ctn-chang-ds">${hang}</div>
      ${nhom ? `<div class="ct-gia__nhom-ds"><div class="nv-text-phu">Ghế khác giá (hệ số ghế đã chốt lúc sinh chuyến) — ghế còn lại giá thường:</div>${nhom}</div>` : ""}`;
    box.querySelectorAll("[data-chang]").forEach((b) =>
      b.addEventListener("click", () => {
        changDangChon = Number(b.dataset.chang);
        renderKhuSoDo();
        renderBangChang();
      })
    );
  }

  // ---------- Modal ----------
  let modal = null;
  let noiDung = null;
  let chuyenDangXem = null;
  let onThayDoi = () => {};

  function dungModal() {
    if (modal) return;
    modal = document.createElement("div");
    modal.className = "nv-modal-overlay";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="nv-modal ctn-modal">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 12h18M3 12l4-5M3 12l4 5M21 12l-4-5M21 12l-4 5"/>
            </svg>
          </div>
          <h2>Chi tiết chuyến</h2>
        </div>
        <div class="nv-modal__body" id="ct-noi-dung">Đang tải...</div>
      </div>`;
    document.body.appendChild(modal);
    noiDung = modal.querySelector("#ct-noi-dung");
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.hidden = true;
    });
  }

  async function mo(chuyenId, tuyChon = {}) {
    dungModal();
    onThayDoi = tuyChon.onThayDoi || (() => {});
    noiDung.innerHTML = "Đang tải...";
    document.body.appendChild(modal); // xuống cuối body để hiện đè lên modal khác đang mở
    modal.hidden = false;
    try {
      chuyenDangXem = await apiGet(`/quan-ly/chuyen/${chuyenId}`);
      await napDiemTuyen(chuyenDangXem.tuyen_id);
      changDangChon = chonChangMacDinh(chuyenDangXem.bang_gia);
      gheDangChon = null;
      renderChiTiet();
    } catch (err) {
      noiDung.innerHTML = `<div class="text-error">${esc(err.message)}</div><div class="nv-modal__actions"><button type="button" class="nv-btn-secondary" id="ct-btn-dong">Đóng</button></div>`;
      noiDung.querySelector("#ct-btn-dong").addEventListener("click", () => { modal.hidden = true; });
    }
  }

  function renderChiTiet() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const ngayGioHienThi = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} · ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    const coTheSua = suaXoaDuoc(c);
    const heSoChuyen = Number(c.he_so_gia);

    noiDung.innerHTML = `
      <div class="cy-ct-dau" style="--mau:${mauTrangThai(c.trang_thai)}">
        <div class="cy-ct-dau__gio">${pad2(d.getHours())}:${pad2(d.getMinutes())}</div>
        <div class="cy-ct-dau__info">
          <strong>${esc(c.ten_tuyen)}</strong>
          <span class="nv-text-phu">${ngayGioHienThi}</span>
        </div>
        ${htmlChieu(c.chieu)}
        <span class="pill pill--nho ${pillTrangThai(c.trang_thai)}">${NHAN_TRANG_THAI[c.trang_thai] || c.trang_thai}</span>
      </div>

      <div class="ctn-meta">
        <div><span>Mã chuyến</span>${htmlMa(esc(c.ma))}</div>
        <div><span>Loại xe</span><b>${esc(c.ma_loai_xe)} · ${esc(c.ten_loai_xe)}</b><em>${c.so_do_ghe.length} ghế${c.so_tang > 1 ? ` · ${c.so_tang} tầng` : ""}</em></div>
        <div><span>Xe</span>${c.bien_so_xe ? `<span class="pill pill--nho pill--gia-vinh-vien">${esc(c.bien_so_xe)}</span>` : '<span class="pill pill--nho pill--gia-thoi-han">Chưa gán xe</span>'}</div>
        <div><span>Vé đang giữ / đã bán</span><b>${c.so_ve_dang_hoat_dong}</b></div>
        <div><span>Hệ số giá chuyến</span><b>×${heSoChuyen}</b></div>
      </div>

      <div class="ctn-luoi">
        <section class="ctn-cot ctn-cot--so-do">
          <div class="cy-ct__tieu-de">Sơ đồ ghế &amp; giá</div>
          <div id="ctn-khu-so-do"></div>
        </section>
        <section class="ctn-cot">
          <div id="ctn-bang-chang"></div>
          ${renderLoTrinhChuyen(c)}
        </section>
      </div>

      <div id="ct-form-sua" hidden></div>

      <div class="nv-modal__actions">
        <button type="button" class="nv-btn-secondary" id="ct-btn-dong">Đóng</button>
        ${
          coTheSua
            ? `<button type="button" class="nv-btn-secondary" id="ct-btn-sua">Sửa giờ</button><button type="button" class="nv-btn-xoa" id="ct-btn-xoa" style="flex:1; border-radius:var(--radius-button);">Xóa chuyến</button>`
            : ""
        }
      </div>
      ${coTheSua ? "" : `<p class="nv-hint" style="margin-top:10px;">${lyDoKhongSuaDuoc(c)} — không thể sửa/xóa ở đây.</p>`}
    `;

    renderKhuSoDo();
    renderBangChang();

    noiDung.querySelector("#ct-btn-dong").addEventListener("click", () => {
      modal.hidden = true;
    });

    if (coTheSua) {
      noiDung.querySelector("#ct-btn-sua").addEventListener("click", moFormSuaGio);
      noiDung.querySelector("#ct-btn-xoa").addEventListener("click", xoaChuyenHienTai);
    }
  }

  function moFormSuaGio() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const gioStr = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    const box = noiDung.querySelector("#ct-form-sua");

    box.innerHTML = `
      <div class="nv-form-row">
        <div><label class="nv-label" for="ct-sua-gio">Giờ khởi hành</label><input class="input-field" type="time" id="ct-sua-gio" value="${gioStr}" /></div>
      </div>
      <div id="ct-sua-loi" class="text-error" hidden></div>
      <div class="cy-ct__nut">
        <button type="button" class="nv-btn-secondary" id="ct-sua-huy">Hủy</button>
        <button type="button" class="btn-primary cy-ct__luu" id="ct-sua-luu">Lưu</button>
      </div>`;
    box.hidden = false;

    box.querySelector("#ct-sua-huy").addEventListener("click", () => {
      box.hidden = true;
      box.innerHTML = "";
    });

    box.querySelector("#ct-sua-luu").addEventListener("click", async () => {
      const gio = box.querySelector("#ct-sua-gio").value;
      const loiEl = box.querySelector("#ct-sua-loi");
      loiEl.hidden = true;
      if (!gio) {
        loiEl.textContent = "Chọn giờ khởi hành";
        loiEl.hidden = false;
        return;
      }
      try {
        chuyenDangXem = await apiPut(`/quan-ly/chuyen/${chuyenDangXem.id}`, { gio: `${gio}:00` });
        renderChiTiet();
        onThayDoi();
      } catch (err) {
        loiEl.textContent = err.message;
        loiEl.hidden = false;
      }
    });
  }

  async function xoaChuyenHienTai() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const ngayHienThi = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
    if (!confirm(`Xóa chuyến "${c.ten_tuyen}" ngày ${ngayHienThi}? Không thể hoàn tác.`)) return;
    try {
      await apiDelete(`/quan-ly/chuyen/${c.id}`);
      modal.hidden = true;
      onThayDoi();
    } catch (err) {
      alert(err.message);
    }
  }

  return { mo, NHAN_TRANG_THAI, pillTrangThai, mauTrangThai, mauChieu, htmlChieu };
})();
