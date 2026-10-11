-- Mã vé: mỗi vé (1 ghế trên 1 chặng) có mã riêng để khách đọc/tra cứu, ngoài mã đặt chỗ chung của cả lượt đặt.
-- Dạng VE000001 (sequence toàn cục, không tái dùng), tự sinh bằng trigger như các mã khác (khu vực, tuyến, chuyến...).
-- Mã không sửa được. Cũng dùng làm tiền tố mã giao dịch VNPay khi khách thanh toán riêng 1 vé tại quầy.

CREATE SEQUENCE ve_ma_seq;

ALTER TABLE ve ADD COLUMN ma_ve TEXT;

-- Vé đã có: đánh số theo thứ tự tạo
WITH thu_tu AS (SELECT id, row_number() OVER (ORDER BY ngay_tao, id) AS so FROM ve)
UPDATE ve SET ma_ve = 'VE' || CASE WHEN thu_tu.so < 1000000 THEN lpad(thu_tu.so::text, 6, '0') ELSE thu_tu.so::text END
FROM thu_tu WHERE ve.id = thu_tu.id;

SELECT setval('ve_ma_seq', GREATEST((SELECT count(*) FROM ve), 1), (SELECT count(*) FROM ve) > 0);

ALTER TABLE ve ALTER COLUMN ma_ve SET NOT NULL;
CREATE UNIQUE INDEX ve_ma_ve_key ON ve (ma_ve);

-- Lưu ý: lpad() của Postgres CẮT BỚT khi số dài hơn độ dài yêu cầu (lpad('1000000', 6, '0') = '100000' → trùng mã), nên chỉ
-- đệm số 0 khi còn dưới 7 chữ số; từ vé thứ 1.000.000 trở đi mã dài ra (VE1000000) thay vì bị cắt.
CREATE FUNCTION sinh_ma_ve() RETURNS trigger AS $$
DECLARE
    so BIGINT := nextval('ve_ma_seq');
BEGIN
    NEW.ma_ve := 'VE' || CASE WHEN so < 1000000 THEN lpad(so::text, 6, '0') ELSE so::text END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ve_sinh_ma BEFORE INSERT ON ve FOR EACH ROW EXECUTE FUNCTION sinh_ma_ve();

-- Mã vé không đổi sau khi tạo
CREATE FUNCTION giu_ma_ve() RETURNS trigger AS $$
BEGIN
    NEW.ma_ve := OLD.ma_ve;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ve_giu_ma BEFORE UPDATE ON ve FOR EACH ROW EXECUTE FUNCTION giu_ma_ve();
