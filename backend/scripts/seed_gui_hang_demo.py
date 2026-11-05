"""Tạo dữ liệu mẫu để TEST role nhân viên gửi hàng trên DB LOCAL (không dùng cho production).

Chạy trong container backend (sau khi đã `yoyo apply` migration):

    docker compose exec backend python scripts/seed_gui_hang_demo.py

Chạy lại bao nhiêu lần cũng được: hạ tầng (khu vực, văn phòng, tuyến, xe, tài khoản) được giữ; đơn hàng do các tài khoản demo
tạo, chuyến của xe demo và thông báo của tài khoản demo được xóa rồi tạo mới theo giờ hiện tại. Đơn/tài khoản sẵn có khác
không bị đụng tới (trừ việc điền SĐT liên hệ cho văn phòng nào còn để trống).

Tài khoản (đăng nhập tại /nhan-vien/dang-nhap.html):
    NV gửi hàng Mỹ Đình   guihang.mydinh@demo.nhaxe.vn   / GuiHang@123
    NV gửi hàng Yên Bái   guihang.yenbai@demo.nhaxe.vn   / GuiHang@123
    NV gửi hàng Lào Cai   guihang.laocai@demo.nhaxe.vn   / GuiHang@123   (cùng văn phòng với guihang@nhaxekhach.com có sẵn)
    NV gửi hàng Sa Pa     guihang.sapa@demo.nhaxe.vn     / GuiHang@123
    Phụ xe xe 24B-888.01  phuxe.guihang@demo.nhaxe.vn    / PhuXe@123     (chuyến đang chạy sắp tới Lào Cai — thử dỡ hàng
                                                                           để văn phòng Lào Cai nhận thông báo real-time)

Mạng lưới: tuyến có sẵn "Mỹ Đình -> Lào Cai" (T001) + tuyến demo "Mỹ Đình -> Sa Pa (qua Yên Bái)":
    VP Mỹ Đình → Điểm dừng Km 140 → VP Yên Bái → VP Lào Cai → VP Sa Pa
nên cặp Mỹ Đình ↔ Lào Cai có 2 tuyến (thử chọn tuyến khi tạo đơn), còn điểm dừng Km 140 không được chọn làm điểm nhận.

Mọi mốc thời gian tính theo giờ của DB lúc chạy script. Các cờ nhắc 24 giờ / cảnh báo 7 ngày / hàng tồn 14 ngày và thông báo
tương ứng được dựng đúng như job UC-46 đã chạy, trừ vài đơn để "chờ job" (job quét mỗi giờ sẽ nhắc và đẩy real-time).
Cuối script in danh sách mã vận đơn nổi bật theo từng văn phòng kèm việc nên thử.
"""

import os
import random
import sys
from datetime import datetime, time, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.repositories import ma_repository  # noqa: E402
from app.services.gui_hang_service import (  # noqa: E402 — dùng đúng câu chữ job UC-46 đang gửi
    _noi_dung_canh_bao_7_ngay,
    _noi_dung_hang_ton_14_ngay,
    _noi_dung_nhac_goi_bao_24h,
)
from app.services.mat_khau_service import _pwd_context  # noqa: E402
from app.utils import ma_tu_sinh  # noqa: E402

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
MAT_KHAU_GUI_HANG = "GuiHang@123"
MAT_KHAU_PHU_XE = "PhuXe@123"
EMAIL_PHU_XE = "phuxe.guihang@demo.nhaxe.vn"

# Ký hiệu điểm → (khu vực, tỉnh, tên điểm, địa chỉ, SĐT liên hệ, loại). Điểm đã có (tìm theo tên) chỉ được điền SĐT nếu còn trống.
DIEM = {
    "MD": ("Hà Nội", "Hà Nội", "Văn phòng Bến xe Mỹ Đình", "20 Phạm Hùng, Nam Từ Liêm, Hà Nội", "02437685549", "van_phong"),
    "KM": ("Yên Bái", "Yên Bái", "Điểm dừng Trạm nghỉ cao tốc Km 140", "Km 140 cao tốc Nội Bài – Lào Cai", None, "diem_dung"),
    "YB": ("Yên Bái", "Yên Bái", "Văn phòng Bến xe Yên Bái", "Đường Điện Biên, TP. Yên Bái", "02163852123", "van_phong"),
    "LC": ("Lào Cai", "Lào Cai", "Văn phòng Bến xe Trung tâm Lào Cai", "Đường Trần Hưng Đạo, TP. Lào Cai", "02143820168", "van_phong"),
    "SP": ("Lào Cai", "Lào Cai", "Văn phòng Sa Pa", "Số 9 Thạch Sơn, TX. Sa Pa", "02143871234", "van_phong"),
}
# Ký hiệu tuyến → (tên, [(ký hiệu điểm, phút dự kiến từ điểm đầu)]). Tuyến đã có (tìm theo tên) giữ nguyên các điểm của nó.
TUYEN = {
    "T1": ("Mỹ Đình -> Lào Cai", [("MD", 0), ("LC", 300)]),
    "TM": ("Mỹ Đình -> Sa Pa (qua Yên Bái)", [("MD", 0), ("KM", 120), ("YB", 170), ("LC", 300), ("SP", 370)]),
}
# Ký hiệu xe → (biển số, tuyến, điểm gốc)
XE = {
    "X1": ("24B-888.01", "TM", "MD"),
    "X2": ("24B-888.02", "TM", "SP"),
    "X3": ("29B-888.03", "T1", "MD"),
    "X4": ("24B-888.04", "TM", "MD"),
}
# Giờ chạy (giờ VN) của các chuyến đã hoàn thành ở những ngày trước, theo (tuyến, chiều)
LICH_QUA_KHU = {("TM", "xuoi"): ("X1", time(7, 0)), ("TM", "nguoc"): ("X2", time(13, 30)),
                ("T1", "xuoi"): ("X3", time(9, 0)), ("T1", "nguoc"): ("X3", time(16, 0))}
NHAN_VIEN = {  # văn phòng → (email, họ tên, SĐT)
    "MD": ("guihang.mydinh@demo.nhaxe.vn", "Nguyễn Thu Trang", "0911000001"),
    "YB": ("guihang.yenbai@demo.nhaxe.vn", "Hà Minh Đức", "0911000002"),
    "LC": ("guihang.laocai@demo.nhaxe.vn", "Lò Văn Hưng", "0911000003"),
    "SP": ("guihang.sapa@demo.nhaxe.vn", "Giàng Thị Mai", "0911000004"),
}

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô", "Lò", "Giàng", "Hà", "Lý", "Sùng"]
DEM = ["Văn", "Thị", "Đức", "Minh", "Quốc", "Thanh", "Hữu", "Ngọc", "Thu", "Anh", "Bảo", "Khánh"]
TEN = ["An", "Bình", "Cường", "Dũng", "Giang", "Hà", "Hải", "Hạnh", "Hiếu", "Hùng", "Huy", "Lan", "Linh", "Long",
       "Mai", "Nam", "Phúc", "Quân", "Sơn", "Thảo", "Trang", "Tú", "Vân", "Yến", "Đạt", "Hương"]
CUA_HANG = ["Cửa hàng điện máy Hưng Thịnh", "Nhà thuốc Bảo An", "Shop thời trang Linh Chi", "Công ty TNHH Thiết bị Minh Phát",
            "Văn phòng phẩm Hồng Hà", "Đặc sản Tây Bắc Sa Pa", "Homestay Cát Cát", "Phụ tùng xe máy Tuấn Hưng"]
DAU_SO = ["090", "091", "093", "094", "096", "097", "098", "032", "033", "035", "036", "038", "039", "077", "081", "083", "085", "088"]


def _chi_chay_tren_may_local() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")


def main() -> None:
    _chi_chay_tren_may_local()
    conn = get_connection()
    cur = conn.cursor()
    rng = random.Random(20261022)  # cố định → mỗi lần seed ra cùng bộ khách, dễ đối chiếu

    def mot(sql, args=()):
        cur.execute(sql, args)
        row = cur.fetchone()
        return row[0] if row else None

    # ---------- hạ tầng (giữ nguyên giữa các lần chạy)
    def khu_vuc(ten, tinh):
        kv = mot("SELECT id FROM khu_vuc WHERE ten = %s", (ten,))
        if kv:
            return kv
        ma = ma_tu_sinh.ma_khu_vuc(ma_repository.so_tiep_theo(cur, "khu_vuc"))
        return mot("INSERT INTO khu_vuc (ma, ten, tinh_thanh) VALUES (%s, %s, %s) RETURNING id", (ma, ten, tinh))

    diem, ten_diem = {}, {}
    for kh, (ten_kv, tinh, ten, dia_chi, sdt, loai) in DIEM.items():
        diem_id = mot("SELECT id FROM diem_don_tra WHERE ten = %s", (ten,))
        if not diem_id:
            ma_kv, so = ma_repository.cap_so_diem_trong_khu_vuc(cur, khu_vuc(ten_kv, tinh))
            diem_id = mot(
                """INSERT INTO diem_don_tra (khu_vuc_id, ten, dia_chi, loai, sdt_lien_he, ma)
                   VALUES ((SELECT id FROM khu_vuc WHERE ma = %s), %s, %s, %s, %s, %s) RETURNING id""",
                (ma_kv, ten, dia_chi, loai, sdt, ma_tu_sinh.ma_diem_don_tra(ma_kv, so)),
            )
        elif sdt:
            cur.execute("UPDATE diem_don_tra SET sdt_lien_he = %s WHERE id = %s AND sdt_lien_he IS NULL", (sdt, diem_id))
        diem[kh], ten_diem[kh] = str(diem_id), ten
    ky_hieu_cua = {v: k for k, v in diem.items()}

    tuyen, diem_tuyen = {}, {}
    for kh, (ten, cac_diem) in TUYEN.items():
        tuyen_id = mot("SELECT id FROM tuyen WHERE ten = %s", (ten,))
        if not tuyen_id:
            ma = ma_tu_sinh.ma_tuyen(ma_repository.so_tiep_theo(cur, "tuyen"))
            tuyen_id = mot("INSERT INTO tuyen (ma, ten) VALUES (%s, %s) RETURNING id", (ma, ten))
            for thu_tu, (d, phut) in enumerate(cac_diem, start=1):
                cur.execute(
                    "INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut) VALUES (%s, %s, %s, %s)",
                    (tuyen_id, diem[d], thu_tu, phut),
                )
        tuyen[kh] = str(tuyen_id)
        # Lấy lại từ DB: tuyến có sẵn có thể khác cấu hình ở trên
        cur.execute(
            "SELECT diem_don_tra_id::text, thoi_gian_du_kien_phut FROM tuyen_diem_don_tra WHERE tuyen_id = %s ORDER BY thu_tu",
            (tuyen_id,),
        )
        diem_tuyen[kh] = [(ky_hieu_cua[d], phut) for d, phut in cur.fetchall() if d in ky_hieu_cua]
        if {"MD", "LC"} - {d for d, _ in diem_tuyen[kh]}:
            sys.exit(f"Tuyến '{ten}' trong DB không đi qua cả Mỹ Đình và Lào Cai — sửa tuyến hoặc đổi tên trong TUYEN.")

    loai_xe = mot("SELECT id FROM loai_xe ORDER BY ma LIMIT 1")
    if not loai_xe:
        sys.exit("Chưa có loại xe nào — tạo 1 loại xe ở trang quản lý trước rồi chạy lại.")
    xe = {}
    for kh, (bien_so, tuyen_kh, goc) in XE.items():
        xe_id = mot("SELECT id FROM xe WHERE bien_so = %s", (bien_so,)) or mot(
            "INSERT INTO xe (bien_so, loai_xe_id, diem_goc_id, tuyen_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (bien_so, loai_xe, diem[goc], tuyen[tuyen_kh]),
        )
        cur.execute("UPDATE xe SET trang_thai = 'hoat_dong' WHERE id = %s", (xe_id,))
        xe[kh] = str(xe_id)

    def tai_khoan(email, ho_ten, sdt, vai_tro, mat_khau):
        nd = mot("SELECT id FROM nguoi_dung WHERE email = %s", (email,)) or mot(
            """INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan)
               VALUES (%s, %s, %s, %s, %s, true) RETURNING id""",
            (email, _pwd_context.hash(mat_khau), ho_ten, sdt, vai_tro),
        )
        # Luôn đặt lại mật khẩu để lần chạy nào cũng đăng nhập được với mật khẩu ghi ở đầu file
        cur.execute("UPDATE nguoi_dung SET mat_khau = %s, da_xac_nhan = true, dang_hoat_dong = true WHERE id = %s",
                    (_pwd_context.hash(mat_khau), nd))
        return str(nd)

    nv = {}
    for vp, (email, ho_ten, sdt) in NHAN_VIEN.items():
        nv[vp] = tai_khoan(email, ho_ten, sdt, "nhan_vien_gui_hang", MAT_KHAU_GUI_HANG)
        cur.execute(
            """INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id) VALUES (%s, %s)
               ON CONFLICT (nguoi_dung_id) DO UPDATE SET van_phong_id = EXCLUDED.van_phong_id""",
            (nv[vp], diem[vp]),
        )
    phu_xe = tai_khoan(EMAIL_PHU_XE, "Phụ Xe Gửi Hàng Demo", "0911000009", "phu_xe", MAT_KHAU_PHU_XE)
    nhan_su = mot("SELECT id FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s", (phu_xe,)) or mot(
        "INSERT INTO nhan_su_van_hanh (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id) VALUES (%s, %s, 'phu_xe', %s) RETURNING id",
        ("Phụ Xe Gửi Hàng Demo", "0911000009", phu_xe),
    )
    cur.execute("UPDATE nhan_su_van_hanh SET trang_thai = 'dang_lam', ngay_nghi_viec = NULL, ly_do_nghi_viec = NULL WHERE id = %s",
                (nhan_su,))
    if not mot("SELECT 1 FROM xe_nhan_su WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe["X1"], nhan_su)):
        cur.execute("INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh')", (xe["X1"], nhan_su))
    cur.execute("UPDATE xe_nhan_su SET trang_thai = 'dang_hoat_dong' WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe["X1"], nhan_su))

    # Người nhận thông báo: MỌI nhân viên gửi hàng đang hoạt động ở văn phòng (kể cả tài khoản có sẵn), và các quản lý
    cur.execute(
        """SELECT h.van_phong_id::text, h.nguoi_dung_id::text FROM ho_so_can_bo_diem h JOIN nguoi_dung nd ON nd.id = h.nguoi_dung_id
           WHERE nd.vai_tro = 'nhan_vien_gui_hang' AND nd.dang_hoat_dong"""
    )
    nv_tai = {vp: [] for vp in diem}
    for van_phong_id, nguoi_dung_id in cur.fetchall():
        if van_phong_id in ky_hieu_cua:
            nv_tai[ky_hieu_cua[van_phong_id]].append(nguoi_dung_id)
    cur.execute("SELECT id::text FROM nguoi_dung WHERE vai_tro = 'quan_ly' AND dang_hoat_dong")
    quan_ly = [r[0] for r in cur.fetchall()]

    # ---------- dữ liệu chạy thử: xóa bản cũ rồi tạo mới
    nv_demo = list(nv.values())
    cur.execute("DELETE FROM bao_cao_su_co_hang WHERE don_hang_id IN (SELECT id FROM don_hang WHERE nhan_vien_gui_id = ANY(%s::uuid[]))",
                (nv_demo,))
    cur.execute("DELETE FROM don_hang WHERE nhan_vien_gui_id = ANY(%s::uuid[])", (nv_demo,))  # lịch sử + thông báo của đơn xóa theo
    cur.execute("DELETE FROM thong_bao WHERE nguoi_nhan_id = ANY(%s::uuid[])", (nv_demo + [phu_xe],))
    # Chuyến của xe demo — trừ chuyến còn chở đơn/vé không phải của demo (VD bạn tự tạo đơn bằng tài khoản khác rồi phụ xe chất lên)
    cur.execute(
        """SELECT id FROM chuyen_xe c WHERE c.xe_id = ANY(%s::uuid[])
             AND NOT EXISTS (SELECT 1 FROM don_hang d WHERE d.chuyen_id = c.id)
             AND NOT EXISTS (SELECT 1 FROM ve v WHERE v.chuyen_id = c.id)""",
        (list(xe.values()),),
    )
    chuyen_cu = [r[0] for r in cur.fetchall()]
    cur.execute("DELETE FROM lich_su_diem_dung_chuyen WHERE chuyen_id = ANY(%s::uuid[])", (chuyen_cu,))
    cur.execute("DELETE FROM chuyen_xe WHERE id = ANY(%s::uuid[])", (chuyen_cu,))

    bay_gio = mot("SELECT now()")  # dùng đồng hồ của DB (job UC-46 cũng so với now() của DB)
    n0 = bay_gio.replace(second=0, microsecond=0)
    hom_nay = bay_gio.astimezone(MUI_GIO_VN).date()

    def phut(so_phut):
        return n0 + timedelta(minutes=so_phut)

    def luc(ngay_truoc, gio, phut_=0):
        """Mốc giờ VN của `ngay_truoc` ngày trước."""
        return datetime.combine(hom_nay - timedelta(days=ngay_truoc), time(gio, phut_), tzinfo=MUI_GIO_VN)

    def khach_ngau_nhien(la_cua_hang=False):
        ten = rng.choice(CUA_HANG) if la_cua_hang else f"{rng.choice(HO)} {rng.choice(DEM)} {rng.choice(TEN)}"
        return ten, rng.choice(DAU_SO) + "".join(str(rng.randint(0, 9)) for _ in range(7))

    # Khách quen: người gửi lặp lại giữa các đơn để thử gợi ý tên theo SĐT
    khach_quen = [khach_ngau_nhien(i % 4 == 0) for i in range(24)]

    cur.execute("SELECT id, ten FROM loai_hang WHERE NOT la_hang_cam ORDER BY ten")
    cac_loai = cur.fetchall()

    def loai_hang(tu_khoa):
        return next((str(i) for i, ten in cac_loai if tu_khoa.lower() in ten.lower()), str(cac_loai[0][0]))

    LOAI = {"thuong": loai_hang("thông thường"), "de_vo": loai_hang("dễ vỡ"), "tai_lieu": loai_hang("tài liệu"),
            "thuc_pham": loai_hang("thực phẩm")}

    # ---------- chuyến xe
    def tao_chuyen(tuyen_kh, chieu, xe_kh, gio_di, trang_thai, so_diem_da_toi=None, lech_phut=0, **them):
        """Tạo chuyến + lịch sử tới điểm. so_diem_da_toi: số điểm (sau điểm đầu) xe đã tới; None = tới hết (hoàn thành)."""
        cac_diem = diem_tuyen[tuyen_kh] if chieu == "xuoi" else diem_tuyen[tuyen_kh][::-1]
        goc = cac_diem[0][1]
        gio = {d: gio_di + timedelta(minutes=abs(p - goc) + (lech_phut if i else 0)) for i, (d, p) in enumerate(cac_diem)}
        da_toi = [d for d, _ in cac_diem[1:]][: (len(cac_diem) - 1 if so_diem_da_toi is None else so_diem_da_toi)]
        ma_tuyen, ma_loai_xe = ma_repository.lay_ma_tuyen_va_loai_xe(cur, tuyen[tuyen_kh], loai_xe)
        while True:  # mã trùng chuyến cũ còn giữ lại (đang chở đơn không phải demo) → lùi 1 phút
            ma = ma_tu_sinh.ma_chuyen(ma_tuyen, ma_loai_xe, gio_di, chieu)
            if not mot("SELECT 1 FROM chuyen_xe WHERE ma = %s", (ma,)):
                break
            gio_di += timedelta(minutes=1)
        cot = {"ma": ma, "tuyen_id": tuyen[tuyen_kh], "xe_id": xe[xe_kh], "loai_xe_id": loai_xe, "gio_khoi_hanh": gio_di,
               "chieu": chieu, "trang_thai": trang_thai, **them}
        if trang_thai != "chua_khoi_hanh":
            cot["gio_xac_nhan_xuat_phat"] = gio_di + timedelta(minutes=2)
        if trang_thai == "hoan_thanh":
            cot["gio_hoan_thanh"] = gio[cac_diem[-1][0]]
        chuyen_id = mot(
            f"INSERT INTO chuyen_xe ({', '.join(cot)}) VALUES ({', '.join(['%s'] * len(cot))}) RETURNING id", tuple(cot.values())
        )
        for d in da_toi:
            cur.execute("INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id, gio_thuc_te) VALUES (%s, %s, %s)",
                        (chuyen_id, diem[d], gio[d]))
        return {"id": str(chuyen_id), "tuyen": tuyen_kh, "gio": gio, "da_qua": {cac_diem[0][0], *da_toi}, "da_toi": set(da_toi)}

    chuyen_qua_khu = {}

    def chuyen_ngay(tuyen_kh, chieu, ngay_truoc):
        """Chuyến đã hoàn thành của (tuyến, chiều) ở `ngay_truoc` ngày trước — tạo khi cần lần đầu."""
        khoa = (tuyen_kh, chieu, ngay_truoc)
        if khoa not in chuyen_qua_khu:
            xe_kh, gio = LICH_QUA_KHU[(tuyen_kh, chieu)]
            chuyen_qua_khu[khoa] = tao_chuyen(tuyen_kh, chieu, xe_kh, luc(ngay_truoc, gio.hour, gio.minute), "hoan_thanh",
                                              lech_phut=rng.randint(-5, 12))
        return chuyen_qua_khu[khoa]

    def chieu_tren(tuyen_kh, gui, nhan):
        thu_tu = [d for d, _ in diem_tuyen[tuyen_kh]]
        return "xuoi" if thu_tu.index(gui) < thu_tu.index(nhan) else "nguoc"

    def tuyen_qua(gui, nhan):
        return [k for k, ds in diem_tuyen.items() if {gui, nhan} <= {d for d, _ in ds}]

    # Chuyến hôm nay
    c0 = tao_chuyen("TM", "xuoi", "X4", phut(-480), "hoan_thanh")  # xong lúc ~2 tiếng trước: hàng vừa tới Lào Cai, Sa Pa
    c1 = tao_chuyen("TM", "xuoi", "X1", phut(-250), "dang_chay", so_diem_da_toi=2,  # đã qua Yên Bái, đang chạy tới Lào Cai
                    dang_di_chuyen=True, gio_roi_diem=phut(-65))
    c2 = tao_chuyen("TM", "nguoc", "X2", phut(-300), "gap_su_co", so_diem_da_toi=1,  # Sa Pa → Lào Cai rồi kẹt giữa đường
                    dang_di_chuyen=True, gio_roi_diem=phut(-220), loai_su_co="loi_khach_quan",
                    ly_do_su_co="Sạt lở taluy cao tốc Nội Bài – Lào Cai đoạn Km 210, xe đang chờ thông đường")
    c3 = tao_chuyen("T1", "xuoi", "X3", phut(-50), "chua_khoi_hanh", so_diem_da_toi=0, dang_hoan=True)  # đã chất hàng nhưng hoãn

    # ---------- đơn hàng
    ma_da_dung = set()
    noi_bat = {vp: [] for vp in NHAN_VIEN}

    def bao(nguoi_nhan_ids, noi_dung, don_id, thoi_diem):
        if thoi_diem > bay_gio:
            return
        for nguoi_id in dict.fromkeys(nguoi_nhan_ids):
            cur.execute(
                "INSERT INTO thong_bao (nguoi_nhan_id, noi_dung, don_hang_id, ngay_tao, da_doc) VALUES (%s, %s, %s, %s, %s)",
                (nguoi_id, noi_dung, don_id, thoi_diem, thoi_diem < bay_gio - timedelta(hours=12)),
            )

    def tao_don(gui, nhan, tao, *, cuoc, kg, cod=False, loai="thuong", tuyen_kh=None, chuyen=None, len_xe=None, giao=None,
                lien_he=(), cho_job=None, huy=None, su_co=None, sua_sdt=None, nguoi_gui=None, nguoi_nhan=None,
                kich_thuoc=None, mo_ta=None):
        """lien_he: [(lúc, đối tượng, kết quả, ghi chú)] — nhân viên văn phòng nhận gọi.
        cho_job: "24h" | "7d" — để nguyên mốc đó chưa xử lý (job UC-46 sẽ làm ở lần quét sau).
        huy: (lý do, ghi chú, lúc). su_co: (loại, mô tả). sua_sdt: (lúc, văn phòng sửa, SĐT mới, lý do)."""
        tuyen_kh = chuyen["tuyen"] if chuyen else (tuyen_kh or rng.choice(tuyen_qua(gui, nhan)))
        nguoi_gui = nguoi_gui or rng.choice(khach_quen)
        nguoi_nhan = nguoi_nhan or khach_ngau_nhien(rng.random() < 0.2)
        sdt_cu = nguoi_nhan[1]
        sdt_nhan = sua_sdt[2] if sua_sdt else sdt_cu

        def sdt_luc(t):
            return sdt_cu if sua_sdt and t < sua_sdt[0] else sdt_nhan

        if chuyen and len_xe is None:
            len_xe = chuyen["gio"][gui] + (timedelta(minutes=5) if gui != min(chuyen["gio"], key=chuyen["gio"].get) else timedelta())
        den = chuyen["gio"][nhan] if chuyen and nhan in chuyen["da_toi"] else None
        moc = giao or bay_gio  # trạng thái các cờ tính tới lúc giao (đơn đã giao) hoặc bây giờ

        def da_bao_luc(t):
            sau_lan_sua = sua_sdt[0] if sua_sdt else None
            return any(dt == "nguoi_nhan" and kq == "da_lien_he" and lc <= t and (sau_lan_sua is None or lc > sau_lan_sua)
                       for lc, dt, kq, _ in lien_he)

        nhac_24h = canh_bao_7 = ton_14 = None
        if den:
            if moc - den >= timedelta(hours=24) and not da_bao_luc(den + timedelta(hours=24)) and cho_job != "24h":
                nhac_24h = den + timedelta(hours=24)
            if moc - den >= timedelta(days=7) and cho_job != "7d":
                canh_bao_7 = den + timedelta(days=7)
            if moc - den >= timedelta(days=14):
                ton_14 = den + timedelta(days=14)
        trang_thai = ("da_huy" if huy else "da_giao" if giao else "qua_han_luu_kho" if ton_14 else
                      "cho_lay" if den else "da_len_xe" if len_xe else "cho_van_chuyen")

        ma = None
        while not ma or ma in ma_da_dung or mot("SELECT 1 FROM don_hang WHERE ma_van_don = %s", (ma,)):
            ma = f"DH-{tao.astimezone(MUI_GIO_VN):%Y%m%d}-{rng.getrandbits(24):06X}"
        ma_da_dung.add(ma)
        da_thu = not cod or bool(giao)
        dai, rong, cao = kich_thuoc or (None, None, None)
        cot = {
            "ma_van_don": ma, "tuyen_id": tuyen[tuyen_kh], "chuyen_id": chuyen["id"] if chuyen and len_xe else None,
            "diem_gui_id": diem[gui], "diem_nhan_id": diem[nhan], "can_nang_kg": kg, "dai_cm": dai, "rong_cm": rong, "cao_cm": cao,
            "loai_hang_id": LOAI[loai], "gia_cuoc": cuoc, "ten_nguoi_gui": nguoi_gui[0], "sdt_nguoi_gui": nguoi_gui[1],
            "ten_nguoi_nhan": nguoi_nhan[0], "sdt_nguoi_nhan": sdt_nhan,
            "phuong_thuc_thanh_toan": "cod_nguoi_nhan_tra" if cod else "nguoi_gui_tra_truoc", "trang_thai": trang_thai,
            "nhan_vien_gui_id": nv[gui], "nhan_vien_nhan_id": nv[nhan] if giao else None, "thoi_gian_den_diem_nhan": den,
            "da_thong_bao_nguoi_nhan": da_bao_luc(moc), "co_canh_bao_cho_lau": bool(canh_bao_7 or ton_14),
            "da_nhac_goi_bao": bool(nhac_24h), "ngay_tao": tao, "ngay_giao": giao, "da_thu_tien": da_thu,
            "nhan_vien_thu_id": (nv[nhan] if cod else nv[gui]) if da_thu else None,
            "thoi_gian_thu": (giao if cod else tao) if da_thu else None,
        }
        if huy:
            cot.update(ly_do_huy=huy[0], ghi_chu_huy=huy[1], thoi_gian_huy=huy[2], nhan_vien_huy_id=nv[gui],
                       so_tien_hoan=None if cod else cuoc)
        don_id = str(mot(f"INSERT INTO don_hang ({', '.join(cot)}) VALUES ({', '.join(['%s'] * len(cot))}) RETURNING id",
                         tuple(cot.values())))

        # Lịch sử trạng thái: trigger chỉ ghi được 1 dòng "tạo đơn" với trạng thái cuối → viết lại đủ chuỗi theo đúng mốc giờ
        cur.execute("DELETE FROM lich_su_trang_thai_don WHERE don_hang_id = %s", (don_id,))
        chuoi = [(None, "cho_van_chuyen", nv[gui], tao)]
        if huy:
            chuoi.append(("cho_van_chuyen", "da_huy", nv[gui], huy[2]))
        if len_xe:
            chuoi.append(("cho_van_chuyen", "da_len_xe", phu_xe, len_xe))
        if den:
            chuoi.append(("da_len_xe", "cho_lay", phu_xe, den))
        if ton_14:
            chuoi.append(("cho_lay", "qua_han_luu_kho", None, ton_14))
        if giao:
            chuoi.append((chuoi[-1][1], "da_giao", nv[nhan], giao))
        cur.executemany(
            "INSERT INTO lich_su_trang_thai_don (don_hang_id, tu_trang_thai, den_trang_thai, nguoi_thuc_hien_id, thoi_gian) VALUES (%s, %s, %s, %s, %s)",
            [(don_id, *dong) for dong in chuoi],
        )

        for lc, doi_tuong, ket_qua, ghi_chu in lien_he:
            cur.execute(
                "INSERT INTO lich_su_lien_he_don_hang (don_hang_id, nhan_vien_id, doi_tuong, ket_qua, ghi_chu, ngay_tao) VALUES (%s, %s, %s, %s, %s, %s)",
                (don_id, nv[nhan], doi_tuong, ket_qua, ghi_chu, lc),
            )
            if doi_tuong == "quan_ly":
                bao(quan_ly, f"Đơn {ma} tại {ten_diem[nhan]} không liên hệ được người nhận/người gửi, cần quản lý xử lý hàng tồn."
                    + (f" Ghi chú: {ghi_chu}" if ghi_chu else ""), don_id, lc)
        if sua_sdt:
            lc, vp_sua, sdt_moi, ly_do = sua_sdt
            cur.execute(
                """INSERT INTO lich_su_chinh_sua_don (don_hang_id, truong, gia_tri_cu, gia_tri_moi, nguoi_thuc_hien_id, ly_do, thoi_gian)
                   VALUES (%s, 'sdt_nguoi_nhan', %s, %s, %s, %s, %s)""",
                (don_id, sdt_cu, sdt_moi, nv[vp_sua], ly_do, lc),
            )
            vp_con_lai = nhan if vp_sua == gui else gui
            noi_dung = f"Đơn {ma} vừa được sửa SĐT người nhận — kiểm tra lại thông tin trước khi gọi/bàn giao."
            if vp_con_lai == nhan and den and den <= lc:
                noi_dung += f" Hàng đang ở văn phòng nhận: gọi báo lại người nhận theo số mới {sdt_moi}."
            bao(nv_tai[vp_con_lai], noi_dung, don_id, lc)
        if su_co:
            lc = (den or len_xe) + timedelta(minutes=3)
            cur.execute("INSERT INTO bao_cao_su_co_hang (don_hang_id, nguoi_bao_cao_id, mo_ta, loai, ngay_tao) VALUES (%s, %s, %s, %s, %s)",
                        (don_id, phu_xe, su_co[1], su_co[0], lc))
            bao(nv_tai[nhan if len_xe else gui] + quan_ly,
                f"Phụ xe báo {'THẤT LẠC' if su_co[0] == 'that_lac' else 'hư hỏng'} hàng đơn {ma}: {su_co[1]}", don_id, lc)

        # Thông báo phụ xe dỡ hàng + job UC-46 — bỏ qua với đơn đã giao xong từ lâu cho chuông khỏi ngập tin cũ
        if den and (not giao or giao >= bay_gio - timedelta(days=2)):
            bao(nv_tai[nhan], f"Đơn {ma} vừa tới văn phòng — gọi báo người nhận {nguoi_nhan[0]} ({sdt_luc(den)}).", don_id, den)
            if nhac_24h:
                bao(nv_tai[nhan], _noi_dung_nhac_goi_bao_24h({"ma_van_don": ma, "ten_nguoi_nhan": nguoi_nhan[0],
                                                               "sdt_nguoi_nhan": sdt_luc(nhac_24h)}), don_id, nhac_24h)
            if canh_bao_7:
                bao(nv_tai[nhan], _noi_dung_canh_bao_7_ngay({"ma_van_don": ma, "da_thong_bao_nguoi_nhan": da_bao_luc(canh_bao_7)}),
                    don_id, canh_bao_7)
            if ton_14:
                bao(nv_tai[nhan], _noi_dung_hang_ton_14_ngay({"ma_van_don": ma}), don_id, ton_14)

        if mo_ta:  # liệt kê ở văn phòng đang phải xử lý đơn: còn ở kho gửi / đã hủy → văn phòng gửi, còn lại → văn phòng nhận
            noi_bat[gui if trang_thai in ("cho_van_chuyen", "da_huy") else nhan].append((ma, trang_thai, mo_ta))
        return ma

    def goi_ok(lc, ghi_chu=None):
        return (lc, "nguoi_nhan", "da_lien_he", ghi_chu)

    def goi_truot(lc, ghi_chu="Thuê bao không liên lạc được"):
        return (lc, "nguoi_nhan", "khong_lien_he_duoc", ghi_chu)

    h = timedelta(hours=1)

    # ===== Chờ xếp xe / hủy đơn (văn phòng gửi)
    tao_don("MD", "LC", phut(-40), tuyen_kh="T1", cuoc=100000, kg=6, kich_thuoc=(40, 30, 30),
            nguoi_gui=("Phạm Thị Hồng", "0904123456"), nguoi_nhan=("Đỗ Văn Khải", "0912888001"),
            mo_ta="Chờ xếp xe, trả trước — thử HỦY ĐƠN (hoàn 100.000đ) hoặc sửa tên/SĐT")
    tao_don("MD", "SP", phut(-25), cod=True, loai="thuc_pham", cuoc=130000, kg=9,
            mo_ta="Chờ xếp xe, người nhận trả cước — hủy thì không hoàn tiền")
    tao_don("MD", "YB", luc(2, 8, 30), loai="tai_lieu", cuoc=60000, kg=0.5, mo_ta="Chờ xếp xe đã 2 ngày")
    tao_don("MD", "LC", phut(-180), cuoc=95000, kg=4, huy=("khach_doi_y", None, phut(-150)),
            mo_ta="Đã hủy hôm nay, đã hoàn 95.000đ — xem ở đối soát tiền")
    tao_don("MD", "SP", luc(1, 9, 10), cod=True, cuoc=150000, kg=11,
            huy=("nhap_sai_thong_tin", "Nhập nhầm văn phòng nhận, đã tạo lại đơn khác", luc(1, 9, 25)),
            mo_ta="Đã hủy hôm qua (nhập sai), đơn COD nên không hoàn")
    tao_don("LC", "MD", phut(-60), tuyen_kh="T1", cuoc=110000, kg=7, nguoi_gui=("Vàng Seo Pao", "0388123456"),
            mo_ta="Chờ xếp xe, trả trước — thử HỦY ĐƠN (hoàn 110.000đ)")
    tao_don("LC", "YB", phut(-180), cod=True, cuoc=40000, kg=2, mo_ta="Chờ xếp xe, người nhận trả cước")
    tao_don("LC", "MD", phut(-300), cuoc=70000, kg=3,
            huy=("khac", "Người gửi muốn chuyển sang gửi chuyến khác của nhà xe bạn", phut(-240)),
            mo_ta="Đã hủy hôm nay (lý do khác), đã hoàn 70.000đ")
    tao_don("SP", "YB", phut(-120), cuoc=45000, kg=2.5, mo_ta="Chờ xếp xe, trả trước")
    tao_don("YB", "MD", phut(-240), cod=True, cuoc=80000, kg=5, mo_ta="Chờ xếp xe, người nhận trả cước")

    # ===== Sắp đến (đang trên xe)
    tao_don("MD", "LC", phut(-360), chuyen=c1, cuoc=150000, kg=12, kich_thuoc=(60, 40, 40),
            nguoi_gui=("Công ty TNHH Thiết bị Minh Phát", "0912345678"), nguoi_nhan=("Cửa hàng điện máy Hưng Thịnh", "0987654321"),
            mo_ta="Sắp đến trên xe 24B-888.01 — đăng nhập phụ xe, xác nhận tới Lào Cai rồi DỠ HÀNG để thấy thông báo real-time")
    tao_don("MD", "LC", phut(-300), chuyen=c1, cod=True, loai="de_vo", cuoc=90000, kg=5, mo_ta="Sắp đến (xe 24B-888.01), hàng dễ vỡ, COD")
    tao_don("YB", "LC", phut(-180), chuyen=c1, cod=True, loai="tai_lieu", cuoc=60000, kg=1, mo_ta="Sắp đến, gửi từ Yên Bái, COD")
    tao_don("MD", "SP", phut(-330), chuyen=c1, loai="thuc_pham", cuoc=180000, kg=8, mo_ta="Sắp đến (xe 24B-888.01)")
    tao_don("MD", "LC", phut(-120), chuyen=c3, len_xe=phut(-60), loai="tai_lieu", cuoc=70000, kg=2,
            mo_ta="Sắp đến nhưng chuyến ĐANG HOÃN — nhãn cảnh báo trễ")
    tao_don("SP", "MD", phut(-360), chuyen=c2, loai="thuc_pham", cuoc=200000, kg=15,
            nguoi_gui=("Đặc sản Tây Bắc Sa Pa", "0915678234"), mo_ta="Sắp đến nhưng chuyến GẶP SỰ CỐ (sạt lở) — nhãn cảnh báo")
    tao_don("LC", "MD", phut(-300), chuyen=c2, cod=True, cuoc=120000, kg=10, mo_ta="Sắp đến, chuyến gặp sự cố, COD")
    tao_don("LC", "YB", phut(-280), chuyen=c2, loai="tai_lieu", cuoc=50000, kg=1.5, mo_ta="Sắp đến, chuyến gặp sự cố")

    # ===== Vừa tới hôm nay (chuyến c0 xong ~2 tiếng trước, c1 vừa qua Yên Bái)
    tao_don("MD", "LC", phut(-540), chuyen=c0, cuoc=85000, kg=6, mo_ta="Vừa tới, CHỜ GỌI BÁO — thử ghi kết quả gọi")
    tao_don("MD", "LC", phut(-560), chuyen=c0, cod=True, cuoc=140000, kg=14, lien_he=[goi_truot(phut(-120))],
            mo_ta="Vừa tới, đã gọi 1 lần không được, COD")
    tao_don("MD", "LC", phut(-600), chuyen=c0, loai="de_vo", cuoc=120000, kg=9, kich_thuoc=(50, 50, 45),
            lien_he=[goi_ok(phut(-160), "Hẹn tối nay ra lấy")],
            su_co=("hu_hong", "Thùng carton móp một góc, hàng bên trong chưa kiểm tra"),
            mo_ta="Chờ lấy, có BÁO CÁO HƯ HỎNG của phụ xe — giao sẽ cảnh báo kiểm hàng")
    tao_don("YB", "LC", phut(-420), chuyen=c0, cod=True, cuoc=55000, kg=3, lien_he=[goi_ok(phut(-150))],
            mo_ta="Chờ lấy, đã báo người nhận, COD 55.000đ — thử GIAO + thu tiền")
    tao_don("MD", "SP", phut(-520), chuyen=c0, cuoc=75000, kg=4, mo_ta="Vừa tới, chờ gọi báo")
    tao_don("MD", "YB", phut(-380), chuyen=c1, cuoc=65000, kg=3, mo_ta="Vừa tới (xe 24B-888.01 dỡ ở Yên Bái), chờ gọi báo")

    # ===== Chờ lâu tại văn phòng nhận (UC-24 / UC-25)
    c = chuyen_ngay("TM", "xuoi", 2)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cuoc=90000, kg=5,
            lien_he=[goi_truot(c["gio"]["LC"] + h), goi_truot(c["gio"]["LC"] + 20 * h, "Đổ chuông không ai nghe")],
            mo_ta="Tới hơn 24 giờ chưa báo được — ĐÃ NHẮC 24h, việc cần làm: gọi lại người nhận")
    c = chuyen_ngay("T1", "xuoi", 2)
    tao_don("MD", "LC", c["gio"]["MD"] - 2 * h, chuyen=c, cuoc=80000, kg=4, cho_job="24h",
            mo_ta="Tới hơn 24 giờ chưa báo, CHƯA NHẮC — job quét mỗi giờ sẽ nhắc + đẩy real-time")
    c = chuyen_ngay("TM", "xuoi", 1)
    tao_don("MD", "LC", c["gio"]["MD"] - 5 * h, chuyen=c, cuoc=100000, kg=8, lien_he=[goi_ok(c["gio"]["LC"] + 40 * h / 60)],
            mo_ta="Chờ lấy, đã báo, trả trước — thử GIAO HÀNG")
    c = chuyen_ngay("TM", "nguoc", 2)
    tao_don("SP", "YB", c["gio"]["SP"] - 4 * h, chuyen=c, cod=True, cuoc=85000, kg=6, lien_he=[goi_ok(c["gio"]["YB"] + h)],
            mo_ta="Chờ lấy, đã báo, COD 85.000đ — giao phải xác nhận đã thu")
    c = chuyen_ngay("T1", "xuoi", 3)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cuoc=95000, kg=7, nguoi_nhan=("Trần Văn Tùng", "0987111222"),
            lien_he=[goi_truot(c["gio"]["LC"] + h / 2, "Số máy không đúng"), goi_ok(luc(2, 9, 0), "Hẹn chiều mai tới lấy")],
            sua_sdt=(c["gio"]["LC"] + 5 * h, "MD", "0987111333", "Người gửi gọi lại báo số đúng của người nhận"),
            mo_ta="Đã SỬA SĐT người nhận (từ VP Mỹ Đình) — xem nhật ký chỉnh sửa")
    c = chuyen_ngay("TM", "xuoi", 8)
    tao_don("MD", "LC", c["gio"]["MD"] - 4 * h, chuyen=c, cuoc=120000, kg=10,
            lien_he=[goi_ok(c["gio"]["LC"] + h), goi_ok(luc(1, 10, 0), "Người nhận hẹn Chủ nhật lên lấy")],
            mo_ta="Chờ quá 7 NGÀY, đã từng báo người nhận — gọi lại người nhận")
    c = chuyen_ngay("T1", "xuoi", 9)
    tao_don("MD", "LC", c["gio"]["MD"] - 2 * h, chuyen=c, cuoc=70000, kg=3,
            lien_he=[goi_truot(c["gio"]["LC"] + h), goi_truot(c["gio"]["LC"] + 26 * h), goi_truot(c["gio"]["LC"] + 72 * h),
                     (luc(1, 15, 0), "nguoi_gui", "khong_lien_he_duoc", "Người gửi tắt máy")],
            mo_ta="Chờ quá 7 NGÀY, CHƯA từng báo được — gọi người gửi; thử BÁO QUẢN LÝ")
    c = chuyen_ngay("T1", "xuoi", 8)
    tao_don("MD", "LC", c["gio"]["MD"] - 2 * h, chuyen=c, cuoc=60000, kg=2, cho_job="7d", lien_he=[goi_ok(c["gio"]["LC"] + 2 * h)],
            mo_ta="Đủ 7 ngày nhưng CHƯA bật cảnh báo — job quét mỗi giờ sẽ cảnh báo + đẩy real-time")
    c = chuyen_ngay("TM", "xuoi", 16)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cuoc=150000, kg=13,
            lien_he=[goi_truot(c["gio"]["LC"] + h), goi_truot(c["gio"]["LC"] + 48 * h),
                     (luc(8, 10, 0), "nguoi_gui", "khong_lien_he_duoc", None), (luc(1, 14, 0), "nguoi_gui", "khong_lien_he_duoc", None)],
            mo_ta="HÀNG TỒN (16 ngày), không liên hệ được ai — thử BÁO QUẢN LÝ")
    c = chuyen_ngay("T1", "xuoi", 19)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cuoc=110000, kg=9,
            lien_he=[goi_truot(c["gio"]["LC"] + h), (luc(5, 9, 0), "nguoi_gui", "khong_lien_he_duoc", None),
                     (luc(3, 10, 0), "quan_ly", "da_bao_quan_ly", "Đã gọi người gửi 3 lần trong 2 ngày, không liên lạc được")],
            mo_ta="HÀNG TỒN (19 ngày), ĐÃ BÁO QUẢN LÝ")
    c = chuyen_ngay("TM", "xuoi", 15)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cod=True, cuoc=60000, kg=4,
            lien_he=[goi_truot(c["gio"]["LC"] + h),
                     (luc(1, 16, 0), "nguoi_gui", "da_lien_he", "Người gửi nhờ em trai Lý Văn Sơn (0978456123) tới lấy thứ Bảy, thu cước khi giao")],
            mo_ta="HÀNG TỒN đã thỏa thuận với người gửi — thử GIAO hàng tồn, COD 60.000đ")
    c = chuyen_ngay("T1", "nguoc", 1)
    tao_don("LC", "MD", c["gio"]["LC"] - 3 * h, chuyen=c, cuoc=85000, kg=5,
            lien_he=[goi_truot(c["gio"]["MD"] + h / 2)], mo_ta="Tới tối qua, chưa báo được người nhận")
    c = chuyen_ngay("TM", "nguoc", 3)
    tao_don("SP", "MD", c["gio"]["SP"] - 2 * h, chuyen=c, cuoc=130000, kg=10, lien_he=[goi_ok(c["gio"]["MD"] + h)],
            mo_ta="Chờ lấy, đã báo — thử GIAO HÀNG")
    c = chuyen_ngay("T1", "nguoc", 10)
    tao_don("LC", "MD", c["gio"]["LC"] - 2 * h, chuyen=c, cuoc=75000, kg=3, lien_he=[goi_ok(c["gio"]["MD"] + h)],
            mo_ta="Chờ quá 7 ngày, đã từng báo người nhận")
    c = chuyen_ngay("TM", "xuoi", 2)
    tao_don("MD", "SP", c["gio"]["MD"] - 4 * h, chuyen=c, cod=True, cuoc=95000, kg=6, lien_he=[goi_ok(c["gio"]["SP"] + h)],
            mo_ta="Chờ lấy, đã báo, COD 95.000đ")
    c = chuyen_ngay("TM", "xuoi", 4)
    tao_don("MD", "YB", c["gio"]["MD"] - 3 * h, chuyen=c, cod=True, cuoc=65000, kg=4, lien_he=[goi_ok(c["gio"]["YB"] + h)],
            mo_ta="Chờ lấy 4 ngày, đã báo, COD 65.000đ")

    # ===== Đã giao hôm nay (đối soát tiền trong ngày)
    c = chuyen_ngay("T1", "xuoi", 2)
    tao_don("MD", "LC", c["gio"]["MD"] - 3 * h, chuyen=c, cod=True, cuoc=75000, kg=5,
            lien_he=[goi_ok(c["gio"]["LC"] + h)], giao=phut(-300), mo_ta="Đã giao hôm nay, thu COD 75.000đ")
    c = chuyen_ngay("T1", "nguoc", 2)
    tao_don("LC", "MD", c["gio"]["LC"] - 3 * h, chuyen=c, cod=True, cuoc=90000, kg=6,
            lien_he=[goi_ok(c["gio"]["MD"] + h)], giao=phut(-240), mo_ta="Đã giao hôm nay, thu COD 90.000đ")

    # ===== Lịch sử 14 ngày cho thống kê / biểu đồ (đã giao, vài đơn hủy)
    so_lich_su = 0
    for ngay_truoc in range(2, 15):
        for _ in range(rng.randint(4, 7)):
            if rng.random() < 0.65:
                gui, nhan = "MD", rng.choices(["LC", "SP", "YB"], weights=[5, 3, 2])[0]
            else:
                # Không có cặp nội khu vực (LC ↔ SP cùng khu vực Lào Cai) — chỉ gửi khác khu vực
                gui, nhan = rng.choice([("LC", "MD"), ("SP", "MD"), ("YB", "MD"), ("SP", "YB"), ("LC", "YB")])
            tuyen_kh = rng.choice(tuyen_qua(gui, nhan))
            c = chuyen_ngay(tuyen_kh, chieu_tren(tuyen_kh, gui, nhan), ngay_truoc)
            kg = rng.choice([0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20])
            cuoc = max(30000, round((30000 + kg * 7000) / 5000) * 5000)
            tao = c["gio"][gui] - timedelta(minutes=rng.randint(40, 1100))
            loai = rng.choices(list(LOAI), weights=[6, 2, 1, 2])[0]
            if rng.random() < 0.07:
                tao_don(gui, nhan, tao, tuyen_kh=tuyen_kh, cuoc=cuoc, kg=kg, loai=loai, cod=rng.random() < 0.4,
                        huy=(rng.choice(["khach_doi_y", "hang_khong_du_dieu_kien"]), None, tao + timedelta(minutes=rng.randint(10, 120))))
            else:
                den = c["gio"][nhan]
                goi = [goi_ok(den + timedelta(minutes=rng.randint(10, 120)))]
                if rng.random() < 0.2:
                    goi.insert(0, goi_truot(den + timedelta(minutes=5)))
                giao = min(den + timedelta(minutes=rng.randint(60, 2200)), bay_gio - timedelta(minutes=90))
                tao_don(gui, nhan, tao, chuyen=c, cuoc=cuoc, kg=kg, loai=loai, cod=rng.random() < 0.4, lien_he=goi, giao=giao)
            so_lich_su += 1

    conn.commit()
    cur.execute("SELECT trang_thai, count(*) FROM don_hang WHERE nhan_vien_gui_id = ANY(%s::uuid[]) GROUP BY 1 ORDER BY 1", (nv_demo,))
    thong_ke = cur.fetchall()
    release_connection(conn)

    print("Đã tạo dữ liệu demo gửi hàng.")
    print("Tài khoản:")
    for vp, (email, ho_ten, _) in NHAN_VIEN.items():
        print(f"  {ten_diem[vp]:<36} {email:<32} / {MAT_KHAU_GUI_HANG}  ({ho_ten})")
    print(f"  {'Phụ xe xe ' + XE['X1'][0]:<36} {EMAIL_PHU_XE:<32} / {MAT_KHAU_PHU_XE}")
    print(f"Đơn demo theo trạng thái ({so_lich_su} đơn lịch sử 14 ngày): " + ", ".join(f"{t} {n}" for t, n in thong_ke))
    for vp, ds in noi_bat.items():
        print(f"\n== {ten_diem[vp]} ==")
        for ma, trang_thai, mo_ta in ds:
            print(f"  {ma}  [{trang_thai}]  {mo_ta}")


if __name__ == "__main__":
    main()
