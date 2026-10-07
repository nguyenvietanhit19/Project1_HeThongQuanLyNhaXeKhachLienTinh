"""Raw SQL cho loai_xe (UC-32, DATABASE.md mục 3.1) và xe (UC-34, mục 3.2).
Không chứa quy tắc nghiệp vụ — việc đó thuộc services/xe_service.py
(ARCHITECTURE.md mục 2).
"""

import json

from app.db import get_connection, release_connection
from app.repositories import ma_repository
from app.utils import ma_tu_sinh


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


# ---------------------------------------------------------
# Loại xe (UC-32)
# ---------------------------------------------------------
def tao_loai_xe(ten: str, he_so_gia, so_do_ghe: list[dict]) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ma = ma_tu_sinh.ma_loai_xe(ma_repository.so_tiep_theo(cur, "loai_xe"))
            cur.execute(
                """
                INSERT INTO loai_xe (ma, ten, he_so_gia, so_do_ghe)
                VALUES (%s, %s, %s, %s)
                RETURNING id, ma, ten, he_so_gia, so_do_ghe
                """,
                (ma, ten, he_so_gia, json.dumps(so_do_ghe)),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua_loai_xe(loai_xe_id: str, ten: str, he_so_gia, so_do_ghe: list[dict]) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE loai_xe SET ten = %s, he_so_gia = %s, so_do_ghe = %s WHERE id = %s",
                (ten, he_so_gia, json.dumps(so_do_ghe), loai_xe_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tim_loai_xe_theo_id(loai_xe_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ma, ten, he_so_gia, so_do_ghe FROM loai_xe WHERE id = %s", (loai_xe_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_loai_xe() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ma, ten, he_so_gia, so_do_ghe FROM loai_xe ORDER BY ten")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_loai_xe(loai_xe_id: str) -> None:
    """Có thể ném psycopg2.errors.ForeignKeyViolation nếu còn xe đang dùng
    loại này — service.py bắt lỗi này để báo thông báo thân thiện."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM loai_xe WHERE id = %s", (loai_xe_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Xe (UC-34)
# ---------------------------------------------------------
_SELECT_XE = """
    SELECT x.id, x.bien_so, x.loai_xe_id, lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, x.trang_thai,
           x.diem_goc_id, d.ma AS ma_diem_goc, d.ten AS ten_diem_goc, x.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen,
           (SELECT count(*) FROM xe_nhan_su xn JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
             WHERE xn.xe_id = x.id AND xn.loai = 'co_dinh' AND n.chuc_danh = 'tai_xe') AS so_tai_xe_co_dinh,
           (SELECT count(*) FROM xe_nhan_su xn JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
             WHERE xn.xe_id = x.id AND xn.loai = 'co_dinh' AND n.chuc_danh = 'phu_xe') AS so_phu_xe_co_dinh
    FROM xe x
    JOIN loai_xe lx ON lx.id = x.loai_xe_id
    JOIN diem_don_tra d ON d.id = x.diem_goc_id
    LEFT JOIN tuyen t ON t.id = x.tuyen_id
"""


def tao_xe(bien_so: str, loai_xe_id: str, diem_goc_id: str, tuyen_id: str | None, trang_thai: str) -> str:
    """Có thể ném UniqueViolation nếu trùng biển số — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO xe (bien_so, loai_xe_id, diem_goc_id, tuyen_id, trang_thai)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (bien_so, loai_xe_id, diem_goc_id, tuyen_id, trang_thai),
            )
            xe_id = cur.fetchone()[0]
        conn.commit()
        return xe_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua_xe(xe_id: str, bien_so: str, loai_xe_id: str, diem_goc_id: str, tuyen_id: str | None, trang_thai: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE xe SET bien_so = %s, loai_xe_id = %s, diem_goc_id = %s, tuyen_id = %s, trang_thai = %s
                WHERE id = %s
                """,
                (bien_so, loai_xe_id, diem_goc_id, tuyen_id, trang_thai, xe_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tim_xe_theo_id(xe_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_XE + " WHERE x.id = %s", (xe_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_xe() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_XE + " ORDER BY x.bien_so")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_xe(xe_id: str) -> None:
    """Có thể ném ForeignKeyViolation nếu xe đã có chuyến/biên chế — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM xe WHERE id = %s", (xe_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def dem_chuyen_chua_xong_cua_xe(xe_id: str) -> int:
    """Số chuyến chưa kết thúc mà xe này đang là xe gốc hoặc xe chạy thực tế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM chuyen_xe
                WHERE (xe_id = %s OR xe_thuc_te_id = %s)
                  AND trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co')
                """,
                (xe_id, xe_id),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def dem_chuyen_dang_chay_thay(xe_id: str) -> int:
    """Số chuyến chưa xong của xe gốc này đang được xe khác chạy thay (xe_thuc_te_id) — UC-34/UC-40."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM chuyen_xe
                WHERE xe_id = %s AND xe_thuc_te_id IS NOT NULL
                  AND trang_thai IN ('chua_khoi_hanh', 'dang_chay')
                """,
                (xe_id,),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)
