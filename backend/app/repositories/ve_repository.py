"""Raw SQL cho bảng ve — DATABASE.md mục 4.

Chỉ chứa các hàm cần cho phần phụ xe (soát vé lên/xuống xe — UC-12/13).
Giữ ghế, chống trùng ghế (SELECT ... FOR UPDATE + kiểm tra overlap,
NGHIEP_VU.md mục 6), đặt vé/thanh toán thuộc phần khách hàng + quầy vé,
chưa cài đặt ở đây — theo đúng CONTRIBUTING.md mục 5.1, đây sẽ là file
riêng `ve_lock_repository.py` khi làm tới phần đó.
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


def tim_theo_id(ve_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id,
                       ten_khach_vang_lai, sdt_khach_vang_lai, trang_thai
                FROM ve WHERE id = %s
                """,
                (ve_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_ve_can_len_xe_tai_diem(chuyen_id: str, diem_don_tra_id: str) -> list[dict]:
    """Khách đã trả tiền, cần lên xe tại đúng điểm đón này — NGHIEP_VU.md mục 8.2 điểm 1/3."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id AS ve_id, v.so_ghe, v.ma_dat_cho,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ho_ten,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS so_dien_thoai
                FROM ve v
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                WHERE v.chuyen_id = %s AND v.diem_don_id = %s AND v.trang_thai = 'da_thanh_toan'
                ORDER BY v.so_ghe ASC
                """,
                (chuyen_id, diem_don_tra_id),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_ve_can_xuong_xe_tai_diem(chuyen_id: str, diem_don_tra_id: str) -> list[dict]:
    """Khách đã lên xe, cần xuống tại đúng điểm trả này — NGHIEP_VU.md mục 8.2 điểm 4."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id AS ve_id, v.so_ghe, v.ma_dat_cho,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ho_ten,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS so_dien_thoai
                FROM ve v
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                WHERE v.chuyen_id = %s AND v.diem_tra_id = %s AND v.trang_thai = 'da_len_xe'
                ORDER BY v.so_ghe ASC
                """,
                (chuyen_id, diem_don_tra_id),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_ve_qua_gio_len_xe(x_phut: int) -> list[dict]:
    """UC-14 (⏱) — vé chưa lên xe nhưng đã quá X phút trước giờ dự kiến
    tại đúng điểm đón của nó (NGHIEP_VU.md mục 8.2 điểm 6) — áp dụng như
    nhau cho vé đã trả tiền (da_thanh_toan) lẫn đang giữ chỗ chờ trả tại
    quầy (giu_cho, mục 9)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.khach_hang_id
                FROM ve v
                JOIN chuyen_xe cx ON cx.id = v.chuyen_id
                JOIN tuyen_diem_don_tra tdt
                    ON tdt.tuyen_id = cx.tuyen_id AND tdt.diem_don_tra_id = v.diem_don_id
                WHERE v.trang_thai IN ('da_thanh_toan', 'giu_cho')
                  AND cx.trang_thai != 'da_huy'
                  AND cx.gio_khoi_hanh + (tdt.thoi_gian_du_kien_phut || ' minutes')::interval
                        - (%s || ' minutes')::interval <= now()
                """,
                (x_phut,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_dau_khong_den(ve_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE ve SET trang_thai = 'khong_den' WHERE id = %s", (ve_id,))
        conn.commit()
    finally:
        release_connection(conn)


def dem_vi_pham_no_show(khach_hang_id: str, so_ngay_gan_day: int) -> int:
    """NGHIEP_VU.md mục 9 — đếm động, không lưu cột riêng. Tính theo giờ
    chuyến đã diễn ra (chuyen_xe.gio_khoi_hanh), không phải lúc đặt vé —
    khách có thể đặt vé từ nhiều tuần trước."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM ve v
                JOIN chuyen_xe cx ON cx.id = v.chuyen_id
                WHERE v.khach_hang_id = %s AND v.trang_thai = 'khong_den'
                      AND cx.gio_khoi_hanh >= now() - (%s || ' days')::interval
                """,
                (khach_hang_id, so_ngay_gan_day),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def tim_khach_cho_don_sau_diem(chuyen_id: str, thu_tu_hien_tai: int) -> list[dict]:
    """Khách có tài khoản, vé còn hiệu lực, đón tại 1 điểm PHÍA SAU điểm
    phụ xe vừa xác nhận đến — dùng để báo cập nhật ETA qua WebSocket
    (NGHIEP_VU.md mục 8.2 điểm 5)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT v.khach_hang_id
                FROM ve v
                JOIN chuyen_xe cx ON cx.id = v.chuyen_id
                JOIN tuyen_diem_don_tra tdt
                    ON tdt.tuyen_id = cx.tuyen_id AND tdt.diem_don_tra_id = v.diem_don_id
                WHERE v.chuyen_id = %s AND v.trang_thai IN ('da_thanh_toan', 'giu_cho')
                      AND v.khach_hang_id IS NOT NULL AND tdt.thu_tu > %s
                """,
                (chuyen_id, thu_tu_hien_tai),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_khach_hang_dang_hoat_dong_theo_chuyen(chuyen_id: str) -> list[dict]:
    """Khách có tài khoản, vé còn hiệu lực trên 1 chuyến — dùng để báo sự
    cố qua WebSocket (NGHIEP_VU.md mục 8.1 điểm 4)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT khach_hang_id
                FROM ve
                WHERE chuyen_id = %s AND khach_hang_id IS NOT NULL
                      AND trang_thai IN ('da_thanh_toan', 'giu_cho', 'da_len_xe')
                """,
                (chuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xac_nhan_len_xe(ve_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_len_xe', gio_len_xe = now() WHERE id = %s",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def xac_nhan_xuong_xe(ve_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_xuong_xe', gio_xuong_xe = now() WHERE id = %s",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)
