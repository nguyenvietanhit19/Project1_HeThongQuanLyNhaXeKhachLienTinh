/*
 * Tiện ích "pro" cho giao diện phụ xe — nạp SAU /shared/api-client.js, TRƯỚC tai-khoan-menu.js.
 *
 *  1. Gọi API bền hơn: GET tự thử lại khi rớt mạng, phân loại lỗi (mất mạng / hết phiên / lỗi máy chủ) thay vì
 *     một câu "Đã có lỗi hệ thống". Ghi đè apiFetch của api-client.js CHỈ trên các trang phụ xe (không đụng file dùng chung).
 *  2. Phản hồi khi bấm: rung nhẹ khi thao tác ghi thành công / thất bại; âm "bíp" (tùy chọn, mặc định tắt).
 *  3. Banner "Mất kết nối" + tự tải lại dữ liệu khi có mạng trở lại.
 *  5. (đã chuyển) Cài đặt Giao diện / Âm báo / Hồ sơ → phu-xe-cai-dat.js.
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

  // ---------- 2. Âm thanh + rung (cài đặt trong menu ☰ → Cài đặt → Âm báo) ----------
  // 5 kiểu âm, mỗi kiểu một giai điệu riêng để nghe là biết không cần nhìn màn hình (phụ xe hay vừa làm vừa nhìn đường):
  //   thanhCong (2 nốt đi lên) · loi (trầm, rè) · canhBao (2 tiếng đều) · hoanTac (2 nốt đi xuống) · nhacNho (chuông 3 nốt: bến mở, tới giờ chạy)
  const K_BAT = "phu_xe_am_bao", K_LUONG = "phu_xe_am_luong", K_RUNG = "phu_xe_rung";
  const AM = {
    bat: () => LS.lay(K_BAT) !== "tat",                     // mặc định BẬT
    luong: () => { const n = parseInt(LS.lay(K_LUONG), 10); return Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : 70; },
    rung: () => LS.lay(K_RUNG) !== "tat",                   // mặc định BẬT
  };
  const GIAI_DIEU = {
    thanhCong: [{ f: 660, t: 0, d: 0.09 }, { f: 880, t: 0.1, d: 0.16 }],
    loi: [{ f: 220, t: 0, d: 0.18, w: "sawtooth" }, { f: 165, t: 0.22, d: 0.26, w: "sawtooth" }],
    canhBao: [{ f: 523, t: 0, d: 0.13, w: "triangle" }, { f: 523, t: 0.2, d: 0.13, w: "triangle" }],
    hoanTac: [{ f: 740, t: 0, d: 0.09 }, { f: 554, t: 0.1, d: 0.16 }],
    nhacNho: [{ f: 784, t: 0, d: 0.13 }, { f: 988, t: 0.15, d: 0.13 }, { f: 1175, t: 0.3, d: 0.26 }],
  };
  const KIEU_RUNG = { thanhCong: [18], loi: [40, 70, 40], canhBao: [30, 50, 30], hoanTac: [14], nhacNho: [60, 40, 60, 40, 120] };

  let ctxAm = null;
  function layCtx() {
    try {
      ctxAm = ctxAm || new (window.AudioContext || window.webkitAudioContext)();
      if (ctxAm.state === "suspended") ctxAm.resume();
      return ctxAm;
    } catch (_) { return null; }
  }
  // Trình duyệt chỉ cho phát âm sau khi người dùng đã chạm vào trang → "mở khóa" ở lần chạm đầu tiên
  ["pointerdown", "keydown"].forEach((ev) => document.addEventListener(ev, () => layCtx(), { once: true, capture: true }));

  function phatAm(kieu, ep) {
    if (!ep && !AM.bat()) return;
    const luong = AM.luong();
    if (!luong) return;
    const c = layCtx();
    if (!c) return;
    const dinh = (luong / 100) * 0.32;   // gain tối đa 0.32 — đủ to trên loa điện thoại mà không chói
    for (const n of GIAI_DIEU[kieu] || []) {
      const dao = c.createOscillator(), vol = c.createGain();
      const bd = c.currentTime + n.t;
      dao.type = n.w || "sine";
      dao.frequency.value = n.f;
      vol.gain.setValueAtTime(0.0001, bd);
      vol.gain.exponentialRampToValueAtTime(dinh, bd + 0.012);
      vol.gain.exponentialRampToValueAtTime(0.0001, bd + n.d);
      dao.connect(vol); vol.connect(c.destination);
      dao.start(bd); dao.stop(bd + n.d + 0.03);
    }
  }
  function rungMay(kieu, ep) {
    if (!ep && !AM.rung()) return;
    try { navigator.vibrate && navigator.vibrate(KIEU_RUNG[kieu] || [18]); } catch (_) {}
  }
  // Một lệnh cho cả hai: phanHoi.bao("thanhCong")
  const phanHoi = {
    bao(kieu) { rungMay(kieu); phatAm(kieu); },
    thanhCong() { phanHoi.bao("thanhCong"); },
    loi() { phanHoi.bao("loi"); },
  };
  const amThanh = {
    lay: () => ({ bat: AM.bat(), luong: AM.luong(), rung: AM.rung() }),
    dat({ bat, luong, rung }) {
      if (bat !== undefined) LS.dat(K_BAT, bat ? "bat" : "tat");
      if (luong !== undefined) LS.dat(K_LUONG, String(Math.round(luong)));
      if (rung !== undefined) LS.dat(K_RUNG, rung ? "bat" : "tat");
    },
    thu(kieu) { rungMay(kieu, true); phatAm(kieu, true); },   // nghe thử: phát dù đang tắt âm báo (để biết nó kêu thế nào)
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

  // ---------- Ngày giờ: LUÔN dd/MM/yyyy HH:mm (tự ghép, không nhờ toLocaleString vì mỗi trình duyệt in một kiểu: "22-10", "10/22"...) ----------
  const hai = (n) => String(n).padStart(2, "0");
  const ngay = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : `${hai(d.getDate())}/${hai(d.getMonth() + 1)}/${d.getFullYear()}`; };
  const gio = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : `${hai(d.getHours())}:${hai(d.getMinutes())}`; };
  const ngayGio = (iso) => { const n = ngay(iso); return n ? `${n} ${gio(iso)}` : ""; };

  window.phuXe = { phanHoi, rung: phanHoi.thanhCong, am: phanHoi.bao, amThanh, ngay, gio, ngayGio };

  // ---------- 6. Gỡ khung xương ----------
  document.addEventListener("DOMContentLoaded", () => {
    const sk = document.getElementById("sk-tai");
    if (!sk) return;
    const go = () => { sk.remove(); };
    const tieuDe = document.getElementById("tieu-de-tuyen");
    if (tieuDe && tieuDe.textContent.trim() !== "Đang tải...") { go(); return; }   // dữ liệu về trước khi DOM sẵn sàng
    if (tieuDe) {
      const bd = tieuDe.textContent;
      new MutationObserver((_, ob) => { if (tieuDe.textContent !== bd) { ob.disconnect(); go(); } })
        .observe(tieuDe, { childList: true, characterData: true, subtree: true });
    }
    setTimeout(go, 15000);   // chốt an toàn: dù lỗi gì cũng không để khung xương treo mãi
  });
})();
