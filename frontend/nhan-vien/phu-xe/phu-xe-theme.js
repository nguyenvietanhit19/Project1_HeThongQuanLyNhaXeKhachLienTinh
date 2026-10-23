/*
 * Áp giao diện Sáng / Tối / Tự động cho trang phụ xe — nạp ở <head> (trước khi vẽ) để không bị nháy nền sáng.
 * Lưu lựa chọn ở localStorage "phu_xe_giao_dien" (auto | sang | toi); không lưu được thì dùng Tự động.
 * CSS: phu-xe-pro.css (khối "Chế độ tối"). Nút đổi nằm trong menu ☰ (tai-khoan-menu.js).
 */
(function () {
  const KHOA = "phu_xe_giao_dien";
  let luaChon = "auto";
  try {
    const v = localStorage.getItem(KHOA);
    if (v === "sang" || v === "toi") luaChon = v;
  } catch (_) {}

  function ap(chon) {
    const goc = document.documentElement;
    if (chon === "sang") goc.setAttribute("data-theme", "light");
    else if (chon === "toi") goc.setAttribute("data-theme", "dark");
    else goc.removeAttribute("data-theme");
    const toi = chon === "toi" || (chon === "auto" && window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
    let meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "theme-color";
      document.head.appendChild(meta);
    }
    meta.content = toi ? "#0E0E14" : "#5B3E96";
  }

  window.phuXeGiaoDien = {
    lay: () => luaChon,
    dat(chon) {
      luaChon = chon === "sang" || chon === "toi" ? chon : "auto";
      try { localStorage.setItem(KHOA, luaChon); } catch (_) {}
      ap(luaChon);
    },
  };
  ap(luaChon);
  if (window.matchMedia) {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const doi = () => { if (luaChon === "auto") ap("auto"); };
    mq.addEventListener ? mq.addEventListener("change", doi) : mq.addListener && mq.addListener(doi);
  }
})();
