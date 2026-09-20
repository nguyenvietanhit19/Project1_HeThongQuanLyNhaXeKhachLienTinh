-- ====================================================================
-- Migration: Tạo các bảng cho phân hệ Gửi hàng và Kế toán hoàn tiền
-- Bám sát thiết kế tại DATABASE.md mục 2, 3, 4, 5
-- ====================================================================

-- 1. Bảng tiền đề: khu_vuc & diem_don_tra (nếu chưa có)
CREATE TABLE IF NOT EXISTS khu_vuc (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten         TEXT NOT NULL,
    tinh_thanh  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diem_don_tra (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    khu_vuc_id  UUID NOT NULL REFERENCES khu_vuc(id) ON DELETE CASCADE,
    ten         TEXT NOT NULL,
    dia_chi     TEXT NOT NULL,
    loai        TEXT NOT NULL CHECK (loai IN ('van_phong', 'diem_dung'))
);

-- 2. Bảng tiền đề: nhom_tuyen, tuyen, chuyen_xe, ve (nếu chưa có)
CREATE TABLE IF NOT EXISTS nhom_tuyen (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tuyen (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhom_tuyen_id UUID NOT NULL REFERENCES nhom_tuyen(id) ON DELETE CASCADE,
    ten           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loai_xe (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten         TEXT NOT NULL,
    he_so_gia   NUMERIC(4,2) NOT NULL DEFAULT 1.0,
    so_do_ghe   JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS xe (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bien_so       TEXT NOT NULL UNIQUE,
    loai_xe_id    UUID NOT NULL REFERENCES loai_xe(id),
    trang_thai    TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong', 'bao_tri', 'ngung_su_dung')),
    diem_goc_id   UUID NOT NULL REFERENCES diem_don_tra(id),
    nhom_tuyen_id UUID NULL REFERENCES nhom_tuyen(id)
);

CREATE TABLE IF NOT EXISTS chuyen_xe (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id                    UUID NOT NULL REFERENCES tuyen(id),
    xe_id                       UUID NULL REFERENCES xe(id),
    xe_thuc_te_id               UUID NULL REFERENCES xe(id),
    gio_khoi_hanh               TIMESTAMPTZ NOT NULL,
    trang_thai                  TEXT NOT NULL DEFAULT 'chua_khoi_hanh' CHECK (trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'den_noi', 'gap_su_co', 'da_huy')),
    dang_hoan                   BOOLEAN NOT NULL DEFAULT false,
    gio_hoan_thanh              TIMESTAMPTZ NULL,
    loai_su_co                  TEXT NULL CHECK (loai_su_co IN ('loi_nha_xe', 'loi_khach_quan')),
    ly_do_su_co                 TEXT NULL,
    co_canh_bao_xung_dot_vi_tri BOOLEAN NOT NULL DEFAULT false,
    ngay_tao                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ve (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id                   UUID NOT NULL REFERENCES chuyen_xe(id),
    so_ghe                      TEXT NOT NULL,
    diem_don_id                 UUID NOT NULL REFERENCES diem_don_tra(id),
    diem_tra_id                 UUID NOT NULL REFERENCES diem_don_tra(id),
    khach_hang_id               UUID NULL REFERENCES nguoi_dung(id),
    ten_khach_vang_lai          TEXT NULL,
    sdt_khach_vang_lai          TEXT NULL,
    gia                         NUMERIC(12,0) NOT NULL,
    ma_dat_cho                  TEXT NOT NULL,
    la_ve_dat_coc               BOOLEAN NOT NULL DEFAULT false,
    loai_hinh_thanh_toan        TEXT NOT NULL CHECK (loai_hinh_thanh_toan IN ('thanh_toan_ngay', 'thanh_toan_tai_quay')),
    phuong_thuc_thanh_toan      TEXT NULL CHECK (phuong_thuc_thanh_toan IN ('tien_mat', 'chuyen_khoan')),
    ma_giao_dich_cong_thanh_toan TEXT NULL,
    trang_thai                  TEXT NOT NULL DEFAULT 'giu_cho' CHECK (trang_thai IN ('giu_cho', 'het_han', 'da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den', 'da_huy')),
    gio_bat_dau_dem_han         TIMESTAMPTZ NULL,
    han_giu_cho_den             TIMESTAMPTZ NULL,
    gio_thanh_toan              TIMESTAMPTZ NULL,
    gio_len_xe                  TIMESTAMPTZ NULL,
    gio_xuong_xe                TIMESTAMPTZ NULL,
    gio_huy                     TIMESTAMPTZ NULL,
    ngay_tao                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================================
-- 3. BẢNG CHÍNH: Phân hệ Gửi hàng (DATABASE.md mục 5)
-- ====================================================================

-- 3.1. Danh mục loại hàng
CREATE TABLE IF NOT EXISTS loai_hang (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten         TEXT NOT NULL UNIQUE,
    la_hang_cam BOOLEAN NOT NULL DEFAULT false
);

-- Seed các loại hàng mẫu
INSERT INTO loai_hang (ten, la_hang_cam) VALUES
    ('Hàng thông thường', false),
    ('Hàng dễ vỡ', false),
    ('Tài liệu / Giấy tờ', false),
    ('Hàng đông lạnh / Thực phẩm', false),
    ('Chất dễ cháy nổ / Hàng cấm', true)
ON CONFLICT (ten) DO NOTHING;

-- 3.2. Bảng don_hang (Đơn hàng gửi)
CREATE TABLE IF NOT EXISTS don_hang (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ma_van_don              TEXT NOT NULL UNIQUE,
    tuyen_id                UUID NOT NULL REFERENCES tuyen(id),
    chuyen_id               UUID NULL REFERENCES chuyen_xe(id),
    diem_gui_id             UUID NOT NULL REFERENCES diem_don_tra(id),
    diem_nhan_id            UUID NOT NULL REFERENCES diem_don_tra(id),
    can_nang_kg             NUMERIC(8,2) NOT NULL,
    dai_cm                  NUMERIC(8,2) NULL,
    rong_cm                 NUMERIC(8,2) NULL,
    cao_cm                  NUMERIC(8,2) NULL,
    loai_hang_id            UUID NOT NULL REFERENCES loai_hang(id),
    gia_cuoc                NUMERIC(12,0) NOT NULL,
    ten_nguoi_gui           TEXT NOT NULL,
    sdt_nguoi_gui           TEXT NOT NULL,
    ten_nguoi_nhan          TEXT NOT NULL,
    sdt_nguoi_nhan          TEXT NOT NULL,
    phuong_thuc_thanh_toan  TEXT NOT NULL CHECK (phuong_thuc_thanh_toan IN ('nguoi_gui_tra_truoc', 'cod_nguoi_nhan_tra')),
    trang_thai              TEXT NOT NULL DEFAULT 'cho_van_chuyen' CHECK (trang_thai IN ('cho_van_chuyen', 'da_len_xe', 'cho_lay', 'da_giao', 'qua_han_luu_kho')),
    nhan_vien_gui_id        UUID NOT NULL REFERENCES nguoi_dung(id),
    nhan_vien_nhan_id       UUID NULL REFERENCES nguoi_dung(id),
    thoi_gian_den_diem_nhan TIMESTAMPTZ NULL,
    da_thong_bao_nguoi_nhan BOOLEAN NOT NULL DEFAULT false,
    co_canh_bao_cho_lau     BOOLEAN NOT NULL DEFAULT false,
    ngay_tao                TIMESTAMPTZ NOT NULL DEFAULT now(),
    ngay_giao               TIMESTAMPTZ NULL
);

-- Index tối ưu truy vấn cho đơn hàng
CREATE INDEX IF NOT EXISTS idx_don_hang_tuyen_cho_xep 
    ON don_hang (tuyen_id) WHERE chuyen_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_don_hang_chuyen 
    ON don_hang (chuyen_id);

CREATE INDEX IF NOT EXISTS idx_don_hang_cho_lay 
    ON don_hang (trang_thai, thoi_gian_den_diem_nhan) WHERE trang_thai = 'cho_lay';

-- ====================================================================
-- 4. BẢNG CHÍNH: Kế toán & Hoàn tiền (DATABASE.md mục 4.1)
-- ====================================================================

CREATE TABLE IF NOT EXISTS lich_su_hoan_tien (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ve_id                   UUID NOT NULL UNIQUE REFERENCES ve(id),
    ly_do                   TEXT NOT NULL CHECK (ly_do IN ('bat_kha_khang_khong_hoan_thanh', 'loi_nha_xe_giua_duong', 'hoan_truoc_gio_chay', 'tu_dong_hoan_qua_3_tieng')),
    so_tien                 NUMERIC(12,0) NOT NULL,
    trang_thai              TEXT NOT NULL DEFAULT 'cho_xu_ly' CHECK (trang_thai IN ('cho_xu_ly', 'da_hoan_tu_dong', 'da_hoan_chuyen_khoan_thu_cong')),
    ma_giao_dich_hoan_tien  TEXT NULL,
    nhan_vien_xu_ly_id      UUID NULL REFERENCES nguoi_dung(id),
    so_tai_khoan_nhan       TEXT NULL,
    ten_ngan_hang_nhan      TEXT NULL,
    ten_chu_tai_khoan_nhan  TEXT NULL,
    thoi_gian_xac_dinh      TIMESTAMPTZ NOT NULL DEFAULT now(),
    thoi_gian_hoan_xong     TIMESTAMPTZ NULL
);

-- Index danh sách chờ hoàn tiền cho Kế toán
CREATE INDEX IF NOT EXISTS idx_hoan_tien_cho_xu_ly 
    ON lich_su_hoan_tien (trang_thai) WHERE trang_thai = 'cho_xu_ly';

