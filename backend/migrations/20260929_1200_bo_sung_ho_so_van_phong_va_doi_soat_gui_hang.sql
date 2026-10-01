-- Bổ sung phạm vi văn phòng cho nhân viên gửi hàng, thông tin liên hệ văn phòng
-- và lưu vết các khoản cước đã thu.

CREATE TABLE IF NOT EXISTS ho_so_can_bo_diem (
    nguoi_dung_id UUID PRIMARY KEY REFERENCES nguoi_dung(id) ON DELETE CASCADE,
    van_phong_id  UUID NOT NULL REFERENCES diem_don_tra(id)
);

CREATE INDEX IF NOT EXISTS idx_ho_so_can_bo_diem_van_phong
    ON ho_so_can_bo_diem (van_phong_id);

ALTER TABLE diem_don_tra
    ADD COLUMN IF NOT EXISTS sdt_lien_he TEXT NULL;

ALTER TABLE don_hang
    ADD COLUMN IF NOT EXISTS da_thu_tien BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS nhan_vien_thu_id UUID NULL REFERENCES nguoi_dung(id),
    ADD COLUMN IF NOT EXISTS ngay_thu TIMESTAMPTZ NULL;

-- Dữ liệu cũ không lưu trạng thái thu riêng. Khôi phục theo quy tắc nghiệp vụ:
-- gửi trả trước được thu tại quầy gửi; COD đã giao được thu tại quầy nhận.
UPDATE don_hang
SET da_thu_tien = true,
    nhan_vien_thu_id = nhan_vien_gui_id,
    ngay_thu = ngay_tao
WHERE phuong_thuc_thanh_toan = 'nguoi_gui_tra_truoc'
  AND da_thu_tien = false;

UPDATE don_hang
SET da_thu_tien = true,
    nhan_vien_thu_id = nhan_vien_nhan_id,
    ngay_thu = ngay_giao
WHERE phuong_thuc_thanh_toan = 'cod_nguoi_nhan_tra'
  AND trang_thai = 'da_giao'
  AND da_thu_tien = false;
