/*
 * api-client.js — Kết nối Backend API cho phân hệ Nhân viên gửi hàng.
 * Tự động gắn Bearer Token, chuẩn hóa bắt lỗi, xử lý hết phiên đăng nhập.
 */

// Cùng quy ước với frontend/shared/api-client.js (nhận diện môi trường qua
// hostname), thêm nhánh IP LAN để thử trên điện thoại cùng mạng.
const API_BASE_URL = (["localhost", "127.0.0.1"].includes(location.hostname) || /^\d+\.\d+\.\d+\.\d+$/.test(location.hostname))
  ? `http://${location.hostname}:8000`
  : "https://nha-xe-khach-backend.onrender.com";

class LoiApi extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function apiFetch(duongDan, tuyChon = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(tuyChon.headers || {}),
  };

  const res = await fetch(`${API_BASE_URL}${duongDan}`, { ...tuyChon, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    let thongBaoLoi = data.loi || data.detail || `Lỗi HTTP ${res.status}`;
    if (Array.isArray(thongBaoLoi)) {
      // Lỗi validate 422 của FastAPI: [{loc, msg}, ...]
      thongBaoLoi = thongBaoLoi.map(e => e.msg).join("; ");
    }
    // 401 = token hết hạn/không hợp lệ; 403 "đã bị khóa" = tài khoản bị khóa → đăng xuất.
    // 403 khác (sai phạm vi văn phòng, không đủ quyền) chỉ báo lỗi, không đăng xuất.
    if (res.status === 401 || (res.status === 403 && thongBaoLoi === "Tài khoản đã bị khóa")) {
      alert(res.status === 401 ? "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại." : thongBaoLoi);
      if (typeof dangXuatNhanVien === "function") dangXuatNhanVien();
    }
    throw new LoiApi(thongBaoLoi, res.status);
  }
  return data;
}

function apiGet(duongDan) {
  return apiFetch(duongDan, { method: "GET" });
}

function apiPost(duongDan, body = {}, headers = {}) {
  return apiFetch(duongDan, { method: "POST", body: JSON.stringify(body), headers });
}

function apiPut(duongDan, body = {}) {
  return apiFetch(duongDan, { method: "PUT", body: JSON.stringify(body) });
}

/** Ghép query string, bỏ qua giá trị rỗng/null. */
function taoQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.append(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** Escape mọi dữ liệu động trước khi chèn vào innerHTML (chống XSS). */
function escapeHtml(giaTri) {
  if (giaTri === null || giaTri === undefined) return "";
  return String(giaTri)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
