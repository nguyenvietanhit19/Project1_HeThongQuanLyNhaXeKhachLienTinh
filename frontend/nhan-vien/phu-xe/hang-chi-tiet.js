/*
 * Khung "Chi tiết đơn hàng" cho màn thao tác của phụ xe (chuyen-dang-chay.html): bấm "Xem chi tiết" ở
 * 1 đơn hàng → hiện người gửi/nhận (có nút gọi), lộ trình, loại + cân nặng, cước, lịch sử trạng thái và
 * các báo cáo thất lạc/hư hỏng, kèm đường dẫn sang màn báo thất lạc/hư hỏng.
 *
 *   moChiTietHang(donHangId, chuyenId)
 *
 * Dữ liệu: GET /phu-xe/don-hang/{id}/chi-tiet. CSS: .modal-*, .tk-ho-so*, .info-list, .timeline-list, .badge*.
 */
(function () {
  const NHAN_HANG = {
    cho_van_chuyen: ["Chờ chất", "badge--cho"],
    da_len_xe: ["Đang trên xe", "badge--tren"],
    cho_lay: ["Chờ người nhận lấy", "badge--cho"],
    da_giao: ["Đã giao", "badge--xong"],
    qua_han_luu_kho: ["Hàng tồn", "badge--loi"],
  };

  function esc(giaTri) {
    return String(giaTri ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function gio(iso) {
    return iso ? new Date(iso).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
  }

  function goi(sdt) {
    return sdt ? `<a class="text-link" href="tel:${esc(sdt)}">${esc(sdt)} · Gọi</a>` : "—";
  }

  function badge(trangThai) {
    const [ten, lop] = NHAN_HANG[trangThai] || [trangThai, ""];
    return `<span class="badge ${lop}">${esc(ten)}</span>`;
  }

  let overlay = null;
  let noiDung = null;

  function dung() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="modal-sheet" role="dialog" aria-modal="true">
        <div id="hct-noi-dung"></div>
        <button class="btn-confirm btn-confirm--outline btn-confirm--block" type="button" id="hct-dong">Đóng</button>
      </div>`;
    document.body.appendChild(overlay);
    noiDung = overlay.querySelector("#hct-noi-dung");
    overlay.querySelector("#hct-dong").addEventListener("click", dong);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) dong();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !overlay.hidden) dong();
    });
  }

  function dong() {
    if (overlay) overlay.hidden = true;
  }

  window.moChiTietHang = async function (donHangId, chuyenId) {
    dung();
    noiDung.innerHTML = '<p class="empty-state">Đang tải...</p>';
    overlay.hidden = false;
    try {
      const d = await apiGet(`/phu-xe/don-hang/${encodeURIComponent(donHangId)}/chi-tiet`);
      const lichSu = d.lich_su_trang_thai.length
        ? d.lich_su_trang_thai
            .map((m) => `<li><b>${esc((NHAN_HANG[m.den_trang_thai] || [m.den_trang_thai])[0])}</b>
              <span class="sub">${gio(m.thoi_gian)} · ${esc(m.ten_nguoi_thuc_hien || "Hệ thống tự chuyển")}</span></li>`)
            .join("")
        : '<li class="sub">Chưa có mốc nào.</li>';
      const baoCao = d.bao_cao_su_co.length
        ? d.bao_cao_su_co
            .map((b) => `<li class="bao-cao"><b>⚠ ${b.loai === "that_lac" ? "THẤT LẠC" : "Hư hỏng"}: ${esc(b.mo_ta)}</b>
              <span class="sub">${gio(b.ngay_tao)} · ${esc(b.ten_nguoi_bao_cao || "")}</span></li>`)
            .join("")
        : '<li class="sub">Chưa có báo cáo thất lạc/hư hỏng.</li>';
      const lienKetBao = chuyenId
        ? `&chuyen_id=${encodeURIComponent(chuyenId)}`
        : "";
      noiDung.innerHTML = `
        <div class="tk-ho-so__dau">
          <div><h2>${esc(d.ma_van_don)}</h2>${badge(d.trang_thai)}</div>
        </div>
        <dl class="info-list">
          <dt>Người gửi</dt><dd>${esc(d.ten_nguoi_gui)}<br>${goi(d.sdt_nguoi_gui)}</dd>
          <dt>Người nhận</dt><dd>${esc(d.ten_nguoi_nhan)}<br>${goi(d.sdt_nguoi_nhan)}</dd>
          <dt>Lộ trình</dt><dd>${esc(d.ten_diem_gui)} → ${esc(d.ten_diem_nhan)}</dd>
          <dt>Hàng</dt><dd>${esc(d.ten_loai_hang || "—")} · ${esc(d.can_nang_kg)}kg</dd>
          <dt>Cước</dt><dd>${Number(d.gia_cuoc || 0).toLocaleString("vi-VN")}đ · ${d.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra" ? "người nhận trả (COD)" : "người gửi đã trả"}</dd>
          ${d.thoi_gian_den_diem_nhan ? `<dt>Dỡ xuống lúc</dt><dd>${gio(d.thoi_gian_den_diem_nhan)}</dd>` : ""}
        </dl>
        <h3 class="muc-nho">Lịch sử trạng thái</h3>
        <ul class="timeline-list">${lichSu}</ul>
        <h3 class="muc-nho">Báo cáo thất lạc / hư hỏng</h3>
        <ul class="timeline-list">${baoCao}</ul>
        <a class="btn-confirm btn-confirm--block" style="display:flex;align-items:center;justify-content:center;text-decoration:none;"
           href="bao-that-lac.html?don_hang_id=${encodeURIComponent(d.id)}&ma_van_don=${encodeURIComponent(d.ma_van_don)}${lienKetBao}">Báo thất lạc / hư hỏng đơn này</a>`;
    } catch (err) {
      noiDung.innerHTML = `<p class="text-error">${esc(err.message)}</p>`;
    }
  };
})();
