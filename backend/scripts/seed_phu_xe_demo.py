"""Tạo dữ liệu mẫu để TEST phần phụ xe trên DB LOCAL (không dùng cho production).

Chạy trong container backend (sau khi đã `yoyo apply` migration):

    docker compose exec backend python scripts/seed_phu_xe_demo.py

Chạy lại bao nhiêu lần cũng được: hạ tầng (khu vực, điểm, tuyến, xe, tài khoản)
được giữ, còn chuyến/vé/đơn hàng demo được xóa và tạo mới để mỗi lần test đều
bắt đầu từ trạng thái sạch ("chưa khởi hành").

Tài khoản (đăng nhập tại /nhan-vien/dang-nhap.html hoặc POST /auth/dang-nhap):
    Phụ xe    phuxe.demo@nhaxe-demo.vn      / PhuXe@123
    Khách     khachhang.demo@nhaxe-demo.vn  / KhachHang@123   (có vé trên chuyến ngược, để thử WebSocket)

Tuyến demo: 4 điểm A → B → C → D theo chiều xuôi. Phụ xe có 3 chuyến:
    1. XUÔI  — đã quá giờ khởi hành 10 phút  (xuất phát được ngay)
    2. NGƯỢC — đã quá giờ khởi hành 5 phút   (D → C → B → A, để thử chuyến ngược)
    3. XUÔI  — khởi hành NGÀY MAI            (để thử bị chặn xuất phát sớm)
"""

import json
import os
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
TEN_TUYEN = "DEMO Hà Nội - Sapa"
BIEN_SO = "29B-DEMO01"


def _chi_chay_tren_may_local() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")


def main() -> None:
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
                (tuyen, diem[ky_hieu], thu_tu, (thu_tu - 1) * 90),
            )
    ghe = [{"ma_ghe": f"A{i}", "tang": 1, "x": i * 40, "y": 0} for i in range(1, 11)]
    loai_xe = lay_hoac_tao(
        "SELECT id FROM loai_xe WHERE ten = %s", ("DEMO Giường nằm 10 chỗ",),
        "INSERT INTO loai_xe (ten, he_so_gia, so_do_ghe, ma) VALUES (%s, 1, %s, '') RETURNING id",
        ("DEMO Giường nằm 10 chỗ", json.dumps(ghe)),
    )
    xe = lay_hoac_tao(
        "SELECT id FROM xe WHERE bien_so = %s", (BIEN_SO,),
        "INSERT INTO xe (bien_so, loai_xe_id, diem_goc_id, tuyen_id) VALUES (%s, %s, %s, %s) RETURNING id",
        (BIEN_SO, loai_xe, diem["A"], tuyen),
    )

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
    # Luôn đặt lại mật khẩu để lần chạy nào cũng đăng nhập được với mật khẩu ghi ở đầu file
    cur.execute("UPDATE nguoi_dung SET mat_khau = %s, da_xac_nhan = true, dang_hoat_dong = true WHERE id = %s",
                (_pwd_context.hash(MAT_KHAU_PHU_XE), phu_xe_nd))
    nhan_su = lay_hoac_tao(
        "SELECT id FROM nhan_su_van_hanh WHERE nguoi_dung_id = %s", (phu_xe_nd,),
        "INSERT INTO nhan_su_van_hanh (ho_ten, so_dien_thoai, chuc_danh, nguoi_dung_id) VALUES ('Phụ Xe Demo', '0900000001', 'phu_xe', %s) RETURNING id",
        (phu_xe_nd,),
    )
    if not mot("SELECT 1 FROM xe_nhan_su WHERE xe_id = %s AND nhan_su_van_hanh_id = %s", (xe, nhan_su)):
        cur.execute("INSERT INTO xe_nhan_su (xe_id, nhan_su_van_hanh_id, loai) VALUES (%s, %s, 'co_dinh')", (xe, nhan_su))

    # ---------- dữ liệu chạy thử: xóa bản cũ rồi tạo mới
    cur.execute("DELETE FROM bao_cao_su_co_hang WHERE don_hang_id IN (SELECT id FROM don_hang WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM don_hang WHERE tuyen_id = %s", (tuyen,))
    cur.execute("DELETE FROM thong_bao WHERE ve_id IN (SELECT v.id FROM ve v JOIN chuyen_xe c ON c.id = v.chuyen_id WHERE c.tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM ve WHERE chuyen_id IN (SELECT id FROM chuyen_xe WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM lich_su_diem_dung_chuyen WHERE chuyen_id IN (SELECT id FROM chuyen_xe WHERE tuyen_id = %s)", (tuyen,))
    cur.execute("DELETE FROM chuyen_xe WHERE tuyen_id = %s", (tuyen,))

    def tao_chuyen(chieu, gio_sql):
        return mot(
            f"""INSERT INTO chuyen_xe (tuyen_id, xe_id, loai_xe_id, gio_khoi_hanh, chieu, ma)
                VALUES (%s, %s, %s, {gio_sql}, %s, '') RETURNING id""",
            (tuyen, xe, loai_xe, chieu),
        )

    c_xuoi = tao_chuyen("xuoi", "now() - interval '10 minutes'")
    c_nguoc = tao_chuyen("nguoc", "now() - interval '5 minutes'")
    c_mai = tao_chuyen("xuoi", "now() + interval '1 day'")

    def tao_ve(chuyen, so_ghe, don, tra, ten, khach_id=None, trang_thai="da_thanh_toan"):
        cur.execute(
            """INSERT INTO ve (chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                               gia, ma_dat_cho, loai_hinh_thanh_toan, trang_thai)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 250000, %s, 'thanh_toan_ngay', %s)""",
            (chuyen, so_ghe, diem[don], diem[tra], khach_id, None if khach_id else ten, None if khach_id else "0911000000",
             f"DEMO-{str(chuyen)[:4]}-{so_ghe}", trang_thai),
        )

    # Chuyến XUÔI A→D: khách lên ở A, B; xuống ở C, D
    tao_ve(c_xuoi, "A1", "A", "D", "Nguyễn Văn An")
    tao_ve(c_xuoi, "A2", "A", "C", "Trần Thị Bình")
    tao_ve(c_xuoi, "A3", "B", "D", "Lê Hoàng Cường")
    tao_ve(c_xuoi, "A4", "A", "D", "Phạm Đức Dũng", trang_thai="giu_cho")  # chưa trả tiền: KHÔNG được lên xe
    # Chuyến NGƯỢC D→A: khách lên ở D, B; xuống ở B, A. Khách hàng demo đón tại B (phía sau C theo chiều ngược) để nhận thông báo ETA khi xe tới C.
    tao_ve(c_nguoc, "B1", "D", "A", "Võ Thị Em")
    tao_ve(c_nguoc, "B2", "D", "B", "Đặng Gia Hân")
    tao_ve(c_nguoc, "B3", "B", "A", "Khách Hàng Demo", khach_id=khach_nd)
    tao_ve(c_mai, "A1", "A", "D", "Hoàng Minh Khôi")

    loai_hang = mot("SELECT id FROM loai_hang WHERE la_hang_cam = false ORDER BY ten LIMIT 1")

    def tao_don(ma, gui, nhan, nguoi_nhan, kg):
        cur.execute(
            """INSERT INTO don_hang (ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, can_nang_kg, loai_hang_id, gia_cuoc,
                                     ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan, phuong_thuc_thanh_toan, nhan_vien_gui_id)
               VALUES (%s, %s, %s, %s, %s, %s, 60000, 'Người Gửi Demo', '0933000000', %s, '0944000000', 'nguoi_gui_tra_truoc', %s)""",
            (ma, tuyen, diem[gui], diem[nhan], kg, loai_hang, nguoi_nhan, nv_gui),
        )

    tao_don("DEMO-H1", "A", "D", "Cửa hàng An Phát", 4)    # xuôi: A→D  (chuyến xuôi chất được, chuyến ngược thì không)
    tao_don("DEMO-H2", "A", "C", "Chị Mai", 2)             # xuôi: A→C
    tao_don("DEMO-H3", "D", "A", "Anh Tuấn", 3)            # ngược: D→A (chỉ chuyến ngược chất được)
    tao_don("DEMO-H4", "D", "B", "Quán Cà Phê Sapa", 5)    # ngược: D→B

    conn.commit()
    release_connection(conn)

    print("Đã tạo dữ liệu demo.")
    print(f"  Phụ xe : {EMAIL_PHU_XE} / {MAT_KHAU_PHU_XE}")
    print(f"  Khách  : {EMAIL_KHACH} / {MAT_KHAU_KHACH}")
    print(f"  Xe {BIEN_SO} — tuyến '{TEN_TUYEN}' — 3 chuyến: xuôi (quá giờ), ngược (quá giờ), xuôi (ngày mai)")


if __name__ == "__main__":
    main()
