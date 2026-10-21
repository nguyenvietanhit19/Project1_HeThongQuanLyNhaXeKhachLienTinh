/*
 * Client gọi API cho các trang Quản lý nhân sự — riêng của domain này
 * (UC-49/51/52), không dùng chung với frontend/khach-hang/ hay các vai trò
 * nhân viên khác (mỗi vai trò tự viết CSS/JS riêng, không có thư mục
 * "shared" giữa các vai trò — xem frontend/nhan-vien/quan-ly/api-client.js,
 * file này cùng nội dung, nhân bản riêng cho đúng domain).
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

function apiGet(duong_dan) {
  return apiFetch(duong_dan);
}

function apiPost(duong_dan, body) {
  return apiFetch(duong_dan, { method: "POST", body: JSON.stringify(body) });
}

function apiPut(duong_dan, body) {
  return apiFetch(duong_dan, { method: "PUT", body: JSON.stringify(body) });
}

// Upload ảnh (multipart) — dùng cho /ho-so/{id}/anh và /ho-so/{id}/giay-to/{loai}/anh.
// Không set Content-Type thủ công: trình duyệt tự thêm boundary đúng cho multipart/form-data.
async function apiUploadAnh(duong_dan, file) {
  const token = localStorage.getItem("token");
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}${duong_dan}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.loi || data.detail || "Không tải ảnh lên được, thử lại sau");
  }
  return data;
}
