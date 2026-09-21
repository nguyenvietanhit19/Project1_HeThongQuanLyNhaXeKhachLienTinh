"""Raw SQL Repository cho bảng lich_su_hoan_tien — DATABASE.md mục 4.1.

Thao tác trực tiếp với CSDL qua psycopg2, phục vụ quy trình hoàn tiền
tự động (UC-21, UC-43), xử lý thủ công của Kế toán (UC-22) và báo cáo doanh thu (UC-39).
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


# ====================================================================
# 1. Tạo và Tra cứu Bản ghi Hoàn tiền
# ====================================================================

def tao_hoan_tien(
    ve_id: str,
    ly_do: str,
    so_tien: int,
    trang_thai: str = "cho_xu_ly",
    ma_giao_dich_hoan_tien: str | None = None,
) -> dict:
    """Tạo bản ghi hoàn tiền mới. Unique constraint trên ve_id ngăn chặn hoàn trùng lặp."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lich_su_hoan_tien (
                    ve_id, ly_do, so_tien, trang_thai, ma_giao_dich_hoan_tien, thoi_gian_hoan_xong
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    CASE WHEN %s = 'da_hoan_tu_dong' THEN now() ELSE NULL END
                )
                ON CONFLICT (ve_id) DO NOTHING
                RETURNING *
                """,
                (ve_id, ly_do, so_tien, trang_thai, ma_giao_dich_hoan_tien, trang_thai),
            )
            row = cur.fetchone()
            bghi = _thanh_dict(cur, row) if row else None
        conn.commit()

        # Nếu đã tồn tại dòng hoàn tiền trước đó, trả về dòng hiện có
        if not bghi:
            return tim_theo_ve_id(ve_id)
        return bghi
    finally:
        release_connection(conn)


def tim_theo_ve_id(ve_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM lich_su_hoan_tien WHERE ve_id = %s", (ve_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(hoan_tien_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM lich_su_hoan_tien WHERE id = %s", (hoan_tien_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 2. Xử lý Chuyển khoản Thủ công & Cập nhật Trạng thái (UC-22)
# ====================================================================

def lay_danh_sach_cho_xu_ly() -> list[dict]:
    """UC-22: Kế toán xem toàn bộ các khoản đang chờ chuyển khoản thủ công trên toàn hệ thống."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ht.*,
                       v.so_ghe, v.ma_dat_cho, v.gia AS gia_ve,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ten_khach_hang,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS sdt_khach_hang
                FROM lich_su_hoan_tien ht
                JOIN ve v ON ht.ve_id = v.id
                LEFT JOIN nguoi_dung nd ON v.khach_hang_id = nd.id
                WHERE ht.trang_thai = 'cho_xu_ly'
                ORDER BY ht.thoi_gian_xac_dinh ASC
                """
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_danh_sach_lich_su(
    limit: int = 50,
    offset: int = 0,
    trang_thai: str | None = None,
    tu_ngay: str | None = None,
    den_ngay: str | None = None,
) -> list[dict]:
    """Kế toán xem danh sách lịch sử hoàn tiền phân trang và lọc theo trạng thái/thời gian."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            conditions = ["1=1"]
            params: list[Any] = []

            if trang_thai:
                conditions.append("ht.trang_thai = %s")
                params.append(trang_thai)
            if tu_ngay:
                conditions.append("ht.thoi_gian_xac_dinh >= %s")
                params.append(tu_ngay)
            if den_ngay:
                conditions.append("ht.thoi_gian_xac_dinh <= %s")
                params.append(den_ngay)

            where_clause = " AND ".join(conditions)
            params.extend([limit, offset])

            query = f"""
                SELECT ht.*,
                       v.so_ghe, v.ma_dat_cho, v.gia AS gia_ve,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ten_khach_hang,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS sdt_khach_hang
                FROM lich_su_hoan_tien ht
                JOIN ve v ON ht.ve_id = v.id
                LEFT JOIN nguoi_dung nd ON v.khach_hang_id = nd.id
                WHERE {where_clause}
                ORDER BY ht.thoi_gian_xac_dinh DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, tuple(params))
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def cap_nhat_chuyen_khoan_thu_cong(
    hoan_tien_id: str,
    nhan_vien_xu_ly_id: str,
    so_tai_khoan_nhan: str,
    ten_ngan_hang_nhan: str,
    ten_chu_tai_khoan_nhan: str,
) -> dict | None:
    """UC-22: Kế toán lưu thông tin tài khoản ngân hàng đã chuyển và cập nhật hoàn tất."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lich_su_hoan_tien
                SET trang_thai = 'da_hoan_chuyen_khoan_thu_cong',
                    nhan_vien_xu_ly_id = %s,
                    so_tai_khoan_nhan = %s,
                    ten_ngan_hang_nhan = %s,
                    ten_chu_tai_khoan_nhan = %s,
                    thoi_gian_hoan_xong = now()
                WHERE id = %s AND trang_thai = 'cho_xu_ly'
                RETURNING *
                """,
                (nhan_vien_xu_ly_id, so_tai_khoan_nhan, ten_ngan_hang_nhan, ten_chu_tai_khoan_nhan, hoan_tien_id),
            )
            bghi = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return bghi
    finally:
        release_connection(conn)


def cap_nhat_da_hoan_tu_dong(hoan_tien_id: str, ma_giao_dich_hoan_tien: str) -> dict | None:
    """Cập nhật khi hoàn qua cổng VNPay thành công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lich_su_hoan_tien
                SET trang_thai = 'da_hoan_tu_dong',
                    ma_giao_dich_hoan_tien = %s,
                    thoi_gian_hoan_xong = now()
                WHERE id = %s
                RETURNING *
                """,
                (ma_giao_dich_hoan_tien, hoan_tien_id),
            )
            bghi = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return bghi
    finally:
        release_connection(conn)


# ====================================================================
# 3. Thao tác trên Vé & Chuyến phục vụ quy trình Hoàn tiền (UC-21, UC-43)
# ====================================================================

def tim_ve_theo_id(ve_id: str) -> dict | None:
    """Tra cứu thông tin vé để lấy giá tiền, mã giao dịch online và trạng thái."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ten_khach_hang,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS sdt_khach_hang
                FROM ve v
                LEFT JOIN nguoi_dung nd ON v.khach_hang_id = nd.id
                WHERE v.id = %s
                """,
                (ve_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_ve_da_thanh_toan_theo_chuyen(chuyen_id: str) -> list[dict]:
    """UC-21 & UC-43: Tìm các vé da_thanh_toan trên chuyến gặp sự cố để hoàn tiền."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*,
                       COALESCE(nd.ho_ten, v.ten_khach_vang_lai) AS ten_khach_hang,
                       COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) AS sdt_khach_hang
                FROM ve v
                LEFT JOIN nguoi_dung nd ON v.khach_hang_id = nd.id
                WHERE v.chuyen_id = %s AND v.trang_thai = 'da_thanh_toan'
                """,
                (chuyen_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def cap_nhat_ve_da_huy(ve_id: str) -> bool:
    """Chuyển trạng thái vé sang da_huy khi hoàn tiền (UC-21, UC-41, UC-42)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET trang_thai = 'da_huy',
                    gio_huy = now()
                WHERE id = %s
                """,
                (ve_id,),
            )
        conn.commit()
        return True
    finally:
        release_connection(conn)


def tim_chuyen_gap_su_co_nha_xe_qua_3_tieng() -> list[dict]:
    """UC-43: Quét các chuyến đang gap_su_co do loi_nha_xe kéo dài >= 3 tiếng chưa hoàn thành."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Nếu chuyến có ngay_tao hoặc gio_khoi_hanh, tính thời gian từ khi xảy ra sự cố
            cur.execute(
                """
                SELECT c.*
                FROM chuyen_xe c
                WHERE c.trang_thai = 'gap_su_co'
                  AND c.loai_su_co = 'loi_nha_xe'
                  AND c.gio_khoi_hanh <= (now() - INTERVAL '3 hours')
                """
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ====================================================================
# 4. Thống kê Tài chính Doanh thu (UC-39 cho Kế toán & Quản lý)
# ====================================================================

def thong_ke_hoan_tien() -> dict:
    """Thống kê tổng số tiền và số lượt hoàn theo từng trạng thái."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    COUNT(*) AS tong_so_luot,
                    COALESCE(SUM(so_tien), 0) AS tong_so_tien,
                    COUNT(*) FILTER (WHERE trang_thai = 'cho_xu_ly') AS so_luot_cho_xu_ly,
                    COUNT(*) FILTER (WHERE trang_thai = 'da_hoan_tu_dong') AS so_luot_tu_dong,
                    COUNT(*) FILTER (WHERE trang_thai = 'da_hoan_chuyen_khoan_thu_cong') AS so_luot_thu_cong
                FROM lich_su_hoan_tien
                """
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def thong_ke_tai_chinh_tong_hop(tu_ngay: str | None = None, den_ngay: str | None = None) -> dict:
    """UC-39 (Kế toán): Thống kê doanh thu vé, doanh thu gửi hàng, tiền hoàn và doanh thu thuần."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Doanh thu vé
            ve_conditions = ["v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')"]
            ve_params: list[Any] = []
            if tu_ngay:
                ve_conditions.append("v.ngay_tao >= %s")
                ve_params.append(tu_ngay)
            if den_ngay:
                ve_conditions.append("v.ngay_tao <= %s")
                ve_params.append(den_ngay)

            ve_query = f"""
                SELECT COUNT(*) AS so_luong_ve,
                       COALESCE(SUM(v.gia), 0) AS tong_doanh_thu_ve
                FROM ve v
                WHERE {" AND ".join(ve_conditions)}
            """
            cur.execute(ve_query, tuple(ve_params))
            ve_res = _thanh_dict(cur, cur.fetchone()) or {"so_luong_ve": 0, "tong_doanh_thu_ve": 0}

            # 2. Doanh thu gửi hàng
            hang_conditions = ["dh.trang_thai != 'qua_han_luu_kho'"]
            hang_params: list[Any] = []
            if tu_ngay:
                hang_conditions.append("dh.ngay_tao >= %s")
                hang_params.append(tu_ngay)
            if den_ngay:
                hang_conditions.append("dh.ngay_tao <= %s")
                hang_params.append(den_ngay)

            hang_query = f"""
                SELECT COUNT(*) AS so_luong_hang,
                       COALESCE(SUM(dh.gia_cuoc), 0) AS tong_doanh_thu_hang
                FROM don_hang dh
                WHERE {" AND ".join(hang_conditions)}
            """
            cur.execute(hang_query, tuple(hang_params))
            hang_res = _thanh_dict(cur, cur.fetchone()) or {"so_luong_hang": 0, "tong_doanh_thu_hang": 0}

            # 3. Tiền hoàn vé
            hoan_conditions = ["ht.trang_thai IN ('da_hoan_tu_dong', 'da_hoan_chuyen_khoan_thu_cong')"]
            hoan_params: list[Any] = []
            if tu_ngay:
                hoan_conditions.append("ht.thoi_gian_xac_dinh >= %s")
                hoan_params.append(tu_ngay)
            if den_ngay:
                hoan_conditions.append("ht.thoi_gian_xac_dinh <= %s")
                hoan_params.append(den_ngay)

            hoan_query = f"""
                SELECT COUNT(*) AS so_luot_hoan,
                       COALESCE(SUM(ht.so_tien), 0) AS tong_tien_hoan
                FROM lich_su_hoan_tien ht
                WHERE {" AND ".join(hoan_conditions)}
            """
            cur.execute(hoan_query, tuple(hoan_params))
            hoan_res = _thanh_dict(cur, cur.fetchone()) or {"so_luot_hoan": 0, "tong_tien_hoan": 0}

            # 4. Chờ xử lý hoàn
            cur.execute("SELECT COUNT(*) AS so_luot_cho FROM lich_su_hoan_tien WHERE trang_thai = 'cho_xu_ly'")
            cho_res = _thanh_dict(cur, cur.fetchone()) or {"so_luot_cho": 0}

            tong_ve = int(ve_res["tong_doanh_thu_ve"])
            tong_hang = int(hang_res["tong_doanh_thu_hang"])
            tong_hoan = int(hoan_res["tong_tien_hoan"])
            doanh_thu_thuan = (tong_ve + tong_hang) - tong_hoan

            return {
                "tong_doanh_thu_ve": tong_ve,
                "tong_doanh_thu_gui_hang": tong_hang,
                "tong_tien_hoan_ve": tong_hoan,
                "doanh_thu_thuan": doanh_thu_thuan,
                "so_luong_ve_da_ban": int(ve_res["so_luong_ve"]),
                "so_luong_don_hang": int(hang_res["so_luong_hang"]),
                "so_luot_hoan_tien": int(hoan_res["so_luot_hoan"]),
                "so_luot_cho_xu_ly": int(cho_res["so_luot_cho"]),
            }
    finally:
        release_connection(conn)
