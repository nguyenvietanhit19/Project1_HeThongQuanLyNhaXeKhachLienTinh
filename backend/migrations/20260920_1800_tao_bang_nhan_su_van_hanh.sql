-- Hồ sơ tài xế/phụ xe + biên chế xe — DATABASE.md mục 1.4, 1.5
CREATE TABLE nhan_su_van_hanh (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ho_ten         TEXT NOT NULL,
    so_dien_thoai  TEXT NOT NULL,
    chuc_danh      TEXT NOT NULL CHECK (chuc_danh IN ('tai_xe', 'phu_xe')),
    nguoi_dung_id  UUID NULL REFERENCES nguoi_dung(id)  -- chỉ có giá trị khi chuc_danh = 'phu_xe'
);

CREATE TABLE xe_nhan_su (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    xe_id                 UUID NOT NULL REFERENCES xe(id),
    nhan_su_van_hanh_id   UUID NOT NULL REFERENCES nhan_su_van_hanh(id),
    loai                  TEXT NOT NULL CHECK (loai IN ('co_dinh', 'tam_thoi')),
    trang_thai            TEXT NOT NULL DEFAULT 'dang_hoat_dong' CHECK (trang_thai IN ('dang_hoat_dong', 'tam_nghi')),
    ngay_bat_dau          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ngay_ket_thuc         TIMESTAMPTZ NULL
);

CREATE INDEX xe_nhan_su_nhan_su_id_idx ON xe_nhan_su(nhan_su_van_hanh_id, trang_thai);
CREATE INDEX xe_nhan_su_xe_id_idx ON xe_nhan_su(xe_id);
