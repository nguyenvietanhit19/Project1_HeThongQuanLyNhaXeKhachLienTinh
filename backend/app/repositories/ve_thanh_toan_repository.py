"""Chuyển trạng thái vé theo kết quả thanh toán VNPay (UC-05 nhánh "thanh toán ngay") — NGHIEP_VU.md mục 3.4, 6.

Tách khỏi ve_lock_repository.py (chỉ lo khóa ghế/chống trùng) nhưng dùng chung điều kiện "vé còn đang giữ chỗ".
Không chứa quy tắc nghiệp vụ — việc ai trả vé nào, cọc bao nhiêu thuộc services/dat_ve_service.py.
"""

import datetime

from app.db import get_connection, release_connection
from app.repositories.ve_lock_repository import _DANG_GIU_CHO, _thanh_list
from app.utils.loi import GiaTriLoi


def bat_dau_thanh_toan_qr_quay(ma_dat_cho: str, van_phong_id: str, ma_giao_dich: str,
                              han_phut: int) -> dict:
    """Khóa toàn bộ lượt tại quầy và gán một mã VNPay, một hạn thanh toán cho mọi ghế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT v.trang_thai, v.gia, v.han_giu_cho_den, v.ma_tham_chieu_vnpay,
                          v.kenh_ban, c.gio_khoi_hanh
                   FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
                   WHERE v.ma_dat_cho = %s AND v.diem_don_id = %s
                   ORDER BY v.id FOR UPDATE OF v""",
                (ma_dat_cho, van_phong_id),
            )
            ve = _thanh_list(cur, cur.fetchall())
            now = datetime.datetime.now(datetime.timezone.utc)
            if not ve or any(v["kenh_ban"] not in ("tai_quay", "hotline") for v in ve):
                raise GiaTriLoi("Không tìm thấy lượt đặt tại văn phòng này")
            if any(v["trang_thai"] != "giu_cho" or v["gio_khoi_hanh"] <= now or
                   (v["han_giu_cho_den"] is not None and v["han_giu_cho_den"] <= now) for v in ve):
                raise GiaTriLoi("Lượt đặt đã thanh toán, hết hạn hoặc không còn mở bán")
            tham_chieu = {v["ma_tham_chieu_vnpay"] for v in ve if v["ma_tham_chieu_vnpay"]}
            if len(tham_chieu) > 1 or any(ref.startswith("VE") for ref in tham_chieu):
                raise GiaTriLoi("Lượt đặt đã có giao dịch thanh toán riêng; vui lòng tra cứu lại")
            ref = next(iter(tham_chieu), ma_giao_dich)
            han = min([now + datetime.timedelta(minutes=han_phut)] +
                      [v["han_giu_cho_den"] for v in ve if v["han_giu_cho_den"] is not None] +
                      [v["gio_khoi_hanh"] for v in ve])
            cur.execute(
                """UPDATE ve SET loai_hinh_thanh_toan = 'thanh_toan_ngay',
                          han_giu_cho_den = %s, ma_tham_chieu_vnpay = %s,
                          gio_bat_dau_dem_han = COALESCE(gio_bat_dau_dem_han, now())
                   WHERE ma_dat_cho = %s AND diem_don_id = %s AND trang_thai = 'giu_cho'""",
                (han, ref, ma_dat_cho, van_phong_id),
            )
            if cur.rowcount != len(ve):
                raise GiaTriLoi("Lượt đặt vừa thay đổi, vui lòng tải lại")
        conn.commit()
        return {"ma_giao_dich": ref, "han_thanh_toan": han,
                "tong_tien": sum(int(v["gia"]) for v in ve), "so_ve": len(ve)}
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def bat_dau_thanh_toan_ngay(
    ma_dat_cho: str,
    khach_hang_id: str,
    so_ghe_online: list[str],
    so_ghe_tai_quay: list[str],
    so_ve_con_giu: int,
    han_phut: int,
    la_dat_coc: bool,
) -> bool:
    """Khách bấm "Thanh toán" bằng VNPay: bắt đầu tính hạn (mặc định 5 phút) từ đúng lúc này (mục 6).

    - `so_ghe_online`: các vé trả qua VNPay (chuyển `thanh_toan_ngay`, đánh dấu cọc nếu lô thuộc diện đặt cọc);
    - `so_ghe_tai_quay`: các vé còn lại của lô cọc, sẽ trả tại quầy — GIỮ cùng hạn, chỉ được chốt khi phần cọc trả xong
      (không xong trong hạn thì cả lô `het_han`, mục 3.4);
    - các ghế khác trong lượt đặt (không tích) bị nhả ngay (`da_huy`).
    Cùng 1 transaction; chỉ thành công nếu đủ `so_ve_con_giu` vé còn sống."""
    chon = so_ghe_online + so_ghe_tai_quay
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE ve v SET trang_thai = 'da_huy', gio_huy = now()
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe <> ALL(%s)
                """,
                (ma_dat_cho, khach_hang_id, chon),
            )
            so_nha = cur.rowcount
            cur.execute(
                f"""
                UPDATE ve v SET loai_hinh_thanh_toan = 'thanh_toan_ngay', la_ve_dat_coc = %s,
                       gio_bat_dau_dem_han = now(), han_giu_cho_den = now() + make_interval(mins => %s)
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe = ANY(%s)
                """,
                (la_dat_coc, han_phut, ma_dat_cho, khach_hang_id, so_ghe_online),
            )
            so_online = cur.rowcount
            so_quay = 0
            if so_ghe_tai_quay:
                cur.execute(
                    f"""
                    UPDATE ve v SET loai_hinh_thanh_toan = 'thanh_toan_tai_quay',
                           han_giu_cho_den = now() + make_interval(mins => %s)
                    WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe = ANY(%s)
                    """,
                    (han_phut, ma_dat_cho, khach_hang_id, so_ghe_tai_quay),
                )
                so_quay = cur.rowcount
            if so_online != len(so_ghe_online) or so_quay != len(so_ghe_tai_quay) or so_online + so_quay + so_nha != so_ve_con_giu:
                conn.rollback()
                return False
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_ve_cua_dat_cho(ma_dat_cho: str) -> list[dict]:
    """Mọi vé của 1 lượt đặt, KHÔNG lọc theo khách — chỉ dành cho xử lý IPN của cổng thanh toán (không có đăng nhập)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma_ve, so_ghe, gia, trang_thai, loai_hinh_thanh_toan, han_giu_cho_den,
                       khach_hang_id, kenh_ban, ma_tham_chieu_vnpay
                FROM ve WHERE ma_dat_cho = %s ORDER BY so_ghe
                """,
                (ma_dat_cho,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def ghi_nhan_thanh_toan_ngay(ma_dat_cho: str, ma_giao_dich_cong_thanh_toan: str,
                             ma_tham_chieu: str | None = None, so_ve_ky_vong: int | None = None) -> int:
    """IPN báo thành công: các vé trả VNPay còn trong hạn → `da_thanh_toan` (`chuyen_khoan`, lưu mã giao dịch của cổng);
    các vé trả tại quầy đang chờ phần cọc được chốt luôn (bỏ hạn). Trả số vé đã thanh toán (0 = quá hạn/không còn vé nào)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'da_thanh_toan', phuong_thuc_thanh_toan = 'chuyen_khoan',
                       ma_giao_dich_cong_thanh_toan = %s, gio_thanh_toan = now(), han_giu_cho_den = NULL,
                       nhan_vien_thu_id = COALESCE(nhan_vien_thu_id, nhan_vien_ban_id)
                WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho' AND loai_hinh_thanh_toan = 'thanh_toan_ngay'
                  AND (%s IS NULL OR ma_tham_chieu_vnpay = %s)
                  AND han_giu_cho_den IS NOT NULL AND han_giu_cho_den > now()
                  AND EXISTS (SELECT 1 FROM chuyen_xe c
                              WHERE c.id = ve.chuyen_id AND c.gio_khoi_hanh > now())
                """,
                (ma_giao_dich_cong_thanh_toan, ma_dat_cho, ma_tham_chieu, ma_tham_chieu),
            )
            so_da_tra = cur.rowcount
            if so_ve_ky_vong is not None and so_da_tra != so_ve_ky_vong:
                conn.rollback()
                return 0
            if so_da_tra:
                cur.execute(
                    """
                    UPDATE ve SET han_giu_cho_den = NULL, gio_bat_dau_dem_han = NULL
                    WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho' AND loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                    """,
                    (ma_dat_cho,),
                )
        conn.commit()
        return so_da_tra
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def huy_thanh_toan_ngay(ma_dat_cho: str, ma_tham_chieu: str | None = None) -> int:
    """IPN báo thất bại/khách hủy: cả lượt đặt đang giữ chỗ → `het_han`, ghế mở lại (mục 3.4, mục 6)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET trang_thai = 'het_han' WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho'
                   AND (%s IS NULL OR ma_tham_chieu_vnpay = %s)""",
                (ma_dat_cho, ma_tham_chieu, ma_tham_chieu),
            )
            so_ve = cur.rowcount
        conn.commit()
        return so_ve
    finally:
        release_connection(conn)


def luu_ma_tham_chieu_vnpay(ma_dat_cho: str, ma_giao_dich: str) -> None:
    """Ghi lại mã giao dịch của lần tạo đường dẫn thanh toán gần nhất, để sau này hỏi VNPay (querydr) kết quả."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET ma_tham_chieu_vnpay = %s
                WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho' AND loai_hinh_thanh_toan = 'thanh_toan_ngay'
                """,
                (ma_giao_dich, ma_dat_cho),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_ma_giao_dich_dang_cho() -> list[str]:
    """Mã giao dịch VNPay của các lượt đang chờ thanh toán còn trong hạn — job hỏi VNPay kết quả cho từng lượt."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ma_tham_chieu_vnpay FROM ve
                WHERE trang_thai = 'giu_cho' AND ma_tham_chieu_vnpay IS NOT NULL
                  AND ((loai_hinh_thanh_toan = 'thanh_toan_ngay' AND han_giu_cho_den > now())
                       OR (loai_hinh_thanh_toan = 'thanh_toan_tai_quay' AND han_giu_cho_den IS NULL))
                """
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Từng vé riêng lẻ (trang Booking): hủy 1 vé, thanh toán riêng 1 vé "thanh toán tại quầy"
# ---------------------------------------------------------
def huy_ve_dang_giu(ve_id: str, khach_hang_id: str) -> bool:
    """Khách tự hủy 1 vé còn đang giữ chỗ (chưa trả tiền): `da_huy`, ghế mở lại ngay. False nếu vé không còn giữ chỗ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE ve v SET trang_thai = 'da_huy', gio_huy = now()
                WHERE v.id = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO}
                """,
                (ve_id, khach_hang_id),
            )
            da_huy = cur.rowcount == 1
        conn.commit()
        return da_huy
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_ve_theo_ma_ve(ma_ve: str) -> dict | None:
    """Vé theo mã vé, KHÔNG lọc theo khách — chỉ dành cho xử lý kết quả của cổng thanh toán (không có đăng nhập)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma_ve, so_ghe, ma_dat_cho, gia, trang_thai, loai_hinh_thanh_toan, han_giu_cho_den,
                       khach_hang_id, ma_tham_chieu_vnpay
                FROM ve WHERE ma_ve = %s
                """,
                (ma_ve,),
            )
            ket_qua = _thanh_list(cur, cur.fetchall())
            return ket_qua[0] if ket_qua else None
    finally:
        release_connection(conn)


def luu_ma_tham_chieu_vnpay_ve(ve_id: str, ma_giao_dich: str, han_giu_cho_den=None) -> bool:
    """Ghi tham chiếu VNPay và hạn ghế cho link thanh toán riêng của vé quầy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE ve SET ma_tham_chieu_vnpay = %s,
                          han_giu_cho_den = COALESCE(%s, han_giu_cho_den)
                   WHERE id = %s AND trang_thai = 'giu_cho'
                     AND (han_giu_cho_den IS NULL OR han_giu_cho_den > now())
                     AND EXISTS (SELECT 1 FROM chuyen_xe c
                                 WHERE c.id = ve.chuyen_id AND c.gio_khoi_hanh > now())""",
                (ma_giao_dich, han_giu_cho_den, ve_id),
            )
            updated = cur.rowcount
        conn.commit()
        return updated == 1
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def ghi_nhan_thanh_toan_ve_le(ma_ve: str, ma_tham_chieu_vnpay: str, ma_giao_dich_cong_thanh_toan: str) -> int:
    """Cổng báo thanh toán thành công cho 1 vé "trả tại quầy" đã chốt (không hạn): → `da_thanh_toan` (`chuyen_khoan`).
    Trả 1 nếu ghi nhận được, 0 nếu vé không còn ở trạng thái đó (đã hủy/hết hạn/đã trả)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'da_thanh_toan', phuong_thuc_thanh_toan = 'chuyen_khoan',
                       ma_giao_dich_cong_thanh_toan = %s, gio_thanh_toan = now(),
                       nhan_vien_thu_id = nhan_vien_ban_id
                WHERE ma_ve = %s AND trang_thai = 'giu_cho'
                  AND loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                  AND ma_tham_chieu_vnpay = %s
                  AND (han_giu_cho_den IS NULL OR han_giu_cho_den > now())
                  AND EXISTS (SELECT 1 FROM chuyen_xe c
                              WHERE c.id = ve.chuyen_id AND c.gio_khoi_hanh > now())
                """,
                (ma_giao_dich_cong_thanh_toan, ma_ve, ma_tham_chieu_vnpay),
            )
            so_ve = cur.rowcount
        conn.commit()
        return so_ve
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
