"""Vòng đời vé — phần dùng bởi phụ xe (UC-12, UC-13), NGHIEP_VU.md mục 5/8.2.

Giữ ghế/chống trùng ghế/thanh toán (mục 3.4, 6) thuộc phần khách hàng +
quầy vé, chưa cài đặt ở đây.
"""

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import ve_repository as ve_repo
from app.services.chuyen_xe_service import diem_hien_tai, lay_chuyen_cua_phu_xe
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
    # Mục 8.2 điểm 1/5: chỉ khách đón tại điểm xe ĐANG đứng mới lên được — không để khách của điểm sau lên sớm.
    if diem_hien_tai(chuyen)["diem_don_tra_id"] != ve["diem_don_id"]:
        raise GiaTriLoi("Xe không đứng ở điểm đón của vé này, chưa thể xác nhận khách lên xe")

    ve_repo.xac_nhan_len_xe(ve_id)


def len_xe_tat_ca(chuyen_id: str, diem_id: str, nguoi_dung_id: str) -> int:
    """Cho lên xe tất cả khách ĐÃ TRẢ TIỀN, đón tại điểm xe đang đứng. Trả số khách đã lên."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến chưa xuất phát hoặc đã kết thúc, không thể xác nhận khách lên xe")
    if diem_hien_tai(chuyen)["diem_don_tra_id"] != diem_id:
        raise GiaTriLoi("Xe không đứng ở điểm này, không thể cho khách lên xe")
    ve_ids = [str(v["ve_id"]) for v in ve_repo.tim_ve_can_len_xe_tai_diem(chuyen_id, diem_id)]
    return ve_repo.xac_nhan_len_xe_nhieu(ve_ids)


def xuong_xe_tat_ca(chuyen_id: str, diem_id: str, nguoi_dung_id: str) -> int:
    """Cho xuống xe tất cả khách đang trên xe có điểm trả là điểm này (xe đã tới điểm đó)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái đang chạy, không thể xác nhận khách xuống xe")
    if diem_id not in {d["diem_don_tra_id"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}:
        raise GiaTriLoi("Xe chưa tới điểm này")
    ve_ids = [str(v["ve_id"]) for v in ve_repo.tim_ve_can_xuong_xe_tai_diem(chuyen_id, diem_id)]
    return ve_repo.xac_nhan_xuong_xe_nhieu(ve_ids)


def hoan_tac_len_xe(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    """Phụ xe bấm nhầm "lên xe": đưa vé về `da_thanh_toan`. Chỉ làm được khi xe
    CÒN ĐỨNG ở điểm đón của vé — xe đã đi thì không còn biết khách có lên thật không."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến không ở trạng thái đang chạy, không thể hoàn tác")
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Vé chưa được đánh dấu lên xe, không có gì để hoàn tác")
    if diem_hien_tai(chuyen)["diem_don_tra_id"] != ve["diem_don_id"]:
        raise GiaTriLoi("Xe đã rời điểm đón của vé này, không thể hoàn tác — hãy báo điều độ viên")

    if not ve_repo.hoan_tac_len_xe(ve_id):
        raise GiaTriLoi("Vé đã được xử lý trước đó, vui lòng tải lại")


def hoan_tac_xuong_xe(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    """Phụ xe bấm nhầm "xuống xe": đưa vé về `da_len_xe`. Chỉ làm được khi xe
    còn đứng ở điểm trả của vé."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái đang chạy, không thể hoàn tác")
    ve = _lay_ve_cua_chuyen(ve_id, chuyen_id)
    if ve["trang_thai"] != "da_xuong_xe":
        raise GiaTriLoi("Vé chưa được đánh dấu xuống xe, không có gì để hoàn tác")
    if diem_hien_tai(chuyen)["diem_don_tra_id"] != ve["diem_tra_id"]:
        raise GiaTriLoi("Xe đã rời điểm trả của vé này, không thể hoàn tác — hãy báo điều độ viên")

    if not ve_repo.hoan_tac_xuong_xe(ve_id):
        raise GiaTriLoi("Vé đã được xử lý trước đó, vui lòng tải lại")


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
