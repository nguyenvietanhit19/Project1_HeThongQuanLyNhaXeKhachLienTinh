"""Lấy số thứ tự cho mã tự sinh (xem utils/ma_tu_sinh.py) — dùng chung cho các repository, chạy TRONG giao dịch của lệnh INSERT.

Số lấy từ sequence của Postgres nên hai người thêm cùng lúc không bao giờ nhận trùng số, và số đã cấp không bao giờ được dùng lại
(kể cả khi giao dịch sau đó bị hủy). Riêng điểm đón/trả đếm theo từng khu vực: UPDATE ... RETURNING khóa dòng khu_vuc nên hai người
cùng thêm điểm vào 1 khu vực được xếp hàng.
"""

import psycopg2.errors

from app.utils import ma_tu_sinh

# Chỉ nhận các sequence đã biết (tên ghép thẳng vào câu SQL, không để chuỗi tùy ý lọt vào)
_SEQUENCE = {"khu_vuc": "seq_ma_khu_vuc", "tuyen": "seq_ma_tuyen", "loai_xe": "seq_ma_loai_xe", "ve": "ve_ma_seq"}


# Sequence mã nhân viên (migration 20261105_0900_ma_nhan_vien.sql) — khóa là vai trò / "tai_xe", mỗi vai trò đếm riêng.
_SEQUENCE.update(
    {
        "tai_xe": "seq_ma_tai_xe",
        "phu_xe": "seq_ma_phu_xe",
        "nhan_vien_quay_ve": "seq_ma_quay_ve",
        "nhan_vien_gui_hang": "seq_ma_gui_hang",
        "dieu_do_vien": "seq_ma_dieu_do_vien",
        "ke_toan": "seq_ma_ke_toan",
        "quan_ly_nhan_su": "seq_ma_quan_ly_nhan_su",
        "quan_ly": "seq_ma_quan_ly",
    }
)


def so_tiep_theo(cur, loai: str) -> int:
    cur.execute(f"SELECT nextval('{_SEQUENCE[loai]}')")
    return cur.fetchone()[0]


def cap_so_diem_trong_khu_vuc(cur, khu_vuc_id: str) -> tuple[str, int]:
    """Cấp số điểm kế tiếp của khu vực → (mã khu vực, số thứ tự)."""
    cur.execute(
        "UPDATE khu_vuc SET so_diem_da_cap = so_diem_da_cap + 1 WHERE id = %s RETURNING ma, so_diem_da_cap",
        (khu_vuc_id,),
    )
    dong = cur.fetchone()
    if dong is None:
        raise psycopg2.errors.ForeignKeyViolation(f"Khu vực {khu_vuc_id} không tồn tại")
    return dong[0], dong[1]


def lay_ma_tuyen_va_loai_xe(cur, tuyen_id: str, loai_xe_id: str) -> tuple[str, str]:
    """Mã tuyến + mã loại xe để dựng mã chuyến."""
    cur.execute(
        "SELECT (SELECT ma FROM tuyen WHERE id = %s), (SELECT ma FROM loai_xe WHERE id = %s)",
        (tuyen_id, loai_xe_id),
    )
    ma_tuyen, ma_loai_xe = cur.fetchone()
    if ma_tuyen is None or ma_loai_xe is None:
        raise psycopg2.errors.ForeignKeyViolation("Tuyến hoặc loại xe của chuyến không tồn tại")
    return ma_tuyen, ma_loai_xe


def cap_ma_nhan_vien(cur, vai_tro: str) -> str:
    """Cấp mã nhân viên kế tiếp của `vai_tro` (hoặc "tai_xe" cho hồ sơ tài xế), VD "PX0007".

    Gọi TRONG giao dịch của lệnh INSERT rồi điền vào cột `ma` (xem tai_khoan_can_bo_repository, nhan_su_van_hanh_repository).
    Vai trò không có mã (khách hàng...) bị từ chối TRƯỚC khi lấy số, để không làm mất số của sequence."""
    if vai_tro not in ma_tu_sinh.TIEN_TO_NHAN_VIEN:
        raise ValueError(f"Vai trò '{vai_tro}' không có mã nhân viên")
    return ma_tu_sinh.ma_nhan_vien(vai_tro, so_tiep_theo(cur, vai_tro))
