"""Raw SQL cho Tạo tài khoản cán bộ — UC-36 (DATABASE.md mục 1.1, 1.3).

Không chứa quy tắc nghiệp vụ (ai được tạo vai trò nào, vai trò nào cần văn
phòng...) — việc đó thuộc services/tai_khoan_can_bo_service.py.

Hàm `tao_tai_khoan` ghi `nguoi_dung` và `ho_so_can_bo_diem` trong CÙNG MỘT
transaction (một kết nối, một commit): không để lại tài khoản quầy vé/gửi
hàng thiếu văn phòng nếu bước gán lỗi giữa chừng.
"""

from psycopg2 import errors

from app.db import get_connection, release_connection
from app.utils.loi import GiaTriLoi


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def la_tai_khoan_goc(nguoi_dung_id: str) -> bool:
    """`quan_ly` gốc (la_tai_khoan_goc = true) — chỉ tài khoản này tạo được quan_ly / quan_ly_nhan_su."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT la_tai_khoan_goc FROM nguoi_dung WHERE id = %s", (nguoi_dung_id,))
            row = cur.fetchone()
            return bool(row and row[0])
    finally:
        release_connection(conn)


def tao_tai_khoan(
    email: str, mat_khau_hash: str, ho_ten: str, so_dien_thoai: str, vai_tro: str, van_phong_id: str | None
) -> dict:
    """Tạo tài khoản cán bộ: có sẵn mật khẩu (đã băm) và ĐÃ xác nhận
    (da_xac_nhan = true) — email do công ty cấp nên không cần xác minh qua OTP,
    và dang_nhap chặn mọi tài khoản có da_xac_nhan = false."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan)
                VALUES (%s, %s, %s, %s, %s, true)
                RETURNING id, email, ho_ten, vai_tro
                """,
                (email, mat_khau_hash, ho_ten, so_dien_thoai, vai_tro),
            )
            tai_khoan = _thanh_dict(cur, cur.fetchone())
            tai_khoan["van_phong_id"] = None
            if van_phong_id:
                cur.execute(
                    "INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id) VALUES (%s, %s)",
                    (tai_khoan["id"], van_phong_id),
                )
                tai_khoan["van_phong_id"] = van_phong_id
        conn.commit()
        return tai_khoan
    except errors.UniqueViolation:
        # Hai người tạo cùng email gần như cùng lúc: kiểm tra trùng ở Service chưa kịp bắt, UNIQUE của DB bắt.
        conn.rollback()
        raise GiaTriLoi("Email đã tồn tại")
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_tai_khoan_can_bo(vai_tro_cho_phep: list[str], tu_khoa: str | None = None) -> list[dict]:
    """Tài khoản cán bộ thuộc các vai trò `vai_tro_cho_phep`, kèm văn phòng (nếu có).
    `tu_khoa` tìm theo email / họ tên / số điện thoại (không phân biệt hoa thường)."""
    if not vai_tro_cho_phep:
        return []
    dieu_kien = ["nd.vai_tro = ANY(%s)"]
    tham_so: list = [vai_tro_cho_phep]
    if tu_khoa:
        dieu_kien.append("(nd.email ILIKE %s OR nd.ho_ten ILIKE %s OR nd.so_dien_thoai ILIKE %s)")
        tham_so += [f"%{tu_khoa}%"] * 3
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT nd.id, nd.email, nd.ho_ten, nd.so_dien_thoai, nd.vai_tro, nd.dang_hoat_dong,
                       (nd.mat_khau IS NOT NULL) AS da_dat_mat_khau,
                       h.van_phong_id, d.ten AS ten_van_phong, nd.ngay_tao
                FROM nguoi_dung nd
                LEFT JOIN ho_so_can_bo_diem h ON h.nguoi_dung_id = nd.id
                LEFT JOIN diem_don_tra d ON d.id = h.van_phong_id
                WHERE {" AND ".join(dieu_kien)}
                ORDER BY nd.ngay_tao DESC
                """,
                tham_so,
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def danh_sach_van_phong() -> list[dict]:
    """Văn phòng (diem_don_tra.loai = 'van_phong') cho ô chọn văn phòng phụ trách."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, dia_chi FROM diem_don_tra WHERE loai = 'van_phong' ORDER BY ten")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        release_connection(conn)
