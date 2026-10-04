/*
 * Kiểm tra + chuẩn hóa số điện thoại Việt Nam ở phía giao diện (báo lỗi sớm, trước khi gọi server).
 *
 * QUAN TRỌNG: quy tắc phải khớp 100% với backend/app/utils/so_dien_thoai.py — sửa 1 bên phải sửa bên kia.
 * Backend vẫn kiểm tra lại, đây chỉ để người dùng thấy lỗi ngay.
 *
 *   kiemTraSoDienThoai("091 234 5678") -> { hopLe: true, soChuan: "0912345678", loi: "" }
 *   kiemTraSoDienThoai("abc")          -> { hopLe: false, soChuan: "", loi: "Số điện thoại không hợp lệ — …" }
 */
function kiemTraSoDienThoai(so) {
  let gon = String(so ?? "").replace(/[\s.\-()]/g, "");
  if (!gon) return { hopLe: false, soChuan: "", loi: "Vui lòng nhập số điện thoại" };
  if (gon.startsWith("+84")) gon = "0" + gon.slice(3);
  else if (gon.startsWith("84") && (gon.length === 11 || gon.length === 12)) gon = "0" + gon.slice(2);
  if (!(/^0[35789]\d{8}$/.test(gon) || /^02\d{9}$/.test(gon))) {
    return { hopLe: false, soChuan: "", loi: "Số điện thoại không hợp lệ — nhập số di động 10 chữ số, VD 0912345678" };
  }
  return { hopLe: true, soChuan: gon, loi: "" };
}
