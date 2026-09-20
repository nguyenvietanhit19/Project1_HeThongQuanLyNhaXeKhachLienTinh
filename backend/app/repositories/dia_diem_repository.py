"""Raw SQL cho khu_vuc/diem_don_tra/nhom_tuyen/tuyen/tuyen_diem_don_tra —
DATABASE.md mục 2.1-2.4. Không chứa quy tắc nghiệp vụ (thứ tự điểm đầu/cuối
phải van_phong...) — việc đó thuộc services/dia_diem_service.py
(ARCHITECTURE.md mục 2).
"""

from app.db import get_connection, release_connection


def _thanh_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


# ---------------------------------------------------------
# 1. Khu vực
# ---------------------------------------------------------
def tao_khu_vuc(ten: str, tinh_thanh: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO khu_vuc (ten, tinh_thanh) VALUES (%s, %s) RETURNING id, ten, tinh_thanh",
                (ten, tinh_thanh),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return ket_qua
    finally:
        release_connection(conn)


def sua_khu_vuc(khu_vuc_id: str, ten: str, tinh_thanh: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE khu_vuc SET ten = %s, tinh_thanh = %s WHERE id = %s",
                (ten, tinh_thanh, khu_vuc_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def tim_khu_vuc_theo_id(khu_vuc_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, tinh_thanh FROM khu_vuc WHERE id = %s", (khu_vuc_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_khu_vuc() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, tinh_thanh FROM khu_vuc ORDER BY tinh_thanh, ten")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_nhieu_khu_vuc_theo_id(khu_vuc_ids: list[str]) -> list[dict]:
    if not khu_vuc_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ten, tinh_thanh FROM khu_vuc WHERE id = ANY(%s::uuid[])",
                (khu_vuc_ids,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_khu_vuc(khu_vuc_id: str) -> None:
    """Có thể ném psycopg2.errors.ForeignKeyViolation nếu còn diem_don_tra
    thuộc khu vực này — service.py bắt lỗi này để báo thông báo thân thiện.
    Rollback trước khi trả connection về pool, tránh để pool giữ connection
    đang ở trạng thái transaction lỗi."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM khu_vuc WHERE id = %s", (khu_vuc_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# 2. Điểm đón/trả
# ---------------------------------------------------------
def tao_diem_don_tra(khu_vuc_id: str, ten: str, dia_chi: str, loai: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO diem_don_tra (khu_vuc_id, ten, dia_chi, loai)
                VALUES (%s, %s, %s, %s)
                RETURNING id, khu_vuc_id, ten, dia_chi, loai
                """,
                (khu_vuc_id, ten, dia_chi, loai),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return ket_qua
    finally:
        release_connection(conn)


def sua_diem_don_tra(diem_id: str, khu_vuc_id: str, ten: str, dia_chi: str, loai: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE diem_don_tra
                SET khu_vuc_id = %s, ten = %s, dia_chi = %s, loai = %s
                WHERE id = %s
                """,
                (khu_vuc_id, ten, dia_chi, loai, diem_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def tim_diem_don_tra_theo_id(diem_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, khu_vuc_id, ten, dia_chi, loai FROM diem_don_tra WHERE id = %s",
                (diem_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_nhieu_diem_don_tra_theo_id(diem_ids: list[str]) -> list[dict]:
    if not diem_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, khu_vuc_id, ten, dia_chi, loai FROM diem_don_tra WHERE id = ANY(%s::uuid[])",
                (diem_ids,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_diem_don_tra(khu_vuc_id: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if khu_vuc_id:
                cur.execute(
                    "SELECT id, khu_vuc_id, ten, dia_chi, loai FROM diem_don_tra WHERE khu_vuc_id = %s ORDER BY ten",
                    (khu_vuc_id,),
                )
            else:
                cur.execute("SELECT id, khu_vuc_id, ten, dia_chi, loai FROM diem_don_tra ORDER BY ten")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_diem_don_tra(diem_id: str) -> None:
    """Có thể ném psycopg2.errors.ForeignKeyViolation nếu điểm này đang
    được tuyen_diem_don_tra/xe/don_hang/ve tham chiếu — service.py bắt lỗi
    này để báo thông báo thân thiện."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM diem_don_tra WHERE id = %s", (diem_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# 3. Nhóm tuyến (gắn danh sách khu vực có thứ tự — mục "Nhóm tuyến")
# ---------------------------------------------------------
def tao_nhom_tuyen_voi_khu_vuc(ten: str, danh_sach_khu_vuc: list[dict]) -> dict:
    """danh_sach_khu_vuc: list [{khu_vuc_id, thu_tu}], đã được service kiểm
    tra hợp lệ. Chạy trong đúng 1 transaction — nhóm tuyến và toàn bộ khu
    vực cùng thành công hoặc cùng thất bại."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO nhom_tuyen (ten) VALUES (%s) RETURNING id", (ten,))
            nhom_tuyen_id = cur.fetchone()[0]

            for kv in danh_sach_khu_vuc:
                cur.execute(
                    "INSERT INTO nhom_tuyen_khu_vuc (nhom_tuyen_id, khu_vuc_id, thu_tu) VALUES (%s, %s, %s)",
                    (nhom_tuyen_id, kv["khu_vuc_id"], kv["thu_tu"]),
                )
        conn.commit()
        return {"id": nhom_tuyen_id, "ten": ten}
    finally:
        release_connection(conn)


def tim_nhom_tuyen_theo_id(nhom_tuyen_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten FROM nhom_tuyen WHERE id = %s", (nhom_tuyen_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_khu_vuc_theo_nhom_tuyen(nhom_tuyen_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kv.id AS khu_vuc_id, kv.ten, kv.tinh_thanh, ntkv.thu_tu
                FROM nhom_tuyen_khu_vuc ntkv
                JOIN khu_vuc kv ON kv.id = ntkv.khu_vuc_id
                WHERE ntkv.nhom_tuyen_id = %s
                ORDER BY ntkv.thu_tu
                """,
                (nhom_tuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_nhom_tuyen(nhom_tuyen_id: str) -> None:
    """Xóa cả nhóm tuyến lẫn danh sách khu vực của nó (nhom_tuyen_khu_vuc
    chỉ là bảng con). Vẫn có thể ném psycopg2.errors.ForeignKeyViolation
    nếu nhóm này đã có tuyen/xe tham chiếu — service.py bắt lỗi này."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM nhom_tuyen_khu_vuc WHERE nhom_tuyen_id = %s", (nhom_tuyen_id,))
            cur.execute("DELETE FROM nhom_tuyen WHERE id = %s", (nhom_tuyen_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_nhom_tuyen() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten FROM nhom_tuyen ORDER BY ten")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ---------------------------------------------------------
# 4. Tuyến + các điểm dừng
# ---------------------------------------------------------
def tao_tuyen_voi_diem(nhom_tuyen_id: str, ten: str, danh_sach_diem: list[dict]) -> dict:
    """danh_sach_diem: list [{diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut}],
    đã được service kiểm tra hợp lệ (điểm đầu/cuối van_phong, không trùng).
    Chạy trong đúng 1 transaction — tuyến và toàn bộ điểm cùng thành công
    hoặc cùng thất bại."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tuyen (nhom_tuyen_id, ten) VALUES (%s, %s) RETURNING id",
                (nhom_tuyen_id, ten),
            )
            tuyen_id = cur.fetchone()[0]

            for diem in danh_sach_diem:
                cur.execute(
                    """
                    INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tuyen_id, diem["diem_don_tra_id"], diem["thu_tu"], diem["thoi_gian_du_kien_phut"]),
                )
        conn.commit()
        return {"id": tuyen_id, "nhom_tuyen_id": nhom_tuyen_id, "ten": ten}
    finally:
        release_connection(conn)


def tim_tuyen_theo_id(tuyen_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nhom_tuyen_id, ten FROM tuyen WHERE id = %s", (tuyen_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_tuyen() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nhom_tuyen_id, ten FROM tuyen ORDER BY ten")
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def xoa_tuyen(tuyen_id: str) -> None:
    """Xóa cả tuyến lẫn danh sách điểm dừng của nó (tuyen_diem_don_tra chỉ
    là bảng con, không phải dữ liệu độc lập được "sử dụng" theo nghĩa cần
    chặn). Vẫn có thể ném psycopg2.errors.ForeignKeyViolation nếu tuyến
    này đã có chuyen_xe/don_hang tham chiếu — service.py bắt lỗi này để
    báo thông báo thân thiện. Cả 2 lệnh DELETE chạy chung 1 transaction:
    nếu bước xóa tuyến thất bại, các dòng tuyen_diem_don_tra vừa xóa cũng
    được rollback lại (không mất dữ liệu điểm dừng của 1 tuyến vẫn còn)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tuyen_diem_don_tra WHERE tuyen_id = %s", (tuyen_id,))
            cur.execute("DELETE FROM tuyen WHERE id = %s", (tuyen_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_diem_theo_tuyen(tuyen_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ddt.id AS diem_don_tra_id, ddt.ten, ddt.khu_vuc_id, ddt.loai,
                       tddt.thu_tu, tddt.thoi_gian_du_kien_phut
                FROM tuyen_diem_don_tra tddt
                JOIN diem_don_tra ddt ON ddt.id = tddt.diem_don_tra_id
                WHERE tddt.tuyen_id = %s
                ORDER BY tddt.thu_tu
                """,
                (tuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
