-- Hoàn thiện phân hệ Gửi hàng (NGHIEP_VU.md mục 10, UC-23..28, UC-39, UC-46).
-- Chạy SAU 20261002_0900 (bảng lich_su_lien_he_don_hang, cột thu tiền).

-- 1. SĐT liên hệ văn phòng — in lên biên nhận cho người gửi (mục 10.3.1 điểm 1:
--    "mã vận đơn + điểm nhận + thông tin liên hệ điểm nhận"). Nullable: quản lý
--    bổ sung dần qua màn quản lý điểm đón/trả (UC-30).
ALTER TABLE diem_don_tra
    ADD COLUMN IF NOT EXISTS sdt_lien_he TEXT NULL;

-- 2. Lịch sử liên hệ chỉ nhận các tổ hợp đối tượng/kết quả có nghĩa
--    (báo quản lý <=> đối tượng là quản lý). Schema API cũng kiểm tra trước.
ALTER TABLE lich_su_lien_he_don_hang
    DROP CONSTRAINT IF EXISTS lich_su_lien_he_to_hop_hop_le;
ALTER TABLE lich_su_lien_he_don_hang
    ADD CONSTRAINT lich_su_lien_he_to_hop_hop_le
    CHECK ((doi_tuong = 'quan_ly') = (ket_qua = 'da_bao_quan_ly'));

-- 3. Ràng buộc dữ liệu đơn hàng (service đã chặn, DB chặn thêm 1 lớp).
ALTER TABLE don_hang
    DROP CONSTRAINT IF EXISTS don_hang_diem_gui_khac_diem_nhan;
ALTER TABLE don_hang
    ADD CONSTRAINT don_hang_diem_gui_khac_diem_nhan CHECK (diem_gui_id <> diem_nhan_id);
ALTER TABLE don_hang
    DROP CONSTRAINT IF EXISTS don_hang_gia_cuoc_duong;
ALTER TABLE don_hang
    ADD CONSTRAINT don_hang_gia_cuoc_duong CHECK (gia_cuoc > 0);

-- 4. Index cho các màn hình tại quầy:
--    - "Đơn gửi đi" của 1 văn phòng, mới nhất trước.
CREATE INDEX IF NOT EXISTS idx_don_hang_diem_gui_ngay_tao
    ON don_hang (diem_gui_id, ngay_tao DESC);
--    - "Hàng đến" của 1 văn phòng nhận (sắp đến / chờ lấy / hàng tồn).
CREATE INDEX IF NOT EXISTS idx_don_hang_diem_nhan_dang_xu_ly
    ON don_hang (diem_nhan_id, trang_thai)
    WHERE trang_thai IN ('da_len_xe', 'cho_lay', 'qua_han_luu_kho');
--    - Tra cứu theo SĐT khi người nhận quên mã vận đơn (mục 10.3.1 điểm 5).
CREATE INDEX IF NOT EXISTS idx_don_hang_sdt_nguoi_nhan ON don_hang (sdt_nguoi_nhan);
CREATE INDEX IF NOT EXISTS idx_don_hang_sdt_nguoi_gui ON don_hang (sdt_nguoi_gui);
--    - Thông báo gắn với đơn hàng.
CREATE INDEX IF NOT EXISTS idx_thong_bao_don_hang ON thong_bao (don_hang_id) WHERE don_hang_id IS NOT NULL;
