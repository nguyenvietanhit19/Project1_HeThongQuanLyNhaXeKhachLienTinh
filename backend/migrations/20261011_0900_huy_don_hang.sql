-- Hủy đơn gửi hàng (đợt B, KE_HOACH_SUA_GUI_HANG.md mục 6): nhân viên văn phòng GỬI hủy đơn
-- khi hàng còn trong kho (cho_van_chuyen, chưa gắn chuyến), trả lại kiện hàng cho người gửi;
-- đơn trả trước đã thu thì hoàn đủ cước bằng tiền mặt tại quầy (so_tien_hoan).
-- Không xóa dòng, không dùng lại mã vận đơn. Trigger trg_lich_su_trang_thai_don (20261005_0900)
-- tự ghi mốc cho_van_chuyen → da_huy. Chạy SAU 20261008_1200.

ALTER TABLE don_hang DROP CONSTRAINT IF EXISTS don_hang_trang_thai_check;
ALTER TABLE don_hang
    ADD CONSTRAINT don_hang_trang_thai_check
    CHECK (trang_thai IN ('cho_van_chuyen', 'da_len_xe', 'cho_lay', 'da_giao', 'qua_han_luu_kho', 'da_huy'));

ALTER TABLE don_hang
    ADD COLUMN IF NOT EXISTS ly_do_huy TEXT NULL
        CHECK (ly_do_huy IN ('khach_doi_y', 'nhap_sai_thong_tin', 'hang_khong_du_dieu_kien', 'khac')),
    ADD COLUMN IF NOT EXISTS ghi_chu_huy TEXT NULL,
    ADD COLUMN IF NOT EXISTS nhan_vien_huy_id UUID NULL REFERENCES nguoi_dung(id),
    ADD COLUMN IF NOT EXISTS thoi_gian_huy TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS so_tien_hoan NUMERIC(12, 0) NULL;

-- Đơn đã hủy phải có đủ lý do, người hủy, thời điểm; đơn chưa hủy không được mang thông tin hủy.
ALTER TABLE don_hang DROP CONSTRAINT IF EXISTS don_hang_thong_tin_huy_day_du;
ALTER TABLE don_hang
    ADD CONSTRAINT don_hang_thong_tin_huy_day_du CHECK (
        (trang_thai = 'da_huy') = (ly_do_huy IS NOT NULL AND nhan_vien_huy_id IS NOT NULL AND thoi_gian_huy IS NOT NULL)
    );

-- Đối soát tiền hoàn theo nhân viên / ngày.
CREATE INDEX IF NOT EXISTS idx_don_hang_hoan_tien
    ON don_hang (nhan_vien_huy_id, thoi_gian_huy)
    WHERE so_tien_hoan IS NOT NULL;
