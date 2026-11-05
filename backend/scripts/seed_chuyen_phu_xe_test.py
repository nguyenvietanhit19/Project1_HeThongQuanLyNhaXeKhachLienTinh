"""Tạo chuyến xe + vé + đơn hàng cho tài khoản phụ xe TEST, dựa trên dữ liệu admin đã tạo (tuyến T001, loại xe LX001).

Dùng khi chưa có role điều độ viên để xếp chuyến. Chạy trong container backend:

    docker-compose exec backend python scripts/seed_chuyen_phu_xe_test.py                    # chuyến xuôi VỪA xuất phát 10 phút, xe còn ở điểm đầu
    docker-compose exec backend python scripts/seed_chuyen_phu_xe_test.py --sap-xuat-phat 3  # chuyến xuôi chưa chạy, xuất phát sau 3 phút

Chạy lại bao nhiêu lần cũng được: xe/biên chế giữ nguyên, chuyến/vé/đơn hàng của xe này được xóa và tạo mới.
Chỉ chạy trên DB local.
"""

import argparse
from datetime import timedelta, timezone
import os
import random
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.repositories import ma_repository  # noqa: E402
from app.utils import ma_tu_sinh  # noqa: E402

EMAIL_PHU_XE = "phuxe.test@nhaxekhach.com"
EMAIL_NV_GUI_HANG = "guihang.demo@nhaxe-demo.vn"  # có sẵn nếu đã chạy seed_phu_xe_demo.py; không có thì bỏ qua đơn hàng
MA_TUYEN = "T001"
MA_LOAI_XE = "LX001"
BIEN_SO = "24B3 - 88888"
PHUT_GIUA_CHUYEN = 12 * 60  # tuyến chạy ~6h20, các chuyến cách nhau 12 tiếng

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
DEM = ["Văn", "Thị", "Đức", "Minh", "Quốc", "Thanh", "Hữu", "Ngọc", "Gia", "Thu", "Anh", "Bảo"]
TEN = ["An", "Bình", "Cường", "Dũng", "Giang", "Hà", "Hải", "Hạnh", "Hiếu", "Hùng", "Huy", "Lan", "Linh", "Long", "Mai", "Nam"]
DAU_SO = ["090", "091", "093", "094", "096", "097", "098", "032", "033", "035", "036", "037", "038", "039"]


def _chi_chay_tren_may_local() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo chuyến cho phụ xe test từ dữ liệu admin")
    parser.add_argument("--sap-xuat-phat", type=float, default=None, metavar="PHUT",
                        help="chuyến xuôi chưa khởi hành, xuất phát sau PHUT phút")
    parser.add_argument("--luc", metavar="HH:MM",
                        help="chuyến xuôi chưa khởi hành, xuất phát đúng lúc HH:MM giờ Việt Nam (gần nhất sau bây giờ)")
    args = parser.parse_args()
    _chi_chay_tren_may_local()
    conn = get_connection()
    cur = conn.cursor()

    def mot(sql, params=()):
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None

    # ---------- đọc dữ liệu admin
    tuyen = mot("SELECT id FROM tuyen WHERE ma = %s", (MA_TUYEN,))
    loai_xe = mot("SELECT id FROM loai_xe WHERE ma = %s", (MA_LOAI_XE,))
    if not tuyen or not loai_xe:
        sys.exit(f"Không thấy tuyến {MA_TUYEN} hoặc loại xe {MA_LOAI_XE} — admin cần tạo trước.")
    cur.execute(
        "SELECT diem_don_tra_id, thoi_gian_du_kien_phut FROM tuyen_diem_don_tra WHERE tuyen_id = %s ORDER BY thu_tu", (tuyen,),
    )
    cac_diem = cur.fetchall()  # theo chiều xuôi
    diem_xuoi = [d for d, _ in cac_diem]
    moc_xuoi = [p for _, p in cac_diem]
    n = len(diem_xuoi)
    # Xe liên tỉnh: khách đón ở văn phòng (đúng luật đặt vé) và trả ở điểm thuộc TỈNH KHÁC — không có vé đón/trả cùng tỉnh
    cur.execute(
        "SELECT d.id, d.loai, kv.tinh_thanh FROM diem_don_tra d JOIN khu_vuc kv ON kv.id = d.khu_vuc_id WHERE d.id = ANY(%s::uuid[])",
        (diem_xuoi,),
    )
    info = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    loai_diem = [info[d][0] for d in diem_xuoi]
    tinh_diem = [info[d][1] for d in diem_xuoi]
    tong_phut = moc_xuoi[-1]
    ma_tuyen = mot("SELECT ma FROM tuyen WHERE id = %s", (tuyen,))
    ma_loai_xe = mot("SELECT ma FROM loai_xe WHERE id = %s", (loai_xe,))
    so_do_ghe = mot("SELECT so_do_ghe FROM loai_xe WHERE id = %s", (loai_xe,))
    ds_ghe = [g["ma_ghe"] for g in (so_do_ghe if isinstance(so_do_ghe, list) else __import__("json").loads(so_do_ghe))]
    gia_goc = mot("SELECT MAX(gia_goc) FROM gia_ve") or 300000  # gia_ve không còn gắn tuyen_id (giá theo bộ giá + khu vực)

    phu_xe_nd = mot("SELECT id FROM nguoi_dung WHERE email = %s", (EMAIL_PHU_XE,))
    nhan_su = mot("SELECT id FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s", (phu_xe_nd,))
    if not nhan_su:
        sys.exit(f"Không thấy hồ sơ nhân sự của {EMAIL_PHU_XE}.")

    # ---------- xe riêng cho phụ xe test + biên chế cố định
    xe = mot("SELECT id FROM xe WHERE bien_so = %s", (BIEN_SO,)) or mot(
        "INSERT INTO xe (bien_so, loai_xe_id, diem_goc_id, tuyen_id) VALUES (%s, %s, %s, %s) RETURNING id",
        (BIEN_SO, loai_xe, diem_xuoi[0], tuyen),
    )
    # Mỗi phụ xe chỉ gắn 1 xe cố định: gỡ biên chế cũ ở xe khác (nếu có) rồi gắn vào xe này
    cur.execute(
        "DELETE FROM xe_nhan_su WHERE nhan_su_van_hanh_id = %s AND loai = 'co_dinh' AND xe_id <> %s", (nhan_su, xe),
    )
    if not mot("SELECT 1 FROM xe_nhan_su WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe, nhan_su)):
        cur.execute("INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh')", (xe, nhan_su))
    cur.execute("UPDATE xe_nhan_su SET trang_thai = 'dang_hoat_dong', ngay_ket_thuc = NULL WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe, nhan_su))

    # ---------- xóa chuyến/vé/đơn cũ của xe này
    chuyen_cu = "SELECT id FROM chuyen_xe WHERE xe_id = %s"
    cur.execute(f"DELETE FROM bao_cao_su_co_hang WHERE don_hang_id IN (SELECT id FROM don_hang WHERE chuyen_id IN ({chuyen_cu}) OR ma_van_don LIKE 'TEST-%%')", (xe,))
    cur.execute(f"DELETE FROM don_hang WHERE chuyen_id IN ({chuyen_cu}) OR ma_van_don LIKE 'TEST-%%'", (xe,))
    cur.execute(f"DELETE FROM thong_bao WHERE ve_id IN (SELECT id FROM ve WHERE chuyen_id IN ({chuyen_cu}))", (xe,))
    cur.execute(f"DELETE FROM ve WHERE chuyen_id IN ({chuyen_cu})", (xe,))
    cur.execute(f"DELETE FROM lich_su_diem_dung_chuyen WHERE chuyen_id IN ({chuyen_cu})", (xe,))
    cur.execute("DELETE FROM chuyen_xe WHERE xe_id = %s", (xe,))

    now_db = mot("SELECT now()")
    rng = random.Random(20261013)

    if args.luc:
        gio, phut_le = (int(x) for x in args.luc.split(":"))
        gio_vn = now_db.astimezone(timezone(timedelta(hours=7)))
        dich = gio_vn.replace(hour=gio, minute=phut_le, second=0, microsecond=0)
        if dich <= gio_vn:
            dich += timedelta(days=1)
        args.sap_xuat_phat = (dich - gio_vn).total_seconds() / 60

    def phut(so_phut):
        return now_db + timedelta(minutes=so_phut)

    def thu_tu_diem(chieu):
        """Chỉ số điểm (theo mảng xuôi) theo hướng đi."""
        return list(range(n)) if chieu == "xuoi" else list(range(n - 1, -1, -1))

    def offset_phut(chieu, vi_tri):
        """Số phút kể từ giờ khởi hành tới điểm thứ vi_tri của hướng đi."""
        i = thu_tu_diem(chieu)[vi_tri]
        return moc_xuoi[i] if chieu == "xuoi" else tong_phut - moc_xuoi[i]

    moc0 = args.sap_xuat_phat if args.sap_xuat_phat is not None else -10
    lich = [  # (số chuyến lệch so với mốc 0, chiều, kiểu, số khách)
        (-1, "nguoc", "hoan_thanh", 14),
        (0, "xuoi", "chua_khoi_hanh" if args.sap_xuat_phat is not None else "dang_chay", 16),
        (1, "nguoc", "chua_khoi_hanh", 9),
        (2, "xuoi", "chua_khoi_hanh", 6),
        (3, "nguoc", "chua_khoi_hanh", 12),
    ]

    seq = {"ma": 0}

    def ten_ngau_nhien():
        return f"{rng.choice(HO)} {rng.choice(DEM)} {rng.choice(TEN)}"

    def sdt_ngau_nhien():
        return rng.choice(DAU_SO) + "".join(str(rng.randint(0, 9)) for _ in range(7))

    def tao_ve(chuyen, so_ghe, don, tra, trang_thai, gio_di, gio_den, tai_quay, mien_job):
        hops = abs(tra - don)
        da_tra = trang_thai in ("da_thanh_toan", "da_len_xe", "da_xuong_xe")
        seq["ma"] += 1
        cur.execute(
            """INSERT INTO ve (ma_ve, chuyen_id, so_ghe, diem_don_id, diem_tra_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                               gia, ma_dat_cho, loai_hinh_thanh_toan, phuong_thuc_thanh_toan, trang_thai,
                               gio_thanh_toan, gio_len_xe, gio_xuong_xe, gio_hoan_tac)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ma_tu_sinh.ma_ve(ma_repository.so_tiep_theo(cur, "ve")), chuyen, so_ghe, diem_xuoi[don], diem_xuoi[tra],
             ten_ngau_nhien(), sdt_ngau_nhien(), int(gia_goc) * hops // max(n - 1, 1), f"TEST{seq['ma']:04d}",
             "thanh_toan_tai_quay" if tai_quay else "thanh_toan_ngay",
             rng.choice(["tien_mat", "chuyen_khoan"]) if da_tra else None, trang_thai,
             phut(-600) if da_tra else None,
             gio_di if trang_thai in ("da_len_xe", "da_xuong_xe") else None,
             gio_den if trang_thai == "da_xuong_xe" else None,
             phut(0) if mien_job else None),
        )

    ds_chuyen = {}
    for k, chieu, kieu, so_khach in lich:
        gio_kh = moc0 + k * PHUT_GIUA_CHUYEN
        c = mot(
            """INSERT INTO chuyen_xe (tuyen_id, xe_id, loai_xe_id, gio_khoi_hanh, chieu, ma)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (tuyen, xe, loai_xe, phut(gio_kh), chieu, ma_tu_sinh.ma_chuyen(ma_tuyen, ma_loai_xe, phut(gio_kh), chieu)),
        )
        ds_chuyen[k] = (c, chieu, kieu, gio_kh)
        di = thu_tu_diem(chieu)

        if kieu in ("dang_chay", "hoan_thanh"):
            cur.execute("UPDATE chuyen_xe SET trang_thai = %s, gio_xac_nhan_xuat_phat = %s WHERE id = %s",
                        (kieu, phut(gio_kh + rng.randint(1, 4)), c))
        if kieu == "hoan_thanh":
            for vi_tri in range(1, n):
                cur.execute(
                    "INSERT INTO lich_su_diem_dung_chuyen (chuyen_id, diem_don_tra_id, gio_thuc_te) VALUES (%s, %s, %s)",
                    (c, diem_xuoi[di[vi_tri]], phut(gio_kh + offset_phut(chieu, vi_tri) + rng.randint(-5, 10))),
                )
            cur.execute("UPDATE chuyen_xe SET gio_hoan_thanh = %s WHERE id = %s", (phut(gio_kh + tong_phut + 8), c))

        # ---- hành khách: chặng ngẫu nhiên theo vị trí trong hướng đi (0..n-1), đón ở văn phòng, trả ở tỉnh khác
        cap_hop_le = [(a, b) for a in range(n - 1) for b in range(a + 1, n)
                      if loai_diem[di[a]] == "van_phong" and tinh_diem[di[a]] != tinh_diem[di[b]]]
        if not cap_hop_le:  # chiều này điểm đầu không phải văn phòng → chỉ giữ ràng buộc khác tỉnh
            cap_hop_le = [(a, b) for a in range(n - 1) for b in range(a + 1, n) if tinh_diem[di[a]] != tinh_diem[di[b]]]
        if not cap_hop_le:
            sys.exit("Tuyến không có cặp điểm đón (văn phòng) → điểm trả khác tỉnh nào — kiểm tra lại dữ liệu tuyến.")
        for so_ghe in rng.sample(ds_ghe, so_khach):
            a_vt, b_vt = rng.choice(cap_hop_le)
            if rng.random() < 0.35 and (0, n - 1) in cap_hop_le:
                a_vt, b_vt = 0, n - 1  # nhiều khách đi cả tuyến
            don, tra = di[a_vt], di[b_vt]
            gio_don = gio_kh + offset_phut(chieu, a_vt)
            gio_tra = gio_kh + offset_phut(chieu, b_vt)
            tai_quay = rng.random() < 0.12
            if kieu == "hoan_thanh":
                trang_thai = "khong_den" if rng.random() < 0.07 else "da_xuong_xe"
                tai_quay = tai_quay and trang_thai == "khong_den"
            elif kieu == "dang_chay":  # vừa xuất phát, xe còn ở điểm đầu: ~nửa khách điểm đầu đã lên
                if a_vt == 0:
                    trang_thai = "da_len_xe" if rng.random() < 0.55 else ("giu_cho" if tai_quay else "da_thanh_toan")
                    tai_quay = tai_quay and trang_thai == "giu_cho"
                else:
                    trang_thai = "giu_cho" if tai_quay else "da_thanh_toan"
            else:
                trang_thai = "giu_cho" if tai_quay else "da_thanh_toan"
            tao_ve(c, so_ghe, don, tra, trang_thai, phut(gio_don + rng.randint(-8, 0)), phut(gio_tra + rng.randint(-5, 10)),
                   tai_quay and trang_thai in ("giu_cho", "khong_den"),
                   # job no-show đánh dấu khách ở điểm đầu "không đến" trước giờ xuất phát 5 phút → miễn để test lên xe được
                   mien_job=(k == 0 and a_vt == 0 and trang_thai in ("da_thanh_toan", "giu_cho") and kieu != "hoan_thanh"))

    # ---------- đơn hàng chờ chất (chưa gắn chuyến) — cần NV gửi hàng + loại hàng
    nv_gui = mot("SELECT id FROM nguoi_dung WHERE email = %s", (EMAIL_NV_GUI_HANG,))
    loai_hang = mot("SELECT id FROM loai_hang WHERE la_hang_cam = false ORDER BY ten LIMIT 1")
    so_don = 0
    if nv_gui and loai_hang:
        def tao_don(ma, gui, nhan, nguoi_nhan, kg):
            cur.execute(
                """INSERT INTO don_hang (ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, can_nang_kg, loai_hang_id, gia_cuoc,
                                         ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan, phuong_thuc_thanh_toan, nhan_vien_gui_id,
                                         da_thu_tien, thoi_gian_thu, nhan_vien_thu_id, trang_thai)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'nguoi_gui_tra_truoc', %s, true, now(), %s, 'cho_van_chuyen')""",
                (ma, tuyen, diem_xuoi[gui], diem_xuoi[nhan], kg, loai_hang, 30000 + 10000 * kg, ten_ngau_nhien(), sdt_ngau_nhien(),
                 nguoi_nhan, sdt_ngau_nhien(), nv_gui, nv_gui),
            )
        tao_don("TEST-H1", 0, n - 1, "Cửa hàng An Phát", 4)
        tao_don("TEST-H2", 0, 2, "Chị Mai", 2)
        tao_don("TEST-H3", 1, n - 1, "Anh Tuấn", 3)
        tao_don("TEST-H4", n - 1, 0, "Quán Cà Phê Sapa", 5)
        so_don = 4

    conn.commit()
    release_connection(conn)

    print(f"Đã tạo chuyến cho {EMAIL_PHU_XE} (xe {BIEN_SO}, tuyến {MA_TUYEN}, {len(lich)} chuyến, {so_don} đơn hàng chờ chất)")
    if not so_don:
        print(f"  (bỏ qua đơn hàng: chưa có tài khoản {EMAIL_NV_GUI_HANG} — chạy seed_phu_xe_demo.py trước nếu muốn)")
    for k, (c, chieu, kieu, gio_kh) in sorted(ds_chuyen.items()):
        print(f"  {(now_db + timedelta(minutes=gio_kh)).astimezone().strftime('%d/%m %H:%M')} UTC  {chieu:5}  {kieu}")


if __name__ == "__main__":
    main()
