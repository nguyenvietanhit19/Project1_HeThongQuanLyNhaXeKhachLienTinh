"""Raw SQL cho bộ giá vé (bo_gia_ve) và giá từng cặp khu vực (gia_ve) — DATABASE.md mục 2.5, UC-33. Không chứa quy tắc
nghiệp vụ — việc đó thuộc services/gia_ve_service.py (ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection

_SELECT_BO = """
    SELECT b.id, b.tuyen_id, t.ma AS ma_tuyen, t.ten AS ten_tuyen, b.ap_dung_tu, b.ap_dung_den, b.ngay_tao
    FROM bo_gia_ve b
    JOIN tuyen t ON t.id = b.tuyen_id
"""


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def _gan_danh_sach_gia(cur, cac_bo: list[dict]) -> list[dict]:
    """Gắn `danh_sach_gia` (giá từng cặp khu vực) vào mỗi bộ."""
    if not cac_bo:
        return cac_bo
    cur.execute(
        """
        SELECT g.id, g.bo_gia_id, g.diem_di_id, g.diem_den_id, g.gia_goc,
               kd.ten AS ten_diem_di, ka.ten AS ten_diem_den
        FROM gia_ve g
        JOIN khu_vuc kd ON kd.id = g.diem_di_id
        JOIN khu_vuc ka ON ka.id = g.diem_den_id
        WHERE g.bo_gia_id = ANY(%s::uuid[])
        """,
        ([str(b["id"]) for b in cac_bo],),
    )
    theo_bo: dict = {}
    for g in _thanh_list(cur, cur.fetchall()):
        theo_bo.setdefault(str(g.pop("bo_gia_id")), []).append(g)
    for b in cac_bo:
        b["danh_sach_gia"] = theo_bo.get(str(b["id"]), [])
    return cac_bo


def danh_sach_bo(tuyen_id: str | None = None) -> list[dict]:
    """Mọi bộ giá (kèm giá từng cặp), cũ → mới trong từng tuyến."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if tuyen_id:
                cur.execute(_SELECT_BO + " WHERE b.tuyen_id = %s ORDER BY b.ap_dung_tu", (tuyen_id,))
            else:
                cur.execute(_SELECT_BO + " ORDER BY t.ten, b.ap_dung_tu")
            return _gan_danh_sach_gia(cur, _thanh_list(cur, cur.fetchall()))
    finally:
        release_connection(conn)


def tim_bo_theo_id(bo_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT_BO + " WHERE b.id = %s", (bo_id,))
            ds = _gan_danh_sach_gia(cur, _thanh_list(cur, cur.fetchall()))
            return ds[0] if ds else None
    finally:
        release_connection(conn)


def _them_gia(cur, bo_id: str, danh_sach_gia: list[dict]) -> None:
    for g in danh_sach_gia:
        cur.execute(
            "INSERT INTO gia_ve (bo_gia_id, diem_di_id, diem_den_id, gia_goc) VALUES (%s, %s, %s, %s)",
            (bo_id, g["diem_di_id"], g["diem_den_id"], g["gia_goc"]),
        )


def tao_bo(tuyen_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> str:
    """Tạo bộ + toàn bộ giá trong 1 giao dịch. Có thể ném UniqueViolation nếu tuyến đã có bộ áp dụng từ đúng ngày này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bo_gia_ve (tuyen_id, ap_dung_tu, ap_dung_den) VALUES (%s, %s, %s) RETURNING id",
                (tuyen_id, ap_dung_tu, ap_dung_den),
            )
            bo_id = str(cur.fetchone()[0])
            _them_gia(cur, bo_id, danh_sach_gia)
        conn.commit()
        return bo_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua_bo(bo_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> None:
    """Đổi khoảng ngày áp dụng và thay toàn bộ giá của bộ, trong 1 giao dịch."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE bo_gia_ve SET ap_dung_tu = %s, ap_dung_den = %s WHERE id = %s", (ap_dung_tu, ap_dung_den, bo_id))
            cur.execute("DELETE FROM gia_ve WHERE bo_gia_id = %s", (bo_id,))
            _them_gia(cur, bo_id, danh_sach_gia)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def xoa_bo(bo_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bo_gia_ve WHERE id = %s", (bo_id,))  # giá từng cặp xóa theo (ON DELETE CASCADE)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def ngay_chuyen_cuoi_trong_khoang(tuyen_id: str, tu, den):
    """Ngày khởi hành (giờ Việt Nam) xa nhất của các chuyến đã sinh trong [tu, den]; None nếu chưa có chuyến nào.
    Dùng chặn rút ngắn bộ giá đã khóa về trước chuyến đã sinh."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT max((gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) FROM chuyen_xe
                WHERE tuyen_id = %s
                  AND (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN %s::date AND %s::date
                """,
                (tuyen_id, tu, den),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def so_chuyen_trong_khoang(tuyen_id: str, tu, den) -> int:
    """Số chuyến đã sinh của tuyến có ngày khởi hành (giờ Việt Nam) nằm trong [tu, den]; None = không giới hạn phía đó.
    Dùng để biết 1 bộ giá đã được dùng để sinh chuyến chưa (khi đó không sửa/xóa được nữa)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM chuyen_xe
                WHERE tuyen_id = %s
                  AND (%s::date IS NULL OR (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date >= %s::date)
                  AND (%s::date IS NULL OR (gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date <= %s::date)
                """,
                (tuyen_id, tu, tu, den, den),
            )
            return cur.fetchone()[0]
    finally:
        release_connection(conn)
