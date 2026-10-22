"""Raw SQL cho bảng nhan_su_van_hanh/xe_nhan_su — DATABASE.md mục 1.4, 1.5.

Gồm các hàm đọc cho phần phụ xe (suy ra "xe của tôi" từ biên chế,
NGHIEP_VU.md mục 3.2) và các hàm quản lý biên chế CỐ ĐỊNH của quản lý
(UC-35). Biên chế tạm thời thuộc điều độ viên (mục 8.6), chưa cài đặt ở đây.
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def tim_theo_nguoi_dung_id(nguoi_dung_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai, chuc_danh FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s",
                (nguoi_dung_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_xe_dang_gan(nhan_su_van_hanh_id: str) -> str | None:
    """Xe hiện tại của 1 phụ xe — đúng 1 dòng dang_hoat_dong tại 1 thời
    điểm (NGHIEP_VU.md mục 3.2). Trả về xe_id hoặc None nếu chưa được biên chế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xe_id FROM xe_nhan_su
                WHERE nhan_su_van_hanh_id = %s AND trang_thai = 'dang_hoat_dong'
                LIMIT 1
                """,
                (nhan_su_van_hanh_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Biên chế cố định (UC-35)
# ---------------------------------------------------------
def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def tim_theo_id(nhan_su_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, trang_thai FROM nhan_su_van_hanh WHERE id = %s",
                (nhan_su_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_dang_lam() -> list[dict]:
    """Nhân sự còn đang làm, kèm biển số xe mà họ đang thuộc biên chế cố định (nếu có)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       (n.nguoi_dung_id IS NOT NULL) AS co_tai_khoan,
                       x.bien_so AS bien_so_xe_co_dinh
                FROM nhan_su_van_hanh n
                LEFT JOIN xe_nhan_su xn ON xn.nhan_su_van_hanh_id = n.id AND xn.loai = 'co_dinh'
                LEFT JOIN xe x ON x.id = xn.xe_id
                WHERE n.trang_thai = 'dang_lam'
                ORDER BY n.chuc_danh, n.ho_ten
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_bien_che_theo_xe(xe_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.id, xn.nhan_su_van_hanh_id, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       xn.loai, xn.trang_thai
                FROM xe_nhan_su xn
                JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                WHERE xn.xe_id = %s
                ORDER BY n.chuc_danh, xn.loai, n.ho_ten
                """,
                (xe_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_bien_che_theo_id(xe_nhan_su_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, xe_id, nhan_su_van_hanh_id, loai FROM xe_nhan_su WHERE id = %s", (xe_nhan_su_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_bien_che_co_dinh_cua_nhan_su(nhan_su_id: str) -> dict | None:
    """Dòng biên chế cố định hiện có của 1 nhân sự (kèm biển số xe) — 1 người chỉ thuộc 1 xe (mục 3.2)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.id, xn.xe_id, x.bien_so
                FROM xe_nhan_su xn JOIN xe x ON x.id = xn.xe_id
                WHERE xn.nhan_su_van_hanh_id = %s AND xn.loai = 'co_dinh'
                LIMIT 1
                """,
                (nhan_su_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def dem_co_dinh_theo_chuc_danh(xe_id: str, chuc_danh: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM xe_nhan_su xn JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                WHERE xn.xe_id = %s AND xn.loai = 'co_dinh' AND n.chuc_danh = %s
                """,
                (xe_id, chuc_danh),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def them_bien_che_co_dinh(xe_id: str, nhan_su_id: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh') RETURNING id",
                (xe_id, nhan_su_id),
            )
            xe_nhan_su_id = cur.fetchone()[0]
        conn.commit()
        return xe_nhan_su_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_bien_che(xe_nhan_su_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM xe_nhan_su WHERE id = %s", (xe_nhan_su_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Hồ sơ nhân sự vận hành (UC-49, quan_ly_nhan_su/quan_ly) — chỉ THÊM hàm mới
# bên dưới đây, không sửa bất kỳ hàm nào ở trên (tim_theo_id ở trên vẫn giữ
# nguyên, chỉ phục vụ UC-35; hồ sơ đầy đủ dùng tim_ho_so_day_du riêng).
# ---------------------------------------------------------
def tim_ho_so_day_du(nhan_su_id: str) -> dict | None:
    """Toàn bộ cột hồ sơ, kể cả cột nhạy cảm (so_cccd, ngay_sinh) —
    Service/Schema ở tầng trên tự quyết định có trả ra API hay không
    (DATABASE.md mục 9, "Phân quyền đọc hồ sơ nhân sự")."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, so_cccd, ngay_sinh,
                       anh_ho_so, ngay_vao_lam, trang_thai, ngay_nghi_viec, ly_do_nghi_viec
                FROM nhan_su_van_hanh
                WHERE id = %s
                """,
                (nhan_su_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_ho_so(chi_dang_lam: bool = False) -> list[dict]:
    """Danh sách tóm tắt (không lấy CCCD/ngày sinh). Sắp theo chức danh rồi tên.
    Chuỗi SQL chỉ nối thêm điều kiện cố định, không nối dữ liệu người dùng
    -> không có nguy cơ SQL injection."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, trang_thai FROM nhan_su_van_hanh"
                + (" WHERE trang_thai = 'dang_lam'" if chi_dang_lam else "")
                + " ORDER BY chuc_danh, ho_ten"
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tao_ho_so(
    ho_ten: str,
    so_dien_thoai: str,
    chuc_danh: str,
    nguoi_dung_id: str | None,
    so_cccd: str | None,
    ngay_sinh,
    ngay_vao_lam,
) -> str:
    # COALESCE(%s, current_date): không truyền ngay_vao_lam thì lấy ngày hôm nay.
    # RETURNING id: lấy luôn id vừa tạo, khỏi phải SELECT lại.
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nhan_su_van_hanh (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, so_cccd, ngay_sinh, ngay_vao_lam)
                VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, current_date))
                RETURNING id
                """,
                (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, so_cccd, ngay_sinh, ngay_vao_lam),
            )
            nhan_su_id = cur.fetchone()[0]
        conn.commit()
        return nhan_su_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def cap_nhat_ho_so(nhan_su_id: str, ho_ten: str, so_dien_thoai: str, so_cccd: str | None, ngay_sinh, ngay_vao_lam) -> None:
    """Không sửa `chuc_danh`/`nguoi_dung_id` — "không đổi chức danh sau khi
    tạo" (NGHIEP_VU.md UC-49)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE nhan_su_van_hanh
                SET ho_ten = %s, so_dien_thoai = %s, so_cccd = %s, ngay_sinh = %s, ngay_vao_lam = %s
                WHERE id = %s
                """,
                (ho_ten, so_dien_thoai, so_cccd, ngay_sinh, ngay_vao_lam, nhan_su_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def cap_nhat_anh_ho_so(nhan_su_id: str, anh_ho_so: str) -> None:
    """Lưu public_id ảnh Cloudinary (không phải URL) vào hồ sơ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE nhan_su_van_hanh SET anh_ho_so = %s WHERE id = %s", (anh_ho_so, nhan_su_id))
        conn.commit()
    finally:
        release_connection(conn)


def danh_sach_tai_khoan_phu_xe_chua_gan() -> list[dict]:
    """Tài khoản vai trò phu_xe đang hoạt động mà CHƯA gắn với hồ sơ nào —
    để frontend cho chọn thay vì phải dán UUID khi tạo hồ sơ phụ xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.id, nd.ho_ten, nd.email, nd.so_dien_thoai
                FROM nguoi_dung nd
                WHERE nd.vai_tro = 'phu_xe'
                  AND nd.dang_hoat_dong = true
                  AND NOT EXISTS (SELECT 1 FROM nhan_su_van_hanh n WHERE n.nguoi_dung_id = nd.id)
                ORDER BY nd.ho_ten
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
