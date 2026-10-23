/*
 * Menu điều hướng cho các trang Quản lý nhân sự — mảng link, tự thêm entry
 * vào cuối mảng khi có UC mới.
 *
 * Hiện có UC-49 (hồ sơ nhân sự vận hành) và UC-36 (tạo tài khoản cán bộ,
 * tai-khoan.html). Còn thiếu backend nên CHƯA thêm vào menu: UC-37
 * (khóa/mở khóa tài khoản), UC-51 (cho nghỉ việc, hiện lồng trong modal sửa
 * hồ sơ ở ho-so.html chứ chưa tách trang riêng), UC-52 (xem nhật ký thao tác).
 *
 * Riêng của domain Quản lý nhân sự — không dùng chung với
 * frontend/nhan-vien/quan-ly/nav.js (dù cùng kiểu actor "quản lý", 2 domain
 * có tập UC khác nhau nên menu khác nhau).
 */

const MENU_QUAN_LY_NHAN_SU = [
  {
    label: "Tổng quan",
    href: "/nhan-vien/quan-li-nhan-su/trang-chu.html",
    icon: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  },
  {
    label: "Hồ sơ nhân sự",
    href: "/nhan-vien/quan-li-nhan-su/ho-so.html",
    icon: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5a3 3 0 0 1 0 6M18 14c1.8.6 3 2.3 3 4"/>',
  },
  {
    label: "Tài khoản cán bộ",
    href: "/nhan-vien/quan-li-nhan-su/tai-khoan.html",
    icon: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M19 8v6M16 11h6"/>',
  },
];

const NHAN_VAI_TRO_QUAN_LY_NHAN_SU = {
  quan_ly: "Quản lý",
  quan_ly_nhan_su: "Quản lý nhân sự",
};

/*
 * Đổ họ tên/vai trò/avatar (chữ cái đầu tên) vào topbar — dùng chung ID
 * cố định trên mọi trang: #topbar-ho-ten, #topbar-vai-tro, #topbar-avatar.
 * Gọi sau khi yeuCauVaiTro() đã xác nhận đăng nhập.
 */
function renderTopbarUser() {
  const hoTen = localStorage.getItem("ho_ten") || "";
  const vaiTro = localStorage.getItem("vai_tro") || "";

  const elHoTen = document.getElementById("topbar-ho-ten");
  if (elHoTen) elHoTen.textContent = hoTen;

  const elVaiTro = document.getElementById("topbar-vai-tro");
  if (elVaiTro) elVaiTro.textContent = NHAN_VAI_TRO_QUAN_LY_NHAN_SU[vaiTro] || vaiTro;

  const elAvatar = document.getElementById("topbar-avatar");
  if (elAvatar) elAvatar.textContent = hoTen.trim().charAt(0).toUpperCase() || "?";
}

function renderSidebar(containerEl, hrefDangMo) {
  const links = MENU_QUAN_LY_NHAN_SU.map(
    (muc) => `
      <a class="nv-sidebar__link${muc.href === hrefDangMo ? " active" : ""}" href="${muc.href}">
        <svg class="nv-sidebar__link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${muc.icon}</svg>
        <span>${muc.label}</span>
      </a>
    `
  ).join("");

  containerEl.innerHTML = `
    <div class="nv-sidebar__brand">
      <span class="nv-sidebar__brand-mark">
        <img src="/shared/assets/logo-mark.png" alt="Logo" />
      </span>
      <span class="nv-sidebar__brand-text">
        <strong>GoBus</strong>
        <em>Kết nối mọi hành trình</em>
      </span>
    </div>
    <div class="nv-sidebar__section-title">Quản lý nhân sự</div>
    <nav class="nv-sidebar__nav">${links}</nav>
    <div class="nv-sidebar__deco" aria-hidden="true"></div>
  `;
}
