-- Bảng còn thiếu để chuyen_xe (migration kế tiếp) có đủ khóa ngoại.
--
-- khu_vuc, diem_don_tra, tuyen, tuyen_diem_don_tra, loai_xe, xe đã có từ các
-- migration 20260920_*; nhan_su_van_hanh và xe_nhan_su đã có từ
-- 20260920_1800_tao_bang_nhan_su_van_hanh.sql — file này chỉ tạo phần CHƯA có:
-- lich_chay_dinh_ky (DATABASE.md mục 3.5).

-- Lịch chạy định kỳ (DATABASE.md mục 3.5) — khuôn để job sinh chuyen_xe mỗi
-- ngày (UC-18). Tuyến chạy được cả 2 chiều nên mỗi dòng lịch nói rõ chiều nào.
CREATE TABLE lich_chay_dinh_ky (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id        UUID NOT NULL REFERENCES tuyen(id),
    chieu           TEXT NOT NULL CHECK (chieu IN ('xuoi', 'nguoc')),
    gio_khoi_hanh   TIME NOT NULL,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    dang_ap_dung    BOOLEAN NOT NULL DEFAULT true,
    ngay_tao        TIMESTAMPTZ NOT NULL DEFAULT now()
);
