/* Xem trọn lượt vé tại quầy; vé được chọn luôn đứng đầu. */
const qvTicketDetail = (() => {
  const dialog = document.createElement("dialog");
  dialog.className = "qv-history-ticket-dialog qv-booking-detail-dialog";
  dialog.setAttribute("aria-labelledby", "qv-booking-detail-title");
  dialog.innerHTML = `
    <div class="qv-history-ticket-dialog__head">
      <div><span>CHI TIẾT LƯỢT VÉ</span><h2 id="qv-booking-detail-title">Thông tin vé</h2></div>
      <button class="qv-history-ticket-dialog__x" type="button" data-close-booking-detail aria-label="Đóng">×</button>
    </div>
    <div class="qv-history-ticket-dialog__body" data-booking-detail-content aria-live="polite"></div>
    <div class="qv-history-ticket-dialog__foot"><button class="qv-btn secondary" type="button" data-close-booking-detail>Đóng</button></div>`;
  document.body.append(dialog);
  const content = dialog.querySelector("[data-booking-detail-content]");
  const title = dialog.querySelector("#qv-booking-detail-title");
  let request = 0;

  const dateText = (value, options) => {
    const date = new Date(value);
    return !value || Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh", ...options
    }).format(date);
  };
  const stopTime = value => dateText(value, {
    hour: "2-digit", minute: "2-digit", weekday: "long", day: "2-digit", month: "2-digit", year: "numeric"
  });

  function ticketHtml(ticket) {
    const paid = ["da_thanh_toan", "da_len_xe", "da_xuong_xe", "khong_den"].includes(ticket.trang_thai);
    const cancelled = ticket.trang_thai === "da_huy";
    const amountPaid = paid ? Number(ticket.gia || 0) : 0;
    const stamp = cancelled ? "ĐÃ HỦY" : paid ? "ĐÃ THANH TOÁN" : "CHỜ THANH TOÁN";
    const stampClass = cancelled ? "qv-ticket__stamp--cancelled" : paid ? "" : "qv-ticket__stamp--pending";
    return `<div class="qv-ticket" aria-label="Vé ${escapeHtml(ticket.ma_ve)}">
      <div class="qv-ticket__main">
        <header class="qv-ticket__header">
          <div class="qv-ticket__brand"><img src="/shared/assets/logo-mark.png" alt="" /><strong>GoBus</strong><span>VÉ XE KHÁCH LIÊN TỈNH</span></div>
          <div class="qv-ticket__code"><small>MÃ VÉ</small><strong>${escapeHtml(ticket.ma_ve)}</strong></div>
        </header>
        <div class="qv-ticket__body">
          <div class="qv-ticket__route"><h2>${escapeHtml(ticket.ten_tuyen || "Thông tin chuyến")}</h2><span class="qv-ticket__stamp ${stampClass}">${stamp}</span></div>
          <div class="qv-ticket__stops">
            <div><small>ĐIỂM ĐÓN</small><strong>${escapeHtml(ticket.ten_diem_don || "—")}</strong><span>${stopTime(ticket.gio_don_du_kien)}</span></div>
            <span class="qv-ticket__arrow" aria-hidden="true">→</span>
            <div><small>ĐIỂM TRẢ</small><strong>${escapeHtml(ticket.ten_diem_tra || "—")}</strong><span>${stopTime(ticket.gio_den_du_kien)} (dự kiến)</span></div>
          </div>
          <dl class="qv-ticket__details">
            <div><dt>LOẠI XE</dt><dd>${escapeHtml(ticket.ten_loai_xe || "—")}</dd></div>
            <div><dt>BIỂN SỐ</dt><dd>${escapeHtml(ticket.bien_so || "Chưa gán xe")}</dd></div>
            <div><dt>GIÁ VÉ</dt><dd>${dinhDangTien(ticket.gia)}</dd></div>
            <div><dt>ĐÃ THANH TOÁN</dt><dd>${dinhDangTien(amountPaid)}</dd></div>
            <div><dt>CÒN LẠI</dt><dd>${dinhDangTien(Math.max(0, Number(ticket.gia || 0) - amountPaid))}</dd></div>
            <div><dt>MÃ ĐẶT CHỖ</dt><dd>${escapeHtml(ticket.ma_dat_cho || "—")}</dd></div>
          </dl>
          <div class="qv-ticket__passenger"><span>HÀNH KHÁCH <strong>${escapeHtml(ticket.ten_khach || "Khách vãng lai")}${ticket.sdt_khach ? ` · ${escapeHtml(ticket.sdt_khach)}` : ""}</strong></span><span>CHUYẾN <strong>${escapeHtml(ticket.ma_chuyen || "—")}</strong></span></div>
          ${ticket.nhan_vien_ban ? `<div class="qv-ticket__seller"><span>NHÂN VIÊN BÁN VÉ</span><strong>${escapeHtml(ticket.nhan_vien_ban)}</strong><b>${escapeHtml(ticket.ma_nhan_vien_ban || "—")}</b>${ticket.van_phong_nhan_vien_ban ? `<small>${escapeHtml(ticket.van_phong_nhan_vien_ban)}</small>` : ""}</div>` : ""}
        </div>
      </div>
      <aside class="qv-ticket__stub"><div class="qv-ticket__seat"><small>GHẾ</small><strong>${escapeHtml(ticket.so_ghe || "—")}</strong></div><div class="qv-ticket__barcode-wrap"><svg class="qv-ticket__barcode" aria-label="Mã vạch vé ${escapeHtml(ticket.ma_ve)}"></svg><strong>${escapeHtml(ticket.ma_ve)}</strong></div><p class="qv-ticket__reminder">Vui lòng có mặt tại điểm đón trước giờ lên xe và xuất trình vé khi được yêu cầu.</p></aside>
    </div>`;
  }

  function renderBarcodes(tickets) {
    content.querySelectorAll(".qv-ticket__barcode").forEach((svg, index) => {
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

  async function open(code, firstId = "") {
    if (!code) return;
    const current = ++request;
    title.textContent = `Lượt vé ${code}`;
    content.innerHTML = '<p class="qv-history-ticket-dialog__loading">Đang tải các vé trong lượt…</p>';
    if (!dialog.open) dialog.showModal();
    try {
      const rows = await apiGet(`/quay-ve/tra-cuu?${queryString({ ma_dat_cho: code })}`);
      if (current !== request) return;
      const tickets = rows.filter(ticket => ticket.ma_dat_cho === code);
      if (!tickets.length) throw new Error("Không tìm thấy vé trong lượt đặt chỗ này tại văn phòng của bạn.");
      tickets.sort((a, b) => Number(String(b.id) === String(firstId)) - Number(String(a.id) === String(firstId)));
      content.innerHTML = `<p class="qv-booking-detail-dialog__summary">${tickets.length} vé trong lượt · Mã đặt chỗ <strong>${escapeHtml(code)}</strong></p><div class="qv-ticket-stack">${tickets.map(ticketHtml).join("")}</div>`;
      renderBarcodes(tickets);
      content.scrollTop = 0;
    } catch (error) {
      if (current === request) content.innerHTML = `<div class="qv-history-ticket-dialog__error"><strong>Không tải được lượt vé</strong><span>${escapeHtml(error.message || "Vui lòng thử lại.")}</span></div>`;
    }
  }

  dialog.querySelectorAll("[data-close-booking-detail]").forEach(button => button.addEventListener("click", () => dialog.close()));
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => { ++request; });
  return { open };
})();
