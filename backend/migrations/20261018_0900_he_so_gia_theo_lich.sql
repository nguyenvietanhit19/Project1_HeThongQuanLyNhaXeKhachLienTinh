-- Hệ số giá chuyển từ LOẠI XE sang LỊCH CHẠY, và được CHỐT vào từng chuyến lúc sinh chuyến.
-- Sửa hệ số của lịch chỉ ảnh hưởng chuyến sinh sau; chuyến đã sinh giữ nguyên giá (tránh "khách xem 300k rồi thành 400k").
-- Giá vé = gia_goc (bộ giá) × chuyen_xe.he_so_gia. Dữ liệu cũ: lịch và chuyến nhận hệ số hiện tại của loại xe.
ALTER TABLE lich_chay_dinh_ky ADD COLUMN he_so_gia NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (he_so_gia > 0);
ALTER TABLE chuyen_xe ADD COLUMN he_so_gia NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (he_so_gia > 0);

UPDATE lich_chay_dinh_ky l SET he_so_gia = lx.he_so_gia FROM loai_xe lx WHERE lx.id = l.loai_xe_id;
UPDATE chuyen_xe c SET he_so_gia = lx.he_so_gia FROM loai_xe lx WHERE lx.id = c.loai_xe_id;

ALTER TABLE loai_xe DROP COLUMN he_so_gia;
