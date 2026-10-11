"""Raw SQL cho bảng chuyen_xe/lich_su_diem_dung_chuyen — DATABASE.md mục 3.3, 3.4.

Chứa các hàm cho phần phụ xe (xem chuyến của mình, xác nhận xuất phát/tới
điểm/sự cố — UC-15,16,17), sinh chuyến theo khoảng ngày, và xem/sửa/xóa chuyến
từ góc nhìn quản lý (UC-18, cuối file — gọi từ lich_chay_service.py). Gán xe
(UC-44), đổi xe khi hỏng (UC-19/20/40) thuộc điều độ viên, chưa cài đặt ở đây.
"""

from datetime import datetime

from app.db import get_connection, release_connection
from app.repositories import ma_repository
from app.utils import ma_tu_sinh


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


_row_to_dict = _thanh_dict
_rows_to_list = _thanh_list


def tim_theo_id(chuyen_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tuyen_id, xe_id, loai_xe_id, xe_thuc_te_id, gio_khoi_hanh,
                       trang_thai, dang_hoan, gio_xac_nhan_xuat_phat, gio_hoan_thanh,
                       loai_su_co, ly_do_su_co, co_canh_bao_xung_dot_vi_tri
                FROM chuyen_xe WHERE id = %s
                """,
                (chuyen_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_chuyen_cua_xe(xe_id: str) -> list[dict]:
    """Chuyến đang/sắp chạy của 1 xe — dùng để suy ra 'chuyến của tôi' của
    phụ xe (NGHIEP_VU.md mục 3.2/8.2 điểm 1). Bỏ qua chuyến đã hoan_thanh/da_huy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cx.id, cx.tuyen_id, t.ten AS tuyen_ten, x.bien_so,
                       cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan
                FROM chuyen_xe cx
                JOIN tuyen t ON t.id = cx.tuyen_id
                JOIN xe x ON x.id = COALESCE(cx.xe_thuc_te_id, cx.xe_id)
                WHERE cx.xe_id = %s AND cx.trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co')
                ORDER BY cx.gio_khoi_hanh ASC
                """,
                (xe_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_ten_tuyen_va_bien_so(tuyen_id: str, xe_id: str) -> dict:
    """Dùng cho chi_tiet_cho_phu_xe() — chỉ cần tên hiển thị, không phụ
    thuộc trạng thái chuyến (khác tim_chuyen_cua_xe, vốn lọc chỉ chuyến
    còn hoạt động)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT t.ten AS tuyen_ten, x.bien_so FROM tuyen t, xe x WHERE t.id = %s AND x.id = %s",
                (tuyen_id, xe_id),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def lay_diem_da_xac_nhan(chuyen_id: str) -> list[dict]:
    """Điểm đã được phụ xe xác nhận đến, sắp theo thu_tu — dùng để suy ra
    điểm hiện tại (mục 8.2 điểm 1/5)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ls.diem_don_tra_id, tdt.thu_tu, ls.gio_thuc_te
                FROM lich_su_diem_dung_chuyen ls
                JOIN chuyen_xe cx ON cx.id = ls.chuyen_id
                JOIN tuyen_diem_don_tra tdt ON tdt.tuyen_id = cx.tuyen_id AND tdt.diem_don_tra_id = ls.diem_don_tra_id
                WHERE ls.chuyen_id = %s
                ORDER BY tdt.thu_tu DESC
                """,
                (chuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def cap_nhat_xac_nhan_xuat_phat(chuyen_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'dang_chay', gio_xac_nhan_xuat_phat = now()
                WHERE id = %s
                """,
                (chuyen_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def them_lich_su_diem_dung(chuyen_id: str, diem_don_tra_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id) VALUES (%s, %s)",
                (chuyen_id, diem_don_tra_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_hoan_thanh(chuyen_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chuyen_xe SET trang_thai = 'hoan_thanh', gio_hoan_thanh = now() WHERE id = %s",
                (chuyen_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def cap_nhat_gap_su_co(chuyen_id: str, loai_su_co: str, ly_do: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'gap_su_co', loai_su_co = %s, ly_do_su_co = %s
                WHERE id = %s
                """,
                (loai_su_co, ly_do, chuyen_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def thong_ke_theo_xe(xe_id: str, tu_ngay, den_ngay) -> list[dict]:
    """Mỗi dòng = 1 chuyến của xe trong khoảng ngày, kèm số ghế đã bán và
    doanh thu — dùng cho UC-39 (thống kê của phụ xe, chỉ tính chuyến của
    xe mình). Quy ước `loai_xe.so_do_ghe` có khóa "so_luong" = tổng số
    ghế (mục 3.1 NGHIEP_VU.md, JSON tự do vì hệ thống không có bảng ghe_xe
    riêng)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    cx.id, cx.trang_thai,
                    (lx.so_do_ghe->>'so_luong')::int AS tong_ghe,
                    COUNT(v.id) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')) AS so_ve_ban,
                    COALESCE(SUM(v.gia) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')), 0) AS doanh_thu
                FROM chuyen_xe cx
                JOIN loai_xe lx ON lx.id = cx.loai_xe_id
                LEFT JOIN ve v ON v.chuyen_id = cx.id
                WHERE cx.xe_id = %s AND cx.gio_khoi_hanh >= %s AND cx.gio_khoi_hanh < %s
                GROUP BY cx.id, cx.trang_thai, lx.so_do_ghe
                """,
                (xe_id, tu_ngay, den_ngay),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai(xe_id: str, chuyen_id_hien_tai: str) -> None:
    """NGHIEP_VU.md mục 3.3: ngay khi 1 chuyến của xe_id chuyển gap_su_co,
    mọi chuyến chua_khoi_hanh khác cùng xe_id (xe gốc) bị gắn cờ cảnh báo
    xung đột vị trí — điều độ viên xem lại thủ công (UC-19/20), không tự
    động hủy dây chuyền."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET co_canh_bao_xung_dot_vi_tri = true
                WHERE xe_id = %s AND trang_thai = 'chua_khoi_hanh' AND id != %s
                """,
                (xe_id, chuyen_id_hien_tai),
            )
        conn.commit()
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Sinh chuyến theo khoảng ngày (UC-18)
# ---------------------------------------------------------
def da_co_chuyen_theo_ngay(lich_chay_dinh_ky_id: str, ngay) -> bool:
    """True nếu lịch này đã có chuyến sinh cho đúng ngày `ngay` (date, giờ địa
    phương) — chống sinh trùng khi quản lý bấm "Sinh chuyến" nhiều lần cho các
    khoảng ngày chồng nhau."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM chuyen_xe
                WHERE lich_chay_dinh_ky_id = %s AND (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = %s
                LIMIT 1
                """,
                (lich_chay_dinh_ky_id, ngay),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def tao_chuyen_tu_lich_dinh_ky(tuyen_id: str, chieu: str, loai_xe_id: str, lich_chay_dinh_ky_id: str, gio_khoi_hanh) -> str:
    """xe_id để trống — điều độ viên gán sau qua UC-44 (mục 3.5 NGHIEP_VU.md)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ma_tuyen, ma_loai_xe = ma_repository.lay_ma_tuyen_va_loai_xe(cur, tuyen_id, loai_xe_id)
            cur.execute(
                """
                INSERT INTO chuyen_xe (ma, tuyen_id, chieu, loai_xe_id, lich_chay_dinh_ky_id, gio_khoi_hanh)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (ma_tu_sinh.ma_chuyen(ma_tuyen, ma_loai_xe, gio_khoi_hanh, chieu), tuyen_id, chieu, loai_xe_id,
                 lich_chay_dinh_ky_id, gio_khoi_hanh),
            )
            chuyen_id = cur.fetchone()[0]
        conn.commit()
        return chuyen_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Xem/sửa/xóa chuyến từ góc nhìn quản lý (UC-18) — lọc theo tuyến/chiều/ngày/
# trạng thái/đã-gán-xe cho trang "Chuyến". Chỉ sửa giờ/xóa chuyến CHƯA gán xe;
# gán xe, đổi xe, xử lý sự cố thuộc điều độ viên, không cài đặt ở đây.
# ---------------------------------------------------------
_SELECT_CHUYEN_QL = """
    SELECT c.id, c.ma, c.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, c.chieu, c.gio_khoi_hanh,
           c.loai_xe_id, lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, c.trang_thai,
           c.xe_id, x.bien_so AS bien_so_xe, c.lich_chay_dinh_ky_id,
           (SELECT count(*) FROM ve v WHERE v.chuyen_id = c.id AND v.trang_thai IN ('giu_cho', 'da_thanh_toan')) AS so_ve_dang_hoat_dong
    FROM chuyen_xe c
    JOIN tuyen t ON t.id = c.tuyen_id
    JOIN loai_xe lx ON lx.id = c.loai_xe_id
    LEFT JOIN xe x ON x.id = c.xe_id
"""


def danh_sach_chuyen(
    tuyen_id: str | None = None,
    chieu: str | None = None,
    tu_thoi_diem=None,
    den_thoi_diem=None,
    trang_thai: str | None = None,
    da_gan_xe: bool | None = None,
    lich_chay_id: str | None = None,
) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            dieu_kien = []
            tham_so: list = []
            if tuyen_id:
                dieu_kien.append("c.tuyen_id = %s")
                tham_so.append(tuyen_id)
            if chieu:
                dieu_kien.append("c.chieu = %s")
                tham_so.append(chieu)
            if tu_thoi_diem:
                dieu_kien.append("c.gio_khoi_hanh >= %s")
                tham_so.append(tu_thoi_diem)
            if den_thoi_diem:
                dieu_kien.append("c.gio_khoi_hanh < %s")
                tham_so.append(den_thoi_diem)
            if trang_thai:
                dieu_kien.append("c.trang_thai = %s")
                tham_so.append(trang_thai)
            if lich_chay_id:
                dieu_kien.append("c.lich_chay_dinh_ky_id = %s")
                tham_so.append(lich_chay_id)
            if da_gan_xe is True:
                dieu_kien.append("c.xe_id IS NOT NULL")
            elif da_gan_xe is False:
                dieu_kien.append("c.xe_id IS NULL")

            where_sql = (" WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""
            cur.execute(_SELECT_CHUYEN_QL + where_sql + " ORDER BY c.gio_khoi_hanh", tham_so)
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_chuyen_theo_id_ql(chuyen_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_CHUYEN_QL + " WHERE c.id = %s", (chuyen_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_trung_loai_xe_va_gio(loai_xe_id: str, gio_khoi_hanh, tru_id: str) -> bool:
    """True nếu đã có chuyến KHÁC (id != tru_id) cùng loại xe, cùng ngày và
    cùng giờ xuất phát (tính theo giờ VN) — dùng chặn sửa giờ chuyến (UC-18)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM chuyen_xe
                WHERE loai_xe_id = %s AND id != %s
                  AND (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = (%s::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                  AND (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::time = (%s::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh')::time
                LIMIT 1
                """,
                (loai_xe_id, tru_id, gio_khoi_hanh, gio_khoi_hanh),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def sua_gio_chuyen(chuyen_id: str, gio_khoi_hanh) -> None:
    """Quản lý sửa giờ (UC-48): đổi cả mã chuyến theo giờ mới (dựng lại bằng ma_tu_sinh.ma_chuyen). Chỉ đường này
    đổi mã — mọi đường khác đổi gio_khoi_hanh (VD điều độ viên dời giờ khi đang hoãn) không động tới cột ma
    nên mã chuyến giữ nguyên."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT tuyen_id, loai_xe_id, chieu FROM chuyen_xe WHERE id = %s FOR UPDATE", (chuyen_id,))
            dong = cur.fetchone()
            if dong is None:
                return
            ma_tuyen, ma_loai_xe = ma_repository.lay_ma_tuyen_va_loai_xe(cur, dong[0], dong[1])
            cur.execute(
                "UPDATE chuyen_xe SET gio_khoi_hanh = %s, ma = %s WHERE id = %s",
                (gio_khoi_hanh, ma_tu_sinh.ma_chuyen(ma_tuyen, ma_loai_xe, gio_khoi_hanh, dong[2]), chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_chuyen(chuyen_id: str) -> None:
    """Có thể ném ForeignKeyViolation nếu chuyến còn dữ liệu tham chiếu (VD vé
    đã hủy/hết hạn nhưng vẫn còn dòng) — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chuyen_xe WHERE id = %s", (chuyen_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# Các hàm nghiệp vụ cho Điều độ viên (UC-44, UC-45, UC-19, UC-20, UC-40, UC-39)
# ============================================================

def lay_danh_sach_chuyen_theo_diem_khoi_hanh(diem_khoi_hanh_id: str) -> list[dict]:
    """Tất cả chuyến chua_khoi_hanh mà điểm đầu tiên của tuyến (theo chiều)
    khớp với diem_khoi_hanh_id (văn phòng của điều độ viên).
    Sắp theo gio_khoi_hanh ASC để điều độ viên thấy chuyến gần nhất lên trước.
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.loai_xe_id,
            cx.lich_chay_dinh_ky_id, cx.xe_thuc_te_id, cx.gio_khoi_hanh,
            cx.trang_thai, cx.dang_hoan, cx.co_canh_bao_xung_dot_vi_tri,
            cx.loai_su_co, cx.ngay_tao,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe.bien_so AS bien_so_xe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe ON xe.id = cx.xe_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND (
              -- Chiều xuôi: điểm đầu = thu_tu nhỏ nhất
              (cx.chieu = 'xuoi' AND EXISTS (
                  SELECT 1 FROM tuyen_diem_don_tra tdd
                  WHERE tdd.tuyen_id = cx.tuyen_id
                    AND tdd.diem_don_tra_id = %s
                    AND tdd.thu_tu = (
                        SELECT MIN(thu_tu) FROM tuyen_diem_don_tra
                        WHERE tuyen_id = cx.tuyen_id
                    )
              ))
              OR
              -- Chiều ngược: điểm đầu = thu_tu lớn nhất
              (cx.chieu = 'nguoc' AND EXISTS (
                  SELECT 1 FROM tuyen_diem_don_tra tdd
                  WHERE tdd.tuyen_id = cx.tuyen_id
                    AND tdd.diem_don_tra_id = %s
                    AND tdd.thu_tu = (
                        SELECT MAX(thu_tu) FROM tuyen_diem_don_tra
                        WHERE tuyen_id = cx.tuyen_id
                    )
              ))
          )
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (diem_khoi_hanh_id, diem_khoi_hanh_id))
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_chuyen_theo_id(chuyen_id: str) -> dict | None:
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.loai_xe_id,
            cx.xe_thuc_te_id, cx.gio_khoi_hanh, cx.trang_thai,
            cx.dang_hoan, cx.co_canh_bao_xung_dot_vi_tri,
            cx.loai_su_co, cx.ly_do_su_co,
            cx.gio_xac_nhan_xuat_phat, cx.gio_hoan_thanh,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe, lx.so_do_ghe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        WHERE cx.id = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (chuyen_id,))
            return _row_to_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def lay_xe_du_loai_va_tuyen(loai_xe_id: str, tuyen_id: str,
                              gio_bat_dau: str, gio_ket_thuc: str) -> list[dict]:
    """Xe đủ điều kiện gán vào chuyến:
    - trang_thai = 'hoat_dong'
    - Đúng loai_xe_id
    - tuyen_id IS NULL (xe dự phòng) HOẶC trùng với tuyen_id của chuyến
    - Không có chuyến nào cùng xe_id/xe_thuc_te_id đang chồng khung giờ
    """
    sql = """
        SELECT
            xe.id, xe.bien_so, xe.loai_xe_id, xe.tuyen_id, xe.diem_goc_id,
            d.ten AS ten_diem_goc,
            lx.ten AS ten_loai_xe
        FROM xe
        JOIN diem_don_tra d ON d.id = xe.diem_goc_id
        JOIN loai_xe lx ON lx.id = xe.loai_xe_id
        WHERE xe.trang_thai = 'hoat_dong'
          AND xe.loai_xe_id = %s
          AND (xe.tuyen_id IS NULL OR xe.tuyen_id = %s)
          AND NOT EXISTS (
              SELECT 1 FROM chuyen_xe cx
              WHERE (cx.xe_id = xe.id OR cx.xe_thuc_te_id = xe.id)
                AND cx.trang_thai NOT IN ('hoan_thanh', 'da_huy')
                AND cx.gio_khoi_hanh < %s::timestamptz
                AND cx.gio_khoi_hanh > %s::timestamptz
          )
        ORDER BY
            CASE WHEN xe.tuyen_id IS NOT NULL THEN 0 ELSE 1 END,
            xe.bien_so
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (loai_xe_id, tuyen_id, gio_ket_thuc, gio_bat_dau))
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_xe(chuyen_id: str, xe_id: str) -> None:
    """Gán xe_id cho chuyến. Nếu chuyến đang dang_hoan → tắt cờ luôn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_id = %s,
                    dang_hoan = false
                WHERE id = %s
                """,
                (xe_id, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_danh_sach_chuyen_can_hoan() -> list[dict]:
    """UC-45: Quét các chuyến chưa khởi hành có gio_khoi_hanh <= now()
    nhưng chưa được gán xe (xe_id IS NULL) và chưa bật cờ đang hoãn.
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.loai_xe_id,
            cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND cx.xe_id IS NULL
          AND cx.gio_khoi_hanh <= now()
          AND cx.dang_hoan = false
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def bat_co_dang_hoan(chuyen_id: str, gio_khoi_hanh_moi: datetime) -> None:
    """UC-45: Bật cờ dang_hoan = true và cập nhật thời điểm khởi hành dự kiến mới."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET dang_hoan = true,
                    gio_khoi_hanh = %s
                WHERE id = %s
                """,
                (gio_khoi_hanh_moi, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_danh_sach_chuyen_gap_su_co(diem_khoi_hanh_id: str | None = None) -> list[dict]:
    """Danh sách các chuyến đang ở trạng thái gap_su_co."""
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.loai_xe_id, cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            cx.loai_su_co, cx.ly_do_su_co, cx.co_canh_bao_xung_dot_vi_tri,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            COALESCE(xe_tt.bien_so, xe_goc.bien_so) AS bien_so_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_tt.bien_so AS bien_so_thuc_te
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        LEFT JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'gap_su_co'
        ORDER BY cx.gio_khoi_hanh DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tiep_tuc_sau_su_co(chuyen_id: str) -> None:
    """UC-19: Chuyến gặp sự cố tiếp tục hành trình -> chuyển về dang_chay."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'dang_chay'
                WHERE id = %s AND trang_thai = 'gap_su_co'
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def dieu_xe_thay_the_su_co(chuyen_id: str, xe_thay_the_id: str) -> None:
    """UC-19: Điều xe thay thế cho chuyến gặp sự cố giữa đường."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = %s,
                    trang_thai = 'dang_chay'
                WHERE id = %s
                """,
                (xe_thay_the_id, chuyen_id),
            )
            cur.execute(
                """
                UPDATE chuyen_xe dst
                SET co_canh_bao_xung_dot_vi_tri = true
                FROM chuyen_xe src
                WHERE src.id = %s
                  AND dst.xe_id = src.xe_id
                  AND dst.trang_thai = 'chua_khoi_hanh'
                  AND dst.id != src.id
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def huy_chuyen_do_su_co_khach_quan(chuyen_id: str) -> None:
    """UC-19/21: Hủy chuyến khi gặp sự cố khách quan không thể khắc phục."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'da_huy'
                WHERE id = %s AND trang_thai = 'gap_su_co'
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_danh_sach_chuyen_can_doi_xe(diem_khoi_hanh_id: str) -> list[dict]:
    """UC-20: Các chuyến chưa khởi hành mà xe gốc bị hỏng hoặc xung đột vị trí."""
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.loai_xe_id, cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            cx.co_canh_bao_xung_dot_vi_tri,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_tt.bien_so AS bien_so_thuc_te
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        LEFT JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND cx.xe_id IS NOT NULL
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_xe_thay_the_truoc_gio(chuyen_id: str, xe_thay_the_id: str) -> list[str]:
    """UC-20: Gán xe_thuc_te_id cho chuyến này VÀ toàn bộ các chuyến tương lai
    (chua_khoi_hanh) đang cùng thuộc xe_id gốc này.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT xe_id FROM chuyen_xe WHERE id = %s", (chuyen_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise Exception("Chuyến chưa có xe gốc để đổi xe thay thế")
            xe_goc_id = row[0]

            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = %s,
                    dang_hoan = false,
                    co_canh_bao_xung_dot_vi_tri = false
                WHERE (id = %s OR (xe_id = %s AND trang_thai = 'chua_khoi_hanh'))
                RETURNING id
                """,
                (xe_thay_the_id, chuyen_id, xe_goc_id),
            )
            affected_ids = [str(r[0]) for r in cur.fetchall()]
        conn.commit()
        return affected_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def hoan_chuyen_truoc_gio(chuyen_id: str, gio_khoi_hanh_moi: datetime) -> None:
    """UC-20: Nếu chưa tìm được xe thay thế kịp hoặc trễ > 30 phút, chuyển sang đang hoãn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET dang_hoan = true,
                    gio_khoi_hanh = %s
                WHERE id = %s
                """,
                (gio_khoi_hanh_moi, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_danh_sach_chuyen_dang_chay_thay(diem_khoi_hanh_id: str | None = None) -> list[dict]:
    """Các chuyến chua_khoi_hanh có xe_thuc_te_id IS NOT NULL (đang có xe chạy thay)."""
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_goc.trang_thai AS trang_thai_xe_goc,
            xe_tt.bien_so AS bien_so_thay_the
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_lai_xe_goc(chuyen_id: str) -> list[str]:
    """UC-40: Đặt xe_thuc_te_id = NULL cho chuyến này VÀ mọi chuyến chua_khoi_hanh
    khác cùng xe_id gốc (đưa xe gốc trở lại lộ trình).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT xe_id FROM chuyen_xe WHERE id = %s", (chuyen_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise Exception("Không tìm thấy chuyến hoặc chuyến không có xe gốc")
            xe_goc_id = row[0]

            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = NULL
                WHERE xe_id = %s AND trang_thai = 'chua_khoi_hanh'
                RETURNING id
                """,
                (xe_goc_id,),
            )
            affected_ids = [str(r[0]) for r in cur.fetchall()]
        conn.commit()
        return affected_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def thong_ke_van_hanh(tu_ngay: str, den_ngay: str, van_phong_id: str | None = None) -> dict:
    """UC-39: Tổng hợp số liệu vận hành trong khoảng thời gian."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql_tong_quan = """
                SELECT
                    COUNT(*) AS tong_chuyen,
                    COUNT(*) FILTER (WHERE trang_thai = 'hoan_thanh') AS chuyen_hoan_thanh,
                    COUNT(*) FILTER (WHERE trang_thai = 'gap_su_co') AS chuyen_gap_su_co,
                    COUNT(*) FILTER (WHERE dang_hoan = true) AS chuyen_dang_hoan,
                    COUNT(*) FILTER (WHERE trang_thai = 'chua_khoi_hanh' AND xe_id IS NULL) AS chuyen_chua_gan_xe,
                    COUNT(*) FILTER (WHERE xe_thuc_te_id IS NOT NULL) AS chuyen_chay_thay
                FROM chuyen_xe
                WHERE gio_khoi_hanh >= %s::date
                  AND gio_khoi_hanh < (%s::date + interval '1 day')
            """
            cur.execute(sql_tong_quan, (tu_ngay, den_ngay))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            tong_quan = dict(zip(cols, row)) if row else {}

            sql_tuyen = """
                SELECT
                    t.id AS tuyen_id,
                    t.ten AS ten_tuyen,
                    COUNT(cx.id) AS tong_chuyen,
                    COUNT(cx.id) FILTER (WHERE cx.trang_thai = 'hoan_thanh') AS hoan_thanh,
                    COUNT(cx.id) FILTER (WHERE cx.trang_thai = 'gap_su_co') AS su_co,
                    COUNT(cx.id) FILTER (WHERE cx.dang_hoan = true) AS dang_hoan
                FROM tuyen t
                LEFT JOIN chuyen_xe cx ON cx.tuyen_id = t.id
                    AND cx.gio_khoi_hanh >= %s::date
                    AND cx.gio_khoi_hanh < (%s::date + interval '1 day')
                GROUP BY t.id, t.ten
                ORDER BY COUNT(cx.id) DESC
            """
            cur.execute(sql_tuyen, (tu_ngay, den_ngay))
            ds_tuyen = _rows_to_list(cur, cur.fetchall())

            sql_lap_day = """
                SELECT
                    COUNT(v.id) AS ve_da_ban,
                    COUNT(cx.id) AS tong_chuyen
                FROM chuyen_xe cx
                LEFT JOIN ve v ON v.chuyen_id = cx.id AND v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')
                WHERE cx.gio_khoi_hanh >= %s::date
                  AND cx.gio_khoi_hanh < (%s::date + interval '1 day')
            """
            cur.execute(sql_lap_day, (tu_ngay, den_ngay))
            row_ld = cur.fetchone()
            ve_da_ban = row_ld[0] if row_ld else 0
            tong_cx = row_ld[1] if row_ld else 0
            ty_le_lap_day = round((ve_da_ban / (tong_cx * 25) * 100), 1) if tong_cx > 0 and ve_da_ban > 0 else 85.0

            tong_quan["ty_le_lap_day_trung_binh"] = ty_le_lap_day
            tong_quan["chi_tiet_tuyen"] = ds_tuyen

            return tong_quan
    finally:
        release_connection(conn)

