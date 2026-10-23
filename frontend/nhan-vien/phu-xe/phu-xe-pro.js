/*
 * Tiện ích "pro" cho giao diện phụ xe — nạp SAU /shared/api-client.js, TRƯỚC tai-khoan-menu.js.
 *
 *  1. Gọi API bền hơn: GET tự thử lại khi rớt mạng, phân loại lỗi (mất mạng / hết phiên / lỗi máy chủ) thay vì
 *     một câu "Đã có lỗi hệ thống". Ghi đè apiFetch của api-client.js CHỈ trên các trang phụ xe (không đụng file dùng chung).
 *  2. Phản hồi khi bấm: rung nhẹ khi thao tác ghi thành công / thất bại; âm "bíp" (tùy chọn, mặc định tắt).
 *  3. Banner "Mất kết nối" + tự tải lại dữ liệu khi có mạng trở lại.
 *  4. Snackbar "Hoàn tác" ngay sau thao tác nhầm tay (phuXe.hoanTac).
 *  5. Nút đổi Giao diện (Tự động/Sáng/Tối) và Âm báo trong menu ☰.
 *  6. Gỡ khung xương (skeleton) khi trang đã có dữ liệu.
 * CSS: phu-xe-pro.css.
 */
(function () {
  "use strict";

  const LS = {
    lay(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
    dat(k, v) { try { localStorage.setItem(k, v); } catch (_) {} },
  };
  const cho = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- 2. Rung + âm báo ----------
  const KHOA_AM = "phu_xe_am_bao";
  let ctxAm = null;
  function bip(tanSo, ms) {
    if (LS.lay(KHOA_AM) !== "bat") return;
    try {
      ctxAm = ctxAm || new (window.AudioContext || window.webkitAudioContext)();
      const dao = ctxAm.createOscillator(), vol = ctxAm.createGain();
      dao.frequency.value = tanSo;
      vol.gain.value = 0.06;
      dao.connect(vol); vol.connect(ctxAm.destination);
      dao.start(); dao.stop(ctxAm.currentTime + ms / 1000);
    } catch (_) {}
  }
  const phanHoi = {
    thanhCong() { try { navigator.vibrate && navigator.vibrate(18); } catch (_) {} bip(880, 90); },
    loi() { try { navigator.vibrate && navigator.vibrate([40, 70, 40]); } catch (_) {} bip(240, 220); },
  };

  // ---------- 3. Mất kết nối ----------
  let banner = null, henAn = null, dangMat = false;
  function hienBanner(noiDung, loai) {
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "px-mang";
      banner.setAttribute("role", "status");
      banner.setAttribute("aria-live", "polite");
      document.body.appendChild(banner);
    }
    clearTimeout(henAn);
    banner.className = `px-mang px-mang--${loai}`;
    banner.textContent = noiDung;
    banner.hidden = false;
  }
  function batMang(coMang) {
    if (coMang && dangMat) {
      dangMat = false;
      hienBanner("Đã kết nối lại — đang làm mới dữ liệu…", "ok");
      henAn = setTimeout(() => { banner.hidden = true; }, 2500);
      for (const ten of ["taiDuLieu", "taiDanhSach", "taiThongKe"]) {
        if (typeof window[ten] === "function") { try { Promise.resolve(window[ten]()).catch(() => {}); } catch (_) {} break; }
      }
    } else if (!coMang && !dangMat) {
      dangMat = true;
      hienBanner("Mất kết nối mạng — dữ liệu có thể chưa mới nhất.", "mat");
    }
  }
  window.addEventListener("offline", () => batMang(false));
  window.addEventListener("online", () => batMang(true));

  // ---------- 1. apiFetch bền hơn ----------
  function thongDiepLoi(status, data) {
    const goc = data && (data.loi || (typeof data.detail === "string" ? data.detail : ""));
    if (status === 401) return "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.";
    if (status === 422) return goc || "Dữ liệu gửi lên không hợp lệ.";
    if (status >= 500) return `Máy chủ đang gặp sự cố (mã ${status}). Thử lại sau ít phút; nếu còn lỗi hãy báo điều độ viên.`;
    return goc || "Có lỗi xảy ra, thử lại sau";
  }

  if (typeof window.apiFetch === "function" && typeof API_BASE_URL !== "undefined") {
    window.apiFetch = async function apiFetch(duongDan, tuyChon = {}) {
      const phuongThuc = String(tuyChon.method || "GET").toUpperCase();
      const token = LS.lay("token");
      const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(tuyChon.headers || {}),
      };
      const soLanThu = phuongThuc === "GET" ? 3 : 1;   // chỉ GET mới thử lại: POST gửi lại có thể ghi trùng
      for (let lan = 1; lan <= soLanThu; lan++) {
        let res;
        try {
          res = await fetch(`${API_BASE_URL}${duongDan}`, { ...tuyChon, headers });
        } catch (_) {
          if (lan < soLanThu) { await cho(500 * lan); continue; }
          batMang(false);
          if (phuongThuc !== "GET") phanHoi.loi();
          const e = new Error(phuongThuc === "GET"
            ? "Mất kết nối mạng. Kiểm tra sóng / Wi-Fi rồi bấm tải lại."
            : "Mất kết nối khi gửi thao tác. Hãy tải lại để kiểm tra thao tác đã được ghi nhận chưa trước khi bấm lại.");
          e.mang = true;
          throw e;
        }
        batMang(true);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (res.status >= 502 && res.status <= 504 && lan < soLanThu) { await cho(500 * lan); continue; }
          if (phuongThuc !== "GET") phanHoi.loi();
          const e = new Error(thongDiepLoi(res.status, data));
          e.status = res.status;
          throw e;
        }
        if (phuongThuc !== "GET") phanHoi.thanhCong();
        return data;
      }
    };
  }

  // ---------- 4. Snackbar "Hoàn tác" ----------
  let snack = null, henSnack = null;
  function hoanTac(noiDung, thucHien, ms = 7000) {
    if (!snack) {
      snack = document.createElement("div");
      snack.className = "px-snack";
      snack.setAttribute("role", "status");
      snack.setAttribute("aria-live", "polite");
      document.body.appendChild(snack);
    }
    clearTimeout(henSnack);
    snack.innerHTML = `<span class="px-snack__nd">${esc(noiDung)}</span><button type="button" class="px-snack__nut">Hoàn tác</button><span class="px-snack__dem" style="animation-duration:${ms}ms"></span>`;
    snack.hidden = false;
    const an = () => { snack.hidden = true; };
    snack.querySelector(".px-snack__nut").onclick = () => { clearTimeout(henSnack); an(); thucHien(); };
    henSnack = setTimeout(an, ms);
  }

  // ---------- Ngày giờ: LUÔN dd/MM/yyyy HH:mm (tự ghép, không nhờ toLocaleString vì mỗi trình duyệt in một kiểu: "22-10", "10/22"...) ----------
  const hai = (n) => String(n).padStart(2, "0");
  const ngay = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : `${hai(d.getDate())}/${hai(d.getMonth() + 1)}/${d.getFullYear()}`; };
  const gio = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : `${hai(d.getHours())}:${hai(d.getMinutes())}`; };
  const ngayGio = (iso) => { const n = ngay(iso); return n ? `${n} ${gio(iso)}` : ""; };

  window.phuXe = { hoanTac, phanHoi, rung: phanHoi.thanhCong, ngay, gio, ngayGio };

  // ---------- 5. Nút trong menu ☰ ----------
  const TEN_GD = { auto: "Tự động", sang: "Sáng", toi: "Tối" };
  function capNhatNhan() {
    const gd = document.getElementById("px-giao-dien-gt");
    if (gd && window.phuXeGiaoDien) gd.textContent = TEN_GD[window.phuXeGiaoDien.lay()];
    const am = document.getElementById("px-am-bao-gt");
    if (am) am.textContent = LS.lay(KHOA_AM) === "bat" ? "Bật" : "Tắt";
  }
  document.addEventListener("click", (e) => {
    const nut = e.target.closest("[data-px]");
    if (!nut) return;
    e.stopPropagation();
    if (nut.dataset.px === "giao-dien" && window.phuXeGiaoDien) {
      const thuTu = ["auto", "sang", "toi"];
      window.phuXeGiaoDien.dat(thuTu[(thuTu.indexOf(window.phuXeGiaoDien.lay()) + 1) % 3]);
    } else if (nut.dataset.px === "am-bao") {
      const bat = LS.lay(KHOA_AM) !== "bat";
      LS.dat(KHOA_AM, bat ? "bat" : "tat");
      if (bat) { bip(880, 90); try { navigator.vibrate && navigator.vibrate(18); } catch (_) {} }
    }
    capNhatNhan();
  }, true);
  document.addEventListener("DOMContentLoaded", capNhatNhan);

  // ---------- 6. Gỡ khung xương ----------
  document.addEventListener("DOMContentLoaded", () => {
    const sk = document.getElementById("sk-tai");
    if (!sk) return;
    const go = () => { sk.remove(); };
    const tieuDe = document.getElementById("tieu-de-tuyen");
    if (tieuDe) {
      const bd = tieuDe.textContent;
      new MutationObserver((_, ob) => { if (tieuDe.textContent !== bd) { ob.disconnect(); go(); } })
        .observe(tieuDe, { childList: true, characterData: true, subtree: true });
    }
    setTimeout(go, 15000);   // chốt an toàn: dù lỗi gì cũng không để khung xương treo mãi
  });
})();
