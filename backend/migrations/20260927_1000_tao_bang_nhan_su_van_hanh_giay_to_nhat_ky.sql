-- Mở rộng nhan_su_van_hanh cho quản lý nhân sự (UC-47/48/49/50,
-- database_quanLyNhanSu.md mục 1) + tạo giay_to_nhan_su, nhat_ky_quan_ly_nhan_su.
--
-- Bảng nhan_su_van_hanh (cột gốc: ho_ten, so_dien_thoai, chuc_danh,
-- nguoi_dung_id) đã được tạo ở migration 20260920_1800_tao_bang_nhan_su_van_hanh.sql
-- — file này KHÔNG tạo lại mà chỉ thêm 7 cột mới + các ràng buộc.

ALTER TABLE nhan_su_van_hanh ADD COLUMN so_cccd           TEXT NULL;
ALTER TABLE nhan_su_van_hanh ADD COLUMN ngay_sinh         DATE NULL;
ALTER TABLE nhan_su_van_hanh ADD COLUMN anh_ho_so         TEXT NULL;  -- public_id trên Cloudinary, KHÔNG phải URL (services/luu_tru_anh_service.py)
ALTER TABLE nhan_su_van_hanh ADD COLUMN ngay_vao_lam      DATE NOT NULL DEFAULT current_date;
ALTER TABLE nhan_su_van_hanh ADD COLUMN trang_thai        TEXT NOT NULL DEFAULT 'dang_lam' CHECK (trang_thai IN ('dang_lam', 'da_nghi_viec'));
ALTER TABLE nhan_su_van_hanh ADD COLUMN ngay_nghi_viec    DATE NULL;
ALTER TABLE nhan_su_van_hanh ADD COLUMN ly_do_nghi_viec   TEXT NULL;

-- 1 tài khoản nguoi_dung chỉ gắn với tối đa 1 hồ sơ nhân sự; chỉ phụ xe mới
-- có tài khoản; đã nghỉ việc thì bắt buộc có ngày nghỉ (và ngược lại).
ALTER TABLE nhan_su_van_hanh ADD CONSTRAINT nhan_su_van_hanh_nguoi_dung_id_key UNIQUE (nguoi_dung_id);
ALTER TABLE nhan_su_van_hanh ADD CONSTRAINT nhan_su_van_hanh_chi_phu_xe_co_tai_khoan
    CHECK (chuc_danh = 'phu_xe' OR nguoi_dung_id IS NULL);
ALTER TABLE nhan_su_van_hanh ADD CONSTRAINT nhan_su_van_hanh_nghi_viec_hop_le
    CHECK ((trang_thai = 'da_nghi_viec') = (ngay_nghi_viec IS NOT NULL));

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
