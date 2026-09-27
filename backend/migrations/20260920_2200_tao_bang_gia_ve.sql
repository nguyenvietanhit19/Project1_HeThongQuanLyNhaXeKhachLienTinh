-- Bảng gia_ve — DATABASE.md mục 2.5, UC-33 (Cấu hình giá vé).
--
-- Giá gốc chỉ phụ thuộc (tuyến, cặp điểm đi/điểm đến) — không phụ thuộc
-- điểm đón/trả cụ thể, không phụ thuộc loại xe (hệ số loai_xe.he_so_gia
-- nhân vào lúc bán, không lưu ở đây). ap_dung_tu/ap_dung_den NULL = áp
-- dụng vô thời hạn, dùng để cấu hình thêm giá theo mùa/dịp lễ.

CREATE TABLE IF NOT EXISTS gia_ve (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id     UUID NOT NULL REFERENCES tuyen(id),
    diem_di_id   UUID NOT NULL REFERENCES khu_vuc(id),
    diem_den_id  UUID NOT NULL REFERENCES khu_vuc(id),
    gia_goc      NUMERIC(12,0) NOT NULL,
    ap_dung_tu   DATE NULL,
    ap_dung_den  DATE NULL,
    UNIQUE (tuyen_id, diem_di_id, diem_den_id, ap_dung_tu)
);

CREATE INDEX IF NOT EXISTS gia_ve_tuyen_id_idx ON gia_ve(tuyen_id);
