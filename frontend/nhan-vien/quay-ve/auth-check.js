function quayVeDangXuat() {
  ["token", "vai_tro", "ho_ten", "email"].forEach((key) => localStorage.removeItem(key));
  location.href = "/nhan-vien/dang-nhap.html";
}
function quayVeKiemTraQuyen() {
  if (!localStorage.getItem("token")) {
    location.href = "/nhan-vien/dang-nhap.html";
    return null;
  }
  if (localStorage.getItem("vai_tro") !== "nhan_vien_quay_ve") {
    qvAlert("Tài khoản không có quyền truy cập phân hệ quầy vé.","Không có quyền truy cập","danger").then(() => {
      location.href = "/nhan-vien/dang-nhap.html";
    });
    return null;
  }
  return true;
}
