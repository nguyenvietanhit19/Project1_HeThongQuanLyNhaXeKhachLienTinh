/*
 * Phân công điều độ viên phụ trách tuyến — dùng ở trang Tuyến của Quản lý (DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md mục 3.2).
 * Mỗi thẻ tuyến hiện tên các điều độ viên phụ trách (hoặc nhãn "Chưa có điều độ viên") kèm nút "Phân công" mở hộp tích chọn.
 * API: GET /quan-ly/phan-cong-dieu-do, GET /quan-ly/dieu-do-vien, PUT /quan-ly/phan-cong-dieu-do/{tuyen_id} (thay cả danh sách).
 * Cần nạp SAU api-client.js; CSS ở phan-cong-dieu-do.css cùng thư mục.
 *
 *   await PhanCongDieuDo.tai();                 // trước khi vẽ danh sách tuyến
 *   PhanCongDieuDo.htmlDong(tuyen.id)           // chuỗi HTML chèn vào thẻ tuyến
 *   PhanCongDieuDo.mo(tuyen, khiLuu)            // mở hộp phân công; khiLuu() chạy sau khi lưu thành công (để vẽ lại danh sách)
 */

const PhanCongDieuDo = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ICON_NGUOI = '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c0-4 3.4-6.5 7.5-6.5s7.5 2.5 7.5 6.5"/>';

  let phanCong = new Map(); // tuyen_id -> [{id, ho_ten, email}]
  let dsDieuDoVien = []; // điều độ viên đang hoạt động, kèm so_tuyen
  let daTai = false;
  let overlay = null;

  async function tai() {
    const [cacPhanCong, ds] = await Promise.all([apiGet("/quan-ly/phan-cong-dieu-do"), apiGet("/quan-ly/dieu-do-vien")]);
    phanCong = new Map(cacPhanCong.map((p) => [String(p.tuyen_id), p.dieu_do_vien]));
    dsDieuDoVien = ds;
    daTai = true;
  }

  // Dòng hiển thị trong thẻ tuyến. Chưa tải được dữ liệu thì không hiện gì (tránh báo "chưa có" sai).
  function htmlDong(tuyenId) {
    if (!daTai) return "";
    const ds = phanCong.get(String(tuyenId)) || [];
    if (!ds.length) return '<div class="pc-dong"><span class="pc-canh-bao">Chưa có điều độ viên</span></div>';
    return `<div class="pc-dong"><span class="pc-dong__nhan">Điều độ viên</span>${ds
      .map((d) => `<span class="pc-chip" title="${esc(d.email)}">${esc(d.ho_ten)}</span>`)
      .join("")}</div>`;
  }

  function dungOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.className = "nv-modal-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="nv-modal pc-modal" role="dialog" aria-modal="true" aria-labelledby="pc-tieu-de">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_NGUOI}</svg>
          </div>
          <h2 id="pc-tieu-de">Phân công điều độ viên</h2>
        </div>
        <div class="nv-modal__body" id="pc-noi-dung"></div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) dong();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !overlay.hidden) dong();
    });
    return overlay;
  }

  function dong() {
    if (overlay) overlay.hidden = true;
  }

  function mo(tuyen, khiLuu) {
    const ov = dungOverlay();
    const noiDung = ov.querySelector("#pc-noi-dung");
    const dangPhuTrach = new Set((phanCong.get(String(tuyen.id)) || []).map((d) => String(d.id)));

    noiDung.innerHTML = `
      <div class="pc-tuyen"><strong>${esc(tuyen.ten)}</strong>${typeof htmlMa === "function" ? " " + htmlMa(esc(tuyen.ma)) : ""}</div>
      <div class="pc-ds">${
        dsDieuDoVien.length
          ? dsDieuDoVien
              .map(
                (d) => `
        <label class="pc-muc">
          <input type="checkbox" value="${esc(d.id)}"${dangPhuTrach.has(String(d.id)) ? " checked" : ""} />
          <span class="pc-muc__than">
            <span class="pc-muc__ten">${esc(d.ho_ten)}</span>
            <span class="pc-muc__phu">${esc(d.email)} · đang phụ trách ${d.so_tuyen} tuyến</span>
          </span>
        </label>`
              )
              .join("")
          : '<div class="kv-trong">Chưa có tài khoản điều độ viên nào đang hoạt động.</div>'
      }</div>
      <div class="text-error" id="pc-loi" hidden></div>
      <div class="nv-modal__actions">
        <button type="button" class="nv-btn-secondary" id="pc-huy">Hủy</button>
        <button type="button" class="btn-primary" id="pc-luu">Lưu</button>
      </div>`;
    ov.hidden = false;

    noiDung.querySelector("#pc-huy").addEventListener("click", dong);
    const nutLuu = noiDung.querySelector("#pc-luu");
    nutLuu.addEventListener("click", async () => {
      const loiEl = noiDung.querySelector("#pc-loi");
      loiEl.hidden = true;
      nutLuu.disabled = true;
      try {
        const ids = [...noiDung.querySelectorAll('input[type="checkbox"]:checked')].map((o) => o.value);
        await apiPut(`/quan-ly/phan-cong-dieu-do/${encodeURIComponent(tuyen.id)}`, { nguoi_dung_ids: ids });
        await tai();
        dong();
        if (typeof khiLuu === "function") khiLuu();
      } catch (err) {
        loiEl.textContent = err.message;
        loiEl.hidden = false;
      } finally {
        nutLuu.disabled = false;
      }
    });
  }

  return { tai, htmlDong, mo };
})();
