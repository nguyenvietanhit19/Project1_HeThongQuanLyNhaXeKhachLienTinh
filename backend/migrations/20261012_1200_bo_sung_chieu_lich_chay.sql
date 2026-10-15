-- Sửa database cũ đã có lich_chay_dinh_ky nhưng thiếu cột chieu.
-- Nguyên nhân: migration tạo bảng dùng CREATE TABLE IF NOT EXISTS nên không
-- cập nhật cấu trúc nếu bảng đã được tạo từ seed/migration phiên bản cũ.

ALTER TABLE lich_chay_dinh_ky
    ADD COLUMN IF NOT EXISTS chieu TEXT;

-- Dữ liệu lịch cũ mặc định là chiều xuôi; lịch mới bắt buộc phải chọn chiều.
UPDATE lich_chay_dinh_ky
SET chieu = 'xuoi'
WHERE chieu IS NULL;

ALTER TABLE lich_chay_dinh_ky
    ALTER COLUMN chieu SET NOT NULL;

ALTER TABLE lich_chay_dinh_ky
    DROP CONSTRAINT IF EXISTS lich_chay_dinh_ky_chieu_check;

ALTER TABLE lich_chay_dinh_ky
    ADD CONSTRAINT lich_chay_dinh_ky_chieu_check
    CHECK (chieu IN ('xuoi', 'nguoc'));
