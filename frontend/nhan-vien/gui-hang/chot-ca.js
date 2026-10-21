/* chot-ca.js — Chốt ca tiền mặt (KE_HOACH_SUA_GUI_HANG.md mục 7, NGHIEP_VU_GUI_HANG.md mục 6).
 *
 * Nhân viên: xem trước số tiền trong két lẽ ra phải có (thu trả trước + COD − hoàn, từ lần chốt trước), nhập số đếm
 * được, chốt và in phiếu. Mốc `den_luc` của màn xem trước được gửi lại khi xác nhận: số đã xem = số được lưu, tiền
 * phát sinh sau mốc sang ca sau. Quản lý chỉ xem lịch sử (không chốt hộ). */

const NHAN_KHOAN_CA = { nguoi_gui_tra_truoc: "Thu trả trước", cod_nguoi_nhan_tra: "Thu COD", hoan: "Hoàn khi hủy đơn" };
const chotCa = { offset: 0, xemTruoc: null, dangChot: false };

/** "140.000" / "140000" / "140 000" → 140000; rỗng hoặc sai → null. */
function docSoTien(chuoi) {
  const s = String(chuoi || "").replace(/[.\s,đ]/g, "");
  return /^[0-9]{1,13}$/.test(s) ? Number(s) : null;
}

function dongTongCa(ca) {
  const dong = (nhan, so, giaTri) => `<div class="receipt-row"><span>${nhan} <span class="cell-sub">(${escapeHtml(so)} khoản)</span></span><strong>${escapeHtml(giaTri)}</strong></div>`;
  return dong("Thu trả trước", ca.so_don_tra_truoc, `+ ${dinhDangTien(ca.tien_tra_truoc)}`)
    + dong("Thu COD", ca.so_don_cod, `+ ${dinhDangTien(ca.tien_cod)}`)
    + dong("Hoàn khi hủy đơn", ca.so_don_hoan, `− ${dinhDangTien(ca.tien_hoan)}`)
    + `<div class="receipt-row total"><span>TRONG KÉT LẼ RA PHẢI CÓ:</span><span>${escapeHtml(dinhDangTien(ca.tien_phai_co))}</span></div>`;
}

function veKhoanCa(ulId, khoan) {
  const ul = $(ulId);
  if (!khoan.length) {
    timelineTrong(ul, "Không có khoản thu / hoàn nào trong ca.");
    return;
  }
  veTimeline(ul, khoan, k => ({
    gio: dinhDangThoiGian(k.thoi_gian),
    ghiChu: `${NHAN_KHOAN_CA[k.loai] || k.loai} — ${k.ma_van_don}: ${k.loai === "hoan" ? "−" : "+"} ${dinhDangTien(k.so_tien)}`,
  }));
}

const moTaKhoangCa = ca => `${ca.tu_luc ? dinhDangThoiGian(ca.tu_luc) : "lần chốt đầu tiên (từ trước tới nay)"} → ${dinhDangThoiGian(ca.den_luc)}`;

function chenhLechHienThi(so) {
  if (so === 0) return { text: "Khớp (0 đ)", cls: "cc-khop" };
  return so < 0
    ? { text: `THIẾU ${dinhDangTien(-so)}`, cls: "cc-lech" }
    : { text: `THỪA ${dinhDangTien(so)}`, cls: "cc-lech" };
}

// ---------------------------------------------------------------------
// Chốt ca (nhân viên)
// ---------------------------------------------------------------------

async function moChotCa() {
  try {
    chotCa.xemTruoc = await apiGet("/gui-hang/chot-ca/xem-truoc");
  } catch (err) {
    showToast("error", "Không mở được chốt ca", err.message);
    return;
  }
  const xt = chotCa.xemTruoc;
  datText("ccKhoang", `Ca: ${moTaKhoangCa(xt)}`);
  $("ccTong").innerHTML = dongTongCa(xt);
  datText("ccSoKhoan", `Xem từng khoản (${xt.khoan.length})`);
  veKhoanCa("ccDanhSachKhoan", xt.khoan);
  $("formChotCa").reset();
  capNhatChenhLech();
  moModal("modalChotCa");
  $("ccTienDem").focus();
}

function capNhatChenhLech() {
  const xt = chotCa.xemTruoc;
  const dem = docSoTien($("ccTienDem").value);
  const o = $("ccChenhLech");
  if (!xt || dem === null) {
    o.textContent = "—";
    o.className = "form-static cc-chenh-lech";
    $("ccGhiChuNhan").classList.remove("required");
    return;
  }
  const { text, cls } = chenhLechHienThi(dem - xt.tien_phai_co);
  o.textContent = text;
  o.className = `form-static cc-chenh-lech ${cls}`;
  $("ccGhiChuNhan").classList.toggle("required", dem !== xt.tien_phai_co);
}

async function xacNhanChotCa(e) {
  e.preventDefault();
  const xt = chotCa.xemTruoc;
  if (!xt || chotCa.dangChot) return;
  const dem = docSoTien($("ccTienDem").value);
  const ghiChu = $("ccGhiChu").value.trim();
  if (dem === null) {
    showToast("warning", "Chưa nhập số tiền", "Nhập số tiền mặt đếm được trong két (chỉ chữ số).");
    $("ccTienDem").focus();
    return;
  }
  if (dem !== xt.tien_phai_co && !ghiChu) {
    showToast("warning", "Thiếu ghi chú", "Số đếm được lệch với số phải có — ghi rõ lý do.");
    $("ccGhiChu").focus();
    return;
  }
  const { text } = chenhLechHienThi(dem - xt.tien_phai_co);
  if (!confirm(`Chốt ca: phải có ${dinhDangTien(xt.tien_phai_co)}, đếm được ${dinhDangTien(dem)} — ${text}. Sau khi chốt không sửa được. Tiếp tục?`)) return;

  const btn = $("btnXacNhanChotCa");
  chotCa.dangChot = true;
  btn.disabled = true;
  try {
    const ca = await apiPost("/gui-hang/chot-ca", { den_luc: xt.den_luc, tien_thuc_dem: dem, ghi_chu: ghiChu || null });
    dongModal("modalChotCa");
    showToast("success", "Đã chốt ca", `Nộp ${dinhDangTien(ca.tien_thuc_dem)} — ${text}.`);
    hienThiPhieuChotCa({ ...ca, khoan: xt.khoan });
    chotCa.offset = 0;
    taiLichSuChotCa();
  } catch (err) {
    showToast("error", "Không chốt được ca", err.message);
  } finally {
    chotCa.dangChot = false;
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------
// Phiếu chốt ca + lịch sử
// ---------------------------------------------------------------------

function hienThiPhieuChotCa(ca) {
  datText("pcNhanVien", ca.ten_nhan_vien || localStorage.getItem("ho_ten") || "--");
  datText("pcVanPhong", ca.ten_van_phong || state.vanPhong?.ten || "--");
  datText("pcTuLuc", ca.tu_luc ? dinhDangThoiGian(ca.tu_luc) : "Lần chốt đầu tiên");
  datText("pcDenLuc", dinhDangThoiGian(ca.den_luc));
  $("pcTong").innerHTML = dongTongCa(ca);
  datText("pcThucDem", dinhDangTien(ca.tien_thuc_dem));
  datText("pcChenhLech", chenhLechHienThi(ca.chenh_lech).text);
  $("pcGhiChuDong").hidden = !ca.ghi_chu;
  datText("pcGhiChu", ca.ghi_chu || "");
  veKhoanCa("pcDanhSachKhoan", ca.khoan || []);
  moModal("modalPhieuChotCa");
}

async function inLaiPhieuChotCa(id) {
  try {
    hienThiPhieuChotCa(await apiGet(`/gui-hang/chot-ca/${encodeURIComponent(id)}`));
  } catch (err) {
    showToast("error", "Không tải được phiếu chốt ca", err.message);
  }
}

async function taiLichSuChotCa() {
  const tbody = $("tbodyChotCa");
  if (!tbody) return;
  const params = {
    tu_ngay: $("tkTuNgay").value,
    den_ngay: $("tkDenNgay").value,
    chi_lech: $("ccChiLech").checked ? "true" : "",
    limit: SO_DONG_MOI_TRANG,
    offset: chotCa.offset,
    ...phamViQuery(),
  };
  let data;
  try {
    data = await apiGet(`/gui-hang/chot-ca${taoQuery(params)}`);
  } catch (err) {
    hienTrangThaiBang("tbodyChotCa", 8, `Lỗi tải lịch sử chốt ca: ${err.message}`, "table-empty table-error");
    return;
  }
  if (!data.items.length) {
    hienTrangThaiBang("tbodyChotCa", 8, data.total ? "Không có ca ở trang này." : "Chưa có lần chốt ca nào trong kỳ.");
  } else {
    tbody.innerHTML = data.items.map(ca => {
      const lech = chenhLechHienThi(ca.chenh_lech);
      return `
        <tr>
          <td>${escapeHtml(dinhDangThoiGian(ca.den_luc))}</td>
          <td>${escapeHtml(ca.ten_nhan_vien || "--")}<div class="cell-sub">${escapeHtml(ca.ten_van_phong || "")}</div></td>
          <td>${escapeHtml(ca.tu_luc ? dinhDangThoiGian(ca.tu_luc) : "Lần đầu")}</td>
          <td class="text-right">${escapeHtml(dinhDangTien(ca.tien_phai_co))}</td>
          <td class="text-right">${escapeHtml(dinhDangTien(ca.tien_thuc_dem))}</td>
          <td class="text-right ${lech.cls}">${escapeHtml(lech.text)}</td>
          <td>${escapeHtml(ca.ghi_chu || "")}</td>
          <td class="text-center"><button type="button" class="btn-action-icon" data-in-chot-ca="${escapeHtml(ca.id)}" title="In lại phiếu chốt ca">🖨️</button></td>
        </tr>`;
    }).join("");
  }
  veThanhPhanTrang("phanTrangChotCa", data.total, chotCa.offset);
}

function khoiTaoChotCa() {
  const btn = $("btnChotCa");
  if (laQuanLyXem()) {
    btn.hidden = true;  // quản lý chỉ xem lịch sử, không chốt ca hộ
    datText("ccMoTa", "Lịch sử chốt ca của nhân viên gửi hàng (lọc theo văn phòng đang xem và khoảng ngày phía trên). Ca bị lệch tiền tô đỏ.");
  }
  btn.addEventListener("click", moChotCa);
  $("ccTienDem").addEventListener("input", capNhatChenhLech);
  $("formChotCa").addEventListener("submit", xacNhanChotCa);
  $("ccChiLech").addEventListener("change", () => { chotCa.offset = 0; taiLichSuChotCa(); });
  ganPhanTrang("phanTrangChotCa", offset => { chotCa.offset = offset; taiLichSuChotCa(); });
  $("tbodyChotCa").addEventListener("click", e => {
    const b = e.target.closest("[data-in-chot-ca]");
    if (b) inLaiPhieuChotCa(b.dataset.inChotCa);
  });
}
