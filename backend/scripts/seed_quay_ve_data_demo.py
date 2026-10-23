"""Thêm dữ liệu thử cho nhân viên quầy vé demo vào PostgreSQL local.

Chạy với DATABASE_URL hoặc các biến PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE.
Script chỉ chấp nhận DB local, không sửa bản ghi có sẵn và chạy lại không tạo trùng
các chuyến/vé của cùng ngày. Các mã đặt chỗ in ra dùng để thử tra cứu/in vé.
"""

import datetime as dt
import os
import sys
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories import ma_repository  # noqa: E402
from app.utils import ma_tu_sinh  # noqa: E402
from app.utils.gia import gia_theo_ghe  # noqa: E402


EMAIL = "quayve.demo@nhaxe-demo.vn"
MA_TUYEN = "T003"
MA_LOAI_XE = "LX004"
MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")
TRANG_THAI_MAU = (
    ("CASH", "Khách Demo Tiền Mặt", "0900000101", "tai_quay", "da_thanh_toan", "tien_mat"),
    ("HOLD", "Khách Demo Giữ Chỗ", "0900000102", "hotline", "giu_cho", None),
    ("CANCEL", "Khách Demo Đã Hủy", "0900000103", "tai_quay", "da_huy", None),
    ("BANK", "Khách Demo Chuyển Khoản", "0900000104", "hotline", "da_thanh_toan", "chuyen_khoan"),
)


def ket_noi_local():
    dsn = os.getenv("DATABASE_URL")
    host = urlparse(dsn).hostname if dsn else (os.getenv("PGHOST") or "localhost")
    if host not in {"db", "localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(f"Chỉ cho phép seed DB local; host hiện tại: {host}")
    return psycopg2.connect(dsn) if dsn else psycopg2.connect()


def gio_chuyen_mau() -> list[dt.datetime]:
    hien_tai = dt.datetime.now(MUI_GIO)
    ket_qua = []
    for ngay_them in range(4):
        ngay = hien_tai.date() + dt.timedelta(days=ngay_them)
        for gio in (9, 14, 19):
            khoi_hanh = dt.datetime.combine(ngay, dt.time(gio, 15), tzinfo=MUI_GIO)
            if khoi_hanh > hien_tai + dt.timedelta(minutes=90):
                ket_qua.append(khoi_hanh)
            if len(ket_qua) == 5:
                return ket_qua
    raise RuntimeError("Không tìm được 5 khung giờ tương lai để tạo dữ liệu demo")


def main() -> None:
    cac_gio = gio_chuyen_mau()
    ma_dat_cho = []
    so_chuyen_moi = 0
    so_ve_moi = 0

    with ket_noi_local() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT n.id, d.id, d.khu_vuc_id, d.ten
                   FROM nguoi_dung n
                   JOIN ho_so_can_bo_diem h ON h.nguoi_dung_id = n.id
                   JOIN diem_don_tra d ON d.id = h.van_phong_id
                   WHERE n.email = %s AND n.vai_tro = 'nhan_vien_quay_ve'
                     AND n.dang_hoat_dong AND d.loai = 'van_phong'""",
                (EMAIL,),
            )
            can_bo = cur.fetchone()
            if not can_bo:
                raise RuntimeError("Chưa có tài khoản quầy vé demo hợp lệ; chạy seed_nhan_vien_quay_ve_demo.py trước")
            nhan_vien_id, diem_don_id, khu_vuc_di_id, ten_van_phong = can_bo

            cur.execute("SELECT id, ma FROM tuyen WHERE ma = %s", (MA_TUYEN,))
            tuyen = cur.fetchone()
            cur.execute("SELECT id, ma, so_do_ghe, he_so_ghe FROM loai_xe WHERE ma = %s", (MA_LOAI_XE,))
            loai_xe = cur.fetchone()
            if not tuyen or not loai_xe:
                raise RuntimeError("Thiếu tuyến T003 hoặc loại xe LX004 trong DB demo")
            tuyen_id, ma_tuyen = tuyen
            loai_xe_id, ma_loai_xe, so_do_ghe, he_so_ghe = loai_xe
            cac_ghe = [g["ma_ghe"] for g in so_do_ghe]
            if len(cac_ghe) < 5:
                raise RuntimeError("Loại xe demo cần tối thiểu 5 ghế để thử đủ trạng thái")

            cur.execute(
                """SELECT d.id, d.khu_vuc_id, d.ten, tdt.thu_tu
                   FROM tuyen_diem_don_tra tdt
                   JOIN diem_don_tra d ON d.id = tdt.diem_don_tra_id
                   WHERE tdt.tuyen_id = %s AND d.loai = 'van_phong'
                   ORDER BY tdt.thu_tu""",
                (tuyen_id,),
            )
            cac_van_phong = cur.fetchall()
            if len(cac_van_phong) < 2 or cac_van_phong[-1][0] != diem_don_id:
                raise RuntimeError("Văn phòng quầy vé demo phải là văn phòng cuối của tuyến T003")
            diem_tra_id, khu_vuc_den_id, ten_diem_tra, _ = cac_van_phong[0]
            if khu_vuc_di_id == khu_vuc_den_id:
                raise RuntimeError("Hai văn phòng demo phải thuộc hai khu vực khác nhau")

            for index, khoi_hanh in enumerate(cac_gio):
                cur.execute(
                    """SELECT g.gia_goc
                       FROM bo_gia_ve b JOIN gia_ve g ON g.bo_gia_id = b.id
                       WHERE b.tuyen_id = %s AND b.ap_dung_tu <= %s
                         AND (b.ap_dung_den IS NULL OR b.ap_dung_den >= %s)
                         AND g.diem_di_id = %s AND g.diem_den_id = %s
                       ORDER BY b.ap_dung_tu DESC LIMIT 1""",
                    (tuyen_id, khoi_hanh.date(), khoi_hanh.date(), khu_vuc_den_id, khu_vuc_di_id),
                )
                gia_row = cur.fetchone()
                if not gia_row:
                    raise RuntimeError(f"Tuyến {MA_TUYEN} chưa có giá vé cho ngày {khoi_hanh.date()}")
                gia_goc = gia_row[0]
                ma_chuyen = ma_tu_sinh.ma_chuyen(ma_tuyen, ma_loai_xe, khoi_hanh, "nguoc")
                cur.execute("SELECT id FROM chuyen_xe WHERE ma = %s FOR UPDATE", (ma_chuyen,))
                existing = cur.fetchone()
                if existing:
                    chuyen_id = existing[0]
                else:
                    cur.execute(
                        """INSERT INTO chuyen_xe
                               (ma, tuyen_id, chieu, loai_xe_id, gio_khoi_hanh, he_so_gia, he_so_ghe)
                           VALUES (%s, %s, 'nguoc', %s, %s, 1, %s)
                           RETURNING id""",
                        (ma_chuyen, tuyen_id, loai_xe_id, khoi_hanh, Json(he_so_ghe)),
                    )
                    chuyen_id = cur.fetchone()[0]
                    so_chuyen_moi += 1

                if index >= len(TRANG_THAI_MAU):
                    continue  # Chuyến cuối để trống hoàn toàn, sẵn cho thao tác bán vé mới.

                suffix, ten_khach, sdt, kenh_ban, trang_thai, phuong_thuc = TRANG_THAI_MAU[index]
                booking = f"QVDEMO-{khoi_hanh:%Y%m%d%H%M}-{suffix}"
                cur.execute("SELECT id, chuyen_id FROM ve WHERE ma_dat_cho = %s", (booking,))
                da_co = cur.fetchall()
                if da_co:
                    if len(da_co) != 1 or da_co[0][1] != chuyen_id:
                        raise RuntimeError(f"Mã demo {booking} đã được dùng cho chuyến khác")
                    ma_dat_cho.append((booking, trang_thai, sdt))
                    continue
                if existing:
                    continue  # Không thêm vé vào chuyến có sẵn không thuộc lô demo hiện tại.

                ghe = cac_ghe[index]
                gia = gia_theo_ghe(gia_goc, 1, [ghe], he_so_ghe)[ghe]
                ma_ve = ma_tu_sinh.ma_ve(ma_repository.so_tiep_theo(cur, "ve"))
                cur.execute(
                    """INSERT INTO ve
                           (ma_ve, chuyen_id, so_ghe, diem_don_id, diem_tra_id,
                            gia, ma_dat_cho, loai_hinh_thanh_toan, trang_thai,
                            ten_khach_vang_lai, sdt_khach_vang_lai,
                            nhan_vien_ban_id, nhan_vien_thu_id, kenh_ban,
                            phuong_thuc_thanh_toan, gio_thanh_toan, gio_huy)
                       VALUES
                           (%s, %s, %s, %s, %s, %s, %s, 'thanh_toan_tai_quay', %s,
                            %s, %s, %s, %s, %s, %s,
                            CASE WHEN %s = 'da_thanh_toan' THEN now() ELSE NULL END,
                            CASE WHEN %s = 'da_huy' THEN now() ELSE NULL END)""",
                    (ma_ve, chuyen_id, ghe, diem_don_id, diem_tra_id, gia, booking, trang_thai,
                     ten_khach, sdt, nhan_vien_id,
                     nhan_vien_id if phuong_thuc == "tien_mat" else None,
                     kenh_ban, phuong_thuc, trang_thai, trang_thai),
                )
                so_ve_moi += 1
                ma_dat_cho.append((booking, trang_thai, sdt))

    print(f"Văn phòng: {ten_van_phong} → {ten_diem_tra}")
    print(f"Đã thêm {so_chuyen_moi} chuyến và {so_ve_moi} vé demo (chạy lại cùng ngày sẽ bỏ qua dữ liệu đã có).")
    for booking, trang_thai, sdt in ma_dat_cho:
        print(f"  {booking} | {trang_thai} | SĐT tra cứu: {sdt}")
    print("Chuyến thứ 5 chưa có vé để thử bán vé mới.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
