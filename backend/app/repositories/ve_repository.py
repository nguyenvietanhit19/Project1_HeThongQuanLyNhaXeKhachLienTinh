"""Raw SQL cho bảng ve — DATABASE.md mục 4.

QUAN TRỌNG (CONTRIBUTING.md mục 5.1):
- File này do Người 2 sở hữu duy nhất.
- Người 3, 4, 5 chỉ được GỌI các hàm public bên dưới, KHÔNG tự viết SQL
  cho bảng ve.
- Riêng cơ chế khóa ghế (SELECT ... FOR UPDATE + kiểm tra overlap chặng)
  đặt ở ve_lock_repository.py — tách file để viết integration test riêng.

Các hàm public cho Người 3/4 gọi vào:
  - xac_nhan_len_xe(ve_id)
  - xac_nhan_xuong_xe(ve_id)
  - huy_ve_nhan_hoan(ve_id, ly_do)
  - tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
"""

import datetime
import uuid

from app.db import get_connection, release_connection


def _row_to_dict(cur, row: tuple | None) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _rows_to_list(cur, rows: list[tuple]) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# ─── Đọc ──────────────────────────────────────────────────────────────────────

def tim_theo_id(ve_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*, dd.ten AS diem_don_ten, dt.ten AS diem_tra_ten
                FROM ve v
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                WHERE v.id = %s
                """,
                (ve_id,),
            )
            return _row_to_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_ma_dat_cho(ma_dat_cho: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*, dd.ten AS diem_don_ten, dt.ten AS diem_tra_ten
                FROM ve v
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                WHERE v.ma_dat_cho = %s
                ORDER BY v.so_ghe
                """,
                (ma_dat_cho,),
            )
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_theo_khach_hang(khach_hang_id: str) -> list[dict]:
    """Lịch sử vé của khách hàng — UC-05 màn hình lịch sử vé."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.*, dd.ten AS diem_don_ten, dt.ten AS diem_tra_ten,
                       cx.gio_khoi_hanh, cx.trang_thai AS trang_thai_chuyen,
                       cx.dang_hoan
                FROM ve v
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                JOIN chuyen_xe cx ON cx.id = v.chuyen_id
                WHERE v.khach_hang_id = %s
                ORDER BY v.ngay_tao DESC
                LIMIT 50
                """,
                (khach_hang_id,),
            )
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_theo_sdt_tai_quay(so_dien_thoai: str, chuyen_id: str | None = None) -> list[dict]:
    """UC-11: Nhân viên quầy vé tra cứu theo SĐT (mục 8.4 NGHIEP_VU.md)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            params: list = [f"%{so_dien_thoai}%"]
            query = """
                SELECT v.*, dd.ten AS diem_don_ten, dt.ten AS diem_tra_ten,
                       nd.ho_ten AS ten_khach, nd.so_dien_thoai
                FROM ve v
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                WHERE (nd.so_dien_thoai LIKE %s OR v.sdt_khach_vang_lai LIKE %s)
            """
            params.append(f"%{so_dien_thoai}%")
            if chuyen_id:
                query += " AND v.chuyen_id = %s"
                params.append(chuyen_id)
            query += " ORDER BY v.ngay_tao DESC LIMIT 20"
            cur.execute(query, params)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ─── Tạo / Cập nhật ───────────────────────────────────────────────────────────

def tao_giu_cho(
    chuyen_id: str,
    so_ghe: str,
    diem_don_id: str,
    diem_tra_id: str,
    gia: int,
    ma_dat_cho: str,
    loai_hinh_thanh_toan: str,
    khach_hang_id: str | None = None,
    ten_khach_vang_lai: str | None = None,
    sdt_khach_vang_lai: str | None = None,
    la_ve_dat_coc: bool = False,
    conn=None,           # Cho phép nhận conn từ ngoài để dùng chung transaction
) -> dict:
    """Tạo 1 vé trạng thái 'giu_cho'. Gọi trong transaction của dat_ve_service.

    Không tự commit — caller phải commit sau khi tất cả vé trong lô đã tạo xong.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ve (
                    id, chuyen_id, so_ghe, diem_don_id, diem_tra_id,
                    khach_hang_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                    gia, ma_dat_cho, la_ve_dat_coc, loai_hinh_thanh_toan, trang_thai
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, 'giu_cho'
                )
                RETURNING id, so_ghe, gia, ma_dat_cho, trang_thai, ngay_tao
                """,
                (
                    chuyen_id, so_ghe, diem_don_id, diem_tra_id,
                    khach_hang_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                    gia, ma_dat_cho, la_ve_dat_coc, loai_hinh_thanh_toan,
                ),
            )
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            if own_conn:
                conn.commit()
            return dict(zip(cols, row))
    except Exception:
        if own_conn:
            conn.rollback()
        raise
    finally:
        if own_conn:
            release_connection(conn)


def cap_nhat_diem_don_tra(
    ma_dat_cho: str, diem_don_id: str, diem_tra_id: str
) -> None:
    """UC-05 bước 5: Thu hẹp đoạn về điểm đón/trả cụ thể (mục 6 NGHIEP_VU.md).

    Không cần khóa lại vì đoạn mới luôn hẹp hơn đoạn đã khóa.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET diem_don_id = %s, diem_tra_id = %s
                WHERE ma_dat_cho = %s
                  AND trang_thai = 'giu_cho'
                """,
                (diem_don_id, diem_tra_id, ma_dat_cho),
            )
        conn.commit()
    finally:
        release_connection(conn)


def bat_dau_dem_han_thanh_toan(ma_dat_cho: str, han_phut: int = 5) -> datetime.datetime:
    """UC-05 bước 6-A: Khách tới màn thanh toán — bắt đầu tính hạn 5 phút.

    Trả về thời điểm hết hạn để Service trả về cho Frontend hiển thị đếm ngược.
    """
    han = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=han_phut)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET gio_bat_dau_dem_han = now(),
                    han_giu_cho_den     = %s,
                    loai_hinh_thanh_toan = 'thanh_toan_ngay'
                WHERE ma_dat_cho = %s
                  AND trang_thai = 'giu_cho'
                """,
                (han, ma_dat_cho),
            )
        conn.commit()
    finally:
        release_connection(conn)
    return han


def xac_nhan_thanh_toan(ve_id: str, ma_giao_dich: str) -> None:
    """Webhook VNPay báo thành công — chuyển sang da_thanh_toan."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET trang_thai = 'da_thanh_toan',
                    phuong_thuc_thanh_toan = 'chuyen_khoan',
                    ma_giao_dich_cong_thanh_toan = %s,
                    gio_thanh_toan = now()
                WHERE id = %s AND trang_thai = 'giu_cho'
                """,
                (ma_giao_dich, ve_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def xac_nhan_thanh_toan_tai_quay(ve_id: str, phuong_thuc: str) -> None:
    """UC-09/11: Nhân viên quầy xác nhận đã thu tiền."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET trang_thai = 'da_thanh_toan',
                    phuong_thuc_thanh_toan = %s,
                    gio_thanh_toan = now()
                WHERE id = %s AND trang_thai = 'giu_cho'
                """,
                (phuong_thuc, ve_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def het_han(ve_id: str) -> None:
    """Chuyển vé sang het_han — từ webhook VNPay thất bại hoặc job quét."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'het_han', gio_huy = now() WHERE id = %s AND trang_thai = 'giu_cho'",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def huy_giu_cho(ve_id: str) -> None:
    """UC-08: Khách/nhân viên quầy hủy vé chưa thanh toán trước mốc chốt."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_huy', gio_huy = now() WHERE id = %s AND trang_thai = 'giu_cho'",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


# ─── Hàm Public cho Người 3, 4 gọi vào (CONTRIBUTING.md mục 5.1) ─────────────

def xac_nhan_len_xe(ve_id: str) -> None:
    """UC-12 (Người 3 gọi): Phụ xe xác nhận khách xuất trình vé cứng lên xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_len_xe', gio_len_xe = now() WHERE id = %s AND trang_thai = 'da_thanh_toan'",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def xac_nhan_xuong_xe(ve_id: str) -> None:
    """UC-13 (Người 3 gọi): Phụ xe xác nhận khách xuống đúng điểm trả."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_xuong_xe', gio_xuong_xe = now() WHERE id = %s AND trang_thai = 'da_len_xe'",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def huy_ve_nhan_hoan(ve_id: str, ly_do: str) -> None:
    """UC-41/42 (Người 3/4 gọi nếu cần, hoặc Service của Người 2 gọi nội bộ):
    Hủy vé đã thanh toán và kích hoạt quy trình hoàn tiền.

    ly_do phải là 1 trong: 'hoan_truoc_gio_chay', 'loi_nha_xe_giua_duong',
    'bat_kha_khang_khong_hoan_thanh' (mục 7 NGHIEP_VU.md / DATABASE.md mục 4.1).
    Việc tạo bản ghi lich_su_hoan_tien do hoan_tien_service (Người 5) thực hiện.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ve SET trang_thai = 'da_huy', gio_huy = now() WHERE id = %s AND trang_thai = 'da_thanh_toan'",
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def tim_ve_da_thanh_toan_theo_chuyen(chuyen_id: str) -> list[dict]:
    """UC-19/21 (Người 4 gọi): Lấy danh sách vé da_thanh_toan để xử lý hoàn khi chuyến bị hủy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.khach_hang_id, v.gia,
                       v.phuong_thuc_thanh_toan, v.ma_giao_dich_cong_thanh_toan,
                       nd.ho_ten, nd.so_dien_thoai,
                       v.ten_khach_vang_lai, v.sdt_khach_vang_lai
                FROM ve v
                LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                WHERE v.chuyen_id = %s AND v.trang_thai = 'da_thanh_toan'
                """,
                (chuyen_id,),
            )
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_dau_khong_den(ve_id: str) -> None:
    """UC-14 (Job Người 2 gọi): Đánh dấu no-show khi đến giờ mà chưa lên xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve
                SET trang_thai = 'khong_den'
                WHERE id = %s AND trang_thai IN ('giu_cho', 'da_thanh_toan')
                """,
                (ve_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)
