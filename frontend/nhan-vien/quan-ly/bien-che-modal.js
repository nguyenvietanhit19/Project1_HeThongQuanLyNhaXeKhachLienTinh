/*
 * Hộp "Biên chế xe" của Quản lý (UC-35, NGHIEP_VU.md mục 3.2): bên trái là biên chế hiện tại của xe (2 tài xế + ít nhất 1 phụ xe, chỗ còn trống
 * hiện rõ), bên phải là danh sách nhân sự đang làm để thêm — lọc theo chức danh / đã có xe chưa, tìm theo mã, tên, số điện thoại, email,
 * biển số xe. Bấm vào ai cũng mở một HỘP CHI TIẾT riêng (có dấu × để đóng, đè lên hộp này để không che danh sách) hiện TOÀN BỘ hồ sơ nhân sự
 * (chỉ xem): thông tin cá nhân, ảnh, giấy tờ, tài khoản, đang ở xe nào... rồi mới quyết định thêm.
 * Dùng: BienCheModal.mo(xe, { khiDong }) với xe là một phần tử của GET /quan-ly/xe. Cần nạp SAU api-client.js (apiGet, apiPost, apiDelete, htmlMa).
 */
const BienCheModal = (() => {
  const SO_TAI_XE = 2;
  const SO_PHU_XE_TOI_THIEU = 1;
  const NHAN_TINH_TRANG = { con_han: "Còn hạn", sap_het_han: "Sắp hết hạn", het_han: "Đã hết hạn" };
  const NHAN_GIAY_TO = { bang_lai: "Bằng lái xe", giay_kham_suc_khoe: "Giấy khám sức khỏe" };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const boDau = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  const chuCaiDau = (ten) => (String(ten || "?").trim().split(/\s+/).pop() || "?").charAt(0).toUpperCase();
  const ngayVN = (iso) => (iso ? iso.split("-").reverse().join("/") : "—");

  function soThang(tuIso) {
    const [y, m] = tuIso.split("-").map(Number);
    const bay = new Date();
    return (bay.getFullYear() - y) * 12 + (bay.getMonth() + 1 - m);
  }

  function thamNien(ngayVaoLam) {
    if (!ngayVaoLam) return "";
    const tong = soThang(ngayVaoLam);
    if (tong < 1) return "dưới 1 tháng";
    const nam = Math.floor(tong / 12);
    const thang = tong % 12;
    return [nam ? `${nam} năm` : "", thang ? `${thang} tháng` : ""].filter(Boolean).join(" ");
  }

  const tuoi = (ngaySinh) => (ngaySinh ? Math.floor(soThang(ngaySinh) / 12) : null);

  // ---------- Trạng thái của lần mở hiện tại ----------
  let overlay = null;
  let overlayCt = null; // hộp chi tiết nhân sự (đè lên hộp biên chế)
  let xe = null;
  let dsBienChe = [];
  let dsUngVien = [];
  let chonId = null; // nhân sự đang xem chi tiết
  let tab = "tai_xe"; // tai_xe | phu_xe | tat_ca
  let loc = "chua_co_xe"; // chua_co_xe | o_xe_khac | tat_ca
  let tuKhoa = "";
  let thongBao = null; // { loi: bool, noi_dung }
  let khiDong = () => {};
  const chiTietCache = new Map(); // nhan_su_id -> chi tiết | "dang_tai" | { loi }

  const laXeDuPhong = () => !xe.tuyen_id;
  const hieuLuc = (d) => d.trang_thai === "dang_hoat_dong" && d.trang_thai_nhan_su !== "da_nghi_viec";
  const theoChucDanh = (cd) => dsBienChe.filter((d) => d.chuc_danh === cd);

  function tinhTrangBienChe() {
    const tx = theoChucDanh("tai_xe").filter(hieuLuc).length;
    const px = theoChucDanh("phu_xe").filter(hieuLuc).length;
    const thieuTx = Math.max(SO_TAI_XE - tx, 0);
    const thieuPx = Math.max(SO_PHU_XE_TOI_THIEU - px, 0);
    return { tx, px, thieuTx, thieuPx, du: !thieuTx && !thieuPx };
  }

  function dungOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.className = "nv-modal-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="nv-modal bcm" role="dialog" aria-modal="true" aria-labelledby="bcm-tieu-de">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5a3 3 0 0 1 0 6M18 14c1.8.6 3 2.3 3 4"/>
            </svg>
          </div>
          <h2 id="bcm-tieu-de">Biên chế xe</h2>
          <button type="button" class="bcm__dong" id="bcm-x" aria-label="Đóng">×</button>
        </div>
        <div class="nv-modal__body bcm__body" id="bcm-noi-dung"></div>
        <div class="bcm__chan">
          <span class="bcm__chan-ghi" id="bcm-chan-ghi"></span>
          <button type="button" class="nv-btn-secondary" id="bcm-dong">Đóng</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) dong(); });
    // Esc đóng hộp trên cùng trước: đang mở chi tiết thì chỉ đóng chi tiết
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || overlay.hidden) return;
      if (overlayCt && !overlayCt.hidden) dongChiTiet();
      else dong();
    });
    overlay.querySelector("#bcm-x").addEventListener("click", dong);
    overlay.querySelector("#bcm-dong").addEventListener("click", dong);
    return overlay;
  }

  function dong() {
    if (overlayCt) overlayCt.hidden = true;
    if (overlay) overlay.hidden = true;
    khiDong();
  }

  // ---------- Hộp chi tiết nhân sự ----------
  function dungOverlayCt() {
    if (overlayCt) return overlayCt;
    overlayCt = document.createElement("div");
    overlayCt.className = "nv-modal-overlay bcm-ct-overlay";
    overlayCt.hidden = true;
    overlayCt.innerHTML = `
      <div class="nv-modal bcm-ct-modal" role="dialog" aria-modal="true" aria-labelledby="bcm-ct-tieu-de">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/></svg>
          </div>
          <h2 id="bcm-ct-tieu-de">Hồ sơ nhân sự</h2>
          <button type="button" class="bcm__dong" id="bcm-ct-x" aria-label="Đóng thông tin nhân sự">×</button>
        </div>
        <div class="nv-modal__body bcm-ct-modal__body" id="bcm-ct-noi-dung"></div>
      </div>`;
    document.body.appendChild(overlayCt);
    overlayCt.addEventListener("click", (e) => { if (e.target === overlayCt) dongChiTiet(); });
    overlayCt.querySelector("#bcm-ct-x").addEventListener("click", dongChiTiet);
    return overlayCt;
  }

  function dongChiTiet() {
    if (overlayCt) overlayCt.hidden = true;
    chonId = null;
    if (!overlay.hidden) veLai(); // bỏ nổi bật dòng đang xem
  }

  function veChiTiet() {
    const goc = dungOverlayCt().querySelector("#bcm-ct-noi-dung");
    goc.innerHTML = htmlChiTiet();
    goc.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); goBienChe(b.dataset.go); }));
    goc.querySelector("[data-them]")?.addEventListener("click", (e) => themBienChe(e.currentTarget.dataset.them));
  }

  // ---------- Cột trái: biên chế hiện tại ----------
  function htmlBadgeNguoiTrongXe(d) {
    const b = [];
    if (d.loai === "tam_thoi") b.push('<span class="bcm-nhan bcm-nhan--vang">Tạm thời</span>');
    if (d.trang_thai === "tam_nghi") b.push('<span class="bcm-nhan bcm-nhan--xam">Tạm nghỉ</span>');
    if (d.trang_thai_nhan_su === "da_nghi_viec") b.push('<span class="bcm-nhan bcm-nhan--do">Đã nghỉ việc — không tính</span>');
    return b.join("");
  }

  function htmlNguoiTrongXe(d) {
    return `
      <div class="bcm-nguoi${chonId === d.nhan_su_van_hanh_id ? " is-chon" : ""}${hieuLuc(d) ? "" : " bcm-nguoi--mo"}" data-xem="${esc(d.nhan_su_van_hanh_id)}" tabindex="0" role="button">
        <span class="bcm-avatar">${esc(chuCaiDau(d.ho_ten))}</span>
        <span class="bcm-nguoi__than"><b>${esc(d.ho_ten)}</b><small>${d.ma ? esc(d.ma) + " · " : ""}${esc(d.so_dien_thoai)}</small>${htmlBadgeNguoiTrongXe(d)}</span>
        ${d.loai === "co_dinh" ? `<button type="button" class="bcm-go" data-go="${esc(d.id)}" title="Gỡ khỏi biên chế cố định của xe">Gỡ</button>` : ""}
      </div>`;
  }

  function htmlChoTrong(chucDanh, nhan) {
    return `<button type="button" class="bcm-cho-trong" data-tab="${chucDanh}">+ Chỗ trống — chọn ${nhan} ở bên phải</button>`;
  }

  function htmlTrai() {
    const t = tinhTrangBienChe();
    const taiXe = theoChucDanh("tai_xe");
    const phuXe = theoChucDanh("phu_xe");
    const thieu = [t.thieuTx ? `${t.thieuTx} tài xế` : "", t.thieuPx ? `${t.thieuPx} phụ xe` : ""].filter(Boolean).join(" và ");
    return `
      <div class="bcm-xe">
        <span class="xe-bien-so">${esc(xe.bien_so)}</span>
        <span class="bcm-xe__phu">${esc(xe.ma_loai_xe)} · ${esc(xe.ten_loai_xe)}<br />${laXeDuPhong() ? "Xe dự phòng" : `Tuyến ${esc(xe.ma_tuyen)} · ${esc(xe.ten_tuyen)}`}</span>
      </div>
      <div class="bcm-tt ${t.du ? "bcm-tt--du" : "bcm-tt--thieu"}">
        <strong>${t.du ? "Đủ nhân sự" : `Chưa đủ nhân sự — thiếu ${thieu}`}</strong>
        <span>${t.du ? "Xe gán được chuyến." : "Xe chưa đủ người thì chưa gán được chuyến."}</span>
        ${!t.du && laXeDuPhong() ? "<small>Xe dự phòng không bị cảnh báo thiếu người trên trang Xe, nhưng vẫn phải đủ người mới gán được chuyến.</small>" : ""}
      </div>
      <section class="bcm-nhom">
        <div class="bcm-nhom__tieu"><span>Tài xế</span><b class="${t.thieuTx ? "bcm-so--thieu" : "bcm-so--du"}">${t.tx}/${SO_TAI_XE}</b></div>
        ${taiXe.map(htmlNguoiTrongXe).join("")}
        ${Array.from({ length: t.thieuTx }, () => htmlChoTrong("tai_xe", "tài xế")).join("")}
      </section>
      <section class="bcm-nhom">
        <div class="bcm-nhom__tieu"><span>Phụ xe</span><b class="${t.thieuPx ? "bcm-so--thieu" : "bcm-so--du"}">${t.px} (cần ≥ ${SO_PHU_XE_TOI_THIEU})</b></div>
        ${phuXe.map(htmlNguoiTrongXe).join("")}
        ${t.thieuPx ? htmlChoTrong("phu_xe", "phụ xe") : ""}
      </section>
      <p class="bcm-huong-dan">Mỗi xe cần đúng ${SO_TAI_XE} tài xế và ít nhất ${SO_PHU_XE_TOI_THIEU} phụ xe cố định. Bấm vào một người để xem hồ sơ.</p>`;
  }

  // ---------- Cột phải: chọn người để thêm ----------
  const ungVienChuaTrongXe = () => {
    const trongXe = new Set(dsBienChe.map((d) => d.nhan_su_van_hanh_id));
    return dsUngVien.filter((n) => !trongXe.has(n.id));
  };

  function locUngVien() {
    const k = boDau(tuKhoa.trim());
    return ungVienChuaTrongXe()
      .filter((n) => tab === "tat_ca" || n.chuc_danh === tab)
      .filter((n) => loc === "tat_ca" || (loc === "chua_co_xe" ? !n.xe_id_co_dinh : !!n.xe_id_co_dinh))
      .filter((n) => !k || boDau(`${n.ma || ""} ${n.ho_ten} ${n.so_dien_thoai} ${n.email || ""} ${n.bien_so_xe_co_dinh || ""}`).includes(k))
      .sort((a, b) => Number(!!a.xe_id_co_dinh) - Number(!!b.xe_id_co_dinh) || a.ho_ten.localeCompare(b.ho_ten, "vi"));
  }

  function htmlBadgeUngVien(n) {
    const b = [];
    b.push(n.xe_id_co_dinh ? `<span class="bcm-nhan bcm-nhan--xam">Đang ở xe ${esc(n.bien_so_xe_co_dinh)}</span>` : '<span class="bcm-nhan bcm-nhan--xanh">Chưa có xe</span>');
    if (n.chuc_danh === "phu_xe" && !n.co_tai_khoan) b.push('<span class="bcm-nhan bcm-nhan--do">Chưa có tài khoản</span>');
    if (n.giay_to_tinh_trang === "het_han") b.push('<span class="bcm-nhan bcm-nhan--do">Giấy tờ hết hạn</span>');
    else if (n.giay_to_tinh_trang === "sap_het_han") b.push('<span class="bcm-nhan bcm-nhan--vang">Giấy tờ sắp hết hạn</span>');
    return b.join("");
  }

  function htmlUngVien(n) {
    return `
      <div class="bcm-nguoi${chonId === n.id ? " is-chon" : ""}" data-xem="${esc(n.id)}" tabindex="0" role="button">
        <span class="bcm-avatar">${esc(chuCaiDau(n.ho_ten))}</span>
        <span class="bcm-nguoi__than"><b>${esc(n.ho_ten)}</b><small>${n.ma ? esc(n.ma) + " · " : ""}${esc(n.so_dien_thoai)}</small>${htmlBadgeUngVien(n)}</span>
      </div>`;
  }

  function htmlBoLoc() {
    const kha = ungVienChuaTrongXe();
    const demTab = { tai_xe: 0, phu_xe: 0, tat_ca: kha.length };
    kha.forEach((n) => demTab[n.chuc_danh]++);
    const trongTab = kha.filter((n) => tab === "tat_ca" || n.chuc_danh === tab);
    const demLoc = { chua_co_xe: trongTab.filter((n) => !n.xe_id_co_dinh).length, o_xe_khac: trongTab.filter((n) => n.xe_id_co_dinh).length, tat_ca: trongTab.length };
    const nutTab = (ma, nhan) => `<button type="button" class="bcm-tab${tab === ma ? " is-active" : ""}" data-tab="${ma}">${nhan} <b>${demTab[ma]}</b></button>`;
    const nutLoc = (ma, nhan) => `<button type="button" class="bcm-loc${loc === ma ? " is-active" : ""}" data-loc="${ma}">${nhan} <b>${demLoc[ma]}</b></button>`;
    return `
      <div class="bcm-cong-cu">
        <div class="bcm-tabs">${nutTab("tai_xe", "Tài xế")}${nutTab("phu_xe", "Phụ xe")}${nutTab("tat_ca", "Tất cả")}</div>
        <input type="search" class="bcm-tim" id="bcm-tim" placeholder="Tìm theo mã, tên, số điện thoại, email, biển số xe" value="${esc(tuKhoa)}" autocomplete="off" />
        <div class="bcm-locs"><span class="bcm-locs__nhan">Lọc:</span>${nutLoc("chua_co_xe", "Chưa có xe")}${nutLoc("o_xe_khac", "Đang ở xe khác")}${nutLoc("tat_ca", "Tất cả")}</div>
      </div>`;
  }

  // ---------- Chi tiết một người: TOÀN BỘ hồ sơ (chỉ xem) ----------
  function lyDoKhongThem(n) {
    if (n.xe_id_co_dinh) return `Đang thuộc biên chế cố định của xe ${n.bien_so_xe_co_dinh} — hãy gỡ khỏi xe đó trước`;
    if (n.chuc_danh === "phu_xe" && !n.co_tai_khoan) return "Phụ xe chưa có tài khoản đăng nhập — nhờ quản lý nhân sự tạo tài khoản trước";
    if (n.chuc_danh === "tai_xe" && theoChucDanh("tai_xe").filter((d) => d.loai === "co_dinh").length >= SO_TAI_XE) return `Xe đã đủ ${SO_TAI_XE} tài xế cố định`;
    return "";
  }

  function htmlGiayTo(g) {
    return `
      <li class="bcm-giay-to bcm-giay-to--${g.tinh_trang}">
        <div class="bcm-giay-to__dau"><strong>${NHAN_GIAY_TO[g.loai] || esc(g.loai)}${g.hang ? ` · hạng ${esc(g.hang)}` : ""}</strong><b>${NHAN_TINH_TRANG[g.tinh_trang] || ""}</b></div>
        <dl class="bcm-kv bcm-kv--nho">
          <dt>Số giấy tờ</dt><dd>${g.so_giay_to ? esc(g.so_giay_to) : "—"}</dd>
          <dt>Ngày cấp</dt><dd>${ngayVN(g.ngay_cap)}</dd>
          <dt>Ngày hết hạn</dt><dd>${ngayVN(g.ngay_het_han)}</dd>
        </dl>
        ${g.anh_url ? `<a class="bcm-xem-anh" href="${esc(g.anh_url)}" target="_blank" rel="noopener">Xem ảnh giấy tờ</a>` : '<span class="bcm-ct__ghi">Chưa có ảnh giấy tờ</span>'}
      </li>`;
  }

  function htmlChiTiet() {
    if (!chonId) return "";
    const ct = chiTietCache.get(chonId);
    if (ct === "dang_tai" || ct === undefined) return '<div class="bcm-ct bcm-ct--rong">Đang tải hồ sơ...</div>';
    if (ct.loi) return `<div class="bcm-ct bcm-ct--rong text-error">${esc(ct.loi)}</div>`;

    const dong = dsBienChe.find((d) => d.nhan_su_van_hanh_id === chonId);
    const uv = dsUngVien.find((n) => n.id === chonId);
    const hanhDong = (() => {
      if (dong) {
        return dong.loai === "co_dinh"
          ? `<span class="bcm-ct__ghi">Đang thuộc biên chế của xe này.</span><button type="button" class="nv-btn-secondary bcm-nut-go" data-go="${esc(dong.id)}">Gỡ khỏi biên chế</button>`
          : '<span class="bcm-ct__ghi">Đang thuộc biên chế tạm thời của xe này (do điều độ viên xử lý).</span>';
      }
      if (ct.trang_thai !== "dang_lam") return '<span class="bcm-ct__ghi bcm-ct__ghi--do">Nhân sự đã nghỉ việc — không đưa vào biên chế được.</span>';
      const ly = uv ? lyDoKhongThem(uv) : "";
      return ly
        ? `<span class="bcm-ct__ghi bcm-ct__ghi--do">${esc(ly)}</span><button type="button" class="btn-primary bcm-nut-them" disabled>Thêm vào xe ${esc(xe.bien_so)}</button>`
        : `<button type="button" class="btn-primary bcm-nut-them" data-them="${esc(chonId)}">Thêm vào xe ${esc(xe.bien_so)}</button>`;
    })();

    const bienCheHienTai = ct.bien_che.length
      ? ct.bien_che.map((b) => `${esc(b.bien_so)} (${b.loai === "co_dinh" ? "cố định" : "tạm thời"}${b.trang_thai === "tam_nghi" ? ", tạm nghỉ" : ""})`).join(", ")
      : "Chưa thuộc xe nào";
    const tuoiNguoi = tuoi(ct.ngay_sinh);

    return `
      <div class="bcm-ct">
        <div class="bcm-ct__dau">
          ${ct.anh_url ? `<img class="bcm-anh" src="${esc(ct.anh_url)}" alt="Ảnh ${esc(ct.ho_ten)}" />` : `<span class="bcm-avatar bcm-avatar--lon">${esc(chuCaiDau(ct.ho_ten))}</span>`}
          <div>
            <strong class="bcm-ct__ten">${esc(ct.ho_ten)}</strong>
            <div class="bcm-ct__phu">${ct.ma ? htmlMa(esc(ct.ma)) + " " : ""}<span class="bcm-nhan bcm-nhan--tim">${ct.chuc_danh === "tai_xe" ? "Tài xế" : "Phụ xe"}</span>
              ${ct.trang_thai === "dang_lam" ? '<span class="bcm-nhan bcm-nhan--xanh">Đang làm</span>' : '<span class="bcm-nhan bcm-nhan--do">Đã nghỉ việc</span>'}</div>
          </div>
        </div>

        <div class="bcm-ct__muc">Thông tin cá nhân</div>
        <dl class="bcm-kv">
          <dt>Họ và tên</dt><dd>${esc(ct.ho_ten)}</dd>
          <dt>Mã nhân viên</dt><dd>${ct.ma ? esc(ct.ma) : "—"}</dd>
          <dt>Số điện thoại</dt><dd>${esc(ct.so_dien_thoai)}</dd>
          <dt>Số CCCD</dt><dd>${ct.so_cccd ? esc(ct.so_cccd) : "—"}</dd>
          <dt>Ngày sinh</dt><dd>${ngayVN(ct.ngay_sinh)}${tuoiNguoi != null ? ` · ${tuoiNguoi} tuổi` : ""}</dd>
          <dt>Ngày vào làm</dt><dd>${ngayVN(ct.ngay_vao_lam)}${ct.ngay_vao_lam ? ` · làm được ${thamNien(ct.ngay_vao_lam)}` : ""}</dd>
          ${ct.trang_thai !== "dang_lam" ? `<dt>Ngày nghỉ việc</dt><dd>${ngayVN(ct.ngay_nghi_viec)}</dd><dt>Lý do nghỉ</dt><dd>${esc(ct.ly_do_nghi_viec || "—")}</dd>` : ""}
        </dl>

        ${ct.chuc_danh === "phu_xe" ? `
          <div class="bcm-ct__muc">Tài khoản đăng nhập</div>
          <dl class="bcm-kv">
            <dt>Email</dt><dd>${ct.co_tai_khoan ? esc(ct.email) : "Chưa có tài khoản"}</dd>
            ${ct.co_tai_khoan ? `<dt>Trạng thái</dt><dd>${ct.tai_khoan_hoat_dong ? "Đang hoạt động" : "Đã khóa"}</dd>` : ""}
          </dl>` : '<div class="bcm-ct__ghi bcm-ct__ghi--nho">Tài xế không có tài khoản đăng nhập hệ thống.</div>'}

        <div class="bcm-ct__muc">Giấy tờ</div>
        ${ct.giay_to.length ? `<ul class="bcm-giay-to-ds">${ct.giay_to.map(htmlGiayTo).join("")}</ul>` : '<div class="bcm-ct__ghi">Hồ sơ chưa có giấy tờ nào.</div>'}

        <div class="bcm-ct__muc">Biên chế xe</div>
        <dl class="bcm-kv"><dt>Hiện tại</dt><dd>${bienCheHienTai}</dd></dl>

        <p class="bcm-ct__ghi bcm-ct__ghi--nho">Hồ sơ chỉ để xem. Chỉnh sửa hồ sơ do quản lý nhân sự thực hiện.</p>
        <div class="bcm-ct__hanh-dong">${hanhDong}</div>
      </div>`;
  }

  // ---------- Vẽ lại ----------
  function veLai() {
    const goc = overlay.querySelector("#bcm-noi-dung");
    const cuonDs = goc.querySelector("#bcm-ds")?.scrollTop || 0;
    const cuonTrai = goc.querySelector(".bcm-trai")?.scrollTop || 0;
    const timFocus = document.activeElement?.id === "bcm-tim";
    const ds = locUngVien();
    goc.innerHTML = `
      <div class="bcm-luoi">
        <aside class="bcm-trai">${htmlTrai()}</aside>
        <section class="bcm-phai">
          <div class="bcm-phai__tieu">Thêm nhân sự vào biên chế</div>
          ${htmlBoLoc()}
          <div class="bcm-dem">${ds.length} người</div>
          <div class="bcm-ds" id="bcm-ds">${ds.length ? ds.map(htmlUngVien).join("") : '<div class="bcm-trong">Không có ai khớp bộ lọc hiện tại.</div>'}</div>
        </section>
      </div>`;
    overlay.querySelector("#bcm-chan-ghi").innerHTML = thongBao ? `<span class="bcm-tb ${thongBao.loi ? "bcm-tb--loi" : ""}">${esc(thongBao.noi_dung)}</span>` : "";
    goc.querySelector("#bcm-ds").scrollTop = cuonDs;
    goc.querySelector(".bcm-trai").scrollTop = cuonTrai;
    if (timFocus) { const o = goc.querySelector("#bcm-tim"); o.focus(); o.setSelectionRange(o.value.length, o.value.length); }

    goc.querySelectorAll("[data-xem]").forEach((el) => {
      const xem = () => chonNguoi(el.dataset.xem);
      el.addEventListener("click", xem);
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); xem(); } });
    });
    goc.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); goBienChe(b.dataset.go); }));
    goc.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { tab = b.dataset.tab; veLai(); }));
    goc.querySelectorAll("[data-loc]").forEach((b) => b.addEventListener("click", () => { loc = b.dataset.loc; veLai(); }));
    goc.querySelector("#bcm-tim").addEventListener("input", (e) => { tuKhoa = e.target.value; veLai(); });
  }

  async function chonNguoi(id) {
    chonId = id;
    thongBao = null;
    veLai();
    dungOverlayCt().hidden = false;
    veChiTiet();
    if (chiTietCache.has(id) && chiTietCache.get(id) !== "dang_tai") return;
    chiTietCache.set(id, "dang_tai");
    try {
      chiTietCache.set(id, await apiGet(`/quan-ly/nhan-su/${encodeURIComponent(id)}/chi-tiet-bien-che`));
    } catch (err) {
      chiTietCache.set(id, { loi: err.message });
    }
    if (!overlayCt.hidden && chonId === id) veChiTiet();
  }

  async function taiDuLieu() {
    [dsBienChe, dsUngVien] = await Promise.all([apiGet(`/quan-ly/xe/${xe.id}/bien-che`), apiGet("/quan-ly/nhan-su-dang-lam")]);
  }

  // Sau khi thêm/gỡ: nạp lại, chi tiết đã nạp bị bỏ (biên chế của người đó đã đổi), chuyển tab sang chức danh còn thiếu
  async function capNhatSauThayDoi(noiDung) {
    chiTietCache.clear();
    await taiDuLieu();
    const t = tinhTrangBienChe();
    if (t.thieuTx) tab = "tai_xe";
    else if (t.thieuPx) tab = "phu_xe";
    if (overlayCt) overlayCt.hidden = true; // xong việc: đóng hộp chi tiết, kết quả hiện ở hộp biên chế
    chonId = null;
    thongBao = { loi: false, noi_dung: noiDung };
    veLai();
  }

  // Lỗi (VD xe đã đủ tài xế) hiện ngay trong hộp chi tiết đang mở, còn không có hộp chi tiết thì ở hộp biên chế
  function baoLoi(err) {
    if (overlayCt && !overlayCt.hidden) {
      const goc = overlayCt.querySelector("#bcm-ct-noi-dung");
      goc.querySelector(".bcm-ct__loi")?.remove();
      goc.insertAdjacentHTML("beforeend", `<div class="bcm-tb bcm-tb--loi bcm-ct__loi">${esc(err.message)}</div>`);
      return;
    }
    thongBao = { loi: true, noi_dung: err.message };
    veLai();
  }

  async function themBienChe(nhanSuId) {
    const ten = (dsUngVien.find((n) => n.id === nhanSuId) || {}).ho_ten || "nhân sự";
    try {
      await apiPost(`/quan-ly/xe/${xe.id}/bien-che`, { nhan_su_van_hanh_id: nhanSuId });
      await capNhatSauThayDoi(`Đã thêm ${ten} vào biên chế xe ${xe.bien_so}.`);
    } catch (err) {
      baoLoi(err);
    }
  }

  async function goBienChe(xeNhanSuId) {
    const d = dsBienChe.find((x) => x.id === xeNhanSuId);
    if (d && !confirm(`Gỡ ${d.ho_ten} khỏi biên chế cố định của xe ${xe.bien_so}?`)) return;
    try {
      await apiDelete(`/quan-ly/bien-che/${xeNhanSuId}`);
      await capNhatSauThayDoi(`Đã gỡ ${d ? d.ho_ten : "nhân sự"} khỏi biên chế xe ${xe.bien_so}.`);
    } catch (err) {
      baoLoi(err);
    }
  }

  async function mo(xeChon, tuyChon = {}) {
    xe = xeChon;
    khiDong = tuyChon.khiDong || (() => {});
    dsBienChe = []; dsUngVien = []; chonId = null; loc = "chua_co_xe"; tuKhoa = ""; thongBao = null;
    chiTietCache.clear();
    if (overlayCt) overlayCt.hidden = true;
    const ov = dungOverlay();
    ov.querySelector("#bcm-tieu-de").textContent = `Biên chế xe ${xe.bien_so}`;
    ov.querySelector("#bcm-chan-ghi").innerHTML = "";
    const goc = ov.querySelector("#bcm-noi-dung");
    goc.innerHTML = '<div class="bcm-trong">Đang tải biên chế và danh sách nhân sự...</div>';
    ov.hidden = false;
    try {
      await taiDuLieu();
    } catch (err) {
      goc.innerHTML = `<div class="text-error">${esc(err.message)}</div>`;
      return;
    }
    const t = tinhTrangBienChe();
    tab = t.thieuTx ? "tai_xe" : t.thieuPx ? "phu_xe" : "tat_ca";
    veLai();
  }

  return { mo };
})();
