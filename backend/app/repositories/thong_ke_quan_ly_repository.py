"""Raw SQL cho trang Thống kê của quản lý (UC-39, NGHIEP_VU.md mục 8.7 điểm 4) — toàn hệ thống, lọc được theo 1 tuyến.

Mọi hàm nhận `p = {"tu": date, "den": date, "tuyen": str | None}`: khoảng NGÀY theo giờ Việt Nam, gồm cả hai đầu (DB chạy UTC nên
so trên mốc 0h giờ VN chứ không cắt `::date` của cột UTC). Không cache — tính động mỗi lần (UC-39 bước 3).

Quy ước tính tiền (khớp trang gửi hàng — NGHIEP_VU_GUI_HANG.md mục 6 — và trang quầy vé):
- Tiền VÉ ghi vào ngày THU tiền (`gio_thanh_toan`; dữ liệu cũ thiếu mốc này mà vé đã trả tiền thì lấy ngày tạo vé).
- Tiền HOÀN vé ghi vào ngày hệ thống XÁC ĐỊNH phải hoàn (`lich_su_hoan_tien.thoi_gian_xac_dinh`) — kể cả khoản đang chờ kế toán chuyển,
  vì từ lúc đó tiền đã thuộc về khách.
- Cước HÀNG: trả trước ghi ở văn phòng gửi, COD ghi ở văn phòng nhận, theo `thoi_gian_thu`; hoàn cước khi hủy đơn ghi theo `thoi_gian_huy`.
- Doanh thu thuần = tiền vé + cước hàng − tiền hoàn (vé + hàng).
Số liệu CHUYẾN (lấp đầy, đúng giờ, hủy/sự cố) tính theo ngày KHỞI HÀNH của chuyến.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.db import get_connection, release_connection
from app.repositories import bien_che_sql

VN = "Asia/Ho_Chi_Minh"

# Vé "đã bán" (có tiền, chưa bị hủy): đã thanh toán / đã lên / đã xuống xe, hoặc không đến nhưng đã trả tiền trước.
VE_DA_BAN = (
    "(v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe') "
    "OR (v.trang_thai = 'khong_den' AND v.gio_thanh_toan IS NOT NULL))"
)
CHUYEN_DA_CHAY = "c.trang_thai IN ('hoan_thanh', 'dang_chay', 'gap_su_co')"
TONG_GHE = "CASE WHEN jsonb_typeof(lx.so_do_ghe) = 'array' THEN jsonb_array_length(lx.so_do_ghe) ELSE 0 END"
PHUT_TRE_TOI_DA = 15  # xuất phát muộn hơn giờ khởi hành không quá 15 phút vẫn tính là đúng giờ

# don_vi → (đơn vị date_trunc, bước mốc, định dạng nhãn mốc) — giống thống kê gửi hàng để nhãn trục khớp nhau
DON_VI_CHUOI = {
    "gio": ("hour", "1 hour", "%Y-%m-%dT%H:00"),
    "ngay": ("day", "1 day", "%Y-%m-%d"),
    "thang": ("month", "1 month", "%Y-%m-01"),
}


def _khoang(cot: str) -> str:
    """Điều kiện `cot` (timestamptz) nằm trong [0h ngày tu, 0h ngày sau den) giờ Việt Nam."""
    return (f"({cot} >= %(tu)s::date::timestamp AT TIME ZONE '{VN}' "
            f"AND {cot} < (%(den)s::date + 1)::timestamp AT TIME ZONE '{VN}')")


def _tuyen(cot: str) -> str:
    return f"(%(tuyen)s::uuid IS NULL OR {cot} = %(tuyen)s::uuid)"


def _chuan(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, UUID):
        return str(v)
    return v


def _rows(cur) -> list[dict]:
    cot = [d[0] for d in cur.description]
    return [{k: _chuan(v) for k, v in zip(cot, r)} for r in cur.fetchall()]


def _mot(cur) -> dict:
    ds = _rows(cur)
    return ds[0] if ds else {}


def _chay(ham):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            return ham(cur)
    finally:
        release_connection(conn)


def _moc_sql(don_vi: str) -> tuple[str, str]:
    """CTE `moc(m)`: đủ mọi mốc giờ/ngày/tháng trong kỳ (cả mốc không có dữ liệu) + định dạng nhãn."""
    trunc, buoc, dinh_dang = DON_VI_CHUOI[don_vi]
    sql = (f"moc AS (SELECT generate_series(date_trunc('{trunc}', %(tu)s::date::timestamp), "
           f"date_trunc('{trunc}', (%(den)s::date + 1)::timestamp - interval '1 second'), interval '{buoc}') AS m)")
    return sql, dinh_dang


def _gan_nhan_moc(rows: list[dict], dinh_dang: str) -> list[dict]:
    for r in rows:
        m = r["moc"]
        r["moc"] = m.strftime(dinh_dang) if isinstance(m, (datetime, date)) else str(m)
    return rows


# =====================================================================================================================
# 1. Tiền
# =====================================================================================================================
# Mỗi dòng = 1 khoản tiền vào (ve / hang) hoặc ra (hoan_ve / hoan_hang, số dương) với thời điểm, tuyến, kênh, phương thức, điểm.
_CTE_TIEN = f"""
tien AS (
    SELECT 've'::text AS loai, COALESCE(v.gio_thanh_toan, v.ngay_tao) AS t, v.gia::bigint AS so_tien, c.tuyen_id,
           COALESCE(v.kenh_ban, 'truc_tuyen') AS kenh, COALESCE(v.phuong_thuc_thanh_toan, 'khac') AS pt, v.diem_don_id AS diem
    FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
    WHERE v.gio_thanh_toan IS NOT NULL OR v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe')
    UNION ALL
    SELECT 'hoan_ve', h.thoi_gian_xac_dinh, h.so_tien::bigint, c.tuyen_id,
           COALESCE(v.kenh_ban, 'truc_tuyen'), COALESCE(v.phuong_thuc_thanh_toan, 'khac'), v.diem_don_id
    FROM lich_su_hoan_tien h JOIN ve v ON v.id = h.ve_id JOIN chuyen_xe c ON c.id = v.chuyen_id
    UNION ALL
    SELECT 'hang', d.thoi_gian_thu, d.gia_cuoc::bigint, d.tuyen_id, 'hang', d.phuong_thuc_thanh_toan,
           CASE WHEN d.phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc' THEN d.diem_gui_id ELSE d.diem_nhan_id END
    FROM don_hang d WHERE d.da_thu_tien AND d.thoi_gian_thu IS NOT NULL
    UNION ALL
    SELECT 'hoan_hang', d.thoi_gian_huy, d.so_tien_hoan::bigint, d.tuyen_id, 'hang', d.phuong_thuc_thanh_toan, d.diem_gui_id
    FROM don_hang d WHERE d.so_tien_hoan IS NOT NULL AND d.thoi_gian_huy IS NOT NULL
),
tk AS (SELECT * FROM tien WHERE {_khoang('t')} AND {_tuyen('tuyen_id')})
"""

_COT_TIEN = """
    COALESCE(sum(so_tien) FILTER (WHERE loai = 've'), 0)::bigint AS tien_ve,
    COALESCE(sum(so_tien) FILTER (WHERE loai = 'hang'), 0)::bigint AS tien_hang,
    COALESCE(sum(so_tien) FILTER (WHERE loai = 'hoan_ve'), 0)::bigint AS hoan_ve,
    COALESCE(sum(so_tien) FILTER (WHERE loai = 'hoan_hang'), 0)::bigint AS hoan_hang
"""


def _them_thuan(r: dict) -> dict:
    r["tien_hoan"] = r["hoan_ve"] + r["hoan_hang"]
    r["thuan"] = r["tien_ve"] + r["tien_hang"] - r["tien_hoan"]
    return r


def tong_tien(p: dict) -> dict:
    def ham(cur):
        cur.execute(f"WITH {_CTE_TIEN} SELECT {_COT_TIEN}, count(*) FILTER (WHERE loai = 've') AS so_ve_thu, "
                    f"count(*) FILTER (WHERE loai = 'hang') AS so_don_thu FROM tk", p)
        return _them_thuan(_mot(cur))
    return _chay(ham)


def chuoi_tien(p: dict, don_vi: str) -> list[dict]:
    moc, dinh_dang = _moc_sql(don_vi)
    trunc = DON_VI_CHUOI[don_vi][0]

    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_TIEN}, {moc}
                SELECT moc.m AS moc, {_COT_TIEN.replace('so_tien', 'tk.so_tien').replace('loai', 'tk.loai')}
                FROM moc LEFT JOIN tk ON date_trunc('{trunc}', tk.t AT TIME ZONE '{VN}') = moc.m
                GROUP BY moc.m ORDER BY moc.m""",
            p,
        )
        return [_them_thuan(r) for r in _gan_nhan_moc(_rows(cur), dinh_dang)]
    return _chay(ham)


def tien_theo_nhom(p: dict) -> dict:
    """Tiền chia theo tuyến, theo điểm (vé: điểm đón; hàng: văn phòng thu), theo kênh bán vé, theo phương thức thanh toán."""
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_TIEN}
                SELECT t.id AS tuyen_id, t.ma, t.ten, {_COT_TIEN.replace('so_tien', 'tk.so_tien').replace('loai', 'tk.loai')},
                       count(*) FILTER (WHERE tk.loai = 've') AS so_ve
                FROM tk JOIN tuyen t ON t.id = tk.tuyen_id GROUP BY t.id, t.ma, t.ten""",
            p,
        )
        theo_tuyen = [_them_thuan(r) for r in _rows(cur)]
        cur.execute(
            f"""WITH {_CTE_TIEN}
                SELECT dd.id AS diem_id, dd.ma, dd.ten, dd.loai AS loai_diem,
                       {_COT_TIEN.replace('so_tien', 'tk.so_tien').replace('loai', 'tk.loai')}
                FROM tk JOIN diem_don_tra dd ON dd.id = tk.diem GROUP BY dd.id, dd.ma, dd.ten, dd.loai""",
            p,
        )
        theo_diem = [_them_thuan(r) for r in _rows(cur)]
        cur.execute(
            f"""WITH {_CTE_TIEN}
                SELECT kenh, pt, loai, count(*) AS so_khoan, COALESCE(sum(so_tien), 0)::bigint AS so_tien
                FROM tk WHERE loai IN ('ve', 'hang') GROUP BY kenh, pt, loai""",
            p,
        )
        return {"theo_tuyen": theo_tuyen, "theo_diem": theo_diem, "theo_kenh_pt": _rows(cur)}
    return _chay(ham)


# =====================================================================================================================
# 2. Chuyến (theo ngày khởi hành)
# =====================================================================================================================
_CTE_CHUYEN = f"""
ck AS (
    SELECT c.id, c.ma, c.tuyen_id, c.chieu, c.trang_thai, c.dang_hoan, c.loai_su_co, c.ly_do_su_co, c.gio_khoi_hanh,
           c.gio_xac_nhan_xuat_phat, c.loai_xe_id, COALESCE(c.xe_thuc_te_id, c.xe_id) AS xe_chay_id,
           {CHUYEN_DA_CHAY} AS da_chay,
           {TONG_GHE} AS tong_ghe,
           (SELECT count(DISTINCT v.so_ghe) FROM ve v WHERE v.chuyen_id = c.id AND {VE_DA_BAN}) AS ghe_ban,
           (SELECT count(*) FROM ve v WHERE v.chuyen_id = c.id AND {VE_DA_BAN}) AS so_ve,
           (SELECT COALESCE(sum(v.gia), 0) FROM ve v WHERE v.chuyen_id = c.id AND {VE_DA_BAN})::bigint AS doanh_thu_ve,
           (SELECT count(*) FROM don_hang d WHERE d.chuyen_id = c.id AND d.trang_thai <> 'da_huy') AS so_don_hang,
           GREATEST(0, EXTRACT(EPOCH FROM (c.gio_xac_nhan_xuat_phat - c.gio_khoi_hanh)) / 60) AS phut_tre
    FROM chuyen_xe c JOIN loai_xe lx ON lx.id = c.loai_xe_id
    WHERE {_khoang('c.gio_khoi_hanh')} AND {_tuyen('c.tuyen_id')}
)
"""

_COT_CHUYEN = f"""
    count(*) AS tong_chuyen,
    count(*) FILTER (WHERE da_chay) AS da_chay,
    count(*) FILTER (WHERE trang_thai = 'hoan_thanh') AS hoan_thanh,
    count(*) FILTER (WHERE trang_thai = 'dang_chay') AS dang_chay,
    count(*) FILTER (WHERE trang_thai = 'gap_su_co') AS gap_su_co,
    count(*) FILTER (WHERE trang_thai = 'da_huy') AS da_huy,
    count(*) FILTER (WHERE trang_thai = 'chua_khoi_hanh') AS chua_khoi_hanh,
    count(*) FILTER (WHERE trang_thai = 'chua_khoi_hanh' AND dang_hoan) AS dang_hoan,
    count(*) FILTER (WHERE loai_su_co IS NOT NULL) AS co_su_co,
    count(*) FILTER (WHERE loai_su_co = 'loi_nha_xe') AS su_co_nha_xe,
    count(*) FILTER (WHERE loai_su_co = 'loi_khach_quan') AS su_co_khach_quan,
    COALESCE(sum(ghe_ban) FILTER (WHERE da_chay), 0)::bigint AS ghe_ban,
    COALESCE(sum(tong_ghe) FILTER (WHERE da_chay), 0)::bigint AS tong_ghe,
    COALESCE(sum(so_ve) FILTER (WHERE da_chay), 0)::bigint AS so_ve,
    COALESCE(sum(doanh_thu_ve) FILTER (WHERE da_chay), 0)::bigint AS doanh_thu_ve,
    COALESCE(sum(so_don_hang) FILTER (WHERE da_chay), 0)::bigint AS so_don_hang,
    count(*) FILTER (WHERE da_chay AND gio_xac_nhan_xuat_phat IS NOT NULL) AS co_gio_xuat_phat,
    count(*) FILTER (WHERE da_chay AND gio_xac_nhan_xuat_phat IS NOT NULL AND phut_tre <= {PHUT_TRE_TOI_DA}) AS dung_gio,
    COALESCE(round(avg(phut_tre) FILTER (WHERE da_chay AND gio_xac_nhan_xuat_phat IS NOT NULL)), 0)::int AS tre_tb_phut
"""


def tong_chuyen(p: dict) -> dict:
    def ham(cur):
        cur.execute(f"WITH {_CTE_CHUYEN} SELECT {_COT_CHUYEN} FROM ck", p)
        return _mot(cur)
    return _chay(ham)


def chuyen_theo_nhom(p: dict) -> dict:
    """Chỉ số chuyến chia theo tuyến và theo loại xe."""
    def ham(cur):
        cur.execute(f"""WITH {_CTE_CHUYEN}
                        SELECT t.id AS tuyen_id, t.ma, t.ten, {_COT_CHUYEN}
                        FROM ck JOIN tuyen t ON t.id = ck.tuyen_id GROUP BY t.id, t.ma, t.ten ORDER BY t.ma""", p)
        theo_tuyen = _rows(cur)
        cur.execute(f"""WITH {_CTE_CHUYEN}
                        SELECT lx.id AS loai_xe_id, lx.ma, lx.ten, {_COT_CHUYEN}
                        FROM ck JOIN loai_xe lx ON lx.id = ck.loai_xe_id GROUP BY lx.id, lx.ma, lx.ten ORDER BY lx.ma""", p)
        return {"theo_tuyen": theo_tuyen, "theo_loai_xe": _rows(cur)}
    return _chay(ham)


def chuoi_chuyen(p: dict, don_vi: str) -> list[dict]:
    moc, dinh_dang = _moc_sql(don_vi)
    trunc = DON_VI_CHUOI[don_vi][0]

    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_CHUYEN}, {moc}
                SELECT moc.m AS moc,
                       count(ck.id) FILTER (WHERE ck.da_chay) AS da_chay,
                       count(ck.id) FILTER (WHERE ck.da_chay AND ck.loai_su_co IS NULL) AS chay_binh_thuong,
                       count(ck.id) FILTER (WHERE ck.da_chay AND ck.loai_su_co IS NOT NULL) AS chay_co_su_co,
                       count(ck.id) FILTER (WHERE ck.trang_thai = 'da_huy') AS da_huy,
                       count(ck.id) FILTER (WHERE ck.loai_su_co IS NOT NULL) AS co_su_co,
                       count(ck.id) FILTER (WHERE ck.trang_thai = 'chua_khoi_hanh') AS chua_khoi_hanh,
                       COALESCE(sum(ck.ghe_ban) FILTER (WHERE ck.da_chay), 0)::bigint AS ghe_ban,
                       COALESCE(sum(ck.tong_ghe) FILTER (WHERE ck.da_chay), 0)::bigint AS tong_ghe
                FROM moc LEFT JOIN ck ON date_trunc('{trunc}', ck.gio_khoi_hanh AT TIME ZONE '{VN}') = moc.m
                GROUP BY moc.m ORDER BY moc.m""",
            p,
        )
        return _gan_nhan_moc(_rows(cur), dinh_dang)
    return _chay(ham)


def nhiet_thu_gio(p: dict) -> list[dict]:
    """Lấp đầy của chuyến đã chạy theo thứ trong tuần (1 = thứ Hai … 7 = Chủ nhật) × giờ khởi hành (giờ VN)."""
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_CHUYEN}
                SELECT EXTRACT(ISODOW FROM gio_khoi_hanh AT TIME ZONE '{VN}')::int AS thu,
                       EXTRACT(HOUR FROM gio_khoi_hanh AT TIME ZONE '{VN}')::int AS gio,
                       count(*) AS so_chuyen, COALESCE(sum(ghe_ban), 0)::bigint AS ghe_ban, COALESCE(sum(tong_ghe), 0)::bigint AS tong_ghe
                FROM ck WHERE da_chay GROUP BY 1, 2 ORDER BY 1, 2""",
            p,
        )
        return _rows(cur)
    return _chay(ham)


def chuyen_bat_thuong(p: dict, gioi_han: int = 100) -> list[dict]:
    """Chuyến bị hủy, gặp sự cố (kể cả đã xử lý xong) hoặc đang hoãn vì quá giờ chưa có xe — mới nhất trước."""
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_CHUYEN}
                SELECT ck.id, ck.ma, ck.chieu, ck.gio_khoi_hanh, ck.trang_thai, ck.dang_hoan, ck.loai_su_co, ck.ly_do_su_co,
                       t.ma AS ma_tuyen, t.ten AS ten_tuyen, x.bien_so,
                       (SELECT count(*) FROM ve v WHERE v.chuyen_id = ck.id AND v.trang_thai <> 'het_han') AS so_ve
                FROM ck JOIN tuyen t ON t.id = ck.tuyen_id LEFT JOIN xe x ON x.id = ck.xe_chay_id
                WHERE ck.trang_thai = 'da_huy' OR ck.loai_su_co IS NOT NULL OR (ck.trang_thai = 'chua_khoi_hanh' AND ck.dang_hoan)
                ORDER BY ck.gio_khoi_hanh DESC LIMIT %(gioi_han)s""",
            {**p, "gioi_han": gioi_han},
        )
        return _rows(cur)
    return _chay(ham)


# =====================================================================================================================
# 3. Vé & khách hàng (theo ngày tạo vé — lúc khách đặt)
# =====================================================================================================================
_CTE_VE = f"""
vk AS (
    SELECT v.*, c.gio_khoi_hanh, c.tuyen_id, {VE_DA_BAN} AS da_ban
    FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id
    WHERE {_khoang('v.ngay_tao')} AND {_tuyen('c.tuyen_id')}
)
"""


def tong_ve(p: dict) -> dict:
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_VE}
                SELECT count(*) AS tong_ve,
                       count(DISTINCT ma_dat_cho) AS so_luot_dat,
                       count(*) FILTER (WHERE da_ban) AS da_ban,
                       COALESCE(sum(gia) FILTER (WHERE da_ban), 0)::bigint AS gia_tri_da_ban,
                       count(*) FILTER (WHERE trang_thai = 'giu_cho') AS giu_cho,
                       count(*) FILTER (WHERE trang_thai = 'da_thanh_toan') AS da_thanh_toan,
                       count(*) FILTER (WHERE trang_thai = 'da_len_xe') AS da_len_xe,
                       count(*) FILTER (WHERE trang_thai = 'da_xuong_xe') AS da_xuong_xe,
                       count(*) FILTER (WHERE trang_thai = 'khong_den') AS khong_den,
                       count(*) FILTER (WHERE trang_thai = 'da_huy') AS da_huy,
                       count(*) FILTER (WHERE trang_thai = 'het_han') AS het_han,
                       count(*) FILTER (WHERE da_ban AND kenh_ban IS NULL) AS kenh_truc_tuyen,
                       count(*) FILTER (WHERE da_ban AND kenh_ban = 'tai_quay') AS kenh_tai_quay,
                       count(*) FILTER (WHERE da_ban AND kenh_ban = 'hotline') AS kenh_hotline,
                       count(*) FILTER (WHERE da_ban AND khach_hang_id IS NOT NULL) AS khach_tai_khoan,
                       count(*) FILTER (WHERE da_ban AND khach_hang_id IS NULL) AS khach_vang_lai,
                       count(*) FILTER (WHERE da_ban AND loai_hinh_thanh_toan = 'thanh_toan_ngay') AS tra_ngay,
                       count(*) FILTER (WHERE da_ban AND loai_hinh_thanh_toan = 'thanh_toan_tai_quay') AS tra_tai_quay,
                       count(*) FILTER (WHERE da_ban AND la_ve_dat_coc) AS ve_dat_coc,
                       count(*) FILTER (WHERE da_ban AND gio_khoi_hanh - ngay_tao < interval '1 day') AS truoc_duoi_1_ngay,
                       count(*) FILTER (WHERE da_ban AND gio_khoi_hanh - ngay_tao >= interval '1 day' AND gio_khoi_hanh - ngay_tao < interval '3 days') AS truoc_1_3_ngay,
                       count(*) FILTER (WHERE da_ban AND gio_khoi_hanh - ngay_tao >= interval '3 days' AND gio_khoi_hanh - ngay_tao < interval '7 days') AS truoc_3_7_ngay,
                       count(*) FILTER (WHERE da_ban AND gio_khoi_hanh - ngay_tao >= interval '7 days') AS truoc_tren_7_ngay,
                       count(DISTINCT COALESCE(khach_hang_id::text, sdt_khach_vang_lai)) FILTER (WHERE da_ban) AS so_khach
                FROM vk""",
            p,
        )
        kq = _mot(cur)
        cur.execute(f"SELECT count(*) AS n FROM nguoi_dung WHERE vai_tro = 'khach_hang' AND {_khoang('ngay_tao')}", p)
        kq["khach_moi"] = _mot(cur)["n"]
        return kq
    return _chay(ham)


def chuoi_ve(p: dict, don_vi: str) -> list[dict]:
    moc, dinh_dang = _moc_sql(don_vi)
    trunc = DON_VI_CHUOI[don_vi][0]

    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_VE}, {moc}
                SELECT moc.m AS moc,
                       count(vk.id) FILTER (WHERE vk.da_ban) AS da_ban,
                       count(vk.id) FILTER (WHERE vk.trang_thai = 'giu_cho') AS giu_cho,
                       count(vk.id) FILTER (WHERE vk.trang_thai IN ('da_huy', 'het_han')) AS huy_het_han,
                       count(vk.id) FILTER (WHERE vk.trang_thai = 'khong_den') AS khong_den
                FROM moc LEFT JOIN vk ON date_trunc('{trunc}', vk.ngay_tao AT TIME ZONE '{VN}') = moc.m
                GROUP BY moc.m ORDER BY moc.m""",
            p,
        )
        return _gan_nhan_moc(_rows(cur), dinh_dang)
    return _chay(ham)


def cap_diem_dong_nhat(p: dict, gioi_han: int = 10) -> list[dict]:
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_VE}
                SELECT don.ten AS diem_don, tra.ten AS diem_tra, count(*) AS so_ve, COALESCE(sum(vk.gia), 0)::bigint AS gia_tri
                FROM vk JOIN diem_don_tra don ON don.id = vk.diem_don_id JOIN diem_don_tra tra ON tra.id = vk.diem_tra_id
                WHERE vk.da_ban GROUP BY don.ten, tra.ten ORDER BY count(*) DESC, sum(vk.gia) DESC LIMIT %(gioi_han)s""",
            {**p, "gioi_han": gioi_han},
        )
        return _rows(cur)
    return _chay(ham)


# =====================================================================================================================
# 4. Gửi hàng
# =====================================================================================================================
def tong_hang(p: dict) -> dict:
    """Luồng (đơn tạo / giao / hủy trong kỳ) + ảnh chụp hiện tại (hàng đang nằm ở đâu, COD chưa thu)."""
    def ham(cur):
        cur.execute(
            f"""SELECT
                    count(*) FILTER (WHERE {_khoang('d.ngay_tao')}) AS don_tao,
                    count(*) FILTER (WHERE {_khoang('d.ngay_tao')} AND d.trang_thai <> 'da_huy') AS don_tao_hieu_luc,
                    COALESCE(sum(d.gia_cuoc) FILTER (WHERE {_khoang('d.ngay_tao')} AND d.trang_thai <> 'da_huy'), 0)::bigint AS cuoc_don_tao,
                    COALESCE(sum(d.can_nang_kg) FILTER (WHERE {_khoang('d.ngay_tao')} AND d.trang_thai <> 'da_huy'), 0) AS tong_kg,
                    count(*) FILTER (WHERE {_khoang('d.ngay_tao')} AND d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra') AS don_cod,
                    count(*) FILTER (WHERE d.trang_thai = 'da_giao' AND {_khoang('d.ngay_giao')}) AS da_giao,
                    COALESCE(round(avg(EXTRACT(EPOCH FROM (d.ngay_giao - d.ngay_tao)) / 3600)
                             FILTER (WHERE d.trang_thai = 'da_giao' AND {_khoang('d.ngay_giao')})), 0)::int AS gio_giao_tb,
                    count(*) FILTER (WHERE d.trang_thai = 'da_huy' AND {_khoang('d.thoi_gian_huy')}) AS da_huy,
                    count(*) FILTER (WHERE d.trang_thai = 'cho_van_chuyen') AS hien_cho_xep_xe,
                    count(*) FILTER (WHERE d.trang_thai = 'da_len_xe') AS hien_tren_xe,
                    count(*) FILTER (WHERE d.trang_thai = 'cho_lay') AS hien_cho_lay,
                    count(*) FILTER (WHERE d.trang_thai = 'cho_lay' AND d.co_canh_bao_cho_lau) AS hien_cho_lau,
                    count(*) FILTER (WHERE d.trang_thai = 'qua_han_luu_kho') AS hien_qua_han,
                    count(*) FILTER (WHERE d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra' AND NOT d.da_thu_tien
                                     AND d.trang_thai <> 'da_huy') AS cod_chua_thu,
                    COALESCE(sum(d.gia_cuoc) FILTER (WHERE d.phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra' AND NOT d.da_thu_tien
                                     AND d.trang_thai <> 'da_huy'), 0)::bigint AS tien_cod_chua_thu
                FROM don_hang d WHERE {_tuyen('d.tuyen_id')}""",
            p,
        )
        kq = _mot(cur)
        cur.execute(
            f"""SELECT count(*) AS n FROM bao_cao_su_co_hang b JOIN don_hang d ON d.id = b.don_hang_id
                WHERE {_khoang('b.ngay_tao')} AND {_tuyen('d.tuyen_id')}""",
            p,
        )
        kq["su_co_hang"] = _mot(cur)["n"]
        return kq
    return _chay(ham)


def hang_theo_nhom(p: dict) -> dict:
    """Đơn tạo trong kỳ chia theo trạng thái hiện tại, văn phòng gửi, văn phòng nhận và loại hàng; sự cố hàng theo loại."""
    def ham(cur):
        loc = f"{_khoang('d.ngay_tao')} AND {_tuyen('d.tuyen_id')}"
        cur.execute(f"SELECT d.trang_thai, count(*) AS so_don FROM don_hang d WHERE {loc} GROUP BY 1", p)
        theo_trang_thai = _rows(cur)
        cur.execute(
            f"""SELECT dd.ten, dd.ma, count(*) AS so_don,
                       COALESCE(sum(d.gia_cuoc) FILTER (WHERE d.trang_thai <> 'da_huy'), 0)::bigint AS cuoc
                FROM don_hang d JOIN diem_don_tra dd ON dd.id = d.diem_gui_id WHERE {loc}
                GROUP BY dd.ten, dd.ma ORDER BY count(*) DESC""",
            p,
        )
        theo_vp_gui = _rows(cur)
        cur.execute(
            f"""SELECT dd.ten, dd.ma, count(*) AS so_don
                FROM don_hang d JOIN diem_don_tra dd ON dd.id = d.diem_nhan_id WHERE {loc}
                GROUP BY dd.ten, dd.ma ORDER BY count(*) DESC""",
            p,
        )
        theo_vp_nhan = _rows(cur)
        cur.execute(
            f"""SELECT COALESCE(lh.ten, 'Khác') AS ten, count(*) AS so_don
                FROM don_hang d LEFT JOIN loai_hang lh ON lh.id = d.loai_hang_id WHERE {loc}
                GROUP BY 1 ORDER BY count(*) DESC""",
            p,
        )
        theo_loai_hang = _rows(cur)
        cur.execute(
            f"""SELECT b.loai, count(*) AS so_vu FROM bao_cao_su_co_hang b JOIN don_hang d ON d.id = b.don_hang_id
                WHERE {_khoang('b.ngay_tao')} AND {_tuyen('d.tuyen_id')} GROUP BY 1 ORDER BY 2 DESC""",
            p,
        )
        return {"theo_trang_thai": theo_trang_thai, "theo_vp_gui": theo_vp_gui, "theo_vp_nhan": theo_vp_nhan,
                "theo_loai_hang": theo_loai_hang, "su_co_theo_loai": _rows(cur)}
    return _chay(ham)


def chuoi_hang(p: dict, don_vi: str) -> list[dict]:
    moc, dinh_dang = _moc_sql(don_vi)
    trunc = DON_VI_CHUOI[don_vi][0]

    def ham(cur):
        cur.execute(
            f"""WITH {moc},
                s AS (
                    SELECT d.ngay_tao AS t, 'tao' AS loai FROM don_hang d WHERE {_khoang('d.ngay_tao')} AND {_tuyen('d.tuyen_id')}
                    UNION ALL
                    SELECT d.ngay_giao, 'giao' FROM don_hang d
                    WHERE d.trang_thai = 'da_giao' AND {_khoang('d.ngay_giao')} AND {_tuyen('d.tuyen_id')}
                    UNION ALL
                    SELECT d.thoi_gian_huy, 'huy' FROM don_hang d
                    WHERE d.trang_thai = 'da_huy' AND {_khoang('d.thoi_gian_huy')} AND {_tuyen('d.tuyen_id')}
                )
                SELECT moc.m AS moc, count(s.loai) FILTER (WHERE s.loai = 'tao') AS tao,
                       count(s.loai) FILTER (WHERE s.loai = 'giao') AS giao, count(s.loai) FILTER (WHERE s.loai = 'huy') AS huy
                FROM moc LEFT JOIN s ON date_trunc('{trunc}', s.t AT TIME ZONE '{VN}') = moc.m
                GROUP BY moc.m ORDER BY moc.m""",
            p,
        )
        return _gan_nhan_moc(_rows(cur), dinh_dang)
    return _chay(ham)


# =====================================================================================================================
# 5. Hoàn tiền
# =====================================================================================================================
_TU_HOAN = "FROM lich_su_hoan_tien h JOIN ve v ON v.id = h.ve_id JOIN chuyen_xe c ON c.id = v.chuyen_id"


def tong_hoan(p: dict) -> dict:
    def ham(cur):
        cur.execute(
            f"""SELECT
                    count(*) FILTER (WHERE {_khoang('h.thoi_gian_xac_dinh')}) AS phat_sinh,
                    COALESCE(sum(h.so_tien) FILTER (WHERE {_khoang('h.thoi_gian_xac_dinh')}), 0)::bigint AS tien_phat_sinh,
                    count(*) FILTER (WHERE h.thoi_gian_hoan_xong IS NOT NULL AND {_khoang('h.thoi_gian_hoan_xong')}) AS da_hoan,
                    COALESCE(sum(h.so_tien) FILTER (WHERE h.thoi_gian_hoan_xong IS NOT NULL AND {_khoang('h.thoi_gian_hoan_xong')}), 0)::bigint AS tien_da_hoan,
                    count(*) FILTER (WHERE h.trang_thai = 'da_hoan_tu_dong' AND h.thoi_gian_hoan_xong IS NOT NULL
                                     AND {_khoang('h.thoi_gian_hoan_xong')}) AS da_hoan_tu_dong,
                    COALESCE(round(avg(EXTRACT(EPOCH FROM (h.thoi_gian_hoan_xong - h.thoi_gian_xac_dinh)) / 3600)
                             FILTER (WHERE h.trang_thai = 'da_hoan_chuyen_khoan_thu_cong' AND h.thoi_gian_hoan_xong IS NOT NULL
                                     AND {_khoang('h.thoi_gian_hoan_xong')})), 0)::int AS gio_xu_ly_tb,
                    count(*) FILTER (WHERE h.trang_thai = 'cho_xu_ly') AS dang_cho,
                    COALESCE(sum(h.so_tien) FILTER (WHERE h.trang_thai = 'cho_xu_ly'), 0)::bigint AS tien_dang_cho,
                    min(h.thoi_gian_xac_dinh) FILTER (WHERE h.trang_thai = 'cho_xu_ly') AS cho_lau_nhat_tu
                {_TU_HOAN} WHERE {_tuyen('c.tuyen_id')}""",
            p,
        )
        kq = _mot(cur)
        cur.execute(
            f"""SELECT count(*) AS so_don, COALESCE(sum(d.so_tien_hoan), 0)::bigint AS so_tien FROM don_hang d
                WHERE d.so_tien_hoan IS NOT NULL AND {_khoang('d.thoi_gian_huy')} AND {_tuyen('d.tuyen_id')}""",
            p,
        )
        h = _mot(cur)
        kq["don_hang_hoan"], kq["tien_hoan_hang"] = h["so_don"], h["so_tien"]
        return kq
    return _chay(ham)


def hoan_theo_ly_do(p: dict) -> list[dict]:
    def ham(cur):
        cur.execute(
            f"""SELECT h.ly_do, count(*) AS so_luot, COALESCE(sum(h.so_tien), 0)::bigint AS so_tien,
                       count(*) FILTER (WHERE h.trang_thai = 'cho_xu_ly') AS dang_cho,
                       COALESCE(sum(h.so_tien) FILTER (WHERE h.trang_thai = 'cho_xu_ly'), 0)::bigint AS tien_dang_cho
                {_TU_HOAN} WHERE {_khoang('h.thoi_gian_xac_dinh')} AND {_tuyen('c.tuyen_id')}
                GROUP BY h.ly_do ORDER BY sum(h.so_tien) DESC""",
            p,
        )
        return _rows(cur)
    return _chay(ham)


def chuoi_hoan(p: dict, don_vi: str) -> list[dict]:
    moc, dinh_dang = _moc_sql(don_vi)
    trunc = DON_VI_CHUOI[don_vi][0]

    def ham(cur):
        cur.execute(
            f"""WITH {moc},
                s AS (
                    SELECT h.thoi_gian_xac_dinh AS t, h.so_tien, 'phat_sinh' AS loai {_TU_HOAN}
                    WHERE {_khoang('h.thoi_gian_xac_dinh')} AND {_tuyen('c.tuyen_id')}
                    UNION ALL
                    SELECT h.thoi_gian_hoan_xong, h.so_tien, 'da_hoan' {_TU_HOAN}
                    WHERE h.thoi_gian_hoan_xong IS NOT NULL AND {_khoang('h.thoi_gian_hoan_xong')} AND {_tuyen('c.tuyen_id')}
                )
                SELECT moc.m AS moc, COALESCE(sum(s.so_tien) FILTER (WHERE s.loai = 'phat_sinh'), 0)::bigint AS phat_sinh,
                       COALESCE(sum(s.so_tien) FILTER (WHERE s.loai = 'da_hoan'), 0)::bigint AS da_hoan
                FROM moc LEFT JOIN s ON date_trunc('{trunc}', s.t AT TIME ZONE '{VN}') = moc.m
                GROUP BY moc.m ORDER BY moc.m""",
            p,
        )
        return _gan_nhan_moc(_rows(cur), dinh_dang)
    return _chay(ham)


def hoan_dang_cho(p: dict, gioi_han: int = 100) -> list[dict]:
    """Các khoản hoàn CHƯA xử lý (không phụ thuộc kỳ), chờ lâu nhất trước."""
    def ham(cur):
        cur.execute(
            f"""SELECT h.id, h.ly_do, h.so_tien, h.thoi_gian_xac_dinh, (h.so_tai_khoan_nhan IS NOT NULL) AS co_tai_khoan_nhan,
                       v.ma_ve, COALESCE(kh.ho_ten, v.ten_khach_vang_lai, '') AS ten_khach,
                       COALESCE(kh.so_dien_thoai, v.sdt_khach_vang_lai, '') AS sdt_khach,
                       c.ma AS ma_chuyen, c.gio_khoi_hanh, t.ma AS ma_tuyen, t.ten AS ten_tuyen
                {_TU_HOAN} JOIN tuyen t ON t.id = c.tuyen_id LEFT JOIN nguoi_dung kh ON kh.id = v.khach_hang_id
                WHERE h.trang_thai = 'cho_xu_ly' AND {_tuyen('c.tuyen_id')}
                ORDER BY h.thoi_gian_xac_dinh LIMIT %(gioi_han)s""",
            {**p, "gioi_han": gioi_han},
        )
        return _rows(cur)
    return _chay(ham)


# =====================================================================================================================
# 6. Xe & nhân sự
# =====================================================================================================================
def tong_xe(p: dict) -> dict:
    """Ảnh chụp đội xe hiện tại. Lọc tuyến: xe cố định tuyến đó (xe dự phòng dùng chung nên tính cả khi lọc)."""
    def ham(cur):
        cur.execute(
            f"""WITH x AS (
                    SELECT x.*, {bien_che_sql.cot_hieu_luc('x')} FROM xe x
                    WHERE %(tuyen)s::uuid IS NULL OR x.tuyen_id = %(tuyen)s::uuid OR x.tuyen_id IS NULL
                )
                SELECT count(*) FILTER (WHERE trang_thai <> 'ngung_su_dung') AS tong_xe,
                       count(*) FILTER (WHERE trang_thai = 'hoat_dong') AS hoat_dong,
                       count(*) FILTER (WHERE trang_thai = 'bao_tri') AS bao_tri,
                       count(*) FILTER (WHERE trang_thai = 'ngung_su_dung') AS ngung_su_dung,
                       count(*) FILTER (WHERE trang_thai = 'hoat_dong' AND tuyen_id IS NULL) AS du_phong,
                       count(*) FILTER (WHERE trang_thai = 'hoat_dong' AND tuyen_id IS NOT NULL) AS co_dinh_tuyen,
                       count(*) FILTER (WHERE trang_thai = 'hoat_dong' AND tuyen_id IS NOT NULL
                                        AND (so_tai_xe_hieu_luc < 2 OR so_phu_xe_hieu_luc < 1)) AS thieu_nhan_su
                FROM x""",
            p,
        )
        return _mot(cur)
    return _chay(ham)


def hieu_suat_xe(p: dict) -> list[dict]:
    """Từng xe (trừ xe ngừng sử dụng không chạy chuyến nào trong kỳ): chuyến đã chạy trong kỳ theo xe THỰC TẾ chạy, lấp đầy, doanh thu vé."""
    def ham(cur):
        cur.execute(
            f"""WITH {_CTE_CHUYEN},
                theo_xe AS (
                    SELECT xe_chay_id, count(*) FILTER (WHERE da_chay) AS da_chay,
                           count(*) FILTER (WHERE trang_thai = 'hoan_thanh') AS hoan_thanh,
                           count(*) FILTER (WHERE loai_su_co IS NOT NULL) AS co_su_co,
                           count(*) FILTER (WHERE trang_thai = 'chua_khoi_hanh') AS sap_chay,
                           COALESCE(sum(ghe_ban) FILTER (WHERE da_chay), 0)::bigint AS ghe_ban,
                           COALESCE(sum(tong_ghe) FILTER (WHERE da_chay), 0)::bigint AS tong_ghe,
                           COALESCE(sum(doanh_thu_ve) FILTER (WHERE da_chay), 0)::bigint AS doanh_thu_ve
                    FROM ck WHERE xe_chay_id IS NOT NULL GROUP BY xe_chay_id
                )
                SELECT x.id, x.bien_so, x.trang_thai, lx.ma AS ma_loai_xe, lx.ten AS ten_loai_xe, t.ma AS ma_tuyen,
                       {bien_che_sql.cot_hieu_luc('x')},
                       COALESCE(tx.da_chay, 0) AS da_chay, COALESCE(tx.hoan_thanh, 0) AS hoan_thanh, COALESCE(tx.co_su_co, 0) AS co_su_co,
                       COALESCE(tx.sap_chay, 0) AS sap_chay, COALESCE(tx.ghe_ban, 0) AS ghe_ban, COALESCE(tx.tong_ghe, 0) AS tong_ghe,
                       COALESCE(tx.doanh_thu_ve, 0) AS doanh_thu_ve
                FROM xe x JOIN loai_xe lx ON lx.id = x.loai_xe_id LEFT JOIN tuyen t ON t.id = x.tuyen_id
                LEFT JOIN theo_xe tx ON tx.xe_chay_id = x.id
                WHERE (x.trang_thai <> 'ngung_su_dung' OR tx.xe_chay_id IS NOT NULL)
                  AND (%(tuyen)s::uuid IS NULL OR x.tuyen_id = %(tuyen)s::uuid OR tx.xe_chay_id IS NOT NULL)
                ORDER BY COALESCE(tx.da_chay, 0) DESC, x.bien_so""",
            p,
        )
        return _rows(cur)
    return _chay(ham)


def tong_nhan_su() -> dict:
    """Ảnh chụp nhân sự vận hành theo chức danh × trạng thái và giấy tờ hết / sắp hết hạn (30 ngày) của người đang làm."""
    def ham(cur):
        cur.execute("SELECT chuc_danh, trang_thai, count(*) AS so_nguoi FROM nhan_su_van_hanh GROUP BY 1, 2 ORDER BY 1, 2")
        theo_chuc_danh = _rows(cur)
        cur.execute(
            f"""SELECT g.loai, g.so_giay_to, g.ngay_het_han, s.ho_ten, s.ma, s.chuc_danh,
                       (g.ngay_het_han < (now() AT TIME ZONE '{VN}')::date) AS da_het_han
                FROM giay_to_nhan_su g JOIN nhan_su_van_hanh s ON s.id = g.nhan_su_van_hanh_id
                WHERE s.trang_thai <> 'da_nghi_viec' AND g.ngay_het_han IS NOT NULL
                  AND g.ngay_het_han <= (now() AT TIME ZONE '{VN}')::date + 30
                ORDER BY g.ngay_het_han, s.ho_ten LIMIT 50"""
        )
        return {"theo_chuc_danh": theo_chuc_danh, "giay_to_can_gia_han": _rows(cur)}
    return _chay(ham)


# =====================================================================================================================
# 7. Việc cần xử lý (ảnh chụp hiện tại — trang Tổng quan)
# =====================================================================================================================
def viec_can_xu_ly(p: dict, gio_nhac_gan_xe: int = 48) -> dict:
    def ham(cur):
        cur.execute(
            f"""SELECT
                  (SELECT count(*) {_TU_HOAN} WHERE h.trang_thai = 'cho_xu_ly' AND {_tuyen('c.tuyen_id')}) AS hoan_dang_cho,
                  (SELECT COALESCE(sum(h.so_tien), 0)::bigint {_TU_HOAN} WHERE h.trang_thai = 'cho_xu_ly' AND {_tuyen('c.tuyen_id')}) AS tien_hoan_dang_cho,
                  (SELECT count(*) FROM don_hang d WHERE d.trang_thai = 'qua_han_luu_kho' AND {_tuyen('d.tuyen_id')}) AS hang_qua_han,
                  (SELECT count(*) FROM don_hang d WHERE d.trang_thai = 'cho_lay' AND d.co_canh_bao_cho_lau AND {_tuyen('d.tuyen_id')}) AS hang_cho_lau,
                  (SELECT count(*) FROM chuyen_xe c WHERE c.trang_thai = 'chua_khoi_hanh' AND c.dang_hoan AND {_tuyen('c.tuyen_id')}) AS chuyen_dang_hoan,
                  (SELECT count(*) FROM chuyen_xe c WHERE c.trang_thai = 'gap_su_co' AND {_tuyen('c.tuyen_id')}) AS chuyen_gap_su_co,
                  (SELECT count(*) FROM chuyen_xe c WHERE c.trang_thai = 'chua_khoi_hanh' AND c.xe_id IS NULL AND NOT c.dang_hoan
                     AND c.gio_khoi_hanh > now() AND c.gio_khoi_hanh <= now() + make_interval(hours => %(gio_nhac)s)
                     AND {_tuyen('c.tuyen_id')}) AS chuyen_chua_gan_xe""",
            {**p, "gio_nhac": gio_nhac_gan_xe},
        )
        kq = _mot(cur)
        cur.execute(
            f"""SELECT count(*) AS n FROM giay_to_nhan_su g JOIN nhan_su_van_hanh s ON s.id = g.nhan_su_van_hanh_id
                WHERE s.trang_thai <> 'da_nghi_viec' AND g.ngay_het_han IS NOT NULL
                  AND g.ngay_het_han <= (now() AT TIME ZONE '{VN}')::date + 30"""
        )
        kq["giay_to_can_gia_han"] = _mot(cur)["n"]
        return kq
    return _chay(ham)
