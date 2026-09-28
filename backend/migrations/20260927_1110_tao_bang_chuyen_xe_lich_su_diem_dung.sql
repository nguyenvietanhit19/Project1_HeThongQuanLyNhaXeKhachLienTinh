-- Bảng thật sự của điều độ viên (người 4, CONTRIBUTING.md mục 2 —
-- chuyen_xe_repository/chuyen_xe_service). Phục vụ UC-19, 20, 39, 40, 44, 45
-- (NGHIEP_VU.md mục 8.6, 12). Xem database_dieuDoVien.md mục 1-3 cho chi
-- tiết nghiệp vụ và các ràng buộc chỉ kiểm tra được ở Service (không diễn
-- tả bằng CHECK/constraint DB).
--
-- Phụ thuộc khóa ngoại vào các bảng ở migration liền trước
-- (20260927_1100_tao_bang_danh_muc_xe_tuyen_tam_thoi.sql) — file đó là
-- TẠM THỜI (đọc cảnh báo ở đầu file đó), file này thì KHÔNG tạm thời.

CREATE TABLE chuyen_xe (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id                        UUID NOT NULL REFERENCES tuyen(id),

    -- Xe gốc — quyết định biên chế tài xế/phụ xe và vị trí suy luận cho các
    -- chuyến sau (NGHIEP_VU.md mục 3.2/3.3). NULL = chưa gán xe (UC-44);
    -- tới gio_khoi_hanh mà vẫn NULL thì job (UC-45) tự bật dang_hoan.
    xe_id                           UUID NULL REFERENCES xe(id),

    -- Loại xe CAM KẾT (copy từ lich_chay_dinh_ky.loai_xe_id lúc sinh chuyến)
    -- — dùng để bán vé/hiển thị sơ đồ ghế ngay cả khi chưa gán xe_id. Khi
    -- gán xe_id, Service bắt buộc xe.loai_xe_id = chuyen_xe.loai_xe_id.
    loai_xe_id                      UUID NOT NULL REFERENCES loai_xe(id),

    lich_chay_dinh_ky_id            UUID NULL REFERENCES lich_chay_dinh_ky(id),

    -- Xe thực tế chạy thay nếu khác xe_id (UC-20, đổi xe khi hỏng trước giờ
    -- chạy) — KHÔNG đổi xe_id gốc, biên chế tài xế/phụ xe không xáo trộn.
    -- NULL = đúng xe gốc đang chạy. Bắt buộc cùng loai_xe với xe_id — kiểm
    -- tra ở Service.
    xe_thuc_te_id                   UUID NULL REFERENCES xe(id),

    gio_khoi_hanh                   TIMESTAMPTZ NOT NULL,

    trang_thai                      TEXT NOT NULL DEFAULT 'chua_khoi_hanh'
                                        CHECK (trang_thai IN (
                                            'chua_khoi_hanh', 'dang_chay', 'gap_su_co',
                                            'hoan_thanh', 'da_huy'
                                        )),

    -- true khi đang chờ tìm xe thay thế trước giờ chạy — bật thủ công bởi
    -- điều độ viên (UC-20) hoặc tự động bởi job (UC-45 ⏱). KHÔNG BAO GIỜ tự
    -- chuyển da_huy chỉ vì hết xe thay thế (NGHIEP_VU.md mục 1/3.3).
    dang_hoan                       BOOLEAN NOT NULL DEFAULT false,

    gio_xac_nhan_xuat_phat          TIMESTAMPTZ NULL,
    gio_hoan_thanh                  TIMESTAMPTZ NULL,

    -- Set khi chuyển gap_su_co (UC-17, người 3 gọi vào) — quyết định toàn bộ
    -- nhánh xử lý ở UC-19: loi_nha_xe luôn tìm được xe thay thế cuối cùng
    -- (không có nhánh hủy); chỉ loi_khach_quan mới có thể dẫn tới da_huy.
    loai_su_co                      TEXT NULL CHECK (loai_su_co IN ('loi_nha_xe', 'loi_khach_quan')),
    ly_do_su_co                     TEXT NULL,

    -- Bật cho MỌI chuyến chua_khoi_hanh cùng xe_id ngay khi 1 chuyến trước
    -- của xe này chuyển gap_su_co giữa đường — điều độ viên xem lại và gỡ
    -- thủ công (UC-19/20), hệ thống không tự gỡ.
    co_canh_bao_xung_dot_vi_tri     BOOLEAN NOT NULL DEFAULT false,

    ngay_tao                        TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
