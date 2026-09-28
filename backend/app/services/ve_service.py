"""Vòng đời vé — phần dùng bởi phụ xe (UC-12, UC-13), NGHIEP_VU.md mục 5/8.2.

Giữ ghế/chống trùng ghế/thanh toán (mục 3.4, 6) thuộc phần khách hàng +
quầy vé, chưa cài đặt ở đây.
"""

from app.repositories import ve_repository as ve_repo
from app.services.chuyen_xe_service import lay_chuyen_cua_phu_xe
from app.utils.loi import GiaTriLoi


def _lay_ve_cua_chuyen(ve_id: str, chuyen_id: str) -> dict:
    ve = ve_repo.tim_theo_id(ve_id)
    if not ve:
        raise GiaTriLoi("Không tìm thấy vé")
    if ve["chuyen_id"] != chuyen_id:
        raise GiaTriLoi("Vé không thuộc chuyến này")
    return ve


def xac_nhan_len_xe(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_thanh_toan":
        raise GiaTriLoi("Vé không hợp lệ để lên xe (chưa thanh toán hoặc đã xử lý)")

    ve_repo.xac_nhan_len_xe(ve_id)


def xac_nhan_xuong_xe(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Vé chưa lên xe, không thể xác nhận xuống xe")

    ve_repo.xac_nhan_xuong_xe(ve_id)
