-- Mã chuyến đổi theo giờ khi QUẢN LÝ sửa giờ (UC-48), nhưng KHÔNG đổi khi giờ bị dời vì lý do
-- khác (điều độ viên dời giờ lúc "đang hoãn" — UC-20/45 — chuyến lúc đó đã có khách).
--
-- Lý do: quản lý chỉ sửa giờ được khi chuyến còn "sạch" (chưa gán xe, chưa khởi hành, chưa có vé)
-- nên chưa ai ngoài hệ thống dùng tới mã; cho mã đổi theo giờ giữ giờ trong mã luôn khớp giờ thực và
-- tránh trùng mã với chuyến sinh sau. Cơ chế: repository bật cờ giao dịch app.doi_ma_theo_gio = 'on'
-- (SET LOCAL) ngay trước lệnh UPDATE; trigger chỉ tính lại mã khi thấy cờ này, còn lại giữ nguyên mã cũ.

-- 1. Công thức mã chuyến dùng chung cho INSERT và cho lúc sửa giờ
CREATE FUNCTION tao_ma_chuyen(p_tuyen_id UUID, p_loai_xe_id UUID, p_gio TIMESTAMPTZ, p_chieu TEXT) RETURNS TEXT AS $$
DECLARE
    v_ma_tuyen TEXT;
    v_ma_loai_xe TEXT;
BEGIN
    SELECT ma INTO v_ma_tuyen FROM tuyen WHERE id = p_tuyen_id;
    SELECT ma INTO v_ma_loai_xe FROM loai_xe WHERE id = p_loai_xe_id;
    IF v_ma_tuyen IS NULL OR v_ma_loai_xe IS NULL THEN
        RAISE EXCEPTION 'Tuyến hoặc loại xe của chuyến không tồn tại' USING ERRCODE = '23503';
    END IF;
    RETURN v_ma_tuyen || '-' || v_ma_loai_xe || '-'
        || to_char(p_gio AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYMMDD-HH24MI')
        || '-' || CASE p_chieu WHEN 'xuoi' THEN 'DI' ELSE 'VE' END;
END;
$$ LANGUAGE plpgsql;

-- 2. Trigger INSERT dùng hàm chung (hành vi giữ nguyên)
CREATE OR REPLACE FUNCTION sinh_ma_chuyen_xe() RETURNS trigger AS $$
BEGIN
    NEW.ma := tao_ma_chuyen(NEW.tuyen_id, NEW.loai_xe_id, NEW.gio_khoi_hanh, NEW.chieu);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Trigger UPDATE riêng cho chuyen_xe: giữ mã cũ, trừ khi cờ app.doi_ma_theo_gio = 'on'
CREATE FUNCTION cap_nhat_ma_chuyen_xe() RETURNS trigger AS $$
BEGIN
    IF current_setting('app.doi_ma_theo_gio', true) = 'on' THEN
        NEW.ma := tao_ma_chuyen(NEW.tuyen_id, NEW.loai_xe_id, NEW.gio_khoi_hanh, NEW.chieu);
    ELSE
        NEW.ma := OLD.ma;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER chuyen_xe_giu_ma ON chuyen_xe;
CREATE TRIGGER chuyen_xe_cap_nhat_ma BEFORE UPDATE ON chuyen_xe FOR EACH ROW EXECUTE FUNCTION cap_nhat_ma_chuyen_xe();
