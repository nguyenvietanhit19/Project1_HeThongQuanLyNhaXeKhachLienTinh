"""Raw SQL cho bảng bao_cao_su_co_hang — DATABASE.md mục 5.3 (UC-28)."""

from app.db import get_connection, release_connection


def tao(don_hang_id: str, nguoi_bao_cao_id: str, mo_ta: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bao_cao_su_co_hang (don_hang_id, nguoi_bao_cao_id, mo_ta) VALUES (%s, %s, %s)",
                (don_hang_id, nguoi_bao_cao_id, mo_ta),
            )
        conn.commit()
    finally:
        release_connection(conn)
