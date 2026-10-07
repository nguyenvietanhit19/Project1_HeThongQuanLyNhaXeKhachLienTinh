/*
 * nav.js — Sidebar, Topbar (văn phòng + chuông thông báo) và banner giới thiệu từng tab
 * cho phân hệ Nhân viên gửi hàng (GoBus Cargo).
 */

const ICON = {
  goi: '<path d="m16.5 9.4-9-5.19M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
  xe: '<rect x="1" y="3" width="15" height="13" rx="2"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  danhSach: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
  canhBao: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  thongKe: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  chuong: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
};

// chiQuay: chỉ nhân viên gửi hàng (thao tác tại quầy), quản lý không thấy.
const MENU_GUI_HANG = [
  { id: "tao-don", label: "Tiếp nhận gửi hàng", icon: ICON.goi, chiQuay: true },
  { id: "hang-den", label: "Hàng đến & Giao hàng", icon: ICON.xe },
  { id: "don-gui", label: "Đơn gửi đi", icon: ICON.danhSach },
  { id: "hang-ton", label: "Hàng chờ lâu", icon: ICON.canhBao },
  { id: "thong-ke", label: "Thống kê & Đối soát", icon: ICON.thongKe },
];

const TAB_METADATA = {
  "tao-don": {
    title: "Tiếp nhận gửi hàng",
    introTitle: "Tiếp nhận đơn gửi hàng mới tại quầy",
    introDesc: "Nhập người gửi/nhận, chọn khu vực → văn phòng nhận → tuyến, cân đo hàng, tự nhập cước, báo giá cho khách rồi tạo đơn và in biên nhận + nhãn dán.",
    icon: ICON.goi, statLabel: "đơn tạo hôm nay", statId: "stat-tao-don-count",
  },
  "hang-den": {
    title: "Hàng đến & Giao hàng",
    introTitle: "Hàng gửi tới văn phòng — gọi báo người nhận & bàn giao",
    introDesc: "Theo dõi hàng sắp đến, gọi báo người nhận ngay khi hàng tới, tra cứu theo mã vận đơn hoặc SĐT, thu COD và xác nhận giao hàng.",
    icon: ICON.xe, statLabel: "kiện chờ giao", statId: "stat-hang-den-count",
  },
  "don-gui": {
    title: "Đơn gửi đi",
    introTitle: "Đơn hàng tiếp nhận tại văn phòng",
    introDesc: "Tra cứu các đơn đã nhận tại quầy, theo dõi hành trình (chờ xếp xe → đang trên xe → chờ lấy → đã giao), in lại biên nhận và nhãn dán.",
    icon: ICON.danhSach, statLabel: "đơn đã tiếp nhận", statId: "stat-don-gui-count",
  },
  "hang-ton": {
    title: "Hàng chờ lâu & Hàng tồn",
    introTitle: "Xử lý hàng chờ quá lâu tại điểm nhận",
    introDesc: "Đơn chờ lấy quá 7 ngày được cảnh báo, quá 14 ngày chuyển hàng tồn. Liên hệ đúng đối tượng theo gợi ý và ghi lại kết quả; không liên hệ được ai thì báo quản lý.",
    icon: ICON.canhBao, statLabel: "kiện cần xử lý", statId: "stat-hang-ton-count",
  },
  "thong-ke": {
    title: "Thống kê & Đối soát",
    introTitle: "Thống kê hàng hóa & đối soát tiền mặt",
    introDesc: "Số đơn gửi đi / nhận về, hàng tồn và tiền thu tại quầy theo khoảng ngày; đối soát tiền mặt từng nhân viên đã thu cuối ca.",
    icon: ICON.thongKe, statLabel: "đơn tiếp nhận trong kỳ", statId: "stat-thong-ke-count",
  },
};

function menuTheoVaiTro() {
  return MENU_GUI_HANG.filter(m => !(m.chiQuay && laQuanLyXem()));
}

function svgIcon(path, cls = "nv-sidebar__link-icon") {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

function renderSidebar(containerEl, tabDangMo) {
  if (!containerEl) return;
  const links = menuTheoVaiTro().map(muc => `
      <a class="nv-sidebar__link${muc.id === tabDangMo ? " active" : ""}" href="#${muc.id}" data-tab="${muc.id}">
        ${svgIcon(muc.icon)}
        <span>${muc.label}</span>
      </a>`).join("");

  containerEl.innerHTML = `
    <div class="nv-sidebar__brand">
      <span class="nv-sidebar__brand-mark">
        <img src="/shared/assets/logo-mark.png" alt="Logo" onerror="this.src='../../shared/assets/logo-mark.png'" />
      </span>
      <span class="nv-sidebar__brand-text">
        <strong>GoBus</strong>
        <em>Kết nối mọi hành trình</em>
      </span>
    </div>
    <div class="nv-sidebar__section-title">Nghiệp vụ gửi hàng</div>
    <nav class="nv-sidebar__nav">${links}</nav>
    <div class="nv-sidebar__deco" aria-hidden="true"></div>
  `;
  containerEl.querySelectorAll("[data-tab]").forEach(a => {
    a.addEventListener("click", e => {
      e.preventDefault();
      chuyenTab(a.dataset.tab);
    });
  });
}

/* Topbar dựng 1 lần, khi chuyển tab chỉ đổi tiêu đề — tránh mất trạng thái
   chuông thông báo / ô chọn văn phòng của quản lý. */
function renderTopbar() {
  const containerEl = document.getElementById("nv-topbar");
  if (!containerEl) return;

  const hoTen = localStorage.getItem("ho_ten") || "Nhân viên gửi hàng";
  const laQuanLy = laQuanLyXem();
  const vaiTroText = laQuanLy ? "Quản lý (chỉ xem)" : "NV Gửi hàng";
  const chuCaiDau = hoTen.trim().charAt(0).toUpperCase() || "?";

  const oVanPhong = laQuanLy
    ? `<select id="selectVanPhongXem" class="nv-topbar__select" title="Văn phòng đang xem">
         <option value="">🌐 Toàn hệ thống</option>
       </select>`
    : `<strong class="nv-topbar__van-phong-name" id="tenVanPhongHienTai">Đang nạp văn phòng...</strong>`;

  containerEl.innerHTML = `
    <div class="nv-topbar__left">
      <h1 id="nv-topbar-title">—</h1>
    </div>

    <div class="nv-topbar__right">
      <div class="nv-topbar__van-phong">
        <span class="nv-topbar__van-phong-icon">🏢</span>
        <div class="nv-topbar__van-phong-text">
          <span class="nv-topbar__van-phong-label">${laQuanLy ? "Văn phòng xem" : "Văn phòng phụ trách"}</span>
          ${oVanPhong}
        </div>
      </div>

      <div class="nv-bell" id="nvBell">
        <button type="button" class="nv-bell__btn" id="nvBellBtn" title="Thông báo" aria-haspopup="true" aria-expanded="false">
          ${svgIcon(ICON.chuong, "nv-bell__icon")}
          <span class="nv-bell__badge" id="nvBellBadge" hidden>0</span>
        </button>
        <div class="nv-bell__panel" id="nvBellPanel" hidden>
          <div class="nv-bell__head">
            <strong>Thông báo</strong>
            <button type="button" class="btn-text-action" id="nvBellDocHet">Đánh dấu đã đọc hết</button>
          </div>
          <div class="nv-bell__list" id="nvBellList"><div class="nv-bell__empty">Đang tải...</div></div>
        </div>
      </div>

      <div class="nv-topbar__user">
        <div class="nv-topbar__avatar">${escapeHtml(chuCaiDau)}</div>
        <div class="nv-topbar__identity">
          <span class="ho-ten">${escapeHtml(hoTen)}</span>
          <span class="nv-topbar__role">${vaiTroText}</span>
        </div>
        <button class="nv-btn-secondary" id="btn-dang-xuat" type="button">Đăng xuất</button>
      </div>
    </div>
  `;
  document.getElementById("btn-dang-xuat").addEventListener("click", dangXuatNhanVien);
}

function renderPageIntro(tabDangMo) {
  const containerEl = document.getElementById("nv-page-intro");
  if (!containerEl) return;
  const meta = TAB_METADATA[tabDangMo] || TAB_METADATA["hang-den"];

  containerEl.innerHTML = `
    <div class="nv-page-intro__icon">${svgIcon(meta.icon, "").replace('stroke="currentColor"', 'stroke="#fff"')}</div>
    <div class="nv-page-intro__body">
      <p class="nv-page-intro__title">${meta.introTitle}</p>
      <p class="nv-page-intro__desc">${meta.introDesc}</p>
    </div>
    <div class="nv-page-intro__stat">
      <span class="nv-page-intro__stat-num" id="${meta.statId}">—</span>
      <span class="nv-page-intro__stat-label">${meta.statLabel}</span>
    </div>
  `;
}

/* Sidebar dựng 1 lần; các lần chuyển tab sau chỉ đổi mục đang chọn. */
function khoiTaoNav(tabHienTai) {
  const sidebar = document.getElementById("nv-sidebar");
  if (sidebar && !sidebar.childElementCount) renderSidebar(sidebar, tabHienTai);
  sidebar?.querySelectorAll("[data-tab]").forEach(a => a.classList.toggle("active", a.dataset.tab === tabHienTai));
  renderPageIntro(tabHienTai);
  const elTitle = document.getElementById("nv-topbar-title");
  if (elTitle) elTitle.textContent = (TAB_METADATA[tabHienTai] || {}).title || "";
}

// ====================================================================
// Chuông thông báo — GET /thong-bao/cua-toi (nhắc hàng chờ 7/14 ngày, hàng mới tới,
// báo cáo sự cố). Cập nhật real-time qua WebSocket /ws; chỉ poll 60s khi WebSocket không kết nối.
// ====================================================================

let danhSachThongBao = [];
let wsDangKetNoi = false;
// Các thông báo của gửi hàng (hàng mới tới, sự cố, nhắc 7/14 ngày) chỉ làm đổi danh sách hàng đến.
const TAB_LAM_MOI_KHI_CO_THONG_BAO = ["hang-den", "hang-ton"];

async function taiThongBao() {
  try {
    const data = await apiGet("/thong-bao/cua-toi?limit=30");
    danhSachThongBao = data.items || [];
    const badge = document.getElementById("nvBellBadge");
    if (badge) {
      badge.textContent = data.so_chua_doc > 99 ? "99+" : String(data.so_chua_doc);
      badge.hidden = !data.so_chua_doc;
    }
    renderDanhSachThongBao();
  } catch (err) {
    console.error("Không tải được thông báo:", err);
  }
}

function renderDanhSachThongBao() {
  const list = document.getElementById("nvBellList");
  if (!list) return;
  if (!danhSachThongBao.length) {
    list.innerHTML = '<div class="nv-bell__empty">Chưa có thông báo nào.</div>';
    return;
  }
  list.innerHTML = danhSachThongBao.map(tb => `
    <button type="button" class="nv-bell__item${tb.da_doc ? "" : " chua-doc"}" data-id="${escapeHtml(tb.id)}" data-ma="${escapeHtml(tb.ma_van_don || "")}">
      <span class="nv-bell__text">${escapeHtml(tb.noi_dung)}</span>
      <span class="nv-bell__time">${escapeHtml(dinhDangThoiGian(tb.ngay_tao))}</span>
    </button>`).join("");
  list.querySelectorAll(".nv-bell__item").forEach(el => {
    el.addEventListener("click", async () => {
      try { await apiPut(`/thong-bao/${el.dataset.id}/da-doc`); } catch (_) {}
      dongChuong();
      taiThongBao();
      if (el.dataset.ma) moChiTietDon(el.dataset.ma);
    });
  });
}

function dongChuong() {
  const panel = document.getElementById("nvBellPanel");
  if (panel) panel.hidden = true;
  document.getElementById("nvBellBtn")?.setAttribute("aria-expanded", "false");
}

function khoiTaoChuong() {
  const btn = document.getElementById("nvBellBtn");
  const panel = document.getElementById("nvBellPanel");
  if (!btn || !panel) return;
  btn.addEventListener("click", e => {
    e.stopPropagation();
    panel.hidden = !panel.hidden;
    btn.setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) taiThongBao();
  });
  panel.addEventListener("click", e => e.stopPropagation());
  document.addEventListener("click", dongChuong);
  document.getElementById("nvBellDocHet")?.addEventListener("click", async () => {
    try { await apiPut("/thong-bao/da-doc-tat-ca"); } catch (_) {}
    taiThongBao();
  });

  taiThongBao();
  setInterval(() => { if (!wsDangKetNoi) taiThongBao(); }, 60000);
  ketNoiWebSocket();
}

function ketNoiWebSocket(soLanThu = 0) {
  const token = localStorage.getItem("token");
  if (!token || !window.WebSocket) return;
  const wsUrl = API_BASE_URL.replace(/^http/, "ws") + `/ws?token=${encodeURIComponent(token)}`;
  let ws;
  try {
    ws = new WebSocket(wsUrl);
  } catch (_) {
    return;
  }
  ws.onopen = () => {
    // Vừa kết nối (lại): tải 1 lần để bắt các thông báo phát ra lúc đang mất kết nối.
    if (soLanThu > 0) taiThongBao();
    soLanThu = 0;
    wsDangKetNoi = true;
  };
  ws.onmessage = event => {
    try {
      const data = JSON.parse(event.data);
      if (data.noi_dung) {
        showToast("info", "Thông báo mới", data.noi_dung, 7000);
        taiThongBao();
        if (TAB_LAM_MOI_KHI_CO_THONG_BAO.includes(state.tab)) lamMoiTabHienTai();
      }
    } catch (_) {}
  };
  ws.onclose = event => {
    wsDangKetNoi = false;
    if (event.code === 1008) return; // token sai/hết hạn — không thử lại
    const cho = Math.min(30000, 2000 * 2 ** soLanThu);
    setTimeout(() => ketNoiWebSocket(soLanThu + 1), cho);
  };
}
