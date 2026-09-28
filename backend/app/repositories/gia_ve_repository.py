"""Raw SQL cho gia_ve — DATABASE.md mục 2.5, UC-33. Không chứa quy tắc
nghiệp vụ — việc đó thuộc services/gia_ve_service.py (ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def tao_gia_ve(tuyen_id: str, diem_di_id: str, diem_den_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO gia_ve (tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den
                """,
                (tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua_gia_ve(gia_ve_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> None:
    """Chỉ sửa giá + thời hạn áp dụng — đổi tuyến/điểm đi/điểm đến coi như
    1 cấu hình giá khác hẳn, phải xóa dòng cũ và tạo dòng mới."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE gia_ve SET gia_goc = %s, ap_dung_tu = %s, ap_dung_den = %s WHERE id = %s",
                (gia_goc, ap_dung_tu, ap_dung_den, gia_ve_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tim_gia_ve_theo_id(gia_ve_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den FROM gia_ve WHERE id = %s",
                (gia_ve_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_gia_ve_theo_cap_diem(tuyen_id: str, diem_di_id: str, diem_den_id: str) -> list[dict]:
    """Dùng để kiểm tra chồng lấn khoảng ngày áp dụng (service.py) — UNIQUE
    constraint của bảng không tự chặn được vì SQL coi 2 giá trị NULL khác
    nhau (không bị tính là trùng), nên phải tự kiểm tra ở tầng nghiệp vụ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ap_dung_tu, ap_dung_den FROM gia_ve
                WHERE tuyen_id = %s AND diem_di_id = %s AND diem_den_id = %s
                """,
                (tuyen_id, diem_di_id, diem_den_id),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_gia_ve(tuyen_id: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT gv.id, gv.tuyen_id, gv.diem_di_id, gv.diem_den_id, gv.gia_goc,
                       gv.ap_dung_tu, gv.ap_dung_den,
                       t.ten AS ten_tuyen, kd.ten AS ten_diem_di, ka.ten AS ten_diem_den
                FROM gia_ve gv
                JOIN tuyen t ON t.id = gv.tuyen_id
                JOIN khu_vuc kd ON kd.id = gv.diem_di_id
                JOIN khu_vuc ka ON ka.id = gv.diem_den_id
            """
            if tuyen_id:
                sql += " WHERE gv.tuyen_id = %s ORDER BY kd.ten, ka.ten, gv.ap_dung_tu NULLS FIRST"
                cur.execute(sql, (tuyen_id,))
            else:
                sql += " ORDER BY t.ten, kd.ten, ka.ten"
                cur.execute(sql)
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_gia_ve(gia_ve_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gia_ve WHERE id = %s", (gia_ve_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
