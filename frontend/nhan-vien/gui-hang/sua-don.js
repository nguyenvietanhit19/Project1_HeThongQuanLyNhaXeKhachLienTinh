/* sua-don.js — Sửa tên / SĐT người gửi, người nhận khi đơn chưa giao (+ nhật ký chỉnh sửa).
 *
 * Chỉ sửa thông tin liên hệ: đổi tuyến, điểm nhận, loại hàng hay cước ảnh hưởng chuyến xe và
 * đối soát tiền nên phải hủy đơn rồi tạo lại. Mọi lần sửa đều được BE ghi nhật ký. */

const NHAN_TRUONG_SUA = {
  ten_nguoi_gui: "Tên người gửi",
  sdt_nguoi_gui: "SĐT người gửi",
  ten_nguoi_nhan: "Tên người nhận",
  sdt_nguoi_nhan: "SĐT người nhận",
};
const O_NHAP_SUA = {
  ten_nguoi_gui: "slTenGui",
  sdt_nguoi_gui: "slSdtGui",
  ten_nguoi_nhan: "slTenNhan",
  sdt_nguoi_nhan: "slSdtNhan",
};

/** Có hiện nút sửa cho đơn này không: nhân viên quầy, đơn chưa giao xong. */
function coTheSuaDon(d) {
  return !laQuanLyXem() && d.trang_thai !== "da_giao";
}

function timDonDeSua(id) {
  return state.donGui.items.find(d => String(d.id) === String(id))
    || state.hangDen.find(d => String(d.id) === String(id));
}

function moModalSuaLienHe(don, { quayLaiChiTiet = false } = {}) {
  state.donDangSua = { don, quayLaiChiTiet };
  datText("slMaVanDon", don.ma_van_don);
  Object.entries(O_NHAP_SUA).forEach(([truong, idO]) => { $(idO).value = don[truong] ?? ""; });
  $("slLyDo").value = "";
  moModal("modalSuaLienHe");
  $(O_NHAP_SUA.sdt_nguoi_nhan).focus(); // gõ nhầm SĐT người nhận là lý do sửa thường gặp nhất
}

async function luuSuaLienHe(e) {
  e.preventDefault();
  if (state.dangSua || !state.donDangSua) return;
  const { don, quayLaiChiTiet } = state.donDangSua;

  const thayDoi = {};
  for (const [truong, idO] of Object.entries(O_NHAP_SUA)) {
    const giaTri = $(idO).value.trim();
    const laTen = truong.startsWith("ten_");
    if (laTen ? giaTri === "" : !/^[0-9]{10,11}$/.test(giaTri)) {
      showToast("warning", "Thông tin chưa hợp lệ",
        laTen ? `${NHAN_TRUONG_SUA[truong]} không được để trống.` : `${NHAN_TRUONG_SUA[truong]} gồm 10–11 chữ số.`);
      $(idO).focus();
      return;
    }
    if (giaTri !== don[truong]) thayDoi[truong] = giaTri; // chỉ gửi trường thật sự đổi → nhật ký gọn
  }
  if (!Object.keys(thayDoi).length) {
    showToast("info", "Chưa có thay đổi", "Bạn chưa sửa thông tin nào.");
    return;
  }

  const btn = $("btnLuuSuaLienHe");
  state.dangSua = true;
  btn.disabled = true;
  try {
    await apiPut(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/thong-tin-lien-he`,
      { ...thayDoi, ly_do: $("slLyDo").value.trim() || null });
    dongModal("modalSuaLienHe");
    showToast("success", "Đã cập nhật", `Đã sửa thông tin liên hệ đơn ${don.ma_van_don}.`);
    lamMoiTabHienTai();
    if (quayLaiChiTiet) moChiTietDon(don.ma_van_don);
  } catch (err) {
    showToast("error", "Không sửa được", err.message);
    lamMoiTabHienTai(); // trạng thái đơn có thể đã đổi (vd vừa được giao) — tải lại để khớp
  } finally {
    state.dangSua = false;
    btn.disabled = false;
  }
}

/** Nhật ký chỉnh sửa trong modal chi tiết. Không có lần sửa nào thì ẩn cả khối. */
async function taiLichSuChinhSua(don) {
  const box = $("ctChinhSua");
  box.replaceChildren();
  if (!don.so_lan_chinh_sua) return;
  let ds;
  try {
    ds = await apiGet(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/lich-su-chinh-sua`);
  } catch (_) {
    return; // nhật ký chỉ để tra cứu — lỗi tải không chặn xem chi tiết
  }
  if ($("ctMaVanDon").textContent !== don.ma_van_don || !ds.length) return; // đã chuyển sang đơn khác

  const ul = taoEl("ul", "timeline");
  veTimeline(ul, ds, m => ({
    gio: dinhDangThoiGian(m.thoi_gian),
    ghiChu: `${NHAN_TRUONG_SUA[m.truong] || m.truong}: "${m.gia_tri_cu ?? ""}" → "${m.gia_tri_moi}" — ${m.ten_nguoi_thuc_hien || "không rõ"}`
      + (m.ly_do ? ` (lý do: ${m.ly_do})` : ""),
  }));
  box.append(taoEl("h4", "panel-title", "Lịch sử chỉnh sửa"), ul);
}
