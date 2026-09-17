-- Bảng nguoi_dung — DATABASE.md mục 1.1
CREATE TABLE nguoi_dung (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT NOT NULL UNIQUE,
    mat_khau          TEXT NULL,  -- NULL với cán bộ vừa được mời, chưa tự đặt mật khẩu lần đầu
    ho_ten            TEXT NOT NULL,
    so_dien_thoai     TEXT NOT NULL,
    vai_tro           TEXT NOT NULL CHECK (vai_tro IN (
                          'khach_hang', 'phu_xe', 'nhan_vien_quay_ve', 'nhan_vien_gui_hang',
                          'dieu_do_vien', 'ke_toan', 'quan_ly_nhan_su', 'quan_ly'
                      )),
    dang_hoat_dong    BOOLEAN NOT NULL DEFAULT true,
    la_tai_khoan_goc  BOOLEAN NOT NULL DEFAULT false,
    da_xac_nhan       BOOLEAN NOT NULL DEFAULT false,
    ma_xac_nhan       TEXT NULL,
    ma_het_han        TIMESTAMPTZ NULL,
    ngay_tao          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tối đa 1 tài khoản quan_ly gốc trong toàn hệ thống (DATABASE.md mục 1.1, mục 9)
CREATE UNIQUE INDEX nguoi_dung_toi_da_1_tai_khoan_goc
    ON nguoi_dung ((true))
    WHERE la_tai_khoan_goc = true;

-- Seed tài khoản quan_ly gốc (DATABASE.md mục 9) — mat_khau để NULL, dùng
-- đúng chức năng "Quên mật khẩu" với email này để tự đặt mật khẩu lần đầu,
-- giống hệt cơ chế cán bộ được mời qua email (không cần hardcode hash mật
-- khẩu vào migration).
INSERT INTO nguoi_dung (email, ho_ten, so_dien_thoai, vai_tro, la_tai_khoan_goc, da_xac_nhan)
VALUES ('admin@nhaxekhach.local', 'Quan ly goc', '0000000000', 'quan_ly', true, true);
