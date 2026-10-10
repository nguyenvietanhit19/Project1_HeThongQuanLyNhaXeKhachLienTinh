/* khoi-tao.js — gắn sự kiện và khởi tạo trang (nạp sau cùng). */

function hienThongBaoChuaGanVanPhong() {
  document.querySelector(".nv-content").innerHTML = `
    <div class="nv-card blocking-card">
      <h2 class="card-title">🏢 Tài khoản chưa được gán văn phòng</h2>
      <p>Nhân viên gửi hàng chỉ thao tác tại văn phòng được phân công.
      Vui lòng liên hệ quản lý để được gán văn phòng phụ trách, sau đó đăng nhập lại.</p>
    </div>`;
}

async function khoiTaoVanPhong() {
  if (laQuanLyXem()) {
    const select = $("selectVanPhongXem");
    try {
      const ds = (await apiGet("/quan-ly/diem-don-tra")).filter(d => d.loai === "van_phong");
      select.innerHTML = '<option value="">🌐 Toàn hệ thống</option>'
        + ds.map(vp => `<option value="${escapeHtml(vp.id)}">${escapeHtml(vp.ten)}</option>`).join("");
      const daLuu = localStorage.getItem("van_phong_truc_id") || "";
      if (ds.some(vp => vp.id === daLuu)) {
        select.value = daLuu;
        state.vanPhongXemId = daLuu;
      }
    } catch (err) {
      showToast("error", "Không tải được danh sách văn phòng", err.message);
    }
    select.addEventListener("change", () => {
      state.vanPhongXemId = select.value;
      try { localStorage.setItem("van_phong_truc_id", select.value); } catch (_) {}
      lamMoiTabHienTai();
    });
    return true;
  }

  const me = await apiGet("/auth/me");
  if (!me.van_phong_id) {
    hienThongBaoChuaGanVanPhong();
    return false;
  }
  state.vanPhong = await apiGet("/gui-hang/van-phong-cua-toi");
  datText("tenVanPhongHienTai", state.vanPhong.ten);
  datText("tenVanPhongGui", `${state.vanPhong.ten}${state.vanPhong.dia_chi ? ` — ${state.vanPhong.dia_chi}` : ""}`);
  return true;
}

function ganSuKien() {
  // Form tạo đơn
  $("formTaoDon").addEventListener("submit", xuLyGuiFormTaoDon);
  $("loai_hang_id").addEventListener("change", xuLyChonLoaiHang);
  $("khu_vuc_den").addEventListener("change", xuLyChonKhuVuc);
  $("diem_nhan_id").addEventListener("change", xuLyChonVanPhongNhan);
  document.querySelectorAll('input[name="phuong_thuc_thanh_toan"]').forEach(r => r.addEventListener("change", capNhatXacNhanThuTruoc));
  $("btnXacNhanTaoDon").addEventListener("click", xacNhanTaoDon);
  ["gui", "nhan"].forEach(vaiTro => {
    const oSdt = $("formTaoDon").elements[CAU_HINH_GOI_Y[vaiTro].sdt];
    oSdt.addEventListener("input", () => henGioGoiYKhach(vaiTro));
    oSdt.addEventListener("change", () => goiYKhach(vaiTro));
  });
  $("btnChuyenSangNhan").addEventListener("click", () => {
    dongModal("modalBienNhan");
    if (donDangIn) hienThiNhanDan(donDangIn);
  });

  // Hàng đến & giao hàng
  $("formTraCuuGiao").addEventListener("submit", xuLyTraCuuGiao);
  $("btnTaiLaiHangDen").addEventListener("click", taiHangDen);
  $("btnTaiLaiHangTon").addEventListener("click", taiHangDen);
  $("btnXuatCsvHangTon").addEventListener("click", xuatCsvHangTon);
  $("chipsHangDen").addEventListener("click", e => {
    const chip = e.target.closest(".quick-filter-chip");
    if (!chip) return;
    state.nhomHangDen = chip.dataset.nhom;
    state.hangDenOffset = 0;
    document.querySelectorAll("#chipsHangDen .quick-filter-chip").forEach(c => c.classList.toggle("active", c === chip));
    renderHangDen();
  });
  let henGioLocHangDen = null;
  // Ô quét/tra cứu dùng chung: gõ thì lọc danh sách, Enter thì tra cứu & mở giao hàng (xuLyTraCuuGiao).
  $("inputTraCuuGiao").addEventListener("input", () => {
    clearTimeout(henGioLocHangDen);
    henGioLocHangDen = setTimeout(locLaiHangDen, 150);
  });
  $("selectThanhToanHangDen").addEventListener("change", locLaiHangDen);
  $("selectBaoNguoiNhanHangDen").addEventListener("change", locLaiHangDen);
  $("btnDatLaiHangDen").addEventListener("click", () => {
    $("inputTraCuuGiao").value = "";
    $("selectThanhToanHangDen").value = "";
    $("selectBaoNguoiNhanHangDen").value = "";
    state.nhomHangDen = "";
    document.querySelectorAll("#chipsHangDen .quick-filter-chip").forEach(c => c.classList.toggle("active", c.dataset.nhom === ""));
    locLaiHangDen();
  });
  ganPhanTrang("phanTrangHangDen", offset => {
    state.hangDenOffset = offset;
    renderHangDen();
  });
  $("btnXacNhanGiaoHang").addEventListener("click", xacNhanGiaoHang);
  $("formLienHe").addEventListener("submit", luuKetQuaLienHe);
  $("formSuaLienHe").addEventListener("submit", luuSuaLienHe);

  // Đơn gửi đi
  $("btnTaiLaiDonGui").addEventListener("click", taiDonGui);
  $("btnXuatCsvDonGui").addEventListener("click", xuatCsvDonGui);
  $("selectTrangThaiDonGui").addEventListener("change", locLaiDonGui);
  $("selectThanhToanDonGui").addEventListener("change", locLaiDonGui);
  $("inputTuKhoaDonGui").addEventListener("input", () => {
    clearTimeout(henGioTimDonGui);
    henGioTimDonGui = setTimeout(locLaiDonGui, 350);
  });
  $("btnDatLaiDonGui").addEventListener("click", () => {
    $("selectTrangThaiDonGui").value = "";
    $("selectThanhToanDonGui").value = "";
    $("inputTuKhoaDonGui").value = "";
    locLaiDonGui();
  });
  ganPhanTrang("phanTrangDonGui", offset => {
    state.donGui.offset = offset;
    taiDonGui();
  });

  // Thống kê
  $("tkPreset").addEventListener("click", e => {
    const b = e.target.closest("[data-so-ngay]");
    if (!b) return;
    datKhoangNgay(Number(b.dataset.soNgay));
    taiThongKe();
  });
  ["tkTuNgay", "tkDenNgay"].forEach(id => $(id).addEventListener("change", () => {
    document.querySelectorAll("#tkPreset .time-tab").forEach(b => b.classList.remove("active"));
    taiThongKe();
  }));
  $("tkBieuDoRange").addEventListener("click", e => {
    const b = e.target.closest("[data-so-ngay]");
    if (!b) return;
    state.bieuDoSoNgay = Number(b.dataset.soNgay);
    document.querySelectorAll("#tkBieuDoRange .time-tab").forEach(x => x.classList.toggle("active", x === b));
    taiBieuDo();
  });
  $("btnXuatCsvDoiSoat").addEventListener("click", xuatCsvDoiSoat);
  $("btnInDoiSoat").addEventListener("click", () => inPhanTu($("tbodyDoiSoat").closest(".card-panel")));

  // Nút trong các dòng bảng/modal (event delegation)
  document.addEventListener("click", e => {
    const btnDong = e.target.closest("[data-dong]");
    if (btnDong) {
      dongModal(btnDong.dataset.dong);
      return;
    }
    const btnIn = e.target.closest("[data-in]");
    if (btnIn) {
      inPhanTu($(btnIn.dataset.in).querySelector(".print-area"));
      return;
    }
    const btn = e.target.closest("[data-hanh-dong]");
    if (!btn) return;
    const id = btn.dataset.id;
    switch (btn.dataset.hanhDong) {
      case "giao": {
        const don = timDonTrongHangDen(id);
        if (don) moModalGiaoHang(don);
        break;
      }
      case "lien-he": {
        const don = timDonTrongHangDen(id);
        if (don) moModalLienHe(don);
        break;
      }
      case "giao-tu-sdt": {
        const don = state.ketQuaSdt.find(d => d.ma_van_don === btn.dataset.ma);
        dongModal("modalKetQuaSdt");
        if (don) moModalGiaoHang(don);
        break;
      }
      case "sua-lien-he": {
        const don = timDonDeSua(id);
        if (don && coTheSuaDon(don)) moModalSuaLienHe(don);
        break;
      }
      case "in-bien-nhan": {
        const don = state.donGui.items.find(d => String(d.id) === id);
        if (don) hienThiBienNhan(don);
        break;
      }
      case "in-nhan": {
        const don = state.donGui.items.find(d => String(d.id) === id);
        if (don) hienThiNhanDan(don);
        break;
      }
    }
  });
}

async function khoiTaoTrang() {
  if (!nguoiDungHienTai) return;
  renderTopbar();
  khoiTaoChuong();

  try {
    if (!(await khoiTaoVanPhong())) return;
  } catch (err) {
    showToast("error", "Không tải được thông tin văn phòng", err.message);
    return;
  }

  ganSuKien();
  khoiTaoPhimTat();
  datKhoangNgay(30);
  capNhatXacNhanThuTruoc();

  if (!laQuanLyXem()) {
    await Promise.all([taiLoaiHang(), taiDiemNhanKhaDung()]);
  }

  let tab = tabMacDinh();
  try {
    const daLuu = localStorage.getItem("nhan_vien_gui_hang_active_tab");
    if (TAB_HOP_LE.includes(daLuu)) tab = daLuu;
  } catch (_) {}
  chuyenTab(tab);
}

window.chuyenTab = chuyenTab;
window.lamMoiTabHienTai = lamMoiTabHienTai;
window.moChiTietDon = moChiTietDon;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", khoiTaoTrang);
} else {
  khoiTaoTrang();
}
