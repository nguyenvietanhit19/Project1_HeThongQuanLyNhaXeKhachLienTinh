/*
 * Menu điều hướng khu vực "Quản lý" — CONTRIBUTING.md mục 5.5: mảng link
 * dùng chung, mỗi người tự thêm entry vào cuối mảng khi UC của mình xong
 * (VD UC-32 loại xe, UC-33 giá vé...), không sửa dòng người khác.
 *
 * Các vai trò khác (điều độ viên, quầy vé...) sẽ có file nav-<vai-tro>.js
 * riêng khi tới lượt — không dùng chung 1 mảng vì mỗi khu vực nhân viên
 * thấy menu hoàn toàn khác nhau (mục 4 CONTRIBUTING.md).
 */

const MENU_QUAN_LY = [
  { label: "Khu vực", href: "/nhan-vien/quan-ly/khu-vuc.html" },
  { label: "Điểm đón/trả", href: "/nhan-vien/quan-ly/diem-don-tra.html" },
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
