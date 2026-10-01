"""Raw SQL cho khu_vuc/diem_don_tra/tuyen/tuyen_diem_don_tra —
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
def tao_diem_don_tra(khu_vuc_id: str, ten: str, dia_chi: str, loai: str, sdt_lien_he: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO diem_don_tra (khu_vuc_id, ten, dia_chi, loai, sdt_lien_he)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, khu_vuc_id, ten, dia_chi, sdt_lien_he, loai
                """,
                (khu_vuc_id, ten, dia_chi, loai, sdt_lien_he),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return ket_qua
    finally:
        release_connection(conn)


def sua_diem_don_tra(diem_id: str, khu_vuc_id: str, ten: str, dia_chi: str, loai: str, sdt_lien_he: str | None = None) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE diem_don_tra
                SET khu_vuc_id = %s, ten = %s, dia_chi = %s, loai = %s, sdt_lien_he = %s
                WHERE id = %s
                """,
                (khu_vuc_id, ten, dia_chi, loai, sdt_lien_he, diem_id),
            )
        conn.commit()
    finally:
        release_connection(conn)


def tim_diem_don_tra_theo_id(diem_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, khu_vuc_id, ten, dia_chi, sdt_lien_he, loai FROM diem_don_tra WHERE id = %s",
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
                "SELECT id, khu_vuc_id, ten, dia_chi, sdt_lien_he, loai FROM diem_don_tra WHERE id = ANY(%s::uuid[])",
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
                    "SELECT id, khu_vuc_id, ten, dia_chi, sdt_lien_he, loai FROM diem_don_tra WHERE khu_vuc_id = %s ORDER BY ten",
                    (khu_vuc_id,),
                )
            else:
                cur.execute("SELECT id, khu_vuc_id, ten, dia_chi, sdt_lien_he, loai FROM diem_don_tra ORDER BY ten")
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
# 3. Tuyến + các điểm dừng — không còn khái niệm "nhóm tuyến", mỗi tuyến
# tự thân đại diện cả 1 hành trình, chạy được cả 2 chiều (NGHIEP_VU.md
# mục 3.1). Danh sách điểm dừng lưu theo đúng "chiều xuôi" duy nhất.
# ---------------------------------------------------------
def tao_tuyen_voi_diem(ten: str, danh_sach_diem: list[dict]) -> dict:
    """danh_sach_diem: list [{diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut}],
    đã được service kiểm tra hợp lệ (điểm đầu/cuối van_phong, không trùng).
    Chạy trong đúng 1 transaction — tuyến và toàn bộ điểm cùng thành công
    hoặc cùng thất bại."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tuyen (ten) VALUES (%s) RETURNING id, ten, ngay_tao",
                (ten,),
            )
            ket_qua = _thanh_dict(cur, cur.fetchone())
            tuyen_id = ket_qua["id"]

            for diem in danh_sach_diem:
                cur.execute(
                    """
                    INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tuyen_id, diem["diem_don_tra_id"], diem["thu_tu"], diem["thoi_gian_du_kien_phut"]),
                )
        conn.commit()
        return ket_qua
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def sua_tuyen_voi_diem(tuyen_id: str, ten: str, danh_sach_diem: list[dict]) -> None:
    """Thay toàn bộ danh sách điểm dừng của tuyến (xóa hết dòng cũ, chèn lại
    theo danh sách mới) — chạy trong đúng 1 transaction cùng việc đổi tên,
    tất cả cùng thành công hoặc cùng thất bại. Hiện chưa có chuyen_xe/ve
    tham chiếu trực tiếp tới tuyen_diem_don_tra nên chưa cần bắt
    ForeignKeyViolation ở đây — cần rà lại khi UC-18/UC-44 được xây."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tuyen SET ten = %s WHERE id = %s", (ten, tuyen_id))
            cur.execute("DELETE FROM tuyen_diem_don_tra WHERE tuyen_id = %s", (tuyen_id,))
            for diem in danh_sach_diem:
                cur.execute(
                    """
                    INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tuyen_id, diem["diem_don_tra_id"], diem["thu_tu"], diem["thoi_gian_du_kien_phut"]),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def tim_tuyen_theo_id(tuyen_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, ngay_tao FROM tuyen WHERE id = %s", (tuyen_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def danh_sach_tuyen() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, ngay_tao FROM tuyen ORDER BY ten")
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
                       kv.ten AS ten_khu_vuc,
                       tddt.thu_tu, tddt.thoi_gian_du_kien_phut
                FROM tuyen_diem_don_tra tddt
                JOIN diem_don_tra ddt ON ddt.id = tddt.diem_don_tra_id
                JOIN khu_vuc kv ON kv.id = ddt.khu_vuc_id
                WHERE tddt.tuyen_id = %s
                ORDER BY tddt.thu_tu
                """,
                (tuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
