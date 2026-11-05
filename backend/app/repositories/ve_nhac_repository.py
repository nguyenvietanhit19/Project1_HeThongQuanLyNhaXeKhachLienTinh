"""Vé cần nhắc "sắp đến giờ đi" (job quet_nhac_sap_di) — chỉ phục vụ thông báo cho khách, NGHIEP_VU.md mục 8.1 điểm 4.

Chỉ nhắc vé đã chắc chắn đi: đã trả tiền, hoặc đã chốt "trả tại quầy" (không hạn giữ chỗ); không nhắc vé đang giữ tạm 10 phút hay
đang chờ trả VNPay (khách còn đang thao tác, giỏ hàng đã báo). Mốc là giờ dự kiến tại ĐÚNG điểm đón của vé (không phải giờ xuất
bến), cùng cách tính với ve_lock_repository.lay_dat_cho.
"""

from app.db import get_connection, release_connection


def tim_ve_can_nhac(phut_truoc_gio_don: int) -> list[dict]:
    """Vé của khách có tài khoản, chuyến chưa khởi hành, giờ đón rơi trong `phut_truoc_gio_don` phút tới, chưa từng được nhắc."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM (
                    SELECT v.id, v.ma_dat_cho, v.so_ghe, v.khach_hang_id, dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra,
                           c.gio_khoi_hanh + make_interval(mins =>
                               CASE WHEN c.chieu = 'xuoi' THEN a.thoi_gian_du_kien_phut
                                    ELSE tong.tong_phut - a.thoi_gian_du_kien_phut END) AS gio_don_du_kien
                    FROM ve v
                    JOIN chuyen_xe c ON c.id = v.chuyen_id
                    JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                    JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                    JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                    JOIN (SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
                          FROM tuyen_diem_don_tra GROUP BY tuyen_id) tong ON tong.tuyen_id = c.tuyen_id
                    WHERE v.khach_hang_id IS NOT NULL AND v.da_nhac_sap_di = false
                      AND (v.trang_thai = 'da_thanh_toan' OR (v.trang_thai = 'giu_cho' AND v.han_giu_cho_den IS NULL))
                      AND c.trang_thai = 'chua_khoi_hanh'
                ) x
                WHERE x.gio_don_du_kien > now() AND x.gio_don_du_kien <= now() + make_interval(mins => %s)
                ORDER BY x.gio_don_du_kien, x.ma_dat_cho, x.so_ghe
                """,
                (phut_truoc_gio_don,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def danh_dau_da_nhac(ve_ids: list[str]) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE ve SET da_nhac_sap_di = true WHERE id = ANY(%s::uuid[])", ([str(i) for i in ve_ids],))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
