const API_BASE_URL = (["localhost", "127.0.0.1"].includes(location.hostname) || /^\d+\.\d+\.\d+\.\d+$/.test(location.hostname))
  ? `http://${location.hostname}:8000`
  : "https://nha-xe-khach-backend.onrender.com";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map((e) => e.msg).join("; ")
      : data.loi || data.detail || `Lỗi HTTP ${response.status}`;
    if (response.status === 401) quayVeDangXuat();
    throw new Error(message);
  }
  return data;
}

function apiGet(path) { return apiFetch(path); }
function apiPost(path, body = {}) { return apiFetch(path, { method: "POST", body: JSON.stringify(body) }); }
function apiPut(path, body = {}) { return apiFetch(path, { method: "PUT", body: JSON.stringify(body) }); }
function queryString(data) {
  const query = new URLSearchParams();
  Object.entries(data).forEach(([key, value]) => { if (value !== "" && value != null) query.set(key, value); });
  return query.toString();
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function dinhDangTien(value) { return new Intl.NumberFormat("vi-VN").format(Number(value || 0)) + " ₫"; }
function dinhDangNgay(value) { return value ? new Date(value).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" }) : "—"; }

const QV_MODAL_ICONS = {
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
  success: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.7 2.7L16 9.5"/>',
  warning: '<path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.4L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 16h.01"/>',
  danger: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
};
const QV_MODAL_LABELS = { info: "THÔNG BÁO", success: "HOÀN TẤT", warning: "CẦN XÁC NHẬN", danger: "THAO TÁC QUAN TRỌNG" };
let qvModalSerial = 0;

function qvModal({ title, message, confirmText = "Đồng ý", cancelText = "", variant = "info" }) {
  return new Promise((resolve) => {
    const tone = Object.hasOwn(QV_MODAL_ICONS, variant) ? variant : "info";
    const id = ++qvModalSerial;
    const dialog = document.createElement("dialog");
    dialog.className = `qv-dialog qv-dialog--${tone}`;
    dialog.setAttribute("aria-labelledby", `qv-dialog-title-${id}`);
    dialog.setAttribute("aria-describedby", `qv-dialog-message-${id}`);
    dialog.innerHTML = `
      <div class="qv-dialog__inner">
        <div class="qv-dialog__top">
          <span class="qv-dialog__icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${QV_MODAL_ICONS[tone]}</svg></span>
          <button class="qv-dialog__close" type="button" data-modal-close aria-label="Đóng thông báo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>
          </button>
        </div>
        <div class="qv-dialog__copy">
          <p class="qv-dialog__eyebrow">${QV_MODAL_LABELS[tone]}</p>
          <h2 id="qv-dialog-title-${id}"></h2>
          <p class="qv-dialog__message" id="qv-dialog-message-${id}"></p>
        </div>
        <div class="qv-dialog__actions">
          ${cancelText ? '<button class="qv-dialog__button qv-dialog__button--secondary" type="button" data-modal-cancel></button>' : ""}
          <button class="qv-dialog__button qv-dialog__button--primary" type="button" data-modal-confirm></button>
        </div>
      </div>`;
    dialog.querySelector(`#qv-dialog-title-${id}`).textContent = title;
    dialog.querySelector(".qv-dialog__message").textContent = message;
    const confirmButton = dialog.querySelector("[data-modal-confirm]");
    confirmButton.textContent = confirmText;
    const cancelButton = dialog.querySelector("[data-modal-cancel]");
    if (cancelButton) cancelButton.textContent = cancelText;
    if (cancelButton) dialog.querySelector("[data-modal-close]").setAttribute("aria-label", "Hủy thao tác và đóng");
    let settled = false;
    const finish = (answer) => {
      if (settled) return;
      settled = true;
      dialog.close();
      dialog.remove();
      resolve(answer);
    };
    confirmButton.addEventListener("click", () => finish(true));
    cancelButton?.addEventListener("click", () => finish(false));
    dialog.querySelector("[data-modal-close]").addEventListener("click", () => finish(false));
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); finish(false); });
    document.body.appendChild(dialog);
    dialog.showModal();
    (cancelButton || confirmButton).focus();
  });
}

function qvAlert(message, title = "Thông báo", variant = "info") {
  return qvModal({ title, message, confirmText: "Đã hiểu", variant });
}

function qvConfirm(message, title = "Xác nhận", confirmText = "Xác nhận", variant = "warning") {
  return qvModal({ title, message, confirmText, cancelText: "Quay lại", variant });
}
