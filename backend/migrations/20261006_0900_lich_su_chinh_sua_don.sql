-- Sửa thông tin liên hệ của đơn gửi hàng (đợt A): mỗi lần sửa tên/SĐT người gửi hoặc
-- người nhận đều để lại 1 dòng nhật ký (trường nào, cũ → mới, ai sửa, lúc nào, lý do).
-- Chạy SAU 20261005_0900. Bảng chỉ INSERT — repository không có hàm sửa/xóa nhật ký.

CREATE TABLE IF NOT EXISTS lich_su_chinh_sua_don (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    don_hang_id         UUID NOT NULL REFERENCES don_hang(id) ON DELETE CASCADE,
    truong              TEXT NOT NULL
                        CHECK (truong IN ('ten_nguoi_gui', 'sdt_nguoi_gui', 'ten_nguoi_nhan', 'sdt_nguoi_nhan')),
    gia_tri_cu          TEXT NULL,
    gia_tri_moi         TEXT NOT NULL,
    nguoi_thuc_hien_id  UUID NOT NULL REFERENCES nguoi_dung(id),
    ly_do               TEXT NULL,
    thoi_gian           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lich_su_chinh_sua_don
    ON lich_su_chinh_sua_don (don_hang_id, thoi_gian);
