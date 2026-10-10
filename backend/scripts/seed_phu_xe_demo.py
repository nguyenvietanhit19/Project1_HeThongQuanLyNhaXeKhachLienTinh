"""Tạo dữ liệu mẫu để TEST phần phụ xe trên DB LOCAL (không dùng cho production).

Chạy trong container backend (sau khi đã `yoyo apply` migration):

    docker compose exec backend python scripts/seed_phu_xe_demo.py                       # mặc định: chuyến xuôi VỪA xuất phát, xe còn ở A
    docker compose exec backend python scripts/seed_phu_xe_demo.py --sap-xuat-phat 3     # chuyến xuôi chưa chạy, xuất phát sau 3 phút
    docker compose exec backend python scripts/seed_phu_xe_demo.py --dang-chay           # chuyến xuôi đang chạy dở, xe đã tới B

Chạy lại bao nhiêu lần cũng được: hạ tầng (khu vực, điểm, tuyến, xe, tài khoản) được giữ, còn
chuyến/vé/đơn hàng demo được xóa và tạo mới.

Tài khoản (đăng nhập tại /nhan-vien/dang-nhap.html hoặc POST /auth/dang-nhap):
    Phụ xe          phuxe.demo@nhaxe-demo.vn       / PhuXe@123
    Khách           khachhang.demo@nhaxe-demo.vn   / KhachHang@123   (có vé trên các chuyến, để thử WebSocket)
    NV gửi hàng A   guihang.demo@nhaxe-demo.vn     / KhachHang@123   (văn phòng A — nhận báo hàng hư hỏng khi đơn chưa lên xe)
    NV gửi hàng D   guihang.d.demo@nhaxe-demo.vn   / KhachHang@123   (văn phòng D — nhận nhắc "gọi báo người nhận" khi phụ xe dỡ hàng tại D)
    Điều độ viên    dieudo.demo@nhaxe-demo.vn      / KhachHang@123   (văn phòng A — nhận cảnh báo khi phụ xe báo sự cố, UC-17)

Tuyến demo: 4 điểm A → B → C → D (A, D là văn phòng; B, C là điểm dừng), mỗi chặng 100 phút (cả tuyến 5 tiếng).
Xe 34 chỗ chạy luôn phiên xuôi/ngược, các chuyến cách nhau 8 tiếng (xe kịp nghỉ + quay đầu), mỗi chuyến 7–30 khách,
khách có tên/SĐT/chặng đi khác nhau, vài khách chưa trả tiền (giữ chỗ trả tại quầy) hoặc không đến.
Chuyến chưa khởi hành chỉ xác nhận xuất phát được khi ĐÚNG giờ (UC-15), không xuất phát sớm.

    Lịch (chuyến mốc 0 là chuyến xuôi: mặc định vừa xuất phát 10 phút trước, xe còn ở A; --dang-chay: xe đã tới B):
        -8h  NGƯỢC  đã hoàn thành (có lịch sử/thống kê)
         0   XUÔI   ĐANG CHẠY — xe vừa tới B sớm hơn dự kiến; khách ở A đã lên xe, khách ở B/C đang chờ đón
        +8h  NGƯỢC  chưa khởi hành (chưa tới giờ → không xuất phát sớm được)
        +16h XUÔI, +24h NGƯỢC  chưa khởi hành
    Chế độ --sap-xuat-phat N: chuyến XUÔI ở mốc 0 chưa khởi hành, xuất phát sau N phút (thử xác nhận xuất phát đúng giờ).

LƯU Ý khi thử: job no-show (UC-14, mỗi phút 1 lần) đánh dấu "không đến" mọi vé chưa lên xe khi tới mốc
"giờ dự kiến tại điểm đón − 5 phút". Khách đón tại điểm xuất phát (A) sẽ bị đánh dấu TRƯỚC giờ xuất phát 5 phút, trong khi xe chỉ
xuất phát được từ đúng giờ → script đánh dấu riêng các vé còn chờ lên ở A (gio_hoan_tac) để job bỏ qua, nhờ đó test lên xe tại A được.
Ở chế độ --dang-chay, xe được đặt tới B SỚM ~35 phút so với dự kiến để khách ở B còn thời gian lên xe.
"""

import argparse
from datetime import timedelta, timezone
import json
import os
import random
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.services.mat_khau_service import _pwd_context  # noqa: E402

MAT_KHAU_PHU_XE = "PhuXe@123"
MAT_KHAU_KHACH = "KhachHang@123"
EMAIL_PHU_XE = "phuxe.demo@nhaxe-demo.vn"
EMAIL_KHACH = "khachhang.demo@nhaxe-demo.vn"
EMAIL_NV_GUI_HANG = "guihang.demo@nhaxe-demo.vn"
EMAIL_NV_GUI_HANG_D = "guihang.d.demo@nhaxe-demo.vn"
EMAIL_DIEU_DO = "dieudo.demo@nhaxe-demo.vn"
TEN_TUYEN = "DEMO Hà Nội - Sapa"
BIEN_SO = "29B-DEMO01"
TEN_LOAI_XE = "DEMO Giường nằm 34 chỗ"
PHUT_MOI_CHANG = 100
PHUT_GIUA_CHUYEN = 8 * 60  # các chuyến cách nhau 8 tiếng (> 6 tiếng)

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
DEM = ["Văn", "Thị", "Đức", "Minh", "Quốc", "Thanh", "Hữu", "Ngọc", "Gia", "Thu", "Anh", "Hoài", "Bảo", "Khánh", "Tuấn", "Phương"]
TEN = ["An", "Bình", "Cường", "Dũng", "Em", "Giang", "Hà", "Hải", "Hạnh", "Hiếu", "Hùng", "Huy", "Khôi", "Lan", "Linh", "Long",
       "Mai", "Nam", "Nga", "Phúc", "Quân", "Sơn", "Thảo", "Trang", "Trung", "Tú", "Vân", "Yến", "Đạt", "Hương"]
DAU_SO = ["090", "091", "093", "094", "096", "097", "098", "032", "033", "035", "036", "037", "038", "039", "070", "076", "077", "078", "079", "081", "082", "083", "084", "085", "088"]
# Chặng (vị trí trong hướng đi: 0..3) khách hay đi — cả tuyến chiếm nhiều nhất
CAC_CHANG = [(0, 3), (0, 2), (0, 1), (1, 3), (1, 2), (2, 3)]
TRONG_SO = [35, 15, 12, 15, 8, 15]


def _chi_chay_tren_may_local() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo dữ liệu demo cho phụ xe")
    parser.add_argument("--sap-xuat-phat", type=int, default=None, metavar="PHUT",
                        help="chuyến xuôi chưa khởi hành, xuất phát sau PHUT phút — test xác nhận xuất phát đúng giờ")
    parser.add_argument("--dang-chay", action="store_true", help="chuyến xuôi đang chạy dở, xe ĐÃ tới B (test xuống xe/dỡ hàng ở B)")
    args = parser.parse_args()
    # Mặc định: chuyến xuôi VỪA xuất phát 10 phút trước, xe còn ở A → thử lên xe ở A, xác nhận tới B, báo sự cố giữa đường...
    args.vua_xuat_phat = args.sap_xuat_phat is None and not args.dang_chay
    _chi_chay_tren_may_local()
    conn = get_connection()
    cur = conn.cursor()

    def mot(sql, args=()):
        cur.execute(sql, args)
        row = cur.fetchone()
        return row[0] if row else None

    def lay_hoac_tao(sql_tim, args_tim, sql_tao, args_tao):
        return mot(sql_tim, args_tim) or mot(sql_tao, args_tao)

    # ---------- hạ tầng (giữ nguyên giữa các lần chạy)
    khu_vuc = lay_hoac_tao(
        "SELECT id FROM khu_vuc WHERE ten = %s", ("DEMO Khu vực",),
        "INSERT INTO khu_vuc (ten, tinh_thanh, ma) VALUES (%s, 'Hà Nội', '') RETURNING id", ("DEMO Khu vực",),
    )
    diem = {}
    for ky_hieu, loai in (("A", "van_phong"), ("B", "diem_dung"), ("C", "diem_dung"), ("D", "van_phong")):
        ten = f"DEMO Điểm {ky_hieu}"
        diem[ky_hieu] = lay_hoac_tao(
            "SELECT id FROM diem_don_tra WHERE ten = %s", (ten,),
            "INSERT INTO diem_don_tra (khu_vuc_id, ten, dia_chi, loai, ma) VALUES (%s, %s, 'Địa chỉ demo', %s, '') RETURNING id",
            (khu_vuc, ten, loai),
        )
    tuyen = lay_hoac_tao(
        "SELECT id FROM tuyen WHERE ten = %s", (TEN_TUYEN,),
        "INSERT INTO tuyen (ten, ma) VALUES (%s, '') RETURNING id", (TEN_TUYEN,),
    )
    if not mot("SELECT COUNT(*) FROM tuyen_diem_don_tra WHERE tuyen_id = %s", (tuyen,)):
        for thu_tu, ky_hieu in enumerate("ABCD", start=1):
            cur.execute(
                "INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut) VALUES (%s, %s, %s, %s)",
                (tuyen, diem[ky_hieu], thu_tu, (thu_tu - 1) * PHUT_MOI_CHANG),
            )
    # Tuyến đã có từ lần seed trước (90'/chặng) → chỉnh về 100'/chặng cho sát thực tế
    cur.execute("UPDATE tuyen_diem_don_tra SET thoi_gian_du_kien_phut = (thu_tu - 1) * %s WHERE tuyen_id = %s", (PHUT_MOI_CHANG, tuyen))
    ghe = [{"ma_ghe": f"{tang}{i}", "tang": 1 if tang == "A" else 2, "x": i * 40, "y": 0 if tang == "A" else 60}
           for tang in "AB" for i in range(1, 18)]
    loai_xe = lay_hoac_tao(
        "SELECT id FROM loai_xe WHERE ten = %s", (TEN_LOAI_XE,),
        "INSERT INTO loai_xe (ten, he_so_gia, so_do_ghe, ma) VALUES (%s, 1, %s, '') RETURNING id",
        (TEN_LOAI_XE, json.dumps(ghe)),
    )
    xe = lay_hoac_tao(
        "SELECT id FROM xe WHERE bien_so = %s", (BIEN_SO,),
        "INSERT INTO xe (bien_so, loai_xe_id, diem_goc_id, tuyen_id) VALUES (%s, %s, %s, %s) RETURNING id",
        (BIEN_SO, loai_xe, diem["A"], tuyen),
    )
    cur.execute("UPDATE xe SET loai_xe_id = %s WHERE id = %s", (loai_xe, xe))

    def tai_khoan(email, ho_ten, sdt, vai_tro, mat_khau):
        return lay_hoac_tao(
            "SELECT id FROM nguoi_dung WHERE email = %s", (email,),
            """INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan)
               VALUES (%s, %s, %s, %s, %s, true) RETURNING id""",
            (email, _pwd_context.hash(mat_khau), ho_ten, sdt, vai_tro),
        )

    phu_xe_nd = tai_khoan(EMAIL_PHU_XE, "Phụ Xe Demo", "0900000001", "phu_xe", MAT_KHAU_PHU_XE)
    khach_nd = tai_khoan(EMAIL_KHACH, "Khách Hàng Demo", "0900000002", "khach_hang", MAT_KHAU_KHACH)
    nv_gui = tai_khoan(EMAIL_NV_GUI_HANG, "Nhân Viên Gửi Hàng Demo", "0900000003", "nhan_vien_gui_hang", MAT_KHAU_KHACH)
    nv_gui_d = tai_khoan(EMAIL_NV_GUI_HANG_D, "Nhân Viên Gửi Hàng D", "0900000004", "nhan_vien_gui_hang", MAT_KHAU_KHACH)
    dieu_do = tai_khoan(EMAIL_DIEU_DO, "Điều Độ Viên Demo", "0900000005", "dieu_do_vien", MAT_KHAU_KHACH)
    # Văn phòng phụ trách (ho_so_can_bo_diem) — nơi nhận thông báo của phụ xe (UC-17, UC-27, UC-28)
    for nguoi_dung_id, ky_hieu in ((nv_gui, "A"), (nv_gui_d, "D"), (dieu_do, "A")):
        cur.execute(
            """INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id) VALUES (%s, %s)
               ON CONFLICT (nguoi_dung_id) DO UPDATE SET van_phong_id = EXCLUDED.van_phong_id""",
            (nguoi_dung_id, diem[ky_hieu]),
        )
    # Luôn đặt lại mật khẩu để lần chạy nào cũng đăng nhập được với mật khẩu ghi ở đầu file
    cur.execute("UPDATE nguoi_dung SET mat_khau = %s, da_xac_nhan = true, dang_hoat_dong = true WHERE id = %s",
                (_pwd_context.hash(MAT_KHAU_PHU_XE), phu_xe_nd))
    cur.execute(
        "UPDATE nguoi_dung SET mat_khau = %s, da_xac_nhan = true, dang_hoat_dong = true WHERE id = ANY(%s::uuid[])",
        (_pwd_context.hash(MAT_KHAU_KHACH), [khach_nd, nv_gui, nv_gui_d, dieu_do]),
    )
    nhan_su = lay_hoac_tao(
        "SELECT id FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s", (phu_xe_nd,),
        "INSERT INTO nhan_su_van_hanh (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id) VALUES ('Phụ Xe Demo', '0900000001', 'phu_xe', %s) RETURNING id",
        (phu_xe_nd,),
    )
    if not mot("SELECT 1 FROM xe_nhan_su WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe, nhan_su)):
        cur.execute("INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh')", (xe, nhan_su))
    # Đề phòng lần test trước đã chuyển biên chế/hồ sơ sang tạm nghỉ
    cur.execute("UPDATE xe_nhan_su SET trang_thai = 'dang_hoat_dong' WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe, nhan_su))

    # ---------- dữ liệu chạy thử: xóa bản cũ rồi tạo mới
    cur.execute("DELETE FROM thong_bao WHERE nguoi_nhan_id = ANY(%s::uuid[])", ([phu_xe_nd, khach_nd, nv_gui, nv_gui_d, dieu_do],))
    cur.execute("DELETE FROM bao_cao_su_co_hang WHERE don_hang_id IN (SELECT id FROM don_hang WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM don_hang WHERE tuyen_id = %s", (tuyen,))
    cur.execute("DELETE FROM thong_bao WHERE ve_id IN (SELECT v.id FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id WHERE c.tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM ve WHERE chuyen_id IN (SELECT id FROM chuyen_xe WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM lich_su_diem_dung_chuyen WHERE chuyen_id IN (SELECT id FROM chuyen_xe WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM chuyen_xe WHERE tuyen_id = %s", (tuyen,))

    now_db = mot("SELECT now()")  # dùng đồng hồ của DB (job no-show và API xuất phát cũng dùng now() của DB)
    rng = random.Random(20261010)  # cố định → mỗi lần seed ra cùng bộ khách, dễ đối chiếu

    def phut(so_phut):
        return now_db + timedelta(minutes=so_phut)

    def tao_chuyen(chieu, gio):
        return mot(
            """INSERT INTO chuyen_xe (tuyen_id, xe_id, loai_xe_id, gio_khoi_hanh, chieu, ma)
               VALUES (%s, %s, %s, %s, %s, '') RETURNING id""",
            (tuyen, xe, loai_xe, gio, chieu),
        )

    def thu_tu_diem(chieu):
        """Các điểm theo hướng đi: xuôi A→D, ngược D→A."""
        return list("ABCD") if chieu == "xuoi" else list("DCBA")

    # ---- Lịch chuyến: mỗi chuyến cách nhau 8 tiếng; mốc 0 là chuyến xuôi đang chạy (hoặc sắp xuất phát)
    moc0 = args.sap_xuat_phat if args.sap_xuat_phat is not None else (-10 if args.vua_xuat_phat else -65)
    lich = [  # (số chuyến lệch so với mốc 0, chiều, kiểu, số khách)
        (-1, "nguoc", "hoan_thanh", 22),
        (0, "xuoi", "chua_khoi_hanh" if args.sap_xuat_phat is not None else "dang_chay", 26),
        (1, "nguoc", "chua_khoi_hanh", 14),
        (2, "xuoi", "chua_khoi_hanh", 7),
        (3, "nguoc", "chua_khoi_hanh", 30),
    ]

    seq = {"ma": 0}

    def sdt_ngau_nhien():
        return rng.choice(DAU_SO) + "".join(str(rng.randint(0, 9)) for _ in range(7))

    def ten_ngau_nhien():
        return f"{rng.choice(HO)} {rng.choice(DEM)} {rng.choice(TEN)}"

    def tao_ve(chuyen, so_ghe, don, tra, trang_thai, gio_di, gio_den, khach_id=None, tai_quay=False, mien_job=False):
        """gio_di/gio_den: giờ lên/xuống thực tế (chỉ dùng khi vé đã lên/xuống)."""
        hops = abs("ABCD".index(tra) - "ABCD".index(don))
        da_tra = trang_thai in ("da_thanh_toan", "da_len_xe", "da_xuong_xe")
        ten, sdt = (None, None) if khach_id else (ten_ngau_nhien(), sdt_ngau_nhien())
        seq["ma"] += 1
        cur.execute(
            """INSERT INTO ve (chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                               gia, ma_dat_cho, loai_hinh_thanh_toan, phuong_thuc_thanh_toan, trang_thai,
                               gio_thanh_toan, gio_len_xe, gio_xuong_xe, gio_hoan_tac)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (chuyen, so_ghe, diem[don], diem[tra], khach_id, ten, sdt, 120000 * hops, f"DEMO{seq['ma']:04d}",
             "thanh_toan_tai_quay" if tai_quay else "thanh_toan_ngay",
             rng.choice(["tien_mat", "chuyen_khoan"]) if da_tra else None, trang_thai,
             phut(-600) if da_tra else None,
             gio_di if trang_thai in ("da_len_xe", "da_xuong_xe") else None,
             gio_den if trang_thai == "da_xuong_xe" else None,
             phut(0) if mien_job else None),
        )

    ds_chuyen = {}
    for k, chieu, kieu, so_khach in lich:
        gio_khoi_hanh_phut = moc0 + k * PHUT_GIUA_CHUYEN
        c = tao_chuyen(chieu, phut(gio_khoi_hanh_phut))
        ds_chuyen[k] = (c, chieu, kieu, gio_khoi_hanh_phut)
        thu_tu = thu_tu_diem(chieu)  # ky hieu diem theo huong di

        if kieu in ("dang_chay", "hoan_thanh"):
            cur.execute(
                "UPDATE chuyen_xe SET trang_thai = %s, gio_xac_nhan_xuat_phat = %s WHERE id = %s",
                (kieu, phut(gio_khoi_hanh_phut + rng.randint(1, 4)), c),
            )

        # Điểm xe đã tới (không tính điểm xuất phát): hoàn thành → tất cả; đang chạy → chỉ B (xe tới SỚM ~35 phút so với dự kiến)
        # Chuyến đang chạy chỉ có điểm B (vị trí 1) vì đang xuôi; chuyến đã hoàn thành đi hết hướng ngược.
        if kieu == "hoan_thanh":
            for vi_tri in range(1, 4):
                cur.execute(
                    "INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id, gio_thuc_te) VALUES (%s, %s, %s)",
                    (c, diem[thu_tu[vi_tri]], phut(gio_khoi_hanh_phut + vi_tri * PHUT_MOI_CHANG + rng.randint(-5, 10))),
                )
            cur.execute("UPDATE chuyen_xe SET gio_hoan_thanh = %s WHERE id = %s", (phut(gio_khoi_hanh_phut + 3 * PHUT_MOI_CHANG + 8), c))
        elif kieu == "dang_chay" and not args.vua_xuat_phat:
            cur.execute(
                "INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id, gio_thuc_te) VALUES (%s, %s, %s)",
                (c, diem[thu_tu[1]], phut(-5)),
            )

        # ---- hành khách: ghế khác nhau, chặng theo trọng số, tên/SĐT ngẫu nhiên nhưng cố định giữa các lần seed
        so_ghe_list = rng.sample([g["ma_ghe"] for g in ghe], so_khach)
        co_khach_demo = False
        for so_ghe in so_ghe_list:
            a_vt, b_vt = rng.choices(CAC_CHANG, weights=TRONG_SO)[0]
            don, tra = thu_tu[a_vt], thu_tu[b_vt]
            gio_don = gio_khoi_hanh_phut + a_vt * PHUT_MOI_CHANG
            gio_tra = gio_khoi_hanh_phut + b_vt * PHUT_MOI_CHANG
            tai_quay = rng.random() < 0.12
            khach_id = None
            if not co_khach_demo and a_vt >= 1 and kieu != "hoan_thanh":
                khach_id, co_khach_demo, tai_quay = khach_nd, True, False  # khách demo: đón ở điểm giữa → nhận ETA qua WebSocket

            if kieu == "hoan_thanh":
                trang_thai = "khong_den" if rng.random() < 0.06 else "da_xuong_xe"
                if trang_thai == "da_xuong_xe":
                    tai_quay = False
            elif kieu == "dang_chay":
                if a_vt == 0 and args.vua_xuat_phat:  # vừa xuất phát: ~nửa khách ở A đã lên, nửa còn đang lên (thử "Lên xe")
                    trang_thai = "da_len_xe" if rng.random() < 0.55 else ("giu_cho" if tai_quay else "da_thanh_toan")
                    tai_quay = tai_quay and trang_thai == "giu_cho"
                elif a_vt == 0:  # đã lên xe từ điểm xuất phát; ~1/12 khách không tới
                    trang_thai = "khong_den" if rng.random() < 0.09 else "da_len_xe"
                    tai_quay = False if trang_thai == "da_len_xe" else tai_quay
                else:  # khách ở B/C còn chờ đón
                    trang_thai = "giu_cho" if tai_quay else "da_thanh_toan"
            else:
                trang_thai = "giu_cho" if tai_quay else "da_thanh_toan"
            tao_ve(c, so_ghe, don, tra, trang_thai, phut(gio_don + rng.randint(-8, 0)), phut(gio_tra + rng.randint(-5, 10)), khach_id,
                   tai_quay and trang_thai in ("giu_cho", "khong_den"),
                   # Khách đón tại điểm xuất phát của chuyến sắp chạy: job no-show sẽ đánh dấu họ trước giờ xuất phát 5 phút
                   # (phụ xe chỉ xuất phát được từ đúng giờ) → miễn job để demo còn cho lên xe được
                   mien_job=(k == 0 and a_vt == 0 and trang_thai in ("da_thanh_toan", "giu_cho") and kieu in ("chua_khoi_hanh", "dang_chay")))

    c_nguoc_ht, c_dang, c_nguoc_sau = ds_chuyen[-1][0], ds_chuyen[0][0], ds_chuyen[1][0]
    chuyen_dang_chay = ds_chuyen[0][2] == "dang_chay"

    loai_hang = mot("SELECT id FROM loai_hang WHERE la_hang_cam = false ORDER BY ten LIMIT 1")

    def tao_don(ma, gui, nhan, nguoi_nhan, kg, trang_thai="cho_van_chuyen", chuyen=None):
        cur.execute(
            """INSERT INTO don_hang (ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, can_nang_kg, loai_hang_id, gia_cuoc,
                                     ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan, phuong_thuc_thanh_toan, nhan_vien_gui_id,
                                     da_thu_tien, thoi_gian_thu, nhan_vien_thu_id, trang_thai, chuyen_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'nguoi_gui_tra_truoc', %s,
                       true, now(), %s, %s, %s)""",
            (ma, tuyen, diem[gui], diem[nhan], kg, loai_hang, 30000 + 10000 * kg, ten_ngau_nhien(), sdt_ngau_nhien(),
             nguoi_nhan, sdt_ngau_nhien(), nv_gui, nv_gui, trang_thai, chuyen),
        )

    # Hàng đang chờ chất (chưa gắn chuyến): chiều xuôi chất được tại A hoặc B; chiều ngược chất tại D
    tao_don("DEMO-H1", "A", "D", "Cửa hàng An Phát", 4)
    tao_don("DEMO-H2", "A", "C", "Chị Mai", 2)
    tao_don("DEMO-H3", "D", "A", "Anh Tuấn", 3)
    tao_don("DEMO-H4", "D", "B", "Quán Cà Phê Sapa", 5)
    tao_don("DEMO-H9", "B", "D", "Chị Lan", 2)
    tao_don("DEMO-H10", "B", "C", "Quán Bà Tư", 7)
    if chuyen_dang_chay:
        # Đơn đã nằm trên chuyến đang chạy (xe đang ở B): H6/H8 nhận ở B → dỡ được ngay; H5/H7 nhận ở D/C → chưa dỡ được
        tao_don("DEMO-H5", "A", "D", "Công ty Minh Long", 6, trang_thai="da_len_xe", chuyen=c_dang)
        tao_don("DEMO-H6", "A", "B", "Cô Hạnh", 1, trang_thai="da_len_xe", chuyen=c_dang)
        tao_don("DEMO-H7", "A", "C", "Cửa hàng Thu Hà", 3, trang_thai="da_len_xe", chuyen=c_dang)
        tao_don("DEMO-H8", "A", "B", "Anh Phúc", 2, trang_thai="da_len_xe", chuyen=c_dang)

    conn.commit()
    release_connection(conn)

    print("Đã tạo dữ liệu demo.")
    print(f"  Phụ xe        : {EMAIL_PHU_XE} / {MAT_KHAU_PHU_XE}")
    print(f"  Khách         : {EMAIL_KHACH} / {MAT_KHAU_KHACH}")
    print(f"  NV gửi hàng A : {EMAIL_NV_GUI_HANG} / {MAT_KHAU_KHACH}")
    print(f"  NV gửi hàng D : {EMAIL_NV_GUI_HANG_D} / {MAT_KHAU_KHACH}")
    print(f"  Điều độ viên  : {EMAIL_DIEU_DO} / {MAT_KHAU_KHACH}")
    print(f"  Xe {BIEN_SO} ({TEN_LOAI_XE}) — tuyến '{TEN_TUYEN}' — {len(lich)} chuyến, cách nhau {PHUT_GIUA_CHUYEN // 60} tiếng:")
    for k, (c, chieu, kieu, phut_kh) in sorted(ds_chuyen.items()):
        gio = (now_db + timedelta(minutes=phut_kh)).astimezone(timezone(timedelta(hours=7))).strftime("%H:%M %d/%m")
        print(f"    {gio}  {chieu:5}  {kieu}")


if __name__ == "__main__":
    main()
