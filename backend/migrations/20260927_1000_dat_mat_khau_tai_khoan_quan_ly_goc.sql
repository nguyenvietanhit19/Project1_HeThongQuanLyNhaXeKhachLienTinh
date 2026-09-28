-- Dat san mat khau tam thoi cho tai khoan quan_ly goc (seed o
-- 20260917_0900, sua email o 20260920_1710) - truoc gio mat_khau = NULL,
-- bat buoc phai qua "Quen mat khau" moi dat duoc lan dau. Nhung email
-- admin@nhaxekhach.com khong phai hop thu that, khong nhan duoc OTP
-- (khong dung .local nua nen qua duoc validate, nhung van la domain
-- khong ton tai) - dat san hash truc tiep de dang nhap ngay duoc.
--
-- Hash sinh bang dung CryptContext(schemes=["bcrypt"]) giong het
-- mat_khau_service.py (khong tu bia chuoi). KHONG ghi mat khau goc (dang
-- chua hash) vao day hay bat ky commit nao - hash nam trong git la chap
-- nhan duoc cho 1 tai khoan bootstrap tam thoi, nhung mat khau that thi
-- khong. BAT BUOC doi lai mat khau nay ngay sau lan dang nhap dau tien
-- (PUT /auth/doi-mat-khau).
UPDATE nguoi_dung
SET mat_khau = '$2b$12$JX0rCzTraSN5ZIO3Y9vWyOh9TjjCUya4fr6qIOrFQLLLXnqZ5Bjs2'
WHERE email = 'admin@nhaxekhach.com' AND la_tai_khoan_goc = true;
