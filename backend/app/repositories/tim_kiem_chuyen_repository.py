"""Raw SQL chỉ-đọc cho tra cứu chuyến công khai (UC-04, NGHIEP_VU.md mục 3.4 bước 1-3).

Không chứa quy tắc nghiệp vụ (chọn giá theo mùa, tính ghế trống, giờ dự kiến...) — việc đó
thuộc services/tim_kiem_chuyen_service.py. Mọi so sánh thứ tự điểm dùng `hl` = thu_tu hiệu lực
theo chiều chuyến (xuôi: thu_tu, ngược: -thu_tu — THAY_DOI_TUYEN_2_CHIEU.md mục 3).
"""

from app.db import get_connection, release_connection


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def danh_sach_khu_vuc_co_tuyen() -> list[dict]:
    """Khu vực có ít nhất 1 điểm nằm trong 1 tuyến nào đó; `co_van_phong` = có văn phòng
    (chỉ khu vực có văn phòng mới làm được điểm đi, mục 3.1)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kv.id, kv.ma, kv.ten, kv.tinh_thanh,
                       bool_or(d.loai = 'van_phong') AS co_van_phong
                FROM khu_vuc kv
                JOIN diem_don_tra d ON d.khu_vuc_id = kv.id
                WHERE EXISTS (SELECT 1 FROM tuyen_diem_don_tra tdt WHERE tdt.diem_don_tra_id = d.id)
                GROUP BY kv.id, kv.ma, kv.ten, kv.tinh_thanh
                ORDER BY kv.tinh_thanh, kv.ten
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_khu_vuc_theo_id(khu_vuc_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ma, ten, tinh_thanh FROM khu_vuc WHERE id = %s", (khu_vuc_id,))
            ket_qua = _thanh_list(cur, cur.fetchall())
            return ket_qua[0] if ket_qua else None
    finally:
        release_connection(conn)


# Điểm của từng chuyến kèm thu_tu hiệu lực (hl) và số phút kể từ lúc khởi hành theo ĐÚNG chiều chuyến.
# Chiều ngược: phút = tổng thời gian tuyến − phút lưu theo chiều xuôi (DATABASE.md mục 2.4).
_CTE_DIEM = """
    tong AS (
        SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
        FROM tuyen_diem_don_tra GROUP BY tuyen_id
    ),
    diem AS (
        SELECT c.id AS chuyen_id, d.id AS diem_id, d.khu_vuc_id, d.loai, d.ten,
               CASE WHEN c.chieu = 'xuoi' THEN tdt.thu_tu ELSE -tdt.thu_tu END AS hl,
               CASE WHEN c.chieu = 'xuoi' THEN tdt.thoi_gian_du_kien_phut
                    ELSE tong.tong_phut - tdt.thoi_gian_du_kien_phut END AS phut
        FROM cc c
        JOIN tuyen_diem_don_tra tdt ON tdt.tuyen_id = c.tuyen_id
        JOIN diem_don_tra d ON d.id = tdt.diem_don_tra_id
        JOIN tong ON tong.tuyen_id = c.tuyen_id
    )
"""

_SELECT_KET_QUA = """
    SELECT c.id, c.ma, c.tuyen_id, c.chieu, c.gio_khoi_hanh, c.dang_hoan,
           lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, lx.he_so_gia,
           jsonb_array_length(lx.so_do_ghe) AS tong_ghe, lx.so_do_ghe,
           don.diem_id AS diem_don_id, don.ten AS ten_diem_don, don.hl AS hl_don, don.phut AS phut_don,
           tra.diem_id AS diem_tra_id, tra.ten AS ten_diem_tra, tra.hl AS hl_tra, tra.phut AS phut_tra,
           x.bien_so
    FROM cc c
    JOIN don ON don.chuyen_id = c.id
    JOIN tra ON tra.chuyen_id = c.id AND don.hl < tra.hl
    JOIN loai_xe lx ON lx.id = c.loai_xe_id
    LEFT JOIN xe x ON x.id = COALESCE(c.xe_thuc_te_id, c.xe_id)
    ORDER BY c.gio_khoi_hanh
"""


def tim_chuyen(khu_vuc_di_id: str, khu_vuc_den_id: str, tu_thoi_diem=None, den_thoi_diem=None, chuyen_id: str | None = None) -> list[dict]:
    """Chuyến còn mở bán (`chua_khoi_hanh`, chưa tới giờ) có đoạn đi từ khu vực đi tới khu vực đến.

    Điểm đón = văn phòng ĐẦU TIÊN (theo chiều chuyến) của khu vực đi, điểm trả = điểm CUỐI CÙNG của
    khu vực đến — đoạn rộng nhất có thể (mục 3.4 bước 3), nên ghế hiện "trống" ở đây chắc chắn
    trống cho mọi cặp điểm đón/trả cụ thể trong 2 khu vực. Lọc theo khoảng giờ [tu, den) hoặc theo 1 chuyến."""
    dieu_kien = ["c.trang_thai = 'chua_khoi_hanh'", "c.gio_khoi_hanh > now()"]
    tham_so: dict = {"di": khu_vuc_di_id, "den": khu_vuc_den_id}
    if chuyen_id:
        dieu_kien.append("c.id = %(chuyen_id)s")
        tham_so["chuyen_id"] = chuyen_id
    if tu_thoi_diem is not None:
        dieu_kien.append("c.gio_khoi_hanh >= %(tu)s")
        tham_so["tu"] = tu_thoi_diem
    if den_thoi_diem is not None:
        dieu_kien.append("c.gio_khoi_hanh < %(den_gio)s")
        tham_so["den_gio"] = den_thoi_diem

    sql = f"""
        WITH cc AS (SELECT * FROM chuyen_xe c WHERE {" AND ".join(dieu_kien)}),
        {_CTE_DIEM},
        don AS (SELECT DISTINCT ON (chuyen_id) * FROM diem
                WHERE khu_vuc_id = %(di)s AND loai = 'van_phong' ORDER BY chuyen_id, hl ASC),
        tra AS (SELECT DISTINCT ON (chuyen_id) * FROM diem
                WHERE khu_vuc_id = %(den)s ORDER BY chuyen_id, hl DESC)
        {_SELECT_KET_QUA}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tham_so)
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_diem_cua_chuyen(chuyen_id: str, khu_vuc_id: str) -> list[dict]:
    """Các điểm của 1 chuyến thuộc 1 khu vực, theo thứ tự chạy thật, kèm phút từ lúc khởi hành."""
    sql = f"""
        WITH cc AS (SELECT * FROM chuyen_xe c WHERE c.id = %(chuyen_id)s),
        {_CTE_DIEM}
        SELECT diem_id, ten, loai, hl, phut FROM diem
        WHERE khu_vuc_id = %(khu_vuc)s ORDER BY hl
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {"chuyen_id": chuyen_id, "khu_vuc": khu_vuc_id})
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lo_trinh_cua_chuyen(chuyen_id: str) -> list[dict]:
    """Toàn bộ điểm đón/trả của tuyến 1 chuyến theo THỨ TỰ CHẠY THẬT (đúng chiều chuyến), kèm số phút kể từ lúc khởi hành,
    địa chỉ, khu vực, và giờ khởi hành/tên tuyến để dựng lộ trình. Rỗng nếu chuyến không tồn tại."""
    sql = f"""
        WITH cc AS (SELECT * FROM chuyen_xe c WHERE c.id = %(chuyen_id)s),
        {_CTE_DIEM}
        SELECT d.diem_id, d.ten, d.loai, d.khu_vuc_id, kv.ten AS ten_khu_vuc, dd.dia_chi, d.hl, d.phut,
               cc.gio_khoi_hanh, tu.ten AS ten_tuyen
        FROM diem d
        JOIN cc ON cc.id = d.chuyen_id
        JOIN tuyen tu ON tu.id = cc.tuyen_id
        JOIN diem_don_tra dd ON dd.id = d.diem_id
        JOIN khu_vuc kv ON kv.id = d.khu_vuc_id
        ORDER BY d.hl
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {"chuyen_id": chuyen_id})
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_doan_ve_dang_giu(chuyen_ids: list[str]) -> list[dict]:
    """Đoạn `[hl_don, hl_tra)` của các vé đang chiếm ghế (`giu_cho` còn hạn/không hạn, `da_thanh_toan`)
    — chỉ trả số ghế + đoạn, KHÔNG trả thông tin khách (ARCHITECTURE.md mục 9)."""
    if not chuyen_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.chuyen_id, v.so_ghe,
                       CASE WHEN c.chieu = 'xuoi' THEN a.thu_tu ELSE -a.thu_tu END AS hl_don,
                       CASE WHEN c.chieu = 'xuoi' THEN b.thu_tu ELSE -b.thu_tu END AS hl_tra
                FROM ve v
                JOIN chuyen_xe c ON c.id = v.chuyen_id
                JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
                WHERE v.chuyen_id = ANY(%s::uuid[])
                  AND (v.trang_thai = 'da_thanh_toan'
                       OR (v.trang_thai = 'giu_cho' AND (v.han_giu_cho_den IS NULL OR v.han_giu_cho_den > now())))
                """,
                (chuyen_ids,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_gia_ve(tuyen_ids: list[str], khu_vuc_a: str, khu_vuc_b: str) -> list[dict]:
    """Mọi dòng giá của các tuyến cho cặp khu vực (a,b) ở cả 2 thứ tự — chọn giá đúng chiều/đúng ngày
    thuộc Service."""
    if not tuyen_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den
                FROM gia_ve
                WHERE tuyen_id = ANY(%s::uuid[])
                  AND ((diem_di_id = %s AND diem_den_id = %s) OR (diem_di_id = %s AND diem_den_id = %s))
                """,
                (tuyen_ids, khu_vuc_a, khu_vuc_b, khu_vuc_b, khu_vuc_a),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
