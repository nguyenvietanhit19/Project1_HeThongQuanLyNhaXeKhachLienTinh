-- Thông báo có thể kèm "đi tới trang nào" (chuông của Quản lý bấm vào thì mở đúng trang liên quan, VD /nhan-vien/quan-ly/lich-chay.html).
-- Đường dẫn tương đối trong frontend; NULL = thông báo chỉ có chữ như trước nay (thông báo cũ không đổi).
ALTER TABLE thong_bao ADD COLUMN duong_dan TEXT;
