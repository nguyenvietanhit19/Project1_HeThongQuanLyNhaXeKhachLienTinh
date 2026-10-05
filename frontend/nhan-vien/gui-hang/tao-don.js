/* tao-don.js — tab Tiếp nhận gửi hàng tại quầy: chọn lộ trình, báo giá, tạo đơn. */

async function taiLoaiHang() {
  const select = $("loai_hang_id");
  try {
    state.loaiHang = await apiGet("/gui-hang/loai-hang");
    const hopLe = state.loaiHang.filter(l => !l.la_hang_cam);
    const cam = state.loaiHang.filter(l => l.la_hang_cam);
    const opt = l => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.ten)}</option>`;
    // Hàng cấm vẫn hiện để nhân viên đối chiếu với món khách mang tới, nhưng không chọn được:
    // chọn vào cũng chỉ để bị từ chối. BE vẫn chặn lại nếu ai gọi API trực tiếp.
    const optCam = l => `<option value="${escapeHtml(l.id)}" disabled>${escapeHtml(l.ten)}</option>`;
    select.innerHTML = '<option value="">-- Chọn loại hàng hóa --</option>'
      + hopLe.map(opt).join("")
      + (cam.length ? `<optgroup label="⛔ Hàng cấm — từ chối tiếp nhận (không chọn được)">${cam.map(optCam).join("")}</optgroup>` : "");
  } catch (err) {
    select.innerHTML = '<option value="">⚠️ Không tải được danh mục</option>';
    showToast("error", "Lỗi tải loại hàng", err.message);
  }
}

function xuLyChonLoaiHang() {
  const loai = state.loaiHang.find(l => l.id === $("loai_hang_id").value);
  const canhBao = $("canhBaoHangCam");
  const laCam = Boolean(loai && loai.la_hang_cam);
  canhBao.hidden = !laCam;
  canhBao.textContent = laCam
    ? `⛔ "${loai.ten}" thuộc danh mục hàng cấm vận chuyển — TỪ CHỐI tiếp nhận đơn này.`
    : "";
  $("btnTaoDon").disabled = laCam;
}

async function taiDiemNhanKhaDung() {
  const selectKv = $("khu_vuc_den");
  try {
    state.diemNhan = await apiGet("/gui-hang/diem-nhan-kha-dung");
    if (!state.diemNhan.length) {
      selectKv.innerHTML = '<option value="">⚠️ Chưa có tuyến nào nối văn phòng này với văn phòng khác</option>';
      return;
    }
    selectKv.innerHTML = '<option value="">-- Chọn khu vực đến --</option>' + state.diemNhan
      .map(kv => `<option value="${escapeHtml(kv.khu_vuc_id)}">${escapeHtml(kv.ten_khu_vuc)}${kv.tinh_thanh ? ` (${escapeHtml(kv.tinh_thanh)})` : ""}</option>`)
      .join("");
  } catch (err) {
    selectKv.innerHTML = '<option value="">⚠️ Không tải được điểm đến</option>';
    showToast("error", "Lỗi tải điểm đến", err.message);
  }
}

function datLaiChonTuyen(thongDiep) {
  const selectTuyen = $("tuyen_id");
  selectTuyen.innerHTML = `<option value="">${escapeHtml(thongDiep)}</option>`;
  selectTuyen.disabled = true;
}

function xuLyChonKhuVuc() {
  const kv = state.diemNhan.find(k => k.khu_vuc_id === $("khu_vuc_den").value);
  const selectVp = $("diem_nhan_id");
  datLaiChonTuyen("-- Chọn văn phòng nhận trước --");
  if (!kv) {
    selectVp.innerHTML = '<option value="">-- Chọn khu vực trước --</option>';
    selectVp.disabled = true;
    return;
  }
  selectVp.innerHTML = '<option value="">-- Chọn văn phòng nhận --</option>' + kv.van_phong
    .map(vp => `<option value="${escapeHtml(vp.id)}">${escapeHtml(vp.ten)}${vp.dia_chi ? ` — ${escapeHtml(vp.dia_chi)}` : ""}</option>`)
    .join("");
  selectVp.disabled = false;
}

async function xuLyChonVanPhongNhan() {
  const diemNhanId = $("diem_nhan_id").value;
  if (!diemNhanId) {
    datLaiChonTuyen("-- Chọn văn phòng nhận trước --");
    return;
  }
  const phien = ++state.phienTuyen;
  datLaiChonTuyen("Đang tìm tuyến...");
  try {
    const tuyen = await apiGet(`/gui-hang/tuyen-phu-hop${taoQuery({ diem_nhan_id: diemNhanId })}`);
    if (phien !== state.phienTuyen) return; // đã đổi văn phòng khác trong lúc chờ
    const selectTuyen = $("tuyen_id");
    if (!tuyen.length) {
      datLaiChonTuyen("⚠️ Không có tuyến nào nối 2 văn phòng — từ chối nhận");
      showToast("warning", "Không có tuyến phù hợp", "Chưa có tuyến nào đi qua văn phòng gửi và văn phòng nhận đã chọn.");
      return;
    }
    const opt = t => `<option value="${escapeHtml(t.id)}">${escapeHtml(t.ma ? `[${t.ma}] ${t.ten}` : t.ten)}</option>`;
    selectTuyen.innerHTML = (tuyen.length > 1 ? '<option value="">-- Có nhiều tuyến, chọn 1 tuyến --</option>' : "")
      + tuyen.map(opt).join("");
    selectTuyen.disabled = false;
  } catch (err) {
    if (phien !== state.phienTuyen) return;
    datLaiChonTuyen("⚠️ Không tải được tuyến");
    showToast("error", "Lỗi tìm tuyến", err.message);
  }
}

function capNhatXacNhanThuTruoc() {
  const traTruoc = document.querySelector('input[name="phuong_thuc_thanh_toan"]:checked')?.value === "nguoi_gui_tra_truoc";
  $("xacNhanThuTruocWrap").hidden = !traTruoc;
  if (!traTruoc) $("xacNhanDaThuTruoc").checked = false;
}

// Gợi ý khách quen: gõ đủ SĐT → lấy các tên từng đi kèm SĐT này ở đơn của văn phòng.
const CAU_HINH_GOI_Y = {
  gui: { sdt: "sdt_nguoi_gui", ten: "ten_nguoi_gui", danhSach: "goiYTenGui" },
  nhan: { sdt: "sdt_nguoi_nhan", ten: "ten_nguoi_nhan", danhSach: "goiYTenNhan" },
};
const henGioGoiY = { gui: null, nhan: null };

async function goiYKhach(vaiTro) {
  if (laQuanLyXem()) return;
  const cfg = CAU_HINH_GOI_Y[vaiTro];
  const form = $("formTaoDon");
  const sdt = form.elements[cfg.sdt].value.trim();
  const danhSach = $(cfg.danhSach);
  danhSach.replaceChildren();
  if (!/^[0-9]{10,11}$/.test(sdt)) return;

  const phien = ++state.phienGoiY[vaiTro];
  let ds;
  try {
    ds = await apiGet(`/gui-hang/goi-y-khach${taoQuery({ sdt, vai_tro: vaiTro })}`);
  } catch (_) {
    return; // gợi ý chỉ là tiện ích — lỗi thì nhân viên cứ nhập tay
  }
  // Bỏ kết quả cũ nếu nhân viên đã sửa SĐT hoặc gõ SĐT khác trong lúc chờ.
  if (phien !== state.phienGoiY[vaiTro] || form.elements[cfg.sdt].value.trim() !== sdt) return;

  danhSach.replaceChildren(...ds.map(g => {
    const o = document.createElement("option");
    o.value = g.ten;
    o.label = `${g.so_don} đơn, gần nhất ${dinhDangNgay(g.lan_cuoi)}`;
    return o;
  }));
  const oTen = form.elements[cfg.ten];
  if (ds.length && !oTen.value.trim()) oTen.value = ds[0].ten;
}

function henGioGoiYKhach(vaiTro) {
  clearTimeout(henGioGoiY[vaiTro]);
  henGioGoiY[vaiTro] = setTimeout(() => goiYKhach(vaiTro), 300);
}

function docSoDuong(id) {
  const v = $(id).value.trim();
  return v === "" ? null : Number(v);
}

function thuThapDuLieuTaoDon() {
  const form = $("formTaoDon");
  const sdtRegex = /^[0-9]{10,11}$/;
  const ten = n => form.elements[n].value.trim();
  const sdt = n => form.elements[n].value.trim();

  const loi = (msg, el) => {
    showToast("warning", "Thiếu / sai thông tin", msg);
    el?.focus();
    return null;
  };

  if (!ten("ten_nguoi_gui")) return loi("Nhập họ tên người gửi.", form.elements.ten_nguoi_gui);
  if (!sdtRegex.test(sdt("sdt_nguoi_gui"))) return loi("SĐT người gửi phải gồm 10-11 chữ số.", form.elements.sdt_nguoi_gui);
  if (!ten("ten_nguoi_nhan")) return loi("Nhập họ tên người nhận.", form.elements.ten_nguoi_nhan);
  if (!sdtRegex.test(sdt("sdt_nguoi_nhan"))) return loi("SĐT người nhận phải gồm 10-11 chữ số.", form.elements.sdt_nguoi_nhan);
  if (!$("diem_nhan_id").value) return loi("Chọn khu vực đến và văn phòng nhận.", $("khu_vuc_den"));
  if (!$("tuyen_id").value) return loi("Chọn tuyến vận chuyển.", $("tuyen_id"));

  const loai = state.loaiHang.find(l => l.id === $("loai_hang_id").value);
  if (!loai) return loi("Chọn loại hàng hóa.", $("loai_hang_id"));
  if (loai.la_hang_cam) return loi(`"${loai.ten}" là hàng cấm — từ chối tiếp nhận.`, $("loai_hang_id"));

  const canNang = docSoDuong("can_nang_kg");
  if (!canNang || canNang <= 0) return loi("Nhập cân nặng thực tế (kg).", $("can_nang_kg"));
  for (const id of ["dai_cm", "rong_cm", "cao_cm"]) {
    const v = docSoDuong(id);
    if (v !== null && v <= 0) return loi("Kích thước phải lớn hơn 0.", $(id));
  }

  const giaCuoc = parseInt($("gia_cuoc").value, 10);
  if (isNaN(giaCuoc) || giaCuoc < 1000) return loi("Nhập cước vận chuyển (tối thiểu 1.000 đ).", $("gia_cuoc"));

  const phuongThuc = form.elements.phuong_thuc_thanh_toan.value;
  const daThu = $("xacNhanDaThuTruoc").checked;
  if (phuongThuc === "nguoi_gui_tra_truoc" && !daThu) {
    return loi("Xác nhận đã thu đủ cước từ người gửi tại quầy.", $("xacNhanDaThuTruoc"));
  }

  const optVp = $("diem_nhan_id").selectedOptions[0];
  return {
    body: {
      tuyen_id: $("tuyen_id").value,
      diem_gui_id: state.vanPhong.id,
      diem_nhan_id: $("diem_nhan_id").value,
      loai_hang_id: loai.id,
      can_nang_kg: canNang,
      dai_cm: docSoDuong("dai_cm"),
      rong_cm: docSoDuong("rong_cm"),
      cao_cm: docSoDuong("cao_cm"),
      gia_cuoc: giaCuoc,
      ten_nguoi_gui: ten("ten_nguoi_gui"),
      sdt_nguoi_gui: sdt("sdt_nguoi_gui"),
      ten_nguoi_nhan: ten("ten_nguoi_nhan"),
      sdt_nguoi_nhan: sdt("sdt_nguoi_nhan"),
      phuong_thuc_thanh_toan: phuongThuc,
      xac_nhan_da_thu: phuongThuc === "nguoi_gui_tra_truoc" && daThu,
    },
    hienThi: {
      vanPhongNhan: optVp ? optVp.textContent : "",
      tuyen: $("tuyen_id").selectedOptions[0]?.textContent || "",
      loaiHang: loai.ten,
    },
  };
}

function xuLyGuiFormTaoDon(e) {
  e.preventDefault();
  if (state.dangTaoDon) return;
  const duLieu = thuThapDuLieuTaoDon();
  if (!duLieu) return;
  state.duLieuTaoDon = duLieu;

  const b = duLieu.body;
  const dong = (nhan, giaTri) => `<div class="receipt-row"><span>${nhan}</span><strong>${escapeHtml(giaTri)}</strong></div>`;
  $("xnNoiDung").innerHTML = `
    ${dong("Người gửi:", `${b.ten_nguoi_gui} — ${b.sdt_nguoi_gui}`)}
    ${dong("Người nhận:", `${b.ten_nguoi_nhan} — ${b.sdt_nguoi_nhan}`)}
    ${dong("Văn phòng nhận:", duLieu.hienThi.vanPhongNhan)}
    ${dong("Tuyến:", duLieu.hienThi.tuyen)}
    ${dong("Hàng hóa:", `${duLieu.hienThi.loaiHang} — ${dinhDangKg(b.can_nang_kg)}`)}
    ${dong("Hình thức:", laCod(b) ? "COD — người nhận trả khi lấy hàng" : "Người gửi trả trước (đã thu tại quầy)")}
    <div class="receipt-row total"><span>CƯỚC VẬN CHUYỂN:</span><span>${escapeHtml(dinhDangTien(b.gia_cuoc))}</span></div>
    <p class="card-desc">Đọc lại thông tin và cước cho khách. Chỉ bấm tạo đơn khi khách đã đồng ý.</p>`;
  moModal("modalXacNhanTaoDon");
}

async function xacNhanTaoDon() {
  if (state.dangTaoDon || !state.duLieuTaoDon) return;
  state.dangTaoDon = true;
  const btn = $("btnXacNhanTaoDon");
  btn.disabled = true;
  try {
    // Cùng nội dung → cùng khóa: bấm 2 lần / gửi lại sau lỗi mạng chỉ tạo 1 đơn.
    const json = JSON.stringify(state.duLieuTaoDon.body);
    if (!state.khoaTaoDon || state.khoaTaoDon.json !== json) {
      state.khoaTaoDon = { json, khoa: taoKhoaNgauNhien() };
    }
    const don = await apiPost("/gui-hang/tao-don", state.duLieuTaoDon.body, { "Idempotency-Key": state.khoaTaoDon.khoa });
    state.khoaTaoDon = null;
    dongModal("modalXacNhanTaoDon");
    datLaiFormTaoDon();
    showToast("success", "Tạo đơn thành công", `Đơn ${don.ma_van_don} đã được tiếp nhận.`);
    hienThiBienNhan(don);
    capNhatSoDonHomNay();
  } catch (err) {
    showToast("error", "Không tạo được đơn", err.message);
  } finally {
    state.dangTaoDon = false;
    btn.disabled = false;
  }
}

function datLaiFormTaoDon() {
  $("formTaoDon").reset();
  state.duLieuTaoDon = null;
  state.khoaTaoDon = null;
  $("goiYTenGui").replaceChildren();
  $("goiYTenNhan").replaceChildren();
  $("diem_nhan_id").innerHTML = '<option value="">-- Chọn khu vực trước --</option>';
  $("diem_nhan_id").disabled = true;
  datLaiChonTuyen("-- Chọn văn phòng nhận trước --");
  xuLyChonLoaiHang();
  capNhatXacNhanThuTruoc();
}

async function capNhatSoDonHomNay() {
  if (laQuanLyXem()) return;
  try {
    const homNay = ngayISO(new Date());
    const tk = await apiGet(`/gui-hang/thong-ke${taoQuery({ tu_ngay: homNay, den_ngay: homNay })}`);
    datText("stat-tao-don-count", tk.tong_don_gui_di);
  } catch (_) {}
}

