-- Phụ xe tách rõ 2 pha giữa các điểm: ĐANG DỪNG tại điểm (cho khách lên/xuống, chất/dỡ hàng) và ĐANG DI CHUYỂN
-- tới điểm kế tiếp. `dang_di_chuyen` = true từ lúc bấm "Bắt đầu di chuyển" tới lúc xác nhận đã đến điểm kế tiếp
-- (hoặc hoàn tác nếu bấm nhầm). Trong lúc di chuyển không lên/xuống xe, không chất/dỡ hàng được.
-- Chạy SAU 20261008_0900.

ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS dang_di_chuyen BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE chuyen_xe ADD COLUMN IF NOT EXISTS gio_roi_diem TIMESTAMPTZ NULL;
