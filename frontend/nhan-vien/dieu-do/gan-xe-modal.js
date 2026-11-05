// Modal "Gán xe cho chu trình" của điều độ viên: bên trái là lộ trình + vị trí các xe lúc khởi hành, bên phải là danh sách xe
// (cả xe không phù hợp, kèm lý do) + chi tiết xe đang chọn với sơ đồ ghế xem khi cần.
// Dùng: GanXeModal.mo(chuTrinh, { khiXong(ketQua) }) — chuTrinh là một phần tử của GET /dieu-do/chu-trinh.
const GanXeModal = (() => {
  const MUI_GIO = "Asia/Ho_Chi_Minh";
  const HE_SO_VE = 1.5; // cùng tỉ lệ vẽ sơ đồ ghế với trang Chuyến của quản lý (lớp ctn-*)
  const RONG_GHE = 60;
  const CAO_GHE = 45;
  const NHAN_LY_DO = {
    khong_hoat_dong: "Đang bảo trì",
    khac_loai: "Khác loại xe",
    tuyen_co_dinh: "Xe tuyến khác",
    trung_lich: "Trùng lịch",
    sai_vi_tri: "Sai vị trí",
    hong_chuyen_ke_tiep: "Vỡ chuyến kế tiếp",
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const boDau = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();

  function phan(iso) {
    const p = Object.fromEntries(
      new Intl.DateTimeFormat("en-GB", { timeZone: MUI_GIO, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
        .formatToParts(new Date(iso)).map((x) => [x.type, x.value]),
    );
    return { nam: +p.year, thang: +p.month, ngay: +p.day, gio: +p.hour, phut: +p.minute };
  }
  const gioPhut = (iso) => { const p = phan(iso); return `${pad2(p.gio)}:${pad2(p.phut)}`; };
  const ngayThang = (iso) => { const p = phan(iso); return `${pad2(p.ngay)}/${pad2(p.thang)}`; };
  const soNgayLech = (a, b) => {
    const x = phan(a), y = phan(b);
    return Math.round((Date.UTC(y.nam, y.thang - 1, y.ngay) - Date.UTC(x.nam, x.thang - 1, x.ngay)) / 86400000);
  };
  // "20:00 → 02:00⁺¹" (dấu +1 dạng mũ, lớp .qua-ngay của style.css)
  function khoangGio(c) {
    if (!c.gio_ket_thuc) return gioPhut(c.gio_khoi_hanh);
    const lech = soNgayLech(c.gio_khoi_hanh, c.gio_ket_thuc);
    return `${gioPhut(c.gio_khoi_hanh)} → ${gioPhut(c.gio_ket_thuc)}${lech > 0 ? `<em class="qua-ngay">+${lech}</em>` : ""}`;
  }
  // Giờ đến một điểm: kèm ngày khi khác ngày khởi hành của chuyến
  function gioDen(iso, mocIso) {
    const lech = soNgayLech(mocIso, iso);
    return `${gioPhut(iso)}${lech > 0 ? `<em class="qua-ngay">+${lech}</em>` : ""}`;
  }

  // ---------- Trạng thái của lần mở hiện tại ----------
  let overlay = null;
  let ct = null; // chu trình (từ danh sách)
  let loTrinh = null;
  let dsXe = [];
  let chon = null; // xe_id đang chọn
  let loc = "phu_hop"; // phu_hop | khong | tat_ca
  let tuKhoa = "";
  let xemSoDo = false;
  let khiXong = () => {};
  const boNhoLoaiXe = new Map(); // loai_xe_id -> sơ đồ ghế (mỗi loại chỉ nạp một lần)

  function dungOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.className = "nv-modal-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="nv-modal gxm" role="dialog" aria-modal="true" aria-labelledby="gxm-tieu-de">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="11" rx="2.5"/><path d="M3 11h18M7 16v3M17 16v3"/></svg>
          </div>
          <h2 id="gxm-tieu-de">Chọn xe cho chu trình</h2>
          <button type="button" class="gxm__dong" id="gxm-dong" aria-label="Đóng">×</button>
        </div>
        <div class="nv-modal__body gxm__body" id="gxm-noi-dung"></div>
        <div class="gxm__chan">
          <span class="text-error" id="gxm-loi" hidden></span>
          <span class="gxm__chan-gia"></span>
          <button type="button" class="nv-btn-secondary" id="gxm-huy">Hủy</button>
          <button type="button" class="btn-primary" id="gxm-xac-nhan" disabled>Gán xe</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) dong(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !overlay.hidden) dong(); });
    overlay.querySelector("#gxm-dong").addEventListener("click", dong);
    overlay.querySelector("#gxm-huy").addEventListener("click", dong);
    overlay.querySelector("#gxm-xac-nhan").addEventListener("click", xacNhan);
    return overlay;
  }

  const dong = () => { if (overlay) overlay.hidden = true; };
  const xeDangChon = () => dsXe.find((x) => String(x.xe_id) === String(chon));
  const hopLe = (x) => x.hop_le;

  // ---------- Cột trái: tóm tắt, lộ trình, vị trí xe ----------
  function htmlChipXe(x) {
    return `<button type="button" class="gxm-chip ${x.hop_le ? "gxm-chip--ok" : "gxm-chip--khong"}${String(x.xe_id) === String(chon) ? " is-chon" : ""}" data-xe="${esc(x.xe_id)}" title="${esc(x.hop_le ? "Gán được" : x.ly_do.join("; "))}">${esc(x.bien_so)}</button>`;
  }

  function htmlLoTrinh() {
    const dau = loTrinh.cac_chuyen[0];
    const xeTheoDiem = new Map();
    dsXe.forEach((x) => {
      const k = String(x.vi_tri.diem_id);
      if (!xeTheoDiem.has(k)) xeTheoDiem.set(k, []);
      xeTheoDiem.get(k).push(x);
    });
    const trenTuyen = new Set(dau.diem.map((d) => String(d.diem_don_tra_id)));

    const cacChang = loTrinh.cac_chuyen.map((c) => `
      <div class="gxm-chuyen">
        <div class="gxm-chuyen__tieu">
          <span class="gx-chieu ${c.chieu === "xuoi" ? "gx-chieu--di" : "gx-chieu--ve"}">${c.chieu === "xuoi" ? "Đi" : "Về"}</span>
          <b>${khoangGio(c)}</b><span class="nv-text-phu">${ngayThang(c.gio_khoi_hanh)}</span>
        </div>
        <ol class="gxm-diem">
          ${c.diem.map((d, i) => {
            const dauCuoi = i === 0 || i === c.diem.length - 1;
            const xeTai = c === dau ? xeTheoDiem.get(String(d.diem_don_tra_id)) || [] : [];
            return `<li class="gxm-diem__dong${dauCuoi ? " gxm-diem__dong--moc" : ""}">
              <span class="gxm-diem__gio">${gioDen(d.gio_den, c.gio_khoi_hanh)}</span>
              <span class="gxm-diem__cham"></span>
              <span class="gxm-diem__ten">${esc(d.ten)}<small>${esc(d.ten_khu_vuc)}</small></span>
              ${xeTai.length ? `<span class="gxm-diem__xe">${xeTai.map(htmlChipXe).join("")}</span>` : ""}
            </li>`;
          }).join("")}
        </ol>
      </div>`).join("");

    // Xe đang ở điểm không nằm trên lộ trình chu trình
    const ngoai = [...xeTheoDiem.entries()].filter(([k]) => !trenTuyen.has(k));
    const khoiNgoai = ngoai.length
      ? `<div class="gxm-ngoai">
          <div class="gxm-muc__tieu">Xe đang ở ngoài lộ trình</div>
          ${ngoai.map(([, xs]) => `<div class="gxm-ngoai__dong"><span class="gxm-ngoai__ten">${esc(xs[0].vi_tri.ten_diem)}</span><span class="gxm-diem__xe">${xs.map(htmlChipXe).join("")}</span></div>`).join("")}
        </div>`
      : "";

    return `
      <div class="gxm-muc">
        <div class="gxm-muc__tieu">Lộ trình chu trình <span class="nv-text-phu">· chip là xe dự kiến có mặt tại điểm lúc ${gioPhut(dau.gio_khoi_hanh)}</span></div>
        <div class="gxm-chuyen-luoi">${cacChang}</div>
        <div class="gxm-chu-giai"><i class="gxm-chip gxm-chip--ok"></i>Gán được <i class="gxm-chip gxm-chip--khong"></i>Không phù hợp</div>
        ${khoiNgoai}
      </div>`;
  }

  function htmlTomTat() {
    const lx = loTrinh.loai_xe_cam_ket;
    return `
      <div class="gxm-tom-tat">
        <div><strong>${esc(loTrinh.tuyen.ten)}</strong> ${htmlMa(esc(loTrinh.tuyen.ma))}</div>
        <div class="gxm-tom-tat__loai">Loại xe cam kết với khách: <b>${esc(lx.ten)}</b> · ${lx.so_ghe} ghế${lx.so_tang > 1 ? ` · ${lx.so_tang} tầng` : ""}</div>
      </div>`;
  }

  // ---------- Cột phải: danh sách xe ----------
  function xeLoc() {
    const k = boDau(tuKhoa.trim());
    return dsXe.filter((x) => (loc === "tat_ca" || (loc === "phu_hop") === hopLe(x)) && (!k || boDau(x.bien_so).includes(k) || boDau(x.loai_xe.ten).includes(k) || boDau(x.loai_xe.ma).includes(k)));
  }

  function htmlDongXe(x) {
    const nhan = x.ma_ly_do.map((m) => `<span class="gxm-nhan">${esc(NHAN_LY_DO[m] || m)}</span>`).join("");
    return `
      <button type="button" class="gxm-xe${hopLe(x) ? "" : " gxm-xe--khong"}${String(x.xe_id) === String(chon) ? " is-chon" : ""}" data-xe="${esc(x.xe_id)}">
        <span class="gxm-xe__dong1"><span class="xe-bien-so gx-bien-so">${esc(x.bien_so)}</span>${x.dang_gan ? '<span class="pill pill--nho pill--gia-vinh-vien">Đang gán</span>' : ""}${hopLe(x) ? '<span class="gxm-ok">Gán được</span>' : nhan}</span>
        <span class="gxm-xe__dong2">${esc(x.loai_xe.ma)} · ${esc(x.loai_xe.ten)} · ${x.loai_xe.so_ghe} ghế</span>
        <span class="gxm-xe__dong2">Vị trí: <b>${esc(x.vi_tri.ten_diem)}</b>${x.vi_tri.nguon === "sau_chuyen" ? ` · sau chuyến ${esc(x.vi_tri.chuyen_ma)}` : " · điểm gốc"}</span>
      </button>`;
  }

  function htmlBoLoc() {
    const dem = { phu_hop: dsXe.filter(hopLe).length, khong: dsXe.filter((x) => !hopLe(x)).length, tat_ca: dsXe.length };
    const chip = (ma, nhan) => `<button type="button" class="gxm-loc${loc === ma ? " is-active" : ""}" data-loc="${ma}">${nhan} <b>${dem[ma]}</b></button>`;
    return `
      <div class="gxm-loc-hang">${chip("phu_hop", "Phù hợp")}${chip("khong", "Không phù hợp")}${chip("tat_ca", "Tất cả")}</div>
      <input type="search" class="gxm-tim" id="gxm-tim" placeholder="Tìm biển số hoặc loại xe" value="${esc(tuKhoa)}" autocomplete="off" />`;
  }

  // ---------- Chi tiết xe đang chọn ----------
  function htmlSoDo(loai) {
    const ghe = loai.so_do_ghe;
    if (!ghe.length) return '<div class="kv-trong">Loại xe này chưa có sơ đồ ghế.</div>';
    const minX = Math.min(...ghe.map((g) => g.x));
    const minY = Math.min(...ghe.map((g) => g.y));
    const rong = (Math.max(...ghe.map((g) => g.x)) - minX) * HE_SO_VE + RONG_GHE;
    const cao = (Math.max(...ghe.map((g) => g.y)) - minY) * HE_SO_VE + CAO_GHE;
    const tang = (t) => `
      <div class="ctn-tang">
        ${loai.so_tang > 1 ? `<div class="ctn-tang__ten">Tầng ${t}</div>` : ""}
        <div class="ctn-canvas" style="width:${rong}px; height:${cao + 26}px">
          <div class="ctn-dau-xe">▲ Đầu xe</div>
          ${ghe.filter((g) => g.tang === t).map((g) => `<div class="ctn-ghe ctn-ghe--trong" style="left:${(g.x - minX) * HE_SO_VE}px; top:${(g.y - minY) * HE_SO_VE + 26}px; width:${RONG_GHE}px; height:${CAO_GHE}px"><b>${esc(g.ma_ghe)}</b></div>`).join("")}
        </div>
      </div>`;
    return `<div class="ctn-so-do gxm-so-do">${Array.from({ length: loai.so_tang }, (_, i) => tang(i + 1)).join("")}</div>`;
  }

  function htmlChiTiet() {
    const x = xeDangChon();
    if (!x) return '<div class="gxm-chi-tiet gxm-chi-tiet--rong">Chọn một xe để xem loại xe, vị trí, lý do và sơ đồ ghế.</div>';
    const lx = x.loai_xe;
    const viTri = x.vi_tri;
    const duLieuLoai = boNhoLoaiXe.get(String(lx.id));
    const khuSoDo = !xemSoDo
      ? ""
      : duLieuLoai === undefined
        ? '<div class="kv-trong">Đang tải sơ đồ ghế...</div>'
        : duLieuLoai === null
          ? '<div class="text-error">Không tải được sơ đồ ghế.</div>'
          : htmlSoDo(duLieuLoai);
    return `
      <div class="gxm-chi-tiet">
        <div class="gxm-chi-tiet__dau">
          <span class="xe-bien-so gx-bien-so">${esc(x.bien_so)}</span>
          <span class="gxm-chi-tiet__trang-thai ${x.hop_le ? "gxm-ok" : "gxm-khong"}">${x.hop_le ? "Gán được cho chu trình này" : "Không gán được"}</span>
        </div>
        <dl class="gxm-kv">
          <dt>Loại xe</dt><dd>${esc(lx.ma)} · ${esc(lx.ten)} · ${lx.so_ghe} ghế${lx.so_tang > 1 ? ` · ${lx.so_tang} tầng` : ""}${x.dung_loai ? "" : ' <span class="gxm-nhan">khác loại cam kết</span>'}</dd>
          <dt>Trạng thái</dt><dd>${x.trang_thai_xe === "hoat_dong" ? "Hoạt động" : "Đang bảo trì"}${x.tuyen_co_dinh ? ` · chỉ chạy tuyến ${esc(x.tuyen_co_dinh.ma)}` : " · xe dự phòng (không cố định tuyến)"}</dd>
          <dt>Vị trí lúc khởi hành</dt><dd><b>${esc(viTri.ten_diem)}</b> ${viTri.nguon === "sau_chuyen" ? `— sau chuyến ${esc(viTri.chuyen_ma)}, tới lúc ${gioPhut(viTri.tu_luc)} ${ngayThang(viTri.tu_luc)}` : "— điểm gốc của xe"}</dd>
          ${x.chuyen_ke_tiep ? `<dt>Chuyến kế tiếp</dt><dd>${esc(x.chuyen_ke_tiep.ma)} · ${gioPhut(x.chuyen_ke_tiep.gio_khoi_hanh)} ${ngayThang(x.chuyen_ke_tiep.gio_khoi_hanh)} · ${esc(x.chuyen_ke_tiep.ten_diem_di)} → ${esc(x.chuyen_ke_tiep.ten_diem_den)}</dd>` : ""}
        </dl>
        ${x.ly_do.length ? `<ul class="gxm-ly-do">${x.ly_do.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}
        <button type="button" class="gxm-nut-so-do" id="gxm-nut-so-do" aria-expanded="${xemSoDo}">${xemSoDo ? "Ẩn sơ đồ ghế" : "Xem sơ đồ ghế"}</button>
        ${khuSoDo}
      </div>`;
  }

  // ---------- Vẽ lại ----------
  function veLai() {
    const goc = overlay.querySelector("#gxm-noi-dung");
    // giữ vị trí cuộn của danh sách xe khi vẽ lại
    const cuonDs = goc.querySelector("#gxm-ds")?.scrollTop || 0;
    const timFocus = document.activeElement?.id === "gxm-tim";
    const ds = xeLoc();
    goc.innerHTML = `
      <div class="gxm-luoi">
        <div class="gxm-trai">${htmlTomTat()}${htmlLoTrinh()}</div>
        <div class="gxm-phai">
          ${htmlBoLoc()}
          <div class="gxm-ds" id="gxm-ds">${ds.length ? ds.map(htmlDongXe).join("") : '<div class="kv-trong">Không có xe nào trong nhóm này.</div>'}</div>
          ${htmlChiTiet()}
        </div>
      </div>`;
    goc.querySelector("#gxm-ds").scrollTop = cuonDs;
    if (timFocus) { const o = goc.querySelector("#gxm-tim"); o.focus(); o.setSelectionRange(o.value.length, o.value.length); }
    goc.querySelectorAll("[data-xe]").forEach((b) => b.addEventListener("click", () => chonXe(b.dataset.xe)));
    goc.querySelectorAll("[data-loc]").forEach((b) => b.addEventListener("click", () => { loc = b.dataset.loc; veLai(); }));
    goc.querySelector("#gxm-tim").addEventListener("input", (e) => { tuKhoa = e.target.value; veLai(); });
    goc.querySelector("#gxm-nut-so-do")?.addEventListener("click", () => { xemSoDo = !xemSoDo; veLai(); nap1LoaiXe(); });
    capNhatNutXacNhan();
  }

  function chonXe(id) {
    chon = id;
    xemSoDo = false; // sơ đồ chỉ mở khi người dùng bấm, không tự mở lại theo xe mới
    overlay.querySelector("#gxm-loi").hidden = true;
    veLai();
  }

  async function nap1LoaiXe() {
    const x = xeDangChon();
    if (!xemSoDo || !x || boNhoLoaiXe.has(String(x.loai_xe.id))) return;
    const idLoai = String(x.loai_xe.id);
    try {
      boNhoLoaiXe.set(idLoai, await apiGet(`/dieu-do/loai-xe/${encodeURIComponent(idLoai)}`));
    } catch {
      boNhoLoaiXe.set(idLoai, null);
    }
    if (!overlay.hidden && xemSoDo) veLai();
  }

  function capNhatNutXacNhan() {
    const x = xeDangChon();
    const nut = overlay.querySelector("#gxm-xac-nhan");
    nut.disabled = !(x && x.hop_le);
    overlay.querySelector(".gxm__chan-gia").textContent = x ? (x.hop_le ? `Gán ${x.bien_so} cho cả chuyến đi và chuyến về` : `${x.bien_so} không gán được — xem lý do bên phải`) : "";
  }

  async function xacNhan() {
    const x = xeDangChon();
    if (!x || !x.hop_le) return;
    const loiEl = overlay.querySelector("#gxm-loi");
    const nut = overlay.querySelector("#gxm-xac-nhan");
    loiEl.hidden = true;
    nut.disabled = true;
    try {
      const kq = await apiPut(`/dieu-do/chu-trinh/${encodeURIComponent(ct.chu_trinh_id)}/xe`, { xe_id: x.xe_id });
      dong();
      await khiXong(kq);
    } catch (err) {
      loiEl.textContent = err.message;
      loiEl.hidden = false;
      nut.disabled = false;
    }
  }

  async function mo(chuTrinh, tuyChon = {}) {
    ct = chuTrinh;
    khiXong = tuyChon.khiXong || (() => {});
    loTrinh = null; dsXe = []; chon = null; loc = "phu_hop"; tuKhoa = ""; xemSoDo = false;
    const ov = dungOverlay();
    const goc = ov.querySelector("#gxm-noi-dung");
    ov.querySelector("#gxm-loi").hidden = true;
    ov.querySelector("#gxm-xac-nhan").disabled = true;
    ov.querySelector(".gxm__chan-gia").textContent = "";
    goc.innerHTML = '<div class="kv-trong">Đang tải lộ trình và danh sách xe...</div>';
    ov.hidden = false;
    try {
      const id = encodeURIComponent(ct.chu_trinh_id);
      [loTrinh, dsXe] = await Promise.all([apiGet(`/dieu-do/chu-trinh/${id}/lo-trinh`), apiGet(`/dieu-do/chu-trinh/${id}/xe`)]);
    } catch (err) {
      goc.innerHTML = `<div class="text-error">${esc(err.message)}</div>`;
      return;
    }
    // Mở sẵn xe đang gán (nếu có) để xem được ngay xe hiện tại của chu trình
    const dangGan = dsXe.find((x) => x.dang_gan);
    if (dangGan) chon = dangGan.xe_id;
    veLai();
  }

  return { mo };
})();
