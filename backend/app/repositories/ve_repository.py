"""Raw SQL cho bảng ve — DATABASE.md mục 3.4.

Người 2 sở hữu file này — CONTRIBUTING.md mục 5.1.
Người 4 gọi hàm contract `tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)`
khi chuyến bị hoãn (UC-45) hoặc bị hủy do sự cố (UC-19/21).
"""

from app.db import get_connection, release_connection


def _row_to_dict(cur, row) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _rows_to_list(cur, rows) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def tim_ve_da_thanh_toan_theo_chuyen(chuyen_id: str) -> list[dict]:
    """Tìm tất cả vé đã thanh toán (chưa lên xe, chưa hủy) của một chuyến.
    Dùng cho:
      - UC-45: Thông báo hoãn chuyến tới khách hàng
      - UC-19 / UC-21: Xử lý hoàn tiền khi chuyến bị hủy
    """
    sql = """
        SELECT
            v.id, v.chuyen_id, v.so_ghe, v.khach_hang_id,
            v.gia, v.ma_dat_cho, v.trang_thai,
            v.ten_khach_vang_lai, v.sdt_khach_vang_lai
        FROM ve v
        WHERE v.chuyen_id = %s
          AND v.trang_thai = 'da_thanh_toan'
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (chuyen_id,))
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
