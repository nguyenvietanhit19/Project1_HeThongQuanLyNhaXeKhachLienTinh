-- Bảng nhat_ky_admin — DATABASE.md mục 6.2.
-- Nhật ký thao tác của quan_ly (tạo/khóa/mở khóa tài khoản, ...), phục vụ tra soát.
-- Hành động của quan_ly_nhan_su ghi ở bảng riêng nhat_ky_quan_ly_nhan_su, không ghi vào đây.
-- hanh_dong và doi_tuong_loai để TEXT tự do (không CHECK) vì bảng này dùng chung
-- cho nhiều nhóm chức năng của quan_ly (tuyến, giá, xe, biên chế, tài khoản...).
CREATE TABLE nhat_ky_admin (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id        UUID NOT NULL REFERENCES nguoi_dung(id),  -- phải vai_tro = quan_ly, kiểm tra ở Service
    hanh_dong       TEXT NOT NULL,
    doi_tuong_loai  TEXT NOT NULL,
    doi_tuong_id    UUID NOT NULL,
    ghi_chu         TEXT NULL,  -- VD lý do khóa / mở khóa tài khoản
    thoi_gian       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Xem thao tác của một quan_ly.
CREATE INDEX nhat_ky_admin_theo_nguoi_thuc_hien
    ON nhat_ky_admin (admin_id, thoi_gian DESC);

-- Tra lịch sử một tài khoản/đối tượng cụ thể.
CREATE INDEX nhat_ky_admin_theo_doi_tuong
    ON nhat_ky_admin (doi_tuong_loai, doi_tuong_id, thoi_gian DESC);
