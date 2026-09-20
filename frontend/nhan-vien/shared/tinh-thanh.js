/*
 * Danh sách 34 đơn vị hành chính cấp tỉnh của Việt Nam sau sáp nhập, hiệu
 * lực từ 01/07/2025 (Nghị quyết 202/2025/QH15) — 28 tỉnh + 6 thành phố
 * trực thuộc trung ương. Dùng cho ô chọn tỉnh/thành ở trang Khu vực (UC-29).
 *
 * QUAN TRỌNG: danh sách này phải khớp 100% với
 * backend/app/utils/tinh_thanh.py — sửa 1 bên phải sửa bên kia. Backend
 * vẫn validate lại (Pydantic Literal), danh sách này chỉ phục vụ UI
 * (gợi ý + chặn nhập tự do phía client).
 */

const DANH_SACH_TINH_THANH = [
  // 6 thành phố trực thuộc trung ương
  "Hà Nội",
  "Hải Phòng",
  "Đà Nẵng",
  "Thành phố Hồ Chí Minh",
  "Cần Thơ",
  "Huế",
  // 28 tỉnh
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
