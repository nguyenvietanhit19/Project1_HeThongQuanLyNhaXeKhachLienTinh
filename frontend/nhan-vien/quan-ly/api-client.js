/*
 * Client gọi API cho các trang Quản lý — riêng của domain này, không dùng
 * chung với frontend/khach-hang/ hay các vai trò nhân viên khác (mỗi vai
 * trò tự viết CSS/JS riêng, không có thư mục "shared" giữa các vai trò).
 */

// Tự nhận diện môi trường qua hostname — không cần build step/bundler
// (ARCHITECTURE.md mục 1: frontend là HTML/JS tĩnh, không qua build).
const API_BASE_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://localhost:8000"
  : "https://nha-xe-khach-backend.onrender.com";

async function apiFetch(duong_dan, tuy_chon = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(tuy_chon.headers || {}),
  };

  const res = await fetch(`${API_BASE_URL}${duong_dan}`, { ...tuy_chon, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.loi || data.detail || "Có lỗi xảy ra, thử lại sau");
  }
  return data;
}

function apiGet(duong_dan) {
  return apiFetch(duong_dan);
}

function apiPost(duong_dan, body) {
  return apiFetch(duong_dan, { method: "POST", body: JSON.stringify(body) });
}

function apiPut(duong_dan, body) {
  return apiFetch(duong_dan, { method: "PUT", body: JSON.stringify(body) });
}

function apiPatch(duong_dan, body) {
  return apiFetch(duong_dan, { method: "PATCH", body: JSON.stringify(body) });
}

function apiDelete(duong_dan) {
  return apiFetch(duong_dan, { method: "DELETE" });
}

// Mã hiển thị tự sinh (KV001, KV001-DT001, T001, LX001, T001-LX001-...) — chỉ để đọc/tra cứu,
// id UUID vẫn là khóa thật. Trả về chuỗi HTML pill; mã rỗng thì hiện gạch ngang.
function htmlMa(ma) {
  return ma ? `<span class="ma-tag">${ma}</span>` : "—";
}
