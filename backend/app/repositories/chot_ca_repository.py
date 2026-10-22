"""Raw SQL Repository cho bảng chot_ca_gui_hang — chốt ca tiền mặt của nhân viên gửi hàng.

Tiền mặt nằm trong tay nhân viên trong 1 ca = khoản tự tay thu (trả trước lúc tạo đơn, COD lúc giao —
theo nhan_vien_thu_id, thoi_gian_thu) trừ khoản tự tay hoàn khi hủy đơn (nhan_vien_huy_id, thoi_gian_huy).
Cùng quy tắc với đối soát tiền theo nhân viên (don_hang_repository.doi_soat_tien_theo_nhan_vien).
"""

from datetime import date, datetime
from typing import Any

from app.db import get_connection, release_connection

MUI_GIO_VN = "Asia/Ho_Chi_Minh"


class DaChotSauMocNay(Exception):
    """Đã có lần chốt với mốc kết thúc trùng hoặc sau mốc đang chốt (bấm 2 lần / 2 tab) — không chốt chồng."""


def _thanh_dict(cur: Any, row: Any) -> dict | None:
    if row is None:
        return None
    return dict(zip([d[0] for d in cur.description], row))


def _thanh_danh_sach_dict(cur: Any, rows: list) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# Từng khoản tiền mặt của 1 nhân viên trong (tu, den]. tu NULL = từ trước tới nay (lần chốt đầu tiên).
_SQL_KHOAN = """
    SELECT d.phuong_thuc_thanh_toan AS loai, d.id AS don_hang_id, d.ma_van_don, d.gia_cuoc AS so_tien,
           d.thoi_gian_thu AS thoi_gian
    FROM don_hang d
    WHERE d.nhan_vien_thu_id = %(nv)s AND d.da_thu_tien
      AND (%(tu)s::timestamptz IS NULL OR d.thoi_gian_thu > %(tu)s::timestamptz)
      AND d.thoi_gian_thu <= %(den)s::timestamptz
    UNION ALL
    SELECT 'hoan', d.id, d.ma_van_don, d.so_tien_hoan, d.thoi_gian_huy
    FROM don_hang d
    WHERE d.nhan_vien_huy_id = %(nv)s AND d.so_tien_hoan IS NOT NULL
      AND (%(tu)s::timestamptz IS NULL OR d.thoi_gian_huy > %(tu)s::timestamptz)
      AND d.thoi_gian_huy <= %(den)s::timestamptz
"""

_SQL_TONG = f"""
    SELECT count(*) FILTER (WHERE loai = 'nguoi_gui_tra_truoc') AS so_don_tra_truoc,
           COALESCE(sum(so_tien) FILTER (WHERE loai = 'nguoi_gui_tra_truoc'), 0) AS tien_tra_truoc,
           count(*) FILTER (WHERE loai = 'cod_nguoi_nhan_tra') AS so_don_cod,
           COALESCE(sum(so_tien) FILTER (WHERE loai = 'cod_nguoi_nhan_tra'), 0) AS tien_cod,
           count(*) FILTER (WHERE loai = 'hoan') AS so_don_hoan,
           COALESCE(sum(so_tien) FILTER (WHERE loai = 'hoan'), 0) AS tien_hoan
    FROM ({_SQL_KHOAN}) k
"""


def lay_moc_chot_cuoi(nhan_vien_id: str) -> datetime | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT max(den_luc) FROM chot_ca_gui_hang WHERE nhan_vien_id = %s", (nhan_vien_id,))
            return cur.fetchone()[0]
    finally:
        release_connection(conn)


def tinh_tong(nhan_vien_id: str, tu_luc: datetime | None, den_luc: datetime) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_SQL_TONG, {"nv": nhan_vien_id, "tu": tu_luc, "den": den_luc})
            return {k: int(v or 0) for k, v in _thanh_dict(cur, cur.fetchone()).items()}
    finally:
        release_connection(conn)


def lay_khoan(nhan_vien_id: str, tu_luc: datetime | None, den_luc: datetime) -> list[dict]:
    """Danh sách từng khoản thu / hoàn để in kèm phiếu chốt ca (cũ trước)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM ({_SQL_KHOAN}) k ORDER BY thoi_gian, ma_van_don",
                        {"nv": nhan_vien_id, "tu": tu_luc, "den": den_luc})
            rows = _thanh_danh_sach_dict(cur, cur.fetchall())
            for r in rows:
                r["so_tien"] = int(r["so_tien"])
            return rows
    finally:
        release_connection(conn)


def tao_chot_ca(
    nhan_vien_id: str,
    van_phong_id: str | None,
    tu_luc_da_xem: datetime | None,
    den_luc: datetime,
    tien_thuc_dem: int,
    ghi_chu: str | None,
) -> dict:
    """Chốt ca trong 1 transaction: khóa theo nhân viên (2 lần bấm cùng lúc thì lần sau chờ), lấy mốc lần chốt
    trước làm tu_luc, tính tổng đúng khoảng (tu_luc, den_luc] rồi INSERT. CHECK của bảng bảo đảm phải có /
    chênh lệch tính đúng và lệch thì phải có ghi chú. Ném DaChotSauMocNay nếu đã chốt tới mốc này rồi, hoặc
    mốc lần chốt trước không còn là `tu_luc_da_xem` (cửa sổ khác vừa chốt — khoảng của ca đã đổi)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"chot_ca:{nhan_vien_id}",))
            cur.execute("SELECT max(den_luc) FROM chot_ca_gui_hang WHERE nhan_vien_id = %s", (nhan_vien_id,))
            tu_luc = cur.fetchone()[0]
            if (tu_luc is not None and den_luc <= tu_luc) or tu_luc != tu_luc_da_xem:
                conn.rollback()
                raise DaChotSauMocNay()
            cur.execute(_SQL_TONG, {"nv": nhan_vien_id, "tu": tu_luc, "den": den_luc})
            tong = {k: int(v or 0) for k, v in _thanh_dict(cur, cur.fetchone()).items()}
            phai_co = tong["tien_tra_truoc"] + tong["tien_cod"] - tong["tien_hoan"]
            cur.execute(
                """
                INSERT INTO chot_ca_gui_hang (
                    nhan_vien_id, van_phong_id, tu_luc, den_luc,
                    so_don_tra_truoc, tien_tra_truoc, so_don_cod, tien_cod, so_don_hoan, tien_hoan,
                    tien_phai_co, tien_thuc_dem, chenh_lech, ghi_chu
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (nhan_vien_id, van_phong_id, tu_luc, den_luc,
                 tong["so_don_tra_truoc"], tong["tien_tra_truoc"], tong["so_don_cod"], tong["tien_cod"],
                 tong["so_don_hoan"], tong["tien_hoan"], phai_co, tien_thuc_dem, tien_thuc_dem - phai_co, ghi_chu),
            )
            chot_id = str(cur.fetchone()[0])
        conn.commit()
    except DaChotSauMocNay:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
    return tim_theo_id(chot_id)


_SELECT_CHOT_CA = """
    SELECT cc.*, nd.ho_ten AS ten_nhan_vien, vp.ten AS ten_van_phong
    FROM chot_ca_gui_hang cc
    LEFT JOIN nguoi_dung nd ON nd.id = cc.nhan_vien_id
    LEFT JOIN diem_don_tra vp ON vp.id = cc.van_phong_id
"""

_COT_SO = ("so_don_tra_truoc", "tien_tra_truoc", "so_don_cod", "tien_cod", "so_don_hoan", "tien_hoan",
           "tien_phai_co", "tien_thuc_dem", "chenh_lech")


def _chuan_hoa(row: dict | None) -> dict | None:
    if row:
        for k in _COT_SO:
            row[k] = int(row[k])
    return row


def tim_theo_id(chot_ca_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"{_SELECT_CHOT_CA} WHERE cc.id = %s", (chot_ca_id,))
            return _chuan_hoa(_thanh_dict(cur, cur.fetchone()))
    finally:
        release_connection(conn)


def lay_lich_su(
    nhan_vien_id: str | None,
    van_phong_id: str | None,
    tu_ngay: date | None,
    den_ngay: date | None,
    chi_lech: bool,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    """Lịch sử chốt ca, mới nhất trước. Lọc theo nhân viên / văn phòng / ngày chốt (giờ VN) / chỉ ca bị lệch."""
    dk: list[str] = []
    ts: list[Any] = []
    if nhan_vien_id:
        dk.append("cc.nhan_vien_id = %s")
        ts.append(nhan_vien_id)
    if van_phong_id:
        dk.append("cc.van_phong_id = %s")
        ts.append(van_phong_id)
    if tu_ngay:
        dk.append(f"(cc.den_luc AT TIME ZONE '{MUI_GIO_VN}')::date >= %s")
        ts.append(tu_ngay)
    if den_ngay:
        dk.append(f"(cc.den_luc AT TIME ZONE '{MUI_GIO_VN}')::date <= %s")
        ts.append(den_ngay)
    if chi_lech:
        dk.append("cc.chenh_lech <> 0")
    where = f"WHERE {' AND '.join(dk)}" if dk else ""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM chot_ca_gui_hang cc {where}", tuple(ts))
            total = int(cur.fetchone()[0])
            cur.execute(f"{_SELECT_CHOT_CA} {where} ORDER BY cc.den_luc DESC, cc.id LIMIT %s OFFSET %s",
                        tuple(ts + [limit, offset]))
            return [_chuan_hoa(r) for r in _thanh_danh_sach_dict(cur, cur.fetchall())], total
    finally:
        release_connection(conn)
