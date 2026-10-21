-- Lịch chạy luôn đi theo cặp (1 lịch chiều đi + 1 lịch chiều về cùng tuyến) để không còn chuyến 1 chiều mà thiếu chiều kia.
-- cap_id: chung cho 2 lịch của 1 cặp. ngay_lech: xe chạy chiều đi xong thì chiều về xuất bến sau bao nhiêu ngày (0 = cùng ngày),
-- lưu trên lịch chiều về (chiều đi luôn 0) để việc sửa thời gian chạy của tuyến sau này không làm lệch các cặp đã có.
ALTER TABLE lich_chay_dinh_ky ADD COLUMN cap_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE lich_chay_dinh_ky ALTER COLUMN cap_id DROP DEFAULT;
ALTER TABLE lich_chay_dinh_ky ADD COLUMN ngay_lech SMALLINT NOT NULL DEFAULT 0 CHECK (ngay_lech >= 0);
ALTER TABLE lich_chay_dinh_ky ADD CONSTRAINT lich_chay_ngay_lech_theo_chieu CHECK (chieu = 'nguoc' OR ngay_lech = 0);
CREATE UNIQUE INDEX lich_chay_moi_chieu_mot_lich_trong_cap ON lich_chay_dinh_ky (cap_id, chieu);
