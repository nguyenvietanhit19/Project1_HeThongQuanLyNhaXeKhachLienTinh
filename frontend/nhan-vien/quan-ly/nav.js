/*
 * Menu điều hướng cho các trang Quản lý — mảng link, tự thêm entry vào
 * cuối mảng khi có UC mới (VD UC-32 loại xe, UC-33 giá vé...).
 *
 * Riêng của domain Quản lý — mỗi vai trò nhân viên khác (điều độ viên,
 * quầy vé...) khi tới lượt sẽ tự viết menu + CSS/JS riêng trong đúng thư
 * mục của họ (VD frontend/nhan-vien/dieu-do/), không dùng chung file này.
 */

const MENU_QUAN_LY = [
  { label: "Khu vực", href: "/nhan-vien/quan-ly/khu-vuc.html" },
  { label: "Điểm đón/trả", href: "/nhan-vien/quan-ly/diem-don-tra.html" },
  { label: "Nhóm tuyến", href: "/nhan-vien/quan-ly/nhom-tuyen.html" },
  { label: "Tuyến", href: "/nhan-vien/quan-ly/tuyen.html" },
];

function renderSidebar(containerEl, hrefDangMo) {
  const links = MENU_QUAN_LY.map(
    (muc) => `<a class="nv-sidebar__link${muc.href === hrefDangMo ? " active" : ""}" href="${muc.href}">${muc.label}</a>`
  ).join("");

  containerEl.innerHTML = `
    <div class="nv-sidebar__brand">Nhà xe khách</div>
    <div class="nv-sidebar__section-title">Danh mục quản lý</div>
    <nav class="nv-sidebar__nav">${links}</nav>
  `;
}
