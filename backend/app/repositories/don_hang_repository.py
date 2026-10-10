"""Raw SQL Repository cho bảng don_hang và loai_hang — DATABASE.md mục 5.

Thao tác trực tiếp với CSDL qua psycopg2, không chứa logic nghiệp vụ
(logic thuộc về services/gui_hang_service.py).
"""

from datetime import date
from typing import Any

from psycopg2 import errors

from app.db import get_connection, release_connection

MUI_GIO_VN = "Asia/Ho_Chi_Minh"


class MaVanDonDaTonTai(Exception):
    """Mã vận đơn sinh ngẫu nhiên bị trùng — service sinh lại mã và thử lại."""


def _thanh_dict(cur: Any, row: Any) -> dict | None:
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _thanh_danh_sach_dict(cur: Any, rows: list) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


# Câu truy vấn SELECT chuẩn: loại hàng, tuyến, văn phòng gửi/nhận (kèm địa chỉ,
# SĐT liên hệ văn phòng nhận — in lên biên nhận, mục 10.3.1 điểm 1), số báo cáo
# sự cố (UC-28) và chuyến/xe đang chở (nếu đã lên xe).
SELECT_DON_HANG_FULL = """
    SELECT
        d.*,
        lh.ten AS ten_loai_hang,
        t.ten AS ten_tuyen,
        dg.ten AS ten_diem_gui,
        dg.dia_chi AS dia_chi_diem_gui,
        dn.ten AS ten_diem_nhan,
        dn.dia_chi AS dia_chi_diem_nhan,
        dn.sdt_lien_he AS sdt_diem_nhan,
        c.ma AS ma_chuyen,
        c.gio_khoi_hanh AS gio_khoi_hanh,
        x.bien_so AS bien_so_xe,
        (SELECT count(*) FROM bao_cao_su_co_hang bc WHERE bc.don_hang_id = d.id)::int AS so_bao_cao_su_co,
        (SELECT count(*) FROM lich_su_chinh_sua_don cs WHERE cs.don_hang_id = d.id)::int AS so_lan_chinh_sua
    FROM don_hang d
    LEFT JOIN loai_hang lh ON d.loai_hang_id = lh.id
    LEFT JOIN tuyen t ON d.tuyen_id = t.id
    LEFT JOIN diem_don_tra dg ON d.diem_gui_id = dg.id
    LEFT JOIN diem_don_tra dn ON d.diem_nhan_id = dn.id
    LEFT JOIN chuyen_xe c ON c.id = d.chuyen_id
    LEFT JOIN xe x ON x.id = COALESCE(c.xe_thuc_te_id, c.xe_id)
"""


# ====================================================================
# 1. Thao tác Loại hàng (loai_hang)
# ====================================================================

def lay_danh_sach_loai_hang() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang ORDER BY la_hang_cam, ten")
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_loai_hang_theo_id(loai_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ten, la_hang_cam FROM loai_hang WHERE id = %s", (loai_hang_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 2. Tạo và Tra cứu Đơn hàng (don_hang)
# ====================================================================

def _ghi_nguoi_thuc_hien(cur: Any, nguoi_dung_id: str | None) -> None:
    """Báo cho trigger lich_su_trang_thai_don biết ai đang đổi trạng thái (trong transaction này)."""
    if nguoi_dung_id:
        cur.execute("SELECT set_config('app.nguoi_dung_id', %s, true)", (str(nguoi_dung_id),))


def tim_theo_khoa_chong_trung(nhan_vien_id: str, khoa: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM don_hang WHERE nhan_vien_gui_id = %s AND khoa_chong_trung = %s",
                (nhan_vien_id, khoa),
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)
    return tim_theo_id(str(row[0])) if row else None


def tao_don_hang(du_lieu: dict) -> dict:
    """INSERT 1 đơn. Ném MaVanDonDaTonTai nếu trùng ma_van_don (để service sinh lại mã).

    Nếu `khoa_chong_trung` đã được dùng bởi cùng nhân viên (2 request song song) thì
    trả lại đơn đã tạo thay vì tạo thêm.
    """
    du_lieu = {"khoa_chong_trung": None, **du_lieu}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO don_hang (
                        ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, loai_hang_id,
                        can_nang_kg, dai_cm, rong_cm, cao_cm, gia_cuoc,
                        ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan,
                        phuong_thuc_thanh_toan, nhan_vien_gui_id, trang_thai,
                        da_thu_tien, thoi_gian_thu, nhan_vien_thu_id, khoa_chong_trung
                    ) VALUES (
                        %(ma_van_don)s, %(tuyen_id)s, %(diem_gui_id)s, %(diem_nhan_id)s, %(loai_hang_id)s,
                        %(can_nang_kg)s, %(dai_cm)s, %(rong_cm)s, %(cao_cm)s, %(gia_cuoc)s,
                        %(ten_nguoi_gui)s, %(sdt_nguoi_gui)s, %(ten_nguoi_nhan)s, %(sdt_nguoi_nhan)s,
                        %(phuong_thuc_thanh_toan)s, %(nhan_vien_gui_id)s, 'cho_van_chuyen',
                        %(da_thu_tien)s, CASE WHEN %(da_thu_tien)s THEN now() ELSE NULL END, %(nhan_vien_thu_id)s,
                        %(khoa_chong_trung)s
                    )
                    RETURNING id
                    """,
                    du_lieu,
                )
            except errors.UniqueViolation as exc:
                conn.rollback()
                ten_rang_buoc = exc.diag.constraint_name or ""
                if "ma_van_don" in ten_rang_buoc:
                    raise MaVanDonDaTonTai() from exc
                if "khoa_chong_trung" in ten_rang_buoc:
                    don_cu = tim_theo_khoa_chong_trung(du_lieu["nhan_vien_gui_id"], du_lieu["khoa_chong_trung"])
                    if don_cu:
                        return don_cu
                raise
            don_id = str(cur.fetchone()[0])
        conn.commit()
        return tim_theo_id(don_id) or {}
    finally:
        release_connection(conn)


def tim_theo_ma_van_don(ma_van_don: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"{SELECT_DON_HANG_FULL} WHERE d.ma_van_don = %s", (ma_van_don,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_id(don_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"{SELECT_DON_HANG_FULL} WHERE d.id = %s", (don_hang_id,))
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def tim_theo_sdt(sdt: str, van_phong_id: str | None = None, chi_cho_giao: bool = False) -> list[dict]:
    """Tra cứu đơn theo SĐT người gửi hoặc người nhận.

    chi_cho_giao=True: chỉ đơn đang chờ giao TẠI văn phòng này (người nhận
    quên mã vận đơn — mục 10.3.1 điểm 5, 10.4.2 bước 2), khớp theo SĐT người nhận.
    """
    dieu_kien = []
    params: list = []
    if chi_cho_giao:
        dieu_kien.append("d.sdt_nguoi_nhan = %s AND d.trang_thai IN ('cho_lay', 'qua_han_luu_kho')")
        params.append(sdt)
        if van_phong_id:
            dieu_kien.append("d.diem_nhan_id = %s")
            params.append(van_phong_id)
    else:
        dieu_kien.append("(d.sdt_nguoi_gui = %s OR d.sdt_nguoi_nhan = %s)")
        params.extend([sdt, sdt])
        if van_phong_id:
            dieu_kien.append("(d.diem_gui_id = %s OR d.diem_nhan_id = %s)")
            params.extend([van_phong_id, van_phong_id])

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"{SELECT_DON_HANG_FULL} WHERE {' AND '.join(dieu_kien)} ORDER BY d.ngay_tao DESC LIMIT 50",
                tuple(params),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ====================================================================
# 3. Cập nhật Trạng thái Đơn hàng (Giao hàng, Chất/Dỡ hàng)
# ====================================================================

def cap_nhat_giao_hang(
    don_hang_id: str, nhan_vien_nhan_id: str, van_phong_id: str | None = None,
    xac_nhan_da_thu: bool = False,
) -> dict | None:
    """UC-24: Xác nhận đã giao hàng cho người nhận (điều kiện trạng thái nằm trong UPDATE)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ghi_nguoi_thuc_hien(cur, nhan_vien_nhan_id)
            dieu_kien_van_phong = "AND diem_nhan_id = %s" if van_phong_id else ""
            cur.execute(
                f"""
                UPDATE don_hang
                SET trang_thai = 'da_giao',
                    nhan_vien_nhan_id = %s,
                    ngay_giao = now(),
                    da_thu_tien = CASE WHEN %s THEN true ELSE da_thu_tien END,
                    thoi_gian_thu = CASE WHEN %s THEN now() ELSE thoi_gian_thu END,
                    nhan_vien_thu_id = CASE WHEN %s THEN %s ELSE nhan_vien_thu_id END
                WHERE id = %s
                  AND trang_thai IN ('cho_lay', 'qua_han_luu_kho')
                  {dieu_kien_van_phong}
                  AND (phuong_thuc_thanh_toan <> 'cod_nguoi_nhan_tra' OR %s)
                RETURNING id
                """,
                tuple(([nhan_vien_nhan_id, xac_nhan_da_thu, xac_nhan_da_thu, xac_nhan_da_thu,
                        nhan_vien_nhan_id if xac_nhan_da_thu else None, don_hang_id]
                       + ([van_phong_id] if van_phong_id else []) + [xac_nhan_da_thu])),
            )
            if not cur.fetchone():
                conn.rollback()
                return None
        conn.commit()
        return tim_theo_id(don_hang_id)
    finally:
        release_connection(conn)


def cap_nhat_chat_hang_len_chuyen(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str | None = None) -> dict | None:
    """UC-26 (Phụ xe): Chất hàng lên chuyến xe.

    Điều kiện trạng thái nằm ngay trong UPDATE: 2 phụ xe cùng bấm 1 đơn thì
    chỉ 1 người thành công, người còn lại nhận None.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ghi_nguoi_thuc_hien(cur, nguoi_dung_id)
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'da_len_xe',
                    chuyen_id = %s
                WHERE id = %s
                  AND trang_thai = 'cho_van_chuyen'
                  AND chuyen_id IS NULL
                RETURNING id
                """,
                (chuyen_id, don_hang_id),
            )
            if not cur.fetchone():
                conn.rollback()
                return None
        conn.commit()
        return tim_theo_id(don_hang_id)
    finally:
        release_connection(conn)


def cap_nhat_do_hang_tai_diem(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str | None = None) -> dict | None:
    """UC-27 (Phụ xe): Dỡ hàng xuống văn phòng điểm nhận, bắt đầu tính hạn lưu kho."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _ghi_nguoi_thuc_hien(cur, nguoi_dung_id)
            cur.execute(
                """
                UPDATE don_hang
                SET trang_thai = 'cho_lay',
                    thoi_gian_den_diem_nhan = now()
                WHERE id = %s
                  AND trang_thai = 'da_len_xe'
                  AND chuyen_id = %s
                RETURNING id
                """,
                (don_hang_id, chuyen_id),
            )
            if not cur.fetchone():
                conn.rollback()
                return None
        conn.commit()
        return tim_theo_id(don_hang_id)
    finally:
        release_connection(conn)


# ====================================================================
# 4. Liên hệ người nhận / người gửi / báo quản lý (UC-25, mục 10.3.1)
# ====================================================================

def ghi_lien_he(
    don_hang_id: str,
    nhan_vien_id: str,
    doi_tuong: str,
    ket_qua: str,
    ghi_chu: str | None,
    danh_dau_da_thong_bao: bool,
    thong_bao_cho: list[str],
    noi_dung_thong_bao: str | None,
) -> None:
    """Ghi lịch sử liên hệ + bật cờ 'đã thông báo được người nhận' + tạo thông
    báo (báo quản lý) trong CÙNG 1 transaction — không để lệch dữ liệu khi lỗi giữa chừng.

    Cờ da_thong_bao_nguoi_nhan chỉ đi lên true, không bao giờ hạ về false
    (mục 10.3.1 điểm 2: tích khi đã gọi báo được người nhận).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO lich_su_lien_he_don_hang
                   (don_hang_id, nhan_vien_id, doi_tuong, ket_qua, ghi_chu)
                   VALUES (%s, %s, %s, %s, %s)""",
                (don_hang_id, nhan_vien_id, doi_tuong, ket_qua, ghi_chu),
            )
            if danh_dau_da_thong_bao:
                cur.execute(
                    "UPDATE don_hang SET da_thong_bao_nguoi_nhan = true WHERE id = %s",
                    (don_hang_id,),
                )
            for nguoi_nhan_id in thong_bao_cho:
                cur.execute(
                    "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, don_hang_id) VALUES (%s, %s, %s)",
                    (nguoi_nhan_id, noi_dung_thong_bao, don_hang_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_lich_su_lien_he(don_hang_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ls.id, ls.doi_tuong, ls.ket_qua, ls.ghi_chu, ls.ngay_tao,
                       nd.ho_ten AS ten_nhan_vien
                FROM lich_su_lien_he_don_hang ls
                LEFT JOIN nguoi_dung nd ON nd.id = ls.nhan_vien_id
                WHERE ls.don_hang_id = %s
                ORDER BY ls.ngay_tao DESC
                """,
                (don_hang_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


TRUONG_LIEN_HE_CHO_PHEP = frozenset({"ten_nguoi_gui", "sdt_nguoi_gui", "ten_nguoi_nhan", "sdt_nguoi_nhan"})


class DonDaGiao(Exception):
    """Đơn đã giao xong — không sửa được nữa."""


def sua_thong_tin_lien_he(don_hang_id: str, thay_doi: dict, nguoi_dung_id: str, ly_do: str | None) -> dict | None:
    """Sửa tên/SĐT người gửi/nhận + ghi nhật ký từng trường đổi, cùng 1 transaction.

    Khóa dòng đơn (FOR UPDATE) rồi mới kiểm tra trạng thái: nếu người khác vừa giao đơn thì
    không sửa lọt sang đơn đã giao. Trả None nếu không có đơn; chỉ ghi trường thực sự đổi
    (gõ lại đúng giá trị cũ thì không tạo nhật ký thừa). Ném DonDaGiao khi đơn đã giao.
    Tên cột lấy từ khóa của `thay_doi` nên service chỉ được truyền các khóa trong TRUONG_LIEN_HE.
    """
    cac_truong = tuple(thay_doi)
    if not cac_truong or not set(cac_truong) <= TRUONG_LIEN_HE_CHO_PHEP:
        raise ValueError("Trường sửa không hợp lệ")  # tên cột được ghép vào SQL nên chỉ nhận danh sách cố định
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT trang_thai, {', '.join(cac_truong)} FROM don_hang WHERE id = %s FOR UPDATE",
                (don_hang_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None
            if row[0] == "da_giao":
                conn.rollback()
                raise DonDaGiao()
            hien_tai = dict(zip(cac_truong, row[1:]))
            doi = {t: v for t, v in thay_doi.items() if hien_tai[t] != v}
            if doi:
                cur.execute(
                    f"UPDATE don_hang SET {', '.join(f'{t} = %s' for t in doi)} WHERE id = %s",
                    (*doi.values(), don_hang_id),
                )
                for truong, moi in doi.items():
                    cur.execute(
                        # clock_timestamp(), không phải now(): now() là lúc BẮT ĐẦU transaction, còn các
                        # lần sửa xếp hàng chờ khóa dòng nên phải đóng dấu thời gian sau khi đã giữ khóa.
                        """INSERT INTO lich_su_chinh_sua_don
                               (don_hang_id, truong, gia_tri_cu, gia_tri_moi, nguoi_thuc_hien_id, ly_do, thoi_gian)
                           VALUES (%s, %s, %s, %s, %s, %s, clock_timestamp())""",
                        (don_hang_id, truong, hien_tai[truong], moi, nguoi_dung_id, ly_do),
                    )
        conn.commit()
        return tim_theo_id(don_hang_id)
    finally:
        release_connection(conn)


def lay_lich_su_chinh_sua(don_hang_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cs.truong, cs.gia_tri_cu, cs.gia_tri_moi, cs.ly_do, cs.thoi_gian,
                       nd.ho_ten AS ten_nguoi_thuc_hien
                FROM lich_su_chinh_sua_don cs
                LEFT JOIN nguoi_dung nd ON nd.id = cs.nguoi_thuc_hien_id
                WHERE cs.don_hang_id = %s
                ORDER BY cs.thoi_gian DESC, cs.id
                """,
                (don_hang_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_lich_su_trang_thai(don_hang_id: str) -> list[dict]:
    """Các mốc đổi trạng thái của đơn, cũ → mới. ten_nguoi_thuc_hien NULL = hệ thống tự chuyển."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ls.tu_trang_thai, ls.den_trang_thai, ls.thoi_gian,
                       nd.ho_ten AS ten_nguoi_thuc_hien
                FROM lich_su_trang_thai_don ls
                LEFT JOIN nguoi_dung nd ON nd.id = ls.nguoi_thuc_hien_id
                WHERE ls.don_hang_id = %s
                ORDER BY ls.thoi_gian, ls.id
                """,
                (don_hang_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def goi_y_khach_theo_sdt(sdt: str, la_nguoi_gui: bool, van_phong_id: str | None, limit: int = 5) -> list[dict]:
    """Các tên từng đi kèm SĐT này trong đơn của văn phòng (mới nhất trước).

    Chỉ nhìn đơn có điểm gửi/nhận là văn phòng mình — không lộ dữ liệu khách của văn phòng khác.
    """
    cot_sdt, cot_ten = ("sdt_nguoi_gui", "ten_nguoi_gui") if la_nguoi_gui else ("sdt_nguoi_nhan", "ten_nguoi_nhan")
    dieu_kien_vp = "AND (diem_gui_id = %s OR diem_nhan_id = %s)" if van_phong_id else ""
    tham_so: list[Any] = [sdt] + ([van_phong_id, van_phong_id] if van_phong_id else []) + [limit]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {cot_ten} AS ten, COUNT(*) AS so_don, MAX(ngay_tao) AS lan_cuoi
                FROM don_hang
                WHERE {cot_sdt} = %s {dieu_kien_vp}
                GROUP BY {cot_ten}
                ORDER BY MAX(ngay_tao) DESC
                LIMIT %s
                """,
                tuple(tham_so),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_bao_cao_su_co(don_hang_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT bc.id, bc.mo_ta, bc.ngay_tao, nd.ho_ten AS ten_nguoi_bao_cao
                FROM bao_cao_su_co_hang bc
                LEFT JOIN nguoi_dung nd ON nd.id = bc.nguoi_bao_cao_id
                WHERE bc.don_hang_id = %s
                ORDER BY bc.ngay_tao DESC
                """,
                (don_hang_id,),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


# ====================================================================
# 5. Truy vấn Tuyến 2 Chiều & Điểm nhận (UC-23)
# ====================================================================

def danh_sach_diem_nhan_kha_dung(van_phong_gui_id: str) -> list[dict]:
    """Văn phòng có thể nhận hàng từ văn phòng gửi: loai='van_phong', khác văn
    phòng gửi, và có ít nhất 1 tuyến đi qua cả 2 (tuyến chạy 2 chiều nên không
    xét thứ tự). Kèm khu vực để giao diện chọn 2 tầng khu_vực → văn phòng (mục 10.4.1 bước 3)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dd.id, dd.ten, dd.dia_chi, dd.khu_vuc_id,
                       kv.ten AS ten_khu_vuc, kv.tinh_thanh
                FROM diem_don_tra dd
                JOIN khu_vuc kv ON kv.id = dd.khu_vuc_id
                WHERE dd.loai = 'van_phong'
                  AND dd.id <> %(gui)s
                  AND EXISTS (
                      SELECT 1
                      FROM tuyen_diem_don_tra a
                      JOIN tuyen_diem_don_tra b ON b.tuyen_id = a.tuyen_id
                      WHERE a.diem_don_tra_id = %(gui)s AND b.diem_don_tra_id = dd.id
                  )
                ORDER BY kv.ten, dd.ten
                """,
                {"gui": van_phong_gui_id},
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_cac_tuyen_qua_hai_diem(diem_gui_id: str, diem_nhan_id: str) -> list[dict]:
    """Tìm mọi tuyến vận chuyển đi qua cả 2 điểm dừng (gửi và nhận) — UC-23, NGHIEP_VU.md mục 10.4.1."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    t.id, t.ma, t.ten,
                    tdt_gui.thu_tu AS thu_tu_gui,
                    tdt_nhan.thu_tu AS thu_tu_nhan,
                    CASE
                        WHEN tdt_gui.thu_tu < tdt_nhan.thu_tu THEN 'xuoi'
                        ELSE 'nguoc'
                    END AS chieu_van_chuyen
                FROM tuyen t
                JOIN tuyen_diem_don_tra tdt_gui ON t.id = tdt_gui.tuyen_id AND tdt_gui.diem_don_tra_id = %s
                JOIN tuyen_diem_don_tra tdt_nhan ON t.id = tdt_nhan.tuyen_id AND tdt_nhan.diem_don_tra_id = %s
                ORDER BY t.ten
                """,
                (diem_gui_id, diem_nhan_id),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def kiem_tra_diem_thuoc_tuyen(tuyen_id: str, diem_gui_id: str, diem_nhan_id: str) -> dict | None:
    """Kiểm tra điểm gửi và điểm nhận có cùng nằm trên tuyến không, trả về thứ tự và chiều vận chuyển."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    t.id, t.ma, t.ten,
                    tdt_gui.thu_tu AS thu_tu_gui,
                    tdt_nhan.thu_tu AS thu_tu_nhan,
                    CASE
                        WHEN tdt_gui.thu_tu < tdt_nhan.thu_tu THEN 'xuoi'
                        ELSE 'nguoc'
                    END AS chieu_van_chuyen
                FROM tuyen t
                JOIN tuyen_diem_don_tra tdt_gui ON t.id = tdt_gui.tuyen_id AND tdt_gui.diem_don_tra_id = %s
                JOIN tuyen_diem_don_tra tdt_nhan ON t.id = tdt_nhan.tuyen_id AND tdt_nhan.diem_don_tra_id = %s
                WHERE t.id = %s
                """,
                (diem_gui_id, diem_nhan_id, tuyen_id),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


# ====================================================================
# 6. Phục vụ Phụ xe (UC-26, UC-27, UC-28)
# ====================================================================

def tim_chuyen_xe_theo_id(chuyen_id: str) -> dict | None:
    """Tra cứu thông tin chuyến xe phục vụ nghiệp vụ xếp dỡ hàng của phụ xe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tuyen_id, xe_id, xe_thuc_te_id, gio_khoi_hanh, chieu, trang_thai, dang_hoan
                FROM chuyen_xe
                WHERE id = %s
                """,
                (chuyen_id,),
            )
            return _thanh_dict(cur, cur.fetchone())
    finally:
        release_connection(conn)


def lay_danh_sach_cho_xep_xe(tuyen_id: str, chuyen_id: str | None = None) -> list[dict]:
    """UC-26: Lấy các đơn hàng đang chờ chất lên xe tại tuyến này.

    Nếu có chuyen_id, chỉ lấy các đơn CÙNG CHIỀU với chuyến xe (mục 10.2 & THAY_DOI_TUYEN_2_CHIEU.md).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            chieu_chuyen = None
            if chuyen_id:
                cur.execute("SELECT chieu FROM chuyen_xe WHERE id = %s", (chuyen_id,))
                row = cur.fetchone()
                if row:
                    chieu_chuyen = row[0]

            if chieu_chuyen:
                sql = f"""
                    {SELECT_DON_HANG_FULL}
                    JOIN tuyen_diem_don_tra tdt_gui ON d.tuyen_id = tdt_gui.tuyen_id AND d.diem_gui_id = tdt_gui.diem_don_tra_id
                    JOIN tuyen_diem_don_tra tdt_nhan ON d.tuyen_id = tdt_nhan.tuyen_id AND d.diem_nhan_id = tdt_nhan.diem_don_tra_id
                    WHERE d.tuyen_id = %s
                      AND d.chuyen_id IS NULL
                      AND d.trang_thai = 'cho_van_chuyen'
                      AND (
                          (%s = 'xuoi' AND tdt_gui.thu_tu < tdt_nhan.thu_tu)
                          OR
                          (%s = 'nguoc' AND tdt_gui.thu_tu > tdt_nhan.thu_tu)
                      )
                    ORDER BY d.ngay_tao ASC
                """
                cur.execute(sql, (tuyen_id, chieu_chuyen, chieu_chuyen))
            else:
                sql = f"""
                    {SELECT_DON_HANG_FULL}
                    WHERE d.tuyen_id = %s AND d.chuyen_id IS NULL AND d.trang_thai = 'cho_van_chuyen'
                    ORDER BY d.ngay_tao ASC
                """
                cur.execute(sql, (tuyen_id,))
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_don_can_do_tai_diem(chuyen_id: str, diem_nhan_id: str) -> list[dict]:
    """UC-27 (Phụ xe): đơn đang trên xe (da_len_xe), cần dỡ tại đúng điểm
    nhận này của đúng chuyến này — bổ sung cho phần phụ xe (tuanhdung)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ma_van_don, ten_nguoi_nhan, can_nang_kg
                FROM don_hang
                WHERE chuyen_id = %s AND diem_nhan_id = %s AND trang_thai = 'da_len_xe'
                ORDER BY ngay_tao ASC
                """,
                (chuyen_id, diem_nhan_id),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def luu_bao_cao_su_co_hang(don_hang_id: str, nguoi_bao_cao_id: str, mo_ta: str) -> dict:
    """UC-28 (Phụ xe): Ghi nhận biên bản sự cố thất lạc / hư hỏng hàng hóa."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bao_cao_su_co_hang (don_hang_id, nguoi_bao_cao_id, mo_ta)
                VALUES (%s, %s, %s)
                RETURNING id, don_hang_id, nguoi_bao_cao_id, mo_ta, ngay_tao
                """,
                (don_hang_id, nguoi_bao_cao_id, mo_ta),
            )
            res = _thanh_dict(cur, cur.fetchone())
        conn.commit()
        return res or {}
    finally:
        release_connection(conn)


# ====================================================================
# 7. Hàng đến văn phòng nhận (UC-24, UC-25, mục 10.4.2)
# ====================================================================

def lay_hang_den(diem_nhan_id: str | None = None) -> list[dict]:
    """Mọi đơn đang hướng về / đang nằm ở văn phòng nhận và chưa giao xong:
    sắp đến (da_len_xe), chờ lấy (cho_lay), hàng tồn (qua_han_luu_kho).
    diem_nhan_id=None: toàn hệ thống (quản lý xem để xử lý hàng tồn, UC-25)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                {SELECT_DON_HANG_FULL}
                WHERE d.trang_thai IN ('da_len_xe', 'cho_lay', 'qua_han_luu_kho')
                  AND (%(vp)s::uuid IS NULL OR d.diem_nhan_id = %(vp)s::uuid)
                ORDER BY
                    CASE d.trang_thai WHEN 'cho_lay' THEN 0 WHEN 'qua_han_luu_kho' THEN 1 ELSE 2 END,
                    d.da_thong_bao_nguoi_nhan ASC,
                    d.thoi_gian_den_diem_nhan ASC NULLS LAST,
                    c.gio_khoi_hanh ASC NULLS LAST
                LIMIT 500
                """,
                {"vp": diem_nhan_id},
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def danh_sach_nhan_vien_gui_hang_tai_diem(diem_id: str) -> list[str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT h.nguoi_dung_id
                   FROM ho_so_can_bo_diem h
                   JOIN nguoi_dung nd ON nd.id = h.nguoi_dung_id
                   WHERE h.van_phong_id = %s AND nd.vai_tro = 'nhan_vien_gui_hang'
                     AND nd.dang_hoat_dong = true""",
                (diem_id,),
            )
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        release_connection(conn)


# ====================================================================
# 8. Job UC-46: cảnh báo 7 ngày & chuyển hàng tồn 14 ngày
# ====================================================================

_SQL_NHAN_VIEN_TAI_DIEM = """
    SELECT h.nguoi_dung_id
    FROM ho_so_can_bo_diem h
    JOIN nguoi_dung nd ON nd.id = h.nguoi_dung_id
    WHERE h.van_phong_id = %s AND nd.vai_tro = 'nhan_vien_gui_hang' AND nd.dang_hoat_dong = true
"""


def _quet_va_thong_bao(sql_cap_nhat: str, tao_noi_dung) -> tuple[int, list[tuple[str, str]]]:
    """Đổi cờ/trạng thái và ghi thông báo cho nhân viên điểm nhận trong CÙNG 1
    transaction — job lỗi giữa chừng thì rollback cả 2, lần quét sau làm lại,
    không có đơn nào bị bật cờ mà mất thông báo. Trả về (số đơn bị đổi,
    [(nguoi_nhan_id, noi_dung)]) để service đẩy WebSocket SAU khi đã commit."""
    can_day: list[tuple[str, str]] = []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_cap_nhat)
            don_list = _thanh_danh_sach_dict(cur, cur.fetchall())
            for don in don_list:
                noi_dung = tao_noi_dung(don)
                cur.execute(_SQL_NHAN_VIEN_TAI_DIEM, (don["diem_nhan_id"],))
                for (nhan_vien_id,) in cur.fetchall():
                    cur.execute(
                        "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, don_hang_id) VALUES (%s, %s, %s)",
                        (nhan_vien_id, noi_dung, don["id"]),
                    )
                    can_day.append((str(nhan_vien_id), noi_dung))
        conn.commit()
        return len(don_list), can_day
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def quet_canh_bao_7_ngay(tao_noi_dung) -> tuple[int, list[tuple[str, str]]]:
    """UC-46 mốc 7 ngày: bật co_canh_bao_cho_lau (vẫn cho_lay) + nhắc nhân viên điểm nhận."""
    return _quet_va_thong_bao(
        """UPDATE don_hang
           SET co_canh_bao_cho_lau = true
           WHERE trang_thai = 'cho_lay' AND co_canh_bao_cho_lau = false
             AND thoi_gian_den_diem_nhan <= now() - INTERVAL '7 days'
           RETURNING id, ma_van_don, diem_nhan_id, da_thong_bao_nguoi_nhan""",
        tao_noi_dung,
    )


def quet_chuyen_hang_ton_14_ngay(tao_noi_dung) -> tuple[int, list[tuple[str, str]]]:
    """UC-46 mốc 14 ngày: chuyển qua_han_luu_kho ("hàng tồn", KHÔNG tự hủy) + nhắc nhân viên."""
    return _quet_va_thong_bao(
        """UPDATE don_hang
           SET trang_thai = 'qua_han_luu_kho', co_canh_bao_cho_lau = true
           WHERE trang_thai = 'cho_lay'
             AND thoi_gian_den_diem_nhan <= now() - INTERVAL '14 days'
           RETURNING id, ma_van_don, diem_nhan_id, da_thong_bao_nguoi_nhan""",
        tao_noi_dung,
    )


# ====================================================================
# 9. Danh sách đơn tại quầy (có phân trang server) & Thống kê (UC-39)
# ====================================================================

def lay_danh_sach_don(
    van_phong_id: str | None = None,
    huong: str = "tat_ca",
    trang_thai: str | None = None,
    phuong_thuc_thanh_toan: str | None = None,
    tu_khoa: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Danh sách đơn của 1 văn phòng theo hướng: 'gui' (đơn tạo tại quầy mình),
    'nhan' (đơn gửi tới mình), 'tat_ca'. van_phong_id=None: toàn hệ thống.
    Trả về (items, total) — total dùng cho phân trang phía giao diện."""
    clauses: list[str] = []
    params: list = []

    if van_phong_id:
        if huong == "gui":
            clauses.append("d.diem_gui_id = %s")
            params.append(van_phong_id)
        elif huong == "nhan":
            clauses.append("d.diem_nhan_id = %s")
            params.append(van_phong_id)
        else:
            clauses.append("(d.diem_gui_id = %s OR d.diem_nhan_id = %s)")
            params.extend([van_phong_id, van_phong_id])

    if trang_thai:
        clauses.append("d.trang_thai = %s")
        params.append(trang_thai)

    if phuong_thuc_thanh_toan:
        clauses.append("d.phuong_thuc_thanh_toan = %s")
        params.append(phuong_thuc_thanh_toan)

    if tu_khoa and tu_khoa.strip():
        kw = f"%{tu_khoa.strip()}%"
        clauses.append(
            "(d.ma_van_don ILIKE %s OR d.ten_nguoi_gui ILIKE %s OR d.sdt_nguoi_gui ILIKE %s"
            " OR d.ten_nguoi_nhan ILIKE %s OR d.sdt_nguoi_nhan ILIKE %s)"
        )
        params.extend([kw, kw, kw, kw, kw])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM don_hang d {where_sql}", tuple(params))
            total = int(cur.fetchone()[0])
            cur.execute(
                f"{SELECT_DON_HANG_FULL} {where_sql} ORDER BY d.ngay_tao DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall()), total
    finally:
        release_connection(conn)


def thong_ke_hang_tai_diem(diem_id: str | None, tu_ngay: date, den_ngay: date) -> dict:
    """UC-39: chỉ số của 1 văn phòng (hoặc toàn hệ thống nếu diem_id None).

    - Chỉ số LUỒNG lọc theo khoảng [tu_ngay, den_ngay] (giờ Việt Nam), mỗi chỉ
      số theo đúng mốc thời gian của nó: tạo đơn (ngay_tao), hàng tới
      (thoi_gian_den_diem_nhan), giao (ngay_giao), thu tiền (thoi_gian_thu).
    - Chỉ số TỒN là ảnh chụp hiện tại (không phụ thuộc khoảng ngày).
    - Tiền trả trước tính ở văn phòng GỬI, tiền COD tính ở văn phòng NHẬN —
      đúng nơi tiền mặt thực sự vào két.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                WITH p AS (SELECT %(vp)s::uuid AS vp, %(tu)s::date AS tu, %(den)s::date AS den),
                d AS (
                    SELECT d.*,
                        (p.vp IS NULL OR d.diem_gui_id = p.vp) AS la_gui,
                        (p.vp IS NULL OR d.diem_nhan_id = p.vp) AS la_nhan,
                        (d.ngay_tao AT TIME ZONE '{MUI_GIO_VN}')::date BETWEEN p.tu AND p.den AS tao_trong_ky,
                        (d.thoi_gian_den_diem_nhan AT TIME ZONE '{MUI_GIO_VN}')::date BETWEEN p.tu AND p.den AS den_trong_ky,
                        (d.ngay_giao AT TIME ZONE '{MUI_GIO_VN}')::date BETWEEN p.tu AND p.den AS giao_trong_ky,
                        (d.thoi_gian_thu AT TIME ZONE '{MUI_GIO_VN}')::date BETWEEN p.tu AND p.den AS thu_trong_ky
                    FROM don_hang d, p
                )
                SELECT
                    -- Hàng gửi đi (văn phòng gửi)
                    count(*) FILTER (WHERE la_gui AND tao_trong_ky) AS tong_don_gui_di,
                    count(*) FILTER (WHERE la_gui AND trang_thai = 'cho_van_chuyen') AS so_don_cho_xep_xe,
                    count(*) FILTER (WHERE la_gui AND trang_thai = 'da_len_xe') AS so_don_gui_dang_tren_xe,
                    COALESCE(sum(gia_cuoc) FILTER (WHERE la_gui AND phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc'
                                                   AND da_thu_tien AND thu_trong_ky), 0) AS tien_cuoc_gui_tra_truoc,
                    -- Hàng nhận về (văn phòng nhận)
                    count(*) FILTER (WHERE la_nhan AND den_trong_ky) AS tong_don_nhan_den,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'da_len_xe') AS so_don_sap_den,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'cho_lay') AS so_don_cho_lay,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'cho_lay' AND NOT da_thong_bao_nguoi_nhan) AS so_don_chua_bao_nguoi_nhan,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'cho_lay' AND co_canh_bao_cho_lau) AS so_don_canh_bao_7_ngay,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'qua_han_luu_kho') AS so_don_ton_kho,
                    count(*) FILTER (WHERE la_nhan AND trang_thai = 'da_giao' AND giao_trong_ky) AS so_don_da_giao,
                    COALESCE(sum(gia_cuoc) FILTER (WHERE la_nhan AND phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'
                                                   AND da_thu_tien AND thu_trong_ky), 0) AS tien_cod_da_thu
                FROM d
                """,
                {"vp": diem_id, "tu": tu_ngay, "den": den_ngay},
            )
            res = _thanh_dict(cur, cur.fetchone()) or {}
            res = {k: (int(v) if v is not None else 0) for k, v in res.items()}
            res["tong_doanh_thu"] = res.get("tien_cuoc_gui_tra_truoc", 0) + res.get("tien_cod_da_thu", 0)
            res["tu_ngay"] = tu_ngay.isoformat()
            res["den_ngay"] = den_ngay.isoformat()
            return res
    finally:
        release_connection(conn)


def thong_ke_hang_theo_ngay(diem_id: str | None, so_ngay: int) -> list[dict]:
    """Số đơn tiếp nhận (văn phòng gửi) và đơn giao xong (văn phòng nhận) theo từng ngày giờ Việt Nam."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                WITH homnay AS (SELECT (now() AT TIME ZONE '{MUI_GIO_VN}')::date AS d),
                ngay AS (
                    SELECT generate_series(homnay.d - (%(so_ngay)s - 1), homnay.d, interval '1 day')::date AS d
                    FROM homnay
                )
                SELECT ngay.d AS ngay,
                       (SELECT count(*) FROM don_hang x
                        WHERE (x.ngay_tao AT TIME ZONE '{MUI_GIO_VN}')::date = ngay.d
                          AND (%(vp)s::uuid IS NULL OR x.diem_gui_id = %(vp)s::uuid)) AS tiep_nhan,
                       (SELECT count(*) FROM don_hang x
                        WHERE x.trang_thai = 'da_giao'
                          AND (x.ngay_giao AT TIME ZONE '{MUI_GIO_VN}')::date = ngay.d
                          AND (%(vp)s::uuid IS NULL OR x.diem_nhan_id = %(vp)s::uuid)) AS da_giao
                FROM ngay ORDER BY ngay.d
                """,
                {"so_ngay": so_ngay, "vp": diem_id},
            )
            return _thanh_danh_sach_dict(cur, cur.fetchall())
    finally:
        release_connection(conn)


def doi_soat_tien_theo_nhan_vien(diem_id: str | None, tu_ngay: date, den_ngay: date) -> list[dict]:
    """Tiền mặt từng nhân viên đã thu trong khoảng ngày: cước trả trước thu ở
    văn phòng gửi, cước COD thu ở văn phòng nhận (theo nhan_vien_thu_id, thoi_gian_thu)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT d.nhan_vien_thu_id AS nhan_vien_id,
                       nd.ho_ten,
                       count(*) FILTER (WHERE d.phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc') AS so_don_tra_truoc,
                       COALESCE(sum(d.gia_cuoc) FILTER (WHERE d.phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc'), 0) AS tien_tra_truoc,
                       count(*) FILTER (WHERE d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra') AS so_don_cod,
                       COALESCE(sum(d.gia_cuoc) FILTER (WHERE d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'), 0) AS tien_cod
                FROM don_hang d
                LEFT JOIN nguoi_dung nd ON nd.id = d.nhan_vien_thu_id
                WHERE d.da_thu_tien
                  AND d.nhan_vien_thu_id IS NOT NULL
                  AND (d.thoi_gian_thu AT TIME ZONE '{MUI_GIO_VN}')::date BETWEEN %(tu)s AND %(den)s
                  AND (
                      %(vp)s::uuid IS NULL
                      OR (d.phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc' AND d.diem_gui_id = %(vp)s::uuid)
                      OR (d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra' AND d.diem_nhan_id = %(vp)s::uuid)
                  )
                GROUP BY d.nhan_vien_thu_id, nd.ho_ten
                ORDER BY nd.ho_ten
                """,
                {"vp": diem_id, "tu": tu_ngay, "den": den_ngay},
            )
            rows = _thanh_danh_sach_dict(cur, cur.fetchall())
            for r in rows:
                for k in ("so_don_tra_truoc", "tien_tra_truoc", "so_don_cod", "tien_cod"):
                    r[k] = int(r[k] or 0)
                r["tong_tien"] = r["tien_tra_truoc"] + r["tien_cod"]
                r["nhan_vien_id"] = str(r["nhan_vien_id"])
            return rows
    finally:
        release_connection(conn)
