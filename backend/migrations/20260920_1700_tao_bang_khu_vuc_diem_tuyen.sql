-- Bảng khu_vuc/diem_don_tra/nhom_tuyen/tuyen — DATABASE.md mục 2.1-2.3
-- UC-29 (Quản lý khu vực), UC-30 (Quản lý điểm đón/trả) — đã được migration
-- 20260920_1600_tao_bang_gui_hang_va_hoan_tien.sql tạo trước (Trinh cần làm
-- FK tiền đề cho don_hang/ve trước khi ai làm domain này), dùng
-- IF NOT EXISTS nên không tạo lại ở đây, chỉ bổ sung phần còn thiếu.
--
-- Bảng thật sự còn thiếu: tuyen_diem_don_tra (DATABASE.md mục 2.4) —
-- UC-31 (Tạo tuyến), chưa ai tạo vì không cần cho gửi hàng/hoàn tiền.

CREATE TABLE IF NOT EXISTS tuyen_diem_don_tra (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id                 UUID NOT NULL REFERENCES tuyen(id),
    diem_don_tra_id          UUID NOT NULL REFERENCES diem_don_tra(id),
    thu_tu                   INTEGER NOT NULL,
    thoi_gian_du_kien_phut   INTEGER NOT NULL,
    UNIQUE (tuyen_id, thu_tu),
    UNIQUE (tuyen_id, diem_don_tra_id)
);

-- Index tra cứu điểm đón/trả theo khu vực (UC-30 — lọc theo khu_vuc_id),
-- và tuyến theo nhóm tuyến (UC-31) — 2 bảng đã tồn tại nhưng chưa có index này.
CREATE INDEX IF NOT EXISTS diem_don_tra_khu_vuc_id_idx ON diem_don_tra(khu_vuc_id);
CREATE INDEX IF NOT EXISTS tuyen_nhom_tuyen_id_idx ON tuyen(nhom_tuyen_id);
