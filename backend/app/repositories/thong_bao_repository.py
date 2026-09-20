"""Raw SQL cho bảng thong_bao — DATABASE.md mục 6.1.

Chỉ chứa hàm ghi — dùng để lưu lại thông báo TRƯỚC khi đẩy qua
websocket_manager.broadcast(), để khách offline lúc sự kiện xảy ra vẫn
đọc lại được sau (ARCHITECTURE.md mục 6). Màn hình xem danh sách thông
báo của khách hàng (đọc) thuộc phần khách hàng, chưa cài đặt ở đây.
"""

from app.db import get_connection, release_connection


def tao(nguoi_nhan_id: str, noi_dung: str, ve_id: str | None = None) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, ve_id) VALUES (%s, %s, %s)",
                (nguoi_nhan_id, noi_dung, ve_id),
            )
        conn.commit()
    finally:
        release_connection(conn)
