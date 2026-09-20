/*
 * Danh sách 34 đơn vị hành chính cấp tỉnh của Việt Nam sau sáp nhập, hiệu
 * lực từ 01/07/2025 (Nghị quyết 202/2025/QH15) — 28 tỉnh + 6 thành phố
 * trực thuộc trung ương. Riêng cho các trang Quản lý — dùng cho ô chọn
 * tỉnh/thành ở trang Khu vực (UC-29), và hienThiTinhThanh() dùng khi hiển
 * thị khu vực kèm tỉnh/thành ở nơi khác (VD ô chọn khu vực ở trang Điểm
 * đón/trả, UC-30).
 *
 * QUAN TRỌNG: danh sách này phải khớp 100% với
 * backend/app/utils/tinh_thanh.py — sửa 1 bên phải sửa bên kia. Backend
 * vẫn validate lại (Pydantic Literal), danh sách này chỉ phục vụ UI
 * (gợi ý + chặn nhập tự do phía client).
 */

const DANH_SACH_THANH_PHO_TW = [
  "Hà Nội",
  "Hải Phòng",
  "Đà Nẵng",
  "Thành phố Hồ Chí Minh",
  "Cần Thơ",
  "Huế",
];

const DANH_SACH_TINH = [
  "Cao Bằng",
  "Điện Biên",
  "Hà Tĩnh",
  "Lai Châu",
  "Lạng Sơn",
  "Nghệ An",
  "Quảng Ninh",
  "Thanh Hóa",
  "Sơn La",
  "Tuyên Quang",
  "Lào Cai",
  "Thái Nguyên",
  "Phú Thọ",
  "Bắc Ninh",
  "Hưng Yên",
  "Ninh Bình",
  "Quảng Trị",
  "Quảng Ngãi",
  "Gia Lai",
  "Khánh Hòa",
  "Lâm Đồng",
  "Đắk Lắk",
  "Đồng Nai",
  "Tây Ninh",
  "Vĩnh Long",
  "Đồng Tháp",
  "Cà Mau",
  "An Giang",
];

const DANH_SACH_TINH_THANH = [...DANH_SACH_THANH_PHO_TW, ...DANH_SACH_TINH];

/** "Nghệ An" -> "tỉnh Nghệ An", "Hà Nội" -> "Hà Nội" (thành phố trực thuộc
 * trung ương đã có tên riêng đủ rõ, không cần thêm tiền tố) — dùng khi
 * hiển thị khu vực kèm tỉnh/thành cho dễ phân biệt, VD "TP Vinh (tỉnh Nghệ An)". */
function hienThiTinhThanh(tinh_thanh) {
  return DANH_SACH_TINH.includes(tinh_thanh) ? `tỉnh ${tinh_thanh}` : tinh_thanh;
}

/** Gắn <datalist> gợi ý tỉnh/thành vào 1 <input list="..."> có sẵn —
 * cho phép gõ để lọc hoặc mở dropdown chọn, nhưng KHÔNG cho nhập tự do:
 * gọi kemTimKiemTinhThanh(inputEl) lúc khởi tạo trang, rồi kiemTraHopLe()
 * lúc submit để chặn giá trị không khớp danh sách. */
function kemTimKiemTinhThanh(inputEl) {
  const datalistId = `${inputEl.id}-goi-y`;
  const datalist = document.createElement("datalist");
  datalist.id = datalistId;
  datalist.innerHTML = DANH_SACH_TINH_THANH.map((t) => `<option value="${t}"></option>`).join("");
  inputEl.after(datalist);
  inputEl.setAttribute("list", datalistId);
  inputEl.setAttribute("autocomplete", "off");
}

function laTinhThanhHopLe(gia_tri) {
  return DANH_SACH_TINH_THANH.includes(gia_tri);
}
