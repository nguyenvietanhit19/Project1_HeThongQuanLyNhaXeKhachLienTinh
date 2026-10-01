/*
 * app.js — Toàn bộ logic tương tác nghiệp vụ cho Nhân viên gửi hàng (UC-23 -> 27, 39)
 */

let danhSachLoaiHang = [];
let danhSachDonGanDay = [];
let donHangHienTai = null;
let danhSachTuyen = [];
let danhSachVanPhong = [];
let vanPhongTrucId = null;
let phamViToanHeThong = false;

// Cấu hình phân trang & Bộ lọc Client-side cho các bảng dữ liệu
const phanTrangDonGanDay = {
  danhSachGoc: [],
  danhSachHienThi: [],
  trangHienTai: 1,
  soDongMoiTrang: 5
};

const phanTrangHangTon = {
  danhSachGoc: [],
  danhSachHienThi: [],
  trangHienTai: 1,
  soDongMoiTrang: 5
};

// ====================================================================
// 0. Hệ thống Toast Notification
// ====================================================================

function showToast(type, title, message, duration = 4000) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const iconMap = {
    success: "✅",
    error: "❌",
    warning: "⚠️",
    info: "ℹ️"
  };

  const toast = document.createElement("div");
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${iconMap[type] || "ℹ️"}</div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button type="button" class="toast-close" onclick="this.parentElement.remove()" title="Đóng">✕</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast-hiding");
    setTimeout(() => toast.remove(), 260);
  }, duration);
}

// ====================================================================
// 1. Quản lý Tab
// ====================================================================

function chuyenTab(tabName) {
  try {
    localStorage.setItem("nhan_vien_gui_hang_active_tab", tabName);
  } catch (_) {}

  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

  const targetPane = document.getElementById(`tab-${tabName}`);
  if (targetPane) {
    targetPane.classList.add("active");
  }

  // Cập nhật trạng thái active trên nav button
  khoiTaoNav(tabName);

  // Nạp dữ liệu tương ứng khi chuyển tab
  if (tabName === "giao-hang") {
    taiDanhSachDonGanDay();
  } else if (tabName === "hang-ton") {
    taiDanhSachHangTon();
  } else if (tabName === "thong-ke") {
    taiThongKe();
  }
}

// ====================================================================
// 2. UC-23: Tiếp nhận gửi hàng tại quầy & Chặn hàng cấm
// ====================================================================

async function taiDanhSachLoaiHang() {
  const select = document.getElementById("loai_hang_id");
  try {
    const data = await apiGet("/gui-hang/loai-hang");
    danhSachLoaiHang = data || [];
    if (!select) return;

    // Loại bỏ hoàn toàn hàng cấm khỏi dropdown theo đúng nghiệp vụ thực tế quầy gửi hàng
    const danhSachHopLe = danhSachLoaiHang.filter(lh => !lh.la_hang_cam);

    select.innerHTML = '<option value="">-- Chọn loại hàng hóa --</option>';
    danhSachHopLe.forEach(lh => {
      const option = document.createElement("option");
      option.value = lh.id;
      option.textContent = lh.ten;
      select.appendChild(option);
    });
  } catch (err) {
    console.error("Không thể tải danh sách loại hàng:", err);
    if (select) {
      select.innerHTML = `<option value="">⚠️ Lỗi kết nối máy chủ: ${err.message}</option>`;
    }
  }
}

async function taiDanhSachTuyenVaVanPhong() {
  const selectTuyen = document.getElementById("tuyen_id");
  const selectGui = document.getElementById("diem_gui_id");
  const selectNhan = document.getElementById("diem_nhan_id");

  try {
    const [resTuyen, resVanPhong, resPhamVi] = await Promise.all([
      apiGet("/gui-hang/tuyen"),
      apiGet("/gui-hang/van-phong"),
      apiGet("/gui-hang/pham-vi"),
    ]);

    danhSachTuyen = resTuyen || [];
    danhSachVanPhong = resVanPhong || [];
    phamViToanHeThong = resPhamVi?.pham_vi_toan_he_thong === true;

    // Nạp tuyến vận chuyển
    if (selectTuyen && danhSachTuyen.length > 0) {
      selectTuyen.innerHTML = '<option value="">-- Chọn tuyến vận chuyển --</option>';
      danhSachTuyen.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.ten;
        selectTuyen.appendChild(opt);
      });
      selectTuyen.selectedIndex = 1;
    }

    if (danhSachVanPhong.length > 0) {
      // Nhân viên lấy văn phòng cố định từ hồ sơ trên BE; chỉ quản lý mới chọn phạm vi.
      vanPhongTrucId = phamViToanHeThong
        ? localStorage.getItem("quan_ly_van_phong_id")
        : resPhamVi?.van_phong_id;
      let vpTruc = danhSachVanPhong.find(v => v.id === vanPhongTrucId);
      if (!vpTruc && phamViToanHeThong) {
        vpTruc = danhSachVanPhong[0];
        vanPhongTrucId = vpTruc.id;
        try {
          localStorage.setItem("quan_ly_van_phong_id", vanPhongTrucId);
        } catch (_) {}
      }
      if (!vpTruc) throw new Error("Tài khoản chưa được phân công văn phòng gửi hàng.");

      // Cập nhật tên văn phòng trên Topbar
      const elTenVP = document.getElementById("tenVanPhongHienTai");
      if (elTenVP) {
        elTenVP.textContent = vpTruc.ten;
      }

      // 2. Nạp văn phòng gửi và KHÓA CỐ ĐỊNH theo đúng nghiệp vụ 10.4.1 bước 1
      if (selectGui) {
        selectGui.innerHTML = danhSachVanPhong.map(vp => `<option value="${vp.id}">${vp.ten} (${vp.dia_chi || ""})</option>`).join("");
        selectGui.value = vanPhongTrucId;
        selectGui.disabled = !phamViToanHeThong;
      }
      const btnDoiQuay = document.getElementById("btnDoiQuayTruc");
      if (btnDoiQuay) btnDoiQuay.hidden = !phamViToanHeThong;

      // 3. Nạp văn phòng nhận (mặc định loại trừ văn phòng gửi để tránh chọn nhầm)
      if (selectNhan) {
        selectNhan.innerHTML = '<option value="">-- Chọn văn phòng nhận --</option>' + danhSachVanPhong
          .filter(vp => vp.id !== vanPhongTrucId)
          .map(vp => `<option value="${vp.id}">${vp.ten} (${vp.dia_chi || ""})</option>`)
          .join("");
        if (selectNhan.options.length > 1) {
          selectNhan.selectedIndex = 1;
          // Tự động gợi ý tuyến phù hợp theo lộ trình
          xuLyThayDoiDiemNhan();
        }
      }

      // 4. Đồng bộ dropdown phạm vi thống kê & tồn kho
      const selectPhamViTK = document.getElementById("selectPhamViThongKe");
      if (selectPhamViTK && danhSachVanPhong.length > 0) {
        selectPhamViTK.innerHTML = phamViToanHeThong
          ? '<option value="">🌐 Toàn hệ thống nhà xe</option>' + danhSachVanPhong.map(vp => `<option value="${vp.id}">${vp.ten}</option>`).join("")
          : `<option value="${vanPhongTrucId}">${vpTruc.ten}</option>`;
        selectPhamViTK.value = phamViToanHeThong ? (vanPhongTrucId || "") : vanPhongTrucId;
        selectPhamViTK.disabled = !phamViToanHeThong;
      }

      const selectPhamViHT = document.getElementById("selectPhamViHangTon");
      if (selectPhamViHT && danhSachVanPhong.length > 0) {
        selectPhamViHT.innerHTML = phamViToanHeThong
          ? '<option value="">🌐 Toàn bộ các kho</option>' + danhSachVanPhong.map(vp => `<option value="${vp.id}">${vp.ten}</option>`).join("")
          : `<option value="${vanPhongTrucId}">${vpTruc.ten}</option>`;
        selectPhamViHT.value = phamViToanHeThong ? (vanPhongTrucId || "") : vanPhongTrucId;
        selectPhamViHT.disabled = !phamViToanHeThong;
      }
      taiDanhSachHangTon();
      taiThongKe();
    }
  } catch (err) {
    console.error("Không thể tải danh sách tuyến/văn phòng:", err);
    if (selectTuyen) selectTuyen.innerHTML = `<option value="">⚠️ Lỗi kết nối: ${err.message}</option>`;
    if (selectGui) selectGui.innerHTML = `<option value="">⚠️ Lỗi kết nối: ${err.message}</option>`;
    if (selectNhan) selectNhan.innerHTML = `<option value="">⚠️ Lỗi kết nối: ${err.message}</option>`;
  }
}

// Cho phép nhân viên đổi quầy trực khi luân chuyển ca
function doiVanPhongTruc() {
  if (!phamViToanHeThong) {
    showToast("error", "Không đủ quyền", "Văn phòng của nhân viên được cố định theo tài khoản.");
    return;
  }
  if (!danhSachVanPhong || danhSachVanPhong.length === 0) {
    showToast("warning", "Chưa có dữ liệu", "Đang tải danh sách văn phòng, vui lòng thử lại sau giây lát.");
    return;
  }

  const dsText = danhSachVanPhong.map((vp, idx) => `${idx + 1}. ${vp.ten}`).join("\n");
  const luaChon = prompt(`Chọn số thứ tự văn phòng bạn đang trực:\n${dsText}\n\n(Nhập số thứ tự từ 1 đến ${danhSachVanPhong.length}):`);
  if (!luaChon) return;

  const index = parseInt(luaChon, 10) - 1;
  if (isNaN(index) || index < 0 || index >= danhSachVanPhong.length) {
    showToast("error", "Lựa chọn không hợp lệ", "Vui lòng nhập đúng số thứ tự trong danh sách!");
    return;
  }

  const vpMoi = danhSachVanPhong[index];
  vanPhongTrucId = vpMoi.id;
  try {
    localStorage.setItem("quan_ly_van_phong_id", vanPhongTrucId);
  } catch (_) {}

  const selectPhamViTK = document.getElementById("selectPhamViThongKe");
  if (selectPhamViTK) selectPhamViTK.value = vanPhongTrucId;
  const selectPhamViHT = document.getElementById("selectPhamViHangTon");
  if (selectPhamViHT) selectPhamViHT.value = vanPhongTrucId;

  const elTenVP = document.getElementById("tenVanPhongHienTai");
  if (elTenVP) elTenVP.textContent = vpMoi.ten;

  const selectGui = document.getElementById("diem_gui_id");
  if (selectGui) {
    selectGui.value = vanPhongTrucId;
    selectGui.disabled = false;
  }

  const selectNhan = document.getElementById("diem_nhan_id");
  if (selectNhan) {
    const currentNhanVal = selectNhan.value;
    selectNhan.innerHTML = '<option value="">-- Chọn văn phòng nhận --</option>' + danhSachVanPhong
      .filter(vp => vp.id !== vanPhongTrucId)
      .map(vp => `<option value="${vp.id}">${vp.ten} (${vp.dia_chi || ""})</option>`)
      .join("");

    if (currentNhanVal && currentNhanVal !== vanPhongTrucId) {
      selectNhan.value = currentNhanVal;
    } else if (selectNhan.options.length > 1) {
      selectNhan.selectedIndex = 1;
    }
  }

  xuLyThayDoiDiemNhan();
  taiDanhSachHangTon();
  taiThongKe();
  showToast("success", "Đổi quầy trực thành công", `Quầy trực hiện tại: ${vpMoi.ten}`);
}

// Tự động nhận diện và gợi ý Tuyến theo Điểm gửi ➔ Điểm nhận (NGHIEP_VU.md 10.4.1 bước 4)
function xuLyThayDoiDiemNhan() {
  const selectGui = document.getElementById("diem_gui_id");
  const selectNhan = document.getElementById("diem_nhan_id");
  const selectTuyen = document.getElementById("tuyen_id");
  if (!selectNhan || !selectTuyen || !danhSachTuyen.length || !danhSachVanPhong.length) return;

  const diemGuiId = vanPhongTrucId || (selectGui ? selectGui.value : null);
  const diemNhanId = selectNhan.value;
  if (!diemGuiId || !diemNhanId) return;

  const vpGui = danhSachVanPhong.find(v => v.id === diemGuiId);
  const vpNhan = danhSachVanPhong.find(v => v.id === diemNhanId);
  if (!vpGui || !vpNhan) return;

  // Lọc lấy từ khóa địa danh chính
  const layDiaDanh = (ten) => {
    const s = (ten || "").toLowerCase();
    const match = s.match(/(hà nội|sài gòn|tp\.hcm|hồ chí minh|đà lạt|đà nẵng|nha trang|cần thơ|hải phòng|vũng tàu|huế|quy nhơn|buôn ma thuột|pleiku|phú quốc|phan thiết|bến xe miền đông|bến xe miền tây|giáp bát|mỹ đình)/i);
    return match ? match[1].toLowerCase() : s.slice(0, 5);
  };

  const ddGui = layDiaDanh(vpGui.ten);
  const ddNhan = layDiaDanh(vpNhan.ten);

  // Tìm tuyến khớp cả 2 địa danh
  const tuyenKhop = danhSachTuyen.find(t => {
    const tNorm = (t.ten || "").toLowerCase();
    return tNorm.includes(ddGui) && tNorm.includes(ddNhan);
  });

  if (tuyenKhop) {
    selectTuyen.value = tuyenKhop.id;
  }
}

function xuLyThayDoiDiemGui() {
  xuLyThayDoiDiemNhan();
}

function xuLyThayDoiLoaiHang() {
  const btnSubmit = document.getElementById("btnTaoDon");
  if (btnSubmit) {
    btnSubmit.disabled = false;
    btnSubmit.innerHTML = "<span>Tạo đơn & In biên nhận</span> 📄";
  }
}

function capNhatXacNhanDaThuTruoc() {
  const hinhThuc = document.querySelector('input[name="phuong_thuc_thanh_toan"]:checked')?.value;
  const wrap = document.getElementById("xacNhanDaThuTruocWrap");
  const checkbox = document.getElementById("chkDaThuTruoc");
  const laTraTruoc = hinhThuc === "nguoi_gui_tra_truoc";
  if (wrap) wrap.style.display = laTraTruoc ? "flex" : "none";
  if (!laTraTruoc && checkbox) checkbox.checked = false;
}

async function xuLyTaoDon(event) {
  event.preventDefault();
  const form = event.target;
  const btnSubmit = document.getElementById("btnTaoDon");

  const sdtGui = form.sdt_nguoi_gui.value.trim();
  const sdtNhan = form.sdt_nguoi_nhan.value.trim();
  const regexSdt = /^[0-9]{10,11}$/;

  if (!regexSdt.test(sdtGui)) {
    showToast("warning", "Dữ liệu không hợp lệ", "Số điện thoại người gửi phải gồm 10-11 chữ số!");
    form.sdt_nguoi_gui.focus();
    return;
  }

  if (!regexSdt.test(sdtNhan)) {
    showToast("warning", "Dữ liệu không hợp lệ", "Số điện thoại người nhận phải gồm 10-11 chữ số!");
    form.sdt_nguoi_nhan.focus();
    return;
  }

  // Lấy văn phòng gửi hiện tại (ưu tiên vanPhongTrucId vì select có thể disabled)
  const diemGuiId = vanPhongTrucId || form.diem_gui_id.value;
  const diemNhanId = form.diem_nhan_id.value;

  if (!diemGuiId) {
    showToast("error", "Thiếu văn phòng gửi", "Chưa xác định được văn phòng gửi tại ca trực!");
    return;
  }

  if (diemGuiId === diemNhanId) {
    showToast("error", "Lỗi lộ trình", "Văn phòng gửi và Văn phòng nhận không được trùng nhau!");
    form.diem_nhan_id.focus();
    return;
  }

  const giaCuoc = parseInt(form.gia_cuoc.value, 10);
  if (isNaN(giaCuoc) || giaCuoc < 1000) {
    showToast("warning", "Thiếu cước vận chuyển", "Vui lòng tự nhập số tiền cước vận chuyển thỏa thuận với khách (tối thiểu 1.000 VNĐ)!");
    form.gia_cuoc.focus();
    return;
  }

  const hinhThucThanhToan = form.phuong_thuc_thanh_toan.value;
  const daThuTruoc = document.getElementById("chkDaThuTruoc")?.checked === true;
  if (hinhThucThanhToan === "nguoi_gui_tra_truoc" && !daThuTruoc) {
    showToast("warning", "Chưa xác nhận thu tiền", "Hãy xác nhận đã nhận đủ cước của người gửi trước khi tạo đơn.");
    return;
  }

  btnSubmit.disabled = true;

  try {
    const body = {
      tuyen_id: form.tuyen_id.value,
      diem_gui_id: diemGuiId,
      diem_nhan_id: diemNhanId,
      loai_hang_id: form.loai_hang_id.value,
      can_nang_kg: parseFloat(form.can_nang_kg.value),
      dai_cm: form.dai_cm.value ? parseFloat(form.dai_cm.value) : null,
      rong_cm: form.rong_cm.value ? parseFloat(form.rong_cm.value) : null,
      cao_cm: form.cao_cm.value ? parseFloat(form.cao_cm.value) : null,
      gia_cuoc: giaCuoc,
      ten_nguoi_gui: form.ten_nguoi_gui.value.trim(),
      sdt_nguoi_gui: sdtGui,
      ten_nguoi_nhan: form.ten_nguoi_nhan.value.trim(),
      sdt_nguoi_nhan: sdtNhan,
      phuong_thuc_thanh_toan: hinhThucThanhToan,
      xac_nhan_da_thu_truoc: daThuTruoc,
    };

    const donHang = await apiPost("/gui-hang/tao-don", body);
    donHangHienTai = donHang;

    // Reset form ngoại trừ giữ nguyên điểm gửi theo quầy trực
    form.reset();
    const selectGui = document.getElementById("diem_gui_id");
    if (selectGui) {
      selectGui.value = vanPhongTrucId;
      selectGui.disabled = !phamViToanHeThong;
    }
    capNhatXacNhanDaThuTruoc();
    xuLyThayDoiLoaiHang();

    // Thông báo Toast thành công
    showToast("success", "Tạo đơn thành công", `Đơn hàng ${donHang.ma_van_don} đã được tiếp nhận.`);

    // Tải lại danh sách đơn vừa tạo & thống kê ngay lập tức
    await taiDanhSachDonGanDay();
    taiThongKe();

    // Mở modal in biên nhận
    hienThiModalBienNhan(donHang);
  } catch (err) {
    showToast("error", "Lỗi tạo đơn hàng", err.message);
  } finally {
    btnSubmit.disabled = false;
  }
}

function dinhDangThoiGian(isoStr) {
  if (!isoStr) return "--";
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return "--";
  const gio = String(d.getHours()).padStart(2, "0");
  const phut = String(d.getMinutes()).padStart(2, "0");
  const ngay = String(d.getDate()).padStart(2, "0");
  const thang = String(d.getMonth() + 1).padStart(2, "0");
  const nam = d.getFullYear();
  return `${gio}:${phut} ${ngay}/${thang}/${nam}`;
}

function hienThiModalBienNhan(don) {
  document.getElementById("modalMaVanDon").textContent = don.ma_van_don;
  const elThoiGian = document.getElementById("modalThoiGianTao");
  if (elThoiGian) {
    elThoiGian.textContent = dinhDangThoiGian(don.ngay_tao);
  }

  const elTuyen = document.getElementById("modalTuyen");
  if (elTuyen) {
    elTuyen.textContent = don.ten_tuyen || "Tuyến vận chuyển";
  }

  const elLoTrinh = document.getElementById("modalLoTrinh");
  if (elLoTrinh) {
    elLoTrinh.textContent = `${don.ten_diem_gui || "VP gửi"} ➔ ${don.ten_diem_nhan || "VP nhận"}`;
  }

  document.getElementById("modalNguoiGui").textContent = `${don.ten_nguoi_gui} (${don.sdt_nguoi_gui})`;
  document.getElementById("modalNguoiNhan").textContent = `${don.ten_nguoi_nhan} (${don.sdt_nguoi_nhan})`;
  document.getElementById("modalCanNang").textContent = `${don.can_nang_kg} kg`;
  const elLienHeVP = document.getElementById("modalLienHeVanPhongNhan");
  if (elLienHeVP) {
    elLienHeVP.textContent = [don.dia_chi_diem_nhan, don.sdt_lien_he_diem_nhan]
      .filter(Boolean).join(" · ") || "Chưa cập nhật thông tin liên hệ";
  }
  document.getElementById("modalGiaCuoc").textContent = `${parseInt(don.gia_cuoc).toLocaleString("vi-VN")} đ`;
  
  const hinhThuc = don.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra" 
    ? "Người nhận thanh toán khi lấy hàng (COD)"
    : "Người gửi trả trước (Đã thanh toán)";
  document.getElementById("modalThanhToan").textContent = hinhThuc;
  const elNhanGiaCuoc = document.getElementById("modalNhanGiaCuocLabel");
  if (elNhanGiaCuoc) {
    elNhanGiaCuoc.textContent = don.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra"
      ? "CƯỚC NGƯỜI NHẬN CẦN THANH TOÁN:"
      : "CƯỚC ĐÃ THU TẠI QUẦY:";
  }

  document.getElementById("modalBienNhan").classList.add("active");
}

function dongModal() {
  document.getElementById("modalBienNhan").classList.remove("active");
}

function inBienNhan() {
  window.print();
}

// ====================================================================
// In ấn Nhãn Dán Kiện Hàng (Shipping Label / Sticker dán thùng)
// ====================================================================

function hienThiModalNhanDan(don) {
  if (!don) return;
  donHangHienTai = don;

  const elMa = document.getElementById("labelMaVanDon");
  if (elMa) elMa.textContent = don.ma_van_don;

  const elDiemNhan = document.getElementById("labelDiemNhan");
  if (elDiemNhan) elDiemNhan.textContent = don.ten_diem_nhan || "VP NHẬN";

  const elTuyen = document.getElementById("labelTuyen");
  if (elTuyen) elTuyen.textContent = `Tuyến: ${don.ten_tuyen || "--"}`;

  const elNguoiNhan = document.getElementById("labelNguoiNhan");
  if (elNguoiNhan) elNguoiNhan.textContent = don.ten_nguoi_nhan;

  const elSdtNhan = document.getElementById("labelSdtNhan");
  if (elSdtNhan) elSdtNhan.textContent = `📞 ${don.sdt_nguoi_nhan}`;

  const elLoaiHang = document.getElementById("labelLoaiHang");
  if (elLoaiHang) elLoaiHang.textContent = don.ten_loai_hang || "Hàng hóa";

  const elCanNang = document.getElementById("labelCanNang");
  if (elCanNang) {
    const kichThuocStr = (don.dai_cm && don.rong_cm && don.cao_cm) 
      ? ` (${don.dai_cm}x${don.rong_cm}x${don.cao_cm} cm)` 
      : "";
    elCanNang.textContent = `⚖️ ${don.can_nang_kg} kg${kichThuocStr}`;
  }

  const elBanner = document.getElementById("labelPaymentBanner");
  if (elBanner) {
    const isCod = don.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra";
    if (isCod) {
      elBanner.className = "label-payment-banner is-cod";
      elBanner.innerHTML = `
        <div class="label-payment-badge">🚚 THU TIỀN COD KHI GIAO:</div>
        <div class="label-cod-highlight">${parseInt(don.gia_cuoc).toLocaleString("vi-VN")} đ</div>
      `;
    } else {
      elBanner.className = "label-payment-banner";
      elBanner.innerHTML = `
        <div class="label-payment-badge">💵 ĐÃ THANH TOÁN CƯỚC TRƯỚC</div>
        <div style="font-weight: 700; color: #15803D; font-size: 0.95rem;">0 đ COD</div>
      `;
    }
  }

  document.getElementById("modalNhanDan")?.classList.add("active");
}

function dongModalNhanDan() {
  document.getElementById("modalNhanDan")?.classList.remove("active");
}

function inNhanDan() {
  window.print();
}

function inKemNhanDanTuBienNhan() {
  dongModal();
  if (donHangHienTai) {
    hienThiModalNhanDan(donHangHienTai);
  }
}

function inLaiNhanDan(maVanDon) {
  const don = danhSachDonGanDay.find(d => d.ma_van_don === maVanDon);
  if (don) {
    hienThiModalNhanDan(don);
  } else {
    apiGet(`/gui-hang/tra-cuu/${encodeURIComponent(maVanDon)}`)
      .then(d => hienThiModalNhanDan(d))
      .catch(err => showToast("error", "Lỗi tải đơn", `Không thể tải thông tin đơn: ${err.message}`));
  }
}

// ====================================================================
// In ấn Phiếu Xuất Kho Bàn Giao Hàng & Thu tiền COD
// ====================================================================

function hienThiModalPhieuXuatKho(don) {
  if (!don) return;

  const elMa = document.getElementById("xuatKhoMaVanDon");
  if (elMa) elMa.textContent = don.ma_van_don;

  const elThoiGian = document.getElementById("xuatKhoThoiGian");
  if (elThoiGian) elThoiGian.textContent = dinhDangThoiGian(new Date().toISOString());

  const elVP = document.getElementById("xuatKhoVanPhong");
  if (elVP) elVP.textContent = don.ten_diem_nhan || "Văn phòng trả hàng";

  const elNhan = document.getElementById("xuatKhoNguoiNhan");
  if (elNhan) elNhan.textContent = don.ten_nguoi_nhan;

  const elSdt = document.getElementById("xuatKhoSdtNhan");
  if (elSdt) elSdt.textContent = don.sdt_nguoi_nhan;

  const isCod = don.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra";
  const elTT = document.getElementById("xuatKhoThanhToan");
  if (elTT) elTT.textContent = isCod ? "Thu tiền COD tại quầy" : "Người gửi đã thanh toán trước";

  const elTien = document.getElementById("xuatKhoTienThu");
  if (elTien) {
    elTien.textContent = isCod ? `${parseInt(don.gia_cuoc).toLocaleString("vi-VN")} đ` : "0 đ (Đã trả trước)";
    elTien.style.color = isCod ? "#C0392B" : "#15803D";
  }

  document.getElementById("modalPhieuXuatKho")?.classList.add("active");
}

function dongModalPhieuXuatKho() {
  document.getElementById("modalPhieuXuatKho")?.classList.remove("active");
}

function inPhieuXuatKho() {
  window.print();
}

// ====================================================================
// HÀM TIỆN ÍCH: PHÂN TRANG GIAO DIỆN (PAGINATION UTILS)
// ====================================================================

function renderThanhPhanTrang(containerId, config, tenHamChuyenTrang, tenHamDoiKichThuoc) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const total = config.danhSachGoc ? config.danhSachGoc.length : 0;
  if (total === 0) {
    container.innerHTML = `
      <div class="pagination-left">
        <div class="pagination-info">Hiển thị <strong>0</strong> đơn</div>
      </div>
    `;
    return;
  }

  const soDong = config.soDongMoiTrang || 5;
  const tongSoTrang = Math.ceil(total / soDong) || 1;
  let trang = config.trangHienTai || 1;
  if (trang > tongSoTrang) trang = tongSoTrang;
  if (trang < 1) trang = 1;
  config.trangHienTai = trang;

  const tuDong = (trang - 1) * soDong + 1;
  const denDong = Math.min(trang * soDong, total);

  // Tạo các nút số trang thông minh
  let nutTrangHtml = "";
  const cacTrang = [];
  if (tongSoTrang <= 7) {
    for (let i = 1; i <= tongSoTrang; i++) cacTrang.push(i);
  } else {
    if (trang <= 4) {
      cacTrang.push(1, 2, 3, 4, 5, "...", tongSoTrang);
    } else if (trang >= tongSoTrang - 3) {
      cacTrang.push(1, "...", tongSoTrang - 4, tongSoTrang - 3, tongSoTrang - 2, tongSoTrang - 1, tongSoTrang);
    } else {
      cacTrang.push(1, "...", trang - 1, trang, trang + 1, "...", tongSoTrang);
    }
  }

  nutTrangHtml = cacTrang.map(p => {
    if (p === "...") {
      return '<span style="padding: 0.35rem 0.5rem; color: #9CA3AF; user-select: none;">...</span>';
    }
    const isActive = p === trang ? "active" : "";
    return `<button type="button" class="pagination-btn ${isActive}" onclick="${tenHamChuyenTrang}(${p})">${p}</button>`;
  }).join("");

  const disablePrev = trang <= 1 ? "disabled" : "";
  const disableNext = trang >= tongSoTrang ? "disabled" : "";

  container.innerHTML = `
    <div class="pagination-left">
      <div class="pagination-info">
        Hiển thị <strong>${tuDong} - ${denDong}</strong> / <strong>${total}</strong> đơn
      </div>
      <div class="pagination-size-box">
        <span>Số dòng:</span>
        <select class="pagination-size-select" onchange="${tenHamDoiKichThuoc}(this.value)">
          <option value="5" ${soDong === 5 ? "selected" : ""}>5</option>
          <option value="10" ${soDong === 10 ? "selected" : ""}>10</option>
          <option value="20" ${soDong === 20 ? "selected" : ""}>20</option>
        </select>
      </div>
    </div>
    <div class="pagination-controls">
      <button type="button" class="pagination-btn" ${disablePrev} onclick="${tenHamChuyenTrang}(${trang - 1})">❮ Trước</button>
      ${nutTrangHtml}
      <button type="button" class="pagination-btn" ${disableNext} onclick="${tenHamChuyenTrang}(${trang + 1})">Tiếp ❯</button>
    </div>
  `;
}

function apDungBoLocDonGanDay() {
  const tuKhoa = (document.getElementById("inputFilterTuKhoaDonGanDay")?.value || "").trim().toLowerCase();
  const trangThai = document.getElementById("selectFilterTrangThaiDonGanDay")?.value || "";
  const thanhToan = document.getElementById("selectFilterThanhToanDonGanDay")?.value || "";

  phanTrangDonGanDay.danhSachHienThi = phanTrangDonGanDay.danhSachGoc.filter(d => {
    // 1. Lọc theo từ khóa (Mã vận đơn, Tên người gửi, SĐT gửi, Tên người nhận, SĐT nhận, Loại hàng)
    if (tuKhoa) {
      const matchMa = (d.ma_van_don || "").toLowerCase().includes(tuKhoa);
      const matchNguoiGui = (d.ten_nguoi_gui || "").toLowerCase().includes(tuKhoa);
      const matchSdtGui = (d.sdt_nguoi_gui || "").includes(tuKhoa);
      const matchNguoiNhan = (d.ten_nguoi_nhan || "").toLowerCase().includes(tuKhoa);
      const matchSdtNhan = (d.sdt_nguoi_nhan || "").includes(tuKhoa);
      const matchLoaiHang = (d.ten_loai_hang || "").toLowerCase().includes(tuKhoa);
      if (!matchMa && !matchNguoiGui && !matchSdtGui && !matchNguoiNhan && !matchSdtNhan && !matchLoaiHang) {
        return false;
      }
    }

    // 2. Lọc theo trạng thái
    if (trangThai && d.trang_thai !== trangThai) {
      return false;
    }

    // 3. Lọc theo phương thức thanh toán
    if (thanhToan && d.phuong_thuc_thanh_toan !== thanhToan) {
      return false;
    }

    return true;
  });

  phanTrangDonGanDay.trangHienTai = 1;
  renderTrangDonGanDay(1);
}

let debounceTimerDonGanDay = null;
function xuLyTimKiemDonGanDayDebounced() {
  clearTimeout(debounceTimerDonGanDay);
  debounceTimerDonGanDay = setTimeout(() => {
    apDungBoLocDonGanDay();
  }, 200);
}

function datLaiBoLocDonGanDay() {
  clearTimeout(debounceTimerDonGanDay);
  const inputTuKhoa = document.getElementById("inputFilterTuKhoaDonGanDay");
  const selectTrangThai = document.getElementById("selectFilterTrangThaiDonGanDay");
  const selectThanhToan = document.getElementById("selectFilterThanhToanDonGanDay");

  if (inputTuKhoa) inputTuKhoa.value = "";
  if (selectTrangThai) selectTrangThai.value = "";
  if (selectThanhToan) selectThanhToan.value = "";

  document.querySelectorAll(".quick-filter-chip").forEach(chip => chip.classList.remove("active"));
  document.getElementById("chip-tat-ca")?.classList.add("active");

  apDungBoLocDonGanDay();
}

function locNhanhTheoTrangThai(trangThai) {
  const selectTrangThai = document.getElementById("selectFilterTrangThaiDonGanDay");
  if (selectTrangThai) {
    selectTrangThai.value = trangThai;
  }

  document.querySelectorAll(".quick-filter-chip").forEach(chip => chip.classList.remove("active"));
  if (!trangThai) {
    document.getElementById("chip-tat-ca")?.classList.add("active");
  } else if (trangThai === "cho_lay") {
    document.getElementById("chip-cho-lay")?.classList.add("active");
  } else if (trangThai === "da_len_xe") {
    document.getElementById("chip-da-len-xe")?.classList.add("active");
  } else if (trangThai === "cho_van_chuyen") {
    document.getElementById("chip-cho-van-chuyen")?.classList.add("active");
  } else if (trangThai === "da_giao") {
    document.getElementById("chip-da-giao")?.classList.add("active");
  } else if (trangThai === "qua_han_luu_kho") {
    document.getElementById("chip-qua-han-luu-kho")?.classList.add("active");
  }

  apDungBoLocDonGanDay();
}

function dongBoSelectSangChip() {
  const val = document.getElementById("selectFilterTrangThaiDonGanDay")?.value || "";
  document.querySelectorAll(".quick-filter-chip").forEach(chip => chip.classList.remove("active"));
  if (!val) {
    document.getElementById("chip-tat-ca")?.classList.add("active");
  } else if (val === "cho_lay") {
    document.getElementById("chip-cho-lay")?.classList.add("active");
  } else if (val === "da_len_xe") {
    document.getElementById("chip-da-len-xe")?.classList.add("active");
  } else if (val === "cho_van_chuyen") {
    document.getElementById("chip-cho-van-chuyen")?.classList.add("active");
  } else if (val === "da_giao") {
    document.getElementById("chip-da-giao")?.classList.add("active");
  } else if (val === "qua_han_luu_kho") {
    document.getElementById("chip-qua-han-luu-kho")?.classList.add("active");
  }
}

function renderTrangDonGanDay(trang = 1) {
  const tbody = document.getElementById("tbodyDonGanDay");
  if (!tbody) return;

  const list = phanTrangDonGanDay.danhSachHienThi || [];
  const total = list.length;
  if (total === 0) {
    if (phanTrangDonGanDay.danhSachGoc.length > 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 2.5rem 1rem; color: #6B7280;">
            <div style="font-size: 1.5rem; margin-bottom: 0.4rem;">🔍</div>
            <div style="font-weight: 600; color: #374151; font-size: 0.95rem;">Không tìm thấy đơn hàng nào phù hợp với điều kiện lọc.</div>
            <div style="font-size: 0.85rem; margin-top: 0.25rem;">Hãy thử thay đổi từ khóa hoặc xóa bớt điều kiện lọc.</div>
            <button type="button" class="btn-filter-reset" style="margin-top: 0.75rem;" onclick="datLaiBoLocDonGanDay()">🔄 Đặt lại bộ lọc</button>
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem; color: #6B7280;">Chưa có đơn hàng nào được tạo hôm nay tại quầy.</td></tr>';
    }
    renderThanhPhanTrang("phanTrangDonGanDay", { danhSachGoc: list, trangHienTai: 1, soDongMoiTrang: phanTrangDonGanDay.soDongMoiTrang }, "chuyenTrangDonGanDay", "doiKichThuocTrangDonGanDay");
    return;
  }

  const soDong = phanTrangDonGanDay.soDongMoiTrang;
  const tongSoTrang = Math.ceil(total / soDong) || 1;
  if (trang > tongSoTrang) trang = tongSoTrang;
  if (trang < 1) trang = 1;
  phanTrangDonGanDay.trangHienTai = trang;

  const start = (trang - 1) * soDong;
  const end = Math.min(start + soDong, total);
  const items = list.slice(start, end);

  tbody.innerHTML = items.map(d => {
    const isCod = d.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra";
    const paymentBadge = isCod
      ? (d.da_thu_tien
        ? '<span class="badge-payment prepaid">✅ Đã thu COD</span>'
        : '<span class="badge-payment cod">🚚 Chưa thu COD</span>')
      : '<span class="badge-payment prepaid">💵 Đã trả trước</span>';

    const dDate = new Date(d.ngay_tao);
    const gioPhut = !isNaN(dDate.getTime()) 
      ? `${String(dDate.getHours()).padStart(2, "0")}:${String(dDate.getMinutes()).padStart(2, "0")}` 
      : "--:--";
    const ngayThang = !isNaN(dDate.getTime()) 
      ? `${String(dDate.getDate()).padStart(2, "0")}/${String(dDate.getMonth() + 1).padStart(2, "0")}/${dDate.getFullYear()}` 
      : "--/--/----";

    let actionBtnHtml = "";
    if (d.trang_thai === "cho_lay" && (phamViToanHeThong || String(d.diem_nhan_id) === String(vanPhongTrucId))) {
      actionBtnHtml = `<button type="button" class="btn-action-deliver" onclick="moModalGiaoHang('${d.ma_van_don}')" title="Bàn giao hàng cho người nhận & thu tiền COD">🚚 Giao hàng</button>`;
    } else if (d.trang_thai === "cho_lay") {
      actionBtnHtml = '<span style="color:#6B7280; font-size:0.8rem; font-style:italic; padding:0.4rem 0.6rem;">Chờ văn phòng nhận</span>';
    } else if (d.trang_thai === "da_giao") {
      actionBtnHtml = `<button type="button" class="btn-action-slip" onclick="inPhieuXuatKhoTheoMa('${d.ma_van_don}')" title="Xem lại & In phiếu xuất kho">📄 Phiếu giao</button>`;
    } else if (d.trang_thai === "qua_han_luu_kho") {
      actionBtnHtml = '<span style="color:#B45309; font-size:0.8rem; font-style:italic; padding:0.4rem 0.6rem;">Liên hệ xử lý kho</span>';
    } else {
      actionBtnHtml = `<span style="color:#9CA3AF; font-size:0.8rem; font-style:italic; padding:0.4rem 0.6rem;">Đang chuyển</span>`;
    }

    return `
      <tr>
        <td style="white-space:nowrap;">
          <strong class="order-code-badge">${d.ma_van_don}</strong>
          <div class="order-time-sub">🕒 ${gioPhut} · 📅 ${ngayThang}</div>
        </td>
        <td>
          <div class="party-name">${d.ten_nguoi_gui}</div>
          <div class="party-phone">📞 ${d.sdt_nguoi_gui}</div>
        </td>
        <td>
          <div class="party-name">${d.ten_nguoi_nhan}</div>
          <div class="party-phone">📞 ${d.sdt_nguoi_nhan}</div>
        </td>
        <td>
          <div class="goods-name">${d.ten_loai_hang || "Hàng hóa"}</div>
          <div class="goods-weight">⚖️ ${d.can_nang_kg} kg</div>
        </td>
        <td class="text-right" style="white-space:nowrap;">
          <div class="price-tag">${parseInt(d.gia_cuoc).toLocaleString("vi-VN")} đ</div>
          <div style="margin-top:4px;">${paymentBadge}</div>
        </td>
        <td class="text-center"><span class="badge-status badge-${d.trang_thai}">${layTenTrangThai(d.trang_thai)}</span></td>
        <td class="text-center" style="white-space:nowrap;">
          <div class="table-actions-cell">
            ${actionBtnHtml}
            <button type="button" class="btn-action-icon" onclick="inLaiBienNhan('${d.ma_van_don}')" title="In biên nhận đưa cho khách gửi">🖨️</button>
            <button type="button" class="btn-action-icon" onclick="inLaiNhanDan('${d.ma_van_don}')" title="In nhãn dán thùng hàng">🏷️</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  renderThanhPhanTrang("phanTrangDonGanDay", { danhSachGoc: list, trangHienTai: trang, soDongMoiTrang: soDong }, "chuyenTrangDonGanDay", "doiKichThuocTrangDonGanDay");
}

function doiKichThuocTrangDonGanDay(soDong) {
  phanTrangDonGanDay.soDongMoiTrang = parseInt(soDong, 10) || 5;
  phanTrangDonGanDay.trangHienTai = 1;
  renderTrangDonGanDay(1);
}

function chuyenTrangDonGanDay(trang) {
  renderTrangDonGanDay(trang);
}

async function taiDanhSachDonGanDay() {
  const tbody = document.getElementById("tbodyDonGanDay");
  if (!tbody) return;

  try {
    const data = await apiGet("/gui-hang/don-gan-day?limit=50");
    danhSachDonGanDay = data || [];
    phanTrangDonGanDay.danhSachGoc = danhSachDonGanDay;

    // Cập nhật số lượng trên các Quick Filter Chips
    const countTatCa = danhSachDonGanDay.length;
    const countChoLay = danhSachDonGanDay.filter(d => d.trang_thai === "cho_lay").length;
    const countDangChuyen = danhSachDonGanDay.filter(d => d.trang_thai === "da_len_xe").length;
    const countChoXep = danhSachDonGanDay.filter(d => d.trang_thai === "cho_van_chuyen").length;
    const countDaGiao = danhSachDonGanDay.filter(d => d.trang_thai === "da_giao").length;
    const countQuaHan = danhSachDonGanDay.filter(d => d.trang_thai === "qua_han_luu_kho").length;

    const setChip = (id, count) => {
      const el = document.getElementById(id);
      if (el) el.textContent = count;
    };
    setChip("chipCountTatCa", countTatCa);
    setChip("chipCountChoLay", countChoLay);
    setChip("chipCountDangChuyen", countDangChuyen);
    setChip("chipCountChoXep", countChoXep);
    setChip("chipCountDaGiao", countDaGiao);
    setChip("chipCountQuaHan", countQuaHan);

    apDungBoLocDonGanDay();
  } catch (err) {
    console.error("Lỗi tải đơn gần đây:", err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #EF4444; padding: 1.5rem;">Lỗi tải danh sách: ${err.message}</td></tr>`;
  }
}

function inLaiBienNhan(maVanDon) {
  const don = danhSachDonGanDay.find(d => d.ma_van_don === maVanDon);
  if (don) {
    hienThiModalBienNhan(don);
  } else {
    apiGet(`/gui-hang/tra-cuu/${encodeURIComponent(maVanDon)}`)
      .then(d => hienThiModalBienNhan(d))
      .catch(err => showToast("error", "Lỗi tải đơn", `Không thể tải thông tin đơn: ${err.message}`));
  }
}

// ====================================================================
// 3. UC-24: Bàn giao hàng & Thu tiền COD
// ====================================================================

let donHangDangGiao = null;

async function moModalGiaoHang(maVanDon) {
  let don = danhSachDonGanDay.find(d => d.ma_van_don === maVanDon);
  if (!don) {
    try {
      don = await apiGet(`/gui-hang/tra-cuu/${encodeURIComponent(maVanDon)}`);
    } catch (err) {
      showToast("error", "Lỗi tải thông tin", `Không thể tải thông tin đơn hàng: ${err.message}`);
      return;
    }
  }

  donHangDangGiao = don;

  const elMa = document.getElementById("modalGiaoHangMaVanDon");
  if (elMa) elMa.textContent = don.ma_van_don;

  const elBadge = document.getElementById("modalGiaoHangBadgeTrangThai");
  if (elBadge) {
    elBadge.innerHTML = `<span class="badge-status badge-${don.trang_thai}">${layTenTrangThai(don.trang_thai)}</span>`;
  }

  const elQuaHan = document.getElementById("modalGiaoHangQuaHanAlert");
  if (elQuaHan) {
    elQuaHan.style.display = don.trang_thai === "qua_han_luu_kho" ? "block" : "none";
  }

  const isCod = don.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra";
  const elThanhToanBox = document.getElementById("modalGiaoHangThanhToanBox");
  if (elThanhToanBox) {
    if (isCod && !don.da_thu_tien) {
      elThanhToanBox.className = "modal-cod-alert is-cod";
      elThanhToanBox.innerHTML = `
        <div class="cod-alert-badge">💵 ĐƠN THU TIỀN COD TRƯỚC KHI GIAO</div>
        <div class="cod-alert-amount">${parseInt(don.gia_cuoc).toLocaleString("vi-VN")} đ</div>
        <div class="cod-alert-subtext">⚠️ Thu đủ tiền từ người nhận trước khi bàn giao kiện hàng!</div>
      `;
    } else if (isCod) {
      elThanhToanBox.className = "modal-cod-alert is-prepaid";
      elThanhToanBox.innerHTML = `
        <div class="cod-alert-badge">✅ ĐÃ THU ĐỦ TIỀN COD</div>
        <div class="cod-alert-amount" style="font-size:1.8rem; color:#16A34A;">${parseInt(don.gia_cuoc).toLocaleString("vi-VN")} đ</div>
        <div class="cod-alert-subtext">Khoản thu đã được ghi nhận trên hệ thống.</div>
      `;
    } else {
      elThanhToanBox.className = "modal-cod-alert is-prepaid";
      elThanhToanBox.innerHTML = `
        <div class="cod-alert-badge">✅ ĐÃ THANH TOÁN CƯỚC TRƯỚC</div>
        <div class="cod-alert-amount" style="font-size:1.8rem; color:#16A34A;">0 đ (Đã trả trước)</div>
        <div class="cod-alert-subtext">Người gửi đã thanh toán xong cước phí. Không thu thêm tiền của người nhận.</div>
      `;
    }
  }

  const setElText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setElText("modalGiaoHangTenNhan", don.ten_nguoi_nhan || "--");
  setElText("modalGiaoHangSdtNhan", don.sdt_nguoi_nhan || "--");
  setElText("modalGiaoHangDiemNhan", don.ten_diem_nhan || "--");
  setElText("modalGiaoHangLoaiHang", don.ten_loai_hang || "Hàng hóa tiêu chuẩn");
  setElText("modalGiaoHangCanNang", `${don.can_nang_kg || 0} kg`);
  setElText("modalGiaoHangNguoiGui", `${don.ten_nguoi_gui || "--"} (📞 ${don.sdt_nguoi_gui || "--"})`);

  const codWrap = document.getElementById("xacNhanCODWrap");
  const codCheck = document.getElementById("chkXacNhanThuCOD");
  if (codWrap) codWrap.style.display = isCod && !don.da_thu_tien ? "block" : "none";
  if (codCheck) codCheck.checked = false;

  document.getElementById("modalGiaoHangCOD")?.classList.add("active");
}

function dongModalGiaoHang() {
  document.getElementById("modalGiaoHangCOD")?.classList.remove("active");
  donHangDangGiao = null;
}

async function xacNhanGiaoHangTuModal() {
  if (!donHangDangGiao) return;

  if (donHangDangGiao.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra" && !donHangDangGiao.da_thu_tien) {
    const codCheck = document.getElementById("chkXacNhanThuCOD");
    if (!codCheck?.checked) {
      showToast("warning", "Chưa xác nhận thu COD", "Vui lòng xác nhận đã nhận đủ tiền COD từ người nhận.");
      return;
    }
  }

  const btn = document.getElementById("btnXacNhanGiaoHangModal");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Đang xử lý...";
  }

  try {
    if (donHangDangGiao.phuong_thuc_thanh_toan === "cod_nguoi_nhan_tra" && !donHangDangGiao.da_thu_tien) {
      donHangDangGiao = await apiPost("/gui-hang/xac-nhan-thu-cod", {
        ma_van_don: donHangDangGiao.ma_van_don,
        xac_nhan_da_thu: true,
      });
    }
    const res = await apiPost("/gui-hang/giao-hang", { ma_van_don: donHangDangGiao.ma_van_don });
    showToast("success", "Giao hàng thành công", `Đã bàn giao đơn hàng ${donHangDangGiao.ma_van_don} thành công!`);
    
    dongModalGiaoHang();
    await taiDanhSachDonGanDay();
    await taiDanhSachHangTon();
    taiThongKe();

    // Mở ngay modal Phiếu xuất kho để in cho khách ký đối soát
    hienThiModalPhieuXuatKho(res || donHangDangGiao);
  } catch (err) {
    showToast("error", "Lỗi giao hàng", err.message || "Không thể xác nhận giao hàng");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>✔️ Xác nhận Giao hàng & In phiếu xuất</span>";
    }
  }
}

async function inPhieuXuatKhoTheoMa(maVanDon) {
  let don = danhSachDonGanDay.find(d => d.ma_van_don === maVanDon);
  if (!don) {
    try {
      don = await apiGet(`/gui-hang/tra-cuu/${encodeURIComponent(maVanDon)}`);
    } catch (err) {
      showToast("error", "Lỗi tải phiếu", err.message);
      return;
    }
  }
  hienThiModalPhieuXuatKho(don);
}

// Fallback tương thích
function traCuuDonHang() {}
function xacNhanGiaoHang(maVanDon) {
  moModalGiaoHang(maVanDon);
}

function layTenTrangThai(tt) {
  const map = {
    cho_van_chuyen: "Chờ xếp xe",
    da_len_xe: "Đang trên xe",
    cho_lay: "Sẵn sàng lấy",
    da_giao: "Đã giao xong",
    qua_han_luu_kho: "Quá hạn kho",
  };
  return map[tt] || tt;
}

// ====================================================================
// 4. UC-25: Hàng chờ lâu tại điểm nhận
// ====================================================================

function apDungBoLocHangTon() {
  const tuKhoa = (document.getElementById("inputFilterTuKhoaHangTon")?.value || "").trim().toLowerCase();
  const mucDo = document.getElementById("selectFilterMucDoHangTon")?.value || "";
  const lienHe = document.getElementById("selectFilterLienHeHangTon")?.value || "";

  phanTrangHangTon.danhSachHienThi = phanTrangHangTon.danhSachGoc.filter(d => {
    // 1. Lọc theo từ khóa (Mã vận đơn, Tên người nhận, SĐT người nhận)
    if (tuKhoa) {
      const matchMa = (d.ma_van_don || "").toLowerCase().includes(tuKhoa);
      const matchTen = (d.ten_nguoi_nhan || "").toLowerCase().includes(tuKhoa);
      const matchSdt = (d.sdt_nguoi_nhan || "").includes(tuKhoa);
      if (!matchMa && !matchTen && !matchSdt) return false;
    }

    // 2. Lọc theo mức độ lưu kho:
    if (mucDo === "qua_han_luu_kho") {
      if (d.trang_thai !== "qua_han_luu_kho") return false;
    } else if (mucDo === "cho_lau") {
      if (!d.co_canh_bao_cho_lau || d.trang_thai === "qua_han_luu_kho") return false;
    } else if (mucDo === "cho_lay") {
      if (d.co_canh_bao_cho_lau || d.trang_thai === "qua_han_luu_kho") return false;
    }

    // 3. Lọc theo tình trạng liên hệ:
    if (lienHe === "da_thong_bao" && !d.da_thong_bao_nguoi_nhan) return false;
    if (lienHe === "chua_thong_bao" && d.da_thong_bao_nguoi_nhan) return false;

    return true;
  });

  phanTrangHangTon.trangHienTai = 1;
  renderTrangHangTon(1);
}

let debounceTimerHangTon = null;
function xuLyTimKiemHangTonDebounced() {
  clearTimeout(debounceTimerHangTon);
  debounceTimerHangTon = setTimeout(() => {
    apDungBoLocHangTon();
  }, 200);
}

function datLaiBoLocHangTon() {
  clearTimeout(debounceTimerHangTon);
  const inputTuKhoa = document.getElementById("inputFilterTuKhoaHangTon");
  const selectMucDo = document.getElementById("selectFilterMucDoHangTon");
  const selectLienHe = document.getElementById("selectFilterLienHeHangTon");

  if (inputTuKhoa) inputTuKhoa.value = "";
  if (selectMucDo) selectMucDo.value = "";
  if (selectLienHe) selectLienHe.value = "";

  apDungBoLocHangTon();
}

function renderTrangHangTon(trang = 1) {
  const tbody = document.getElementById("tbodyHangTon");
  if (!tbody) return;

  const list = phanTrangHangTon.danhSachHienThi || [];
  const total = list.length;
  if (total === 0) {
    if (phanTrangHangTon.danhSachGoc.length > 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center; padding:2.5rem 1rem; color:#6B7280;">
            <div style="font-size: 1.5rem; margin-bottom: 0.4rem;">🔍</div>
            <div style="font-weight: 600; color: #374151; font-size: 0.95rem;">Không tìm thấy kiện hàng nào phù hợp với điều kiện lọc.</div>
            <div style="font-size: 0.85rem; margin-top: 0.25rem;">Hãy thử thay đổi từ khóa hoặc xóa bớt điều kiện lọc.</div>
            <button type="button" class="btn-action-sm" style="margin-top: 0.75rem;" onclick="datLaiBoLocHangTon()">🔄 Đặt lại bộ lọc</button>
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:#10B981; font-weight:600;">✅ Không có đơn hàng nào chờ lâu tại kho này</td></tr>';
    }
    renderThanhPhanTrang("phanTrangHangTon", { danhSachGoc: list, trangHienTai: 1, soDongMoiTrang: phanTrangHangTon.soDongMoiTrang }, "chuyenTrangHangTon", "doiKichThuocTrangHangTon");
    return;
  }

  const soDong = phanTrangHangTon.soDongMoiTrang;
  const tongSoTrang = Math.ceil(total / soDong) || 1;
  if (trang > tongSoTrang) trang = tongSoTrang;
  if (trang < 1) trang = 1;
  phanTrangHangTon.trangHienTai = trang;

  const start = (trang - 1) * soDong;
  const end = Math.min(start + soDong, total);
  const items = list.slice(start, end);

  tbody.innerHTML = items.map(d => {
    const isQuaHan = d.trang_thai === "qua_han_luu_kho";
    const hasCanhBao = d.co_canh_bao_cho_lau || isQuaHan;
    const statusBadge = isQuaHan
      ? '<span class="badge-status badge-qua_han_luu_kho">🚨 Quá hạn (>14 ngày)</span>'
      : (d.co_canh_bao_cho_lau 
          ? '<span class="badge-status badge-cho_lay" style="background:#FED7AA; color:#9A3412;">⚠️ Chờ lâu (>7 ngày)</span>'
          : '<span class="badge-status badge-cho_lay">⏳ Sẵn sàng lấy</span>');

    const contactStatus = d.da_thong_bao_nguoi_nhan
      ? '<span style="color:#166534; font-size:0.8rem; font-weight:600; display:block; margin-top:3px;">✅ Đã gọi báo khách</span>'
      : '<span style="color:#DC2626; font-size:0.8rem; font-weight:600; display:block; margin-top:3px;">❌ Chưa liên hệ được</span>';

    let thoiGianKhoHtml = '<span style="color:#9CA3AF;">Chưa rõ</span>';
    if (d.thoi_gian_den_diem_nhan) {
      const dArrive = new Date(d.thoi_gian_den_diem_nhan);
      const diffMs = Math.max(0, Date.now() - dArrive.getTime());
      const soNgay = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      let badgeDays = "";
      if (isQuaHan || soNgay >= 14) {
        badgeDays = `<span class="badge-days badge-days-danger">🚨 Quá hạn: ${soNgay} ngày</span>`;
      } else if (d.co_canh_bao_cho_lau || soNgay >= 7) {
        badgeDays = `<span class="badge-days badge-days-warning">⚠️ Chờ lâu: ${soNgay} ngày</span>`;
      } else {
        badgeDays = `<span class="badge-days badge-days-normal">⏳ Lưu kho: ${soNgay} ngày</span>`;
      }

      thoiGianKhoHtml = `
        <div style="font-weight:600; color:#1F2937;">📅 ${dArrive.toLocaleDateString("vi-VN")}</div>
        <div style="margin-top:4px;">${badgeDays}</div>
      `;
    }

    return `
      <tr>
        <td style="white-space: nowrap;">
          <strong style="color:var(--color-secondary, #5B3E96); font-family:monospace;">${d.ma_van_don}</strong>
          ${hasCanhBao ? '<span title="Cần ưu tiên xử lý" style="margin-left:4px;">⚠️</span>' : ''}
        </td>
        <td>
          ${d.ten_nguoi_nhan}<br>
          <span style="color:#6B7280; font-size:0.85rem; white-space: nowrap;">📞 ${d.sdt_nguoi_nhan}</span>
          ${contactStatus}
        </td>
        <td style="white-space: nowrap;">${d.can_nang_kg} kg</td>
        <td class="text-right"><span class="price-tag">${parseInt(d.gia_cuoc).toLocaleString("vi-VN")} đ</span></td>
        <td class="text-center">${statusBadge}</td>
        <td style="white-space: nowrap;">${thoiGianKhoHtml}</td>
        <td class="text-center" style="white-space:nowrap;">
          ${d.trang_thai === "cho_lay"
            ? `<button type="button" class="btn-action-deliver" onclick="moModalGiaoHang('${d.ma_van_don}')">🚚 Giao hàng</button>`
            : ""}
          ${!d.da_thong_bao_nguoi_nhan
            ? `<button type="button" class="btn-action-sm" onclick="lienHeLai('${d.id}')">📞 Báo đã gọi nhắc</button>`
            : ""}
        </td>
      </tr>
    `;
  }).join("");

  renderThanhPhanTrang("phanTrangHangTon", { danhSachGoc: list, trangHienTai: trang, soDongMoiTrang: soDong }, "chuyenTrangHangTon", "doiKichThuocTrangHangTon");
}

function doiKichThuocTrangHangTon(soDong) {
  phanTrangHangTon.soDongMoiTrang = parseInt(soDong, 10) || 5;
  phanTrangHangTon.trangHienTai = 1;
  renderTrangHangTon(1);
}

function chuyenTrangHangTon(trang) {
  renderTrangHangTon(trang);
}

// Gán hàm vào window để gọi từ inline onclick
window.apDungBoLocHangTon = apDungBoLocHangTon;
window.xuLyTimKiemHangTonDebounced = xuLyTimKiemHangTonDebounced;
window.datLaiBoLocHangTon = datLaiBoLocHangTon;
window.chuyenTrangHangTon = chuyenTrangHangTon;
window.doiKichThuocTrangHangTon = doiKichThuocTrangHangTon;

async function taiDanhSachHangTon() {
  const tbody = document.getElementById("tbodyHangTon");
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem;">Đang tải dữ liệu...</td></tr>';

  try {
    const selectVP = document.getElementById("selectPhamViHangTon");
    const diemNhanId = selectVP ? selectVP.value : "";
    const url = diemNhanId ? `/gui-hang/hang-cho-lau?diem_nhan_id=${encodeURIComponent(diemNhanId)}` : "/gui-hang/hang-cho-lau";
    const data = await apiGet(url);
    phanTrangHangTon.danhSachGoc = data || [];
    apDungBoLocHangTon();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#EF4444; padding:2rem;">Lỗi tải dữ liệu: ${err.message}</td></tr>`;
  }
}

async function lienHeLai(donHangId) {
  try {
    await apiPost(`/gui-hang/hang-cho-lau/${donHangId}/lien-he-lai`);
    showToast("success", "Cập nhật thành công", "Đã ghi nhận liên hệ nhắc người nhận đến lấy hàng!");
    taiDanhSachHangTon();
  } catch (err) {
    showToast("error", "Lỗi cập nhật", err.message);
  }
}

// ====================================================================
// 5. UC-39: Báo cáo thống kê, Sơ đồ cột & Hiệu suất vận hành
// ====================================================================

let duLieuThongKeHienTai = null;
let phamViThoiGianBieuDoHienTai = 7;

function doiPhamViThoiGianBieuDo(soNgay) {
  phamViThoiGianBieuDoHienTai = soNgay;

  // Cập nhật giao diện tab thời gian
  document.querySelectorAll(".time-tab").forEach(tab => tab.classList.remove("active"));
  const btn = document.getElementById(`btnRange${soNgay}`);
  if (btn) btn.classList.add("active");

  taiThongKe();
}

function renderColumnChart(soNgay = 7) {
  const container = document.getElementById("columnChartContainer");
  if (!container) return;

  const data = duLieuThongKeHienTai || {};
  const theoNgay = Array.isArray(data.theo_ngay) ? data.theo_ngay : [];
  const tongTiepNhan = theoNgay.reduce((sum, row) => sum + Number(row.don_tiep_nhan || 0), 0);
  const tongDaGiao = theoNgay.reduce((sum, row) => sum + Number(row.da_giao || 0), 0);
  const elLegDaGiao = document.getElementById("legendDaGiaoCount");
  const elLegTiepNhan = document.getElementById("legendDangXuLyCount");
  if (elLegDaGiao) elLegDaGiao.textContent = tongDaGiao;
  if (elLegTiepNhan) elLegTiepNhan.textContent = tongTiepNhan;

  // Hiển thị dữ liệu thực do BE đã nhóm theo ngày tạo và ngày giao.
  const days = theoNgay.map(row => {
    const [, month, day] = row.ngay.split("-");
    return {
      dateStr: `${day}/${month}`,
      fullDate: row.ngay,
      daGiao: Number(row.da_giao || 0),
      tiepNhan: Number(row.don_tiep_nhan || 0),
    };
  }).slice(-soNgay);

  // Tìm giá trị max để scale chiều cao cột
  const maxVal = Math.max(...days.map(d => Math.max(d.daGiao, d.tiepNhan)), 5);
  const ceiling = Math.ceil(maxVal * 1.25);

  // Kích thước SVG
  const svgWidth = 650;
  const svgHeight = 250;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 25;
  const padBottom = 40;
  const chartW = svgWidth - padLeft - padRight;
  const chartH = svgHeight - padTop - padBottom;

  // Grid lines Y
  const gridSteps = 4;
  let gridLinesSvg = "";
  for (let s = 0; s <= gridSteps; s++) {
    const val = Math.round((ceiling / gridSteps) * s);
    const y = padTop + chartH - (s / gridSteps) * chartH;
    gridLinesSvg += `
      <line x1="${padLeft}" y1="${y}" x2="${svgWidth - padRight}" y2="${y}" stroke="#E5E7EB" stroke-width="1" stroke-dasharray="3 3"/>
      <text x="${padLeft - 10}" y="${y + 4}" text-anchor="end" font-size="11" fill="#9CA3AF" font-family="sans-serif">${val}</text>
    `;
  }

  // Columns X
  const count = days.length;
  const groupW = chartW / count;
  const barW = Math.max(4, Math.min(18, (groupW - 12) / 2));
  let barsSvg = "";

  days.forEach((item, idx) => {
    const groupX = padLeft + idx * groupW;
    const centerX = groupX + groupW / 2;

    const hGiao = (item.daGiao / ceiling) * chartH;
    const yGiao = padTop + chartH - hGiao;
    const xGiao = centerX - barW - 2;

    const hXuLy = (item.tiepNhan / ceiling) * chartH;
    const yXuLy = padTop + chartH - hXuLy;
    const xXuLy = centerX + 2;

    // Hiển thị nhãn ngày
    const showLabel = soNgay <= 14 || idx % 3 === 0 || idx === count - 1;
    const labelSvg = showLabel ? `
      <text x="${centerX}" y="${svgHeight - 12}" text-anchor="middle" font-size="10.5" fill="#6B7280" font-weight="500">${item.dateStr}</text>
    ` : "";

    barsSvg += `
      <!-- Nhóm cột ngày ${item.dateStr} -->
      <g class="chart-col-group" data-date="${item.dateStr}" data-giao="${item.daGiao}" data-xuly="${item.tiepNhan}"
         onmouseenter="hienThiTooltipBieuDo(event, '${item.dateStr}', ${item.daGiao}, ${item.tiepNhan})"
         onmouseleave="anTooltipBieuDo()">
        <rect x="${xGiao}" y="${yGiao}" width="${barW}" height="${hGiao}" rx="4" fill="#10B981" class="chart-bar bar-green" style="cursor:pointer;"/>
        <rect x="${xXuLy}" y="${yXuLy}" width="${barW}" height="${hXuLy}" rx="4" fill="#3B82F6" class="chart-bar bar-blue" style="cursor:pointer;"/>
        ${labelSvg}
      </g>
    `;
  });

  container.innerHTML = `
    <div style="position: relative; width: 100%; height: 100%;">
      <svg viewBox="0 0 ${svgWidth} ${svgHeight}" class="chart-svg-wrap" preserveAspectRatio="none">
        ${gridLinesSvg}
        ${barsSvg}
      </svg>
      <div id="chartTooltip" class="chart-tooltip"></div>
    </div>
  `;
}

function hienThiTooltipBieuDo(event, dateStr, daGiao, dangXuLy) {
  const tooltip = document.getElementById("chartTooltip");
  const container = document.getElementById("columnChartContainer");
  if (!tooltip || !container) return;

  tooltip.innerHTML = `
    <div style="font-weight:700; border-bottom:1px solid #374151; padding-bottom:3px; margin-bottom:3px; color:#F3F4F6;">
      📅 Ngày ${dateStr}
    </div>
    <div style="display:flex; justify-content:space-between; gap:10px; color:#34D399;">
      <span>✔️ Đã giao:</span><strong>${daGiao} đơn</strong>
    </div>
    <div style="display:flex; justify-content:space-between; gap:10px; color:#60A5FA;">
        <span>📦 Tiếp nhận:</span><strong>${dangXuLy} đơn</strong>
    </div>
  `;

  const rect = container.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
  tooltip.classList.add("visible");
}

function anTooltipBieuDo() {
  const tooltip = document.getElementById("chartTooltip");
  if (tooltip) tooltip.classList.remove("visible");
}

async function taiThongKe() {
  try {
    const selectPhamVi = document.getElementById("selectPhamViThongKe");
    const diemId = selectPhamVi ? selectPhamVi.value : "";
    const query = new URLSearchParams({ so_ngay: String(phamViThoiGianBieuDoHienTai) });
    if (diemId) query.set("diem_id", diemId);
    const url = `/gui-hang/thong-ke?${query.toString()}`;
    const data = await apiGet(url);
    if (!data) return;

    duLieuThongKeHienTai = data;

    const tongDon = data.tong_so_don ?? data.tong_don_gui_di ?? 0;
    const choXep = data.cho_van_chuyen ?? data.so_don_cho_xep_xe ?? 0;
    const dangChuyen = data.dang_van_chuyen ?? data.so_don_dang_van_chuyen ?? 0;
    const choLay = data.cho_lay ?? data.so_don_cho_lay ?? 0;
    const daGiao = data.da_giao ?? data.so_don_da_giao ?? 0;
    const hangTon = data.hang_ton_qua_han ?? data.so_don_ton_kho ?? 0;

    const cuocTraTruoc = Number(data.tien_cuoc_gui_tra_truoc || 0);
    const codDaThu = Number(data.tien_cod_da_thu || 0);
    const tongDoanhThu = data.tong_doanh_thu ?? (cuocTraTruoc + codDaThu);

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    // 4 Thẻ KPI
    setVal("statTongDon", tongDon);
    setVal("statDangChuyen", dangChuyen);
    setVal("statHangTon", hangTon);
    setVal("statDaGiao", daGiao);

    // Banner dòng tiền
    setVal("statDoanhThu", `${parseInt(tongDoanhThu).toLocaleString("vi-VN")} đ`);
    setVal("statCuocTraTruoc", `${parseInt(cuocTraTruoc).toLocaleString("vi-VN")} đ`);
    setVal("statCodDaThu", `${parseInt(codDaThu).toLocaleString("vi-VN")} đ`);

    // Tính phần trăm phân bổ trạng thái cho các Progress Bar
    const tongTrangThai = (choXep + dangChuyen + choLay + daGiao + hangTon) || 1;
    const pctDaGiao = Math.round((daGiao / tongTrangThai) * 100);
    const pctDangChuyen = Math.round((dangChuyen / tongTrangThai) * 100);
    const pctChoLay = Math.round((choLay / tongTrangThai) * 100);
    const pctChoXep = Math.round((choXep / tongTrangThai) * 100);
    const pctHangTon = Math.round((hangTon / tongTrangThai) * 100);

    setVal("pctDaGiao", `${pctDaGiao}% (${daGiao} đơn)`);
    setVal("pctDangChuyen", `${pctDangChuyen}% (${dangChuyen} đơn)`);
    setVal("pctChoLay", `${pctChoLay}% (${choLay} đơn)`);
    setVal("pctChoXep", `${pctChoXep}% (${choXep} đơn)`);
    setVal("pctHangTon", `${pctHangTon}% (${hangTon} đơn)`);
    setVal("kpiDonChoLay", choLay);
    setVal("kpiCanhBaoChoLau", data.so_don_canh_bao_7_ngay ?? 0);

    const setWidth = (id, pct) => {
      const el = document.getElementById(id);
      if (el) el.style.width = `${Math.min(100, pct)}%`;
    };

    setWidth("barDaGiao", pctDaGiao);
    setWidth("barDangChuyen", pctDangChuyen);
    setWidth("barChoLay", pctChoLay);
    setWidth("barChoXep", pctChoXep);
    setWidth("barHangTon", pctHangTon);

    // Vẽ biểu đồ cột
    renderColumnChart(phamViThoiGianBieuDoHienTai);
  } catch (err) {
    console.error("Lỗi tải thống kê:", err);
  }
}

// Khởi chạy khi nạp trang
function khoiTaoTrang() {
  let activeTab = "tao-don";
  try {
    const savedTab = localStorage.getItem("nhan_vien_gui_hang_active_tab");
    if (savedTab && ["tao-don", "giao-hang", "hang-ton", "thong-ke"].includes(savedTab)) {
      activeTab = savedTab;
    }
  } catch (_) {}

  document.querySelectorAll('input[name="phuong_thuc_thanh_toan"]').forEach(input => {
    input.addEventListener("change", capNhatXacNhanDaThuTruoc);
  });
  capNhatXacNhanDaThuTruoc();

  chuyenTab(activeTab);
  taiDanhSachLoaiHang();
  taiDanhSachTuyenVaVanPhong();
  taiDanhSachDonGanDay();
  taiThongKe();
}

// Gán toàn bộ các hàm nghiệp vụ vào window để HTML onclick gọi trực tiếp
window.doiVanPhongTruc = doiVanPhongTruc;
window.xuLyThayDoiDiemNhan = xuLyThayDoiDiemNhan;
window.xuLyThayDoiDiemGui = xuLyThayDoiDiemGui;
window.dongModal = dongModal;
window.inBienNhan = inBienNhan;
window.hienThiModalNhanDan = hienThiModalNhanDan;
window.dongModalNhanDan = dongModalNhanDan;
window.inNhanDan = inNhanDan;
window.inKemNhanDanTuBienNhan = inKemNhanDanTuBienNhan;
window.inLaiNhanDan = inLaiNhanDan;
window.hienThiModalPhieuXuatKho = hienThiModalPhieuXuatKho;
window.dongModalPhieuXuatKho = dongModalPhieuXuatKho;
window.inPhieuXuatKho = inPhieuXuatKho;
window.xacNhanGiaoHang = xacNhanGiaoHang;
window.traCuuDonHang = traCuuDonHang;
window.inLaiBienNhan = inLaiBienNhan;
window.lienHeLai = lienHeLai;
window.chuyenTab = chuyenTab;
window.xuLyTaoDon = xuLyTaoDon;
window.xuLyThayDoiLoaiHang = xuLyThayDoiLoaiHang;
window.taiThongKe = taiThongKe;
window.doiPhamViThoiGianBieuDo = doiPhamViThoiGianBieuDo;
window.renderColumnChart = renderColumnChart;
window.hienThiTooltipBieuDo = hienThiTooltipBieuDo;
window.anTooltipBieuDo = anTooltipBieuDo;
window.taiDanhSachHangTon = taiDanhSachHangTon;
window.taiDanhSachDonGanDay = taiDanhSachDonGanDay;
window.locNhanhTheoTrangThai = locNhanhTheoTrangThai;
window.dongBoSelectSangChip = dongBoSelectSangChip;
window.moModalGiaoHang = moModalGiaoHang;
window.dongModalGiaoHang = dongModalGiaoHang;
window.xacNhanGiaoHangTuModal = xacNhanGiaoHangTuModal;
window.inPhieuXuatKhoTheoMa = inPhieuXuatKhoTheoMa;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", khoiTaoTrang);
} else {
  khoiTaoTrang();
}

