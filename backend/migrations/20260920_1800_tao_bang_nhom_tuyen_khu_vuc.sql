-- Bảng nhom_tuyen_khu_vuc — mở rộng thiết kế nhom_tuyen: mỗi nhóm tuyến giờ
-- gắn với 1 danh sách khu vực CÓ THỨ TỰ dọc hành trình vật lý (không giới
-- hạn đúng 2 tỉnh — có thể nhiều khu vực nếu tuyến đi qua nhiều tỉnh).
--
-- Dùng để: (1) khi tạo tuyến, chỉ được chọn điểm dừng thuộc khu vực đã có
-- trong nhóm; (2) thứ tự điểm dừng trong tuyến phải khớp thứ tự khu vực
-- của nhóm (tăng dần hoặc giảm dần — 2 chiều đi/về của cùng 1 nhóm),
-- không được chọn xen kẽ lộn xộn. Validate ở services/dia_diem_service.py.

CREATE TABLE IF NOT EXISTS nhom_tuyen_khu_vuc (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhom_tuyen_id UUID NOT NULL REFERENCES nhom_tuyen(id),
    khu_vuc_id    UUID NOT NULL REFERENCES khu_vuc(id),
    thu_tu        INTEGER NOT NULL,
    UNIQUE (nhom_tuyen_id, thu_tu),
    UNIQUE (nhom_tuyen_id, khu_vuc_id)
);
