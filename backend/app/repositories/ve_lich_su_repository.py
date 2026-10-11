"""Vé của khách cho trang Booking (xem vé, hủy 1 vé, thanh toán riêng 1 vé) — NGHIEP_VU.md mục 5, 6.

Tách khỏi ve_lock_repository.py (khóa ghế, CONTRIBUTING.md mục 5.1) và chỉ SELECT: vé của đúng 1 khách, kèm thông tin
chuyến, tuyến, biển số xe (xe thực tế nếu đã đổi, không thì xe gán ban đầu), điểm đón/trả và giờ dự kiến tại 2 điểm đó
(cùng cách tính với ve_lock_repository.lay_dat_cho).
"""

from app.db import get_connection, release_connection

SO_LUOT_TOI_DA = 100  # lấy tối đa chừng này lượt đặt gần nhất

_CAC_COT_VA_BANG = """
    SELECT v.id, v.ma_ve, v.so_ghe, v.gia, v.trang_thai, v.loai_hinh_thanh_toan, v.la_ve_dat_coc,
           v.han_giu_cho_den, v.gio_bat_dau_dem_han, v.gio_thanh_toan, v.ma_dat_cho, v.ngay_tao,
           v.chuyen_id, c.ma AS ma_chuyen, c.gio_khoi_hanh, c.trang_thai AS trang_thai_chuyen,
           lx.ten AS ten_loai_xe, tu.ten AS ten_tuyen, x.bien_so,
           dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra,
           c.gio_khoi_hanh + make_interval(mins =>
               CASE WHEN c.chieu = 'xuoi' THEN a.thoi_gian_du_kien_phut
                    ELSE tong.tong_phut - a.thoi_gian_du_kien_phut END) AS gio_don_du_kien,
           c.gio_khoi_hanh + make_interval(mins =>
               CASE WHEN c.chieu = 'xuoi' THEN b.thoi_gian_du_kien_phut
                    ELSE tong.tong_phut - b.thoi_gian_du_kien_phut END) AS gio_den_du_kien
    FROM ve v
    {them_bang}
    JOIN chuyen_xe c ON c.id = v.chuyen_id
    JOIN tuyen tu ON tu.id = c.tuyen_id
    JOIN loai_xe lx ON lx.id = c.loai_xe_id
    LEFT JOIN xe x ON x.id = COALESCE(c.xe_thuc_te_id, c.xe_id)
    JOIN diem_don_tra dd ON dd.id = v.diem_don_id
    JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
    JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
    JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
    JOIN (SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
          FROM tuyen_diem_don_tra GROUP BY tuyen_id) tong ON tong.tuyen_id = c.tuyen_id
"""


def _thanh_list(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def lay_ve_cua_khach(khach_hang_id: str, so_luot_toi_da: int = SO_LUOT_TOI_DA) -> list[dict]:
    """Mọi vé của `so_luot_toi_da` lượt đặt gần nhất của khách (mới nhất trước); các vé cùng lượt nằm liền nhau."""
    sql = (
        _CAC_COT_VA_BANG.format(
            them_bang="""JOIN (SELECT ma_dat_cho, MAX(ngay_tao) AS gan_nhat FROM ve WHERE khach_hang_id = %s
                             GROUP BY ma_dat_cho ORDER BY MAX(ngay_tao) DESC LIMIT %s) lan_cuoi ON lan_cuoi.ma_dat_cho = v.ma_dat_cho"""
        )
        + " WHERE v.khach_hang_id = %s ORDER BY lan_cuoi.gan_nhat DESC, v.ma_dat_cho, v.so_ghe"
    )
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (khach_hang_id, so_luot_toi_da, khach_hang_id))
            return _thanh_list(cur)
    finally:
        release_connection(conn)


def lay_ve_theo_id(ve_id: str, khach_hang_id: str) -> dict | None:
    """1 vé thuộc đúng khách này (vé của khách khác không xem được dù đoán trúng mã)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_CAC_COT_VA_BANG.format(them_bang="") + " WHERE v.id = %s AND v.khach_hang_id = %s", (ve_id, khach_hang_id))
            ket_qua = _thanh_list(cur)
            return ket_qua[0] if ket_qua else None
    finally:
        release_connection(conn)
