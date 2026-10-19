"""Raw SQL cho lich_chay_dinh_ky — DATABASE.md mục 3.5, UC-18. Không chứa quy tắc
nghiệp vụ — việc đó thuộc services/lich_chay_service.py (ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection

_SELECT = """
    SELECT l.id, l.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, l.chieu, l.gio_khoi_hanh,
           l.loai_xe_id, lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, l.dang_ap_dung, l.ngay_tao, l.cap_id, l.ngay_lech, l.he_so_gia,
           (SELECT MAX(d.thoi_gian_du_kien_phut) FROM tuyen_diem_don_tra d WHERE d.tuyen_id = l.tuyen_id) AS tong_phut,
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


def tong_phut_tuyen(tuyen_id: str) -> int | None:
    """Thời gian chạy cả tuyến (phút) = mốc muộn nhất trong các điểm dừng của tuyến."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(thoi_gian_du_kien_phut) FROM tuyen_diem_don_tra WHERE tuyen_id = %s", (tuyen_id,))
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def tao_cap(tuyen_id: str, xuoi: dict, nguoc: dict, ngay_lech: int, he_so_gia) -> str:
    """Tạo cả 2 lịch của 1 cặp trong cùng 1 giao dịch; xuoi/nguoc: {gio_khoi_hanh, loai_xe_id}. Trả về cap_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT gen_random_uuid()")
            cap_id = cur.fetchone()[0]
            for chieu, lich, lech in (("xuoi", xuoi, 0), ("nguoc", nguoc, ngay_lech)):
                cur.execute(
                    """
                    INSERT INTO lich_chay_dinh_ky (tuyen_id, chieu, gio_khoi_hanh, loai_xe_id, cap_id, ngay_lech, he_so_gia)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (tuyen_id, chieu, lich["gio_khoi_hanh"], lich["loai_xe_id"], cap_id, lech, he_so_gia),
                )
        conn.commit()
        return str(cap_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua(lich_id: str, gio_khoi_hanh, loai_xe_id: str, cap_id: str, ngay_lech: int) -> None:
    """Sửa giờ của 1 lịch, đổi loại xe cho cả cặp và cập nhật độ lệch ngày (lưu ở lịch chiều về)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE lich_chay_dinh_ky SET gio_khoi_hanh = %s WHERE id = %s", (gio_khoi_hanh, lich_id)
            )
            cur.execute("UPDATE lich_chay_dinh_ky SET loai_xe_id = %s WHERE cap_id = %s", (loai_xe_id, cap_id))
            cur.execute("UPDATE lich_chay_dinh_ky SET ngay_lech = %s WHERE cap_id = %s AND chieu = 'nguoc'", (ngay_lech, cap_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def doi_he_so_gia_cap(cap_id: str, he_so_gia) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE lich_chay_dinh_ky SET he_so_gia = %s WHERE cap_id = %s", (he_so_gia, cap_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def doi_ap_dung_cap(cap_id: str, dang_ap_dung: bool) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE lich_chay_dinh_ky SET dang_ap_dung = %s WHERE cap_id = %s", (dang_ap_dung, cap_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_cap(cap_id: str) -> None:
    """Có thể ném ForeignKeyViolation nếu 1 trong 2 lịch đã sinh chuyến — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lich_chay_dinh_ky WHERE cap_id = %s", (cap_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lich_cua_cap(cap_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE l.cap_id = %s ORDER BY l.chieu DESC", (cap_id,))
            return _thanh_list(cur, cur.fetchall())
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
            cur.execute(sql + " ORDER BY t.ten, l.cap_id, l.chieu DESC", tham_so)
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
