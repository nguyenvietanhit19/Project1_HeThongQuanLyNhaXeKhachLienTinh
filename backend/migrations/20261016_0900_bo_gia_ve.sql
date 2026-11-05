-- Giá vé theo BỘ: mỗi tuyến có nhiều bộ giá nối tiếp nhau theo ngày áp dụng, mỗi bộ gồm giá của mọi cặp khu vực trên tuyến.
-- Bộ có hiệu lực từ ap_dung_tu đến hết ngày liền trước ap_dung_tu của bộ kế tiếp (không có ngày kết thúc riêng, không chồng nhau).
-- Bỏ giá theo mùa/dịp lễ: dòng giá có ap_dung_tu/ap_dung_den (giá có hạn) bị xóa ở bước chuyển đổi.
CREATE TABLE bo_gia_ve (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id    UUID NOT NULL REFERENCES tuyen(id),
    ap_dung_tu  DATE NOT NULL,
    ngay_tao    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tuyen_id, ap_dung_tu)
);
CREATE INDEX bo_gia_ve_tuyen_id_idx ON bo_gia_ve (tuyen_id);

ALTER TABLE gia_ve ADD COLUMN bo_gia_id UUID REFERENCES bo_gia_ve(id) ON DELETE CASCADE;

-- Mỗi tuyến đang có giá "thường" (không giới hạn ngày) → 1 bộ, áp dụng từ ngày sớm nhất cần dùng tới (chuyến đã sinh hoặc hôm nay)
INSERT INTO bo_gia_ve (tuyen_id, ap_dung_tu)
SELECT g.tuyen_id,
       LEAST(
           (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date,
           COALESCE((SELECT min((c.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) FROM chuyen_xe c WHERE c.tuyen_id = g.tuyen_id),
                    (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)
       )
FROM gia_ve g
WHERE g.ap_dung_tu IS NULL AND g.ap_dung_den IS NULL
GROUP BY g.tuyen_id;

UPDATE gia_ve g SET bo_gia_id = b.id
FROM bo_gia_ve b
WHERE b.tuyen_id = g.tuyen_id AND g.ap_dung_tu IS NULL AND g.ap_dung_den IS NULL;

DELETE FROM gia_ve WHERE bo_gia_id IS NULL;

ALTER TABLE gia_ve ALTER COLUMN bo_gia_id SET NOT NULL;
ALTER TABLE gia_ve DROP COLUMN ap_dung_tu;
ALTER TABLE gia_ve DROP COLUMN ap_dung_den;
ALTER TABLE gia_ve DROP COLUMN tuyen_id;
ALTER TABLE gia_ve ADD CONSTRAINT gia_ve_moi_cap_mot_gia_trong_bo UNIQUE (bo_gia_id, diem_di_id, diem_den_id);
CREATE INDEX gia_ve_bo_gia_id_idx ON gia_ve (bo_gia_id);
