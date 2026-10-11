/* huy-don.js — Hủy đơn tại văn phòng gửi (KE_HOACH_SUA_GUI_HANG.md mục 6).
 *
 * Hủy = trả lại kiện hàng cho người gửi, nên chỉ hủy được khi hàng còn trong kho văn phòng gửi
 * (chờ xếp xe, chưa gắn chuyến). Đơn trả trước đã thu → hoàn đủ cước tiền mặt, in phiếu hoàn.
 * Đơn đã rời văn phòng gửi thì xử lý ở văn phòng nhận theo UC-25, không hủy ở đây. */

const LY_DO_HUY = {
  khach_doi_y: "Khách đổi ý, không gửi nữa",
  nhap_sai_thong_tin: "Nhập sai thông tin, cần tạo lại đơn",
  hang_khong_du_dieu_kien: "Hàng không đủ điều kiện vận chuyển",
  khac: "Lý do khác",
};

/** Có hiện nút hủy cho đơn này không: nhân viên văn phòng gửi, hàng còn trong kho chờ xếp xe. */
function coTheHuyDon(d) {
  return !laQuanLyXem()
    && d.trang_thai === "cho_van_chuyen"
    && !d.chuyen_id
    && Boolean(state.vanPhong)
    && String(d.diem_gui_id) === String(state.vanPhong.id);
}

/** Số tiền phải hoàn nếu hủy ngay bây giờ (BE tính lại theo đúng dữ liệu lúc hủy). */
function tienSeHoan(d) {
  return !laCod(d) && d.da_thu_tien ? Number(d.gia_cuoc) : 0;
}

function moModalHuyDon(don) {
  state.donDangHuy = don;
  datText("hdMaVanDon", don.ma_van_don);
  const dong = (nhan, giaTri) => `<div class="receipt-row"><span>${nhan}</span><strong>${escapeHtml(giaTri)}</strong></div>`;
  $("hdNoiDung").innerHTML = `
    ${dong("Người gửi:", `${don.ten_nguoi_gui} — ${don.sdt_nguoi_gui}`)}
    ${dong("Người nhận:", `${don.ten_nguoi_nhan} — ${don.sdt_nguoi_nhan}`)}
    ${dong("Văn phòng nhận:", don.ten_diem_nhan || "--")}
    ${dong("Hàng hóa:", moTaHang(don))}
    ${dong("Cước:", `${dinhDangTien(don.gia_cuoc)} — ${laCod(don) ? "COD (chưa thu)" : "trả trước"}`)}`;

  const hoan = tienSeHoan(don);
  const box = $("hdHoanTien");
  box.className = hoan ? "modal-cod-alert" : "goi-y-box";
  box.textContent = hoan
    ? `💵 Hoàn lại cho người gửi: ${dinhDangTien(hoan)} tiền mặt (cước đã thu lúc tạo đơn).`
    : "Không hoàn tiền: đơn COD hoặc chưa thu cước tại quầy.";

  $("formHuyDon").reset();
  capNhatGhiChuHuy();
  moModal("modalHuyDon");
}

/** Lý do "Khác" thì ghi chú bắt buộc. */
function capNhatGhiChuHuy() {
  const laKhac = $("formHuyDon").elements.ly_do_huy.value === "khac";
  $("hdGhiChuNhan").classList.toggle("required", laKhac);
}

async function xacNhanHuyDon(e) {
  e.preventDefault();
  if (state.dangHuy || !state.donDangHuy) return;
  const form = $("formHuyDon");
  const lyDo = form.elements.ly_do_huy.value;
  const ghiChu = $("hdGhiChu").value.trim();
  if (!lyDo) {
    showToast("warning", "Chưa chọn lý do", "Chọn lý do hủy đơn.");
    return;
  }
  if (lyDo === "khac" && !ghiChu) {
    showToast("warning", "Thiếu ghi chú", "Chọn lý do \"Khác\" thì phải ghi rõ lý do hủy.");
    $("hdGhiChu").focus();
    return;
  }
  if (!$("hdDaTraHang").checked) {
    showToast("warning", "Chưa xác nhận", "Xác nhận đã gỡ nhãn, thu lại biên nhận và trả kiện hàng cho người gửi.");
    return;
  }

  const don = state.donDangHuy;
  const btn = $("btnXacNhanHuyDon");
  state.dangHuy = true;
  btn.disabled = true;
  try {
    const daHuy = await apiPost(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/huy`,
      { ly_do: lyDo, ghi_chu: ghiChu || null });
    dongModal("modalHuyDon");
    showToast("success", "Đã hủy đơn", daHuy.so_tien_hoan
      ? `Đơn ${daHuy.ma_van_don} đã hủy — hoàn ${dinhDangTien(daHuy.so_tien_hoan)} cho người gửi.`
      : `Đơn ${daHuy.ma_van_don} đã hủy.`);
    lamMoiTabHienTai();
    if (daHuy.so_tien_hoan || lyDo === "nhap_sai_thong_tin") hienThiPhieuHuy(daHuy);
  } catch (err) {
    showToast("error", "Không hủy được đơn", err.message);
    lamMoiTabHienTai(); // đơn có thể vừa được phụ xe chất lên xe — tải lại để khớp
  } finally {
    state.dangHuy = false;
    btn.disabled = false;
  }
}

/** Phiếu hủy đơn / hoàn tiền: in cho người gửi ký nhận tiền hoàn. Lý do "nhập sai" có nút tạo lại đơn. */
function hienThiPhieuHuy(don) {
  state.donVuaHuy = don;
  datText("phMaVanDon", don.ma_van_don);
  veMaVach("phMaVach", don.ma_van_don);
  datText("phThoiGian", dinhDangThoiGian(don.thoi_gian_huy));
  datText("phVanPhong", don.ten_diem_gui || state.vanPhong?.ten || "--");
  datText("phNguoiGui", `${don.ten_nguoi_gui} — ${don.sdt_nguoi_gui}`);
  datText("phLyDo", LY_DO_HUY[don.ly_do_huy] + (don.ghi_chu_huy ? ` (${don.ghi_chu_huy})` : ""));
  datText("phTienHoan", dinhDangTien(don.so_tien_hoan || 0));
  $("btnTaoLaiDon").hidden = don.ly_do_huy !== "nhap_sai_thong_tin";
  moModal("modalPhieuHuy");
}

/** Mở tab tạo đơn, điền sẵn người gửi/nhận và hàng của đơn vừa hủy. Lộ trình, cước và
 * thanh toán để nhân viên nhập lại — đó thường là phần bị nhập sai. */
function taoLaiDonTuDonHuy() {
  const don = state.donVuaHuy;
  if (!don) return;
  dongModal("modalPhieuHuy");
  chuyenTab("tao-don");
  datLaiFormTaoDon();
  const form = $("formTaoDon");
  ["ten_nguoi_gui", "sdt_nguoi_gui", "ten_nguoi_nhan", "sdt_nguoi_nhan"].forEach(t => { form.elements[t].value = don[t] || ""; });
  if (state.loaiHang.some(l => l.id === String(don.loai_hang_id) && !l.la_hang_cam)) {
    $("loai_hang_id").value = String(don.loai_hang_id);
    xuLyChonLoaiHang();
  }
  $("can_nang_kg").value = don.can_nang_kg ?? "";
  ["dai_cm", "rong_cm", "cao_cm"].forEach(id => { $(id).value = don[id] ?? ""; });
  showToast("info", "Đã điền sẵn thông tin", "Chọn lại văn phòng nhận, tuyến, cước và hình thức thanh toán rồi tạo đơn mới.");
  $("khu_vuc_den").focus();
}

/** Dòng thông tin hủy trong modal chi tiết đơn (dùng chung cho tra cứu). */
function dongThongTinHuy(don) {
  if (don.trang_thai !== "da_huy") return "";
  const dong = (nhan, giaTri) => `<div class="receipt-row"><span>${nhan}</span><strong>${escapeHtml(giaTri)}</strong></div>`;
  return dong("Hủy lúc:", `${dinhDangThoiGian(don.thoi_gian_huy)} — ${don.ten_nhan_vien_huy || "không rõ"}`)
    + dong("Lý do hủy:", LY_DO_HUY[don.ly_do_huy] + (don.ghi_chu_huy ? ` (${don.ghi_chu_huy})` : ""))
    + dong("Đã hoàn:", don.so_tien_hoan ? dinhDangTien(don.so_tien_hoan) : "Không hoàn");
}
