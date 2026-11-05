-- Bổ sung thông tin nguồn bán và nhân viên tạo/thu tiền cho vé quầy.
ALTER TABLE ve
    ADD COLUMN IF NOT EXISTS nhan_vien_ban_id UUID NULL REFERENCES nguoi_dung(id),
    ADD COLUMN IF NOT EXISTS nhan_vien_thu_id UUID NULL REFERENCES nguoi_dung(id),
    ADD COLUMN IF NOT EXISTS kenh_ban TEXT NULL CHECK (kenh_ban IS NULL OR kenh_ban IN ('tai_quay', 'hotline'));

CREATE INDEX IF NOT EXISTS ve_nhan_vien_ban_ngay_idx
    ON ve (nhan_vien_ban_id, ngay_tao DESC);
CREATE INDEX IF NOT EXISTS ve_sdt_khach_vang_lai_idx
    ON ve (sdt_khach_vang_lai);
