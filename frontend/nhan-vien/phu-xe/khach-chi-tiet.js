/*
 * Khung "Chi tiết hành khách" dùng chung cho màn thao tác (chuyen-dang-chay.html) và màn tổng quan
 * chuyến (chi-tiet-chuyen.html): bấm tên một khách → hiện SĐT (có nút gọi), ghế, mã đặt chỗ,
 * điểm đón/trả, giờ lên/xuống, giá vé; nếu truyền `hanhDong` thì có thêm nút xác nhận lên/xuống xe.
 *
 *   moChiTietKhach(khach, { hanhDong: { nhan: "Xác nhận lên xe", chay: () => Promise } })
 *
 * `khach` là 1 phần tử của `hanh_khach` trong GET /phu-xe/chuyen/{id}/tong-quan.
 * CSS: .modal-*, .tk-ho-so*, .info-list, .badge* trong phu-xe.css.
 */
(function () {
  const NHAN_KHACH = {
    da_thanh_toan: ["Chờ lên xe", "badge--cho"],
    giu_cho: ["Chờ lên · chưa trả tiền", "badge--cho"],
    da_len_xe: ["Đang trên xe", "badge--tren"],
    da_xuong_xe: ["Đã xuống xe", "badge--xong"],
    khong_den: ["Không đến", "badge--loi"],
  };

  function esc(giaTri) {
    return String(giaTri ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function gio(iso) {
    return iso ? window.phuXe.ngayGio(iso) : "—";
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
        <div id="kct-noi-dung"></div>
        <button class="btn-confirm btn-confirm--outline btn-confirm--block" type="button" id="kct-dong">Đóng</button>
      </div>`;
    document.body.appendChild(overlay);
    noiDung = overlay.querySelector("#kct-noi-dung");
    overlay.querySelector("#kct-dong").addEventListener("click", dong);
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

  window.moChiTietKhach = function (v, tuyChon = {}) {
    dung();
    const [tenTrangThai, lopTrangThai] = NHAN_KHACH[v.trang_thai] || [v.trang_thai, ""];
    const sdt = window.sdtSaoChep(v.so_dien_thoai);
    // Nhiều ghế trong cùng 1 lượt đặt = nhiều vé cùng ma_dat_cho (1 vé = 1 ghế)
    const cungDat = (tuyChon.tatCaKhach || []).filter((k) => k.ma_dat_cho === v.ma_dat_cho)
      .sort((a, b) => String(a.so_ghe).localeCompare(String(b.so_ghe), "vi", { numeric: true }));
    const thanhToan =v.loai_hinh_thanh_toan === "thanh_toan_tai_quay" ? "thanh toán tại quầy" : "đã thanh toán online";
    noiDung.innerHTML = `
      <div class="tk-ho-so__dau">
        <div class="tk-ho-so__avatar">${esc(v.so_ghe)}</div>
        <div><h2>${esc(v.ho_ten)}</h2><span class="badge ${lopTrangThai}">${esc(tenTrangThai)}</span></div>
      </div>
      <dl class="info-list">
        <dt>Số điện thoại</dt><dd>${sdt}</dd>
        <dt>Số ghế</dt><dd><b>${esc(v.so_ghe)}</b></dd>
        <dt>Mã đặt chỗ</dt><dd>${esc(v.ma_dat_cho)}</dd>
        ${cungDat.length > 1 ? `<dt>Cùng đặt chỗ</dt><dd>${cungDat.length} ghế: ${cungDat.map((k) => {
          const [ten] = NHAN_KHACH[k.trang_thai] || [k.trang_thai];
          return `<span${k.ve_id === v.ve_id ? ' style="font-weight:700"' : ""}>${esc(k.so_ghe)} (${esc(ten)})</span>`;
        }).join(", ")}</dd>` : ""}
        <dt>Điểm đón</dt><dd>${esc(v.ten_diem_don)}</dd>
        <dt>Điểm trả</dt><dd>${esc(v.ten_diem_tra)}</dd>
        <dt>Lên xe lúc</dt><dd>${gio(v.gio_len_xe)}</dd>
        <dt>Xuống xe lúc</dt><dd>${gio(v.gio_xuong_xe)}</dd>
        <dt>Giá vé</dt><dd>${Number(v.gia || 0).toLocaleString("vi-VN")}đ<br>${thanhToan}</dd>
      </dl>
      ${tuyChon.ghiChu ? `<p class="hint">${esc(tuyChon.ghiChu)}</p>` : ""}
      ${tuyChon.hanhDong ? `<button class="btn-primary" type="button" id="kct-hanh-dong" style="margin-bottom:8px;">${esc(tuyChon.hanhDong.nhan)}</button>` : ""}`;

    if (tuyChon.hanhDong) {
      const nut = noiDung.querySelector("#kct-hanh-dong");
      nut.addEventListener("click", async () => {
        // hỏi lại trước khi thao tác (hộp thoại giữa màn hình nếu trang đã nạp thong-bao.js)
        if (tuyChon.hanhDong.hoi) {
          const dongY = window.thongBao
            ? await window.thongBao.xacNhan({ tieuDe: "Xác nhận", noiDung: tuyChon.hanhDong.hoi, nhan: tuyChon.hanhDong.nhan })
            : window.confirm(tuyChon.hanhDong.hoi);
          if (!dongY) return;
        }
        nut.disabled = true;
        try {
          await tuyChon.hanhDong.chay();
          dong();
        } catch (err) {
          nut.disabled = false;
          nut.insertAdjacentHTML("beforebegin", `<div class="text-error">${esc(err.message)}</div>`);
        }
      });
    }
    overlay.hidden = false;
  };
})();
