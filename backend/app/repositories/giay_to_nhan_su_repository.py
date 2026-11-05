"""Raw SQL cho bảng giay_to_nhan_su — DATABASE.md mục 1.6, phục vụ UC-49.

Mỗi nhân sự tối đa 1 dòng cho mỗi `loai` giấy tờ (UNIQUE (nhan_su_van_hanh_id,
loai)) — gia hạn thì UPDATE dòng đó, không lưu lịch sử các lần gia hạn cũ.
Không chứa quy tắc nghiệp vụ (VD "tài xế bắt buộc có bằng lái") — việc đó
thuộc services/ho_so_nhan_su_service.py.
"""

import datetime

from app.db import get_connection, release_connection


# Hai hàm tiện ích: đổi kết quả psycopg (tuple) thành dict {tên_cột: giá_trị}.
def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# ---------------------------------------------------------
# Đọc
# ---------------------------------------------------------
def tim_theo_id(giay_to_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nhan_su_van_hanh_id, loai, so_giay_to, hang, ngay_cap, ngay_het_han,
                       anh_giay_to, da_canh_bao_sap_het_han, da_canh_bao_het_han
                FROM giay_to_nhan_su
                WHERE id = %s
                """,
                (giay_to_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_nhan_su_va_loai(nhan_su_van_hanh_id: str, loai: str) -> dict | None:
    """Tìm giấy tờ theo (nhân sự, loại) — tối đa 1 dòng nhờ ràng buộc UNIQUE."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nhan_su_van_hanh_id, loai, so_giay_to, hang, ngay_cap, ngay_het_han,
                       anh_giay_to, da_canh_bao_sap_het_han, da_canh_bao_het_han
                FROM giay_to_nhan_su
                WHERE nhan_su_van_hanh_id = %s AND loai = %s
                """,
                (nhan_su_van_hanh_id, loai),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_theo_nhan_su(nhan_su_van_hanh_id: str) -> list[dict]:
    """Mọi giấy tờ của 1 nhân sự."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nhan_su_van_hanh_id, loai, so_giay_to, hang, ngay_cap, ngay_het_han,
                       anh_giay_to, da_canh_bao_sap_het_han, da_canh_bao_het_han
                FROM giay_to_nhan_su
                WHERE nhan_su_van_hanh_id = %s
                ORDER BY loai
                """,
                (nhan_su_van_hanh_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Ghi (mẫu chung: mở kết nối -> chạy SQL -> commit; lỗi thì rollback;
# luôn trả kết nối về pool trong finally)
# ---------------------------------------------------------
def tao(
    nhan_su_van_hanh_id: str,
    loai: str,
    so_giay_to: str | None,
    hang: str | None,
    ngay_cap,
    ngay_het_han,
) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO giay_to_nhan_su (nhan_su_van_hanh_id, loai, so_giay_to, hang, ngay_cap, ngay_het_han)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (nhan_su_van_hanh_id, loai, so_giay_to, hang, ngay_cap, ngay_het_han),
            )
            giay_to_id = cur.fetchone()[0]
        conn.commit()
        return giay_to_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def cap_nhat(giay_to_id: str, so_giay_to: str | None, hang: str | None, ngay_cap, ngay_het_han) -> None:
    """Luôn đặt lại cả 2 cờ cảnh báo về false — đúng quy tắc "gia hạn thì xóa
    cờ, chu kỳ nhắc bắt đầu lại từ đầu" (NGHIEP_VU.md UC-49)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE giay_to_nhan_su
                SET so_giay_to = %s, hang = %s, ngay_cap = %s, ngay_het_han = %s,
                    da_canh_bao_sap_het_han = false, da_canh_bao_het_han = false
                WHERE id = %s
                """,
                (so_giay_to, hang, ngay_cap, ngay_het_han, giay_to_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def cap_nhat_anh(giay_to_id: str, anh_giay_to: str) -> None:
    """Lưu public_id ảnh Cloudinary (không phải URL) vào giấy tờ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE giay_to_nhan_su SET anh_giay_to = %s WHERE id = %s", (anh_giay_to, giay_to_id))
        conn.commit()
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Phục vụ job cảnh báo hết hạn (nhánh kèm theo UC-49, trước đây là UC-50)
# ---------------------------------------------------------
def can_canh_bao_sap_het_han(nguong_ngay: int, hom_nay: datetime.date | None = None) -> list[dict]:
    """Giấy tờ của nhân sự `dang_lam`, còn <= nguong_ngay tới hạn, chưa từng
    cảnh báo mốc này."""
    hom_nay = hom_nay or datetime.date.today()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gt.id, gt.loai, gt.ngay_het_han, n.id AS nhan_su_van_hanh_id, n.ho_ten
                FROM giay_to_nhan_su gt
                JOIN nhan_su_van_hanh n ON n.id = gt.nhan_su_van_hanh_id
                WHERE n.trang_thai = 'dang_lam'
                  AND gt.da_canh_bao_sap_het_han = false
                  AND gt.ngay_het_han <= %s
                """,
                (hom_nay + datetime.timedelta(days=nguong_ngay),),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def can_canh_bao_da_het_han(hom_nay: datetime.date | None = None) -> list[dict]:
    """Giấy tờ của nhân sự `dang_lam`, đã quá hạn (< hôm nay), chưa cảnh báo mốc này."""
    hom_nay = hom_nay or datetime.date.today()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gt.id, gt.loai, gt.ngay_het_han, n.id AS nhan_su_van_hanh_id, n.ho_ten
                FROM giay_to_nhan_su gt
                JOIN nhan_su_van_hanh n ON n.id = gt.nhan_su_van_hanh_id
                WHERE n.trang_thai = 'dang_lam'
                  AND gt.da_canh_bao_het_han = false
                  AND gt.ngay_het_han < %s
                """,
                (hom_nay,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


# Đặt cờ = true sau khi đã gửi thông báo, để không nhắc lặp lại.
def danh_dau_da_canh_bao_sap_het_han(giay_to_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE giay_to_nhan_su SET da_canh_bao_sap_het_han = true WHERE id = %s", (giay_to_id,))
        conn.commit()
    finally:
        release_connection(conn)


def danh_dau_da_canh_bao_het_han(giay_to_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE giay_to_nhan_su SET da_canh_bao_het_han = true WHERE id = %s", (giay_to_id,))
        conn.commit()
    finally:
        release_connection(conn)
