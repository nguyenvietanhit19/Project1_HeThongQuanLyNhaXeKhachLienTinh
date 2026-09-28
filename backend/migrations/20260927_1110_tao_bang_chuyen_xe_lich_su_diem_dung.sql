-- chuyen_xe của điều độ viên (người 4, UC-19, 20, 39, 40, 44, 45 — NGHIEP_VU.md
-- mục 8.6, 12). Xem database_dieuDoVien.md mục 1-3 cho chi tiết nghiệp vụ và
-- các ràng buộc chỉ kiểm tra được ở Service.
--
-- Bảng chuyen_xe ĐÃ được tạo sẵn ở migration 20260920_1600 (bản tối thiểu
-- phục vụ khóa ngoại của ve/don_hang) — file này KHÔNG tạo lại mà chỉ bổ sung
-- các cột còn thiếu và sửa trang thái cho đúng DATABASE.md mục 3.3. Cột
-- "chieu" do migration 20260928_1000 thêm.

-- Loại xe CAM KẾT phục vụ chuyến (copy từ lich_chay_dinh_ky.loai_xe_id lúc
-- sinh chuyến) — dùng để bán vé/hiển thị sơ đồ ghế ngay cả khi chưa gán xe_id.
-- Khi gán xe_id, Service bắt buộc xe.loai_xe_id = chuyen_xe.loai_xe_id.
-- Chưa có code nào tạo chuyen_xe nên bảng rỗng; nếu có dòng cũ thì điền từ xe
-- gốc, còn dòng không có xe_id thì SET NOT NULL sẽ báo lỗi để xử lý tay.
ALTER TABLE chuyen_xe ADD COLUMN loai_xe_id UUID REFERENCES loai_xe(id);
UPDATE chuyen_xe c SET loai_xe_id = x.loai_xe_id FROM xe x WHERE c.xe_id = x.id;
ALTER TABLE chuyen_xe ALTER COLUMN loai_xe_id SET NOT NULL;

ALTER TABLE chuyen_xe ADD COLUMN lich_chay_dinh_ky_id UUID NULL REFERENCES lich_chay_dinh_ky(id);
ALTER TABLE chuyen_xe ADD COLUMN gio_xac_nhan_xuat_phat TIMESTAMPTZ NULL;

-- Trạng thái theo DATABASE.md mục 3.3: 'hoan_thanh' thay cho 'den_noi' ở bản tạm.
ALTER TABLE chuyen_xe DROP CONSTRAINT IF EXISTS chuyen_xe_trang_thai_check;
UPDATE chuyen_xe SET trang_thai = 'hoan_thanh' WHERE trang_thai = 'den_noi';
ALTER TABLE chuyen_xe ADD CONSTRAINT chuyen_xe_trang_thai_check
    CHECK (trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co', 'hoan_thanh', 'da_huy'));

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


-- Ghi giờ thực tế phụ xe xác nhận tới từng điểm trung gian (UC-16, người 3
-- gọi vào chuyen_xe_service.xac_nhan_toi_diem()) — dùng cập nhật ETA cho
-- khách đang chờ ở các điểm phía sau (DATABASE.md mục 3.4).
CREATE TABLE lich_su_diem_dung_chuyen (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id           UUID NOT NULL REFERENCES chuyen_xe(id),
    diem_don_tra_id     UUID NOT NULL REFERENCES diem_don_tra(id),  -- phải thuộc tuyen_diem_don_tra của tuyến chuyến này, kiểm tra ở Service
    gio_thuc_te         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (chuyen_id, diem_don_tra_id)
);
