-- chuyen_xe của điều độ viên (người 4, UC-19, 20, 39, 40, 44, 45 — NGHIEP_VU.md
-- mục 8.6, 12). Xem database_dieuDoVien.md mục 1-3 cho chi tiết nghiệp vụ.
--
-- Bảng chuyen_xe đã được tạo ở 20260920_1600 và bổ sung ở 20260920_1810
-- (gio_xac_nhan_xuat_phat, loai_xe_id nullable, CHECK trang_thai dùng
-- 'hoan_thanh', bảng lich_su_diem_dung_chuyen) — file này KHÔNG lặp lại các
-- phần đó, chỉ hoàn thiện theo DATABASE.md mục 3.3: siết loai_xe_id thành
-- NOT NULL, thêm lich_chay_dinh_ky_id và các index. Cột "chieu" do migration
-- 20260928_1000 thêm.

-- Loại xe CAM KẾT phục vụ chuyến (copy từ lich_chay_dinh_ky.loai_xe_id lúc
-- sinh chuyến). Chưa có code nào tạo chuyen_xe nên bảng rỗng; nếu có dòng cũ
-- thì điền từ xe gốc, còn dòng không có xe_id thì SET NOT NULL sẽ báo lỗi.
ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS loai_xe_id UUID REFERENCES loai_xe(id);
UPDATE chuyen_xe c SET loai_xe_id = x.loai_xe_id FROM xe x WHERE c.xe_id = x.id AND c.loai_xe_id IS NULL;
ALTER TABLE chuyen_xe ALTER COLUMN loai_xe_id SET NOT NULL;

ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS lich_chay_dinh_ky_id UUID NULL REFERENCES lich_chay_dinh_ky(id);

-- Vị trí xe suy luận (DATABASE.md mục 7) truy vấn theo (xe_id, gio_khoi_hanh)
-- rất thường xuyên khi gán xe (UC-44) — index tổng hợp tránh full scan.
CREATE INDEX chuyen_xe_theo_xe_va_gio
    ON chuyen_xe (xe_id, gio_khoi_hanh);

-- UC-40: liệt kê nhanh mọi chuyến đang "chạy thay bằng xe khác" của 1 xe gốc.
CREATE INDEX chuyen_xe_dang_chay_thay
    ON chuyen_xe (xe_id)
    WHERE xe_thuc_te_id IS NOT NULL;

-- UC-44/3.5: danh sách "chuyến cần gán xe" — cũng là điều kiện job UC-45 quét.
CREATE INDEX chuyen_xe_chua_gan_xe
    ON chuyen_xe (xe_id)
    WHERE xe_id IS NULL;
