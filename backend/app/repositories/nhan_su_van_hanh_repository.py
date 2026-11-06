"""Raw SQL cho bảng nhan_su_van_hanh/xe_nhan_su — DATABASE.md mục 1.4, 1.5.

Gồm các hàm đọc cho phần phụ xe (suy ra "xe của tôi" từ biên chế,
NGHIEP_VU.md mục 3.2) và các hàm quản lý biên chế CỐ ĐỊNH của quản lý
(UC-35). Biên chế tạm thời thuộc điều độ viên (mục 8.6), chưa cài đặt ở đây.
"""

import psycopg2.errors

from app.db import get_connection, release_connection
from app.repositories import ma_repository
from app.utils.loi import GiaTriLoi

# Tên ràng buộc UNIQUE của bảng này -> câu báo lỗi cho người dùng. Lưới an toàn khi 2 người lưu cùng lúc lọt qua
# bước kiểm tra trùng ở service (kiểm tra trước rồi mới ghi vẫn có khe hở); không có nó người dùng chỉ thấy "lỗi hệ thống".
_LOI_TRUNG = {
    "nhan_su_van_hanh_so_cccd_duy_nhat": "Số CCCD này đã có trong một hồ sơ khác",
    "nhan_su_van_hanh_nguoi_dung_id_key": "Tài khoản này đã gắn với 1 hồ sơ khác",
}


def _doi_loi_trung(loi: psycopg2.errors.UniqueViolation) -> GiaTriLoi:
    ten = getattr(loi.diag, "constraint_name", None)
    return GiaTriLoi(_LOI_TRUNG.get(ten, "Dữ liệu bị trùng với một hồ sơ khác"))


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
    """Nhân sự còn đang làm, kèm mã, email (phụ xe), ngày vào làm, xe mà họ đang thuộc biên chế cố định (nếu có) và hạn giấy tờ sớm nhất
    (service tự phân loại hết hạn / sắp hết hạn)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, COALESCE(n.ma, nd.ma) AS ma, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       (n.nguoi_dung_id IS NOT NULL) AS co_tai_khoan, nd.email, n.ngay_vao_lam,
                       x.id AS xe_id_co_dinh, x.bien_so AS bien_so_xe_co_dinh,
                       (SELECT min(g.ngay_het_han) FROM giay_to_nhan_su g WHERE g.nhan_su_van_hanh_id = n.id) AS ngay_het_han_giay_to_som
                FROM nhan_su_van_hanh n
                LEFT JOIN nguoi_dung nd ON nd.id = n.nguoi_dung_id
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
                SELECT xn.id, xn.nhan_su_van_hanh_id, COALESCE(n.ma, nd.ma) AS ma, n.ho_ten, n.so_dien_thoai, n.chuc_danh,
                       xn.loai, xn.trang_thai, n.trang_thai AS trang_thai_nhan_su
                FROM xe_nhan_su xn
                JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                LEFT JOIN nguoi_dung nd ON nd.id = n.nguoi_dung_id
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
    (DATABASE.md mục 9, "Phân quyền đọc hồ sơ nhân sự").

    `ma` = mã nhân viên: tài xế lấy mã của hồ sơ (TX...), phụ xe không có mã riêng nên lấy mã của tài khoản
    liên kết (PX...) — KE_HOACH_MA_NHAN_VIEN.md mục 3.2."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, COALESCE(n.ma, nd.ma) AS ma, n.ho_ten, n.so_dien_thoai, n.chuc_danh, n.nguoi_dung_id,
                       n.so_cccd, n.ngay_sinh, n.anh_ho_so, n.ngay_vao_lam, n.trang_thai, n.ngay_nghi_viec,
                       n.ly_do_nghi_viec
                FROM nhan_su_van_hanh n
                LEFT JOIN nguoi_dung nd ON nd.id = n.nguoi_dung_id
                WHERE n.id = %s
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
                "SELECT n.id, COALESCE(n.ma, nd.ma) AS ma, n.ho_ten, n.so_dien_thoai, n.chuc_danh, n.nguoi_dung_id,"
                " n.trang_thai FROM nhan_su_van_hanh n LEFT JOIN nguoi_dung nd ON nd.id = n.nguoi_dung_id"
                + (" WHERE n.trang_thai = 'dang_lam'" if chi_dang_lam else "")
                + " ORDER BY n.chuc_danh, n.ho_ten"
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
    # Mã nhân viên: chỉ TÀI XẾ có mã riêng (TX0001...), cấp trong cùng transaction; phụ xe dùng mã của tài khoản
    # (nguoi_dung.ma, cấp lúc tạo tài khoản ở UC-36) nên để ma = NULL.
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ma = ma_repository.cap_ma_nhan_vien(cur, "tai_xe") if chuc_danh == "tai_xe" else None
            cur.execute(
                """
                INSERT INTO nhan_su_van_hanh (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, so_cccd, ngay_sinh, ngay_vao_lam, ma)
                VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, current_date), %s)
                RETURNING id
                """,
                (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id, so_cccd, ngay_sinh, ngay_vao_lam, ma),
            )
            nhan_su_id = cur.fetchone()[0]
        conn.commit()
        return nhan_su_id
    except psycopg2.errors.UniqueViolation as loi:
        conn.rollback()
        raise _doi_loi_trung(loi) from loi
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
    except psycopg2.errors.UniqueViolation as loi:
        conn.rollback()
        raise _doi_loi_trung(loi) from loi
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def cap_nhat_anh_ho_so(nhan_su_id: str, anh_ho_so: str) -> str | None:
    """Lưu public_id ảnh Cloudinary (không phải URL) vào hồ sơ và TRẢ VỀ public_id ảnh cũ (None nếu chưa có / không có hồ sơ).

    Đọc ảnh cũ và ghi ảnh mới trong MỘT câu lệnh có khóa dòng (`FOR UPDATE`): hai người cùng đổi ảnh một hồ sơ sẽ xếp
    hàng, người sau nhận lại ảnh của người trước làm "ảnh cũ" để xóa — không để sót ảnh rác trên Cloudinary."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH cu AS (SELECT id, anh_ho_so FROM nhan_su_van_hanh WHERE id = %s FOR UPDATE)
                UPDATE nhan_su_van_hanh n SET anh_ho_so = %s FROM cu WHERE n.id = cu.id
                RETURNING cu.anh_ho_so
                """,
                (nhan_su_id, anh_ho_so),
            )
            row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception:
        conn.rollback()
        raise
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
                SELECT nd.id, nd.ma, nd.ho_ten, nd.email, nd.so_dien_thoai
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


# ---------------------------------------------------------
# Cho nghỉ việc (UC-51) — chỉ THÊM hàm, không sửa hàm cũ ở trên
# ---------------------------------------------------------
# Chuyến coi là "chưa kết thúc" khi cho nghỉ: đang chạy hoặc gặp sự cố (sự cố vẫn có thể quay lại đang chạy).
_TRANG_THAI_CHUYEN_CHUA_XONG = ("dang_chay", "gap_su_co")


def bien_che_cua_nhan_su(nhan_su_id: str) -> list[dict]:
    """Mọi dòng biên chế của 1 nhân sự (cố định + tạm thời, đang hoạt động hay tạm nghỉ), kèm biển số xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.id, xn.xe_id, x.bien_so, xn.loai, xn.trang_thai
                FROM xe_nhan_su xn JOIN xe x ON x.id = xn.xe_id
                WHERE xn.nhan_su_van_hanh_id = %s
                ORDER BY x.bien_so, xn.loai
                """,
                (nhan_su_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def _xe_co_chuyen_chua_xong(cur, nhan_su_id: str) -> list[dict]:
    # Xe thực tế của chuyến = xe_thuc_te_id nếu đã đổi xe, ngược lại xe_id — người trên xe nào thì chuyến đó mới "có" họ.
    cur.execute(
        """
        SELECT DISTINCT x.id AS xe_id, x.bien_so
        FROM xe_nhan_su xn
        JOIN xe x ON x.id = xn.xe_id
        JOIN chuyen_xe c ON COALESCE(c.xe_thuc_te_id, c.xe_id) = xn.xe_id
        WHERE xn.nhan_su_van_hanh_id = %s
          AND xn.trang_thai = 'dang_hoat_dong'
          AND c.trang_thai = ANY(%s)
        ORDER BY x.bien_so
        """,
        (nhan_su_id, list(_TRANG_THAI_CHUYEN_CHUA_XONG)),
    )
    return _thanh_list(cur, cur.fetchall())


def xe_co_chuyen_chua_xong(nhan_su_id: str) -> list[dict]:
    """Xe trong biên chế đang hoạt động của người này mà đang có chuyến dang_chay / gap_su_co."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            return _xe_co_chuyen_chua_xong(cur, nhan_su_id)
    finally:
        release_connection(conn)


def xe_thieu_nguoi_neu_nghi(nhan_su_id: str) -> list[dict]:
    """Xe sẽ THIẾU NGƯỜI nếu nhân sự này nghỉ — NGHIEP_VU.md UC-51, rẽ nhánh bước 2.

    Chỉ xét biên chế CỐ ĐỊNH đang hoạt động của xe, KHÔNG tính người này; đủ người = 2 tài xế + ≥1 phụ xe
    (hồ sơ `dang_lam`, phụ xe còn phải có tài khoản đang hoạt động). Chỉ báo chức danh của chính người nghỉ
    (tài xế nghỉ -> xét thiếu tài xế; phụ xe nghỉ -> xét thiếu phụ xe), để không nhắc lại chỗ vốn đã thiếu từ trước.
    Dòng biên chế tạm thời của người này không tạo cảnh báo."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT x.id AS xe_id, x.bien_so, n.chuc_danh,
                       (SELECT count(*) FROM xe_nhan_su k JOIN nhan_su_van_hanh p ON p.id = k.nhan_su_van_hanh_id
                         WHERE k.xe_id = x.id AND k.loai = 'co_dinh' AND k.trang_thai = 'dang_hoat_dong'
                           AND p.trang_thai = 'dang_lam' AND p.chuc_danh = 'tai_xe'
                           AND p.id <> n.id) AS so_tai_xe_con_lai,
                       (SELECT count(*) FROM xe_nhan_su k JOIN nhan_su_van_hanh p ON p.id = k.nhan_su_van_hanh_id
                         LEFT JOIN nguoi_dung u ON u.id = p.nguoi_dung_id
                         WHERE k.xe_id = x.id AND k.loai = 'co_dinh' AND k.trang_thai = 'dang_hoat_dong'
                           AND p.trang_thai = 'dang_lam' AND p.chuc_danh = 'phu_xe' AND u.dang_hoat_dong = true
                           AND p.id <> n.id) AS so_phu_xe_con_lai
                FROM xe_nhan_su xn
                JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                JOIN xe x ON x.id = xn.xe_id
                WHERE n.id = %s AND xn.loai = 'co_dinh' AND xn.trang_thai = 'dang_hoat_dong'
                ORDER BY x.bien_so
                """,
                (nhan_su_id,),
            )
            ket_qua = []
            for r in _thanh_list(cur, cur.fetchall()):
                thieu_tai_xe = r["chuc_danh"] == "tai_xe" and r["so_tai_xe_con_lai"] < 2
                thieu_phu_xe = r["chuc_danh"] == "phu_xe" and r["so_phu_xe_con_lai"] < 1
                if thieu_tai_xe or thieu_phu_xe:
                    ket_qua.append(
                        {
                            "xe_id": r["xe_id"],
                            "bien_so": r["bien_so"],
                            "thieu_tai_xe": thieu_tai_xe,
                            "thieu_phu_xe": thieu_phu_xe,
                            "so_tai_xe_con_lai": r["so_tai_xe_con_lai"],
                            "so_phu_xe_con_lai": r["so_phu_xe_con_lai"],
                        }
                    )
            return ket_qua
    finally:
        release_connection(conn)


def cho_nghi_viec(nhan_su_id: str, ngay_nghi, ly_do: str) -> str:
    """Cho nghỉ việc trong MỘT transaction: đóng hồ sơ + khóa tài khoản phụ xe (nếu có) + chuyển mọi dòng biên chế
    sang `tam_nghi`. Khóa dòng hồ sơ (FOR UPDATE) rồi kiểm tra lại, không tin kết quả xem trước.

    Trả về: 'ok' | 'khong_tim_thay' | 'da_nghi_viec' | 'xe_dang_chay' (không ghi gì nếu khác 'ok').
    Không xóa dòng biên chế cố định — gỡ hẳn là việc của quan_ly (UC-35)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT trang_thai, nguoi_dung_id FROM nhan_su_van_hanh WHERE id = %s FOR UPDATE", (nhan_su_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return "khong_tim_thay"
            trang_thai, nguoi_dung_id = row
            if trang_thai != "dang_lam":
                conn.rollback()
                return "da_nghi_viec"
            if _xe_co_chuyen_chua_xong(cur, nhan_su_id):
                conn.rollback()
                return "xe_dang_chay"

            cur.execute(
                "UPDATE nhan_su_van_hanh SET trang_thai = 'da_nghi_viec', ngay_nghi_viec = %s, ly_do_nghi_viec = %s WHERE id = %s",
                (ngay_nghi, ly_do, nhan_su_id),
            )
            if nguoi_dung_id:
                cur.execute("UPDATE nguoi_dung SET dang_hoat_dong = false WHERE id = %s", (nguoi_dung_id,))
            cur.execute(
                "UPDATE xe_nhan_su SET trang_thai = 'tam_nghi' WHERE nhan_su_van_hanh_id = %s AND trang_thai = 'dang_hoat_dong'",
                (nhan_su_id,),
            )
        conn.commit()
        return "ok"
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def dem_hieu_luc_theo_xe(xe_ids: list[str]) -> dict[str, tuple[int, int]]:
    """{xe_id: (số tài xế, số phụ xe) đang hoạt động} cho các xe cho trước — xe không có người nào thì không có trong kết quả (coi như (0, 0)).
    Cùng quy tắc "hiệu lực" với app/repositories/bien_che_sql.py."""
    if not xe_ids:
        return {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT xn.xe_id,
                       count(*) FILTER (WHERE n.chuc_danh = 'tai_xe'),
                       count(*) FILTER (WHERE n.chuc_danh = 'phu_xe')
                FROM xe_nhan_su xn JOIN nhan_su_van_hanh n ON n.id = xn.nhan_su_van_hanh_id
                WHERE xn.xe_id = ANY(%s::uuid[]) AND xn.trang_thai = 'dang_hoat_dong' AND n.trang_thai = 'dang_lam'
                GROUP BY xn.xe_id
                """,
                (list(xe_ids),),
            )
            return {str(xe_id): (int(tai_xe), int(phu_xe)) for xe_id, tai_xe, phu_xe in cur.fetchall()}
    finally:
        release_connection(conn)


def email_tai_khoan(nguoi_dung_id: str) -> dict | None:
    """Email và trạng thái hoạt động của tài khoản (phụ xe) — cho hộp chi tiết biên chế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, dang_hoat_dong FROM nguoi_dung WHERE id = %s", (nguoi_dung_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_ho_so_trung(cot: str, gia_tri: str, bo_qua_id: str | None = None) -> dict | None:
    """Hồ sơ KHÁC đang dùng cùng `so_cccd` hoặc `so_dien_thoai` (kể cả hồ sơ đã nghỉ việc, vì số CCCD vẫn bị chiếm).
    bo_qua_id: khi sửa, bỏ qua chính hồ sơ đang sửa. Trả id, mã, họ tên, trạng thái để báo rõ trùng với ai."""
    if cot not in ("so_cccd", "so_dien_thoai"):  # tên cột đi thẳng vào câu SQL nên chỉ cho 2 giá trị cố định
        raise ValueError("Cột không hợp lệ")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT n.id, n.ma, n.ho_ten, n.chuc_danh, n.trang_thai
                FROM nhan_su_van_hanh n
                WHERE n.{cot} = %s AND (%s::uuid IS NULL OR n.id <> %s::uuid)
                LIMIT 1
                """,
                (gia_tri, bo_qua_id, bo_qua_id),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)
