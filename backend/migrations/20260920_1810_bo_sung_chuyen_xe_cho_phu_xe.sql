-- Bổ sung cột còn thiếu ở bảng chuyen_xe (đã tạo ở
-- 20260920_1600_tao_bang_gui_hang_va_hoan_tien.sql) — cần cho phần phụ xe
-- (UC-15 xác nhận xuất phát; UC-05/44 tính giá + sơ đồ ghế theo loại xe
-- ngay cả khi chưa gán xe cụ thể, NGHIEP_VU.md mục 3.5).
--
-- Đồng thời sửa CHECK constraint của trang_thai: bản 1600 dùng nhầm
-- 'den_noi' thay vì 'hoan_thanh' như NGHIEP_VU.md mục 4 quy định (vòng đời
-- chuyến: chua_khoi_hanh/dang_chay/gap_su_co/hoan_thanh/da_huy) — kiểm tra
-- toàn bộ code hiện có, chưa ai dùng giá trị 'den_noi' nên sửa an toàn,
-- không có dữ liệu nào bị vi phạm constraint mới.
--
-- Không sửa lại file 1600 (quy tắc vàng, HUONG_DAN_LAM_VIEC.md mục 4).

ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS gio_xac_nhan_xuat_phat TIMESTAMPTZ NULL;

-- Nullable (không NOT NULL như DATABASE.md mục 3.3 lý tưởng) — vì UC-18
-- (lịch chạy định kỳ, nguồn duy nhất sinh chuyen_xe) chưa ai xây, nên
-- chưa thể bắt buộc ngay bây giờ mà không biết chắc luồng insert tương
-- lai truyền giá trị này thế nào; siết lại NOT NULL khi UC-18 hoàn thiện.
ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS loai_xe_id UUID REFERENCES loai_xe(id);

ALTER TABLE chuyen_xe DROP CONSTRAINT IF EXISTS chuyen_xe_trang_thai_check;
ALTER TABLE chuyen_xe ADD CONSTRAINT chuyen_xe_trang_thai_check
    CHECK (trang_thai IN ('chua_khoi_hanh', 'dang_chay', 'gap_su_co', 'hoan_thanh', 'da_huy'));

-- Ghi nhận giờ thực tế phụ xe xác nhận đến từng điểm trung gian (UC-16,
-- NGHIEP_VU.md mục 8.2 điểm 5) — chưa ai tạo bảng này (không cần cho gửi
-- hàng/hoàn tiền/quản lý danh mục).
CREATE TABLE IF NOT EXISTS lich_su_diem_dung_chuyen (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id        UUID NOT NULL REFERENCES chuyen_xe(id),
    diem_don_tra_id  UUID NOT NULL REFERENCES diem_don_tra(id),
    gio_thuc_te      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chuyen_id, diem_don_tra_id)
);
