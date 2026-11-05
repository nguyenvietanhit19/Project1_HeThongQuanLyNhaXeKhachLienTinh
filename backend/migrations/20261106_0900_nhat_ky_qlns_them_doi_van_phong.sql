-- Nhánh "Đổi văn phòng của cán bộ" (UC-36, KE_HOACH_DOI_VAN_PHONG.md): nhật ký của quan_ly_nhan_su cần ghi thêm hành động
-- `doi_van_phong`. CHECK cũ chỉ cho 6 hành động nên phải nới thêm đúng 1 giá trị (không đổi dữ liệu có sẵn).
-- nhat_ky_admin để TEXT tự do (không CHECK) nên không cần sửa.
ALTER TABLE nhat_ky_quan_ly_nhan_su DROP CONSTRAINT nhat_ky_quan_ly_nhan_su_hanh_dong_check;
ALTER TABLE nhat_ky_quan_ly_nhan_su ADD CONSTRAINT nhat_ky_quan_ly_nhan_su_hanh_dong_check CHECK (hanh_dong IN (
    'tao_tai_khoan', 'khoa_tai_khoan', 'mo_khoa_tai_khoan',
    'tao_ho_so_nhan_su', 'sua_ho_so_nhan_su', 'cho_nghi_viec',
    'doi_van_phong'
));
