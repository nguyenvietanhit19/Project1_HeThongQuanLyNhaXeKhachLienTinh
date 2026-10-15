-- Phân loại báo cáo sự cố hàng của phụ xe (UC-28): hư hỏng (hàng vẫn còn, tới nơi được) hay thất lạc/mất
-- (hàng không còn trên xe). Chỉ để phụ xe/văn phòng nhìn đúng tình trạng — KHÔNG đổi trạng thái đơn
-- và không chặn chất/dỡ (UC-28 hậu điều kiện). Báo cáo cũ mặc định là hư hỏng.
-- Chạy SAU 20261007_0900.

ALTER TABLE bao_cao_su_co_hang
    ADD COLUMN IF NOT EXISTS loai TEXT NOT NULL DEFAULT 'hu_hong' CHECK (loai IN ('hu_hong', 'that_lac'));
