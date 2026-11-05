/*
 * Menu sidebar của khu Điều độ viên — dùng chung cho các trang (Tổng quan, Gán xe). Nạp SAU nav.js, TRƯỚC script của trang.
 * Quản lý vào các trang này được thêm mục "Về trang quản lý" ở từng trang.
 */
const MENU_DIEU_DO = [
  {
    label: "Tổng quan",
    href: "/nhan-vien/dieu-do/thong-ke.html",
    icon: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  },
  {
    label: "Gán xe",
    href: "/nhan-vien/dieu-do/gan-xe.html",
    icon: '<rect x="3" y="5" width="18" height="11" rx="2.5"/><path d="M3 11h18M7 16v3M17 16v3"/><circle cx="7.5" cy="13.5" r="0.8"/><circle cx="16.5" cy="13.5" r="0.8"/>',
  },
];

const MUC_VE_TRANG_QUAN_LY = { label: "Về trang quản lý", href: "/nhan-vien/quan-ly/chuyen.html", icon: '<path d="M15 6l-6 6 6 6"/>' };

// Menu theo vai trò: quản lý có thêm đường quay về khu quản lý
const menuDieuDoCho = (vaiTro) => (vaiTro === "quan_ly" ? [...MENU_DIEU_DO, MUC_VE_TRANG_QUAN_LY] : MENU_DIEU_DO);
