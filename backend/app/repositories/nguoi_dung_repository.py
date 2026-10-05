"""Raw SQL cho bảng nguoi_dung — DATABASE.md mục 1.1.

Không chứa quy tắc nghiệp vụ (không tự quyết định khi nào tài khoản hợp lệ,
mã còn hạn hay không...) — chỉ đọc/ghi đúng bảng, việc đó thuộc
services/mat_khau_service.py (ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def tim_theo_email(email: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, mat_khau, ho_ten, so_dien_thoai, vai_tro,
                       dang_hoat_dong, da_xac_nhan, ma_xac_nhan, ma_het_han
                FROM nguoi_dung
                WHERE email = %s
                """,
                (email,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(nguoi_dung_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.id, nd.email, nd.ho_ten, nd.so_dien_thoai, nd.vai_tro,
                       nd.dang_hoat_dong, nd.ngay_tao, h.van_phong_id
                FROM nguoi_dung nd
                LEFT JOIN ho_so_can_bo_diem h ON h.nguoi_dung_id = nd.id
                WHERE nd.id = %s
                """,
                (nguoi_dung_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def gan_van_phong(nguoi_dung_id: str, van_phong_id: str) -> None:
    """Gán văn phòng phụ trách cho nhân viên quầy/điều độ viên."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id)
                VALUES (%s, %s)
                ON CONFLICT (nguoi_dung_id)
                DO UPDATE SET van_phong_id = EXCLUDED.van_phong_id
                """,
                (nguoi_dung_id, van_phong_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def lay_mat_khau_hash(nguoi_dung_id: str) -> str | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT mat_khau FROM nguoi_dung WHERE id = %s", (nguoi_dung_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)


def tao_khach_hang_chua_kich_hoat(
    email: str, mat_khau_hash: str, ho_ten: str, so_dien_thoai: str, ma_xac_nhan: str, ma_het_han
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, ma_xac_nhan, ma_het_han)
                VALUES (%s, %s, %s, %s, 'khach_hang', %s, %s)
                """,
                (email, mat_khau_hash, ho_ten, so_dien_thoai, ma_xac_nhan, ma_het_han),
            )
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_lai_thong_tin_va_ma(
    nguoi_dung_id: str, mat_khau_hash: str, ho_ten: str, so_dien_thoai: str, ma_xac_nhan: str, ma_het_han
) -> None:
    """Dùng khi email đã tồn tại nhưng chưa kích hoạt (khách bỏ dở đăng ký
    lần trước) — ghi đè lại thông tin + sinh mã mới."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE nguoi_dung
                SET mat_khau = %s, ho_ten = %s, so_dien_thoai = %s, ma_xac_nhan = %s, ma_het_han = %s
                WHERE id = %s
                """,
                (mat_khau_hash, ho_ten, so_dien_thoai, ma_xac_nhan, ma_het_han, nguoi_dung_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_ma_xac_nhan_quen_mat_khau(nguoi_dung_id: str, ma_xac_nhan: str, ma_het_han) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE nguoi_dung SET ma_xac_nhan = %s, ma_het_han = %s WHERE id = %s",
                (ma_xac_nhan, ma_het_han, nguoi_dung_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def xoa_ma_xac_nhan(nguoi_dung_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE nguoi_dung SET ma_xac_nhan = NULL, ma_het_han = NULL WHERE id = %s",
                (nguoi_dung_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def kich_hoat_tai_khoan(nguoi_dung_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE nguoi_dung
                SET da_xac_nhan = true, ma_xac_nhan = NULL, ma_het_han = NULL
                WHERE id = %s
                """,
                (nguoi_dung_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def dat_lai_mat_khau(nguoi_dung_id: str, mat_khau_hash: str) -> None:
    """Dùng cho luồng quên-mật-khẩu (qua OTP) — xóa luôn mã xác nhận sau khi đặt xong."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE nguoi_dung
                SET mat_khau = %s, ma_xac_nhan = NULL, ma_het_han = NULL
                WHERE id = %s
                """,
                (mat_khau_hash, nguoi_dung_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_mat_khau(nguoi_dung_id: str, mat_khau_hash: str) -> None:
    """Dùng cho luồng đổi-mật-khẩu khi đã đăng nhập (không liên quan OTP)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE nguoi_dung SET mat_khau = %s WHERE id = %s", (mat_khau_hash, nguoi_dung_id))
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_so_dien_thoai(nguoi_dung_id: str, so_dien_thoai: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE nguoi_dung SET so_dien_thoai = %s WHERE id = %s", (so_dien_thoai, nguoi_dung_id))
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_ho_ten(nguoi_dung_id: str, ho_ten: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE nguoi_dung SET ho_ten = %s WHERE id = %s", (ho_ten, nguoi_dung_id))
        conn.commit()
    finally:
        release_connection(conn)


def danh_sach_id_theo_vai_tro(vai_tro: str, chi_dang_hoat_dong: bool = False) -> list[str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM nguoi_dung WHERE vai_tro = %s"
                + (" AND dang_hoat_dong = true" if chi_dang_hoat_dong else ""),
                (vai_tro,),
            )
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        release_connection(conn)
