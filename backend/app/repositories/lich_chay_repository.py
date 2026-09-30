"""Raw SQL cho lich_chay_dinh_ky — DATABASE.md mục 3.5, UC-18. Không chứa quy tắc
nghiệp vụ — việc đó thuộc services/lich_chay_service.py (ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection

_SELECT = """
    SELECT l.id, l.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, l.chieu, l.gio_khoi_hanh,
           l.loai_xe_id, lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, l.dang_ap_dung, l.ngay_tao,
           (SELECT count(*) FROM chuyen_xe c WHERE c.lich_chay_dinh_ky_id = l.id) AS so_chuyen_da_sinh
    FROM lich_chay_dinh_ky l
    JOIN tuyen t ON t.id = l.tuyen_id
    JOIN loai_xe lx ON lx.id = l.loai_xe_id
"""


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def tao(tuyen_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lich_chay_dinh_ky (tuyen_id, chieu, gio_khoi_hanh, loai_xe_id)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (tuyen_id, chieu, gio_khoi_hanh, loai_xe_id),
            )
            lich_id = cur.fetchone()[0]
        conn.commit()
        return lich_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua(lich_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE lich_chay_dinh_ky SET chieu = %s, gio_khoi_hanh = %s, loai_xe_id = %s WHERE id = %s",
                (chieu, gio_khoi_hanh, loai_xe_id, lich_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def doi_ap_dung(lich_id: str, dang_ap_dung: bool) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE lich_chay_dinh_ky SET dang_ap_dung = %s WHERE id = %s", (dang_ap_dung, lich_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa(lich_id: str) -> None:
    """Có thể ném ForeignKeyViolation nếu lịch đã sinh chuyến — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lich_chay_dinh_ky WHERE id = %s", (lich_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tim_theo_id(lich_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE l.id = %s", (lich_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach(tuyen_id: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = _SELECT
            tham_so: tuple = ()
            if tuyen_id:
                sql += " WHERE l.tuyen_id = %s"
                tham_so = (tuyen_id,)
            cur.execute(sql + " ORDER BY t.ten, l.chieu, l.gio_khoi_hanh", tham_so)
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_trung(tuyen_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str, tru_id: str | None = None) -> dict | None:
    """Lịch đã có cùng (tuyến, chiều, giờ, loại xe) — dùng chặn tạo trùng."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM lich_chay_dinh_ky
                WHERE tuyen_id = %s AND chieu = %s AND gio_khoi_hanh = %s AND loai_xe_id = %s
                  AND (%s::uuid IS NULL OR id <> %s::uuid)
                LIMIT 1
                """,
                (tuyen_id, chieu, gio_khoi_hanh, loai_xe_id, tru_id, tru_id),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)
