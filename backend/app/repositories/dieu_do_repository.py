"""Raw SQL cho phần điều độ viên gán xe theo CHU TRÌNH (chuyến đi + chuyến về cùng `chu_trinh_id`) —
DIEU_DO_VIEN_THIET_KE_MOI.md. Không chứa quy tắc nghiệp vụ — việc đó thuộc services/dieu_do_service.py.

Mỗi chuyến trả về kèm: thời gian chạy cả tuyến (`tong_phut` = mốc muộn nhất của tuyến_diem_don_tra), giờ kết thúc dự kiến,
điểm xuất phát/điểm đến THEO CHIỀU của chuyến.
"""

from app.db import get_connection, release_connection

_SELECT_CHUYEN = """
    SELECT c.id, c.ma, c.chu_trinh_id, c.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, c.chieu, c.gio_khoi_hanh,
           c.loai_xe_id, lx.ten AS ten_loai_xe, c.trang_thai, c.dang_hoan, c.xe_id, x.bien_so AS bien_so_xe, c.xe_thuc_te_id,
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
    SELECT x.id, x.bien_so, x.loai_xe_id, x.trang_thai, x.tuyen_id, x.diem_goc_id, d.ten AS ten_diem_goc
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
    """Các chuyến `chua_khoi_hanh` thuộc những chu trình có chuyến đầu khởi hành trong [tu, den). `tuyen_ids` khác None
    thì chỉ lấy các tuyến đó (phạm vi của điều độ viên = tuyến được phân công; danh sách rỗng = không có gì). Sắp theo giờ khởi hành."""
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
                      HAVING MIN(gio_khoi_hanh) >= %s AND MIN(gio_khoi_hanh) < %s
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
           t.ma AS ma_tuyen_co_dinh, t.ten AS ten_tuyen_co_dinh
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
    - trong_khoang: chuyến chồng lên [tu_khung, den_khung] (xe gốc HOẶC xe chạy thay đều tính là xe đang bận);
    - truoc: chuyến gần nhất của xe gốc kết thúc không muộn hơn `moc_truoc` — để suy ra vị trí xe tại giờ khởi hành;
    - sau: chuyến sớm nhất của xe gốc khởi hành từ `den_khung` trở đi — để kiểm tra chu trình không làm hỏng chuyến kế tiếp."""
    cur.execute(
        "SELECT * FROM (" + _SELECT_CHUYEN + """
            WHERE (c.xe_id = %s OR c.xe_thuc_te_id = %s) AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[]))
        ) q WHERE q.gio_khoi_hanh < %s AND q.gio_ket_thuc > %s ORDER BY q.gio_khoi_hanh""",
        (xe_id, xe_id, loai_tru_ids, den_khung, tu_khung),
    )
    trong_khoang = _thanh_list(cur, cur.fetchall())
    cur.execute(
        "SELECT * FROM (" + _SELECT_CHUYEN + """
            WHERE c.xe_id = %s AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[]))
        ) q WHERE q.gio_ket_thuc <= %s ORDER BY q.gio_ket_thuc DESC LIMIT 1""",
        (xe_id, loai_tru_ids, moc_truoc),
    )
    truoc = _thanh_dict(cur, cur.fetchone())
    cur.execute(
        _SELECT_CHUYEN + """
            WHERE c.xe_id = %s AND c.trang_thai <> 'da_huy' AND NOT (c.id = ANY(%s::uuid[])) AND c.gio_khoi_hanh >= %s
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
                "UPDATE chuyen_xe SET xe_id = %s WHERE chu_trinh_id = %s AND trang_thai = 'chua_khoi_hanh'",
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
