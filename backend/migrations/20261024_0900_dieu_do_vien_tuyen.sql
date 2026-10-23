-- Điều độ viên phụ trách theo TUYẾN (DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md): quan hệ nhiều–nhiều giữa tài khoản điều độ viên và tuyến.
-- Quản lý phân công ở trang Tuyến. Xóa tài khoản/tuyến thì dòng phân công đi theo. Điều độ viên KHÔNG còn gắn văn phòng (ho_so_can_bo_diem).
CREATE TABLE dieu_do_vien_tuyen (
    nguoi_dung_id UUID NOT NULL REFERENCES nguoi_dung(id) ON DELETE CASCADE,
    tuyen_id      UUID NOT NULL REFERENCES tuyen(id) ON DELETE CASCADE,
    ngay_tao      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (nguoi_dung_id, tuyen_id)
);
CREATE INDEX dieu_do_vien_tuyen_tuyen_idx ON dieu_do_vien_tuyen (tuyen_id);
