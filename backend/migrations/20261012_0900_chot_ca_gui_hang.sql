-- Chốt ca tiền mặt của nhân viên gửi hàng (KE_HOACH_SUA_GUI_HANG.md mục 7, NGHIEP_VU_GUI_HANG.md mục 6).
-- Mỗi lần chốt: tiền mặt nhân viên đã thu (trả trước + COD) trừ tiền đã hoàn khi hủy đơn, trong khoảng
-- (tu_luc, den_luc] — tu_luc = den_luc của lần chốt trước của CHÍNH nhân viên đó (NULL = lần chốt đầu tiên,
-- tính từ trước tới nay). Nhân viên nhập số tiền đếm thực tế, hệ thống lưu chênh lệch. Bảng chỉ INSERT.
-- Chạy SAU 20261011_0900.

CREATE TABLE IF NOT EXISTS chot_ca_gui_hang (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhan_vien_id      UUID NOT NULL REFERENCES nguoi_dung(id),
    van_phong_id      UUID NULL REFERENCES diem_don_tra(id),
    tu_luc            TIMESTAMPTZ NULL,
    den_luc           TIMESTAMPTZ NOT NULL,
    so_don_tra_truoc  INTEGER NOT NULL DEFAULT 0,
    tien_tra_truoc    NUMERIC(14, 0) NOT NULL DEFAULT 0,
    so_don_cod        INTEGER NOT NULL DEFAULT 0,
    tien_cod          NUMERIC(14, 0) NOT NULL DEFAULT 0,
    so_don_hoan       INTEGER NOT NULL DEFAULT 0,
    tien_hoan         NUMERIC(14, 0) NOT NULL DEFAULT 0,
    tien_phai_co      NUMERIC(14, 0) NOT NULL,
    tien_thuc_dem     NUMERIC(14, 0) NOT NULL CHECK (tien_thuc_dem >= 0),
    chenh_lech        NUMERIC(14, 0) NOT NULL,
    ghi_chu           TEXT NULL,
    ngay_tao          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chot_ca_khoang_hop_le CHECK (tu_luc IS NULL OR tu_luc < den_luc),
    CONSTRAINT chot_ca_phai_co_dung CHECK (tien_phai_co = tien_tra_truoc + tien_cod - tien_hoan),
    CONSTRAINT chot_ca_chenh_lech_dung CHECK (chenh_lech = tien_thuc_dem - tien_phai_co),
    CONSTRAINT chot_ca_lech_phai_ghi_chu CHECK (chenh_lech = 0 OR (ghi_chu IS NOT NULL AND btrim(ghi_chu) <> '')),
    CONSTRAINT chot_ca_khong_trung UNIQUE (nhan_vien_id, den_luc)
);

CREATE INDEX IF NOT EXISTS idx_chot_ca_nhan_vien ON chot_ca_gui_hang (nhan_vien_id, den_luc DESC);
CREATE INDEX IF NOT EXISTS idx_chot_ca_van_phong ON chot_ca_gui_hang (van_phong_id, den_luc DESC);
