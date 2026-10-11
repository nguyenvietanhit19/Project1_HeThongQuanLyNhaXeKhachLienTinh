"""Raw SQL cho bảng ho_so_khach_hang — DATABASE.md mục 1.2.

Chỉ chứa hàm cần cho hệ quả tự động của UC-14 (khóa "thanh toán tại quầy"
khi đủ ngưỡng vi phạm no-show, NGHIEP_VU.md mục 9). Việc khách hàng bị
khóa hẳn tài khoản (bi_khoa) hay quan_ly gỡ hạn chế thuộc UC-37/38, chưa
cài đặt ở đây.
"""

from app.db import get_connection, release_connection


def khoa_thanh_toan_tai_quay(nguoi_dung_id: str) -> None:
    """Tạo hồ sơ nếu chưa có (upsert) — hầu hết khách hàng sẽ chưa từng có
    dòng nào ở đây cho tới lần vi phạm đủ ngưỡng đầu tiên."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ho_so_khach_hang (nguoi_dung_id, khoa_thanh_toan_tai_quay)
                VALUES (%s, true)
                ON CONFLICT (nguoi_dung_id) DO UPDATE SET khoa_thanh_toan_tai_quay = true
                """,
                (nguoi_dung_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def lay_theo_id(nguoi_dung_id: str) -> dict:
    """Hạn chế đặt vé của khách (mục 9). Khách chưa từng vi phạm thì chưa có dòng nào → mọi cờ là false."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT khoa_thanh_toan_tai_quay, bi_khoa, ly_do_khoa FROM ho_so_khach_hang WHERE nguoi_dung_id = %s",
                (nguoi_dung_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {"khoa_thanh_toan_tai_quay": False, "bi_khoa": False, "ly_do_khoa": None}
            return {"khoa_thanh_toan_tai_quay": row[0], "bi_khoa": row[1], "ly_do_khoa": row[2]}
    finally:
        release_connection(conn)
