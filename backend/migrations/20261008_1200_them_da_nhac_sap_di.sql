-- Đánh dấu vé đã được nhắc "sắp đến giờ đi" (thông báo cho khách, NGHIEP_VU.md mục 8.1 điểm 4) để mỗi vé chỉ nhắc đúng 1 lần.
-- Job jobs/quet_nhac_sap_di.py bật cờ này sau khi gửi thông báo.
ALTER TABLE ve ADD COLUMN da_nhac_sap_di BOOLEAN NOT NULL DEFAULT false;
