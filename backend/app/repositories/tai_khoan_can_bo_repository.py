"""Raw SQL cho Tạo tài khoản cán bộ — UC-36 (DATABASE.md mục 1.1, 1.3).

Không chứa quy tắc nghiệp vụ (ai được tạo vai trò nào, vai trò nào cần văn
phòng...) — việc đó thuộc services/tai_khoan_can_bo_service.py.

Hàm `tao_tai_khoan` ghi `nguoi_dung` và `ho_so_can_bo_diem` trong CÙNG MỘT
transaction (một kết nối, một commit): không để lại tài khoản quầy vé/gửi
hàng thiếu văn phòng nếu bước gán lỗi giữa chừng.
"""

from psycopg2 import errors

from app.db import get_connection, release_connection
from app.repositories import ma_repository
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
    email: str, mat_khau_hash: str, ho_ten: str, so_dien_thoai: str, vai_tro: str, van_phong_id: str | None,
    nhan_su_id: str | None = None,
) -> dict:
    """Tạo tài khoản cán bộ: có sẵn mật khẩu (đã băm) và ĐÃ xác nhận
    (da_xac_nhan = true) — email do công ty cấp nên không cần xác minh qua OTP,
    và dang_nhap chặn mọi tài khoản có da_xac_nhan = false.

    Mã nhân viên (PX0001, QV0001...) được cấp TRONG cùng transaction: lấy số từ sequence của vai trò rồi điền vào `ma`.
    nhan_su_id (chỉ phụ xe): hồ sơ nhân sự tài khoản này gắn vào.
    Nếu INSERT hỏng sau đó (VD trùng email) thì số đã lấy bị bỏ, mã kế tiếp sẽ nhảy cách một số — đúng như các mã khác."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ma = ma_repository.cap_ma_nhan_vien(cur, vai_tro)
            cur.execute(
                """
                INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan, ma)
                VALUES (%s, %s, %s, %s, %s, true, %s)
                RETURNING id, ma, email, ho_ten, vai_tro
                """,
                (email, mat_khau_hash, ho_ten, so_dien_thoai, vai_tro, ma),
            )
            tai_khoan = _thanh_dict(cur, cur.fetchone())
            tai_khoan["van_phong_id"] = None
            if van_phong_id:
                cur.execute(
                    "INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id) VALUES (%s, %s)",
                    (tai_khoan["id"], van_phong_id),
                )
                tai_khoan["van_phong_id"] = van_phong_id
            if nhan_su_id:
                # Phụ xe: gắn tài khoản vào hồ sơ có sẵn trong CÙNG transaction. Điều kiện `nguoi_dung_id IS NULL` chặn 2 người
                # cùng tạo tài khoản cho một hồ sơ: người sau không cập nhật được dòng nào -> hủy hết, không để lại tài khoản mồ côi.
                cur.execute(
                    "UPDATE nhan_su_van_hanh SET nguoi_dung_id = %s WHERE id = %s AND nguoi_dung_id IS NULL",
                    (tai_khoan["id"], nhan_su_id),
                )
                if cur.rowcount != 1:
                    raise GiaTriLoi("Hồ sơ này đã có tài khoản")
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
    `tu_khoa` tìm theo mã / email / họ tên / số điện thoại (không phân biệt hoa thường)."""
    if not vai_tro_cho_phep:
        return []
    dieu_kien = ["nd.vai_tro = ANY(%s)"]
    tham_so: list = [vai_tro_cho_phep]
    if tu_khoa:
        dieu_kien.append("(nd.ma ILIKE %s OR nd.email ILIKE %s OR nd.ho_ten ILIKE %s OR nd.so_dien_thoai ILIKE %s)")
        tham_so += [f"%{tu_khoa}%"] * 4
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT nd.id, nd.ma, nd.email, nd.ho_ten, nd.so_dien_thoai, nd.vai_tro, nd.dang_hoat_dong,
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


# ---------------------------------------------------------
# UC-37: khóa / mở khóa tài khoản (KE_HOACH_UC37 bước 2)
# ---------------------------------------------------------
def tim_tai_khoan(nguoi_dung_id: str) -> dict | None:
    """Thông tin tối thiểu để Service kiểm tra quyền khóa / mở khóa (None nếu không có tài khoản)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma, email, ho_ten, vai_tro, dang_hoat_dong, la_tai_khoan_goc
                FROM nguoi_dung
                WHERE id = %s
                """,
                (nguoi_dung_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def dat_trang_thai_hoat_dong(nguoi_dung_id: str, dang_hoat_dong: bool) -> None:
    """Khóa (false) / mở khóa (true). Chỉ đổi cờ, không xóa gì — lịch sử của tài khoản vẫn giữ nguyên."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE nguoi_dung SET dang_hoat_dong = %s WHERE id = %s", (dang_hoat_dong, nguoi_dung_id))
        conn.commit()
    finally:
        release_connection(conn)


def xe_thieu_phu_xe(nguoi_dung_id: str) -> list[dict]:
    """Các xe mà tài khoản phụ xe này đang thuộc biên chế CỐ ĐỊNH và, khi không tính người này,
    không còn phụ xe cố định nào đang hoạt động — NGHIEP_VU.md UC-37, hậu điều kiện.

    "Đang hoạt động" = dòng `xe_nhan_su` cố định ở trạng thái `dang_hoat_dong`, hồ sơ `dang_lam`
    VÀ tài khoản `dang_hoat_dong = true`. Gọi SAU khi đã khóa: tài khoản vừa bị khóa tự bị loại khỏi
    phép đếm nhờ điều kiện cuối, không cần loại trừ riêng. Trả danh sách rỗng nếu người này không
    phải phụ xe hoặc không thuộc biên chế xe nào."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT x.id AS xe_id, x.bien_so
                FROM xe_nhan_su ns
                JOIN nhan_su_van_hanh t ON t.id = ns.nhan_su_van_hanh_id
                JOIN xe x ON x.id = ns.xe_id
                WHERE t.nguoi_dung_id = %s
                  AND ns.loai = 'co_dinh' AND ns.trang_thai = 'dang_hoat_dong'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM xe_nhan_su ns2
                      JOIN nhan_su_van_hanh p ON p.id = ns2.nhan_su_van_hanh_id
                      JOIN nguoi_dung u ON u.id = p.nguoi_dung_id
                      WHERE ns2.xe_id = ns.xe_id
                        AND ns2.loai = 'co_dinh' AND ns2.trang_thai = 'dang_hoat_dong'
                        AND p.chuc_danh = 'phu_xe' AND p.trang_thai = 'dang_lam'
                        AND u.dang_hoat_dong = true
                  )
                ORDER BY x.bien_so
                """,
                (nguoi_dung_id,),
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Đổi văn phòng của cán bộ — nhánh kèm UC-36 (KE_HOACH_DOI_VAN_PHONG.md)
# ---------------------------------------------------------
def doi_van_phong(nguoi_dung_id: str, van_phong_moi_id: str) -> tuple[str, str | None]:
    """Đổi (hoặc gán lần đầu) văn phòng của quầy vé / gửi hàng trong MỘT transaction.

    Quy tắc "văn phòng cũ còn ≥ 1 người": khóa dòng văn phòng cũ (`FOR UPDATE`) rồi mới đếm đồng nghiệp CÙNG VAI TRÒ
    đang hoạt động ở văn phòng cũ, không tính người chuyển — nhờ khóa này hai người cùng chuyển một lúc khỏi văn
    phòng chỉ có 2 người sẽ xếp hàng, người sau bị chặn. Không áp dụng khi: chưa có văn phòng cũ (gán lần đầu), hoặc
    người chuyển đang bị khóa tài khoản (họ vốn không được tính là đang làm).

    Trả về (mã kết quả, van_phong_cu_id): 'ok' | 'khong_tim_thay' | 'trung_van_phong' | 'het_nguoi'. Khác 'ok' thì
    không ghi gì. Không dùng nguoi_dung_repository.gan_van_phong (của phần gửi hàng) để khỏi sửa file của họ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.vai_tro, nd.dang_hoat_dong, h.van_phong_id
                FROM nguoi_dung nd
                LEFT JOIN ho_so_can_bo_diem h ON h.nguoi_dung_id = nd.id
                WHERE nd.id = %s
                FOR UPDATE OF nd
                """,
                (nguoi_dung_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return "khong_tim_thay", None
            vai_tro, dang_hoat_dong, van_phong_cu_id = row
            if van_phong_cu_id is not None and str(van_phong_cu_id) == str(van_phong_moi_id):
                conn.rollback()
                return "trung_van_phong", van_phong_cu_id

            if van_phong_cu_id is not None and dang_hoat_dong:
                cur.execute("SELECT id FROM diem_don_tra WHERE id = %s FOR UPDATE", (van_phong_cu_id,))
                cur.execute(
                    """
                    SELECT count(*)
                    FROM ho_so_can_bo_diem h
                    JOIN nguoi_dung u ON u.id = h.nguoi_dung_id
                    WHERE h.van_phong_id = %s AND u.vai_tro = %s AND u.dang_hoat_dong = true AND u.id <> %s
                    """,
                    (van_phong_cu_id, vai_tro, nguoi_dung_id),
                )
                if cur.fetchone()[0] < 1:
                    conn.rollback()
                    return "het_nguoi", van_phong_cu_id

            cur.execute(
                """
                INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id)
                VALUES (%s, %s)
                ON CONFLICT (nguoi_dung_id) DO UPDATE SET van_phong_id = EXCLUDED.van_phong_id
                """,
                (nguoi_dung_id, van_phong_moi_id),
            )
        conn.commit()
        return "ok", van_phong_cu_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
