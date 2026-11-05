"""Raw SQL ĐỌC nhật ký thao tác — UC-52 (NGHIEP_VU.md UC-52, mục 8.9 điểm 7).

Gộp hai bảng nhật ký cùng cấu trúc, chỉ đọc (không có hàm ghi/sửa/xóa — hai bảng chỉ INSERT):
- nhat_ky_quan_ly_nhan_su: hành động của quan_ly_nhan_su (DATABASE.md mục 6.3)
- nhat_ky_admin: hành động của quan_ly, dùng chung nhiều nhóm chức năng (mục 6.2)

Hàm ghi nằm ở nhat_ky_quan_ly_nhan_su_repository.py / nhat_ky_admin_repository.py (không sửa ở đây).

Phạm vi xem:
- gioi_han_nguoi_id có giá trị -> CHỈ đọc nhat_ky_quan_ly_nhan_su, CHỈ dòng của người đó (dành cho
  quan_ly_nhan_su; câu SQL không hề chạm bảng nhat_ky_admin).
- gioi_han_nguoi_id = None -> đọc cả hai bảng (dành cho quan_ly).

Mọi giá trị người dùng truyền qua %s; chuỗi SQL chỉ nối thêm các điều kiện cố định (không nối dữ liệu).
"""

from app.db import get_connection, release_connection

# Hai nguồn có cùng cột để UNION ALL; `nguon` cho biết dòng đến từ bảng nào.
_NGUON_QLNS = """
    SELECT id, 'quan_ly_nhan_su' AS nguon, quan_ly_nhan_su_id AS nguoi_id, hanh_dong, doi_tuong_loai,
           doi_tuong_id, ghi_chu, thoi_gian
    FROM nhat_ky_quan_ly_nhan_su
"""
_NGUON_ADMIN = """
    SELECT id, 'admin' AS nguon, admin_id AS nguoi_id, hanh_dong, doi_tuong_loai,
           doi_tuong_id, ghi_chu, thoi_gian
    FROM nhat_ky_admin
"""


def _nguon(gioi_han_nguoi_id: str | None) -> tuple[str, list]:
    """Trả (câu SQL của CTE `nk`, tham số của nó)."""
    if gioi_han_nguoi_id:
        return _NGUON_QLNS + " WHERE quan_ly_nhan_su_id = %s", [gioi_han_nguoi_id]
    return _NGUON_QLNS + " UNION ALL " + _NGUON_ADMIN, []


def _dieu_kien(tu, den, hanh_dong, doi_tuong_loai, nguoi_id) -> tuple[str, list]:
    cac_dk: list[str] = []
    tham_so: list = []
    if tu is not None:
        cac_dk.append("nk.thoi_gian >= %s")
        tham_so.append(tu)
    if den is not None:
        cac_dk.append("nk.thoi_gian < %s")  # den = đầu ngày KẾ TIẾP (Service tính)
        tham_so.append(den)
    if hanh_dong:
        cac_dk.append("nk.hanh_dong = %s")
        tham_so.append(hanh_dong)
    if doi_tuong_loai:
        cac_dk.append("nk.doi_tuong_loai = %s")
        tham_so.append(doi_tuong_loai)
    if nguoi_id:
        cac_dk.append("nk.nguoi_id = %s")
        tham_so.append(nguoi_id)
    return (" WHERE " + " AND ".join(cac_dk)) if cac_dk else "", tham_so


def tim(
    gioi_han_nguoi_id: str | None,
    tu=None,
    den=None,
    hanh_dong: str | None = None,
    doi_tuong_loai: str | None = None,
    nguoi_id: str | None = None,
    trang: int = 1,
    so_dong: int = 50,
) -> tuple[list[dict], int]:
    """Một trang nhật ký (mới nhất trước) + tổng số dòng khớp bộ lọc.

    tu / den: datetime có múi giờ, khoảng [tu, den). Tên + mã của người thực hiện lấy từ nguoi_dung; của đối
    tượng lấy từ nguoi_dung (doi_tuong_loai = 'nguoi_dung') hoặc nhan_su_van_hanh ('nhan_su_van_hanh', phụ xe lấy
    mã của tài khoản). Loại đối tượng khác (nhóm khác ghi vào nhat_ky_admin) -> ten/ma = NULL, Service hiển thị thô."""
    cte, tham_so_cte = _nguon(gioi_han_nguoi_id)
    where, tham_so_dk = _dieu_kien(tu, den, hanh_dong, doi_tuong_loai, nguoi_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"WITH nk AS ({cte}) SELECT count(*) FROM nk{where}", tham_so_cte + tham_so_dk)
            tong = cur.fetchone()[0]

            cur.execute(
                f"""
                WITH nk AS ({cte})
                SELECT nk.id, nk.nguon, nk.nguoi_id, u.ho_ten AS ten_nguoi, u.ma AS ma_nguoi, u.vai_tro AS vai_tro_nguoi,
                       nk.hanh_dong, nk.doi_tuong_loai, nk.doi_tuong_id,
                       CASE nk.doi_tuong_loai WHEN 'nguoi_dung' THEN dn.ho_ten WHEN 'nhan_su_van_hanh' THEN ns.ho_ten END AS ten_doi_tuong,
                       CASE nk.doi_tuong_loai WHEN 'nguoi_dung' THEN dn.ma WHEN 'nhan_su_van_hanh' THEN COALESCE(ns.ma, nsnd.ma) END AS ma_doi_tuong,
                       nk.ghi_chu, nk.thoi_gian
                FROM nk
                JOIN nguoi_dung u ON u.id = nk.nguoi_id
                LEFT JOIN nguoi_dung dn ON nk.doi_tuong_loai = 'nguoi_dung' AND dn.id = nk.doi_tuong_id
                LEFT JOIN nhan_su_van_hanh ns ON nk.doi_tuong_loai = 'nhan_su_van_hanh' AND ns.id = nk.doi_tuong_id
                LEFT JOIN nguoi_dung nsnd ON nsnd.id = ns.nguoi_dung_id
                {where}
                ORDER BY nk.thoi_gian DESC, nk.id
                LIMIT %s OFFSET %s
                """,
                tham_so_cte + tham_so_dk + [so_dong, (trang - 1) * so_dong],
            )
            cot = [c[0] for c in cur.description]
            return [dict(zip(cot, r)) for r in cur.fetchall()], tong
    finally:
        release_connection(conn)


def danh_sach_nguoi_thuc_hien() -> list[dict]:
    """Những người đã từng có dòng nhật ký (cả hai bảng) — đổ ô chọn "người thực hiện" cho quan_ly."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                WITH nk AS ({_NGUON_QLNS} UNION ALL {_NGUON_ADMIN})
                SELECT DISTINCT u.id, u.ho_ten, u.ma, u.vai_tro
                FROM nk JOIN nguoi_dung u ON u.id = nk.nguoi_id
                ORDER BY u.ho_ten
                """
            )
            cot = [c[0] for c in cur.description]
            return [dict(zip(cot, r)) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def cac_gia_tri_loc(gioi_han_nguoi_id: str | None) -> dict:
    """Các giá trị hanh_dong / doi_tuong_loai hiện có trong phạm vi được xem — đổ ô lọc. nhat_ky_admin để TEXT tự
    do (nhiều nhóm ghi) nên liệt kê từ dữ liệu thật thay vì cố định."""
    cte, tham_so = _nguon(gioi_han_nguoi_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"WITH nk AS ({cte}) SELECT DISTINCT hanh_dong FROM nk ORDER BY hanh_dong", tham_so)
            hanh_dong = [r[0] for r in cur.fetchall()]
            cur.execute(f"WITH nk AS ({cte}) SELECT DISTINCT doi_tuong_loai FROM nk ORDER BY doi_tuong_loai", tham_so)
            doi_tuong = [r[0] for r in cur.fetchall()]
            return {"hanh_dong": hanh_dong, "doi_tuong_loai": doi_tuong}
    finally:
        release_connection(conn)
