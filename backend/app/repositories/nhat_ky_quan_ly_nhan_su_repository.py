"""Raw SQL cho bảng nhat_ky_quan_ly_nhan_su — DATABASE.md mục 6.3.

TÁCH RIÊNG khỏi nhat_ky_admin — bảng này CHỈ ghi hành động do chính
quan_ly_nhan_su thực hiện, không lẫn hành động của quan_ly hay vai trò khác
(UC-52). Bảng chỉ INSERT, không có hàm sửa/xóa — xem DATABASE.md mục 6.3.
"""

from app.db import get_connection, release_connection


def ghi(quan_ly_nhan_su_id: str, hanh_dong: str, doi_tuong_loai: str, doi_tuong_id: str, ghi_chu: str | None = None) -> None:
    """Chỉ ghi khi actor đang thao tác là `quan_ly_nhan_su` — Service gọi
    hàm này tự chịu trách nhiệm kiểm tra vai_tro trước (không có CHECK nào ở
    DB diễn tả được việc này vì phải join sang nguoi_dung)."""
    # doi_tuong_loai/doi_tuong_id: đối tượng bị tác động (VD "nhan_su_van_hanh" + id hồ sơ)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nhat_ky_quan_ly_nhan_su (quan_ly_nhan_su_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (quan_ly_nhan_su_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu),
            )
        conn.commit()
    finally:
        release_connection(conn)
