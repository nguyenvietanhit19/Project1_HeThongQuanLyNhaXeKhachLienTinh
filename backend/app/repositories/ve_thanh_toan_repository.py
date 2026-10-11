"""Chuyển trạng thái vé theo kết quả thanh toán VNPay (UC-05 nhánh "thanh toán ngay") — NGHIEP_VU.md mục 3.4, 6.

Tách khỏi ve_lock_repository.py (chỉ lo khóa ghế/chống trùng) nhưng dùng chung điều kiện "vé còn đang giữ chỗ".
Không chứa quy tắc nghiệp vụ — việc ai trả vé nào, cọc bao nhiêu thuộc services/dat_ve_service.py.
"""

from app.db import get_connection, release_connection
from app.repositories.ve_lock_repository import _DANG_GIU_CHO, _thanh_list


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
                SELECT id, ma_ve, so_ghe, gia, trang_thai, loai_hinh_thanh_toan, han_giu_cho_den, khach_hang_id
                FROM ve WHERE ma_dat_cho = %s ORDER BY so_ghe
                """,
                (ma_dat_cho,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def ghi_nhan_thanh_toan_ngay(ma_dat_cho: str, ma_giao_dich_cong_thanh_toan: str) -> int:
    """IPN báo thành công: các vé trả VNPay còn trong hạn → `da_thanh_toan` (`chuyen_khoan`, lưu mã giao dịch của cổng);
    các vé trả tại quầy đang chờ phần cọc được chốt luôn (bỏ hạn). Trả số vé đã thanh toán (0 = quá hạn/không còn vé nào)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'da_thanh_toan', phuong_thuc_thanh_toan = 'chuyen_khoan',
                       ma_giao_dich_cong_thanh_toan = %s, gio_thanh_toan = now(), han_giu_cho_den = NULL
                WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho' AND loai_hinh_thanh_toan = 'thanh_toan_ngay'
                  AND han_giu_cho_den IS NOT NULL AND han_giu_cho_den > now()
                """,
                (ma_giao_dich_cong_thanh_toan, ma_dat_cho),
            )
            so_da_tra = cur.rowcount
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


def huy_thanh_toan_ngay(ma_dat_cho: str) -> int:
    """IPN báo thất bại/khách hủy: cả lượt đặt đang giữ chỗ → `het_han`, ghế mở lại (mục 3.4, mục 6)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'het_han' WHERE ma_dat_cho = %s AND trang_thai = 'giu_cho'",
                (ma_dat_cho,),
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
                SELECT id, ma_ve, so_ghe, ma_dat_cho, gia, trang_thai, loai_hinh_thanh_toan, han_giu_cho_den, khach_hang_id
                FROM ve WHERE ma_ve = %s
                """,
                (ma_ve,),
            )
            ket_qua = _thanh_list(cur, cur.fetchall())
            return ket_qua[0] if ket_qua else None
    finally:
        release_connection(conn)


def luu_ma_tham_chieu_vnpay_ve(ve_id: str, ma_giao_dich: str) -> None:
    """Ghi lại mã giao dịch của lần thanh toán riêng 1 vé gần nhất, để sau này hỏi VNPay (querydr) kết quả."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE ve SET ma_tham_chieu_vnpay = %s WHERE id = %s", (ma_giao_dich, ve_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def ghi_nhan_thanh_toan_ve_le(ma_ve: str, ma_giao_dich_cong_thanh_toan: str) -> int:
    """Cổng báo thanh toán thành công cho 1 vé "trả tại quầy" đã chốt (không hạn): → `da_thanh_toan` (`chuyen_khoan`).
    Trả 1 nếu ghi nhận được, 0 nếu vé không còn ở trạng thái đó (đã hủy/hết hạn/đã trả)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'da_thanh_toan', phuong_thuc_thanh_toan = 'chuyen_khoan',
                       ma_giao_dich_cong_thanh_toan = %s, gio_thanh_toan = now()
                WHERE ma_ve = %s AND trang_thai = 'giu_cho' AND loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                  AND han_giu_cho_den IS NULL
                """,
                (ma_giao_dich_cong_thanh_toan, ma_ve),
            )
            so_ve = cur.rowcount
        conn.commit()
        return so_ve
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
