-- Mã nhân viên tự sinh: tiền tố theo vai trò + số thứ tự 4 chữ số (KE_HOACH_MA_NHAN_VIEN.md).
--
--   nguoi_dung.ma        phu_xe PX0001 | nhan_vien_quay_ve QV0001 | nhan_vien_gui_hang GH0001 | dieu_do_vien DDV0001
--                        ke_toan KT0001 | quan_ly_nhan_su NS0001 | quan_ly QL0001 (tài khoản GỐC cố định QL0000)
--                        khach_hang: KHÔNG có mã
--   nhan_su_van_hanh.ma  chỉ tài xế TX0001. Phụ xe dùng mã của tài khoản (nguoi_dung.ma), hồ sơ phụ xe không có mã riêng.
--
-- Mỗi vai trò đếm riêng bằng một sequence (số đã cấp không tái sử dụng, kể cả khi tài khoản bị khóa hay người nghỉ việc).
-- Mã được sinh bằng Python lúc tạo (repositories/ma_repository.py), như các mã khu vực / tuyến / vé;
-- migration này chỉ tạo cột + sequence, điền mã cho dữ liệu cũ và đặt các ràng buộc.
--
-- Cột `ma` cho phép trống vì cấu trúc dữ liệu (khách hàng và hồ sơ phụ xe không có mã riêng), KHÔNG có CHECK bắt buộc
-- cán bộ phải có mã (các script seed demo của người khác chèn thẳng vào bảng). CHECK ở đây chỉ kiểm tra ĐỊNH DẠNG khi có mã.

-- 1. Cột + sequence ------------------------------------------------------
ALTER TABLE nguoi_dung       ADD COLUMN ma TEXT NULL;
ALTER TABLE nhan_su_van_hanh ADD COLUMN ma TEXT NULL;

CREATE SEQUENCE seq_ma_tai_xe;
CREATE SEQUENCE seq_ma_phu_xe;
CREATE SEQUENCE seq_ma_quay_ve;
CREATE SEQUENCE seq_ma_gui_hang;
CREATE SEQUENCE seq_ma_dieu_do_vien;
CREATE SEQUENCE seq_ma_ke_toan;
CREATE SEQUENCE seq_ma_quan_ly_nhan_su;
CREATE SEQUENCE seq_ma_quan_ly;

-- 2. Điền mã cho dữ liệu cũ ---------------------------------------------
-- Phải điền TRƯỚC khi tạo trigger giữ mã ở mục 4, nếu không chính lệnh điền sẽ bị trigger hủy.
-- Số thứ tự đệm 0 nhưng KHÔNG cắt khi quá 9999 (lpad() của Postgres cắt bớt, từng làm mã bị trùng ở các bảng khác).

-- Tài khoản quản lý gốc: mã cố định, không dùng sequence.
UPDATE nguoi_dung SET ma = 'QL0000' WHERE la_tai_khoan_goc = true;

-- Cán bộ còn lại: đếm riêng từng vai trò, theo thứ tự tạo (ngay_tao, id).
UPDATE nguoi_dung n
SET ma = t.tien_to || CASE WHEN t.stt < 10000 THEN lpad(t.stt::text, 4, '0') ELSE t.stt::text END
FROM (
    SELECT nd.id, m.tien_to,
           row_number() OVER (PARTITION BY nd.vai_tro ORDER BY nd.ngay_tao, nd.id) AS stt
    FROM nguoi_dung nd
    JOIN (VALUES
        ('phu_xe',             'PX'),
        ('nhan_vien_quay_ve',  'QV'),
        ('nhan_vien_gui_hang', 'GH'),
        ('dieu_do_vien',       'DDV'),
        ('ke_toan',            'KT'),
        ('quan_ly_nhan_su',    'NS'),
        ('quan_ly',            'QL')
    ) AS m(vai_tro, tien_to) ON m.vai_tro = nd.vai_tro
    WHERE nd.la_tai_khoan_goc = false
) t
WHERE n.id = t.id;

-- Tài xế: nhan_su_van_hanh không có ngay_tao, dùng ngay_vao_lam rồi id (thứ tự giữa người cùng ngày chỉ cần ổn định).
UPDATE nhan_su_van_hanh h
SET ma = 'TX' || CASE WHEN t.stt < 10000 THEN lpad(t.stt::text, 4, '0') ELSE t.stt::text END
FROM (
    SELECT id, row_number() OVER (ORDER BY ngay_vao_lam, id) AS stt
    FROM nhan_su_van_hanh
    WHERE chuc_danh = 'tai_xe'
) t
WHERE h.id = t.id;

-- Đưa mỗi sequence tới đúng số đã cấp, để mã tạo sau tiếp nối (quan_ly không tính tài khoản gốc vì gốc là QL0000).
-- Chưa ai có mã thì setval(..., 1, false): mã đầu tiên cấp ra là 0001.
SELECT setval('seq_ma_tai_xe',
              GREATEST((SELECT count(*) FROM nhan_su_van_hanh WHERE chuc_danh = 'tai_xe'), 1),
              (SELECT count(*) FROM nhan_su_van_hanh WHERE chuc_danh = 'tai_xe') > 0);
SELECT setval('seq_ma_phu_xe',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'phu_xe'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'phu_xe') > 0);
SELECT setval('seq_ma_quay_ve',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'nhan_vien_quay_ve'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'nhan_vien_quay_ve') > 0);
SELECT setval('seq_ma_gui_hang',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'nhan_vien_gui_hang'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'nhan_vien_gui_hang') > 0);
SELECT setval('seq_ma_dieu_do_vien',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'dieu_do_vien'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'dieu_do_vien') > 0);
SELECT setval('seq_ma_ke_toan',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'ke_toan'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'ke_toan') > 0);
SELECT setval('seq_ma_quan_ly_nhan_su',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'quan_ly_nhan_su'), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'quan_ly_nhan_su') > 0);
SELECT setval('seq_ma_quan_ly',
              GREATEST((SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'quan_ly' AND la_tai_khoan_goc = false), 1),
              (SELECT count(*) FROM nguoi_dung WHERE vai_tro = 'quan_ly' AND la_tai_khoan_goc = false) > 0);

-- 3. Ràng buộc -----------------------------------------------------------
-- Mã duy nhất (nhiều dòng trống không bị coi là trùng).
CREATE UNIQUE INDEX nguoi_dung_ma_duy_nhat       ON nguoi_dung (ma)       WHERE ma IS NOT NULL;
CREATE UNIQUE INDEX nhan_su_van_hanh_ma_duy_nhat ON nhan_su_van_hanh (ma) WHERE ma IS NOT NULL;

-- Định dạng: nếu có mã thì tiền tố phải đúng vai trò; khách hàng không có mã; QL0000 dành riêng cho tài khoản gốc.
ALTER TABLE nguoi_dung ADD CONSTRAINT nguoi_dung_ma_hop_le CHECK (
    CASE vai_tro
        WHEN 'khach_hang'         THEN ma IS NULL
        WHEN 'phu_xe'             THEN ma IS NULL OR ma ~ '^PX[0-9]{4,}$'
        WHEN 'nhan_vien_quay_ve'  THEN ma IS NULL OR ma ~ '^QV[0-9]{4,}$'
        WHEN 'nhan_vien_gui_hang' THEN ma IS NULL OR ma ~ '^GH[0-9]{4,}$'
        WHEN 'dieu_do_vien'       THEN ma IS NULL OR ma ~ '^DDV[0-9]{4,}$'
        WHEN 'ke_toan'            THEN ma IS NULL OR ma ~ '^KT[0-9]{4,}$'
        WHEN 'quan_ly_nhan_su'    THEN ma IS NULL OR ma ~ '^NS[0-9]{4,}$'
        WHEN 'quan_ly'            THEN ma IS NULL OR ma ~ '^QL[0-9]{4,}$'
        ELSE ma IS NULL   -- vai trò mới chưa có tiền tố: chưa cấp mã, vẫn INSERT được
    END
);
ALTER TABLE nguoi_dung ADD CONSTRAINT nguoi_dung_ql0000_chi_cho_tai_khoan_goc CHECK (
    ma IS DISTINCT FROM 'QL0000' OR la_tai_khoan_goc = true
);

-- Hồ sơ nhân sự: chỉ tài xế có mã riêng (phụ xe dùng mã tài khoản).
ALTER TABLE nhan_su_van_hanh ADD CONSTRAINT nhan_su_van_hanh_ma_hop_le CHECK (
    ma IS NULL OR (chuc_danh = 'tai_xe' AND ma ~ '^TX[0-9]{4,}$')
);

-- 4. Mã đã cấp thì không sửa được ---------------------------------------
-- Khác giu_nguyen_ma() của các bảng khác (luôn ghi đè NEW.ma bằng OLD.ma): hàm này chỉ giữ khi mã ĐÃ CÓ, nên tài khoản
-- tạo ra chưa có mã (VD script seed demo) vẫn được điền mã về sau, còn đã có mã thì không đổi được nữa.
CREATE FUNCTION giu_ma_nhan_vien() RETURNS trigger AS $$
BEGIN
    IF OLD.ma IS NOT NULL THEN
        NEW.ma := OLD.ma;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER nguoi_dung_giu_ma       BEFORE UPDATE ON nguoi_dung       FOR EACH ROW EXECUTE FUNCTION giu_ma_nhan_vien();
CREATE TRIGGER nhan_su_van_hanh_giu_ma BEFORE UPDATE ON nhan_su_van_hanh FOR EACH ROW EXECUTE FUNCTION giu_ma_nhan_vien();
