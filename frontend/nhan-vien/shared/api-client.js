/*
 * Client gọi API dùng chung cho mọi trang nhân viên — người 1 xây, xem
 * CONTRIBUTING.md mục 6. Bản riêng cho frontend/nhan-vien/ (khác bản ở
 * frontend/shared/ dùng cho khách hàng) — logic giống hệt nhau, tách vì
 * 2 domain phục vụ 2 nhóm trang khác nhau (mục 30 CONTRIBUTING.md).
 */

const API_BASE_URL = "http://localhost:8000";

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
