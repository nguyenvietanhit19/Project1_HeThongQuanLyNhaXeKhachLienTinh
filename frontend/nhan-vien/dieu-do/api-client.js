/*
 * Client gọi API cho các trang Điều độ viên — riêng domain dieu-do,
 * không dùng chung với quan-ly/ hay domain khác (CONTRIBUTING.md mục 5.5).
 */

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

const apiGet  = (d)    => apiFetch(d);
const apiPost = (d, b) => apiFetch(d, { method: "POST",   body: JSON.stringify(b) });
const apiPut  = (d, b) => apiFetch(d, { method: "PUT",    body: JSON.stringify(b) });
const apiDel  = (d)    => apiFetch(d, { method: "DELETE" });
