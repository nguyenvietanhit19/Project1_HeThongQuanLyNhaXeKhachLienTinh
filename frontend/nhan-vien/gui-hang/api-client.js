/*
 * api-client.js — Module kết nối Backend API cho phân hệ Nhân viên gửi hàng.
 * Tự động gắn Bearer Token và chuẩn hóa bắt lỗi.
 */

const API_BASE_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://localhost:8000"
  : "https://nha-xe-khach-backend.onrender.com";

async function apiFetch(duongDan, tuyChon = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(tuyChon.headers || {}),
  };

  try {
    const res = await fetch(`${API_BASE_URL}${duongDan}`, { ...tuyChon, headers });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const thongBaoLoi = data.loi || data.detail || `Lỗi HTTP ${res.status}`;
      throw new Error(thongBaoLoi);
    }
    return data;
  } catch (err) {
    console.error(`[API Lỗi] ${duongDan}:`, err);
    throw err;
  }
}

function apiGet(duongDan) {
  return apiFetch(duongDan, { method: "GET" });
}

function apiPost(duongDan, body = {}) {
  return apiFetch(duongDan, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function apiPut(duongDan, body = {}) {
  return apiFetch(duongDan, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

