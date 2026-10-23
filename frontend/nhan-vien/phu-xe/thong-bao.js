/*
 * Hộp thoại thông báo / xác nhận ở GIỮA màn hình, thay window.alert() và window.confirm().
 *
 *   thongBao.hien("Nội dung")                         → thông báo 1 nút "Đã hiểu" (tự đoán loại theo nội dung)
 *   thongBao.hien("Lỗi...", { loai: "loi", tieuDe })  → loai: loi | thanh-cong | canh-bao | thong-tin
 *   await thongBao.xacNhan({ noiDung, tieuDe, nhan, loai: "thuong" | "nguy-hiem" | "canh-bao" })  → true / false
 *
 * Luôn trả Promise (hien cũng vậy, resolve khi đóng) nên dùng được với await.
 * Xếp hàng: gọi nhiều lần liên tiếp thì hiện lần lượt, không chồng lên nhau.
 * CSS: .tb-* trong phu-xe.css.
 */
(function () {
  const ICON = { loi: "!", "thanh-cong": "✓", "canh-bao": "!", "thong-tin": "i", thuong: "?", "nguy-hiem": "!" };
  const TIEU_DE = { loi: "Có lỗi xảy ra", "thanh-cong": "Thành công", "canh-bao": "Lưu ý", "thong-tin": "Thông báo", thuong: "Xác nhận", "nguy-hiem": "Xác nhận" };
  const MAU = { loi: "loi", "thanh-cong": "ok", "canh-bao": "canh-bao", "thong-tin": "tin", thuong: "tin", "nguy-hiem": "loi" };

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Không truyền loại → đoán từ nội dung. Mặc định là thông tin trung tính: KHÔNG mặc định "lỗi" vì thông báo
  // thành công từ server ("Xe bắt đầu di chuyển tới...") cũng chỉ là một chuỗi. Nơi bắt lỗi phải truyền loai: "loi".
  function doanLoai(nd) {
    const s = String(nd || "");
    if (/không xử lý được|không thể|thất bại/i.test(s)) return "canh-bao";
    if (/^\s*✓|^\s*(Đã|Xong|Xe bắt đầu|Xe đã)\b/.test(s)) return "thanh-cong";
    return "thong-tin";
  }

  let hangDoi = Promise.resolve();
  let dangMo = null;   // { dong(giaTri) } của hộp đang hiện — Esc / bấm nền dùng

  function mo({ loai, tieuDe, noiDung, nhanXacNhan, nhanHuy }) {
    return new Promise((xong) => {
      const mau = MAU[loai] || "tin";
      // Hộp cảnh báo / xác nhận nguy hiểm có tiếng "cảnh báo" (lỗi API và thành công đã có tiếng riêng ở phu-xe-pro.js nên không phát lại ở đây)
      if ((loai === "canh-bao" || loai === "nguy-hiem") && window.phuXe && window.phuXe.am) window.phuXe.am("canhBao");
      const ov = document.createElement("div");
      ov.className = "tb-overlay";
      ov.innerHTML = `
        <div class="tb-hop tb-hop--${mau}" role="${nhanHuy ? "alertdialog" : "alert"}" aria-modal="true" aria-labelledby="tb-tieu" aria-describedby="tb-nd">
          <div class="tb-icon" aria-hidden="true">${ICON[loai] || "i"}</div>
          <h2 class="tb-tieu" id="tb-tieu">${esc(tieuDe)}</h2>
          <div class="tb-nd" id="tb-nd">${String(noiDung ?? "").split("\n").map(esc).join("<br>")}</div>
          <div class="tb-nut">
            ${nhanHuy ? `<button type="button" class="btn-confirm btn-confirm--outline" data-tb="huy">${esc(nhanHuy)}</button>` : ""}
            <button type="button" class="${loai === "nguy-hiem" || loai === "loi" ? "btn-primary tb-nut--do" : "btn-primary"}" data-tb="ok">${esc(nhanXacNhan)}</button>
          </div>
        </div>`;
      const truoc = document.activeElement;
      const dong = (giaTri) => {
        document.removeEventListener("keydown", phim, true);
        ov.classList.add("dang-dong");
        setTimeout(() => ov.remove(), 170);
        dangMo = null;
        if (truoc && truoc.focus && document.body.contains(truoc)) truoc.focus();
        xong(giaTri);
      };
      const phim = (e) => {
        if (e.key === "Escape") { e.preventDefault(); dong(false); }
        else if (e.key === "Tab") {   // giữ focus trong hộp
          const nut = [...ov.querySelectorAll("button")];
          const i = nut.indexOf(document.activeElement);
          e.preventDefault();
          nut[(i + (e.shiftKey ? nut.length - 1 : 1)) % nut.length].focus();
        }
      };
      ov.addEventListener("click", (e) => {
        const t = e.target.closest("[data-tb]");
        if (t) dong(t.dataset.tb === "ok");
        else if (e.target === ov) dong(false);
      });
      document.addEventListener("keydown", phim, true);
      document.body.appendChild(ov);
      dangMo = { dong };
      // Hộp hỏi nguy hiểm: focus vào "Hủy" để Enter lỡ tay không xác nhận; còn lại focus nút chính
      (ov.querySelector(loai === "nguy-hiem" ? '[data-tb="huy"]' : '[data-tb="ok"]') || ov.querySelector("button")).focus();
    });
  }

  function xepHang(tuyChon) {
    const p = hangDoi.then(() => mo(tuyChon));
    hangDoi = p.catch(() => {});
    return p;
  }

  window.thongBao = {
    hien(noiDung, tuyChon = {}) {
      const loai = tuyChon.loai || doanLoai(noiDung);
      return xepHang({ loai, noiDung, tieuDe: tuyChon.tieuDe || TIEU_DE[loai], nhanXacNhan: tuyChon.nhan || "Đã hiểu" });
    },
    xacNhan({ noiDung, tieuDe, nhan = "Xác nhận", nhanHuy = "Hủy", loai = "thuong" } = {}) {
      return xepHang({ loai, noiDung, tieuDe: tieuDe || TIEU_DE[loai], nhanXacNhan: nhan, nhanHuy });
    },
  };

  // ---------- Số điện thoại: nút "Sao chép" thay cho liên kết gọi (phụ xe hay dùng máy bàn/điện thoại khác để gọi) ----------
  //   innerHTML = `... ${sdtSaoChep(v.so_dien_thoai)} ...`   — 1 trình nghe chung xử lý mọi nút, không cần gắn lại sau khi render
  window.sdtSaoChep = function (sdt) {
    if (!sdt) return "—";
    const so = esc(sdt);
    return `<span class="sdt-chep"><span class="sdt-chep__so">${so}</span><button type="button" class="sdt-chep__nut" data-sao-chep="${so}" aria-label="Sao chép số ${so}">Sao chép</button></span>`;
  };

  async function saoChep(chu) {
    try {
      await navigator.clipboard.writeText(chu);
    } catch (_) {   // http thường / trình duyệt cũ không có clipboard API → dùng cách cũ
      const o = document.createElement("textarea");
      o.value = chu;
      o.style.cssText = "position:fixed;opacity:0;";
      document.body.appendChild(o);
      o.select();
      const xong = document.execCommand("copy");
      o.remove();
      if (!xong) throw new Error("Không sao chép được");
    }
  }

  document.addEventListener("click", async (e) => {
    const nut = e.target.closest("[data-sao-chep]");
    if (!nut) return;
    e.preventDefault();
    e.stopPropagation();   // nút nằm trong ô/khung bấm được (vd. dòng khách) — không kích hoạt thao tác của khung
    const goc = nut.dataset.goc || nut.textContent;
    nut.dataset.goc = goc;
    clearTimeout(nut._hen);
    try {
      await saoChep(nut.dataset.saoChep);
      nut.textContent = "✓ Đã chép";
      nut.classList.add("is-xong");
    } catch (_) {
      nut.textContent = "Không chép được";
    }
    nut._hen = setTimeout(() => { nut.textContent = goc; nut.classList.remove("is-xong"); }, 1600);
  }, true);
})();
