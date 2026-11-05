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
  const VAI_TRO_CO_CHUONG = ["quan_ly", "nhan_vien_quay_ve"];
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
  let lanTai = 0;
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

  const modalChiTiet = document.createElement("dialog");
  modalChiTiet.className = "nv-bell-detail";
  modalChiTiet.setAttribute("aria-labelledby", "nv-bell-detail-title");
  modalChiTiet.innerHTML = `
    <div class="nv-bell-detail__head">
      <div><span class="nv-bell-detail__eyebrow">NHẮC KHÁCH SẮP ĐẾN GIỜ ĐI</span><h2 id="nv-bell-detail-title">Thông tin khách và vé</h2></div>
      <button type="button" class="nv-bell-detail__close" aria-label="Đóng">×</button>
    </div>
    <div class="nv-bell-detail__body" aria-live="polite"><p class="nv-bell-detail__loading">Đang tải thông tin lượt vé…</p></div>
    <div class="nv-bell-detail__foot"><button type="button" class="nv-bell-detail__done">Đóng</button></div>`;
  document.body.appendChild(modalChiTiet);
  const modalBody = modalChiTiet.querySelector(".nv-bell-detail__body");
  const dongModalChiTiet = () => modalChiTiet.close();
  modalChiTiet.querySelector(".nv-bell-detail__close").addEventListener("click", dongModalChiTiet);
  modalChiTiet.querySelector(".nv-bell-detail__done").addEventListener("click", dongModalChiTiet);
  modalChiTiet.addEventListener("click", (e) => {
    if (e.target === modalChiTiet) dongModalChiTiet();
  });

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
        <button type="button" class="nv-bell__item${tb.da_doc ? "" : " chua-doc"}${laNhacQuayVe(tb) ? " nv-bell__item--urgent" : ""}" data-id="${esc(tb.id)}">
          <span class="nv-bell__cham" aria-hidden="true"></span>
          <span class="nv-bell__noi-dung">
            ${laNhacQuayVe(tb) ? '<span class="nv-bell__nhan-khan">CẦN LIÊN HỆ KHÁCH</span>' : ""}
            <span class="nv-bell__text">${esc(tb.noi_dung)}</span>
            <span class="nv-bell__cuoi">
              <span class="nv-bell__time">${esc(thoiGianTuongDoi(tb.ngay_tao))}</span>
              <span class="nv-bell__trang-thai${tb.da_doc ? "" : " nv-bell__trang-thai--moi"}">${tb.da_doc ? "Đã đọc" : "Chưa đọc"}</span>
              ${laNhacQuayVe(tb) ? '<span class="nv-bell__hanh-dong">Xem các vé cần liên hệ →</span>' : ""}
            </span>
          </span>
        </button>`
      )
      .join("");
  }

  function laNhacQuayVe(tb) {
    return typeof tb?.duong_dan === "string" && tb.duong_dan.startsWith("/nhan-vien/quay-ve/tra-cuu-ve.html?ma_dat_cho=");
  }

  function dinhDangTien(value) {
    return `${new Intl.NumberFormat("vi-VN").format(Number(value || 0))} đ`;
  }

  function dinhDangNgayGio(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Chưa có giờ chạy" : date.toLocaleString("vi-VN", { dateStyle: "long", timeStyle: "short" });
  }

  function veTrongModal(item, maDatCho) {
    const daTraTien = ["da_thanh_toan", "da_len_xe", "da_xuong_xe", "khong_den"].includes(item.trang_thai);
    const daHuy = item.trang_thai === "da_huy";
    const stamp = daHuy ? "ĐÃ HỦY" : daTraTien ? "ĐÃ THANH TOÁN" : "CHỜ THANH TOÁN";
    const stampClass = daHuy ? "nv-bell-ticket__stamp--cancelled" : daTraTien ? "" : "nv-bell-ticket__stamp--pending";
    const gia = Number(item.gia || 0);
    const daThanhToan = daTraTien ? gia : 0;
    return `
      <div class="nv-bell-ticket" aria-label="Vé ${esc(item.ma_ve || "")}">
        <div class="nv-bell-ticket__main">
          <header class="nv-bell-ticket__header">
            <div class="nv-bell-ticket__brand"><img src="/shared/assets/logo-mark.png" alt="" /><strong>GoBus</strong><span>VÉ XE KHÁCH LIÊN TỈNH</span></div>
            <div class="nv-bell-ticket__code"><small>MÃ VÉ</small><strong>${esc(item.ma_ve || "—")}</strong></div>
          </header>
          <div class="nv-bell-ticket__body">
            <div class="nv-bell-ticket__route"><h3>${esc(item.ten_tuyen || "Thông tin chuyến")}</h3><span class="nv-bell-ticket__stamp ${stampClass}">${stamp}</span></div>
            <div class="nv-bell-ticket__stops">
              <div><small>ĐIỂM ĐÓN</small><strong>${esc(item.ten_diem_don || "—")}</strong><span>${esc(dinhDangNgayGio(item.gio_don_du_kien))}</span></div>
              <span class="nv-bell-ticket__arrow" aria-hidden="true">→</span>
              <div><small>ĐIỂM TRẢ</small><strong>${esc(item.ten_diem_tra || "—")}</strong><span>${esc(dinhDangNgayGio(item.gio_den_du_kien))} (dự kiến)</span></div>
            </div>
            <div class="nv-bell-ticket__details">
              <div><small>LOẠI XE</small><strong>${esc(item.ten_loai_xe || "—")}</strong></div>
              <div><small>BIỂN SỐ</small><strong>${esc(item.bien_so || "Chưa gán xe")}</strong></div>
              <div><small>GIÁ VÉ</small><strong>${esc(dinhDangTien(gia))}</strong></div>
              <div><small>ĐÃ THANH TOÁN</small><strong>${esc(dinhDangTien(daThanhToan))}</strong></div>
              <div><small>CÒN LẠI</small><strong class="nv-bell-ticket__remaining">${esc(dinhDangTien(Math.max(0, gia - daThanhToan)))}</strong></div>
              <div><small>MÃ ĐẶT CHỖ</small><strong>${esc(item.ma_dat_cho || maDatCho)}</strong></div>
            </div>
            <div class="nv-bell-ticket__passenger"><span>HÀNH KHÁCH <strong>${esc(item.ten_khach || "Khách vãng lai")}${item.sdt_khach ? ` · ${esc(item.sdt_khach)}` : ""}</strong></span><span>CHUYẾN <strong>${esc(item.ma_chuyen || "—")}</strong></span></div>
          </div>
        </div>
        <aside class="nv-bell-ticket__stub"><div class="nv-bell-ticket__seat"><small>GHẾ</small><strong>${esc(item.so_ghe || "—")}</strong></div><div class="nv-bell-ticket__barcode"><span></span><strong>${esc(item.ma_ve || "—")}</strong></div><p>Vui lòng có mặt tại điểm đón trước giờ lên xe.</p></aside>
      </div>`;
  }

  async function saoChepSoDienThoai(phone, status) {
    if (!phone) return;
    try {
      await navigator.clipboard.writeText(phone);
    } catch (_) {
      const input = document.createElement("textarea");
      input.value = phone;
      input.setAttribute("readonly", "");
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      input.remove();
    }
    status.textContent = "Đã sao chép số điện thoại";
    setTimeout(() => { if (status.isConnected) status.textContent = ""; }, 1800);
  }

  async function moChiTietNhacQuayVe(tb) {
    dongBang();
    modalBody.innerHTML = '<p class="nv-bell-detail__loading">Đang tải thông tin lượt vé…</p>';
    modalChiTiet.showModal();
    try {
      const maDatCho = new URL(tb.duong_dan, location.origin).searchParams.get("ma_dat_cho");
      if (!maDatCho) throw new Error("Thông báo không có mã đặt chỗ hợp lệ.");
      const ve = await apiGet(`/quay-ve/tra-cuu?ma_dat_cho=${encodeURIComponent(maDatCho)}`);
      if (!Array.isArray(ve) || !ve.length) throw new Error("Không tìm thấy vé thuộc văn phòng của bạn.");
      const khach = ve[0];
      const bayGio = Date.now();
      const gioiHanNhac = bayGio + 2 * 60 * 60 * 1000;
      const veCanNhac = ve.filter((item) => {
        const gioKhoiHanh = new Date(item.gio_khoi_hanh).getTime();
        return item.trang_thai === "giu_cho"
          && item.loai_hinh_thanh_toan === "thanh_toan_tai_quay"
          && !item.han_giu_cho_den
          && item.trang_thai_chuyen === "chua_khoi_hanh"
          && gioKhoiHanh > bayGio
          && gioKhoiHanh <= gioiHanNhac;
      });
      const phone = khach.sdt_khach || "";
      modalBody.innerHTML = `
        <section class="nv-bell-detail__customer">
          <div class="nv-bell-detail__customer-icon" aria-hidden="true">${esc((khach.ten_khach || "K").trim().slice(0, 1).toUpperCase())}</div>
          <div class="nv-bell-detail__customer-info">
            <span class="nv-bell-detail__label">KHÁCH HÀNG</span>
            <strong class="nv-bell-detail__customer-name">${esc(khach.ten_khach || "Khách vãng lai")}</strong>
            <div class="nv-bell-detail__phone-row">
              <span class="nv-bell-detail__phone">${esc(phone || "Chưa có số điện thoại")}</span>
              <button type="button" class="nv-bell-detail__copy" ${phone ? "" : "disabled"}>Sao chép</button>
            </div>
            <span class="nv-bell-detail__copy-status" aria-live="polite"></span>
          </div>
        </section>
        <section class="nv-bell-detail__tickets">
          <div class="nv-bell-detail__tickets-head"><h3>Vé chưa thanh toán, sắp khởi hành</h3><span>${veCanNhac.length} vé</span></div>
          <div class="nv-bell-detail__ticket-stack">${veCanNhac.length
            ? veCanNhac.map((item) => veTrongModal(item, maDatCho)).join("")
            : '<div class="nv-bell-detail__no-tickets">Không còn vé chưa thanh toán trong vòng 2 giờ tới. Có thể khách đã thanh toán hoặc chuyến đã khởi hành.</div>'}</div>
        </section>`;
      const copyButton = modalBody.querySelector(".nv-bell-detail__copy");
      const copyStatus = modalBody.querySelector(".nv-bell-detail__copy-status");
      copyButton?.addEventListener("click", () => saoChepSoDienThoai(phone, copyStatus));

      if (!modalChiTiet.open) return;
      try {
        await apiPut(`/thong-bao/${encodeURIComponent(tb.id)}/da-doc`);
        await tai();
      } catch (_) { /* giữ modal mở; người dùng vẫn xem được chi tiết */ }
    } catch (err) {
      modalBody.innerHTML = `<div class="nv-bell-detail__error"><strong>Chưa tải được thông tin vé</strong><span>${esc(err.message || "Vui lòng thử lại.")}</span></div>`;
    }
  }

  function hienToast(tb) {
    while (khungToast.children.length >= SO_TOAST_TOI_DA) khungToast.firstElementChild.remove();
    const el = document.createElement("div");
    const khan = laNhacQuayVe(tb);
    el.className = `tb-toast${khan ? " tb-toast--urgent" : ""}`;
    el.innerHTML = `
      <span class="tb-toast__than">
        <span class="tb-toast__tieu-de">${khan ? "CẦN LIÊN HỆ KHÁCH" : "Thông báo mới"}</span>
        <span class="tb-toast__noi-dung">${esc(tb.noi_dung)}</span>
        ${khan ? '<span class="tb-toast__hanh-dong">Mở lượt vé để xem thông tin →</span>' : ""}
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
    const lan = ++lanTai;
    try {
      const data = await apiGet("/thong-bao/cua-toi?limit=30");
      if (lan !== lanTai) return;
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
    if (laNhacQuayVe(tb)) {
      moChiTietNhacQuayVe(tb);
      return;
    }
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
