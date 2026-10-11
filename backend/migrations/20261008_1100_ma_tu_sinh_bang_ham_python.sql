-- Chuyển việc SINH mã tự động (khu vực, điểm đón/trả, tuyến, loại xe, chuyến, vé) từ trigger của Postgres sang hàm Python
-- (app/utils/ma_tu_sinh.py + app/repositories/ma_repository.py). Repository lấy số thứ tự từ sequence rồi tự điền cột `ma`
-- trong lệnh INSERT, nên sequence và bộ đếm `khu_vuc.so_diem_da_cap` GIỮ NGUYÊN (số vẫn không trùng, không tái dùng).
--
-- Giữ lại các trigger "mã không sửa được" (giu_nguyen_ma, giu_ma_ve) và "không đổi khu vực của điểm" — đó là ràng buộc
-- của dữ liệu chứ không phải sinh mã. Riêng chuyến: gỡ cả trigger sửa mã, vì khi quản lý sửa giờ thì Python tự tính lại mã
-- (chuyen_xe_repository.sua_gio_chuyen); không đường nào khác động tới cột `ma` của chuyến.
--
-- Từ đây mọi INSERT vào 6 bảng này PHẢI tự điền `ma` (cột đã NOT NULL + UNIQUE nên quên là báo lỗi ngay, không sinh mã sai).

DROP TRIGGER khu_vuc_sinh_ma      ON khu_vuc;
DROP TRIGGER diem_don_tra_sinh_ma ON diem_don_tra;
DROP TRIGGER tuyen_sinh_ma        ON tuyen;
DROP TRIGGER loai_xe_sinh_ma      ON loai_xe;
DROP TRIGGER chuyen_xe_sinh_ma    ON chuyen_xe;
DROP TRIGGER ve_sinh_ma           ON ve;

DROP TRIGGER chuyen_xe_cap_nhat_ma ON chuyen_xe;

DROP FUNCTION sinh_ma_khu_vuc();
DROP FUNCTION sinh_ma_diem_don_tra();
DROP FUNCTION sinh_ma_tuyen();
DROP FUNCTION sinh_ma_loai_xe();
DROP FUNCTION sinh_ma_chuyen_xe();
DROP FUNCTION sinh_ma_ve();
DROP FUNCTION cap_nhat_ma_chuyen_xe();
DROP FUNCTION tao_ma_chuyen(UUID, UUID, TIMESTAMPTZ, TEXT);
