/*
 * Client gọi API dùng chung cho mọi trang — người 1 xây, xem CONTRIBUTING.md mục 6.
 * Ai cần gọi API chỉ dùng apiGet/apiPost/apiPut, không tự viết lại fetch() + token.
 */

// Suy ra host của backend từ chính host đang xem trang, không hardcode
// "localhost" — "localhost" trên điện thoại thật là chính điện thoại đó,
// không phải máy tính chạy backend, nên phải cùng địa chỉ IP với trang
// frontend đang mở (dev local: cùng máy -> localhost; qua điện thoại
// trong cùng mạng LAN -> đúng IP máy tính, VD 192.168.x.x).
const API_BASE_URL = `http://${window.location.hostname}:8000`;

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
