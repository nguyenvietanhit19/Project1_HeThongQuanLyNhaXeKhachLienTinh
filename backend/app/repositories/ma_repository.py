"""Lấy số thứ tự cho mã tự sinh (xem utils/ma_tu_sinh.py) — dùng chung cho các repository, chạy TRONG giao dịch của lệnh INSERT.

Số lấy từ sequence của Postgres nên hai người thêm cùng lúc không bao giờ nhận trùng số, và số đã cấp không bao giờ được dùng lại
(kể cả khi giao dịch sau đó bị hủy). Riêng điểm đón/trả đếm theo từng khu vực: UPDATE ... RETURNING khóa dòng khu_vuc nên hai người
cùng thêm điểm vào 1 khu vực được xếp hàng.
"""

import psycopg2.errors

# Chỉ nhận các sequence đã biết (tên ghép thẳng vào câu SQL, không để chuỗi tùy ý lọt vào)
_SEQUENCE = {"khu_vuc": "seq_ma_khu_vuc", "tuyen": "seq_ma_tuyen", "loai_xe": "seq_ma_loai_xe", "ve": "ve_ma_seq"}


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
