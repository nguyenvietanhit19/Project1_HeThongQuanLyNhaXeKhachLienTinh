"""Tạo/cập nhật tài khoản demo nhân viên quầy vé trên DB local.

Chạy trong container backend: `docker compose exec backend python scripts/seed_nhan_vien_quay_ve_demo.py`.
Tài khoản: quayve.demo@nhaxe-demo.vn / QuayVe@123.
"""

import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.repositories import ma_repository  # noqa: E402
from app.services.mat_khau_service import _pwd_context  # noqa: E402

EMAIL = "quayve.demo@nhaxe-demo.vn"
MAT_KHAU = "QuayVe@123"
HO_TEN = "Nhân Viên Quầy Vé Demo"
SDT = "0900000006"


def main() -> None:
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script chỉ dành cho DB local.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT d.id FROM diem_don_tra d
                   WHERE d.loai = 'van_phong'
                     AND EXISTS (
                         SELECT 1 FROM tuyen_diem_don_tra tdt
                         WHERE tdt.diem_don_tra_id = d.id
                     )
                   ORDER BY d.ten, d.id LIMIT 1"""
            )
            row = cur.fetchone()
            if not row:
                sys.exit("Chưa có văn phòng thuộc tuyến. Hãy tạo tuyến và gán văn phòng trước khi seed tài khoản.")
            van_phong_id = row[0]

            cur.execute("SELECT ma, vai_tro FROM nguoi_dung WHERE email = %s FOR UPDATE", (EMAIL,))
            tai_khoan_cu = cur.fetchone()
            if tai_khoan_cu and tai_khoan_cu[1] != "nhan_vien_quay_ve":
                sys.exit("Email demo đã thuộc tài khoản có vai trò khác.")
            ma_nhan_vien = (tai_khoan_cu[0] if tai_khoan_cu else None) or ma_repository.cap_ma_nhan_vien(
                cur, "nhan_vien_quay_ve"
            )

            cur.execute(
                """INSERT INTO nguoi_dung
                       (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan, dang_hoat_dong, ma)
                   VALUES (%s, %s, %s, %s, 'nhan_vien_quay_ve', true, true, %s)
                   ON CONFLICT (email) DO UPDATE SET
                       mat_khau = EXCLUDED.mat_khau,
                       ho_ten = EXCLUDED.ho_ten,
                       so_dien_thoai = EXCLUDED.so_dien_thoai,
                       vai_tro = EXCLUDED.vai_tro,
                       ma = COALESCE(nguoi_dung.ma, EXCLUDED.ma),
                       da_xac_nhan = true,
                       dang_hoat_dong = true
                   RETURNING id""",
                (EMAIL, _pwd_context.hash(MAT_KHAU), HO_TEN, SDT, ma_nhan_vien),
            )
            nguoi_dung_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id)
                   VALUES (%s, %s)
                   ON CONFLICT (nguoi_dung_id) DO UPDATE
                   SET van_phong_id = EXCLUDED.van_phong_id""",
                (nguoi_dung_id, van_phong_id),
            )
            cur.execute("SELECT ten FROM diem_don_tra WHERE id = %s", (van_phong_id,))
            ten_van_phong = cur.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)

    print("Đã sẵn sàng tài khoản nhân viên quầy vé demo:")
    print(f"  Email: {EMAIL}")
    print(f"  Mã nhân viên: {ma_nhan_vien}")
    print(f"  Mật khẩu: {MAT_KHAU}")
    print(f"  Văn phòng: {ten_van_phong}")


if __name__ == "__main__":
    main()
