"""Vòng đời vé — phần dùng bởi phụ xe (UC-12, UC-13), NGHIEP_VU.md mục 5/8.2.

Giữ ghế/chống trùng ghế/thanh toán (mục 3.4, 6) thuộc phần khách hàng +
quầy vé, chưa cài đặt ở đây.
"""

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
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
    """UC-12 — tiền điều kiện: chuyến `dang_chay`, vé `da_thanh_toan`."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến chưa xuất phát hoặc đã kết thúc, không thể xác nhận khách lên xe")
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_thanh_toan":
        raise GiaTriLoi("Vé không hợp lệ để lên xe (chưa thanh toán hoặc đã xử lý)")

    ve_repo.xac_nhan_len_xe(ve_id)


def xac_nhan_xuong_xe(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    """UC-13 — tiền điều kiện: vé `da_len_xe`, xe đã tới đúng điểm trả của vé.

    Chấp nhận cả chuyến `hoan_thanh`: xác nhận đến điểm cuối chuyển chuyến
    sang hoan_thanh, nhưng khách xuống tại điểm cuối vẫn cần được xác nhận
    ngay sau đó (cùng lý do với khach_tai_diem_hien_tai)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái đang chạy, không thể xác nhận khách xuống xe")
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Vé chưa lên xe, không thể xác nhận xuống xe")

    da_toi = {d["diem_don_tra_id"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}
    if ve["diem_tra_id"] not in da_toi:
        raise GiaTriLoi("Xe chưa tới điểm trả của vé này")

    ve_repo.xac_nhan_xuong_xe(ve_id)
