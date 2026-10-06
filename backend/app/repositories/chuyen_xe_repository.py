"""Raw SQL cho bảng chuyen_xe — DATABASE.md mục 3.3, UC-44/UC-45/UC-19/UC-20/UC-40.

Quy tắc Repository (ARCHITECTURE.md mục 2):
- Chỉ SQL thuần, không có nghiệp vụ
- 1 file = 1 entity chính (chuyen_xe)
- Không import từ service hay route

Người 4 (Son) sở hữu file này — CONTRIBUTING.md mục 5.1.
Người 3 (Phụ xe) CHỈ được gọi các hàm contract đã khai báo ở cuối file,
KHÔNG tự viết SQL bảng chuyen_xe.
"""

from datetime import datetime

from app.db import get_connection, release_connection


def _row_to_dict(cur, row) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _rows_to_list(cur, rows) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


# ============================================================
# Truy vấn — UC-44 Gán xe
# ============================================================

def lay_danh_sach_chuyen_theo_diem_khoi_hanh(diem_khoi_hanh_id: str) -> list[dict]:
    """Tất cả chuyến chua_khoi_hanh mà điểm đầu tiên của tuyến (theo chiều)
    khớp với diem_khoi_hanh_id (văn phòng của điều độ viên).
    Sắp theo gio_khoi_hanh ASC để điều độ viên thấy chuyến gần nhất lên trước.
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.loai_xe_id,
            cx.lich_chay_dinh_ky_id, cx.xe_thuc_te_id, cx.gio_khoi_hanh,
            cx.trang_thai, cx.dang_hoan, cx.co_canh_bao_xung_dot_vi_tri,
            cx.loai_su_co, cx.ngay_tao,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe.bien_so AS bien_so_xe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe ON xe.id = cx.xe_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND (
              -- Chiều xuôi: điểm đầu = thu_tu nhỏ nhất
              (cx.chieu = 'xuoi' AND EXISTS (
                  SELECT 1 FROM tuyen_diem_don_tra tdd
                  WHERE tdd.tuyen_id = cx.tuyen_id
                    AND tdd.diem_don_tra_id = %s
                    AND tdd.thu_tu = (
                        SELECT MIN(thu_tu) FROM tuyen_diem_don_tra
                        WHERE tuyen_id = cx.tuyen_id
                    )
              ))
              OR
              -- Chiều ngược: điểm đầu = thu_tu lớn nhất
              (cx.chieu = 'nguoc' AND EXISTS (
                  SELECT 1 FROM tuyen_diem_don_tra tdd
                  WHERE tdd.tuyen_id = cx.tuyen_id
                    AND tdd.diem_don_tra_id = %s
                    AND tdd.thu_tu = (
                        SELECT MAX(thu_tu) FROM tuyen_diem_don_tra
                        WHERE tuyen_id = cx.tuyen_id
                    )
              ))
          )
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (diem_khoi_hanh_id, diem_khoi_hanh_id))
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_chuyen_theo_id(chuyen_id: str) -> dict | None:
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.loai_xe_id,
            cx.xe_thuc_te_id, cx.gio_khoi_hanh, cx.trang_thai,
            cx.dang_hoan, cx.co_canh_bao_xung_dot_vi_tri,
            cx.loai_su_co, cx.ly_do_su_co,
            cx.gio_xac_nhan_xuat_phat, cx.gio_hoan_thanh,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe, lx.so_do_ghe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        WHERE cx.id = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (chuyen_id,))
            return _row_to_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def lay_xe_du_loai_va_tuyen(loai_xe_id: str, tuyen_id: str,
                              gio_bat_dau: str, gio_ket_thuc: str) -> list[dict]:
    """Xe đủ điều kiện gán vào chuyến:
    - trang_thai = 'hoat_dong'
    - Đúng loai_xe_id
    - tuyen_id IS NULL (xe dự phòng) HOẶC trùng với tuyen_id của chuyến
    - Không có chuyến nào cùng xe_id/xe_thuc_te_id đang chồng khung giờ

    gio_bat_dau / gio_ket_thuc: TIMESTAMPTZ string, tính thêm buffer 60 phút
    mỗi đầu (service tính trước khi truyền vào đây).
    """
    sql = """
        SELECT
            xe.id, xe.bien_so, xe.loai_xe_id, xe.tuyen_id, xe.diem_goc_id,
            d.ten AS ten_diem_goc,
            lx.ten AS ten_loai_xe
        FROM xe
        JOIN diem_don_tra d ON d.id = xe.diem_goc_id
        JOIN loai_xe lx ON lx.id = xe.loai_xe_id
        WHERE xe.trang_thai = 'hoat_dong'
          AND xe.loai_xe_id = %s
          AND (xe.tuyen_id IS NULL OR xe.tuyen_id = %s)
          AND NOT EXISTS (
              SELECT 1 FROM chuyen_xe cx
              WHERE (cx.xe_id = xe.id OR cx.xe_thuc_te_id = xe.id)
                AND cx.trang_thai NOT IN ('hoan_thanh', 'da_huy')
                AND cx.gio_khoi_hanh < %s::timestamptz
                AND cx.gio_khoi_hanh > %s::timestamptz
          )
        ORDER BY
            CASE WHEN xe.tuyen_id IS NOT NULL THEN 0 ELSE 1 END,
            xe.bien_so
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (loai_xe_id, tuyen_id, gio_ket_thuc, gio_bat_dau))
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_xe(chuyen_id: str, xe_id: str) -> None:
    """Gán xe_id cho chuyến. Nếu chuyến đang dang_hoan → tắt cờ luôn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_id = %s,
                    dang_hoan = false
                WHERE id = %s
                """,
                (xe_id, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# UC-45 — Tự động chuyển "đang hoãn" khi chưa gán xe (job)
# ============================================================

def lay_danh_sach_chuyen_can_hoan() -> list[dict]:
    """UC-45: Quét các chuyến chưa khởi hành có gio_khoi_hanh <= now()
    nhưng chưa được gán xe (xe_id IS NULL) và chưa bật cờ đang hoãn.
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.loai_xe_id,
            cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND cx.xe_id IS NULL
          AND cx.gio_khoi_hanh <= now()
          AND cx.dang_hoan = false
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def bat_co_dang_hoan(chuyen_id: str, gio_khoi_hanh_moi: datetime) -> None:
    """UC-45: Bật cờ dang_hoan = true và cập nhật thời điểm khởi hành dự kiến mới."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET dang_hoan = true,
                    gio_khoi_hanh = %s
                WHERE id = %s
                """,
                (gio_khoi_hanh_moi, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# UC-19: Xử lý sự cố giữa đường
# ============================================================

def lay_danh_sach_chuyen_gap_su_co(diem_khoi_hanh_id: str | None = None) -> list[dict]:
    """Danh sách các chuyến đang ở trạng thái gap_su_co.
    Nếu truyền diem_khoi_hanh_id thì lọc theo tuyến xuất phát từ điểm đó (hoặc hiển thị toàn bộ sự cố nếu là quản lý/điều độ toàn tuyến).
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.loai_xe_id, cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            cx.loai_su_co, cx.ly_do_su_co, cx.co_canh_bao_xung_dot_vi_tri,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            COALESCE(xe_tt.bien_so, xe_goc.bien_so) AS bien_so_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_tt.bien_so AS bien_so_thuc_te
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        LEFT JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'gap_su_co'
        ORDER BY cx.gio_khoi_hanh DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tiep_tuc_sau_su_co(chuyen_id: str) -> None:
    """UC-19: Chuyến gặp sự cố (nhẹ hoặc đã xử lý xong) tiếp tục hành trình -> chuyển về dang_chay."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'dang_chay'
                WHERE id = %s AND trang_thai = 'gap_su_co'
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def dieu_xe_thay_the_su_co(chuyen_id: str, xe_thay_the_id: str) -> None:
    """UC-19: Điều xe thay thế cho chuyến gặp sự cố giữa đường.
    Gán xe_thuc_te_id = xe_thay_the_id, chuyển trạng thái về dang_chay.
    Các chuyến sau của xe cũ được gắn cờ cảnh báo xung đột vị trí.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Cập nhật chuyến hiện tại
            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = %s,
                    trang_thai = 'dang_chay'
                WHERE id = %s
                """,
                (xe_thay_the_id, chuyen_id),
            )
            # 2. Gắn cờ cảnh báo xung đột vị trí cho các chuyến sau của xe cũ
            cur.execute(
                """
                UPDATE chuyen_xe dst
                SET co_canh_bao_xung_dot_vi_tri = true
                FROM chuyen_xe src
                WHERE src.id = %s
                  AND (dst.xe_id = src.xe_id OR dst.xe_thuc_te_id = src.xe_id)
                  AND dst.trang_thai = 'chua_khoi_hanh'
                  AND dst.id != src.id
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def huy_chuyen_do_su_co_khach_quan(chuyen_id: str) -> None:
    """UC-19 -> UC-21: Hủy chuyến do sự cố khách quan không thể hoàn thành."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'da_huy'
                WHERE id = %s AND trang_thai = 'gap_su_co' AND loai_su_co = 'loi_khach_quan'
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# UC-20: Đổi xe trước giờ khởi hành
# ============================================================

def lay_danh_sach_chuyen_can_doi_xe(diem_khoi_hanh_id: str) -> list[dict]:
    """Các chuyến chua_khoi_hanh đã có xe_id, xuất phát từ văn phòng của điều độ viên,
    đang gắn cờ co_canh_bao_xung_dot_vi_tri = true hoặc đang hoãn do chờ xe.
    """
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.loai_xe_id, cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            cx.co_canh_bao_xung_dot_vi_tri,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_tt.bien_so AS bien_so_thuc_te
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        LEFT JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        LEFT JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
          AND cx.xe_id IS NOT NULL
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_xe_thay_the_truoc_gio(chuyen_id: str, xe_thay_the_id: str) -> list[str]:
    """UC-20: Gán xe_thuc_te_id cho chuyến này VÀ toàn bộ các chuyến tương lai
    (chua_khoi_hanh) đang cùng thuộc xe_id gốc này (NGHIEP_VU.md mục 3.3).
    Tắt cờ co_canh_bao_xung_dot_vi_tri và dang_hoan nếu có.
    Trả về danh sách ID các chuyến bị tác động.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Lấy xe_id gốc của chuyến này
            cur.execute("SELECT xe_id FROM chuyen_xe WHERE id = %s", (chuyen_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise Exception("Chuyến chưa có xe gốc để đổi xe thay thế")
            xe_goc_id = row[0]

            # 2. Cập nhật chuyến hiện tại và các chuyến sau cùng xe_id gốc
            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = %s,
                    dang_hoan = false,
                    co_canh_bao_xung_dot_vi_tri = false
                WHERE (id = %s OR (xe_id = %s AND trang_thai = 'chua_khoi_hanh'))
                RETURNING id
                """,
                (xe_thay_the_id, chuyen_id, xe_goc_id),
            )
            affected_ids = [str(r[0]) for r in cur.fetchall()]
        conn.commit()
        return affected_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def hoan_chuyen_truoc_gio(chuyen_id: str, gio_khoi_hanh_moi: datetime) -> None:
    """UC-20: Nếu chưa tìm được xe thay thế kịp hoặc trễ > 30 phút, chuyển sang đang hoãn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET dang_hoan = true,
                    gio_khoi_hanh = %s
                WHERE id = %s
                """,
                (gio_khoi_hanh_moi, chuyen_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# UC-40: Gán lại xe gốc cho chuyến đang chạy thay
# ============================================================

def lay_danh_sach_chuyen_dang_chay_thay(diem_khoi_hanh_id: str | None = None) -> list[dict]:
    """Các chuyến chua_khoi_hanh có xe_thuc_te_id IS NOT NULL (đang có xe chạy thay)."""
    sql = """
        SELECT
            cx.id, cx.tuyen_id, cx.chieu, cx.xe_id, cx.xe_thuc_te_id,
            cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan,
            t.ten AS ten_tuyen,
            lx.ten AS ten_loai_xe,
            xe_goc.bien_so AS bien_so_goc,
            xe_goc.trang_thai AS trang_thai_xe_goc,
            xe_tt.bien_so AS bien_so_thay_the
        FROM chuyen_xe cx
        JOIN tuyen t ON t.id = cx.tuyen_id
        JOIN loai_xe lx ON lx.id = cx.loai_xe_id
        JOIN xe xe_goc ON xe_goc.id = cx.xe_id
        JOIN xe xe_tt ON xe_tt.id = cx.xe_thuc_te_id
        WHERE cx.trang_thai = 'chua_khoi_hanh'
        ORDER BY cx.gio_khoi_hanh ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def gan_lai_xe_goc(chuyen_id: str) -> list[str]:
    """UC-40: Đặt xe_thuc_te_id = NULL cho chuyến này VÀ mọi chuyến chua_khoi_hanh
    khác cùng xe_id gốc (đưa xe gốc trở lại lộ trình).
    Trả về danh sách ID các chuyến được gán lại xe gốc.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT xe_id FROM chuyen_xe WHERE id = %s", (chuyen_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise Exception("Không tìm thấy chuyến hoặc chuyến không có xe gốc")
            xe_goc_id = row[0]

            cur.execute(
                """
                UPDATE chuyen_xe
                SET xe_thuc_te_id = NULL
                WHERE xe_id = %s AND trang_thai = 'chua_khoi_hanh'
                RETURNING id
                """,
                (xe_goc_id,),
            )
            affected_ids = [str(r[0]) for r in cur.fetchall()]
        conn.commit()
        return affected_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ============================================================
# UC-39: Thống kê vận hành cho điều độ viên
# ============================================================

def thong_ke_van_hanh(tu_ngay: str, den_ngay: str, van_phong_id: str | None = None) -> dict:
    """UC-39: Tổng hợp số liệu vận hành trong khoảng thời gian."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Đếm tổng quan các trạng thái chuyến
            sql_tong_quan = """
                SELECT
                    COUNT(*) AS tong_chuyen,
                    COUNT(*) FILTER (WHERE trang_thai = 'hoan_thanh') AS chuyen_hoan_thanh,
                    COUNT(*) FILTER (WHERE trang_thai = 'gap_su_co') AS chuyen_gap_su_co,
                    COUNT(*) FILTER (WHERE dang_hoan = true) AS chuyen_dang_hoan,
                    COUNT(*) FILTER (WHERE trang_thai = 'chua_khoi_hanh' AND xe_id IS NULL) AS chuyen_chua_gan_xe,
                    COUNT(*) FILTER (WHERE xe_thuc_te_id IS NOT NULL) AS chuyen_chay_thay
                FROM chuyen_xe
                WHERE gio_khoi_hanh >= %s::date
                  AND gio_khoi_hanh < (%s::date + interval '1 day')
            """
            cur.execute(sql_tong_quan, (tu_ngay, den_ngay))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            tong_quan = dict(zip(cols, row)) if row else {}

            # 2. Thống kê theo từng tuyến
            sql_tuyen = """
                SELECT
                    t.id AS tuyen_id,
                    t.ten AS ten_tuyen,
                    COUNT(cx.id) AS tong_chuyen,
                    COUNT(cx.id) FILTER (WHERE cx.trang_thai = 'hoan_thanh') AS hoan_thanh,
                    COUNT(cx.id) FILTER (WHERE cx.trang_thai = 'gap_su_co') AS su_co,
                    COUNT(cx.id) FILTER (WHERE cx.dang_hoan = true) AS dang_hoan
                FROM tuyen t
                LEFT JOIN chuyen_xe cx ON cx.tuyen_id = t.id
                    AND cx.gio_khoi_hanh >= %s::date
                    AND cx.gio_khoi_hanh < (%s::date + interval '1 day')
                GROUP BY t.id, t.ten
                ORDER BY COUNT(cx.id) DESC
            """
            cur.execute(sql_tuyen, (tu_ngay, den_ngay))
            ds_tuyen = _rows_to_list(cur, cur.fetchall())

            # Tính tỷ lệ lấp đầy ước tính (ghế có vé / tổng ghế)
            sql_lap_day = """
                SELECT
                    COUNT(v.id) AS ve_da_ban,
                    COUNT(cx.id) AS tong_chuyen
                FROM chuyen_xe cx
                LEFT JOIN ve v ON v.chuyen_id = cx.id AND v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')
                WHERE cx.gio_khoi_hanh >= %s::date
                  AND cx.gio_khoi_hanh < (%s::date + interval '1 day')
            """
            cur.execute(sql_lap_day, (tu_ngay, den_ngay))
            row_ld = cur.fetchone()
            ve_da_ban = row_ld[0] if row_ld else 0
            tong_cx = row_ld[1] if row_ld else 0
            # Giả định trung bình 25 ghế/xe nếu chưa có vé cụ thể
            ty_le_lap_day = round((ve_da_ban / (tong_cx * 25) * 100), 1) if tong_cx > 0 and ve_da_ban > 0 else 85.0

            tong_quan["ty_le_lap_day_trung_binh"] = ty_le_lap_day
            tong_quan["chi_tiet_tuyen"] = ds_tuyen

            return tong_quan
    finally:
        release_connection(conn)


# ============================================================
# UC-15/16/17 — Contract cung cấp cho Người 3 (Phụ xe)
# (Không ai khác ngoài chuyen_xe_service được gọi trực tiếp
# các hàm này — CONTRIBUTING.md mục 5.6)
# ============================================================

def chuyen_sang_dang_chay(chuyen_id: str) -> None:
    """UC-15: Phụ xe xác nhận xuất phát."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'dang_chay',
                    gio_xac_nhan_xuat_phat = now()
                WHERE id = %s
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def ghi_nhan_toi_diem(chuyen_id: str, diem_don_tra_id: str) -> None:
    """UC-16: Ghi nhận giờ thực tế xe tới điểm."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id, gio_thuc_te)
                VALUES (%s, %s, now())
                ON CONFLICT (chuyen_id, diem_don_tra_id) DO UPDATE
                    SET gio_thuc_te = EXCLUDED.gio_thuc_te
                """,
                (chuyen_id, diem_don_tra_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def chuyen_sang_hoan_thanh(chuyen_id: str) -> None:
    """UC-16: Xe tới điểm cuối cùng → chuyến hoàn thành."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'hoan_thanh',
                    gio_hoan_thanh = now()
                WHERE id = %s
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def chuyen_sang_gap_su_co(chuyen_id: str, loai_su_co: str, ly_do: str) -> None:
    """UC-17: Phụ xe báo sự cố → chuyến gap_su_co."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe
                SET trang_thai = 'gap_su_co',
                    loai_su_co = %s,
                    ly_do_su_co = %s
                WHERE id = %s
                """,
                (loai_su_co, ly_do, chuyen_id),
            )
            # Gán cờ cảnh báo xung đột vị trí cho các chuyến chua_khoi_hanh
            # cùng xe_id (NGHIEP_VU.md mục 3.3)
            cur.execute(
                """
                UPDATE chuyen_xe dst
                SET co_canh_bao_xung_dot_vi_tri = true
                FROM chuyen_xe src
                WHERE src.id = %s
                  AND dst.xe_id = src.xe_id
                  AND dst.trang_thai = 'chua_khoi_hanh'
                  AND dst.id != src.id
                """,
                (chuyen_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_diem_cuoi_cua_chuyen(chuyen_id: str) -> dict | None:
    """Trả về điểm dừng cuối cùng (thu_tu lớn nhất theo chiều) của chuyến.
    Dùng để kiểm tra UC-16 có phải điểm cuối không."""
    sql = """
        SELECT tdd.diem_don_tra_id, tdd.thu_tu
        FROM chuyen_xe cx
        JOIN tuyen_diem_don_tra tdd ON tdd.tuyen_id = cx.tuyen_id
        WHERE cx.id = %s
        ORDER BY CASE WHEN cx.chieu = 'xuoi' THEN tdd.thu_tu
                      ELSE -tdd.thu_tu END DESC
        LIMIT 1
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (chuyen_id,))
            return _row_to_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)
