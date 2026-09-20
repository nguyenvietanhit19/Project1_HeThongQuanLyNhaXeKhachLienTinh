-- Bảng bổ sung — không có tên tường minh trong NGHIEP_VU.md (giống tiền
-- lệ thong_bao, DATABASE.md mục 5.3) — lưu vết báo cáo thất lạc/hư hỏng
-- của phụ xe (UC-28). don_hang đã được tạo ở
-- 20260920_1600_tao_bang_gui_hang_va_hoan_tien.sql, không tạo lại ở đây.
CREATE TABLE IF NOT EXISTS bao_cao_su_co_hang (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    don_hang_id       UUID NOT NULL REFERENCES don_hang(id),
    nguoi_bao_cao_id  UUID NOT NULL REFERENCES nguoi_dung(id),
    mo_ta             TEXT NOT NULL,
    ngay_tao          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS bao_cao_su_co_hang_don_hang_id_idx ON bao_cao_su_co_hang(don_hang_id);
