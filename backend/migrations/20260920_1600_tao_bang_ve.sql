-- Bảng ve — DATABASE.md mục 4
-- Bảng trung tâm hệ thống: vòng đời đặt vé + cơ chế chống trùng ghế.
--
-- PHỤ THUỘC (phải chạy migration TRƯỚC file này):
--   - 0001_init_extensions.sql           (pgcrypto — gen_random_uuid)
--   - 20260917_0900_tao_bang_nguoi_dung.sql (bảng nguoi_dung)
--   - migration tạo bảng chuyen_xe       (người 4 — chưa có, xem ghi chú bên dưới)
--   - migration tạo bảng diem_don_tra    (người 1 — chưa có, xem ghi chú bên dưới)
--
-- GHI CHÚ: Các FK tới chuyen_xe và diem_don_tra CHƯA THỂ BẬT vì bảng chưa tồn
-- tại. File này tạm dùng cột UUID thuần (không FK) cho 3 cột đó; khi người 1 và
-- người 4 đã tạo bảng xong, chạy thêm 1 migration ALTER TABLE ADD CONSTRAINT
-- để bổ sung FK — xem file đi kèm bên dưới.

CREATE TABLE ve (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Chuyến xe mà vé này thuộc về
    chuyen_id                     UUID NOT NULL,
    -- TODO: khi bảng chuyen_xe tồn tại → thêm FK
    -- CONSTRAINT fk_ve_chuyen_xe FOREIGN KEY (chuyen_id) REFERENCES chuyen_xe(id)

    -- Số ghế — khớp loai_xe.so_do_ghe; KHÔNG unique cùng chuyen_id
    -- vì 1 ghế hợp lệ có nhiều vé nếu chặng không giao nhau (DATABASE.md mục 0)
    so_ghe                        TEXT NOT NULL,

    -- Điểm đón (bắt buộc loai = 'van_phong', kiểm tra ở Service)
    diem_don_id                   UUID NOT NULL,
    -- TODO: CONSTRAINT fk_ve_diem_don FOREIGN KEY (diem_don_id) REFERENCES diem_don_tra(id)

    -- Điểm trả (van_phong hoặc diem_dung)
    diem_tra_id                   UUID NOT NULL,
    -- TODO: CONSTRAINT fk_ve_diem_tra FOREIGN KEY (diem_tra_id) REFERENCES diem_don_tra(id)

    -- Khách hàng có tài khoản; NULL = vé vãng lai (mua tại quầy/hotline)
    khach_hang_id                 UUID NULL REFERENCES nguoi_dung(id),

    -- Bắt buộc nếu khach_hang_id IS NULL (kiểm tra ở Service)
    ten_khach_vang_lai            TEXT NULL,
    sdt_khach_vang_lai            TEXT NULL,

    -- Giá copy từ gia_ve tại thời điểm đặt — không tính lại nếu gia_ve đổi sau
    gia                           NUMERIC(12, 0) NOT NULL,

    -- Nhóm các vé cùng 1 lần đặt (NGHIEP_VU.md mục 3.4)
    ma_dat_cho                    TEXT NOT NULL,

    -- true nếu vé bắt buộc thanh toán ngay trong lô > 600.000đ (mục 3.4)
    la_ve_dat_coc                 BOOLEAN NOT NULL DEFAULT false,

    -- Kênh/thời điểm trả tiền — chọn lúc đặt vé
    -- thanh_toan_tai_quay dùng chung cho: online chọn trả sau, bán tại quầy UC-09,
    -- bán qua hotline UC-10 — cả 3 không có hạn giữ chỗ (NGHIEP_VU.md mục 3.4/6)
    loai_hinh_thanh_toan          TEXT NOT NULL CHECK (loai_hinh_thanh_toan IN (
                                      'thanh_toan_ngay', 'thanh_toan_tai_quay'
                                  )),

    -- Trả bằng gì — chỉ có giá trị khi đã thu tiền (gio_thanh_toan IS NOT NULL)
    -- thanh_toan_ngay luôn = 'chuyen_khoan' (VNPay); thanh_toan_tai_quay do
    -- nhân viên quầy chọn lúc thu (tien_mat / chuyen_khoan QR)
    phuong_thuc_thanh_toan        TEXT NULL CHECK (phuong_thuc_thanh_toan IN (
                                      'tien_mat', 'chuyen_khoan'
                                  )),

    -- Mã giao dịch VNPay — dùng gọi API hoàn tiền sau này (NGHIEP_VU.md mục 7)
    -- NULL nếu trả tiền mặt
    ma_giao_dich_cong_thanh_toan  TEXT NULL,

    -- Vòng đời vé — NGHIEP_VU.md mục 5
    trang_thai                    TEXT NOT NULL DEFAULT 'giu_cho' CHECK (trang_thai IN (
                                      'giu_cho', 'het_han', 'da_thanh_toan',
                                      'da_len_xe', 'da_xuong_xe',
                                      'khong_den', 'da_huy'
                                  )),

    -- Set khi khách tới màn thanh toán (mục 3.4 bước 6)
    -- NULL = ghế đã khóa nhưng chưa bắt đầu tính giờ
    gio_bat_dau_dem_han           TIMESTAMPTZ NULL,

    -- 5 phút sau gio_bat_dau_dem_han — chỉ với thanh_toan_ngay
    -- NULL với thanh_toan_tai_quay (không có hạn, giữ tới giờ khởi hành)
    han_giu_cho_den               TIMESTAMPTZ NULL,

    gio_thanh_toan                TIMESTAMPTZ NULL,
    gio_len_xe                    TIMESTAMPTZ NULL,
    gio_xuong_xe                  TIMESTAMPTZ NULL,
    gio_huy                       TIMESTAMPTZ NULL,

    ngay_tao                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index bắt buộc (DATABASE.md mục 4, ARCHITECTURE.md mục 4):
-- KHÔNG unique — 1 ghế hợp lệ có nhiều vé nếu chặng không giao nhau.
-- Dùng cho SELECT ... FOR UPDATE trong ve_lock_repository quét nhanh đúng
-- các dòng cần khóa khi chống trùng ghế (NGHIEP_VU.md mục 6).
CREATE INDEX idx_ve_chuyen_ghe ON ve (chuyen_id, so_ghe);

-- Index tra cứu theo mã đặt chỗ (tìm vé, thanh toán vé lô, in vé)
CREATE INDEX idx_ve_ma_dat_cho ON ve (ma_dat_cho);

-- Index tra cứu lịch sử vé của khách hàng có tài khoản
CREATE INDEX idx_ve_khach_hang ON ve (khach_hang_id) WHERE khach_hang_id IS NOT NULL;

-- Index phục vụ job quét vé hết hạn giữ chỗ (UC-14)
CREATE INDEX idx_ve_quet_het_han ON ve (trang_thai, han_giu_cho_den)
    WHERE trang_thai = 'giu_cho' AND han_giu_cho_den IS NOT NULL;
