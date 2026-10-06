/*
 * Menu sidebar cho Điều độ viên — riêng domain dieu-do.
 * Thêm UC mới: chỉ cần thêm object vào MENU_DIEU_DO.
 */

const MENU_DIEU_DO = [
  {
    label: "Gán xe cho chuyến",
    href: "/nhan-vien/dieu-do/danh-sach-chuyen.html",
    icon: '<rect x="3" y="7" width="18" height="9" rx="3"/><path d="M7 16v2M17 16v2"/><path d="M3 12h18"/>',
  },
  {
    label: "Xử lý sự cố",
    href: "/nhan-vien/dieu-do/xu-ly-su-co.html",
    icon: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>',
  },
  {
    label: "Gán lại xe gốc",
    href: "/nhan-vien/dieu-do/gan-lai-xe-goc.html",
    icon: '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.27"/>',
  },
  {
    label: "Thống kê",
    href: "/nhan-vien/dieu-do/thong-ke.html",
    icon: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  },
];

function renderTopbarUser() {
  const hoTen = localStorage.getItem("ho_ten") || "";
  const el = document.getElementById("topbar-ho-ten");
  if (el) el.textContent = hoTen;
  const elRole = document.getElementById("topbar-vai-tro");
  if (elRole) elRole.textContent = "Điều độ viên";
  const elAvatar = document.getElementById("topbar-avatar");
  if (elAvatar) elAvatar.textContent = hoTen.trim().charAt(0).toUpperCase() || "Đ";
}

function renderSidebar(containerEl, hrefDangMo) {
  const links = MENU_DIEU_DO.map(
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
    <div class="nv-sidebar__section-title">Điều độ vận hành</div>
    <nav class="nv-sidebar__nav">${links}</nav>
    <div class="nv-sidebar__deco" aria-hidden="true"></div>
  `;
}
