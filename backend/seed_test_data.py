"""Script nạp dữ liệu mẫu THỰC TẾ vào database PostgreSQL để test toàn bộ UC của Điều độ viên:
- UC-44: Gán xe (chuyến sắp chạy chưa có xe)
- UC-45: Tự động hoãn (chuyến quá giờ chưa có xe)
- UC-19: Xử lý sự cố giữa đường (chuyến đang gặp sự cố lỗi nhà xe và sự cố khách quan)
- UC-20: Đổi xe trước giờ (chuyến bị cảnh báo xung đột vị trí hoặc cần đổi xe)
- UC-40: Gán lại xe gốc (chuyến đang có xe chạy thay)
- UC-39: Thống kê vận hành

Chạy: docker-compose exec backend python seed_test_data.py
"""

from datetime import datetime, timedelta, timezone
from app.db import get_connection, release_connection

def seed():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("1. Tạo bảng ho_so_can_bo_diem nếu chưa có...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ho_so_can_bo_diem (
                    nguoi_dung_id UUID PRIMARY KEY REFERENCES nguoi_dung(id),
                    van_phong_id  UUID NOT NULL REFERENCES diem_don_tra(id)
                );
            """)

            print("2. Seed khu_vuc...")
            cur.execute("""
                INSERT INTO khu_vuc (id, ten, tinh_thanh) VALUES
                    ('11111111-0000-0000-0000-000000000001', 'Hà Nội', 'Hà Nội'),
                    ('11111111-0000-0000-0000-000000000002', 'Hải Phòng', 'Hải Phòng'),
                    ('11111111-0000-0000-0000-000000000003', 'Lào Cai', 'Lào Cai')
                ON CONFLICT (id) DO UPDATE SET ten = EXCLUDED.ten;
            """)

            print("3. Seed diem_don_tra...")
            cur.execute("""
                INSERT INTO diem_don_tra (id, khu_vuc_id, ten, dia_chi, loai) VALUES
                    ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001', 'VP Hà Nội - Mỹ Đình', '20 Phạm Hùng, Mỹ Đình, HN', 'van_phong'),
                    ('22222222-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000002', 'VP Hải Phòng - Cầu Rào', '98 Tô Hiệu, Lê Chân, HP', 'van_phong'),
                    ('22222222-0000-0000-0000-000000000003', '11111111-0000-0000-0000-000000000003', 'VP Sa Pa - Trung tâm', '18 Fansipan, Sa Pa, Lào Cai', 'van_phong'),
                    ('22222222-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000001', 'Điểm dừng Cầu Giấy', '125 Cầu Giấy, HN', 'diem_dung'),
                    ('22222222-0000-0000-0000-000000000005', '11111111-0000-0000-0000-000000000002', 'Điểm dừng Thượng Lý', '55 Lạch Tray, HP', 'diem_dung')
                ON CONFLICT (id) DO UPDATE SET ten = EXCLUDED.ten;
            """)

            print("4. Seed loai_xe...")
            cur.execute("""
                INSERT INTO loai_xe (id, ten, he_so_gia, so_do_ghe) VALUES
                    ('33333333-0000-0000-0000-000000000001', 'Limousine 11 chỗ', 1.50,
                     '[{"ma_ghe":"A1-1","tang":1,"x":0,"y":0},{"ma_ghe":"A2-1","tang":1,"x":0,"y":40}]'::jsonb),
                    ('33333333-0000-0000-0000-000000000002', 'Giường nằm 34 chỗ', 1.20,
                     '[{"ma_ghe":"A1-1","tang":1,"x":0,"y":0},{"ma_ghe":"A2-1","tang":1,"x":0,"y":40}]'::jsonb)
                ON CONFLICT (id) DO UPDATE SET ten = EXCLUDED.ten;
            """)

            print("5. Seed tuyen...")
            cur.execute("""
                INSERT INTO tuyen (id, ten) VALUES
                    ('44444444-0000-0000-0000-000000000001', 'Hà Nội - Hải Phòng'),
                    ('44444444-0000-0000-0000-000000000002', 'Hà Nội - Sa Pa')
                ON CONFLICT (id) DO UPDATE SET ten = EXCLUDED.ten;
            """)

            print("6. Seed tuyen_diem_don_tra...")
            cur.execute("""
                INSERT INTO tuyen_diem_don_tra (tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut) VALUES
                    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 1, 0),
                    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000004', 2, 20),
                    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000005', 3, 90),
                    ('44444444-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', 4, 120),
                    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000001', 1, 0),
                    ('44444444-0000-0000-0000-000000000002', '22222222-0000-0000-0000-000000000003', 2, 360)
                ON CONFLICT (tuyen_id, thu_tu) DO NOTHING;
            """)

            print("7. Seed xe...")
            cur.execute("""
                INSERT INTO xe (id, bien_so, loai_xe_id, trang_thai, diem_goc_id, tuyen_id) VALUES
                    ('55555555-0000-0000-0000-000000000001', '29B-123.45', '33333333-0000-0000-0000-000000000001', 'hoat_dong', '22222222-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001'),
                    ('55555555-0000-0000-0000-000000000002', '29B-678.90', '33333333-0000-0000-0000-000000000001', 'hoat_dong', '22222222-0000-0000-0000-000000000001', NULL),
                    ('55555555-0000-0000-0000-000000000003', '14B-555.88', '33333333-0000-0000-0000-000000000002', 'hoat_dong', '22222222-0000-0000-0000-000000000001', NULL),
                    ('55555555-0000-0000-0000-000000000004', '29B-777.11', '33333333-0000-0000-0000-000000000001', 'hoat_dong', '22222222-0000-0000-0000-000000000001', NULL),
                    ('55555555-0000-0000-0000-000000000005', '29B-888.22', '33333333-0000-0000-0000-000000000002', 'bao_tri',   '22222222-0000-0000-0000-000000000001', NULL)
                ON CONFLICT (bien_so) DO UPDATE SET trang_thai = EXCLUDED.trang_thai;
            """)

            print("7b. Seed tài khoản điều độ viên riêng biệt...")
            # Mật khẩu 123456 hash bcrypt
            mat_khau_123456 = '$2b$12$pDA4fcW81C30L2eBwDgx0OJnXp0OBW.rUNz5G4/aqKoK/XKZlzGya'
            cur.execute("""
                INSERT INTO nguoi_dung (
                    id, email, mat_khau, ho_ten, so_dien_thoai, vai_tro,
                    dang_hoat_dong, da_xac_nhan
                ) VALUES (
                    '77777777-0000-0000-0000-000000000001',
                    'dieudo@nhaxekhach.com',
                    %s,
                    'Nguyễn Văn Điều Độ',
                    '0912345678',
                    'dieu_do_vien',
                    true,
                    true
                )
                ON CONFLICT (email) DO UPDATE SET
                    mat_khau = EXCLUDED.mat_khau,
                    vai_tro = EXCLUDED.vai_tro,
                    dang_hoat_dong = true,
                    da_xac_nhan = true;
            """, (mat_khau_123456,))

            print("8. Gán ho_so_can_bo_diem cho cán bộ...")
            cur.execute("""
                INSERT INTO ho_so_can_bo_diem (nguoi_dung_id, van_phong_id)
                SELECT id, '22222222-0000-0000-0000-000000000001'
                FROM nguoi_dung
                ON CONFLICT (nguoi_dung_id) DO UPDATE SET van_phong_id = EXCLUDED.van_phong_id;
            """)

            print("9. Seed các chuyến xe đa dạng cho toàn bộ UC...")
            now = datetime.now(timezone.utc)
            t_qua_gio = now - timedelta(minutes=15)
            t_2h = now + timedelta(hours=2)
            t_5h = now + timedelta(hours=5)
            t_24h = now + timedelta(hours=24)
            t_quakhu = now - timedelta(hours=3)

            cur.execute("""
                DELETE FROM chuyen_xe WHERE id IN (
                    '66666666-0000-0000-0000-000000000001',
                    '66666666-0000-0000-0000-000000000002',
                    '66666666-0000-0000-0000-000000000003',
                    '66666666-0000-0000-0000-000000000004',
                    '66666666-0000-0000-0000-000000000005',
                    '66666666-0000-0000-0000-000000000006',
                    '66666666-0000-0000-0000-000000000007',
                    '66666666-0000-0000-0000-000000000008'
                );
            """)

            cur.execute("""
                INSERT INTO chuyen_xe (
                    id, tuyen_id, chieu, loai_xe_id, xe_id, xe_thuc_te_id,
                    gio_khoi_hanh, trang_thai, dang_hoan, loai_su_co, ly_do_su_co, co_canh_bao_xung_dot_vi_tri
                ) VALUES
                    -- 1. UC-44: Chuyến cần gán xe (2h nữa, chưa có xe)
                    ('66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', NULL, NULL,
                     %s, 'chua_khoi_hanh', false, NULL, NULL, false),

                    -- 2. UC-45: Chuyến quá giờ chưa gán xe (để test job)
                    ('66666666-0000-0000-0000-000000000002', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', NULL, NULL,
                     %s, 'chua_khoi_hanh', false, NULL, NULL, false),

                    -- 3. UC-19: Chuyến gặp sự cố LỖI NHÀ XE (Hỏng hóc động cơ tại Km 45)
                    ('66666666-0000-0000-0000-000000000003', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000001', NULL,
                     %s, 'gap_su_co', false, 'loi_nha_xe', 'Nổ lốp và hỏng trục bánh sau tại Km 45 Cao tốc 5B', false),

                    -- 4. UC-19: Chuyến gặp sự cố KHÁCH QUAN (Sạt lở đèo Bảo Hà)
                    ('66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000002', 'xuoi', '33333333-0000-0000-0000-000000000002', '55555555-0000-0000-0000-000000000003', NULL,
                     %s, 'gap_su_co', false, 'loi_khach_quan', 'Sạt lở đất nghiêm trọng tại đèo Bảo Hà, cấm đường hoàn toàn', false),

                    -- 5. UC-20: Chuyến cần đổi xe trước giờ (chuyến bị cảnh báo xung đột vị trí do xe gặp nạn)
                    ('66666666-0000-0000-0000-000000000005', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000001', NULL,
                     %s, 'chua_khoi_hanh', false, NULL, NULL, true),

                    -- 6. UC-40: Chuyến ĐANG CÓ XE CHẠY THAY (xe_thuc_te_id = 29B-777.11)
                    ('66666666-0000-0000-0000-000000000006', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000004',
                     %s, 'chua_khoi_hanh', false, NULL, NULL, false),

                    -- 7. UC-39: Chuyến hoàn thành để có số liệu thống kê
                    ('66666666-0000-0000-0000-000000000007', '44444444-0000-0000-0000-000000000001', 'xuoi', '33333333-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000001', NULL,
                     %s, 'hoan_thanh', false, NULL, NULL, false);
            """, (t_2h, t_qua_gio, t_quakhu, t_quakhu, t_5h, t_24h, t_quakhu))

        conn.commit()
        print(">> Hoàn thành nạp dữ liệu test cho UC-44, 45, 19, 20, 40, 39 thành công!")
    except Exception as e:
        conn.rollback()
        print(f"Lỗi: {e}")
        raise
    finally:
        release_connection(conn)

if __name__ == "__main__":
    seed()
