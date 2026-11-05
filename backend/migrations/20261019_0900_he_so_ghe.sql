-- Hệ số giá TỪNG GHẾ: loai_xe.he_so_ghe ({"A1-1": 1.1}, ghế vắng mặt = 1) luôn sửa được (kể cả khi sơ đồ ghế đã khóa) và
-- được CHỐT vào chuyen_xe.he_so_ghe lúc sinh chuyến — sửa hệ số chỉ ảnh hưởng chuyến sinh sau (giống chuyen_xe.he_so_gia).
-- loai_xe.phien_ban: khóa lạc quan — tăng mỗi lần sửa; form gửi kèm phiên bản đang xem, lệch thì báo xung đột.
ALTER TABLE loai_xe ADD COLUMN he_so_ghe JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE loai_xe ADD COLUMN phien_ban INTEGER NOT NULL DEFAULT 1;
ALTER TABLE chuyen_xe ADD COLUMN he_so_ghe JSONB NOT NULL DEFAULT '{}'::jsonb;
