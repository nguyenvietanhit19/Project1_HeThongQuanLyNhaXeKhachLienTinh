-- Nhắc lại văn phòng nhận khi hàng đã tới hơn 24 giờ mà vẫn chưa gọi báo được người nhận
-- (NGHIEP_VU_GUI_HANG.md mục 5.2, KE_HOACH_SUA_GUI_HANG.md mục 7). Trước đây chỉ báo 1 lần lúc phụ xe dỡ
-- hàng, sau đó im lặng tới mốc cảnh báo 7 ngày. Cờ này bảo đảm mỗi đơn chỉ được nhắc đúng 1 lần
-- (job quet_hang_ton chạy mỗi giờ). Chạy SAU 20261019_0900.

ALTER TABLE don_hang ADD COLUMN IF NOT EXISTS da_nhac_goi_bao BOOLEAN NOT NULL DEFAULT false;
