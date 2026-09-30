"""Raw SQL cho bảng chuyen_xe/lich_su_diem_dung_chuyen — DATABASE.md mục 3.3, 3.4.

Chứa các hàm cho phần phụ xe (xem chuyến của mình, xác nhận xuất phát/tới
điểm/sự cố — UC-15,16,17), sinh chuyến theo khoảng ngày, và xem/sửa/xóa chuyến
từ góc nhìn quản lý (UC-18, cuối file — gọi từ lich_chay_service.py). Gán xe
(UC-44), đổi xe khi hỏng (UC-19/20/40) thuộc điều độ viên, chưa cài đặt ở đây.
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


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
            cur.execute(
                """
                INSERT INTO chuyen_xe (tuyen_id, chieu, loai_xe_id, lich_chay_dinh_ky_id, gio_khoi_hanh)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (tuyen_id, chieu, loai_xe_id, lich_chay_dinh_ky_id, gio_khoi_hanh),
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
    """Quản lý sửa giờ (UC-48): đổi cả mã chuyến theo giờ mới. Cờ SET LOCAL chỉ sống trong giao dịch
    này — mọi đường khác đổi gio_khoi_hanh (VD điều độ viên dời giờ khi đang hoãn) không bật cờ nên
    mã chuyến giữ nguyên (trigger cap_nhat_ma_chuyen_xe, migration 20260930_1100)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.doi_ma_theo_gio = 'on'")
            cur.execute("UPDATE chuyen_xe SET gio_khoi_hanh = %s WHERE id = %s", (gio_khoi_hanh, chuyen_id))
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
