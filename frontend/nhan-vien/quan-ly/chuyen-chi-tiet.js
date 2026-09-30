/*
 * Modal "Chi tiết chuyến" dùng chung cho trang Chuyến và trang Lịch chạy — xem
 * lộ trình + mốc thời gian, sửa giờ, xóa (chỉ chuyến chưa gán xe/chưa khởi hành/
 * chưa có vé). Cần api-client.js (apiGet/apiPut/apiDelete/htmlMa) nạp trước.
 *
 *   ChuyenChiTiet.mo(chuyenId, { onThayDoi })
 *   - onThayDoi(): gọi sau khi chuyến bị sửa giờ hoặc xóa, để trang gọi tải lại dữ liệu
 *
 * Modal tự dựng vào <body> ở lần mở đầu tiên và luôn được đưa xuống cuối body
 * mỗi lần mở, nên hiện đè lên modal khác đang mở (VD lịch các ngày đã sinh chuyến).
 */
const ChuyenChiTiet = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");

  const NHAN_TRANG_THAI = {
    chua_khoi_hanh: "Chưa khởi hành",
    dang_chay: "Đang chạy",
    gap_su_co: "Gặp sự cố",
    hoan_thanh: "Hoàn thành",
    da_huy: "Đã hủy",
  };

  function pillTrangThai(trangThai) {
    if (trangThai === "chua_khoi_hanh") return "pill--gia-vinh-vien";
    if (trangThai === "dang_chay") return "pill--gia-thoi-han";
    if (trangThai === "gap_su_co") return "pill--do";
    return "pill--xam"; // hoan_thanh, da_huy
  }

  function mauTrangThai(trangThai) {
    if (trangThai === "chua_khoi_hanh") return "#16A34A";
    if (trangThai === "dang_chay") return "#D97706";
    if (trangThai === "gap_su_co") return "#DC2626";
    return "#9CA3AF"; // hoan_thanh, da_huy
  }

  function suaXoaDuoc(chuyen) {
    return !chuyen.xe_id && chuyen.trang_thai === "chua_khoi_hanh" && chuyen.so_ve_dang_hoat_dong === 0;
  }

  function lyDoKhongSuaDuoc(chuyen) {
    if (chuyen.xe_id) return "Đã gán xe — điều độ viên quản lý";
    if (chuyen.trang_thai !== "chua_khoi_hanh") return "Đã/đang khởi hành";
    return "Đã có khách đặt vé";
  }

  // ---------- Lộ trình từng tuyến (nạp theo yêu cầu, có cache) ----------
  const diemTheoTuyen = new Map(); // tuyen_id -> danh sách điểm (sắp theo thu_tu tăng dần)

  async function napDiemTuyen(tuyenId) {
    if (diemTheoTuyen.has(tuyenId)) return;
    const chiTiet = await apiGet(`/quan-ly/tuyen/${tuyenId}`).catch(() => null);
    diemTheoTuyen.set(tuyenId, [...(chiTiet?.danh_sach_diem || [])].sort((a, b) => a.thu_tu - b.thu_tu));
  }

  // Danh sách điểm + số phút cộng dồn TÍNH ĐÚNG THEO CHIỀU của chuyến — chiều
  // ngược đọc ngược danh sách, thời gian giữa 2 điểm liền kề giữ nguyên độ lớn
  // như chiều xuôi (NGHIEP_VU.md mục 3.1/2.4: thời gian di chuyển đối xứng 2 chiều).
  function loTrinhTheoChieu(tuyenId, chieu) {
    const diem = diemTheoTuyen.get(tuyenId);
    if (!diem || !diem.length) return [];
    const tongPhut = diem[diem.length - 1].thoi_gian_du_kien_phut;
    const ds = chieu === "xuoi" ? diem : [...diem].reverse();
    return ds.map((d) => ({
      ten: d.ten,
      ten_khu_vuc: d.ten_khu_vuc,
      loai: d.loai,
      phut: chieu === "xuoi" ? d.thoi_gian_du_kien_phut : tongPhut - d.thoi_gian_du_kien_phut,
    }));
  }

  function renderLoTrinhChuyen(c) {
    const diem = loTrinhTheoChieu(c.tuyen_id, c.chieu);
    if (!diem.length) return "";

    const goc = new Date(c.gio_khoi_hanh);
    const hang = diem
      .map((d, idx) => {
        const gioDiem = new Date(goc.getTime() + d.phut * 60000);
        const quaNgay = gioDiem.getDate() !== goc.getDate() || gioDiem.getMonth() !== goc.getMonth();
        const gioHienThi = `${pad2(gioDiem.getHours())}:${pad2(gioDiem.getMinutes())}`;
        return `
          <div class="nv-lt__hang">
            <span class="nv-chi-tiet-tuyen__thu-tu">${idx + 1}</span>
            <span class="lc-lo-trinh__gio">${gioHienThi}${quaNgay ? "<em>+1</em>" : ""}</span>
            <span class="nv-lt__ten">${esc(d.ten)}</span>
            <span><span class="pill pill--nho pill--khu-vuc">${esc(d.ten_khu_vuc)}</span></span>
            <span>${d.loai === "van_phong" ? '<span class="pill pill--primary">Văn phòng</span>' : '<span class="pill pill--diem-dung">Điểm dừng</span>'}</span>
          </div>`;
      })
      .join("");

    return `
      <div class="cy-ct__tieu-de">Lộ trình &amp; mốc thời gian</div>
      <div class="nv-lt">
        <div class="nv-lt__hang nv-lt__hang--dau">
          <span>#</span><span>Giờ</span><span>Điểm dừng</span><span>Khu vực</span><span>Loại</span>
        </div>
        ${hang}
      </div>`;
  }

  // ---------- Modal ----------
  let modal = null;
  let noiDung = null;
  let chuyenDangXem = null;
  let onThayDoi = () => {};

  function dungModal() {
    if (modal) return;
    modal = document.createElement("div");
    modal.className = "nv-modal-overlay";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="nv-modal" style="max-width:600px;">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 12h18M3 12l4-5M3 12l4 5M21 12l-4-5M21 12l-4 5"/>
            </svg>
          </div>
          <h2>Chi tiết chuyến</h2>
        </div>
        <div class="nv-modal__body" id="ct-noi-dung">Đang tải...</div>
      </div>`;
    document.body.appendChild(modal);
    noiDung = modal.querySelector("#ct-noi-dung");
  }

  async function mo(chuyenId, tuyChon = {}) {
    dungModal();
    onThayDoi = tuyChon.onThayDoi || (() => {});
    noiDung.innerHTML = "Đang tải...";
    document.body.appendChild(modal); // xuống cuối body để hiện đè lên modal khác đang mở
    modal.hidden = false;
    try {
      chuyenDangXem = await apiGet(`/quan-ly/chuyen/${chuyenId}`);
      await napDiemTuyen(chuyenDangXem.tuyen_id);
      renderChiTiet();
    } catch (err) {
      noiDung.innerHTML = `<div class="text-error">${esc(err.message)}</div><div class="nv-modal__actions"><button type="button" class="nv-btn-secondary" id="ct-btn-dong">Đóng</button></div>`;
      noiDung.querySelector("#ct-btn-dong").addEventListener("click", () => { modal.hidden = true; });
    }
  }

  function renderChiTiet() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const ngayGioHienThi = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} · ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    const coTheSua = suaXoaDuoc(c);

    noiDung.innerHTML = `
      <div class="cy-ct-dau" style="--mau:${mauTrangThai(c.trang_thai)}">
        <div class="cy-ct-dau__gio">${pad2(d.getHours())}:${pad2(d.getMinutes())}</div>
        <div class="cy-ct-dau__info">
          <strong>${esc(c.ten_tuyen)}</strong>
          <span class="nv-text-phu">${ngayGioHienThi}</span>
        </div>
        <span class="pill pill--nho ${c.chieu === "xuoi" ? "pill--khu-vuc" : "pill--gia-thoi-han"}">${c.chieu === "xuoi" ? "Xuôi" : "Ngược"}</span>
        <span class="pill pill--nho ${pillTrangThai(c.trang_thai)}">${NHAN_TRANG_THAI[c.trang_thai] || c.trang_thai}</span>
      </div>

      <div class="ct-dong">
        <span class="nv-label" style="margin:0;">Mã chuyến</span>
        ${htmlMa(esc(c.ma))}
      </div>
      <div class="ct-dong">
        <span class="nv-label" style="margin:0;">Loại xe</span>
        <span class="pill pill--nho pill--khu-vuc">${esc(c.ma_loai_xe)} · ${esc(c.ten_loai_xe)}</span>
      </div>
      <div class="ct-dong">
        <span class="nv-label" style="margin:0;">Xe</span>
        ${c.bien_so_xe ? `<span class="pill pill--nho pill--gia-vinh-vien">${esc(c.bien_so_xe)}</span>` : '<span class="pill pill--nho pill--gia-thoi-han">Chưa gán xe</span>'}
      </div>
      <div class="ct-dong">
        <span class="nv-label" style="margin:0;">Vé đang giữ/đã bán</span>
        <span class="nv-text-phu">${c.so_ve_dang_hoat_dong}</span>
      </div>

      ${renderLoTrinhChuyen(c)}

      <div id="ct-form-sua" hidden></div>

      <div class="nv-modal__actions">
        <button type="button" class="nv-btn-secondary" id="ct-btn-dong">Đóng</button>
        ${
          coTheSua
            ? `<button type="button" class="nv-btn-secondary" id="ct-btn-sua">Sửa giờ</button><button type="button" class="nv-btn-xoa" id="ct-btn-xoa" style="flex:1; border-radius:var(--radius-button);">Xóa chuyến</button>`
            : ""
        }
      </div>
      ${coTheSua ? "" : `<p class="nv-hint" style="margin-top:10px;">${lyDoKhongSuaDuoc(c)} — không thể sửa/xóa ở đây.</p>`}
    `;

    noiDung.querySelector("#ct-btn-dong").addEventListener("click", () => {
      modal.hidden = true;
    });

    if (coTheSua) {
      noiDung.querySelector("#ct-btn-sua").addEventListener("click", moFormSuaGio);
      noiDung.querySelector("#ct-btn-xoa").addEventListener("click", xoaChuyenHienTai);
    }
  }

  function moFormSuaGio() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const gioStr = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    const box = noiDung.querySelector("#ct-form-sua");

    box.innerHTML = `
      <div class="nv-form-row">
        <div><label class="nv-label" for="ct-sua-gio">Giờ khởi hành</label><input class="input-field" type="time" id="ct-sua-gio" value="${gioStr}" /></div>
      </div>
      <div id="ct-sua-loi" class="text-error" hidden></div>
      <div class="cy-ct__nut">
        <button type="button" class="nv-btn-secondary" id="ct-sua-huy">Hủy</button>
        <button type="button" class="btn-primary cy-ct__luu" id="ct-sua-luu">Lưu</button>
      </div>`;
    box.hidden = false;

    box.querySelector("#ct-sua-huy").addEventListener("click", () => {
      box.hidden = true;
      box.innerHTML = "";
    });

    box.querySelector("#ct-sua-luu").addEventListener("click", async () => {
      const gio = box.querySelector("#ct-sua-gio").value;
      const loiEl = box.querySelector("#ct-sua-loi");
      loiEl.hidden = true;
      if (!gio) {
        loiEl.textContent = "Chọn giờ khởi hành";
        loiEl.hidden = false;
        return;
      }
      try {
        chuyenDangXem = await apiPut(`/quan-ly/chuyen/${chuyenDangXem.id}`, { gio: `${gio}:00` });
        renderChiTiet();
        onThayDoi();
      } catch (err) {
        loiEl.textContent = err.message;
        loiEl.hidden = false;
      }
    });
  }

  async function xoaChuyenHienTai() {
    const c = chuyenDangXem;
    const d = new Date(c.gio_khoi_hanh);
    const ngayHienThi = `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
    if (!confirm(`Xóa chuyến "${c.ten_tuyen}" ngày ${ngayHienThi}? Không thể hoàn tác.`)) return;
    try {
      await apiDelete(`/quan-ly/chuyen/${c.id}`);
      modal.hidden = true;
      onThayDoi();
    } catch (err) {
      alert(err.message);
    }
  }

  return { mo, NHAN_TRANG_THAI, pillTrangThai, mauTrangThai };
})();
