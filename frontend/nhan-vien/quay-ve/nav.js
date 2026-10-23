const QV_MENU = [
  { label: "Tổng quan", href: "/nhan-vien/quay-ve/index.html", icon: '<path d="M3 10.5 12 3l9 7.5V21H3z"/><path d="M9 21v-7h6v7"/>' },
  { label: "Bán vé", href: "/nhan-vien/quay-ve/ban-ve.html", icon: '<path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h5"/>' },
  { label: "Tra cứu / in vé", href: "/nhan-vien/quay-ve/tra-cuu-ve.html", icon: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>' },
  { label: "Thống kê", href: "/nhan-vien/quay-ve/thong-ke.html", icon: '<path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 6-7"/>' },
];

const QV_SIDEBAR_KEY = "qv_sidebar_thu_gon";

function qvIcon(content, className = "") {
  return `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${content}</svg>`;
}

function renderQuayVeNav(active) {
  const sidebar = document.querySelector("#qv-nav");
  const name = localStorage.getItem("ho_ten") || "Nhân viên quầy vé";
  const initial = name.trim().split(/\s+/).slice(-1)[0]?.charAt(0).toUpperCase() || "?";
  sidebar.innerHTML = `
    <div class="nv-sidebar__brand">
      <button type="button" class="nv-sidebar__brand-mark" id="qv-sidebar-expand" aria-label="Mở rộng thanh bên" title="Mở rộng thanh bên">
        <img src="/shared/assets/logo-mark.png" alt="Logo GoBus" />
        ${qvIcon('<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>', "nv-sidebar__expand-icon")}
      </button>
      <span class="nv-sidebar__brand-text"><strong>GoBus</strong><em>Kết nối mọi hành trình</em></span>
      <button type="button" class="nv-sidebar__collapse" id="qv-sidebar-collapse" aria-label="Thu gọn thanh bên" title="Thu gọn thanh bên">
        ${qvIcon('<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>')}
      </button>
    </div>
    <div class="nv-sidebar__section-title">Danh mục quầy vé</div>
    <nav class="nv-sidebar__nav" aria-label="Chức năng quầy vé">
      ${QV_MENU.map(({ label, href, icon }) => `
        <a class="nv-sidebar__link${active === href ? " active" : ""}" href="${href}"${active === href ? ' aria-current="page"' : ""}>
          ${qvIcon(icon, "nv-sidebar__link-icon")}<span>${label}</span>
        </a>`).join("")}
    </nav>
    <div class="nv-sidebar__tai-khoan">
      <div class="nv-tk-menu" id="qv-account-menu" role="menu" hidden>
        <button type="button" class="nv-tk-menu__muc" id="qv-view-account" role="menuitem">
          ${qvIcon('<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>')}
          Xem chi tiết tài khoản
        </button>
        <button type="button" class="nv-tk-menu__muc nv-tk-menu__muc--nguy" id="qv-logout" role="menuitem">
          ${qvIcon('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>')}
          Đăng xuất
        </button>
      </div>
      <button type="button" class="nv-tk-nut" id="qv-account-button" aria-haspopup="menu" aria-controls="qv-account-menu" aria-expanded="false">
        <span class="nv-tk-nut__avatar">${escapeHtml(initial)}</span>
        <span class="nv-tk-nut__ten"><strong>${escapeHtml(name)}</strong><em>Nhân viên quầy vé</em></span>
        ${qvIcon('<path d="M7 14l5-5 5 5"/>', "nv-tk-nut__mui")}
      </button>
    </div>`;

  const setCollapsed = (collapsed) => {
    sidebar.classList.toggle("is-thu-gon", collapsed);
    try {
      localStorage.setItem(QV_SIDEBAR_KEY, collapsed ? "1" : "0");
    } catch (_) {
      // Trình duyệt chặn lưu trữ: trạng thái vẫn áp dụng trong phiên này.
    }
  };
  try {
    sidebar.classList.toggle("is-thu-gon", localStorage.getItem(QV_SIDEBAR_KEY) === "1");
  } catch (_) {
    sidebar.classList.remove("is-thu-gon");
  }
  document.querySelector("#qv-sidebar-collapse").addEventListener("click", () => setCollapsed(true));
  document.querySelector("#qv-sidebar-expand").addEventListener("click", () => setCollapsed(false));

  const menu = document.querySelector("#qv-account-menu");
  const accountButton = document.querySelector("#qv-account-button");
  const closeMenu = () => {
    menu.hidden = true;
    accountButton.setAttribute("aria-expanded", "false");
  };
  accountButton.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
    accountButton.setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("click", (event) => {
    if (!menu.hidden && !menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  document.querySelector("#qv-view-account").addEventListener("click", () => {
    closeMenu();
    qvShowAccountDetails(accountButton);
  });
  document.querySelector("#qv-logout").addEventListener("click", quayVeDangXuat);
}

let qvAccountDialog = null;
let qvAccountRequestId = 0;

function qvShowAccountDetails(returnFocusTo) {
  if (!qvAccountDialog) {
    qvAccountDialog = document.createElement("div");
    qvAccountDialog.className = "nv-modal-overlay";
    qvAccountDialog.hidden = true;
    qvAccountDialog.innerHTML = `
      <section class="nv-modal qv-profile-modal" role="dialog" aria-modal="true" aria-labelledby="qv-profile-title">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">${qvIcon('<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>')}</div>
          <h2 id="qv-profile-title">Thông tin tài khoản</h2>
        </div>
        <div class="nv-modal__body">
          <div id="qv-profile-content" aria-live="polite"></div>
          <div class="nv-modal__actions"><button type="button" class="nv-btn-secondary" id="qv-profile-close">Đóng</button></div>
        </div>
      </section>`;
    document.body.appendChild(qvAccountDialog);
    qvAccountDialog.addEventListener("click", (event) => {
      if (event.target === qvAccountDialog) qvCloseAccountDetails();
    });
    qvAccountDialog.querySelector("#qv-profile-close").addEventListener("click", qvCloseAccountDetails);
    document.addEventListener("keydown", (event) => {
      if (qvAccountDialog.hidden) return;
      if (event.key === "Escape") qvCloseAccountDetails();
      if (event.key === "Tab") {
        event.preventDefault();
        qvAccountDialog.querySelector("#qv-profile-close").focus();
      }
    });
  }

  qvAccountDialog.returnFocusTo = returnFocusTo;
  qvAccountDialog.hidden = false;
  const requestId = ++qvAccountRequestId;
  const content = qvAccountDialog.querySelector("#qv-profile-content");
  content.innerHTML = '<p class="qv-muted" role="status">Đang tải thông tin tài khoản…</p>';
  qvAccountDialog.querySelector("#qv-profile-close").focus();

  Promise.all([apiGet("/auth/toi"), apiGet("/quay-ve/van-phong-cua-toi")])
    .then(([account, office]) => {
      if (qvAccountDialog.hidden || requestId !== qvAccountRequestId) return;
      const initial = account.ho_ten?.trim().split(/\s+/).slice(-1)[0]?.charAt(0).toUpperCase() || "?";
      const joinedAt = account.ngay_tao
        ? new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(account.ngay_tao))
        : "—";
      const row = (label, value) => `<li class="tk-muc"><div class="tk-hang"><span class="tk-nhan">${label}</span><span class="tk-gia-tri">${escapeHtml(value || "—")}</span></div></li>`;
      content.innerHTML = `
        <div class="tk-avatar" aria-hidden="true">${escapeHtml(initial)}</div>
        <ul class="tk-ds">
          ${row("Họ và tên", account.ho_ten)}
          ${row("Email", account.email)}
          ${row("Số điện thoại", account.so_dien_thoai)}
          ${row("Vai trò", "Nhân viên quầy vé")}
          ${row("Văn phòng", office.ten)}
          ${row("Địa chỉ văn phòng", office.dia_chi)}
          ${row("Ngày tham gia", joinedAt)}
        </ul>`;
    })
    .catch((error) => {
      if (!qvAccountDialog.hidden && requestId === qvAccountRequestId) {
        content.innerHTML = `<p class="qv-alert error" role="alert">${escapeHtml(error.message || "Không tải được thông tin tài khoản.")}</p>`;
      }
    });
}

function qvCloseAccountDetails() {
  if (!qvAccountDialog || qvAccountDialog.hidden) return;
  qvAccountRequestId += 1;
  qvAccountDialog.hidden = true;
  qvAccountDialog.returnFocusTo?.focus();
}

function qvPageHeader(title) {
  const heading = document.querySelector("#qv-header h1");
  if (heading) heading.textContent = title;
}
