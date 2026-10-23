"""Raw SQL cho bảng nhat_ky_admin — DATABASE.md mục 6.2.

Bảng này CHỈ ghi hành động do `quan_ly` thực hiện. Hành động của
`quan_ly_nhan_su` ghi ở nhat_ky_quan_ly_nhan_su_repository, không ghi vào đây.
Bảng chỉ INSERT, không có hàm sửa/xóa để nhật ký không bị chỉnh sau khi ghi.
"""

from app.db import get_connection, release_connection


def ghi(admin_id: str, hanh_dong: str, doi_tuong_loai: str, doi_tuong_id: str, ghi_chu: str | None = None) -> None:
    """Service gọi hàm này tự chịu trách nhiệm kiểm tra actor là `quan_ly`
    trước (không có CHECK nào ở DB diễn tả được vì phải join sang nguoi_dung)."""
    # doi_tuong_loai/doi_tuong_id: đối tượng bị tác động (VD "nguoi_dung" + id tài khoản)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nhat_ky_admin (admin_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (admin_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu),
            )
        conn.commit()
    finally:
        release_connection(conn)
