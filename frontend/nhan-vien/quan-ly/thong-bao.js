/*
 * Chuông thông báo cho vai trò Quản lý (quan_ly): chuông + huy hiệu số chưa đọc ở thanh trên cùng (`.nv-topbar`), bảng thả xuống
 * 30 thông báo gần nhất, toast khi có thông báo mới. Bấm 1 thông báo: đánh dấu đã đọc và mở trang liên quan nếu có `duong_dan`.
 * Dùng chung API với mọi vai trò: GET /thong-bao/cua-toi, PUT /thong-bao/{id}/da-doc, PUT /thong-bao/da-doc-tat-ca.
 * Bên gửi thông báo gọi thong_bao_khach_service.gui(nguoi_nhan_id, noi_dung, duong_dan=...).
 * CSS ở thong-bao.css cùng thư mục. Vai trò khác muốn có chuông thì sao chép 2 file này vào khu vực của mình, đổi VAI_TRO_CO_CHUONG,
 * nạp thong-bao.css trong <head> và thong-bao.js sau api-client.js (cần apiGet, apiPut, API_BASE_URL).
 *
 * Giao diện Quản lý gồm nhiều trang .html: mỗi lần chuyển trang đường dây WebSocket cũ đóng và trang mới nối lại, và máy chủ có thể
 * lỡ nhớ nhầm đường dây (xem websocket_manager.py). Vì vậy real-time chỉ là phần thêm cho nhanh; chuông luôn đúng nhờ:
 *   1. mỗi trang vừa tải xong là hỏi API lấy số chưa đọc;
 *   2. hỏi lại định kỳ mỗi 60 giây (bất kể WebSocket);
 *   3. hỏi lại khi tab hiện lại sau khi bị ẩn, và khi WebSocket nối lại;
 *   4. chủ động đóng WebSocket khi rời trang.
 * Bọc IIFE để không đụng tên biến của từng trang.
 */

(() => {
  const VAI_TRO_CO_CHUONG = ["quan_ly"]; // chỉ vai trò Quản lý
  const CHU_KY_HOI_LAI_MS = 60000;
  const SO_TOAST_TOI_DA = 3;
  const THOI_GIAN_TOAST_MS = 8000;
  const ICON_CHUONG = '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>';

  if (!localStorage.getItem("token") || !VAI_TRO_CO_CHUONG.includes(localStorage.getItem("vai_tro"))) return;
  const topbar = document.querySelector(".nv-topbar");
  if (!topbar) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");

  let thongBao = []; // 30 thông báo gần nhất, mới nhất trước
  let soChuaDoc = 0;
  let daBiet = null; // tập id đã thấy — null cho tới lần tải đầu tiên (lần đầu không bật toast)
  let ws = null;
  let henNoiLai = null;
  let dangDong = false;

  // ---------- Dựng chuông ----------
  const chuong = document.createElement("div");
  chuong.className = "nv-bell";
  chuong.innerHTML = `
    <button type="button" class="nv-bell__btn" id="nv-bell-btn" aria-haspopup="true" aria-expanded="false" aria-label="Thông báo">
      <svg class="nv-bell__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_CHUONG}</svg>
      <span class="nv-bell__badge" id="nv-bell-badge" hidden>0</span>
    </button>
    <div class="nv-bell__panel" id="nv-bell-panel" role="dialog" aria-label="Thông báo" hidden>
      <div class="nv-bell__head">
        <strong>Thông báo</strong>
        <button type="button" class="nv-bell__doc-het" id="nv-bell-doc-het">Đánh dấu đã đọc hết</button>
      </div>
      <div class="nv-bell__list" id="nv-bell-list"></div>
    </div>`;
  topbar.appendChild(chuong);

  const khungToast = document.createElement("div");
  khungToast.className = "tb-toast-khung";
  khungToast.setAttribute("aria-live", "polite");
  document.body.appendChild(khungToast);

  const nut = chuong.querySelector("#nv-bell-btn");
  const huyHieu = chuong.querySelector("#nv-bell-badge");
  const bang = chuong.querySelector("#nv-bell-panel");
  const danhSach = chuong.querySelector("#nv-bell-list");
  const nutDocHet = chuong.querySelector("#nv-bell-doc-het");

  // ---------- Hiển thị ----------
  function thoiGianTuongDoi(iso) {
    const t = new Date(iso).getTime();
    if (isNaN(t)) return "";
    const giay = Math.max(0, (Date.now() - t) / 1000);
    if (giay < 60) return "Vừa xong";
    if (giay < 3600) return `${Math.floor(giay / 60)} phút trước`;
    if (giay < 86400) return `${Math.floor(giay / 3600)} giờ trước`;
    if (giay < 172800) return "Hôm qua";
    const d = new Date(t);
    return `${pad2(d.getHours())}:${pad2(d.getMinutes())} ${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
  }

  // Chỉ cho đi tới trang nội bộ của khu nhân viên — đề phòng đường dẫn lạ trong dữ liệu
  function duongDanAnToan(duongDan) {
    return typeof duongDan === "string" && duongDan.startsWith("/nhan-vien/") && !duongDan.includes("//") ? duongDan : null;
  }

  function veHuyHieu() {
    huyHieu.textContent = soChuaDoc > 99 ? "99+" : String(soChuaDoc);
    huyHieu.hidden = soChuaDoc === 0;
  }

  function veDanhSach() {
    if (!thongBao.length) {
      danhSach.innerHTML = '<div class="nv-bell__trong">Chưa có thông báo nào.</div>';
      return;
    }
    danhSach.innerHTML = thongBao
      .map(
        (tb) => `
        <button type="button" class="nv-bell__item${tb.da_doc ? "" : " chua-doc"}" data-id="${esc(tb.id)}">
          <span class="nv-bell__cham" aria-hidden="true"></span>
          <span class="nv-bell__noi-dung">
            <span class="nv-bell__text">${esc(tb.noi_dung)}</span>
            <span class="nv-bell__time">${esc(thoiGianTuongDoi(tb.ngay_tao))}</span>
          </span>
        </button>`
      )
      .join("");
  }

  function hienToast(tb) {
    while (khungToast.children.length >= SO_TOAST_TOI_DA) khungToast.firstElementChild.remove();
    const el = document.createElement("div");
    el.className = "tb-toast";
    el.innerHTML = `
      <span class="tb-toast__than">
        <span class="tb-toast__tieu-de">Thông báo mới</span>
        <span class="tb-toast__noi-dung">${esc(tb.noi_dung)}</span>
      </span>
      <button type="button" class="tb-toast__dong" aria-label="Đóng">✕</button>`;
    const tat = () => {
      el.classList.add("dang-an");
      setTimeout(() => el.remove(), 260);
    };
    el.querySelector(".tb-toast__dong").addEventListener("click", (e) => {
      e.stopPropagation();
      tat();
    });
    el.addEventListener("click", () => {
      tat();
      moThongBao(tb.id);
    });
    khungToast.appendChild(el);
    setTimeout(tat, THOI_GIAN_TOAST_MS);
  }

  // ---------- Tải dữ liệu ----------
  async function tai() {
    try {
      const data = await apiGet("/thong-bao/cua-toi?limit=30");
      const moi = (data.items || []).filter((tb) => !tb.da_doc && daBiet && !daBiet.has(tb.id));
      thongBao = data.items || [];
      soChuaDoc = data.so_chua_doc || 0;
      daBiet = new Set(thongBao.map((tb) => tb.id));
      veHuyHieu();
      if (!bang.hidden) veDanhSach();
      moi.slice(0, SO_TOAST_TOI_DA).reverse().forEach(hienToast);
    } catch (err) {
      console.error("Không tải được thông báo:", err);
    }
  }

  // ---------- Thao tác ----------
  async function moThongBao(id) {
    const tb = thongBao.find((x) => x.id === id);
    try {
      await apiPut(`/thong-bao/${encodeURIComponent(id)}/da-doc`);
    } catch (_) {
      /* vẫn cho đi tiếp */
    }
    dongBang();
    const dich = duongDanAnToan(tb && tb.duong_dan);
    if (dich && dich !== location.pathname) {
      location.href = dich;
      return;
    }
    tai();
  }

  function dongBang() {
    bang.hidden = true;
    nut.setAttribute("aria-expanded", "false");
  }

  function moBang() {
    bang.hidden = false;
    nut.setAttribute("aria-expanded", "true");
    veDanhSach();
    tai();
  }

  nut.addEventListener("click", (e) => {
    e.stopPropagation();
    bang.hidden ? moBang() : dongBang();
  });
  bang.addEventListener("click", (e) => e.stopPropagation());
  danhSach.addEventListener("click", (e) => {
    const muc = e.target.closest(".nv-bell__item");
    if (muc) moThongBao(muc.dataset.id);
  });
  document.addEventListener("click", dongBang);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dongBang();
  });
  nutDocHet.addEventListener("click", async () => {
    try {
      await apiPut("/thong-bao/da-doc-tat-ca");
    } catch (_) {
      /* bỏ qua, tải lại bên dưới sẽ cho thấy trạng thái thật */
    }
    tai();
  });

  // ---------- Real-time (WebSocket) ----------
  function noiWebSocket(soLanThu = 0) {
    if (dangDong || !window.WebSocket) return;
    const token = localStorage.getItem("token");
    if (!token) return;
    let ket;
    try {
      ket = new WebSocket(`${API_BASE_URL.replace(/^http/, "ws")}/ws?token=${encodeURIComponent(token)}`);
    } catch (_) {
      return;
    }
    ws = ket;
    ket.onopen = () => {
      // Vừa nối (lại): tải 1 lần để bắt các thông báo phát ra lúc đang mất kết nối
      if (soLanThu > 0) tai();
      soLanThu = 0;
    };
    ket.onmessage = () => tai();
    ket.onclose = (e) => {
      if (ws === ket) ws = null;
      if (dangDong || e.code === 1008) return; // rời trang, hoặc token sai/hết hạn — không nối lại
      henNoiLai = setTimeout(() => noiWebSocket(soLanThu + 1), Math.min(30000, 2000 * 2 ** soLanThu));
    };
  }

  // Rời trang: đóng đường dây ngay để máy chủ không còn giữ đường dây cũ khi trang mới nối vào
  window.addEventListener("pagehide", () => {
    dangDong = true;
    clearTimeout(henNoiLai);
    if (ws) ws.close(1000);
  });

  // ---------- Khởi động ----------
  tai();
  noiWebSocket();
  setInterval(() => {
    if (!document.hidden) tai();
  }, CHU_KY_HOI_LAI_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tai();
  });
})();
