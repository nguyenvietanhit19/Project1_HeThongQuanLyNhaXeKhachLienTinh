-- Mã hiển thị tự sinh cho khu vực / điểm đón-trả / tuyến / loại xe / chuyến xe.
-- id UUID giữ nguyên làm khóa chính + khóa ngoại; "ma" chỉ để người đọc, tra cứu.
--
--   khu_vuc       KV001                       (sequence toàn cục)
--   diem_don_tra  KV001-DT001                 (đếm riêng từng khu vực — khu_vuc.so_diem_da_cap)
--   tuyen         T001                        (sequence toàn cục)
--   loai_xe       LX001                       (sequence toàn cục)
--   chuyen_xe     T001-LX001-260930-0630-DI   (tuyến-loại xe-ngày giờ khởi hành-chiều)
--
-- Sinh mã bằng trigger BEFORE INSERT để mọi đường INSERT đều có mã mà không phải
-- sửa từng repository. Mã chốt lúc tạo, không bao giờ đổi (trigger BEFORE UPDATE
-- giữ nguyên ma) và số đã cấp không tái sử dụng kể cả khi xóa bản ghi.
-- Mã chuyến gồm cả loại xe vì 1 tuyến có thể có 2 chuyến cùng chiều, cùng giờ,
-- khác loại xe. Giờ tính theo Asia/Ho_Chi_Minh (session Postgres mặc định UTC).

-- 1. Cột + sequence ------------------------------------------------------
ALTER TABLE khu_vuc      ADD COLUMN ma TEXT;
ALTER TABLE khu_vuc      ADD COLUMN so_diem_da_cap INTEGER NOT NULL DEFAULT 0;
ALTER TABLE diem_don_tra ADD COLUMN ma TEXT;
ALTER TABLE tuyen        ADD COLUMN ma TEXT;
ALTER TABLE loai_xe      ADD COLUMN ma TEXT;
ALTER TABLE chuyen_xe    ADD COLUMN ma TEXT;

CREATE SEQUENCE seq_ma_khu_vuc;
CREATE SEQUENCE seq_ma_tuyen;
CREATE SEQUENCE seq_ma_loai_xe;

-- 2. Điền mã cho dữ liệu cũ (theo thứ tự ổn định) -----------------------
UPDATE khu_vuc k SET ma = 'KV' || lpad(t.stt::text, 3, '0')
FROM (SELECT id, row_number() OVER (ORDER BY tinh_thanh, ten, id) AS stt FROM khu_vuc) t
WHERE k.id = t.id;
SELECT setval('seq_ma_khu_vuc', GREATEST((SELECT count(*) FROM khu_vuc), 1), (SELECT count(*) FROM khu_vuc) > 0);

UPDATE diem_don_tra d SET ma = k.ma || '-DT' || lpad(t.stt::text, 3, '0')
FROM (SELECT id, row_number() OVER (PARTITION BY khu_vuc_id ORDER BY ten, id) AS stt FROM diem_don_tra) t,
     khu_vuc k
WHERE d.id = t.id AND k.id = d.khu_vuc_id;
UPDATE khu_vuc k SET so_diem_da_cap = (SELECT count(*) FROM diem_don_tra d WHERE d.khu_vuc_id = k.id);

UPDATE tuyen x SET ma = 'T' || lpad(t.stt::text, 3, '0')
FROM (SELECT id, row_number() OVER (ORDER BY ngay_tao, ten, id) AS stt FROM tuyen) t
WHERE x.id = t.id;
SELECT setval('seq_ma_tuyen', GREATEST((SELECT count(*) FROM tuyen), 1), (SELECT count(*) FROM tuyen) > 0);

UPDATE loai_xe x SET ma = 'LX' || lpad(t.stt::text, 3, '0')
FROM (SELECT id, row_number() OVER (ORDER BY ten, id) AS stt FROM loai_xe) t
WHERE x.id = t.id;
SELECT setval('seq_ma_loai_xe', GREATEST((SELECT count(*) FROM loai_xe), 1), (SELECT count(*) FROM loai_xe) > 0);

UPDATE chuyen_xe c
SET ma = t.ma || '-' || l.ma || '-'
      || to_char(c.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYMMDD-HH24MI')
      || '-' || CASE c.chieu WHEN 'xuoi' THEN 'DI' ELSE 'VE' END
FROM tuyen t, loai_xe l
WHERE t.id = c.tuyen_id AND l.id = c.loai_xe_id;

-- 3. Ràng buộc ------------------------------------------------------------
ALTER TABLE khu_vuc      ALTER COLUMN ma SET NOT NULL;
ALTER TABLE diem_don_tra ALTER COLUMN ma SET NOT NULL;
ALTER TABLE tuyen        ALTER COLUMN ma SET NOT NULL;
ALTER TABLE loai_xe      ALTER COLUMN ma SET NOT NULL;
ALTER TABLE chuyen_xe    ALTER COLUMN ma SET NOT NULL;
ALTER TABLE khu_vuc      ADD CONSTRAINT khu_vuc_ma_key      UNIQUE (ma);
ALTER TABLE diem_don_tra ADD CONSTRAINT diem_don_tra_ma_key UNIQUE (ma);
ALTER TABLE tuyen        ADD CONSTRAINT tuyen_ma_key        UNIQUE (ma);
ALTER TABLE loai_xe      ADD CONSTRAINT loai_xe_ma_key      UNIQUE (ma);
ALTER TABLE chuyen_xe    ADD CONSTRAINT chuyen_xe_ma_key    UNIQUE (ma);

-- 4. Trigger sinh mã (BEFORE INSERT) -------------------------------------
CREATE FUNCTION sinh_ma_khu_vuc() RETURNS trigger AS $$
BEGIN
    NEW.ma := 'KV' || lpad(nextval('seq_ma_khu_vuc')::text, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION sinh_ma_tuyen() RETURNS trigger AS $$
BEGIN
    NEW.ma := 'T' || lpad(nextval('seq_ma_tuyen')::text, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION sinh_ma_loai_xe() RETURNS trigger AS $$
BEGIN
    NEW.ma := 'LX' || lpad(nextval('seq_ma_loai_xe')::text, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- UPDATE ... RETURNING khóa dòng khu_vuc nên 2 người cùng thêm điểm vào 1 khu
-- vực được xếp hàng, không bao giờ trùng số.
CREATE FUNCTION sinh_ma_diem_don_tra() RETURNS trigger AS $$
DECLARE
    v_ma_khu_vuc TEXT;
    v_so INTEGER;
BEGIN
    UPDATE khu_vuc SET so_diem_da_cap = so_diem_da_cap + 1
    WHERE id = NEW.khu_vuc_id
    RETURNING ma, so_diem_da_cap INTO v_ma_khu_vuc, v_so;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Khu vực % không tồn tại', NEW.khu_vuc_id USING ERRCODE = '23503';
    END IF;
    NEW.ma := v_ma_khu_vuc || '-DT' || lpad(v_so::text, 3, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION sinh_ma_chuyen_xe() RETURNS trigger AS $$
DECLARE
    v_ma_tuyen TEXT;
    v_ma_loai_xe TEXT;
BEGIN
    SELECT ma INTO v_ma_tuyen FROM tuyen WHERE id = NEW.tuyen_id;
    SELECT ma INTO v_ma_loai_xe FROM loai_xe WHERE id = NEW.loai_xe_id;
    IF v_ma_tuyen IS NULL OR v_ma_loai_xe IS NULL THEN
        RAISE EXCEPTION 'Tuyến hoặc loại xe của chuyến không tồn tại' USING ERRCODE = '23503';
    END IF;
    NEW.ma := v_ma_tuyen || '-' || v_ma_loai_xe || '-'
           || to_char(NEW.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYMMDD-HH24MI')
           || '-' || CASE NEW.chieu WHEN 'xuoi' THEN 'DI' ELSE 'VE' END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER khu_vuc_sinh_ma      BEFORE INSERT ON khu_vuc      FOR EACH ROW EXECUTE FUNCTION sinh_ma_khu_vuc();
CREATE TRIGGER diem_don_tra_sinh_ma BEFORE INSERT ON diem_don_tra FOR EACH ROW EXECUTE FUNCTION sinh_ma_diem_don_tra();
CREATE TRIGGER tuyen_sinh_ma        BEFORE INSERT ON tuyen        FOR EACH ROW EXECUTE FUNCTION sinh_ma_tuyen();
CREATE TRIGGER loai_xe_sinh_ma      BEFORE INSERT ON loai_xe      FOR EACH ROW EXECUTE FUNCTION sinh_ma_loai_xe();
CREATE TRIGGER chuyen_xe_sinh_ma    BEFORE INSERT ON chuyen_xe    FOR EACH ROW EXECUTE FUNCTION sinh_ma_chuyen_xe();

-- 5. Trigger giữ nguyên mã khi UPDATE (mã không sửa được) ----------------
CREATE FUNCTION giu_nguyen_ma() RETURNS trigger AS $$
BEGIN
    NEW.ma := OLD.ma;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER khu_vuc_giu_ma      BEFORE UPDATE ON khu_vuc      FOR EACH ROW EXECUTE FUNCTION giu_nguyen_ma();
CREATE TRIGGER diem_don_tra_giu_ma BEFORE UPDATE ON diem_don_tra FOR EACH ROW EXECUTE FUNCTION giu_nguyen_ma();
CREATE TRIGGER tuyen_giu_ma        BEFORE UPDATE ON tuyen        FOR EACH ROW EXECUTE FUNCTION giu_nguyen_ma();
CREATE TRIGGER loai_xe_giu_ma      BEFORE UPDATE ON loai_xe      FOR EACH ROW EXECUTE FUNCTION giu_nguyen_ma();
CREATE TRIGGER chuyen_xe_giu_ma    BEFORE UPDATE ON chuyen_xe    FOR EACH ROW EXECUTE FUNCTION giu_nguyen_ma();

-- Mã điểm gắn với khu vực (KV001-DT...) nên khu vực của điểm không được đổi
-- sau khi tạo — chặn cả ở DB để không đường nào lách được.
CREATE FUNCTION chan_doi_khu_vuc_diem() RETURNS trigger AS $$
BEGIN
    IF NEW.khu_vuc_id IS DISTINCT FROM OLD.khu_vuc_id THEN
        RAISE EXCEPTION 'Không được đổi khu vực của điểm đón/trả sau khi tạo' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER diem_don_tra_chan_doi_khu_vuc BEFORE UPDATE ON diem_don_tra FOR EACH ROW EXECUTE FUNCTION chan_doi_khu_vuc_diem();
