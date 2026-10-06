-- Bổ sung các cột còn thiếu vào chuyen_xe và tạo bảng lich_chay_dinh_ky.
-- Bảng chuyen_xe đã tồn tại từ migration 20260920_1600 (khung ban đầu) và
-- đã được thêm cột `chieu` ở 20260928_1000, nhưng còn thiếu:
--   loai_xe_id      — cam kết loại xe từ lich_chay_dinh_ky (DATABASE.md 3.3)
--   lich_chay_dinh_ky_id — liên kết về lịch sinh ra chuyến này
--   gio_xac_nhan_xuat_phat — thời điểm phụ xe bấm "xuất phát" (UC-15)
--   trang_thai check cũ sai (có 'den_noi', thiếu 'hoan_thanh') — fix lại
--
-- Bảng lich_chay_dinh_ky — DATABASE.md mục 3.5, UC-18 (Quản lý thiết lập).
-- Người 4 (Điều độ viên) đọc bảng này để job sinh chuyen_xe (UC-45 / sinh_chuyen_dinh_ky.py).
-- ============================================================================

-- 1. Thêm loai_xe_id vào chuyen_xe (nếu chưa có)
ALTER TABLE chuyen_xe
    ADD COLUMN IF NOT EXISTS loai_xe_id UUID REFERENCES loai_xe(id);

-- 2. Thêm lich_chay_dinh_ky_id (nullable — chuyến tạo thủ công có thể NULL)
ALTER TABLE chuyen_xe
    ADD COLUMN IF NOT EXISTS lich_chay_dinh_ky_id UUID;

-- 3. Thêm gio_xac_nhan_xuat_phat (UC-15, phụ xe xác nhận xuất phát)
ALTER TABLE chuyen_xe
    ADD COLUMN IF NOT EXISTS gio_xac_nhan_xuat_phat TIMESTAMPTZ;

-- 4. Fix constraint trang_thai: bảng cũ có 'den_noi' không đúng spec DATABASE.md.
--    Phải drop constraint cũ trước rồi add lại.
ALTER TABLE chuyen_xe DROP CONSTRAINT IF EXISTS chuyen_xe_trang_thai_check;
ALTER TABLE chuyen_xe ADD CONSTRAINT chuyen_xe_trang_thai_check
    CHECK (trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co', 'hoan_thanh', 'da_huy'));

-- 5. Tạo bảng lich_chay_dinh_ky (DATABASE.md mục 3.5)
CREATE TABLE IF NOT EXISTS lich_chay_dinh_ky (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id        UUID NOT NULL REFERENCES tuyen(id),
    chieu           TEXT NOT NULL CHECK (chieu IN ('xuoi', 'nguoc')),
    gio_khoi_hanh   TIME NOT NULL,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    dang_ap_dung    BOOLEAN NOT NULL DEFAULT true,
    ngay_tao        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Gán FK từ chuyen_xe.lich_chay_dinh_ky_id → lich_chay_dinh_ky(id)
--    (Làm sau khi bảng đã tồn tại)
ALTER TABLE chuyen_xe
    DROP CONSTRAINT IF EXISTS chuyen_xe_lich_chay_dinh_ky_id_fkey;
ALTER TABLE chuyen_xe
    ADD CONSTRAINT chuyen_xe_lich_chay_dinh_ky_id_fkey
    FOREIGN KEY (lich_chay_dinh_ky_id) REFERENCES lich_chay_dinh_ky(id);

-- 7. Tạo bảng lich_su_diem_dung_chuyen (DATABASE.md mục 3.4 — ghi nhận
--    giờ thực tế xe tới từng điểm, UC-16 phụ xe xác nhận tới điểm)
CREATE TABLE IF NOT EXISTS lich_su_diem_dung_chuyen (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id       UUID NOT NULL REFERENCES chuyen_xe(id),
    diem_don_tra_id UUID NOT NULL REFERENCES diem_don_tra(id),
    gio_thuc_te     TIMESTAMPTZ NOT NULL,
    UNIQUE (chuyen_id, diem_don_tra_id)
);

-- 8. Indexes bắt buộc (DATABASE.md mục bổ sung cần làm rõ mục 9)
CREATE INDEX IF NOT EXISTS idx_chuyen_xe_xe_id
    ON chuyen_xe (xe_id);
CREATE INDEX IF NOT EXISTS idx_chuyen_xe_chua_gan_xe
    ON chuyen_xe (xe_id) WHERE xe_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_chuyen_xe_trang_thai
    ON chuyen_xe (trang_thai);
CREATE INDEX IF NOT EXISTS idx_chuyen_xe_gio_khoi_hanh
    ON chuyen_xe (gio_khoi_hanh);
CREATE INDEX IF NOT EXISTS idx_lich_su_diem_dung_chuyen_id
    ON lich_su_diem_dung_chuyen (chuyen_id);
