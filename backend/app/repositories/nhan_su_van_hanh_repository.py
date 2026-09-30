"""Raw SQL cho bảng nhan_su_van_hanh/xe_nhan_su — DATABASE.md mục 1.4, 1.5.

Gồm các hàm đọc cho phần phụ xe (suy ra "xe của tôi" từ biên chế,
NGHIEP_VU.md mục 3.2) và các hàm quản lý biên chế CỐ ĐỊNH của quản lý
(UC-35). Biên chế tạm thời thuộc điều độ viên (mục 8.6), chưa cài đặt ở đây.
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def tim_theo_nguoi_dung_id(nguoi_dung_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai, chuc_danh FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s",
                (nguoi_dung_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_xe_dang_gan(nhan_su_van_hanh_id: str) -> str | None:
    """Xe hiện tại của 1 phụ xe — đúng 1 dòng dang_hoat_dong tại 1 thời
    điểm (NGHIEP_VU.md mục 3.2). Trả về xe_id hoặc None nếu chưa được biên chế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xe_id FROM xe_nhan_su
                WHERE nhan_su_van_hanh_id = %s AND trang_thai = 'dang_hoat_dong'
                LIMIT 1
                """,
                (nhan_su_van_hanh_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Biên chế cố định (UC-35)
# ---------------------------------------------------------
def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def tim_theo_id(nhan_su_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, trang_thai FROM nhan_su_van_hanh WHERE id = %s",
                (nhan_su_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_dang_lam() -> list[dict]:
    """Nhân sự còn đang làm, kèm biển số xe mà họ đang thuộc biên chế cố định (nếu có)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       (n.nguoi_dung_id IS NOT NULL) AS co_tai_khoan,
                       x.bien_so AS bien_so_xe_co_dinh
                FROM nhan_su_van_hanh n
                LEFT JOIN xe_nhan_su xn ON xn.nhan_su_van_hanh_id = n.id AND xn.loai = 'co_dinh'
                LEFT JOIN xe x ON x.id = xn.xe_id
                WHERE n.trang_thai = 'dang_lam'
                ORDER BY n.chuc_danh, n.ho_ten
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_bien_che_theo_xe(xe_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.id, xn.nhan_su_van_hanh_id, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       xn.loai, xn.trang_thai
                FROM xe_nhan_su xn
                JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                WHERE xn.xe_id = %s
                ORDER BY n.chuc_danh, xn.loai, n.ho_ten
                """,
                (xe_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_bien_che_theo_id(xe_nhan_su_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, xe_id, nhan_su_van_hanh_id, loai FROM xe_nhan_su WHERE id = %s", (xe_nhan_su_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_bien_che_co_dinh_cua_nhan_su(nhan_su_id: str) -> dict | None:
    """Dòng biên chế cố định hiện có của 1 nhân sự (kèm biển số xe) — 1 người chỉ thuộc 1 xe (mục 3.2)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.id, xn.xe_id, x.bien_so
                FROM xe_nhan_su xn JOIN xe x ON x.id = xn.xe_id
                WHERE xn.nhan_su_van_hanh_id = %s AND xn.loai = 'co_dinh'
                LIMIT 1
                """,
                (nhan_su_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def dem_co_dinh_theo_chuc_danh(xe_id: str, chuc_danh: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM xe_nhan_su xn JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                WHERE xn.xe_id = %s AND xn.loai = 'co_dinh' AND n.chuc_danh = %s
                """,
                (xe_id, chuc_danh),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def them_bien_che_co_dinh(xe_id: str, nhan_su_id: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh') RETURNING id",
                (xe_id, nhan_su_id),
            )
            xe_nhan_su_id = cur.fetchone()[0]
        conn.commit()
        return xe_nhan_su_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_bien_che(xe_nhan_su_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM xe_nhan_su WHERE id = %s", (xe_nhan_su_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
