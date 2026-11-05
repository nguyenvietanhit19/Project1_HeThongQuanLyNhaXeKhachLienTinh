-- Chu trình = chuyến đi + chuyến về của cùng 1 chu kỳ (cùng cặp lịch, ngày đi D; chuyến về chạy ngày D + ngay_lech).
-- Điều độ viên gán xe cho cả chu trình (DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md), nên 2 chuyến phải biết nhau.
-- NULL = chuyến không sinh từ lịch định kỳ (không thuộc chu trình nào).
ALTER TABLE chuyen_xe ADD COLUMN chu_trinh_id UUID;
CREATE INDEX chuyen_xe_chu_trinh ON chuyen_xe (chu_trinh_id) WHERE chu_trinh_id IS NOT NULL;

-- Điền cho các chuyến đã sinh: chuyến về ghép với chuyến đi cùng cap_id có ngày đi = ngày về - ngay_lech (giờ Việt Nam).
-- Chuyến đi chưa có chuyến về (hoặc ngược lại) vẫn nhận chu_trinh_id riêng — chu trình chỉ có 1 chuyến.
WITH di AS (
    SELECT cx.id, l.cap_id, (cx.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay_di, gen_random_uuid() AS ct
    FROM chuyen_xe cx
    JOIN lich_chay_dinh_ky l ON l.id = cx.lich_chay_dinh_ky_id
    WHERE l.chieu = 'xuoi'
), ve AS (
    SELECT cx.id, l.cap_id, (cx.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - l.ngay_lech AS ngay_di
    FROM chuyen_xe cx
    JOIN lich_chay_dinh_ky l ON l.id = cx.lich_chay_dinh_ky_id
    WHERE l.chieu = 'nguoc'
), gan AS (
    SELECT di.id AS chuyen_id, di.ct FROM di
    UNION ALL
    SELECT ve.id, COALESCE(di.ct, gen_random_uuid())
    FROM ve LEFT JOIN di ON di.cap_id = ve.cap_id AND di.ngay_di = ve.ngay_di
)
UPDATE chuyen_xe c SET chu_trinh_id = gan.ct FROM gan WHERE c.id = gan.chuyen_id;
