-- ====================================================================
-- Migration: Bổ sung index + bảng tuyen_diem_don_tra còn thiếu
-- Bám sát DATABASE.md mục 2.4, 3.3, 4
-- Bảng ve và các bảng tiền đề cơ bản đã được tạo trong migration trước.
-- File này chỉ thêm những gì còn thiếu.
-- ====================================================================

-- 1. Bảng tuyen_diem_don_tra (DATABASE.md mục 2.4) — còn thiếu trong migration trước
CREATE TABLE IF NOT EXISTS tuyen_diem_don_tra (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id                UUID NOT NULL REFERENCES tuyen(id) ON DELETE CASCADE,
    diem_don_tra_id         UUID NOT NULL REFERENCES diem_don_tra(id),
    thu_tu                  INTEGER NOT NULL,   -- Dùng cho cơ chế chống trùng ghế [thu_tu, thu_tu)
    thoi_gian_du_kien_phut  INTEGER NOT NULL,   -- Số phút lệch so với gio_khoi_hanh của chuyen_xe
    UNIQUE (tuyen_id, thu_tu),
    UNIQUE (tuyen_id, diem_don_tra_id)
);

-- 2. Bảng gia_ve (DATABASE.md mục 2.5) — còn thiếu
CREATE TABLE IF NOT EXISTS gia_ve (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id    UUID NOT NULL REFERENCES tuyen(id) ON DELETE CASCADE,
    diem_di_id  UUID NOT NULL REFERENCES khu_vuc(id),
    diem_den_id UUID NOT NULL REFERENCES khu_vuc(id),
    gia_goc     NUMERIC(12,0) NOT NULL,
    ap_dung_tu  DATE NULL,
    ap_dung_den DATE NULL,
    UNIQUE (tuyen_id, diem_di_id, diem_den_id, ap_dung_tu)
);

-- 3. Bảng lich_chay_dinh_ky (DATABASE.md mục 3.5) — còn thiếu
CREATE TABLE IF NOT EXISTS lich_chay_dinh_ky (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id        UUID NOT NULL REFERENCES tuyen(id) ON DELETE CASCADE,
    gio_khoi_hanh   TIME NOT NULL,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    dang_ap_dung    BOOLEAN NOT NULL DEFAULT true,
    ngay_tao        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Bổ sung cột còn thiếu vào chuyen_xe (DATABASE.md mục 3.3)
ALTER TABLE chuyen_xe
    ADD COLUMN IF NOT EXISTS loai_xe_id           UUID REFERENCES loai_xe(id),
    ADD COLUMN IF NOT EXISTS lich_chay_dinh_ky_id UUID NULL REFERENCES lich_chay_dinh_ky(id),
    ADD COLUMN IF NOT EXISTS gio_xac_nhan_xuat_phat TIMESTAMPTZ NULL;

-- Sửa CHECK constraint trang_thai của chuyen_xe cho đúng DATABASE.md
-- (bản trước có 'den_noi' không đúng, bản đúng là 'hoan_thanh')
ALTER TABLE chuyen_xe DROP CONSTRAINT IF EXISTS chuyen_xe_trang_thai_check;
ALTER TABLE chuyen_xe
    ADD CONSTRAINT chuyen_xe_trang_thai_check
    CHECK (trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co', 'hoan_thanh', 'da_huy'));

-- 5. Bảng lich_su_diem_dung_chuyen (DATABASE.md mục 3.4)
CREATE TABLE IF NOT EXISTS lich_su_diem_dung_chuyen (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id       UUID NOT NULL REFERENCES chuyen_xe(id) ON DELETE CASCADE,
    diem_don_tra_id UUID NOT NULL REFERENCES diem_don_tra(id),
    gio_thuc_te     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chuyen_id, diem_don_tra_id)
);

-- 6. Bảng ho_so_khach_hang (DATABASE.md mục 1.2)
CREATE TABLE IF NOT EXISTS ho_so_khach_hang (
    nguoi_dung_id           UUID PRIMARY KEY REFERENCES nguoi_dung(id) ON DELETE CASCADE,
    khoa_thanh_toan_tai_quay BOOLEAN NOT NULL DEFAULT false,
    bi_khoa                 BOOLEAN NOT NULL DEFAULT false,
    ly_do_khoa              TEXT NULL
);

-- 7. Index bắt buộc trên bảng ve — ARCHITECTURE.md mục 4, DATABASE.md mục 4
-- KHÔNG tạo UNIQUE (chuyen_id, so_ghe) — cố ý, DATABASE.md mục 0
CREATE INDEX IF NOT EXISTS idx_ve_chuyen_ghe
    ON ve (chuyen_id, so_ghe);

-- Index hỗ trợ job quét vé hết hạn (UC-14, ARCHITECTURE.md mục 5)
CREATE INDEX IF NOT EXISTS idx_ve_het_han_check
    ON ve (trang_thai, han_giu_cho_den)
    WHERE trang_thai = 'giu_cho' AND han_giu_cho_den IS NOT NULL;

-- Index hỗ trợ tìm vé theo khách hàng cho trang lịch sử vé
CREATE INDEX IF NOT EXISTS idx_ve_khach_hang
    ON ve (khach_hang_id)
    WHERE khach_hang_id IS NOT NULL;
