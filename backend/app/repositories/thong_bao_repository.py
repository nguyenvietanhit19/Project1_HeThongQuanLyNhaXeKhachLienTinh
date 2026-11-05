"""Raw SQL cho bảng thong_bao — DATABASE.md mục 6.1.

Hàm ghi dùng để lưu lại thông báo TRƯỚC khi đẩy qua
websocket_manager.broadcast(), để người nhận offline lúc sự kiện xảy ra vẫn
đọc lại được sau (ARCHITECTURE.md mục 6). Các hàm đọc phục vụ route chung
/thong-bao (mọi vai trò đã đăng nhập) — luôn lọc theo nguoi_nhan_id lấy từ
token, không bao giờ đọc/đánh dấu được thông báo của người khác.
"""

from app.db import get_connection, release_connection


# Nhắc quầy vé được nhận diện bằng mã đặt chỗ trong đường dẫn; trạng thái đã đọc
# không quyết định vòng đời của cảnh báo. Wildcard SQL phải viết thành %%.
_DUONG_DAN_NHAC_QUAY_VE = "/nhan-vien/quay-ve/tra-cuu-ve.html?ma_dat_cho={}"
_NHAC_QUAY_VE = "tb.duong_dan LIKE '/nhan-vien/quay-ve/tra-cuu-ve.html?ma_dat_cho=%%'"


def _thanh_danh_sach_dict(cur, rows) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def tao(
    nguoi_nhan_id: str, noi_dung: str, ve_id: str | None = None, don_hang_id: str | None = None,
    duong_dan: str | None = None,
) -> None:
    """`duong_dan`: trang frontend để mở khi bấm vào thông báo (VD /nhan-vien/quan-ly/lich-chay.html); None = chỉ có chữ."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, ve_id, don_hang_id, duong_dan) VALUES (%s, %s, %s, %s, %s)",
                (nguoi_nhan_id, noi_dung, ve_id, don_hang_id, duong_dan),
            )
        conn.commit()
    finally:
        release_connection(conn)


def da_co_thong_bao_giong(nguoi_nhan_id: str, noi_dung: str, trong_ngay: int = 30) -> bool:
    """True nếu người này đã nhận đúng nội dung này trong `trong_ngay` ngày gần đây — để các thông báo nhắc định kỳ
    (cùng một tình trạng) chỉ gửi một lần, không báo lặp mỗi lần job chạy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM thong_bao
                WHERE nguoi_nhan_id = %s AND noi_dung = %s AND ngay_tao > now() - make_interval(days => %s)
                LIMIT 1
                """,
                (nguoi_nhan_id, noi_dung, trong_ngay),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def tao_nhac_quay_ve(nguoi_nhan_id: str, ma_dat_cho: str, noi_dung: str) -> bool:
    """Tạo tối đa một cảnh báo cho một nhân viên và một lượt đặt, kể cả khi nội dung thay đổi.

    Khóa giao dịch theo cặp (nhân viên, mã đặt chỗ) để các worker scheduler
    chạy đồng thời cũng không tạo thông báo trùng.
    """
    duong_dan = _DUONG_DAN_NHAC_QUAY_VE.format(ma_dat_cho)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                (nguoi_nhan_id, ma_dat_cho),
            )
            cur.execute(
                """UPDATE thong_bao SET noi_dung = %s
                   WHERE nguoi_nhan_id = %s AND duong_dan = %s
                     AND noi_dung IS DISTINCT FROM %s""",
                (noi_dung, nguoi_nhan_id, duong_dan, noi_dung),
            )
            cur.execute(
                """INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, duong_dan)
                   SELECT %s, %s, %s
                   WHERE NOT EXISTS (
                       SELECT 1 FROM thong_bao
                       WHERE nguoi_nhan_id = %s AND duong_dan = %s
                   ) AND EXISTS (
                       SELECT 1 FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
                       WHERE v.ma_dat_cho = %s
                         AND (v.kenh_ban IS NULL OR v.kenh_ban = 'hotline')
                         AND v.trang_thai = 'giu_cho'
                         AND v.loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                         AND v.han_giu_cho_den IS NULL
                         AND c.trang_thai = 'chua_khoi_hanh'
                         AND c.gio_khoi_hanh > now()
                         AND c.gio_khoi_hanh <= now() + interval '2 hours'
                   ) RETURNING id""",
                (nguoi_nhan_id, noi_dung, duong_dan, nguoi_nhan_id, duong_dan, ma_dat_cho),
            )
            da_tao = cur.fetchone() is not None
        conn.commit()
        return da_tao
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_nhac_quay_ve_neu_da_xu_ly(ma_dat_cho: str) -> list[str]:
    """Gỡ nhắc khi mọi vé cần trả tại quầy đã được thanh toán, hoặc đã tới giờ chạy.

    Không gỡ do đã đọc hoặc do khách tự hủy trước giờ khởi hành.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM thong_bao tb
                WHERE tb.duong_dan = %s
                  AND (
                      EXISTS (
                          SELECT 1 FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
                          WHERE v.ma_dat_cho = %s AND c.gio_khoi_hanh <= now()
                      )
                      OR (
                          EXISTS (
                              SELECT 1 FROM ve v WHERE v.ma_dat_cho = %s
                                AND v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den')
                          )
                          AND NOT EXISTS (
                              SELECT 1 FROM ve v WHERE v.ma_dat_cho = %s
                                AND v.trang_thai = 'giu_cho'
                                AND v.loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                          )
                      )
                  )
                RETURNING tb.nguoi_nhan_id
                """,
                (_DUONG_DAN_NHAC_QUAY_VE.format(ma_dat_cho), ma_dat_cho, ma_dat_cho, ma_dat_cho),
            )
            nguoi_nhan = sorted({str(row[0]) for row in cur.fetchall()})
        conn.commit()
        return nguoi_nhan
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_nhac_quay_ve_da_xu_ly() -> list[str]:
    """Đồng bộ cảnh báo sau thanh toán hoặc đến giờ chạy, kể cả khi callback/job lỡ chạy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""DELETE FROM thong_bao tb
                    WHERE {_NHAC_QUAY_VE}
                      AND (
                          EXISTS (
                              SELECT 1 FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
                              WHERE v.ma_dat_cho = split_part(tb.duong_dan, 'ma_dat_cho=', 2)
                                AND c.gio_khoi_hanh <= now()
                          )
                          OR (
                              EXISTS (
                                  SELECT 1 FROM ve v
                                  WHERE v.ma_dat_cho = split_part(tb.duong_dan, 'ma_dat_cho=', 2)
                                    AND v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den')
                              )
                              AND NOT EXISTS (
                                  SELECT 1 FROM ve v
                                  WHERE v.ma_dat_cho = split_part(tb.duong_dan, 'ma_dat_cho=', 2)
                                    AND v.trang_thai = 'giu_cho'
                                    AND v.loai_hinh_thanh_toan = 'thanh_toan_tai_quay'
                              )
                          )
                      ) RETURNING tb.nguoi_nhan_id"""
            )
            nguoi_nhan = sorted({str(row[0]) for row in cur.fetchall()})
        conn.commit()
        return nguoi_nhan
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def gop_nhac_quay_ve_trung() -> list[str]:
    """Dọn nhắc trùng được tạo trước khi chống trùng theo mã đặt chỗ.

    Nếu một bản đã đọc thì giữ bản đã đọc, tránh làm huy hiệu xuất hiện lại.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""DELETE FROM thong_bao tb
                    USING (
                        SELECT id, row_number() OVER (
                            PARTITION BY nguoi_nhan_id, duong_dan
                            ORDER BY da_doc DESC, ngay_tao ASC, id ASC
                        ) AS thu_tu
                        FROM thong_bao tb
                        WHERE {_NHAC_QUAY_VE}
                    ) nhac
                    WHERE tb.id = nhac.id AND nhac.thu_tu > 1
                    RETURNING tb.nguoi_nhan_id"""
            )
            nguoi_nhan = sorted({str(row[0]) for row in cur.fetchall()})
        conn.commit()
        return nguoi_nhan
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_cua_toi(nguoi_nhan_id: str, chi_chua_doc: bool = False, limit: int = 30) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT tb.id, tb.noi_dung, tb.da_doc, tb.ngay_tao, tb.ve_id, tb.don_hang_id, tb.duong_dan,
                       dh.ma_van_don, v.ma_dat_cho
                FROM thong_bao tb
                LEFT JOIN don_hang dh ON dh.id = tb.don_hang_id
                LEFT JOIN ve v ON v.id = tb.ve_id
                WHERE tb.nguoi_nhan_id = %s {"AND tb.da_doc = false" if chi_chua_doc else ""}
                ORDER BY tb.ngay_tao DESC
                LIMIT %s
                """,
                (nguoi_nhan_id, limit),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def dem_chua_doc(nguoi_nhan_id: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM thong_bao WHERE nguoi_nhan_id = %s AND da_doc = false",
                (nguoi_nhan_id,),
            )
            return int(cur.fetchone()[0])
    finally:
        release_connection(conn)


def danh_dau_da_doc(thong_bao_id: str, nguoi_nhan_id: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE thong_bao tb SET da_doc = true
                    WHERE tb.id = %s AND tb.nguoi_nhan_id = %s
                    RETURNING tb.id""",
                (thong_bao_id, nguoi_nhan_id),
            )
            ket_qua = "updated" if cur.fetchone() is not None else "not_found"
        conn.commit()
        return ket_qua
    finally:
        release_connection(conn)


def danh_dau_tat_ca_da_doc(nguoi_nhan_id: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE thong_bao tb SET da_doc = true
                    WHERE tb.nguoi_nhan_id = %s AND tb.da_doc = false""",
                (nguoi_nhan_id,),
            )
            so_dong = cur.rowcount
        conn.commit()
        return so_dong
    finally:
        release_connection(conn)
