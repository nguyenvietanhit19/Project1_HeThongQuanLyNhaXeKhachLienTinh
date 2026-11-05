/* Xem trước và in vé ngay trên trang bán vé. */
const qvTicketPrint = (() => {
  const dialog = document.querySelector("#print-dialog");
  const content = document.querySelector("#print-dialog-content");
  const sheet = document.querySelector("#print-sheet");
  const printButton = document.querySelector("#print-ticket-button");
  let request = 0;

  const ticketTime = value => {
    const date = new Date(value);
    return !value || Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false
    }).format(date);
  };
  const ticketDate = value => {
    const date = new Date(value);
    return !value || Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh", weekday: "long", day: "2-digit", month: "2-digit", year: "numeric"
    }).format(date);
  };
  function ticketHtml(ticket) {
    const paid = ["da_thanh_toan", "da_len_xe", "da_xuong_xe", "khong_den"].includes(ticket.trang_thai);
    const cancelled = ticket.trang_thai === "da_huy";
    const paidAmount = paid ? Number(ticket.gia || 0) : 0;
    const stamp = cancelled ? "ĐÃ HỦY" : paid ? "ĐÃ THANH TOÁN" : "CHỜ THANH TOÁN";
    const stampClass = cancelled ? "qv-ticket__stamp--cancelled" : paid ? "" : "qv-ticket__stamp--pending";
    return `<div class="qv-ticket" aria-label="Vé xe khách ${escapeHtml(ticket.ma_ve)}">
      <div class="qv-ticket__main">
        <header class="qv-ticket__header">
          <div class="qv-ticket__brand"><img src="/shared/assets/logo-mark.png" alt="" /><strong>GoBus</strong><span>VÉ XE KHÁCH LIÊN TỈNH</span></div>
          <div class="qv-ticket__code"><small>MÃ VÉ</small><strong>${escapeHtml(ticket.ma_ve)}</strong></div>
        </header>
        <div class="qv-ticket__body">
          <div class="qv-ticket__route"><h2>${escapeHtml(ticket.ten_tuyen || "Thông tin chuyến")}</h2><span class="qv-ticket__stamp ${stampClass}">${stamp}</span></div>
          <div class="qv-ticket__stops">
            <div><small>ĐIỂM ĐÓN</small><strong>${escapeHtml(ticket.ten_diem_don || "—")}</strong><span>${ticketTime(ticket.gio_don_du_kien)} · ${ticketDate(ticket.gio_don_du_kien)}</span></div>
            <span class="qv-ticket__arrow" aria-hidden="true">→</span>
            <div><small>ĐIỂM TRẢ</small><strong>${escapeHtml(ticket.ten_diem_tra || "—")}</strong><span>${ticketTime(ticket.gio_den_du_kien)} · ${ticketDate(ticket.gio_den_du_kien)} (dự kiến)</span></div>
          </div>
          <dl class="qv-ticket__details">
            <div><dt>LOẠI XE</dt><dd>${escapeHtml(ticket.ten_loai_xe || "—")}</dd></div>
            <div><dt>BIỂN SỐ</dt><dd>${escapeHtml(ticket.bien_so || "Chưa gán xe")}</dd></div>
            <div><dt>GIÁ VÉ</dt><dd>${dinhDangTien(ticket.gia)}</dd></div>
            <div><dt>ĐÃ THANH TOÁN</dt><dd>${dinhDangTien(paidAmount)}</dd></div>
            <div><dt>CÒN LẠI</dt><dd>${dinhDangTien(Math.max(0, Number(ticket.gia || 0) - paidAmount))}</dd></div>
            <div><dt>MÃ ĐẶT CHỖ</dt><dd>${escapeHtml(ticket.ma_dat_cho || "—")}</dd></div>
          </dl>
          <div class="qv-ticket__passenger"><span>HÀNH KHÁCH <strong>${escapeHtml(ticket.ten_khach || "Khách vãng lai")}${ticket.sdt_khach ? ` · ${escapeHtml(ticket.sdt_khach)}` : ""}</strong></span><span>CHUYẾN <strong>${escapeHtml(ticket.ma_chuyen || "—")}</strong></span></div>
        </div>
      </div>
      <aside class="qv-ticket__stub" aria-label="Cuống vé">
        <div class="qv-ticket__seat"><small>GHẾ</small><strong>${escapeHtml(ticket.so_ghe || "—")}</strong></div>
        <div class="qv-ticket__barcode-wrap"><svg class="qv-ticket__barcode" role="img" aria-label="Mã vạch vé ${escapeHtml(ticket.ma_ve)}"></svg><strong>${escapeHtml(ticket.ma_ve)}</strong></div>
        <p class="qv-ticket__reminder">Vui lòng có mặt tại điểm đón trước giờ lên xe và xuất trình vé khi được yêu cầu.</p>
      </aside>
    </div>`;
  }
  function renderBarcode(container, tickets) {
    container.querySelectorAll(".qv-ticket__barcode").forEach((svg, index) => {
      if (typeof JsBarcode !== "function") { svg.hidden = true; return; }
      try {
        JsBarcode(svg, String(tickets[index].ma_ve), {
          format: "CODE128", width: 2, height: 50, displayValue: false, margin: 0, lineColor: "#282038"
        });
        const width = svg.getAttribute("width"), height = svg.getAttribute("height");
        if (width && height) svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.removeAttribute("width"); svg.removeAttribute("height");
      } catch (_) { svg.hidden = true; }
    });
  }
  function openLoading() {
    const id = ++request;
    document.querySelector("#print-dialog-title").textContent = "Đang tải vé…";
    content.innerHTML = '<p class="qv-history-ticket-dialog__loading">Đang tải vé để in…</p>';
    sheet.innerHTML = "";
    document.body.classList.remove("qv-print-ready");
    printButton.disabled = true;
    if (!dialog.open) dialog.showModal();
    return id;
  }
  function showError(error) {
    document.querySelector("#print-dialog-title").textContent = "Không tải được vé";
    content.innerHTML = `<div class="qv-history-ticket-dialog__error"><strong>Không thể in vé</strong><span>${escapeHtml(error.message || "Vui lòng thử lại.")}</span></div>`;
  }
  function showTickets(tickets, bookingCode = "", total = tickets.length) {
    document.querySelector("#print-dialog-title").textContent = bookingCode ? `Lượt vé ${bookingCode}` : `Vé ${tickets[0].ma_ve}`;
    const html = `<div class="qv-ticket-stack">${tickets.map(ticketHtml).join("")}</div>`;
    const excluded = total - tickets.length;
    content.innerHTML = `<p class="qv-print-dialog__note">${tickets.length} vé đã thanh toán sẵn sàng in.${excluded ? ` ${excluded} vé chưa đủ điều kiện sẽ không có trong bản in.` : ""}</p>${html}`;
    sheet.innerHTML = html;
    renderBarcode(content, tickets);
    renderBarcode(sheet, tickets);
    printButton.textContent = `In ${tickets.length} vé`;
    printButton.disabled = false;
    document.body.classList.add("qv-print-ready");
  }
  async function openTicket(id) {
    const current = openLoading();
    try {
      const ticket = await apiGet(`/quay-ve/ve/${encodeURIComponent(id)}/in`);
      if (current === request) showTickets([ticket]);
    } catch (error) { if (current === request) showError(error); }
  }
  async function openBooking(code) {
    const current = openLoading();
    try {
      const all = await apiGet(`/quay-ve/tra-cuu?${queryString({ ma_dat_cho: code })}`);
      if (current !== request) return;
      const matching = all.filter(ticket => ticket.ma_dat_cho === code);
      if (!matching.length) throw new Error("Không tìm thấy vé thuộc lượt đặt chỗ này tại văn phòng của bạn.");
      const printable = matching.filter(ticket => ticket.co_the_in && ticket.trang_thai === "da_thanh_toan");
      if (!printable.length) throw new Error("Lượt này chưa có vé đã thanh toán để in.");
      const tickets = await Promise.all(printable.map(ticket => apiGet(`/quay-ve/ve/${encodeURIComponent(ticket.id)}/in`)));
      if (current === request) showTickets(tickets, code, matching.length);
    } catch (error) { if (current === request) showError(error); }
  }
  dialog.querySelectorAll("[data-close-print-dialog]").forEach(button => button.addEventListener("click", () => dialog.close()));
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => {
    if (dialog.open) return;
    ++request;
    sheet.innerHTML = "";
    document.body.classList.remove("qv-print-ready");
  });
  printButton.addEventListener("click", () => { if (!printButton.disabled) window.print(); });
  return { openTicket, openBooking };
})();
