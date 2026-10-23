"""Raw SQL cho phân công điều độ viên phụ trách tuyến — bảng dieu_do_vien_tuyen (DATABASE.md mục 2.x,
DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md). Không chứa quy tắc nghiệp vụ — việc đó thuộc services/phan_cong_dieu_do_service.py.

Chỉ tính điều độ viên ĐANG HOẠT ĐỘNG là người phụ trách: tài khoản bị khóa vẫn còn dòng phân công nhưng bị bỏ qua ở mọi truy vấn đọc.
"""

from app.db import get_connection, release_connection


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def danh_sach_dieu_do_vien_dang_hoat_dong() -> list[dict]:
    """Điều độ viên đang hoạt động kèm số tuyến đang phụ trách — dữ liệu cho ô chọn ở trang Tuyến."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.id, nd.ho_ten, nd.email,
                       (SELECT count(*) FROM dieu_do_vien_tuyen d WHERE d.nguoi_dung_id = nd.id)::int AS so_tuyen
                FROM nguoi_dung nd
                WHERE nd.vai_tro = 'dieu_do_vien' AND nd.dang_hoat_dong = true
                ORDER BY nd.ho_ten, nd.email
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_phan_cong() -> list[dict]:
    """Mỗi dòng = 1 (tuyến, điều độ viên đang hoạt động) đang được phân công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.tuyen_id, nd.id AS nguoi_dung_id, nd.ho_ten, nd.email
                FROM dieu_do_vien_tuyen d
                JOIN nguoi_dung nd ON nd.id = d.nguoi_dung_id
                WHERE nd.vai_tro = 'dieu_do_vien' AND nd.dang_hoat_dong = true
                ORDER BY d.tuyen_id, nd.ho_ten, nd.email
                """
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def dem_dieu_do_vien_hop_le(nguoi_dung_ids: list[str]) -> int:
    """Số id trong danh sách thật sự là điều độ viên đang hoạt động (để chặn id lạ hoặc vai trò khác)."""
    if not nguoi_dung_ids:
        return 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM nguoi_dung WHERE id = ANY(%s::uuid[]) AND vai_tro = 'dieu_do_vien' AND dang_hoat_dong = true",
                (nguoi_dung_ids,),
            )
            return int(cur.fetchone()[0])
    finally:
        release_connection(conn)


def dat_phan_cong_tuyen(tuyen_id: str, nguoi_dung_ids: list[str]) -> None:
    """Thay toàn bộ phân công của 1 tuyến bằng đúng danh sách `nguoi_dung_ids` (rỗng = bỏ hết), trong 1 giao dịch."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM tuyen WHERE id = %s FOR UPDATE", (tuyen_id,))  # tuần tự hóa 2 người cùng sửa 1 tuyến
            cur.execute(
                "DELETE FROM dieu_do_vien_tuyen WHERE tuyen_id = %s AND NOT (nguoi_dung_id = ANY(%s::uuid[]))",
                (tuyen_id, nguoi_dung_ids),
            )
            for nguoi_dung_id in nguoi_dung_ids:
                cur.execute(
                    "INSERT INTO dieu_do_vien_tuyen (nguoi_dung_id, tuyen_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (nguoi_dung_id, tuyen_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def danh_sach_id_dieu_do_vien_cua_tuyen(tuyen_id: str) -> list[str]:
    """Id các điều độ viên đang hoạt động phụ trách tuyến — dùng gửi cảnh báo sự cố (UC-17)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.id FROM dieu_do_vien_tuyen d
                JOIN nguoi_dung nd ON nd.id = d.nguoi_dung_id
                WHERE d.tuyen_id = %s AND nd.vai_tro = 'dieu_do_vien' AND nd.dang_hoat_dong = true
                """,
                (tuyen_id,),
            )
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        release_connection(conn)
