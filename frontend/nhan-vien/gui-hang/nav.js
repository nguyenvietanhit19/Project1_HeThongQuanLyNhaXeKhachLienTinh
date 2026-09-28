/*
 * nav.js — Thanh điều hướng header và quản lý chuyển Tab nghiệp vụ
 */

function khoiTaoNav(tabHienTai = "tao-don") {
  const navContainer = document.getElementById("main-nav");
  if (!navContainer) return;

  const hoTen = localStorage.getItem("ho_ten") || "Nhân viên gửi hàng";
  const vaiTro = localStorage.getItem("vai_tro") === "quan_ly" ? "Quản lý" : "NV Gửi hàng";

  navContainer.innerHTML = `
    <header class="app-header">
      <div class="header-left">
        <div class="brand-badge">
          <img src="../../shared/assets/logo-mark.png" alt="Logo Nhà Xe" class="brand-logo-img" onerror="this.src='/shared/assets/logo-mark.png'" />
          <div class="brand-title-wrap">
            <span class="brand-title">NHÀ XE LIÊN TỈNH</span>
            <span class="sub-role-badge">${vaiTro}</span>
          </div>
        </div>
      </div>

      <nav class="header-tabs">
        <button class="nav-tab ${tabHienTai === "tao-don" ? "active" : ""}" onclick="chuyenTab('tao-don')">
          <span class="tab-icon">📦</span> Tiếp nhận gửi hàng
        </button>
        <button class="nav-tab ${tabHienTai === "giao-hang" ? "active" : ""}" onclick="chuyenTab('giao-hang')">
          <span class="tab-icon">🚚</span> Giao hàng & COD
        </button>
        <button class="nav-tab ${tabHienTai === "hang-ton" ? "active" : ""}" onclick="chuyenTab('hang-ton')">
          <span class="tab-icon">⚠️</span> Hàng chờ lâu
        </button>
        <button class="nav-tab ${tabHienTai === "thong-ke" ? "active" : ""}" onclick="chuyenTab('thong-ke')">
          <span class="tab-icon">📊</span> Thống kê báo cáo
        </button>
      </nav>

      <div class="header-right">
        <div class="user-profile">
          <span class="user-avatar">👤</span>
          <div class="user-details">
            <span class="user-name">${hoTen}</span>
            <span class="user-role">Quầy gửi hàng</span>
          </div>
        </div>
        <button class="btn-logout" onclick="dangXuatNhanVien()" title="Đăng xuất">
          <span>Đăng xuất</span> 🚪
        </button>
      </div>
    </header>
  `;
}
