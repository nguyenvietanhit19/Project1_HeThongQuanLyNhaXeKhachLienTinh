/* hang-den.js — tab Hàng đến & Hàng chờ lâu: tra cứu, giao hàng, liên hệ người nhận/người gửi. */

// ====================================================================
// Hàng đến, tra cứu & giao hàng
// ====================================================================

function nhomCuaDon(d) {
  if (d.trang_thai === "da_len_xe") return "sap_den";
  if (d.trang_thai === "qua_han_luu_kho") return "hang_ton";
  if (d.co_canh_bao_cho_lau) return "qua_7_ngay";
  return d.da_thong_bao_nguoi_nhan ? "cho_lay" : "can_goi";
}

/** Cách xử lý theo nhóm. viec: 1 dòng ngắn trên bảng (màu theo cls); goiY: câu đầy đủ (tooltip, modal liên hệ);
 * doiTuong: người nên gọi; thuTu: việc phải làm ngay lên đầu, hàng chỉ đang trên đường xuống cuối.
 * Nhóm "qua_7_ngay" tách 2 nhánh theo việc đã từng báo được người nhận hay chưa. */
const CACH_XU_LY = {
  can_goi: { thuTu: 0, viec: "📞 Gọi báo người nhận", cls: "viec--gap", goiY: "Hàng đã tới — gọi báo NGƯỜI NHẬN ngay.", doiTuong: "nguoi_nhan" },
  qua_7_ngay_da_bao: { thuTu: 1, viec: "📞 Gọi lại người nhận", cls: "viec--gap", goiY: "Quá 7 ngày — gọi lại NGƯỜI NHẬN hỏi khi nào tới lấy (hoặc nhờ người lấy hộ).", doiTuong: "nguoi_nhan" },
  qua_7_ngay_chua_bao: { thuTu: 1, viec: "📞 Gọi người gửi", cls: "viec--gui", goiY: "Quá 7 ngày, chưa từng báo được người nhận — chuyển sang gọi NGƯỜI GỬI.", doiTuong: "nguoi_gui" },
  cho_lay: { thuTu: 2, viec: "Chờ người nhận tới lấy", cls: "viec--cho", goiY: "Đã báo người nhận — chờ người nhận tới lấy.", doiTuong: null },
  hang_ton: { thuTu: 3, viec: "📞 Gọi người gửi", cls: "viec--gui", sub: "Không liên hệ được ai → báo quản lý", goiY: "Hàng tồn (>14 ngày) — liên hệ NGƯỜI GỬI để thống nhất xử lý; không liên hệ được ai thì báo quản lý.", doiTuong: "nguoi_gui" },
  sap_den: { thuTu: 4, viec: "Đang trên xe", cls: "viec--cho", doiTuong: null },
};

function xuLyCuaDon(d) {
  const nhom = nhomCuaDon(d);
  if (nhom === "sap_den") {
    return {
      ...CACH_XU_LY.sap_den,
      sub: d.bien_so_xe || "Chưa tới văn phòng",
      goiY: `Đang trên xe${d.bien_so_xe ? ` ${d.bien_so_xe}` : ""} — chưa tới văn phòng.`,
    };
  }
  if (nhom === "qua_7_ngay") return CACH_XU_LY[d.da_thong_bao_nguoi_nhan ? "qua_7_ngay_da_bao" : "qua_7_ngay_chua_bao"];
  return CACH_XU_LY[nhom];
}

/** Đếm đơn theo nhóm; khóa "" = tổng. */
function demTheoNhom(ds) {
  const dem = { "": ds.length, sap_den: 0, can_goi: 0, cho_lay: 0, qua_7_ngay: 0, hang_ton: 0 };
  ds.forEach(d => dem[nhomCuaDon(d)]++);
  return dem;
}

async function taiHangDen() {
  const tbodyId = state.tab === "hang-ton" ? "tbodyHangTon" : "tbodyHangDen";
  try {
    state.hangDen = await apiGet(`/gui-hang/hang-den${taoQuery(phamViQuery())}`);
  } catch (err) {
    hienTrangThaiBang(tbodyId, 6, `Lỗi tải dữ liệu: ${err.message}`, "table-empty table-error");
    return;
  }
  const dem = demTheoNhom(state.hangDen);
  datText("stat-hang-den-count", dem[""] - dem.sap_den);
  datText("stat-hang-ton-count", dem.qua_7_ngay + dem.hang_ton);

  capNhatChipHangDen();
  renderHangDen();
  renderHangTon();
}

/** Bỏ dấu + hạ chữ thường để tìm "tran van" ra "Trần Văn". */
function boDau(s) {
  return String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
}

/** Lọc theo ô tìm kiếm + 2 dropdown (chưa tính chip nhóm). Danh sách đã tải đủ về client nên lọc tại chỗ. */
function locHangDenTheoBoLoc() {
  const tuKhoa = boDau($("inputTraCuuGiao").value.trim());
  const thanhToan = $("selectThanhToanHangDen").value;
  const baoNguoiNhan = $("selectBaoNguoiNhanHangDen").value;
  return state.hangDen.filter(d => {
    if (thanhToan && d.phuong_thuc_thanh_toan !== thanhToan) return false;
    if (baoNguoiNhan) {
      if (d.trang_thai === "da_len_xe") return false; // chưa tới văn phòng nên chưa có chuyện báo hay chưa báo
      if ((baoNguoiNhan === "da_bao") !== Boolean(d.da_thong_bao_nguoi_nhan)) return false;
    }
    if (!tuKhoa) return true;
    return [d.ma_van_don, d.ten_nguoi_nhan, d.sdt_nguoi_nhan, d.ten_nguoi_gui, d.sdt_nguoi_gui]
      .some(v => boDau(v).includes(tuKhoa));
  });
}

/** Số trên từng chip = số đơn của nhóm đó trong kết quả đã qua ô tìm kiếm/dropdown. */
function capNhatChipHangDen() {
  const dem = demTheoNhom(locHangDenTheoBoLoc());
  document.querySelectorAll("#chipsHangDen [data-dem]").forEach(el => { el.textContent = dem[el.dataset.dem]; });
}

function locLaiHangDen() {
  state.hangDenOffset = 0;
  capNhatChipHangDen();
  renderHangDen();
}

function nutThaoTacDon(d) {
  if (laQuanLyXem()) return "";
  const nutSua = `<button type="button" class="btn-action-icon" data-hanh-dong="sua-lien-he" data-id="${escapeHtml(d.id)}" title="Sửa tên / SĐT người gửi, người nhận">✏️</button>`;
  if (d.trang_thai === "da_len_xe") return nutSua; // chưa tới văn phòng: chưa liên hệ/giao được, nhưng vẫn sửa được SĐT
  return `
    ${nutSua}
    <button type="button" class="btn-action-sm" data-hanh-dong="lien-he" data-id="${escapeHtml(d.id)}">📞 Liên hệ</button>
    <button type="button" class="btn-action-deliver" data-hanh-dong="giao" data-id="${escapeHtml(d.id)}">🚚 Giao</button>`;
}

/** Đếm ngược tới mốc 7 ngày (cảnh báo) hoặc 14 ngày (hàng tồn), tính từ lúc hàng tới văn phòng nhận.
 * Trả null khi không áp dụng (chưa tới văn phòng, hoặc đã là hàng tồn). */
function demNguocMoc(d) {
  if (d.trang_thai !== "cho_lay" || !d.thoi_gian_den_diem_nhan) return null;
  const moc = d.co_canh_bao_cho_lau ? 14 : 7;
  const conLaiMs = moc * 86400000 - (Date.now() - new Date(d.thoi_gian_den_diem_nhan).getTime());
  const viec = moc === 14 ? "thành hàng tồn" : "cảnh báo";
  if (conLaiMs <= 0) return { text: `đã tới mốc ${viec} — chờ hệ thống cập nhật`, gan: true };
  const gio = Math.ceil(conLaiMs / 3600000);
  return gio < 24
    ? { text: `${viec} sau ~${gio} giờ`, gan: true }
    : { text: `${viec} sau ${Math.ceil(gio / 24)} ngày`, gan: gio <= 48 };
}

function dongDemNguoc(d) {
  const dn = demNguocMoc(d);
  return dn ? `<div class="cell-sub${dn.gan ? " cell-sub--warn" : ""}">⏳ ${escapeHtml(dn.text)}</div>` : "";
}

function moTaTinhTrang(d) {
  if (d.trang_thai === "da_len_xe") {
    const chuyen = [d.ma_chuyen, d.bien_so_xe].filter(Boolean).join(" · ");
    return `${badgeTrangThai(d.trang_thai)}<div class="cell-sub">${escapeHtml(chuyen || "Đã xếp lên xe")}${d.gio_khoi_hanh ? ` — xuất phát ${escapeHtml(dinhDangThoiGian(d.gio_khoi_hanh))}` : ""}</div>`;
  }
  const soNgay = soNgayTu(d.thoi_gian_den_diem_nhan);
  const thongBao = d.da_thong_bao_nguoi_nhan
    ? '<span class="tag-ok" title="Đã báo được người nhận">✅ Đã báo</span>'
    : '<span class="tag-warn" title="Chưa báo được người nhận">❗ Chưa báo</span>';
  const suCo = d.so_bao_cao_su_co ? `<span class="tag-danger">⚠️ ${escapeHtml(d.so_bao_cao_su_co)} báo cáo sự cố</span>` : "";
  return `<div class="hd-trang-thai">${badgeTrangThai(d.trang_thai)}${thongBao}${suCo}</div>
    <div class="cell-sub">Tới ${escapeHtml(dinhDangNgay(d.thoi_gian_den_diem_nhan))}${soNgay !== null ? ` · ${soNgay} ngày` : ""}</div>
    ${dongDemNguoc(d)}`;
}

/** Cùng nhóm thì đơn chờ lâu nhất trước (thứ tự nhóm lấy từ CACH_XU_LY). */
function sapXepHangDen(ds) {
  const moc = d => new Date(d.thoi_gian_den_diem_nhan || d.gio_khoi_hanh || d.ngay_tao).getTime();
  return [...ds].sort((a, b) => xuLyCuaDon(a).thuTu - xuLyCuaDon(b).thuTu || moc(a) - moc(b));
}

// Các ô dùng chung cho bảng Hàng đến và bảng Hàng chờ lâu.
function oMaVanDon(d, phu) {
  return `<td><strong class="order-code-badge hd-ma">${escapeHtml(d.ma_van_don)}</strong>${phu}</td>`;
}

function oNguoi(ten, sdt, phu = "") {
  return `<td><div class="party-name">${escapeHtml(ten)}</div>${telLink(sdt)}${phu}</td>`;
}

/** Hàng có các ô riêng của từng bảng, nối thêm ô "Việc cần làm" (câu đầy đủ ở tooltip) và ô "Thao tác". */
function dongHangDen(d, cacORieng) {
  const x = xuLyCuaDon(d);
  return `
    <tr class="hd-row hd-row--${nhomCuaDon(d)}">
      ${cacORieng}
      <td title="${escapeHtml(x.goiY)}"><div class="viec ${x.cls}">${escapeHtml(x.viec)}</div>${x.sub ? `<span class="viec__sub">${escapeHtml(x.sub)}</span>` : ""}</td>
      <td class="text-center"><div class="table-actions-cell">${nutThaoTacDon(d)}</div></td>
    </tr>`;
}

function renderHangDen() {
  const tbody = $("tbodyHangDen");
  if (!tbody) return;
  const ds = sapXepHangDen(locHangDenTheoBoLoc().filter(d => !state.nhomHangDen || nhomCuaDon(d) === state.nhomHangDen));

  // Danh sách tải 1 lần về client (cần đủ để đếm các nhóm ở thanh chip) nên phân trang phía client.
  // Sau khi giao/liên hệ danh sách ngắn lại: lùi về trang cuối còn dữ liệu thay vì hiện trang trống.
  if (state.hangDenOffset >= ds.length) {
    state.hangDenOffset = Math.max(0, Math.floor((ds.length - 1) / SO_DONG_MOI_TRANG) * SO_DONG_MOI_TRANG);
  }
  veThanhPhanTrang("phanTrangHangDen", ds.length, state.hangDenOffset);
  if (!ds.length) {
    hienTrangThaiBang("tbodyHangDen", 6, state.hangDen.length ? "Không có đơn nào phù hợp." : "Chưa có hàng nào gửi tới văn phòng.");
    return;
  }
  tbody.innerHTML = ds.slice(state.hangDenOffset, state.hangDenOffset + SO_DONG_MOI_TRANG).map(d => dongHangDen(d, `
      ${oMaVanDon(d, `<div class="cell-sub">từ ${escapeHtml(d.ten_diem_gui || "--")}</div>`)}
      ${oNguoi(d.ten_nguoi_nhan, d.sdt_nguoi_nhan)}
      <td>
        <div class="goods-name">${escapeHtml(d.ten_loai_hang || "Hàng hóa")}</div>
        <div class="cell-sub">${escapeHtml(dinhDangKg(d.can_nang_kg))}</div>
        <div class="hd-cuoc"><span class="price-tag">${escapeHtml(dinhDangTien(d.gia_cuoc))}</span>${badgeThanhToan(d)}</div>
      </td>
      <td>${moTaTinhTrang(d)}</td>`)).join("");
}

function laHangChoLau(d) {
  return ["qua_7_ngay", "hang_ton"].includes(nhomCuaDon(d));
}

function renderHangTon() {
  const tbody = $("tbodyHangTon");
  if (!tbody) return;
  const ds = sapXepHangDen(state.hangDen.filter(laHangChoLau));
  if (!ds.length) {
    hienTrangThaiBang("tbodyHangTon", 6, "✅ Không có đơn nào chờ quá 7 ngày.", "table-empty table-ok");
    return;
  }
  tbody.innerHTML = ds.map(d => {
    const soNgay = soNgayTu(d.thoi_gian_den_diem_nhan);
    const daBao = d.da_thong_bao_nguoi_nhan
      ? '<span class="tag-ok">✅ Từng báo được</span>'
      : '<span class="tag-warn">❗ Chưa từng báo được</span>';
    return dongHangDen(d, `
      ${oMaVanDon(d, `<div>${badgeTrangThai(d.trang_thai)}</div>`)}
      ${oNguoi(d.ten_nguoi_nhan, d.sdt_nguoi_nhan, `<div class="cell-tags">${daBao}</div>`)}
      ${oNguoi(d.ten_nguoi_gui, d.sdt_nguoi_gui, `<div class="cell-sub">gửi từ ${escapeHtml(d.ten_diem_gui || "--")}</div>`)}
      <td><span class="badge-days ${d.trang_thai === "qua_han_luu_kho" ? "badge-days-danger" : "badge-days-warning"}">${soNgay ?? "?"} ngày</span><div class="cell-sub">tới ${escapeHtml(dinhDangNgay(d.thoi_gian_den_diem_nhan))}</div>${dongDemNguoc(d)}</td>`);
  }).join("");
}

function timDonTrongHangDen(id) {
  return state.hangDen.find(d => String(d.id) === String(id));
}

async function xuLyTraCuuGiao(e) {
  e.preventDefault();
  const giaTri = $("inputTraCuuGiao").value.trim();
  if (!giaTri) {
    showToast("warning", "Chưa nhập", "Quét hoặc nhập mã vận đơn / SĐT người nhận.");
    return;
  }
  const daMoDuoc = /^[0-9]{10,11}$/.test(giaTri)
    ? await traCuuTheoSdt(giaTri)
    : await moChiTietDon(giaTri.toUpperCase(), { uuTienGiao: true });
  if (daMoDuoc) {
    // Đã mở được đơn: xóa ô để quét đơn kế tiếp và trả danh sách về đầy đủ.
    $("inputTraCuuGiao").value = "";
    locLaiHangDen();
  } else {
    $("inputTraCuuGiao").select(); // không thấy: giữ chữ vừa gõ để nhân viên đối chiếu / sửa
  }
}

async function traCuuTheoSdt(sdt) {
  try {
    const ds = await apiGet(`/gui-hang/tra-cuu-sdt${taoQuery({ sdt, muc_dich: "giao", ...phamViQuery() })}`);
    if (!ds.length) {
      showToast("warning", "Không có đơn chờ giao", `Không có đơn nào đang chờ giao tại văn phòng cho SĐT ${sdt}.`);
      return false;
    }
    datText("ksSdt", sdt);
    $("ksDanhSach").innerHTML = ds.map(d => `
      <div class="pick-item">
        <div>
          <div class="party-name">${escapeHtml(d.ten_nguoi_nhan)}</div>
          <div class="cell-sub">${escapeHtml(d.ma_van_don)} · ${escapeHtml(d.ten_loai_hang || "")} ${escapeHtml(dinhDangKg(d.can_nang_kg))} · từ ${escapeHtml(d.ten_diem_gui || "--")} · gửi bởi ${escapeHtml(d.ten_nguoi_gui)}</div>
        </div>
        ${laQuanLyXem() ? "" : `<button type="button" class="btn-action-deliver" data-hanh-dong="giao-tu-sdt" data-ma="${escapeHtml(d.ma_van_don)}">Đúng người — Giao</button>`}
      </div>`).join("");
    state.ketQuaSdt = ds;
    moModal("modalKetQuaSdt");
    return true;
  } catch (err) {
    showToast("error", "Lỗi tra cứu", err.message);
    return false;
  }
}

/** Tra 1 đơn theo mã: nếu giao được tại văn phòng mình thì mở thẳng modal giao,
 * ngược lại hiện chi tiết kèm lý do (chặn hàng chưa tới / đã giao / giao ở văn phòng khác). */
async function moChiTietDon(ma, { uuTienGiao = false } = {}) {
  let don;
  try {
    don = await apiGet(`/gui-hang/noi-bo/tra-cuu/${encodeURIComponent(ma)}`);
  } catch (err) {
    showToast("error", "Không tìm thấy đơn", err.message);
    return false;
  }
  const taiVanPhongNhan = !state.vanPhong || String(don.diem_nhan_id) === String(state.vanPhong.id);
  const giaoDuoc = ["cho_lay", "qua_han_luu_kho"].includes(don.trang_thai) && taiVanPhongNhan && !laQuanLyXem();

  if (uuTienGiao && giaoDuoc) {
    moModalGiaoHang(don);
    return true;
  }

  let canhBao = "";
  if (don.trang_thai === "da_giao") canhBao = `Đơn đã giao lúc ${dinhDangThoiGian(don.ngay_giao)} — không giao lại.`;
  else if (["cho_van_chuyen", "da_len_xe"].includes(don.trang_thai)) canhBao = "Hàng chưa tới văn phòng nhận — chưa thể giao.";
  else if (!taiVanPhongNhan) canhBao = `Đơn này giao tại văn phòng khác: ${don.ten_diem_nhan || ""}.`;

  datText("ctMaVanDon", don.ma_van_don);
  $("ctCanhBao").hidden = !canhBao;
  datText("ctCanhBao", canhBao ? `⚠️ ${canhBao}` : "");
  const dong = (nhan, giaTri) => `<div class="receipt-row"><span>${nhan}</span><strong>${escapeHtml(giaTri)}</strong></div>`;
  $("ctNoiDung").innerHTML = `
    <div class="receipt-row"><span>Trạng thái:</span>${badgeTrangThai(don.trang_thai)}</div>
    ${dong("Lộ trình:", `${don.ten_diem_gui || "--"} ➔ ${don.ten_diem_nhan || "--"}`)}
    ${dong("Tuyến:", don.ten_tuyen || "--")}
    ${don.ma_chuyen ? dong("Chuyến / xe:", [don.ma_chuyen, don.bien_so_xe].filter(Boolean).join(" · ")) : ""}
    ${dong("Người gửi:", `${don.ten_nguoi_gui} (${don.sdt_nguoi_gui})`)}
    ${dong("Người nhận:", `${don.ten_nguoi_nhan} (${don.sdt_nguoi_nhan})`)}
    ${dong("Hàng hóa:", moTaHang(don))}
    ${dong("Cước:", `${dinhDangTien(don.gia_cuoc)} — ${laCod(don) ? "COD" : "trả trước"}`)}
    ${dong("Tạo lúc:", dinhDangThoiGian(don.ngay_tao))}
    ${don.thoi_gian_den_diem_nhan ? dong("Tới văn phòng nhận:", dinhDangThoiGian(don.thoi_gian_den_diem_nhan)) : ""}`;

  taiLichSuTrangThai(don);
  taiLichSuChinhSua(don);

  const hanhDong = $("ctHanhDong");
  hanhDong.innerHTML = "";
  const themNut = (nhan, cls, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = cls;
    b.textContent = nhan;
    b.addEventListener("click", fn);
    hanhDong.appendChild(b);
  };
  if (giaoDuoc) {
    themNut("📞 Liên hệ", "btn-action-sm", () => { dongModal("modalChiTietDon"); moModalLienHe(don); });
    themNut("🚚 Giao hàng", "btn-print", () => { dongModal("modalChiTietDon"); moModalGiaoHang(don); });
  }
  if (coTheSuaDon(don)) {
    themNut("✏️ Sửa thông tin liên hệ", "btn-action-sm", () => { dongModal("modalChiTietDon"); moModalSuaLienHe(don, { quayLaiChiTiet: true }); });
  }
  if (!laQuanLyXem() && state.vanPhong && String(don.diem_gui_id) === String(state.vanPhong.id)) {
    themNut("🖨️ In lại biên nhận", "btn-action-sm", () => { dongModal("modalChiTietDon"); hienThiBienNhan(don); });
  }
  themNut("Đóng", "btn-close-modal", () => dongModal("modalChiTietDon"));
  moModal("modalChiTietDon");
  return true;
}

/** Timeline đổi trạng thái của đơn (ai chuyển, lúc nào). Lỗi tải không chặn xem chi tiết. */
async function taiLichSuTrangThai(don) {
  const box = $("ctLichSu");
  box.innerHTML = '<h4 class="panel-title">Hành trình đơn hàng</h4><ul class="timeline"><li class="timeline__empty">Đang tải...</li></ul>';
  let moc;
  try {
    moc = await apiGet(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/lich-su-trang-thai`);
  } catch (_) {
    timelineTrong(box.querySelector(".timeline"), "Không tải được hành trình.");
    return;
  }
  if ($("ctMaVanDon").textContent !== don.ma_van_don) return; // đã chuyển sang đơn khác
  const ten = t => TRANG_THAI[t]?.ten || t;
  veTimeline(box.querySelector(".timeline"), moc, m => {
    const viec = m.tu_trang_thai ? `${ten(m.tu_trang_thai)} → ${ten(m.den_trang_thai)}` : `Tiếp nhận đơn (${ten(m.den_trang_thai)})`;
    return { gio: dinhDangThoiGian(m.thoi_gian), ghiChu: `${viec} — ${m.ten_nguoi_thuc_hien || "Hệ thống tự động"}` };
  });
}

function xuatCsvHangTon() {
  const ds = state.hangDen.filter(laHangChoLau);
  if (!ds.length) {
    showToast("warning", "Không có dữ liệu", "Không có đơn nào để xuất.");
    return;
  }
  xuatCsv(`hang-ton-${ngayISO(new Date())}.csv`,
    ["Mã vận đơn", "Nhóm", "Tên người nhận", "SĐT người nhận", "Tên người gửi", "SĐT người gửi", "Văn phòng gửi",
      "Tới văn phòng nhận", "Số ngày chờ", "Đã từng báo được người nhận", "Cước (VNĐ)", "Hình thức"],
    ds.map(d => [
      d.ma_van_don, nhomCuaDon(d) === "hang_ton" ? "Hàng tồn (>14 ngày)" : "Quá 7 ngày",
      d.ten_nguoi_nhan, d.sdt_nguoi_nhan, d.ten_nguoi_gui, d.sdt_nguoi_gui, d.ten_diem_gui || "",
      dinhDangThoiGian(d.thoi_gian_den_diem_nhan), soNgayTu(d.thoi_gian_den_diem_nhan) ?? "",
      d.da_thong_bao_nguoi_nhan ? "Có" : "Chưa", d.gia_cuoc,
      laCod(d) ? "COD" : "Trả trước",
    ]));
}

async function moModalGiaoHang(don) {
  state.donDangGiao = don;
  const cod = laCod(don);

  datText("ghMaVanDon", don.ma_van_don);
  $("ghTrangThai").innerHTML = badgeTrangThai(don.trang_thai);
  $("ghHangTon").hidden = don.trang_thai !== "qua_han_luu_kho";
  datText("ghTenNhan", don.ten_nguoi_nhan);
  datText("ghSdtNhan", `📞 ${don.sdt_nguoi_nhan}`);
  datText("ghLoaiHang", don.ten_loai_hang || "Hàng hóa");
  datText("ghCanNang", dinhDangKg(don.can_nang_kg));
  datText("ghNguoiGui", `${don.ten_nguoi_gui} (${don.sdt_nguoi_gui})`);

  const hop = $("ghThanhToan");
  hop.className = `modal-cod-alert ${cod ? "is-cod" : "is-prepaid"}`;
  hop.innerHTML = '<div class="cod-alert-badge"></div><div class="cod-alert-amount"></div><div class="cod-alert-subtext"></div>';
  hop.children[0].textContent = cod ? "💵 THU COD TRƯỚC KHI GIAO" : "✅ NGƯỜI GỬI ĐÃ TRẢ CƯỚC";
  hop.children[1].textContent = cod ? dinhDangTien(don.gia_cuoc) : "0 đ";
  hop.children[2].textContent = cod ? "Thu đủ tiền mặt từ người nhận rồi mới bàn giao." : "Không thu thêm tiền của người nhận.";

  $("chkKiemTraKienHang").checked = false;
  $("chkXacNhanThuCOD").checked = false;
  $("ghXacNhanCodWrap").hidden = !cod;

  const hopSuCo = $("ghSuCo");
  hopSuCo.hidden = true;
  moModal("modalGiaoHangCOD");

  if (don.so_bao_cao_su_co) {
    try {
      const ds = await apiGet(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/su-co`);
      if (ds.length && state.donDangGiao === don) {
        hopSuCo.innerHTML = "<strong>⚠️ Phụ xe đã báo sự cố với kiện hàng này — kiểm tra kỹ cùng người nhận:</strong><ul></ul>";
        const ul = hopSuCo.querySelector("ul");
        ds.forEach(bc => {
          const li = document.createElement("li");
          li.textContent = `${dinhDangThoiGian(bc.ngay_tao)} — ${bc.mo_ta}${bc.ten_nguoi_bao_cao ? ` (${bc.ten_nguoi_bao_cao})` : ""}`;
          ul.appendChild(li);
        });
        hopSuCo.hidden = false;
      }
    } catch (_) {}
  }
}

async function xacNhanGiaoHang() {
  const don = state.donDangGiao;
  if (!don) return;
  const cod = laCod(don);
  if (!$("chkKiemTraKienHang").checked) {
    showToast("warning", "Chưa xác nhận kiểm hàng", "Người nhận cần kiểm tra kiện hàng trước khi bàn giao.");
    return;
  }
  if (cod && !$("chkXacNhanThuCOD").checked) {
    showToast("warning", "Chưa xác nhận thu COD", "Thu đủ cước COD và tích xác nhận trước khi giao.");
    return;
  }
  const btn = $("btnXacNhanGiaoHang");
  btn.disabled = true;
  try {
    const ketQua = await apiPost("/gui-hang/giao-hang", { ma_van_don: don.ma_van_don, xac_nhan_da_thu: cod });
    dongModal("modalGiaoHangCOD");
    state.donDangGiao = null;
    showToast("success", "Đã giao hàng", `Đơn ${ketQua.ma_van_don} đã bàn giao cho người nhận.`);
    hienThiPhieuBanGiao(ketQua);
    taiHangDen();
  } catch (err) {
    showToast("error", "Không giao được", err.message);
  } finally {
    btn.disabled = false;
  }
}

// ====================================================================
// Liên hệ người nhận / người gửi / báo quản lý
// ====================================================================

const LUA_CHON_LIEN_HE = [
  { doi_tuong: "nguoi_nhan", ket_qua: "da_lien_he", nhan: "✅ Đã gọi báo được người nhận" },
  { doi_tuong: "nguoi_nhan", ket_qua: "khong_lien_he_duoc", nhan: "❌ Gọi người nhận không được" },
  { doi_tuong: "nguoi_gui", ket_qua: "da_lien_he", nhan: "✅ Đã liên hệ được người gửi (ghi hướng xử lý)", chiKhiQuaHan: true },
  { doi_tuong: "nguoi_gui", ket_qua: "khong_lien_he_duoc", nhan: "❌ Gọi người gửi không được", chiKhiQuaHan: true },
  { doi_tuong: "quan_ly", ket_qua: "da_bao_quan_ly", nhan: "🧑‍💼 Không liên hệ được ai — báo quản lý xử lý", chiKhiQuaHan: true },
];

async function moModalLienHe(don) {
  state.donDangLienHe = don;
  const quaHan = don.co_canh_bao_cho_lau || don.trang_thai === "qua_han_luu_kho";
  const goiY = xuLyCuaDon(don);

  datText("lhMaVanDon", don.ma_van_don);
  datText("lhGoiY", `💡 ${goiY.goiY}`);
  $("lhDanhBa").innerHTML = `
    <div class="danh-ba-item"><span>Người nhận</span><strong>${escapeHtml(don.ten_nguoi_nhan)}</strong>${telLink(don.sdt_nguoi_nhan)}</div>
    <div class="danh-ba-item"><span>Người gửi</span><strong>${escapeHtml(don.ten_nguoi_gui)}</strong>${telLink(don.sdt_nguoi_gui)}</div>`;

  const luaChon = LUA_CHON_LIEN_HE.filter(l => !l.chiKhiQuaHan || quaHan);
  const macDinh = goiY.doiTuong
    ? luaChon.findIndex(l => l.doi_tuong === goiY.doiTuong && l.ket_qua === "da_lien_he")
    : -1;
  $("lhLuaChon").innerHTML = luaChon.map((l, i) => `
    <label class="radio-item">
      <input type="radio" name="ketQuaLienHe" value="${i}" ${i === macDinh ? "checked" : ""}>
      <span>${escapeHtml(l.nhan)}</span>
    </label>`).join("");
  state.luaChonLienHe = luaChon;
  $("lhGhiChu").value = "";
  $("formLienHe").hidden = laQuanLyXem();

  moModal("modalLienHe");
  taiLichSuLienHe(don);
}

const TEN_KET_QUA = {
  "nguoi_nhan:da_lien_he": "Đã báo được người nhận",
  "nguoi_nhan:khong_lien_he_duoc": "Gọi người nhận không được",
  "nguoi_gui:da_lien_he": "Đã liên hệ người gửi",
  "nguoi_gui:khong_lien_he_duoc": "Gọi người gửi không được",
  "quan_ly:da_bao_quan_ly": "Đã báo quản lý",
};

async function taiLichSuLienHe(don) {
  const ul = $("lhLichSu");
  timelineTrong(ul, "Đang tải...");
  let ds;
  try {
    ds = await apiGet(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/lich-su-lien-he`);
  } catch (err) {
    timelineTrong(ul, `Không tải được lịch sử: ${err.message}`);
    return;
  }
  if (state.donDangLienHe !== don) return;
  if (!ds.length) {
    timelineTrong(ul, "Chưa có lần liên hệ nào được ghi lại.");
    return;
  }
  veTimeline(ul, ds, ls => ({
    gio: dinhDangThoiGian(ls.ngay_tao),
    tieuDe: `${TEN_KET_QUA[`${ls.doi_tuong}:${ls.ket_qua}`] || ls.ket_qua}${ls.ten_nhan_vien ? ` — ${ls.ten_nhan_vien}` : ""}`,
    ghiChu: ls.ghi_chu || "",
  }));
}

async function luuKetQuaLienHe(e) {
  e.preventDefault();
  const don = state.donDangLienHe;
  const chon = document.querySelector('input[name="ketQuaLienHe"]:checked');
  if (!don || !chon) {
    showToast("warning", "Chưa chọn kết quả", "Chọn kết quả của lần liên hệ.");
    return;
  }
  const lc = state.luaChonLienHe[Number(chon.value)];
  const ghiChu = $("lhGhiChu").value.trim();
  if (lc.doi_tuong === "nguoi_gui" && lc.ket_qua === "da_lien_he" && !ghiChu) {
    showToast("warning", "Thiếu hướng xử lý", "Ghi lại hướng xử lý đã thỏa thuận với người gửi.");
    $("lhGhiChu").focus();
    return;
  }
  const btn = $("btnLuuLienHe");
  btn.disabled = true;
  try {
    const capNhat = await apiPost(`/gui-hang/don-hang/${encodeURIComponent(don.id)}/lien-he`, {
      doi_tuong: lc.doi_tuong, ket_qua: lc.ket_qua, ghi_chu: ghiChu || null,
    });
    showToast("success", "Đã lưu kết quả liên hệ", lc.doi_tuong === "quan_ly" ? "Đã gửi thông báo tới quản lý." : "Đã ghi vào lịch sử đơn hàng.");
    state.donDangLienHe = capNhat;
    $("lhGhiChu").value = "";
    taiLichSuLienHe(capNhat);
    taiHangDen();
  } catch (err) {
    showToast("error", "Không lưu được", err.message);
  } finally {
    btn.disabled = false;
  }
}

