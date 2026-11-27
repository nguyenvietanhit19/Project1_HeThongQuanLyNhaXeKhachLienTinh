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
                       ten_khach_vang_lai, sdt_khach_vang_lai, trang_thai, ma_ve, gio_thanh_toan
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


def tim_hanh_khach_cua_chuyen(chuyen_id: str) -> list[dict]:
    """Mọi hành khách của chuyến (kể cả đã xuống xe / không đến) kèm trạng thái và
    điểm đón/trả — màn "tổng quan chuyến" của phụ xe (mục 8.2 điểm 1). Không lấy vé
    hết hạn/đã hủy vì khách đó không còn đi chuyến này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id AS ve_id, v.so_ghe, v.ma_dat_cho, v.trang_thai, v.diem_don_id, v.diem_tra_id,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ho_ten,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS so_dien_thoai,
                       dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra,
                       v.gia, v.loai_hinh_thanh_toan, v.gio_len_xe, v.gio_xuong_xe,
                       (v.gio_hoan_tac IS NOT NULL) AS da_hoan_tac,
                       (v.gio_thanh_toan IS NOT NULL) AS da_tra_tien
                FROM ve v
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                WHERE v.chuyen_id = %s
                  AND v.trang_thai IN ('giu_cho', 'da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den')
                ORDER BY length(v.so_ghe), v.so_ghe
                """,
                (chuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_dau_khong_den(ve_id: str) -> bool:
    """Vé đã trả tiền, hoặc vé trả tại quầy chưa trả (không có hạn giữ) → `khong_den`. False nếu vé không còn ở trạng thái đó."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET trang_thai = 'khong_den'
                   WHERE id = %s AND (trang_thai = 'da_thanh_toan' OR (trang_thai = 'giu_cho' AND han_giu_cho_den IS NULL))""",
                (ve_id,),
            )
            da_sua = cur.rowcount > 0
        conn.commit()
        return da_sua
    finally:
        release_connection(conn)


def hoan_tac_khong_den(ve_id: str) -> bool:
    """khong_den → da_len_xe, CHỈ với vé đã trả tiền (có gio_thanh_toan) — vé chưa trả tiền không được ghi nhận lên xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET trang_thai = 'da_len_xe', gio_len_xe = now(), gio_hoan_tac = now()
                   WHERE id = %s AND trang_thai = 'khong_den' AND gio_thanh_toan IS NOT NULL""",
                (ve_id,),
            )
            da_sua = cur.rowcount > 0
        conn.commit()
        return da_sua
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
    (NGHIEP_VU.md mục 8.2 điểm 5). "Phía sau" tính THEO HƯỚNG ĐI: chuyến
    xuôi là thu_tu lớn hơn, chuyến ngược là thu_tu nhỏ hơn."""
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
                      AND v.khach_hang_id IS NOT NULL
                      AND CASE WHEN cx.chieu = 'xuoi' THEN tdt.thu_tu > %s ELSE tdt.thu_tu < %s END
                """,
                (chuyen_id, thu_tu_hien_tai, thu_tu_hien_tai),
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


def hoan_tac_len_xe(ve_id: str) -> bool:
    """da_len_xe -> da_thanh_toan. Điều kiện nằm trong WHERE để 2 lần bấm
    liên tiếp không làm hỏng trạng thái. Trả False nếu vé không còn da_len_xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET trang_thai = 'da_thanh_toan', gio_len_xe = NULL, gio_hoan_tac = now()
                   WHERE id = %s AND trang_thai = 'da_len_xe'""",
                (ve_id,),
            )
            da_sua = cur.rowcount > 0
        conn.commit()
        return da_sua
    finally:
        release_connection(conn)


def hoan_tac_xuong_xe(ve_id: str) -> bool:
    """da_xuong_xe -> da_len_xe (khách vẫn đang trên xe)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET trang_thai = 'da_len_xe', gio_xuong_xe = NULL, gio_hoan_tac = now()
                   WHERE id = %s AND trang_thai = 'da_xuong_xe'""",
                (ve_id,),
            )
            da_sua = cur.rowcount > 0
        conn.commit()
        return da_sua
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


def tim_ve_chua_len_tai_diem(chuyen_id: str, diem_don_id: str) -> list[dict]:
    """Vé chưa lên xe tại điểm đón này: đã thanh toán, hoặc đang giữ chỗ còn hiệu lực (gồm "thanh toán tại quầy" —
    không có hạn). Vé giữ chỗ quá hạn không tính vì ghế đã mở lại (het_han). NGHIEP_VU.md mục 8.2 điểm 6, mục 9."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.id AS ve_id, v.khach_hang_id, v.ma_ve, v.so_ghe, v.trang_thai, v.ma_dat_cho, v.han_giu_cho_den,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ho_ten
                FROM ve v
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                WHERE v.chuyen_id = %s AND v.diem_don_id = %s
                  AND (v.trang_thai = 'da_thanh_toan'
                       OR (v.trang_thai = 'giu_cho' AND (v.han_giu_cho_den IS NULL OR v.han_giu_cho_den > now())))
                ORDER BY length(v.so_ghe), v.so_ghe
                """,
                (chuyen_id, diem_don_id),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
