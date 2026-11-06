/*
 * Menu điều hướng cho các trang Quản lý nhân sự — mảng link, tự thêm entry
 * vào cuối mảng khi có UC mới.
 *
 * Hiện có UC-49 (hồ sơ nhân sự vận hành) + UC-51 (cho nghỉ việc, nút ở từng hàng
 * trong ho-so.html), UC-36 (tạo tài khoản cán bộ) + UC-37 (khóa/mở khóa) cùng trang
 * tai-khoan.html, và UC-52 (xem nhật ký thao tác, nhat-ky.html).
 *
 * Khung sidebar (thu gọn/mở rộng, khối tài khoản + "Tài khoản của tôi" + "Đăng xuất" ở cuối sidebar)
 * dùng chung với Quản lý: nạp frontend/nhan-vien/quan-ly/nav.js và tai-khoan.js TRƯỚC file này, rồi gọi
 *   renderSidebar(el, href, MENU_QUAN_LY_NHAN_SU, "Quản lý nhân sự");
 * File này chỉ chứa phần riêng của domain: danh sách mục menu.
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
  {
    label: "Nhật ký thao tác",
    href: "/nhan-vien/quan-li-nhan-su/nhat-ky.html",
    icon: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  },
];
