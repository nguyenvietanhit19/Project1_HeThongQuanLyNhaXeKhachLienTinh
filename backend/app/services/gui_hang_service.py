"""Gửi hàng — phần dùng bởi phụ xe (UC-26, UC-27, UC-28), NGHIEP_VU.md mục 10.2/8.2.

Tạo đơn tại quầy gửi (UC-23), giao hàng cho người nhận (UC-24), xử lý hàng
tồn (UC-25) thuộc nhân viên gửi hàng — đã có sẵn ở `don_hang_repository.py`
(Trinh, UC-21/22, #6). File này chỉ gọi vào các hàm sẵn có của repository
đó cho đúng 3 UC của phụ xe, không tự viết SQL riêng (CONTRIBUTING.md).
"""

from app.repositories import bao_cao_su_co_hang_repository as bao_cao_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.services.chuyen_xe_service import diem_hien_tai, lay_chuyen_cua_phu_xe
from app.utils.loi import GiaTriLoi


def danh_sach_cho_chat(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """NGHIEP_VU.md mục 10.2 — đơn đang chờ, cùng tuyến, cùng điểm với
    điểm phụ xe đang đứng trên chính chuyến này.

    `don_hang_repo.lay_danh_sach_cho_xep_xe(tuyen_id)` chỉ lọc theo tuyến,
    chưa lọc theo điểm gửi cụ thể — lọc thêm ở đây (Python) thay vì sửa
    lại file của Trinh, vì đây là hành vi CHỈ phụ xe cần (mục 10.2: "đơn
    đang cho_van_chuyen, còn chờ TẠI ĐIỂM ĐANG ĐỨNG", không phải mọi đơn
    trên cả tuyến)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để chất hàng")

    diem = diem_hien_tai(chuyen)
    don_hang_ca_tuyen = don_hang_repo.lay_danh_sach_cho_xep_xe(chuyen["tuyen_id"])
    don_hang_tai_diem = [d for d in don_hang_ca_tuyen if d["diem_gui_id"] == diem["diem_don_tra_id"]]

    # lay_danh_sach_cho_xep_xe() không kèm tên điểm nhận (chỉ có id) —
    # giao diện phụ xe cần hiển thị "đến <tên điểm>" (mục 8.2), bổ sung ở
    # đây thay vì sửa lại query của Trinh.
    ket_qua = []
    for d in don_hang_tai_diem:
        diem_nhan = dia_diem_repo.tim_diem_don_tra_theo_id(d["diem_nhan_id"])
        ket_qua.append({**d, "ten_diem_nhan": diem_nhan["ten"] if diem_nhan else "?"})
    return ket_qua


def danh_sach_cho_do(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """NGHIEP_VU.md mục 8.2 điểm 9 — đơn đang trên xe, cần dỡ tại điểm phụ
    xe đang đứng trên chính chuyến này."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để dỡ hàng")
    # 'hoan_thanh' được phép — xác nhận đến điểm CUỐI cùng lúc chuyển
    # chuyến sang hoan_thanh (mục 8.2 điểm 8), nhưng hàng chở đến đúng
    # điểm cuối đó vẫn cần dỡ nốt (UC-27) ngay sau đó.

    diem = diem_hien_tai(chuyen)
    return don_hang_repo.tim_don_can_do_tai_diem(chuyen_id, diem["diem_don_tra_id"])


def xac_nhan_chat_hang(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str) -> None:
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)

    don_hang = don_hang_repo.tim_theo_id(don_hang_id)
    if not don_hang:
        raise GiaTriLoi("Không tìm thấy đơn hàng")
    if don_hang["trang_thai"] != "cho_van_chuyen" or don_hang["chuyen_id"] is not None:
        raise GiaTriLoi("Đơn hàng không ở trạng thái chờ chất lên chuyến")
    if don_hang["tuyen_id"] != chuyen["tuyen_id"]:
        raise GiaTriLoi("Đơn hàng không cùng tuyến với chuyến này")

    don_hang_repo.cap_nhat_chat_hang_len_chuyen(don_hang_id, chuyen_id)


def xac_nhan_do_hang(don_hang_id: str, nguoi_dung_id: str) -> None:
    don_hang = don_hang_repo.tim_theo_id(don_hang_id)
    if not don_hang:
        raise GiaTriLoi("Không tìm thấy đơn hàng")
    if not don_hang["chuyen_id"]:
        raise GiaTriLoi("Đơn hàng chưa từng được chất lên chuyến nào")

    lay_chuyen_cua_phu_xe(don_hang["chuyen_id"], nguoi_dung_id)
    if don_hang["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Đơn hàng không ở trạng thái đang trên xe")

    don_hang_repo.cap_nhat_do_hang_tai_diem(don_hang_id)


def bao_that_lac(don_hang_id: str, mo_ta: str, nguoi_dung_id: str) -> None:
    don_hang = don_hang_repo.tim_theo_id(don_hang_id)
    if not don_hang:
        raise GiaTriLoi("Không tìm thấy đơn hàng")

    bao_cao_repo.tao(don_hang_id, nguoi_dung_id, mo_ta)
