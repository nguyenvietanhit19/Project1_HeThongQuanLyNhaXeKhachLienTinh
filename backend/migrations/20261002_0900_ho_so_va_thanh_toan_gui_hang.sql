-- Gắn nhân viên quầy với văn phòng và lưu vết thu cước gửi hàng.
CREATE TABLE IF NOT EXISTS ho_so_can_bo_diem (
    nguoi_dung_id UUID PRIMARY KEY REFERENCES nguoi_dung(id) ON DELETE CASCADE,
    van_phong_id UUID NOT NULL REFERENCES diem_don_tra(id)
);

ALTER TABLE don_hang
    ADD COLUMN IF NOT EXISTS da_thu_tien BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS thoi_gian_thu TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS nhan_vien_thu_id UUID NULL REFERENCES nguoi_dung(id);

-- Trước migration, quy ước của giao diện là "người gửi trả trước" đã thu tại quầy.
UPDATE don_hang
SET da_thu_tien = true, thoi_gian_thu = ngay_tao, nhan_vien_thu_id = nhan_vien_gui_id
WHERE phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc' AND da_thu_tien = false;

CREATE TABLE IF NOT EXISTS lich_su_lien_he_don_hang (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    don_hang_id UUID NOT NULL REFERENCES don_hang(id) ON DELETE CASCADE,
    nhan_vien_id UUID NOT NULL REFERENCES nguoi_dung(id),
    doi_tuong TEXT NOT NULL CHECK (doi_tuong IN ('nguoi_nhan', 'nguoi_gui', 'quan_ly')),
    ket_qua TEXT NOT NULL CHECK (ket_qua IN ('da_lien_he', 'khong_lien_he_duoc', 'da_bao_quan_ly')),
    ghi_chu TEXT NULL,
    ngay_tao TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lich_su_lien_he_don_hang_idx
    ON lich_su_lien_he_don_hang(don_hang_id, ngay_tao DESC);

ALTER TABLE thong_bao
    ADD COLUMN IF NOT EXISTS don_hang_id UUID NULL REFERENCES don_hang(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ho_so_can_bo_diem_van_phong_idx
    ON ho_so_can_bo_diem(van_phong_id);
