"""Truy vấn hồ sơ gắn cán bộ tại điểm/văn phòng."""

from app.db import get_connection, release_connection


def lay_theo_nguoi_dung_id(nguoi_dung_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.nguoi_dung_id, h.van_phong_id, d.ten AS ten_van_phong,
                       d.dia_chi, d.sdt_lien_he
                FROM ho_so_can_bo_diem h
                JOIN diem_don_tra d ON d.id = h.van_phong_id
                WHERE h.nguoi_dung_id = %s AND d.loai = 'van_phong'
                """,
                (nguoi_dung_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return dict(zip([c[0] for c in cur.description], row))
    finally:
        release_connection(conn)


def danh_sach_nhan_vien_gui_hang() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nd.id AS nguoi_dung_id, nd.email, nd.ho_ten,
                       h.van_phong_id, d.ten AS ten_van_phong
                FROM nguoi_dung nd
                LEFT JOIN ho_so_can_bo_diem h ON h.nguoi_dung_id = nd.id
                LEFT JOIN diem_don_tra d ON d.id = h.van_phong_id
                WHERE nd.vai_tro = 'nhan_vien_gui_hang'
                ORDER BY nd.ho_ten, nd.email
                """
            )
            return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def gan_van_phong(nguoi_dung_id: str, van_phong_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id)
                VALUES (%s, %s)
                ON CONFLICT (nguoi_dung_id) DO UPDATE
                SET van_phong_id = EXCLUDED.van_phong_id
                """,
                (nguoi_dung_id, van_phong_id),
            )
        conn.commit()
    finally:
        release_connection(conn)
