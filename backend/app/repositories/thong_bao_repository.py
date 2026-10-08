"""Raw SQL cho bảng thong_bao — DATABASE.md mục 6.1.

Hàm ghi dùng để lưu lại thông báo TRƯỚC khi đẩy qua
websocket_manager.broadcast(), để người nhận offline lúc sự kiện xảy ra vẫn
đọc lại được sau (ARCHITECTURE.md mục 6). Các hàm đọc phục vụ route chung
/thong-bao (mọi vai trò đã đăng nhập) — luôn lọc theo nguoi_nhan_id lấy từ
token, không bao giờ đọc/đánh dấu được thông báo của người khác.
"""

from app.db import get_connection, release_connection


def _thanh_danh_sach_dict(cur, rows) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def tao(
    nguoi_nhan_id: str, noi_dung: str, ve_id: str | None = None, don_hang_id: str | None = None
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, ve_id, don_hang_id) VALUES (%s, %s, %s, %s)",
                (nguoi_nhan_id, noi_dung, ve_id, don_hang_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def danh_sach_cua_toi(nguoi_nhan_id: str, chi_chua_doc: bool = False, limit: int = 30) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT tb.id, tb.noi_dung, tb.da_doc, tb.ngay_tao, tb.ve_id, tb.don_hang_id,
                       dh.ma_van_don, v.ma_dat_cho
                FROM thong_bao tb
                LEFT JOIN don_hang dh ON dh.id = tb.don_hang_id
                LEFT JOIN ve v ON v.id = tb.ve_id
                WHERE tb.nguoi_nhan_id = %s {"AND tb.da_doc = false" if chi_chua_doc else ""}
                ORDER BY tb.ngay_tao DESC
                LIMIT %s
                """,
                (nguoi_nhan_id, limit),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def dem_chua_doc(nguoi_nhan_id: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM thong_bao WHERE nguoi_nhan_id = %s AND da_doc = false",
                (nguoi_nhan_id,),
            )
            return int(cur.fetchone()[0])
    finally:
        release_connection(conn)


def danh_dau_da_doc(thong_bao_id: str, nguoi_nhan_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE thong_bao SET da_doc = true WHERE id = %s AND nguoi_nhan_id = %s RETURNING id",
                (thong_bao_id, nguoi_nhan_id),
            )
            co_dong = cur.fetchone() is not None
        conn.commit()
        return co_dong
    finally:
        release_connection(conn)


def danh_dau_tat_ca_da_doc(nguoi_nhan_id: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE thong_bao SET da_doc = true WHERE nguoi_nhan_id = %s AND da_doc = false",
                (nguoi_nhan_id,),
            )
            so_dong = cur.rowcount
        conn.commit()
        return so_dong
    finally:
        release_connection(conn)
