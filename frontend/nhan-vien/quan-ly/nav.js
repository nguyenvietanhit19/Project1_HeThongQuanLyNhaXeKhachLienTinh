/*
 * Menu điều hướng cho các trang Quản lý — mảng link, tự thêm entry vào
 * cuối mảng khi có UC mới (VD UC-32 loại xe, UC-33 giá vé...).
 *
 * Sidebar thu gọn/mở rộng được (nhớ lựa chọn trong localStorage); khối tài khoản (họ tên, vai trò, menu
 * "Tài khoản của tôi" / "Đăng xuất") nằm ở cuối sidebar. Modal tài khoản ở tai-khoan.js (nạp sau file này).
 *
 * Riêng của domain Quản lý — mỗi vai trò nhân viên khác (điều độ viên,
 * quầy vé...) khi tới lượt sẽ tự viết menu + CSS/JS riêng trong đúng thư
 * mục của họ (VD frontend/nhan-vien/dieu-do/), không dùng chung file này.
 */

const MENU_QUAN_LY = [
  {
    label: "Khu vực",
    href: "/nhan-vien/quan-ly/khu-vuc.html",
    icon: '<path d="M9 3 3 5v16l6-2 6 2 6-2V3l-6 2-6-2Z"/><path d="M9 3v16M15 5v16"/>',
  },
  {
    label: "Điểm đón/trả",
    href: "/nhan-vien/quan-ly/diem-don-tra.html",
    icon: '<path d="M12 21s7-7.16 7-12a7 7 0 1 0-14 0c0 4.84 7 12 7 12Z"/><circle cx="12" cy="9" r="2.3"/>',
  },
  {
    label: "Tuyến",
    href: "/nhan-vien/quan-ly/tuyen.html",
    icon: '<circle cx="6" cy="19" r="2.3"/><circle cx="18" cy="5" r="2.3"/><path d="M6 16.7V13a4 4 0 0 1 4-4h2a4 4 0 0 0 4-4V5.3" stroke-dasharray="2.6 2.6"/>',
  },
  {
    label: "Loại xe",
    href: "/nhan-vien/quan-ly/loai-xe.html",
    icon: '<rect x="3" y="7" width="18" height="9" rx="3"/><path d="M7 16v2M17 16v2"/><path d="M3 12h18"/>',
  },
  {
    label: "Xe",
    href: "/nhan-vien/quan-ly/xe.html",
    icon: '<rect x="3" y="5" width="18" height="11" rx="2.5"/><path d="M3 11h18M7 16v3M17 16v3"/><circle cx="7.5" cy="13.5" r="0.8"/><circle cx="16.5" cy="13.5" r="0.8"/>',
  },
  {
    label: "Giá vé",
    href: "/nhan-vien/quan-ly/gia-ve.html",
    icon: '<circle cx="12" cy="12" r="9"/><path d="M9 15V9l1.8 1.8L12 9l1.2 1.8L15 9v6"/>',
  },
  {
    label: "Lịch chạy",
    href: "/nhan-vien/quan-ly/lich-chay.html",
    icon: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
  },
  {
    label: "Chuyến",
    href: "/nhan-vien/quan-ly/chuyen.html",
    icon: '<path d="M3 12h18M3 12l4-5M3 12l4 5M21 12l-4-5M21 12l-4 5"/>',
  },
];

const NHAN_VAI_TRO_QUAN_LY = {
  quan_ly: "Quản lý",
  quan_ly_nhan_su: "Quản lý nhân sự",
};

/*
 * Nhớ trạng thái của từng trang (tuyến đang chọn, ô tìm kiếm, bộ lọc...) khi chuyển qua trang khác rồi quay lại.
 * Lưu trong sessionStorage theo đường dẫn trang: sống trong 1 tab, mất khi đóng tab (không để lại dữ liệu cũ lâu ngày),
 * và bị xóa khi đăng xuất. Trình duyệt chặn lưu trữ thì bỏ qua êm, trang vẫn chạy bình thường.
 * Dùng: const tt = TrangThaiTrang.doc();  ...  TrangThaiTrang.luu({ tuKhoa });
 */
const TrangThaiTrang = {
  _khoa: () => "nv_tt:" + location.pathname,
  doc() {
    try {
      return JSON.parse(sessionStorage.getItem(this._khoa()) || "{}") || {};
    } catch (e) {
      return {};
    }
  },
  luu(phanThayDoi) {
    try {
      sessionStorage.setItem(this._khoa(), JSON.stringify({ ...this.doc(), ...phanThayDoi }));
    } catch (e) {
      /* bỏ qua */
    }
  },
  // Chọn lại giá trị đã lưu cho <select> có option nạp bất đồng bộ — chỉ chọn nếu option còn tồn tại
  chonLaiSelect(selectEl, giaTri) {
    if (giaTri && [...selectEl.options].some((o) => o.value === giaTri)) selectEl.value = giaTri;
  },
};

const KHOA_THU_GON_SIDEBAR = "nv_sidebar_thu_gon";

const ICON_SIDEBAR = '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>';
const ICON_NGUOI = '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c0-4 3.4-6.5 7.5-6.5s7.5 2.5 7.5 6.5"/>';
const ICON_DANG_XUAT = '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>';

function docTrangThaiThuGon() {
  try {
    return localStorage.getItem(KHOA_THU_GON_SIDEBAR) === "1";
  } catch (e) {
    return false;
  }
}

function luuTrangThaiThuGon(thuGon) {
  try {
    localStorage.setItem(KHOA_THU_GON_SIDEBAR, thuGon ? "1" : "0");
  } catch (e) {
    /* trình duyệt chặn lưu trữ — vẫn thu gọn được trong phiên này */
  }
}

function svgIcon(noiDung, lop = "") {
  return `<svg class="${lop}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${noiDung}</svg>`;
}

function renderSidebar(containerEl, hrefDangMo) {
  const links = MENU_QUAN_LY.map(
    (muc) => `
      <a class="nv-sidebar__link${muc.href === hrefDangMo ? " active" : ""}" href="${muc.href}">
        <svg class="nv-sidebar__link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${muc.icon}</svg>
        <span>${muc.label}</span>
      </a>
    `
  ).join("");

  containerEl.innerHTML = `
    <div class="nv-sidebar__brand">
      <button type="button" class="nv-sidebar__brand-mark" id="nv-sidebar-mo-rong" aria-label="Mở rộng thanh bên" title="Mở rộng thanh bên">
        <img src="/shared/assets/logo-mark.png" alt="Logo" />
        ${svgIcon(ICON_SIDEBAR, "nv-sidebar__expand-icon")}
      </button>
      <span class="nv-sidebar__brand-text">
        <strong>GoBus</strong>
        <em>Kết nối mọi hành trình</em>
      </span>
      <button type="button" class="nv-sidebar__collapse" id="nv-sidebar-thu-gon" aria-label="Thu gọn thanh bên" title="Thu gọn thanh bên">${svgIcon(ICON_SIDEBAR)}</button>
    </div>
    <div class="nv-sidebar__section-title">Danh mục quản lý</div>
    <nav class="nv-sidebar__nav">${links}</nav>

    <div class="nv-sidebar__tai-khoan">
      <div class="nv-tk-menu" id="nv-tk-menu" role="menu" hidden>
        <button type="button" class="nv-tk-menu__muc" role="menuitem" id="nv-tk-mo-ho-so">${svgIcon(ICON_NGUOI)}Tài khoản của tôi</button>
        <button type="button" class="nv-tk-menu__muc nv-tk-menu__muc--nguy" role="menuitem" id="nv-tk-dang-xuat">${svgIcon(ICON_DANG_XUAT)}Đăng xuất</button>
      </div>
      <button type="button" class="nv-tk-nut" id="nv-tk-nut" aria-haspopup="true" aria-expanded="false">
        <span class="nv-tk-nut__avatar" id="topbar-avatar"></span>
        <span class="nv-tk-nut__ten">
          <strong id="topbar-ho-ten"></strong>
          <em id="topbar-vai-tro"></em>
        </span>
        <svg class="nv-tk-nut__mui" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 14l5-5 5 5"/></svg>
      </button>
    </div>
  `;

  const datThuGon = (thuGon) => {
    containerEl.classList.toggle("is-thu-gon", thuGon);
    luuTrangThaiThuGon(thuGon);
    dongMenuTaiKhoan();
  };
  containerEl.classList.toggle("is-thu-gon", docTrangThaiThuGon());
  document.getElementById("nv-sidebar-thu-gon").addEventListener("click", () => datThuGon(true));
  document.getElementById("nv-sidebar-mo-rong").addEventListener("click", () => datThuGon(false));

  ganMenuTaiKhoan();
  renderThongTinTaiKhoan();
}

/*
 * Đổ họ tên/vai trò/avatar (chữ cái đầu tên) vào khối tài khoản ở cuối sidebar — ID cố định
 * #topbar-ho-ten, #topbar-vai-tro, #topbar-avatar. Gọi lại sau khi đổi họ tên.
 */
function renderThongTinTaiKhoan() {
  const hoTen = localStorage.getItem("ho_ten") || "";
  const vaiTro = localStorage.getItem("vai_tro") || "";
  const elHoTen = document.getElementById("topbar-ho-ten");
  if (elHoTen) elHoTen.textContent = hoTen;
  const elVaiTro = document.getElementById("topbar-vai-tro");
  if (elVaiTro) elVaiTro.textContent = NHAN_VAI_TRO_QUAN_LY[vaiTro] || vaiTro;
  const elAvatar = document.getElementById("topbar-avatar");
  if (elAvatar) elAvatar.textContent = hoTen.trim().split(/\s+/).slice(-1)[0]?.charAt(0).toUpperCase() || "?";
}

// ---------- Menu tài khoản (mở lên phía trên nút ở cuối sidebar) ----------
function dongMenuTaiKhoan() {
  const menu = document.getElementById("nv-tk-menu");
  const nut = document.getElementById("nv-tk-nut");
  if (menu) menu.hidden = true;
  if (nut) nut.setAttribute("aria-expanded", "false");
}

function ganMenuTaiKhoan() {
  const menu = document.getElementById("nv-tk-menu");
  const nut = document.getElementById("nv-tk-nut");
  nut.addEventListener("click", (e) => {
    e.stopPropagation();
    const mo = menu.hidden;
    menu.hidden = !mo;
    nut.setAttribute("aria-expanded", String(mo));
  });
  document.addEventListener("click", (e) => {
    if (!menu.hidden && !menu.contains(e.target)) dongMenuTaiKhoan();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dongMenuTaiKhoan();
  });
  document.getElementById("nv-tk-mo-ho-so").addEventListener("click", () => {
    dongMenuTaiKhoan();
    TaiKhoanQuanLy.mo();
  });
  document.getElementById("nv-tk-dang-xuat").addEventListener("click", dangXuat);
}
