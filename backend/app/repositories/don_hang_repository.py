"""Raw SQL Repository cho bảng don_hang và loai_hang — DATABASE.md mục 5.

Thao tác trực tiếp với CSDL qua psycopg2, không chứa logic nghiệp vụ
(logic thuộc về services/gui_hang_service.py).
"""

from typing import Any
from app.db import get_connection, release_connection


def _thanh_dict(cur: Any, row: Any) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_danh_sach_dict(cur: Any, rows: list) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# Câu truy vấn SELECT chuẩn kèm thông tin loại hàng, tuyến và văn phòng gửi/nhận
SELECT_DON_HANG_FULL = """
    SELECT 
        d.*,
        lh.ten AS ten_loai_hang,
        t.ten AS ten_tuyen,
        dg.ten AS ten_diem_gui,
        dn.ten AS ten_diem_nhan,
        dn.dia_chi AS dia_chi_diem_nhan,
        dn.sdt_lien_he AS sdt_lien_he_diem_nhan
    FROM don_hang d
    LEFT JOIN loai_hang lh ON d.loai_hang_id = lh.id
    LEFT JOIN tuyen t ON d.tuyen_id = t.id
    LEFT JOIN diem_don_tra dg ON d.diem_gui_id = dg.id
    LEFT JOIN diem_don_tra dn ON d.diem_nhan_id = dn.id
"""


# ====================================================================
# 1. Thao tác Loại hàng (loai_hang)
# ====================================================================

def lay_danh_sach_loai_hang() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang ORDER BY ten")
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_loai_hang_theo_id(loai_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang WHERE id = %s", (loai_hang_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 2. Tạo và Tra cứu Đơn hàng (don_hang)
# ====================================================================

def tao_don_hang(du_lieu: dict) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO don_hang (
                    ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, loai_hang_id,
                    can_nang_kg, dai_cm, rong_cm, cao_cm, gia_cuoc,
                    ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan,
                    phuong_thuc_thanh_toan, nhan_vien_gui_id, trang_thai,
                    da_thu_tien, nhan_vien_thu_id, ngay_thu
                ) VALUES (
                    %(ma_van_don)s, %(tuyen_id)s, %(diem_gui_id)s, %(diem_nhan_id)s, %(loai_hang_id)s,
                    %(can_nang_kg)s, %(dai_cm)s, %(rong_cm)s, %(cao_cm)s, %(gia_cuoc)s,
                    %(ten_nguoi_gui)s, %(sdt_nguoi_gui)s, %(ten_nguoi_nhan)s, %(sdt_nguoi_nhan)s,
                    %(phuong_thuc_thanh_toan)s, %(nhan_vien_gui_id)s, 'cho_van_chuyen',
                    %(da_thu_tien)s, %(nhan_vien_thu_id)s, CASE WHEN %(da_thu_tien)s THEN now() ELSE NULL END
                )
                RETURNING id
                """,
                du_lieu,
            )
            row = cur.fetchone()
            don_id = str(row[0]) if row else None
        conn.commit()
        return tim_theo_id(don_id) if don_id else {}
    finally:
        release_connection(conn)


def tim_theo_ma_van_don(ma_van_don: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                {SELECT_DON_HANG_FULL}
                WHERE d.ma_van_don = %s
                """,
                (ma_van_don,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_thong_tin_theo_ma_van_don_cong_khai(ma_van_don: str, sdt: str) -> dict | None:
    """Đọc dữ liệu theo dõi tối thiểu sau khi đối chiếu SĐT một bên của đơn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.ma_van_don, d.trang_thai, dg.ten AS ten_diem_gui,
                       dn.ten AS ten_diem_nhan, d.ngay_tao,
                       d.thoi_gian_den_diem_nhan, d.ngay_giao
                FROM don_hang d
                LEFT JOIN diem_don_tra dg ON dg.id = d.diem_gui_id
                LEFT JOIN diem_don_tra dn ON dn.id = d.diem_nhan_id
                WHERE d.ma_van_don = %s
                  AND (%s = d.sdt_nguoi_gui OR %s = d.sdt_nguoi_nhan)
                """,
                (ma_van_don, sdt, sdt),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(don_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                {SELECT_DON_HANG_FULL}
                WHERE d.id = %s
                """,
                (don_hang_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_sdt(sdt: str, ten: str, van_phong_id: str | None = None) -> list[dict]:
    """Tra cứu tại quầy theo SĐT + tên, giới hạn theo văn phòng nếu được yêu cầu."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                {SELECT_DON_HANG_FULL}
                WHERE (
                    (d.sdt_nguoi_gui = %s AND lower(trim(d.ten_nguoi_gui)) = lower(trim(%s)))
                    OR
                    (d.sdt_nguoi_nhan = %s AND lower(trim(d.ten_nguoi_nhan)) = lower(trim(%s)))
                )
                  AND (%s::uuid IS NULL OR d.diem_gui_id = %s OR d.diem_nhan_id = %s)
                ORDER BY d.ngay_tao DESC
                """,
                (sdt, ten, sdt, ten, van_phong_id, van_phong_id, van_phong_id),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ====================================================================
# 3. Cập nhật Trạng thái Đơn hàng (Giao hàng, Chất/Dỡ hàng)
# ====================================================================

def cap_nhat_thu_cod(don_hang_id: str, nhan_vien_thu_id: str, diem_nhan_id: str | None = None) -> dict | None:
    """Ghi nhận thu COD một lần, đúng đơn đang chờ lấy tại văn phòng nhận."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE don_hang
                SET da_thu_tien = true, nhan_vien_thu_id = %s, ngay_thu = now()
                WHERE id = %s AND trang_thai = 'cho_lay'
                  AND phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'
                  AND da_thu_tien = false
            """
            params: list = [nhan_vien_thu_id, don_hang_id]
            if diem_nhan_id:
                sql += " AND diem_nhan_id = %s"
                params.append(diem_nhan_id)
            sql += " RETURNING id"
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
        conn.commit()
        return tim_theo_id(str(row[0])) if row else None
    finally:
        release_connection(conn)


def cap_nhat_giao_hang(don_hang_id: str, nhan_vien_nhan_id: str, diem_nhan_id: str | None = None) -> dict | None:
    """UC-24: Xác nhận đã giao hàng cho người nhận."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'da_giao', nhan_vien_nhan_id = %s, ngay_giao = now()
                WHERE id = %s AND trang_thai = 'cho_lay' AND da_thu_tien = true
                  AND (%s::uuid IS NULL OR diem_nhan_id = %s)
                RETURNING id
                """,
                (nhan_vien_nhan_id, don_hang_id, diem_nhan_id, diem_nhan_id),
            )
            row = cur.fetchone()
        conn.commit()
        return tim_theo_id(str(row[0])) if row else None
    finally:
        release_connection(conn)


def cap_nhat_chat_hang_len_chuyen(don_hang_id: str, chuyen_id: str) -> dict | None:
    """UC-26 (Phụ xe): Chất hàng lên chuyến xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'da_len_xe',
                    chuyen_id = %s
                WHERE id = %s AND trang_thai = 'cho_van_chuyen' AND chuyen_id IS NULL
                RETURNING id
                """,
                (chuyen_id, don_hang_id),
            )
            row = cur.fetchone()
        conn.commit()
        return tim_theo_id(str(row[0])) if row else None
    finally:
        release_connection(conn)


def cap_nhat_do_hang_tai_diem(don_hang_id: str, chuyen_id: str) -> dict | None:
    """UC-27 (Phụ xe): Dỡ hàng xuống văn phòng điểm nhận, bắt đầu tính hạn lưu kho."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'cho_lay',
                    thoi_gian_den_diem_nhan = now()
                WHERE id = %s AND chuyen_id = %s AND trang_thai = 'da_len_xe'
                RETURNING id
                """,
                (don_hang_id, chuyen_id),
            )
            row = cur.fetchone()
        conn.commit()
        return tim_theo_id(str(row[0])) if row else None
    finally:
        release_connection(conn)


def cap_nhat_thong_bao_nguoi_nhan(don_hang_id: str, da_thong_bao: bool) -> None:
    """UC-25: Ghi nhận đã liên hệ người nhận thành công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET da_thong_bao_nguoi_nhan = %s
                WHERE id = %s
                """,
                (da_thong_bao, don_hang_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


# ====================================================================
# 4. Truy vấn Danh sách phục vụ Vận hành & Tác vụ nền (UC-25, UC-46)
# ====================================================================

def lay_danh_sach_cho_xep_xe(
    tuyen_id: str,
    chuyen_id: str | None = None,
    diem_gui_id: str | None = None,
) -> list[dict]:
    """UC-26: Phụ xe xem các đơn hàng đang chờ chất lên xe.
    Lọc theo tuyến, và nếu có chuyen_id thì chỉ lấy đơn cùng chiều theo thứ tự hiệu lực.
    Nếu có diem_gui_id thì chỉ lấy đơn gửi từ điểm hiện tại.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if chuyen_id:
                sql = f"""
                {SELECT_DON_HANG_FULL}
                JOIN chuyen_xe cx ON cx.id = %s
                JOIN tuyen_diem_don_tra tg ON tg.tuyen_id = d.tuyen_id AND tg.diem_don_tra_id = d.diem_gui_id
                JOIN tuyen_diem_don_tra tn ON tn.tuyen_id = d.tuyen_id AND tn.diem_don_tra_id = d.diem_nhan_id
                WHERE d.tuyen_id = %s
                  AND d.chuyen_id IS NULL
                  AND d.trang_thai = 'cho_van_chuyen'
                  AND (
                    (cx.chieu = 'xuoi' AND tg.thu_tu < tn.thu_tu)
                    OR
                    (cx.chieu = 'nguoc' AND tg.thu_tu > tn.thu_tu)
                  )
                """
                params = [chuyen_id, tuyen_id]
                if diem_gui_id:
                    sql += " AND d.diem_gui_id = %s"
                    params.append(diem_gui_id)
                sql += " ORDER BY d.ngay_tao ASC"
                cur.execute(sql, tuple(params))
            else:
                sql = f"""
                {SELECT_DON_HANG_FULL}
                WHERE d.tuyen_id = %s AND d.chuyen_id IS NULL AND d.trang_thai = 'cho_van_chuyen'
                """
                params = [tuyen_id]
                if diem_gui_id:
                    sql += " AND d.diem_gui_id = %s"
                    params.append(diem_gui_id)
                sql += " ORDER BY d.ngay_tao ASC"
                cur.execute(sql, tuple(params))
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_danh_sach_hang_cho_tai_diem(diem_nhan_id: str | None = None) -> list[dict]:
    """UC-25: Xem danh sách hàng đang chờ lấy hoặc cảnh báo/tồn kho tại điểm nhận (hoặc toàn bộ)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if diem_nhan_id:
                cur.execute(
                    f"""
                    {SELECT_DON_HANG_FULL}
                    WHERE d.diem_nhan_id = %s AND d.trang_thai IN ('cho_lay', 'qua_han_luu_kho')
                    ORDER BY d.thoi_gian_den_diem_nhan ASC NULLS LAST
                    """,
                    (diem_nhan_id,),
                )
            else:
                cur.execute(
                    f"""
                    {SELECT_DON_HANG_FULL}
                    WHERE d.trang_thai IN ('cho_lay', 'qua_han_luu_kho')
                    ORDER BY d.thoi_gian_den_diem_nhan ASC NULLS LAST
                    """
                )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_don_can_do_tai_diem(chuyen_id: str, diem_nhan_id: str) -> list[dict]:
    """UC-27 (Phụ xe): đơn đang trên xe (da_len_xe), cần dỡ tại đúng điểm
    nhận này của đúng chuyến này — bổ sung cho phần phụ xe (tuanhdung),
    lay_danh_sach_hang_cho_tai_diem() ở trên phục vụ UC-25 (hàng đã dỡ,
    chờ người đến lấy), không phải trường hợp này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma_van_don, ten_nguoi_nhan, can_nang_kg
                FROM don_hang
                WHERE chuyen_id = %s AND diem_nhan_id = %s AND trang_thai = 'da_len_xe'
                ORDER BY ngay_tao ASC
                """,
                (chuyen_id, diem_nhan_id),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def quet_bat_canh_bao_7_ngay() -> int:
    """UC-46: Bật cờ co_canh_bao_cho_lau cho đơn chờ lấy >= 7 ngày."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET co_canh_bao_cho_lau = true
                WHERE trang_thai = 'cho_lay'
                  AND co_canh_bao_cho_lau = false
                  AND thoi_gian_den_diem_nhan <= now() - INTERVAL '7 days'
                """
            )
            so_luong = cur.rowcount
        conn.commit()
        return so_luong
    finally:
        release_connection(conn)


def quet_chuyen_hang_ton_14_ngay() -> int:
    """UC-46: Chuyển sang 'qua_han_luu_kho' (hàng tồn) cho đơn chờ lấy >= 14 ngày."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'qua_han_luu_kho'
                WHERE trang_thai = 'cho_lay'
                  AND thoi_gian_den_diem_nhan <= now() - INTERVAL '14 days'
                """
            )
            so_luong = cur.rowcount
        conn.commit()
        return so_luong
    finally:
        release_connection(conn)


def lay_danh_sach_don_gan_day(
    limit: int = 20,
    diem_gui_id: str | None = None,
    trang_thai: str | None = None,
    tu_khoa: str | None = None,
) -> list[dict]:
    """Lấy danh sách các đơn hàng mới nhất để hiển thị tại quầy, có hỗ trợ lọc theo trạng thái và từ khóa."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            clauses = []
            params = []

            if diem_gui_id:
                clauses.append("d.diem_gui_id = %s")
                params.append(diem_gui_id)

            if trang_thai and trang_thai != "all":
                clauses.append("d.trang_thai = %s")
                params.append(trang_thai)

            if tu_khoa and tu_khoa.strip():
                kw = f"%{tu_khoa.strip()}%"
                clauses.append(
                    "(d.ma_van_don ILIKE %s OR d.ten_nguoi_gui ILIKE %s OR d.sdt_nguoi_gui ILIKE %s OR d.ten_nguoi_nhan ILIKE %s OR d.sdt_nguoi_nhan ILIKE %s)"
                )
                params.extend([kw, kw, kw, kw, kw])

            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)

            sql = f"""
                {SELECT_DON_HANG_FULL}
                {where_sql}
                ORDER BY d.ngay_tao DESC
                LIMIT %s
            """
            cur.execute(sql, tuple(params))
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def thong_ke_hang_tai_diem(diem_id: str | None = None, so_ngay: int = 7) -> dict:
    """Thống kê tổng quan và chuỗi tiếp nhận/giao thực tế theo ngày."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if diem_id:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE diem_gui_id = %(diem_id)s) AS tong_don_gui_di,
                        COUNT(*) FILTER (WHERE diem_gui_id = %(diem_id)s AND trang_thai = 'cho_van_chuyen') AS so_don_cho_xep_xe,
                        COUNT(*) FILTER (WHERE (diem_gui_id = %(diem_id)s OR diem_nhan_id = %(diem_id)s) AND trang_thai = 'da_len_xe') AS so_don_dang_van_chuyen,
                        COALESCE(SUM(gia_cuoc) FILTER (WHERE diem_gui_id = %(diem_id)s AND phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc' AND da_thu_tien), 0) AS tien_cuoc_gui_tra_truoc,
                        COUNT(*) FILTER (WHERE diem_nhan_id = %(diem_id)s) AS tong_don_nhan_den,
                        COUNT(*) FILTER (WHERE diem_nhan_id = %(diem_id)s AND trang_thai = 'cho_lay') AS so_don_cho_lay,
                        COUNT(*) FILTER (WHERE diem_nhan_id = %(diem_id)s AND co_canh_bao_cho_lau = true AND da_thong_bao_nguoi_nhan = false AND trang_thai IN ('cho_lay', 'qua_han_luu_kho')) AS so_don_canh_bao_7_ngay,
                        COUNT(*) FILTER (WHERE diem_nhan_id = %(diem_id)s AND trang_thai = 'qua_han_luu_kho') AS so_don_ton_kho,
                        COUNT(*) FILTER (WHERE diem_nhan_id = %(diem_id)s AND trang_thai = 'da_giao') AS so_don_da_giao,
                        COALESCE(SUM(gia_cuoc) FILTER (WHERE diem_nhan_id = %(diem_id)s AND da_thu_tien AND phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'), 0) AS tien_cod_da_thu
                    FROM don_hang
                    WHERE diem_gui_id = %(diem_id)s OR diem_nhan_id = %(diem_id)s
                    """,
                    {"diem_id": diem_id},
                )
            else:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS tong_don_gui_di,
                        COUNT(*) FILTER (WHERE trang_thai = 'cho_van_chuyen') AS so_don_cho_xep_xe,
                        COUNT(*) FILTER (WHERE trang_thai = 'da_len_xe') AS so_don_dang_van_chuyen,
                        COALESCE(SUM(gia_cuoc) FILTER (WHERE phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc' AND da_thu_tien), 0) AS tien_cuoc_gui_tra_truoc,
                        COUNT(*) AS tong_don_nhan_den,
                        COUNT(*) FILTER (WHERE trang_thai = 'cho_lay') AS so_don_cho_lay,
                        COUNT(*) FILTER (WHERE co_canh_bao_cho_lau = true AND da_thong_bao_nguoi_nhan = false AND trang_thai IN ('cho_lay', 'qua_han_luu_kho')) AS so_don_canh_bao_7_ngay,
                        COUNT(*) FILTER (WHERE trang_thai = 'qua_han_luu_kho') AS so_don_ton_kho,
                        COUNT(*) FILTER (WHERE trang_thai = 'da_giao') AS so_don_da_giao,
                        COALESCE(SUM(gia_cuoc) FILTER (WHERE da_thu_tien AND phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'), 0) AS tien_cod_da_thu
                    FROM don_hang
                    """
                )
            res = _thanh_dict(cur, cur.fetchone()) or {}
            tien_truoc = float(res.get("tien_cuoc_gui_tra_truoc") or 0)
            tien_cod = float(res.get("tien_cod_da_thu") or 0)
            res["tong_doanh_thu"] = int(tien_truoc + tien_cod)
            res["tong_so_don"] = res.get("tong_don_gui_di", 0)
            res["cho_van_chuyen"] = res.get("so_don_cho_xep_xe", 0)
            res["dang_van_chuyen"] = res.get("so_don_dang_van_chuyen", 0)
            res["cho_lay"] = res.get("so_don_cho_lay", 0)
            res["da_giao"] = res.get("so_don_da_giao", 0)
            res["hang_ton_qua_han"] = res.get("so_don_ton_kho", 0)
            cur.execute(
                """
                WITH ngay AS (
                    SELECT generate_series(
                        ((now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - (%(so_ngay)s - 1))::timestamp,
                        (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date::timestamp,
                        INTERVAL '1 day'
                    )::date AS ngay
                ), tao AS (
                    SELECT (ngay_tao AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay,
                           COUNT(*) AS so_don
                    FROM don_hang
                    WHERE ngay_tao >= (((now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - (%(so_ngay)s - 1))::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                      AND (%(diem_id)s::uuid IS NULL OR diem_gui_id = %(diem_id)s OR diem_nhan_id = %(diem_id)s)
                    GROUP BY 1
                ), giao AS (
                    SELECT (ngay_giao AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay,
                           COUNT(*) AS so_don
                    FROM don_hang
                    WHERE ngay_giao >= (((now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - (%(so_ngay)s - 1))::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                      AND (%(diem_id)s::uuid IS NULL OR diem_gui_id = %(diem_id)s OR diem_nhan_id = %(diem_id)s)
                    GROUP BY 1
                )
                SELECT ngay.ngay,
                       COALESCE(tao.so_don, 0) AS don_tiep_nhan,
                       COALESCE(giao.so_don, 0) AS da_giao
                FROM ngay
                LEFT JOIN tao USING (ngay)
                LEFT JOIN giao USING (ngay)
                ORDER BY ngay.ngay
                """,
                {"diem_id": diem_id, "so_ngay": so_ngay},
            )
            res["theo_ngay"] = [
                {
                    "ngay": row[0].isoformat(),
                    "don_tiep_nhan": row[1],
                    "da_giao": row[2],
                }
                for row in cur.fetchall()
            ]
            return res
    finally:
        release_connection(conn)


