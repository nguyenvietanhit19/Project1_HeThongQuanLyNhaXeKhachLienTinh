-- Hồ sơ khách hàng — DATABASE.md mục 1.2. Không lưu bộ đếm no-show riêng
-- (tính động qua COUNT ve.trang_thai = 'khong_den', NGHIEP_VU.md mục 9) —
-- bảng này chỉ lưu 2 cờ hạn chế là HỆ QUẢ của việc vượt ngưỡng vi phạm.
CREATE TABLE ho_so_khach_hang (
    nguoi_dung_id             UUID PRIMARY KEY REFERENCES nguoi_dung(id) ON DELETE CASCADE,
    khoa_thanh_toan_tai_quay  BOOLEAN NOT NULL DEFAULT false,
    bi_khoa                   BOOLEAN NOT NULL DEFAULT false,
    ly_do_khoa                TEXT NULL
);

-- Bảng bổ sung — không có tên tường minh trong NGHIEP_VU.md (DATABASE.md
-- mục 6.1) — lưu lại thông báo để khách offline lúc sự kiện xảy ra vẫn
-- đọc lại được sau, thay vì chỉ đẩy qua WebSocket rồi mất.
CREATE TABLE thong_bao (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nguoi_nhan_id UUID NOT NULL REFERENCES nguoi_dung(id),
    noi_dung      TEXT NOT NULL,
    ve_id         UUID NULL REFERENCES ve(id),
    da_doc        BOOLEAN NOT NULL DEFAULT false,
    ngay_tao      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX thong_bao_nguoi_nhan_id_idx ON thong_bao(nguoi_nhan_id, ngay_tao DESC);
