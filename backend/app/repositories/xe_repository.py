"""Raw SQL cho loai_xe — DATABASE.md mục 3.1, UC-32. (Bảng `xe` cũng đã
tồn tại trong DB, sẽ bổ sung hàm CRU D cho nó ở đây khi làm tới UC-34.)
Không chứa quy tắc nghiệp vụ — việc đó thuộc services/xe_service.py
(ARCHITECTURE.md mục 2).
"""

import json

from app.db import get_connection, release_connection


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
            cur.execute(
                """
                INSERT INTO loai_xe (ten, he_so_gia, so_do_ghe)
                VALUES (%s, %s, %s)
                RETURNING id, ten, he_so_gia, so_do_ghe
                """,
                (ten, he_so_gia, json.dumps(so_do_ghe)),
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
            cur.execute("SELECT id, ten, he_so_gia, so_do_ghe FROM loai_xe WHERE id = %s", (loai_xe_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_loai_xe() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, he_so_gia, so_do_ghe FROM loai_xe ORDER BY ten")
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
