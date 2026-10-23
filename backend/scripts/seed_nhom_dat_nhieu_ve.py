"""Thêm vào chuyến test của phụ xe 3 NHÓM KHÁCH ĐẶT NHIỀU VÉ (1 người đặt cho cả nhà/đồng nghiệp) để xem màn hình phụ xe hiển thị thế nào.

Chạy sau seed_chuyen_phu_xe_test.py, trong container backend:

    docker-compose exec backend python scripts/seed_nhom_dat_nhieu_ve.py

Nhóm tạo ra (mã đặt chỗ đúng định dạng thật DC + 8 ký tự; chạy lại sẽ xóa nhóm cũ rồi tạo mới):
  nhóm A  khách có tài khoản "Khách Hàng Demo", 5 vé cùng lần đặt, tất cả đã thanh toán, lên ở điểm đầu
  nhóm B  khách vãng lai "Lê Thị Hoa", 3 vé: 1 đã lên xe, 1 chờ lên, 1 giữ chỗ tại quầy chưa trả tiền
  nhóm C  khách có tài khoản thứ hai, 3 vé đã thanh toán, lên ở điểm thứ 2 (để xem nhóm ở điểm giữa)
Chuyến được chọn: chuyến chưa khởi hành / đang chạy sớm nhất của xe phụ xe test. Chỉ chạy trên DB local.
"""

import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.repositories import ma_repository  # noqa: E402
from app.services.dat_ve_service import sinh_ma_dat_cho  # noqa: E402
from app.utils import ma_tu_sinh  # noqa: E402

BIEN_SO = "24B3 - 88888"
EMAIL_KHACH_A = "khachhang.demo@nhaxe-demo.vn"


def main() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")

    conn = get_connection()
    cur = conn.cursor()

    def mot(sql, params=()):
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None

    chuyen = mot(
        """SELECT c.id FROM chuyen_xe c JOIN xe x ON x.id = c.xe_id
           WHERE x.bien_so = %s AND c.trang_thai IN ('chua_khoi_hanh', 'dang_chay')
           ORDER BY c.gio_khoi_hanh LIMIT 1""", (BIEN_SO,))
    if not chuyen:
        sys.exit("Không có chuyến chưa khởi hành/đang chạy của xe test — chạy seed_chuyen_phu_xe_test.py trước.")
    chieu, tuyen, loai_xe = None, None, None
    cur.execute("SELECT chieu, tuyen_id, loai_xe_id FROM chuyen_xe WHERE id = %s", (chuyen,))
    chieu, tuyen, loai_xe = cur.fetchone()

    cur.execute("SELECT diem_don_tra_id FROM tuyen_diem_don_tra WHERE tuyen_id = %s ORDER BY thu_tu", (tuyen,))
    diem = [r[0] for r in cur.fetchall()]
    if chieu == "nguoc":
        diem.reverse()
    n = len(diem)
    gia_goc = mot("SELECT MAX(gia_goc) FROM gia_ve") or 300000

    # ghế còn trống trên chuyến này (không bị vé nào đang hiệu lực chiếm), theo thứ tự trên sơ đồ
    cur.execute("SELECT so_do_ghe FROM loai_xe WHERE id = %s", (loai_xe,))
    so_do = cur.fetchone()[0]
    import json
    so_do = so_do if isinstance(so_do, list) else json.loads(so_do)
    # dọn nhóm demo cũ: vé của xe test có mã đặt chỗ KHÔNG bắt đầu bằng TEST (vé seed thường là TEST0001...)
    cu = "SELECT id FROM ve WHERE ma_dat_cho NOT LIKE 'TEST%%' AND chuyen_id IN (SELECT c.id FROM chuyen_xe c JOIN xe x ON x.id = c.xe_id WHERE x.bien_so = %s)"
    cur.execute(f"DELETE FROM thong_bao WHERE ve_id IN ({cu})", (BIEN_SO,))
    cur.execute(f"DELETE FROM ve WHERE id IN ({cu})", (BIEN_SO,))
    ma_a, ma_b, ma_c = sinh_ma_dat_cho(), sinh_ma_dat_cho(), sinh_ma_dat_cho()   # mã đặt chỗ đúng định dạng thật: DC + 8 ký tự hex
    cur.execute("SELECT so_ghe FROM ve WHERE chuyen_id = %s AND trang_thai NOT IN ('da_huy', 'het_han')", (chuyen,))
    ban = {r[0] for r in cur.fetchall()}
    ghe_trong = sorted((g["ma_ghe"] for g in so_do if g["ma_ghe"] not in ban),
                       key=lambda s: [int(t) if t.isdigit() else t for t in __import__("re").split(r"(\d+)", s)])
    can = 5 + 3 + 3
    if len(ghe_trong) < can:
        sys.exit(f"Chuyến chỉ còn {len(ghe_trong)} ghế trống, cần {can} — chạy lại seed_chuyen_phu_xe_test.py để làm mới.")

    khach_a = mot("SELECT id FROM nguoi_dung WHERE email = %s", (EMAIL_KHACH_A,))
    khach_c = mot("SELECT id FROM nguoi_dung WHERE vai_tro = 'khach_hang' AND email <> %s ORDER BY email LIMIT 1", (EMAIL_KHACH_A,))
    if not khach_a:
        sys.exit(f"Không thấy tài khoản {EMAIL_KHACH_A} — chạy seed_phu_xe_demo.py trước.")

    def tao_ve(ma_dat, so_ghe, don, tra, trang_thai, khach_id=None, ten=None, sdt=None, tai_quay=False):
        da_tra = trang_thai in ("da_thanh_toan", "da_len_xe")
        cur.execute(
            """INSERT INTO ve (ma_ve, chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id, ten_khach_vang_lai, sdt_khach_vang_lai,
                               gia, ma_dat_cho, loai_hinh_thanh_toan, phuong_thuc_thanh_toan, trang_thai, gio_thanh_toan, gio_len_xe, gio_hoan_tac)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       CASE WHEN %s THEN now() - interval '600 minutes' END,
                       CASE WHEN %s THEN now() END, now())""",
            (ma_tu_sinh.ma_ve(ma_repository.so_tiep_theo(cur, "ve")), chuyen, so_ghe, diem[don], diem[tra], khach_id, ten, sdt,
             int(gia_goc) * abs(tra - don) // max(n - 1, 1), ma_dat,
             "thanh_toan_tai_quay" if tai_quay else "thanh_toan_ngay",
             "tien_mat" if da_tra else None, trang_thai, da_tra, trang_thai == "da_len_xe"),
        )

    # gio_hoan_tac = now() để job no-show bỏ qua các vé demo này (cùng cách seed_chuyen_phu_xe_test.py dùng), nên nhóm không bị đánh "không đến" tự động
    g = iter(ghe_trong)
    for _ in range(5):
        tao_ve(ma_a, next(g), 0, n - 1, "da_thanh_toan", khach_id=khach_a)
    tao_ve(ma_b, next(g), 0, n - 1, "da_len_xe", ten="Lê Thị Hoa", sdt="0912000111")
    tao_ve(ma_b, next(g), 0, n - 1, "da_thanh_toan", ten="Lê Thị Hoa", sdt="0912000111")
    tao_ve(ma_b, next(g), 0, n - 1, "giu_cho", ten="Lê Thị Hoa", sdt="0912000111", tai_quay=True)
    if n > 2:
        for _ in range(3):
            tao_ve(ma_c, next(g), 1, n - 1, "da_thanh_toan", khach_id=khach_c or khach_a)

    conn.commit()
    release_connection(conn)
    print(f"Đã tạo 3 nhóm khách đặt nhiều vé cho chuyến {chuyen} ({chieu}):")
    print(f"  {ma_a}  Khách Hàng Demo        5 vé đã thanh toán, lên ở điểm đầu")
    print(f"  {ma_b}  Lê Thị Hoa (vãng lai)  3 vé: 1 đã lên xe · 1 chờ lên · 1 giữ chỗ tại quầy chưa trả tiền")
    print(f"  {ma_c}  khách tài khoản 2      3 vé đã thanh toán, lên ở điểm thứ 2")


if __name__ == "__main__":
    main()
