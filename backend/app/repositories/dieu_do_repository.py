"""Raw SQL cho phần điều độ viên gán xe theo CHU TRÌNH (chuyến đi + chuyến về cùng `chu_trinh_id`) —
DIEU_DO_VIEN_THIET_KE_MOI.md. Không chứa quy tắc nghiệp vụ — việc đó thuộc services/dieu_do_service.py.

Mỗi chuyến trả về kèm: thời gian chạy cả tuyến (`tong_phut` = mốc muộn nhất của tuyến_diem_don_tra), giờ kết thúc dự kiến,
điểm xuất phát/điểm đến THEO CHIỀU của chuyến.
"""

from app.db import get_connection, release_connection
from app.repositories import bien_che_sql

_SELECT_CHUYEN = """
    SELECT c.id, c.ma, c.chu_trinh_id, c.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, c.chieu, c.gio_khoi_hanh,
           c.loai_xe_id, lx.ten AS ten_loai_xe, c.trang_thai, c.dang_hoan, c.xe_id, x.bien_so AS bien_so_xe, x.trang_thai AS trang_thai_xe, c.xe_thuc_te_id,
           xt.bien_so AS bien_so_xe_thuc_te, xt.trang_thai AS trang_thai_xe_thuc_te,
           c.co_canh_bao_xung_dot_vi_tri, c.loai_su_co, c.ly_do_su_co,
           tp.tong_phut,
           c.gio_khoi_hanh + tp.tong_phut * interval '1 minute' AS gio_ket_thuc,
           CASE WHEN c.chieu = 'xuoi' THEN dau.diem_id ELSE cuoi.diem_id END AS diem_di_id,
           CASE WHEN c.chieu = 'xuoi' THEN dau.ten ELSE cuoi.ten END AS ten_diem_di,
           CASE WHEN c.chieu = 'xuoi' THEN cuoi.diem_id ELSE dau.diem_id END AS diem_den_id,
           CASE WHEN c.chieu = 'xuoi' THEN cuoi.ten ELSE dau.ten END AS ten_diem_den
    FROM chuyen_xe c
    JOIN tuyen t ON t.id = c.tuyen_id
    JOIN loai_xe lx ON lx.id = c.loai_xe_id
    LEFT JOIN xe x ON x.id = c.xe_id
    LEFT JOIN xe xt ON xt.id = c.xe_thuc_te_id
    JOIN LATERAL (
        SELECT COALESCE(MAX(thoi_gian_du_kien_phut), 0) AS tong_phut FROM tuyen_diem_don_tra WHERE tuyen_id = c.tuyen_id
    ) tp ON true
    JOIN LATERAL (
        SELECT d.diem_don_tra_id AS diem_id, dd.ten FROM tuyen_diem_don_tra d JOIN diem_don_tra dd ON dd.id = d.diem_don_tra_id
        WHERE d.tuyen_id = c.tuyen_id ORDER BY d.thu_tu ASC LIMIT 1
    ) dau ON true
    JOIN LATERAL (
        SELECT d.diem_don_tra_id AS diem_id, dd.ten FROM tuyen_diem_don_tra d JOIN diem_don_tra dd ON dd.id = d.diem_don_tra_id
        WHERE d.tuyen_id = c.tuyen_id ORDER BY d.thu_tu DESC LIMIT 1
    ) cuoi ON true
"""

_SELECT_XE = """
    SELECT x.id, x.bien_so, x.loai_xe_id, x.trang_thai, x.tuyen_id, x.diem_goc_id, d.ten AS ten_diem_goc,
           """ + bien_che_sql.cot_hieu_luc("x") + """
    FROM xe x
    JOIN diem_don_tra d ON d.id = x.diem_goc_id
"""


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def danh_sach_chuyen_trong_cua_so(tu_thoi_diem, den_thoi_diem, tuyen_ids: list[str] | None) -> list[dict]:
    """Các chuyến `chua_khoi_hanh` thuộc những chu trình có chuyến đầu khởi hành trong [tu, den) — cộng các chu trình có chuyến
    ĐANG HOÃN (đã quá giờ mà chưa có xe, NGHIEP_VU.md mục 3.3) dù giờ khởi hành đã qua, vì điều độ viên vẫn phải gán xe cho chúng.
    `tuyen_ids` khác None thì chỉ lấy các tuyến đó (phạm vi của điều độ viên = tuyến được phân công; danh sách rỗng = không có gì).
    Sắp theo giờ khởi hành."""
    if tuyen_ids is not None and not tuyen_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            tham_so: list = [tu_thoi_diem, den_thoi_diem]
            loc_tuyen = ""
            if tuyen_ids is not None:
                loc_tuyen = " AND c.tuyen_id = ANY(%s::uuid[])"
                tham_so.append(tuyen_ids)
            cur.execute(
                _SELECT_CHUYEN
                + """
                WHERE c.trang_thai = 'chua_khoi_hanh'
                  AND c.chu_trinh_id IN (
                      SELECT chu_trinh_id FROM chuyen_xe
                      WHERE chu_trinh_id IS NOT NULL AND trang_thai = 'chua_khoi_hanh'
                      GROUP BY chu_trinh_id
                      HAVING (MIN(gio_khoi_hanh) >= %s AND MIN(gio_khoi_hanh) < %s) OR bool_or(dang_hoan)
                  )"""
                + loc_tuyen
                + " ORDER BY c.gio_khoi_hanh, c.chieu DESC",
                tham_so,
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def _chuyen_cua_chu_trinh(cur, chu_trinh_id: str, khoa: bool = False) -> list[dict]:
    cur.execute(
        _SELECT_CHUYEN + " WHERE c.chu_trinh_id = %s ORDER BY c.gio_khoi_hanh" + (" FOR UPDATE OF c" if khoa else ""),
        (chu_trinh_id,),
    )
    return _thanh_list(cur, cur.fetchall())


def lay_chu_trinh(chu_trinh_id: str) -> list[dict]:
    """Mọi chuyến (mọi trạng thái) của chu trình, theo giờ khởi hành. Rỗng nếu không có chu trình này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            return _chuyen_cua_chu_trinh(cur, chu_trinh_id)
    finally:
        release_connection(conn)


_SELECT_XE_DE_CHON = """
    SELECT x.id, x.bien_so, x.loai_xe_id, x.trang_thai, x.tuyen_id, x.diem_goc_id, d.ten AS ten_diem_goc,
           lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe,
           CASE WHEN jsonb_typeof(lx.so_do_ghe) = 'array' THEN jsonb_array_length(lx.so_do_ghe) ELSE 0 END AS so_ghe,
           COALESCE((SELECT max((g->>'tang')::int)
                     FROM jsonb_array_elements(CASE WHEN jsonb_typeof(lx.so_do_ghe) = 'array' THEN lx.so_do_ghe ELSE '[]'::jsonb END) g), 1) AS so_tang,
           t.ma AS ma_tuyen_co_dinh, t.ten AS ten_tuyen_co_dinh,
           """ + bien_che_sql.cot_hieu_luc("x") + """
    FROM xe x
    JOIN diem_don_tra d ON d.id = x.diem_goc_id
    JOIN loai_xe lx ON lx.id = x.loai_xe_id
    LEFT JOIN tuyen t ON t.id = x.tuyen_id
"""


def danh_sach_xe_de_chon() -> list[dict]:
    """MỌI xe còn dùng (trừ `ngung_su_dung`) kèm loại xe, số ghế/tầng và tuyến cố định — để điều độ viên xem cả xe không phù hợp
    (khác loại, đang bảo trì...) cùng vị trí của chúng, không chỉ xe gán được."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_XE_DE_CHON + " WHERE x.trang_thai <> 'ngung_su_dung' ORDER BY x.bien_so")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def _lich_xe(cur, xe_id: str, tu_khung, den_khung, moc_truoc, loai_tru_ids: list[str]) -> dict:
    """Lịch của 1 xe quanh một chu trình (không tính chính các chuyến của chu trình đó, `loai_tru_ids`):
    "Xe của chuyến" ở đây là xe THỰC SỰ chạy: xe chạy thay nếu có (`xe_thuc_te_id`), không thì xe gốc — nên xe đang bị thay
    ra được coi là rảnh ở chuyến đó, còn xe chạy thay thì bận.
    - trong_khoang: chuyến chồng lên [tu_khung, den_khung];
    - truoc: chuyến gần nhất kết thúc không muộn hơn `moc_truoc` — để suy ra vị trí xe tại giờ khởi hành;
    - sau: chuyến sớm nhất khởi hành từ `den_khung` trở đi — để kiểm tra chu trình không làm hỏng chuyến kế tiếp."""
    cur.execute(
        "SELECT * FROM (" + _SELECT_CHUYEN + """
            WHERE COALESCE(c.xe_thuc_te_id, c.xe_id) = %s AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[]))
        ) q WHERE q.gio_khoi_hanh < %s AND q.gio_ket_thuc > %s ORDER BY q.gio_khoi_hanh""",
        (xe_id, loai_tru_ids, den_khung, tu_khung),
    )
    trong_khoang = _thanh_list(cur, cur.fetchall())
    cur.execute(
        "SELECT * FROM (" + _SELECT_CHUYEN + """
            WHERE COALESCE(c.xe_thuc_te_id, c.xe_id) = %s AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[]))
        ) q WHERE q.gio_ket_thuc <= %s ORDER BY q.gio_ket_thuc DESC LIMIT 1""",
        (xe_id, loai_tru_ids, moc_truoc),
    )
    truoc = _thanh_dict(cur, cur.fetchone())
    cur.execute(
        _SELECT_CHUYEN + """
            WHERE COALESCE(c.xe_thuc_te_id, c.xe_id) = %s AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[]))
              AND c.gio_khoi_hanh >= %s
            ORDER BY c.gio_khoi_hanh LIMIT 1""",
        (xe_id, loai_tru_ids, den_khung),
    )
    sau = _thanh_dict(cur, cur.fetchone())
    return {"trong_khoang": trong_khoang, "truoc": truoc, "sau": sau}


def lich_cac_xe(xe_ids: list[str], tu_khung, den_khung, moc_truoc, loai_tru_ids: list[str]) -> dict[str, dict]:
    """Lịch quanh chu trình của nhiều xe trong 1 kết nối — khóa kết quả là str(xe_id)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            return {str(xe_id): _lich_xe(cur, str(xe_id), tu_khung, den_khung, moc_truoc, loai_tru_ids) for xe_id in xe_ids}
    finally:
        release_connection(conn)


def gan_xe_cho_chu_trinh(chu_trinh_id: str, xe_id: str, kiem_tra) -> list[dict]:
    """Khóa dòng xe rồi dòng các chuyến của chu trình (FOR UPDATE, luôn theo thứ tự xe → chuyến để không bế tắc), gọi
    `kiem_tra(chuyen, xe, lich_xe)` (service ném GiaTriLoi/KhongTimThay... nếu không được gán) rồi gán `xe_id` cho mọi
    chuyến `chua_khoi_hanh` của chu trình — tất cả trong 1 giao dịch. Nhờ khóa dòng xe, 2 điều độ viên cùng gán 1 xe cho 2
    chu trình chồng giờ sẽ được xử lý tuần tự (người sau thấy lịch người trước đã ghi). `lich_xe(tu_khung, den_khung,
    moc_truoc, loai_tru_ids)` đọc cùng giao dịch. Trả về các chuyến của chu trình sau khi gán."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_XE + " WHERE x.id = %s FOR UPDATE OF x", (xe_id,))
            xe = _thanh_dict(cur, cur.fetchone())
            chuyen = _chuyen_cua_chu_trinh(cur, chu_trinh_id, khoa=True)
            kiem_tra(
                chuyen,
                xe,
                lambda tu_khung, den_khung, moc_truoc, loai_tru_ids: _lich_xe(cur, xe_id, tu_khung, den_khung, moc_truoc, loai_tru_ids),
            )
            cur.execute(
                "UPDATE chuyen_xe SET xe_id = %s, dang_hoan = false, co_canh_bao_xung_dot_vi_tri = false "
                "WHERE chu_trinh_id = %s AND trang_thai = 'chua_khoi_hanh'",
                (xe_id, chu_trinh_id),
            )
            ket_qua = _chuyen_cua_chu_trinh(cur, chu_trinh_id)
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def _khoa_xe_va_chuyen(cur, chu_trinh_id: str, xe_id: str | None):
    """Khóa dòng xe (nếu có) rồi các chuyến của chu trình — luôn theo thứ tự xe → chuyến để không bế tắc."""
    xe = None
    if xe_id:
        cur.execute(_SELECT_XE + " WHERE x.id = %s FOR UPDATE OF x", (xe_id,))
        xe = _thanh_dict(cur, cur.fetchone())
    return xe, _chuyen_cua_chu_trinh(cur, chu_trinh_id, khoa=True)


def thay_xe_cho_chu_trinh(chu_trinh_id: str, xe_thay_id: str, kiem_tra) -> list[dict]:
    """UC-20: cho xe `xe_thay_id` CHẠY THAY các chuyến `chua_khoi_hanh` đã có xe của chu trình — chỉ ghi `xe_thuc_te_id`, giữ nguyên
    `xe_id` (xe gốc) để sau này trả về xe gốc được. Cùng kiểu khóa/kiểm tra trong 1 giao dịch như `gan_xe_cho_chu_trinh`;
    `kiem_tra(chuyen, xe, lich_xe)` ném lỗi nếu không được. Tắt cờ cảnh báo vị trí của các chuyến đó (đã được xử lý)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            xe, chuyen = _khoa_xe_va_chuyen(cur, chu_trinh_id, xe_thay_id)
            kiem_tra(
                chuyen,
                xe,
                lambda tu_khung, den_khung, moc_truoc, loai_tru_ids: _lich_xe(cur, xe_thay_id, tu_khung, den_khung, moc_truoc, loai_tru_ids),
            )
            cur.execute(
                "UPDATE chuyen_xe SET xe_thuc_te_id = %s, co_canh_bao_xung_dot_vi_tri = false "
                "WHERE chu_trinh_id = %s AND trang_thai = 'chua_khoi_hanh' AND xe_id IS NOT NULL",
                (xe_thay_id, chu_trinh_id),
            )
            ket_qua = _chuyen_cua_chu_trinh(cur, chu_trinh_id)
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tra_xe_goc_cho_chu_trinh(chu_trinh_id: str, kiem_tra) -> list[dict]:
    """UC-20 (nửa "gán lại xe gốc"): bỏ xe chạy thay, các chuyến `chua_khoi_hanh` của chu trình chạy lại bằng xe gốc (`xe_thuc_te_id`
    = NULL). `kiem_tra(chuyen, xe_goc, lich_xe)` xét xe gốc (khóa dòng xe gốc trước)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT xe_id FROM chuyen_xe WHERE chu_trinh_id = %s AND trang_thai = 'chua_khoi_hanh' AND xe_thuc_te_id IS NOT NULL LIMIT 1",
                (chu_trinh_id,),
            )
            dong = cur.fetchone()
            xe_goc_id = str(dong[0]) if dong and dong[0] else None
            xe, chuyen = _khoa_xe_va_chuyen(cur, chu_trinh_id, xe_goc_id)
            kiem_tra(
                chuyen,
                xe,
                lambda tu_khung, den_khung, moc_truoc, loai_tru_ids: _lich_xe(cur, xe_goc_id, tu_khung, den_khung, moc_truoc, loai_tru_ids),
            )
            cur.execute(
                "UPDATE chuyen_xe SET xe_thuc_te_id = NULL WHERE chu_trinh_id = %s AND trang_thai = 'chua_khoi_hanh'",
                (chu_trinh_id,),
            )
            ket_qua = _chuyen_cua_chu_trinh(cur, chu_trinh_id)
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_chuyen_gap_su_co(tuyen_ids: list[str] | None) -> list[dict]:
    """Các chuyến đang `gap_su_co` (xe đang dọc đường, chưa xử lý xong) thuộc `tuyen_ids` (None = mọi tuyến), mới nhất trước."""
    if tuyen_ids is not None and not tuyen_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            tham_so: list = []
            loc_tuyen = ""
            if tuyen_ids is not None:
                loc_tuyen = " AND c.tuyen_id = ANY(%s::uuid[])"
                tham_so.append(tuyen_ids)
            cur.execute(_SELECT_CHUYEN + " WHERE c.trang_thai = 'gap_su_co'" + loc_tuyen + " ORDER BY c.gio_khoi_hanh DESC", tham_so)
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Thống kê tổng quan (trang Tổng quan của điều độ viên)
# ---------------------------------------------------------
def thong_ke_doi_xe(tu_thoi_diem, den_thoi_diem) -> dict:
    """Đội xe toàn hệ thống (xe dùng chung giữa các tuyến, NGHIEP_VU.md mục 8.6): số xe hoạt động / bảo trì, trong số hoạt động bao nhiêu
    xe dự phòng (không cố định tuyến) và bao nhiêu xe cố định tuyến, bao nhiêu xe RẢNH (chưa có chuyến nào chưa kết thúc khởi hành trong
    [tu, den) — tính xe chạy thay nếu có). Bỏ qua xe `ngung_su_dung`."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FILTER (WHERE x.trang_thai = 'hoat_dong') AS hoat_dong,
                       count(*) FILTER (WHERE x.trang_thai = 'bao_tri') AS bao_tri,
                       count(*) FILTER (WHERE x.trang_thai = 'hoat_dong' AND x.tuyen_id IS NULL) AS du_phong,
                       count(*) FILTER (WHERE x.trang_thai = 'hoat_dong' AND x.tuyen_id IS NOT NULL) AS co_dinh_tuyen,
                       count(*) FILTER (WHERE x.trang_thai = 'hoat_dong' AND NOT EXISTS (
                           SELECT 1 FROM chuyen_xe c
                           WHERE COALESCE(c.xe_thuc_te_id, c.xe_id) = x.id AND c.trang_thai NOT IN ('da_huy', 'hoan_thanh')
                             AND c.gio_khoi_hanh >= %s AND c.gio_khoi_hanh < %s)) AS ranh
                FROM xe x WHERE x.trang_thai <> 'ngung_su_dung'
                """,
                (tu_thoi_diem, den_thoi_diem),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def dem_chuyen_theo_trang_thai(tu_thoi_diem, den_thoi_diem, tuyen_ids: list[str] | None) -> dict[str, int]:
    """Số chuyến khởi hành trong [tu, den) theo trạng thái (`hoan_thanh`, `dang_chay`, `gap_su_co`, `da_huy`, `chua_khoi_hanh`),
    thuộc `tuyen_ids` (None = mọi tuyến)."""
    if tuyen_ids is not None and not tuyen_ids:
        return {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            tham_so: list = [tu_thoi_diem, den_thoi_diem]
            loc_tuyen = ""
            if tuyen_ids is not None:
                loc_tuyen = " AND tuyen_id = ANY(%s::uuid[])"
                tham_so.append(tuyen_ids)
            cur.execute(
                "SELECT trang_thai, count(*) FROM chuyen_xe WHERE gio_khoi_hanh >= %s AND gio_khoi_hanh < %s" + loc_tuyen + " GROUP BY trang_thai",
                tham_so,
            )
            return {tt: int(so) for tt, so in cur.fetchall()}
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# Cho job nhắc / đang hoãn (jobs/quet_chuyen_chua_co_xe.py)
# ---------------------------------------------------------
def chuyen_chua_gan_xe_sap_toi(tu_thoi_diem, den_thoi_diem) -> list[dict]:
    """Chuyến `chua_khoi_hanh` CHƯA có xe (`xe_id` NULL), chưa bị hoãn, khởi hành trong (tu, den] — để nhắc điều độ viên."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                _SELECT_CHUYEN + """
                WHERE c.trang_thai = 'chua_khoi_hanh' AND c.xe_id IS NULL AND NOT c.dang_hoan
                  AND c.gio_khoi_hanh > %s AND c.gio_khoi_hanh <= %s
                ORDER BY c.gio_khoi_hanh""",
                (tu_thoi_diem, den_thoi_diem),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_dau_dang_hoan_chuyen_qua_gio(bay_gio, tu_thoi_diem) -> list[dict]:
    """UC-44 ⏱: chuyến `chua_khoi_hanh` đã tới/quá giờ khởi hành (trong khoảng [tu_thoi_diem, bay_gio]) mà `xe_id` vẫn NULL → bật
    `dang_hoan`. Chặn dưới `tu_thoi_diem` để chuyến quá khứ xa (dữ liệu cũ chưa từng chạy) không bị hoãn hàng loạt và báo khách nhầm.
    Trả các chuyến vừa được bật (chỉ những chuyến đổi từ chưa hoãn sang hoãn, nên mỗi chuyến chỉ được báo 1 lần). Câu UPDATE duy nhất nên 2 lần chạy job
    chồng nhau cũng không bật/báo trùng."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chuyen_xe SET dang_hoan = true
                WHERE trang_thai = 'chua_khoi_hanh' AND xe_id IS NULL AND NOT dang_hoan AND gio_khoi_hanh <= %s AND gio_khoi_hanh >= %s
                RETURNING id
                """,
                (bay_gio, tu_thoi_diem),
            )
            ids = [str(r[0]) for r in cur.fetchall()]
            ket_qua = []
            if ids:
                cur.execute(_SELECT_CHUYEN + " WHERE c.id = ANY(%s::uuid[]) ORDER BY c.gio_khoi_hanh", (ids,))
                ket_qua = _thanh_list(cur, cur.fetchall())
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
