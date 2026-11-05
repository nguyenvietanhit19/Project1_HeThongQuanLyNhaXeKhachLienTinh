-- Mã nhân viên hiển thị trên vé: cấp một lần, không dùng lại khi tài khoản bị khóa.
CREATE SEQUENCE seq_ma_nhan_vien START WITH 1;

ALTER TABLE nguoi_dung ADD COLUMN ma_nhan_vien TEXT;

CREATE FUNCTION cap_ma_nhan_vien() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    so_moi BIGINT;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.ma_nhan_vien IS NOT NULL
           AND NEW.ma_nhan_vien IS DISTINCT FROM OLD.ma_nhan_vien THEN
            RAISE EXCEPTION 'Không được sửa mã nhân viên đã cấp';
        END IF;
    END IF;

    IF NEW.vai_tro <> 'khach_hang' AND NEW.ma_nhan_vien IS NULL THEN
        so_moi := nextval('seq_ma_nhan_vien');
        NEW.ma_nhan_vien := 'NV' || lpad(so_moi::TEXT, GREATEST(6, length(so_moi::TEXT)), '0');
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER nguoi_dung_cap_ma_nhan_vien
    BEFORE INSERT OR UPDATE OF vai_tro, ma_nhan_vien ON nguoi_dung
    FOR EACH ROW EXECUTE FUNCTION cap_ma_nhan_vien();

-- Tài khoản đã tồn tại được gán mã theo thứ tự tạo; tài khoản khách hàng không có mã nhân viên.
DO $$
DECLARE
    nhan_vien RECORD;
BEGIN
    FOR nhan_vien IN
        SELECT id FROM nguoi_dung
        WHERE vai_tro <> 'khach_hang' AND ma_nhan_vien IS NULL
        ORDER BY ngay_tao, id
    LOOP
        UPDATE nguoi_dung SET ma_nhan_vien = NULL WHERE id = nhan_vien.id;
    END LOOP;
END $$;

ALTER TABLE nguoi_dung ADD CONSTRAINT nguoi_dung_ma_nhan_vien_theo_vai_tro
    CHECK ((vai_tro = 'khach_hang' AND ma_nhan_vien IS NULL)
        OR (vai_tro <> 'khach_hang' AND ma_nhan_vien ~ '^NV[0-9]{6,}$'));
CREATE UNIQUE INDEX nguoi_dung_ma_nhan_vien_unique ON nguoi_dung(ma_nhan_vien);
