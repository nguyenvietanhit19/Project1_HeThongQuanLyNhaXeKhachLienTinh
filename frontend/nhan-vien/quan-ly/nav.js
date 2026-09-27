/*
 * Menu điều hướng cho các trang Quản lý — mảng link, tự thêm entry vào
 * cuối mảng khi có UC mới (VD UC-32 loại xe, UC-33 giá vé...).
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
    label: "Nhóm tuyến",
    href: "/nhan-vien/quan-ly/nhom-tuyen.html",
    icon: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
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
    label: "Giá vé",
    href: "/nhan-vien/quan-ly/gia-ve.html",
    icon: '<circle cx="12" cy="12" r="9"/><path d="M9 15V9l1.8 1.8L12 9l1.2 1.8L15 9v6"/>',
  },
];

const NHAN_VAI_TRO_QUAN_LY = {
  quan_ly: "Quản lý",
  quan_ly_nhan_su: "Quản lý nhân sự",
};

/*
 * Đổ họ tên/vai trò/avatar (chữ cái đầu tên) vào topbar — dùng chung ID
 * cố định trên mọi trang Quản lý: #topbar-ho-ten, #topbar-vai-tro,
 * #topbar-avatar. Gọi sau khi yeuCauVaiTro() đã xác nhận đăng nhập.
 */
function renderTopbarUser() {
  const hoTen = localStorage.getItem("ho_ten") || "";
  const vaiTro = localStorage.getItem("vai_tro") || "";

  const elHoTen = document.getElementById("topbar-ho-ten");
  if (elHoTen) elHoTen.textContent = hoTen;

  const elVaiTro = document.getElementById("topbar-vai-tro");
  if (elVaiTro) elVaiTro.textContent = NHAN_VAI_TRO_QUAN_LY[vaiTro] || vaiTro;

  const elAvatar = document.getElementById("topbar-avatar");
  if (elAvatar) elAvatar.textContent = hoTen.trim().charAt(0).toUpperCase() || "?";
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
      <span class="nv-sidebar__brand-mark">
        <img src="/shared/assets/logo-mark.png" alt="Logo" />
      </span>
      <span class="nv-sidebar__brand-text">
        <strong>GoBus</strong>
        <em>Kết nối mọi hành trình</em>
      </span>
    </div>
    <div class="nv-sidebar__section-title">Danh mục quản lý</div>
    <nav class="nv-sidebar__nav">${links}</nav>
    <div class="nv-sidebar__deco" aria-hidden="true"></div>
  `;
}
