-- ⚠️ TẠM THỜI — đọc kỹ trước khi merge vào main.
--
-- nhan_su_van_hanh đúng ra thuộc domain của Trưởng nhóm (CONTRIBUTING.md
-- mục 2: xe/xe_nhan_su_repository) nhưng tính đến ngày viết file này chưa
-- có migration nào (ở bất kỳ nhánh nào trong repo) tạo ra bảng này. Migration
-- dưới đây tạo TRỌN VẸN nhan_su_van_hanh (cột gốc theo DATABASE.md mục 1.4
-- + cột mới cho quản lý nhân sự, database_quanLyNhanSu.md mục 1) để CÓ THỂ
-- TỰ TEST UC-47/48/49/50 trên nhánh này ngay, không phải chờ Trưởng nhóm.
--
-- TRƯỚC KHI MERGE: phải trao đổi với Trưởng nhóm. Nếu họ cũng tạo
-- "CREATE TABLE nhan_su_van_hanh" ở migration riêng của họ, 2 migration
-- cùng tạo 1 bảng sẽ lỗi "relation already exists" khi áp dụng chung trên
-- cùng 1 nhánh. Khi đó cần xóa đoạn CREATE TABLE này, đổi lại thành
-- ALTER TABLE ... ADD COLUMN cho đúng 7 cột mới, dựa trên bảng thật của họ.

CREATE TABLE nhan_su_van_hanh (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ho_ten            TEXT NOT NULL,
    so_dien_thoai     TEXT NOT NULL,
    chuc_danh         TEXT NOT NULL CHECK (chuc_danh IN ('tai_xe', 'phu_xe')),
    nguoi_dung_id     UUID NULL UNIQUE REFERENCES nguoi_dung(id),

    -- Cột mới cho quản lý nhân sự — database_quanLyNhanSu.md mục 1
    so_cccd           TEXT NULL,
    ngay_sinh         DATE NULL,
    anh_ho_so         TEXT NULL,  -- public_id trên Cloudinary, KHÔNG phải URL (services/luu_tru_anh_service.py)
    ngay_vao_lam      DATE NOT NULL DEFAULT current_date,
    trang_thai        TEXT NOT NULL DEFAULT 'dang_lam' CHECK (trang_thai IN ('dang_lam', 'da_nghi_viec')),
    ngay_nghi_viec    DATE NULL,
    ly_do_nghi_viec   TEXT NULL,

    CHECK (chuc_danh = 'phu_xe' OR nguoi_dung_id IS NULL),
    CHECK ((trang_thai = 'da_nghi_viec') = (ngay_nghi_viec IS NOT NULL))
);

-- CCCD trùng nhau là dữ liệu sai — nhưng nhiều dòng NULL (chưa nhập) không
-- được coi là trùng nhau, nên phải dùng partial unique index.
CREATE UNIQUE INDEX nhan_su_van_hanh_so_cccd_duy_nhat
    ON nhan_su_van_hanh (so_cccd)
    WHERE so_cccd IS NOT NULL;


-- Bảng giay_to_nhan_su — database_quanLyNhanSu.md mục 2.
-- Mỗi nhân sự tối đa 1 dòng cho mỗi loại giấy tờ — gia hạn thì UPDATE dòng
-- đó, không lưu lịch sử các lần gia hạn cũ.
CREATE TABLE giay_to_nhan_su (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhan_su_van_hanh_id         UUID NOT NULL REFERENCES nhan_su_van_hanh(id),
    loai                        TEXT NOT NULL CHECK (loai IN ('bang_lai', 'giay_kham_suc_khoe')),
    so_giay_to                  TEXT NULL,
    hang                        TEXT NULL,  -- chỉ dùng cho bang_lai (VD D, E)
    ngay_cap                    DATE NULL,
    ngay_het_han                DATE NOT NULL,
    anh_giay_to                 TEXT NULL,  -- public_id trên Cloudinary, KHÔNG phải URL
    da_canh_bao_sap_het_han     BOOLEAN NOT NULL DEFAULT false,
    da_canh_bao_het_han         BOOLEAN NOT NULL DEFAULT false,

    UNIQUE (nhan_su_van_hanh_id, loai)
);

-- Job cảnh báo hết hạn (UC-48) quét theo mốc ngày này mỗi ngày.
CREATE INDEX giay_to_nhan_su_ngay_het_han ON giay_to_nhan_su (ngay_het_han);


-- Bảng nhat_ky_quan_ly_nhan_su — database_quanLyNhanSu.md mục 3.
-- TÁCH RIÊNG khỏi nhat_ky_admin (bảng đó chỉ ghi hành động của quan_ly) —
-- bảng này CHỈ ghi hành động do chính quan_ly_nhan_su thực hiện, không lẫn
-- lịch sử của vai trò khác kể cả khi cùng làm 1 việc giống nhau.
CREATE TABLE nhat_ky_quan_ly_nhan_su (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quan_ly_nhan_su_id      UUID NOT NULL REFERENCES nguoi_dung(id),  -- phải vai_tro = quan_ly_nhan_su, kiểm tra ở Service
    hanh_dong               TEXT NOT NULL CHECK (hanh_dong IN (
                                'tao_tai_khoan', 'khoa_tai_khoan', 'mo_khoa_tai_khoan',
                                'tao_ho_so_nhan_su', 'sua_ho_so_nhan_su', 'cho_nghi_viec'
                            )),
    doi_tuong_loai          TEXT NOT NULL CHECK (doi_tuong_loai IN ('nguoi_dung', 'nhan_su_van_hanh')),
    doi_tuong_id            UUID NOT NULL,
    ghi_chu                 TEXT NULL,
    thoi_gian               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- UC-50: quan_ly_nhan_su chỉ xem dòng của chính mình.
CREATE INDEX nhat_ky_quan_ly_nhan_su_theo_nguoi_thuc_hien
    ON nhat_ky_quan_ly_nhan_su (quan_ly_nhan_su_id, thoi_gian DESC);

-- Tra lịch sử 1 tài khoản/hồ sơ cụ thể (VD lý do khóa gần nhất, UC-38).
CREATE INDEX nhat_ky_quan_ly_nhan_su_theo_doi_tuong
    ON nhat_ky_quan_ly_nhan_su (doi_tuong_loai, doi_tuong_id, thoi_gian DESC);
