"""Raw SQL Repository cho bảng lich_su_hoan_tien — DATABASE.md mục 4.1.

Thao tác trực tiếp với CSDL qua psycopg2, phục vụ quy trình hoàn tiền
tự động (UC-21, UC-43) và xử lý thủ công của Kế toán (UC-22).
"""

from typing import Any
from app.db import get_connection, release_connection


def _thanh_dict(cur: Any, row: Any) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_danh_sach_dict(cur: Any, rows: list) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# ====================================================================
# 1. Tạo và Tra cứu Bản ghi Hoàn tiền
# ====================================================================

def tao_hoan_tien(
    ve_id: str,
    ly_do: str,
    so_tien: int,
    trang_thai: str = "cho_xu_ly",
    ma_giao_dich_hoan_tien: str | None = None,
) -> dict:
    """Tạo bản ghi hoàn tiền mới. Unique constraint trên ve_id ngăn chặn hoàn trùng lặp."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lich_su_hoan_tien (
                    ve_id, ly_do, so_tien, trang_thai, ma_giao_dich_hoan_tien, thoi_gian_hoan_xong
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    CASE WHEN %s = 'da_hoan_tu_dong' THEN now() ELSE NULL END
                )
                ON CONFLICT (ve_id) DO NOTHING
                RETURNING *
                """,
                (ve_id, ly_do, so_tien, trang_thai, ma_giao_dich_hoan_tien, trang_thai),
            )
            row = cur.fetchone()
            bghi = _thanh_dict(cur, row) if row else None
        conn.commit()

        # Nếu đã tồn tại dòng hoàn tiền trước đó, trả về dòng hiện có
        if not bghi:
            return tim_theo_ve_id(ve_id)
        return bghi
    finally:
        release_connection(conn)


def tim_theo_ve_id(ve_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM lich_su_hoan_tien WHERE ve_id = %s", (ve_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(hoan_tien_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM lich_su_hoan_tien WHERE id = %s", (hoan_tien_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 2. Xử lý Chuyển khoản Thủ công & Cập nhật Trạng thái (UC-22)
# ====================================================================

def lay_danh_sach_cho_xu_ly() -> list[dict]:
    """UC-22: Kế toán xem toàn bộ các khoản đang chờ chuyển khoản thủ công trên toàn hệ thống."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ht.*,
                       v.so_ghe, v.ma_dat_cho, v.gia AS gia_ve,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ten_khach_hang,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS sdt_khach_hang
                FROM lich_su_hoan_tien ht
                JOIN ve v ON ht.ve_id = v.id
                LEFT JOIN nguoi_dung nd ON v.khach_hang_id = nd.id
                WHERE ht.trang_thai = 'cho_xu_ly'
                ORDER BY ht.thoi_gian_xac_dinh ASC
                """
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def cap_nhat_chuyen_khoan_thu_cong(
    hoan_tien_id: str,
    nhan_vien_xu_ly_id: str,
    so_tai_khoan_nhan: str,
    ten_ngan_hang_nhan: str,
    ten_chu_tai_khoan_nhan: str,
) -> dict | None:
    """UC-22: Kế toán lưu thông tin tài khoản ngân hàng đã chuyển và cập nhật hoàn tất."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lich_su_hoan_tien
                SET trang_thai = 'da_hoan_chuyen_khoan_thu_cong',
                    nhan_vien_xu_ly_id = %s,
                    so_tai_khoan_nhan = %s,
                    ten_ngan_hang_nhan = %s,
                    ten_chu_tai_khoan_nhan = %s,
                    thoi_gian_hoan_xong = now()
                WHERE id = %s AND trang_thai = 'cho_xu_ly'
                RETURNING *
                """,
                (nhan_vien_xu_ly_id, so_tai_khoan_nhan, ten_ngan_hang_nhan, ten_chu_tai_khoan_nhan, hoan_tien_id),
            )
            bghi = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return bghi
    finally:
        release_connection(conn)


def cap_nhat_da_hoan_tu_dong(hoan_tien_id: str, ma_giao_dich_hoan_tien: str) -> dict | None:
    """Cập nhật khi hoàn qua cổng VNPay thành công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lich_su_hoan_tien
                SET trang_thai = 'da_hoan_tu_dong',
                    ma_giao_dich_hoan_tien = %s,
                    thoi_gian_hoan_xong = now()
                WHERE id = %s
                RETURNING *
                """,
                (ma_giao_dich_hoan_tien, hoan_tien_id),
            )
            bghi = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return bghi
    finally:
        release_connection(conn)


# ====================================================================
# 3. Thống kê Hoàn tiền (UC-39 cho Kế toán & Quản lý)
# ====================================================================

def thong_ke_hoan_tien() -> dict:
    """Thống kê tổng số tiền và số lượt hoàn theo từng lý do."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    COUNT(*) AS tong_so_luot,
                    COALESCE(SUM(so_tien), 0) AS tong_so_tien,
                    COUNT(*) FILTER (WHERE trang_thai = 'cho_xu_ly') AS so_luot_cho_xu_ly,
                    COUNT(*) FILTER (WHERE trang_thai = 'da_hoan_tu_dong') AS so_luot_tu_dong,
                    COUNT(*) FILTER (WHERE trang_thai = 'da_hoan_chuyen_khoan_thu_cong') AS so_luot_thu_cong
                FROM lich_su_hoan_tien
                """
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)

