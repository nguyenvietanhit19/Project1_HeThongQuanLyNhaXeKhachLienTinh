-- Bỏ khái niệm nhóm tuyến — mỗi tuyến giờ tự thân đại diện cả 1 hành trình
-- vật lý, chạy được CẢ 2 CHIỀU (không còn tách 2 bản ghi tuyến riêng cho
-- chiều đi/chiều về, không còn gộp nhóm để nối chúng lại).
-- Xem NGHIEP_VU.md mục 3.1, DATABASE.md mục 2.3/2.4 (đã cập nhật).
--
-- Bảng nhom_tuyen/nhom_tuyen_khu_vuc/tuyen/xe/chuyen_xe đã tồn tại (migration
-- 20260920_1600/1700/1800) nhưng CHƯA có repository/service nào dùng tới
-- (UC-18/31/34/44 chưa ai code) — an toàn đổi cấu trúc ngay, không cần giữ
-- tương thích ngược hay lo mất dữ liệu thật.

-- 1. Xe: đổi tham chiếu từ nhom_tuyen sang thẳng tuyen (vẫn nullable — NULL
-- nghĩa là xe dự phòng, dùng chung cho mọi tuyến, không đổi ý nghĩa).
ALTER TABLE xe DROP CONSTRAINT xe_nhom_tuyen_id_fkey;
ALTER TABLE xe RENAME COLUMN nhom_tuyen_id TO tuyen_id;
ALTER TABLE xe ADD CONSTRAINT xe_tuyen_id_fkey FOREIGN KEY (tuyen_id) REFERENCES tuyen(id);

-- 2. Tuyến: bỏ cột nhom_tuyen_id (không còn khái niệm nhóm) — DROP COLUMN
-- tự gỡ luôn FK constraint và index gắn với cột này. (ngay_tao của tuyen đã
-- có từ migration 20260921_0900, không thêm lại.)
DROP INDEX IF EXISTS tuyen_nhom_tuyen_id_idx;
ALTER TABLE tuyen DROP COLUMN nhom_tuyen_id;

-- 3. Chuyến xe: thêm "chiều" (xuôi/ngược) — tuyến giờ chạy được cả 2 chiều
-- nên 1 lần chạy cụ thể phải nói rõ đang chạy chiều nào (DATABASE.md mục
-- 3.3). Set default 'xuoi' cho các dòng cũ (nếu có) rồi bỏ default ngay,
-- ép mọi chuyến tạo sau phải chọn rõ chiều.
ALTER TABLE chuyen_xe ADD COLUMN chieu TEXT NOT NULL DEFAULT 'xuoi' CHECK (chieu IN ('xuoi', 'nguoc'));
ALTER TABLE chuyen_xe ALTER COLUMN chieu DROP DEFAULT;

-- 4. Bỏ hẳn nhom_tuyen_khu_vuc và nhom_tuyen — không còn dùng.
DROP TABLE IF EXISTS nhom_tuyen_khu_vuc;
DROP TABLE IF EXISTS nhom_tuyen;
