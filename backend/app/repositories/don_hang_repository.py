"""Raw SQL Repository cho bảng don_hang và loai_hang — DATABASE.md mục 5.

Thao tác trực tiếp với CSDL qua psycopg2, không chứa logic nghiệp vụ
(logic thuộc về services/gui_hang_service.py).
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
# 1. Thao tác Loại hàng (loai_hang)
# ====================================================================

def lay_danh_sach_loai_hang() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang ORDER BY ten")
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_loai_hang_theo_id(loai_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang WHERE id = %s", (loai_hang_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 2. Tạo và Tra cứu Đơn hàng (don_hang)
# ====================================================================

def tao_don_hang(du_lieu: dict) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO don_hang (
                    ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, loai_hang_id,
                    can_nang_kg, dai_cm, rong_cm, cao_cm, gia_cuoc,
                    ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan,
                    phuong_thuc_thanh_toan, nhan_vien_gui_id, trang_thai
                ) VALUES (
                    %(ma_van_don)s, %(tuyen_id)s, %(diem_gui_id)s, %(diem_nhan_id)s, %(loai_hang_id)s,
                    %(can_nang_kg)s, %(dai_cm)s, %(rong_cm)s, %(cao_cm)s, %(gia_cuoc)s,
                    %(ten_nguoi_gui)s, %(sdt_nguoi_gui)s, %(ten_nguoi_nhan)s, %(sdt_nguoi_nhan)s,
                    %(phuong_thuc_thanh_toan)s, %(nhan_vien_gui_id)s, 'cho_van_chuyen'
                )
                RETURNING *
                """,
                du_lieu,
            )
            don = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return don
    finally:
        release_connection(conn)


def tim_theo_ma_van_don(ma_van_don: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.*, lh.ten AS ten_loai_hang
                FROM don_hang d
                JOIN loai_hang lh ON d.loai_hang_id = lh.id
                WHERE d.ma_van_don = %s
                """,
                (ma_van_don,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(don_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.*, lh.ten AS ten_loai_hang
                FROM don_hang d
                JOIN loai_hang lh ON d.loai_hang_id = lh.id
                WHERE d.id = %s
                """,
                (don_hang_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_sdt(sdt: str) -> list[dict]:
    """Tra cứu các đơn hàng theo SĐT người gửi hoặc người nhận."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.*, lh.ten AS ten_loai_hang
                FROM don_hang d
                JOIN loai_hang lh ON d.loai_hang_id = lh.id
                WHERE d.sdt_nguoi_gui = %s OR d.sdt_nguoi_nhan = %s
                ORDER BY d.ngay_tao DESC
                """,
                (sdt, sdt),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ====================================================================
# 3. Cập nhật Trạng thái Đơn hàng (Giao hàng, Chất/Dỡ hàng)
# ====================================================================

def cap_nhat_giao_hang(don_hang_id: str, nhan_vien_nhan_id: str) -> dict | None:
    """UC-24: Xác nhận đã giao hàng cho người nhận."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'da_giao',
                    nhan_vien_nhan_id = %s,
                    ngay_giao = now()
                WHERE id = %s
                RETURNING *
                """,
                (nhan_vien_nhan_id, don_hang_id),
            )
            don = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return don
    finally:
        release_connection(conn)


def cap_nhat_chat_hang_len_chuyen(don_hang_id: str, chuyen_id: str) -> dict | None:
    """UC-26 (Phụ xe): Chất hàng lên chuyến xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'da_len_xe',
                    chuyen_id = %s
                WHERE id = %s
                RETURNING *
                """,
                (chuyen_id, don_hang_id),
            )
            don = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return don
    finally:
        release_connection(conn)


def cap_nhat_do_hang_tai_diem(don_hang_id: str) -> dict | None:
    """UC-27 (Phụ xe): Dỡ hàng xuống văn phòng điểm nhận, bắt đầu tính hạn lưu kho."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'cho_lay',
                    thoi_gian_den_diem_nhan = now()
                WHERE id = %s
                RETURNING *
                """,
                (don_hang_id,),
            )
            don = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return don
    finally:
        release_connection(conn)


def cap_nhat_thong_bao_nguoi_nhan(don_hang_id: str, da_thong_bao: bool) -> None:
    """UC-25: Ghi nhận đã liên hệ người nhận thành công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET da_thong_bao_nguoi_nhan = %s
                WHERE id = %s
                """,
                (da_thong_bao, don_hang_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


# ====================================================================
# 4. Truy vấn Danh sách phục vụ Vận hành & Tác vụ nền (UC-25, UC-46)
# ====================================================================

def lay_danh_sach_cho_xep_xe(tuyen_id: str) -> list[dict]:
    """Lấy các đơn hàng đang chờ chất lên chuyến thuộc đúng tuyến."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.*, lh.ten AS ten_loai_hang
                FROM don_hang d
                JOIN loai_hang lh ON d.loai_hang_id = lh.id
                WHERE d.tuyen_id = %s AND d.chuyen_id IS NULL AND d.trang_thai = 'cho_van_chuyen'
                ORDER BY d.ngay_tao ASC
                """,
                (tuyen_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_danh_sach_hang_cho_tai_diem(diem_nhan_id: str) -> list[dict]:
    """UC-25: Xem danh sách hàng đang chờ lấy hoặc cảnh báo/tồn kho tại điểm nhận."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.*, lh.ten AS ten_loai_hang
                FROM don_hang d
                JOIN loai_hang lh ON d.loai_hang_id = lh.id
                WHERE d.diem_nhan_id = %s AND d.trang_thai IN ('cho_lay', 'qua_han_luu_kho')
                ORDER BY d.thoi_gian_den_diem_nhan ASC NULLS LAST
                """,
                (diem_nhan_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_don_can_do_tai_diem(chuyen_id: str, diem_nhan_id: str) -> list[dict]:
    """UC-27 (Phụ xe): đơn đang trên xe (da_len_xe), cần dỡ tại đúng điểm
    nhận này của đúng chuyến này — bổ sung cho phần phụ xe (tuanhdung),
    lay_danh_sach_hang_cho_tai_diem() ở trên phục vụ UC-25 (hàng đã dỡ,
    chờ người đến lấy), không phải trường hợp này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma_van_don, ten_nguoi_nhan, can_nang_kg
                FROM don_hang
                WHERE chuyen_id = %s AND diem_nhan_id = %s AND trang_thai = 'da_len_xe'
                ORDER BY ngay_tao ASC
                """,
                (chuyen_id, diem_nhan_id),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def quet_bat_canh_bao_7_ngay() -> int:
    """UC-46: Bật cờ co_canh_bao_cho_lau cho đơn chờ lấy >= 7 ngày."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET co_canh_bao_cho_lau = true
                WHERE trang_thai = 'cho_lay'
                  AND co_canh_bao_cho_lau = false
                  AND thoi_gian_den_diem_nhan <= now() - INTERVAL '7 days'
                """
            )
            so_luong = cur.rowcount
        conn.commit()
        return so_luong
    finally:
        release_connection(conn)


def quet_chuyen_hang_ton_14_ngay() -> int:
    """UC-46: Chuyển sang 'qua_han_luu_kho' (hàng tồn) cho đơn chờ lấy >= 14 ngày."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'qua_han_luu_kho'
                WHERE trang_thai = 'cho_lay'
                  AND thoi_gian_den_diem_nhan <= now() - INTERVAL '14 days'
                """
            )
            so_luong = cur.rowcount
        conn.commit()
        return so_luong
    finally:
        release_connection(conn)

