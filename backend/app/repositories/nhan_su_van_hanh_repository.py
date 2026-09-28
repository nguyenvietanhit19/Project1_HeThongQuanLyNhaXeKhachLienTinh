"""Raw SQL cho bảng nhan_su_van_hanh/xe_nhan_su — DATABASE.md mục 1.4, 1.5.

Chỉ chứa các hàm đọc cần cho phần phụ xe (suy ra "xe của tôi" từ biên chế,
NGHIEP_VU.md mục 3.2). CRUD biên chế cố định/tạm thời thuộc quản lý/điều độ
viên (UC-35, mục 8.6), chưa cài đặt ở đây.
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
