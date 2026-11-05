-- Nâng cấp phân hệ Gửi hàng: chống tạo trùng đơn + lịch sử trạng thái đơn.
-- Chạy SAU 20261004_0900.

-- 1. Khóa chống trùng: FE sinh 1 UUID cho mỗi lần "mở form → tạo đơn". Bấm 2 lần,
--    mạng chậm rồi gửi lại, hay F5 giữa chừng đều gửi cùng khóa → BE trả lại đơn đã
--    tạo thay vì tạo đơn thứ hai. Khóa chỉ có nghĩa trong phạm vi 1 nhân viên.
ALTER TABLE don_hang
    ADD COLUMN IF NOT EXISTS khoa_chong_trung TEXT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_don_hang_khoa_chong_trung
    ON don_hang (nhan_vien_gui_id, khoa_chong_trung)
    WHERE khoa_chong_trung IS NOT NULL;

-- 2. Lịch sử trạng thái đơn. Ghi bằng trigger nên mọi đường đổi trạng thái (nhân viên
--    giao hàng, phụ xe chất/dỡ, job quét 7/14 ngày, code của vai trò khác) đều được
--    ghi, không phụ thuộc từng service có nhớ ghi hay không.
--    nguoi_thuc_hien_id = NULL nghĩa là hệ thống tự chuyển (job UC-46).
CREATE TABLE IF NOT EXISTS lich_su_trang_thai_don (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    don_hang_id         UUID NOT NULL REFERENCES don_hang(id) ON DELETE CASCADE,
    tu_trang_thai       TEXT NULL,
    den_trang_thai      TEXT NOT NULL,
    nguoi_thuc_hien_id  UUID NULL REFERENCES nguoi_dung(id) ON DELETE SET NULL,
    thoi_gian           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lich_su_trang_thai_don
    ON lich_su_trang_thai_don (don_hang_id, thoi_gian);

-- Người thực hiện: repository gọi set_config('app.nguoi_dung_id', ..., true) trong cùng
-- transaction trước khi UPDATE; thiếu thì NULL (hệ thống).
CREATE OR REPLACE FUNCTION ghi_lich_su_trang_thai_don() RETURNS trigger AS $$
DECLARE
    nguoi TEXT := NULLIF(current_setting('app.nguoi_dung_id', true), '');
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO lich_su_trang_thai_don (don_hang_id, tu_trang_thai, den_trang_thai, nguoi_thuc_hien_id, thoi_gian)
        VALUES (NEW.id, NULL, NEW.trang_thai, NEW.nhan_vien_gui_id, NEW.ngay_tao);
    ELSIF NEW.trang_thai IS DISTINCT FROM OLD.trang_thai THEN
        INSERT INTO lich_su_trang_thai_don (don_hang_id, tu_trang_thai, den_trang_thai, nguoi_thuc_hien_id)
        VALUES (NEW.id, OLD.trang_thai, NEW.trang_thai, nguoi::uuid);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_lich_su_trang_thai_don ON don_hang;
CREATE TRIGGER trg_lich_su_trang_thai_don
    AFTER INSERT OR UPDATE OF trang_thai ON don_hang
    FOR EACH ROW EXECUTE FUNCTION ghi_lich_su_trang_thai_don();

-- 3. Đơn đã có trước migration: dựng lại 2 mốc biết chắc (tạo đơn, giao hàng).
--    Các mốc trung gian (lên xe, dỡ hàng) không có dữ liệu gốc nên không dựng.
INSERT INTO lich_su_trang_thai_don (don_hang_id, tu_trang_thai, den_trang_thai, nguoi_thuc_hien_id, thoi_gian)
SELECT d.id, NULL, 'cho_van_chuyen', d.nhan_vien_gui_id, d.ngay_tao
FROM don_hang d
WHERE NOT EXISTS (SELECT 1 FROM lich_su_trang_thai_don l WHERE l.don_hang_id = d.id);

INSERT INTO lich_su_trang_thai_don (don_hang_id, tu_trang_thai, den_trang_thai, nguoi_thuc_hien_id, thoi_gian)
SELECT d.id, 'cho_lay', 'da_giao', d.nhan_vien_nhan_id, d.ngay_giao
FROM don_hang d
WHERE d.trang_thai = 'da_giao' AND d.ngay_giao IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM lich_su_trang_thai_don l
      WHERE l.don_hang_id = d.id AND l.den_trang_thai = 'da_giao'
  );
