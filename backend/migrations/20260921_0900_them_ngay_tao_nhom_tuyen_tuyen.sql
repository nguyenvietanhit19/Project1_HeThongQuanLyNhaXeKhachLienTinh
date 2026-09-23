-- Thêm ngay_tao cho nhom_tuyen/tuyen — hiển thị thời gian tạo trên giao
-- diện Quản lý (mục Nhóm tuyến/Tuyến). 2 bảng này tạo trước UC-36+ chưa
-- có cột này, khác các bảng còn lại đã có ngay_tao ngay từ đầu.

ALTER TABLE nhom_tuyen ADD COLUMN IF NOT EXISTS ngay_tao TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE tuyen ADD COLUMN IF NOT EXISTS ngay_tao TIMESTAMPTZ NOT NULL DEFAULT now();
