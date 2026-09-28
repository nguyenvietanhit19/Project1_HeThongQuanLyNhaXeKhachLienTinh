-- Bảng còn thiếu để chuyen_xe (migration kế tiếp) có đủ khóa ngoại.
--
-- Các bảng khu_vuc, diem_don_tra, tuyen, tuyen_diem_don_tra, loai_xe, xe đã
-- được tạo ở các migration 20260920_* — file này chỉ tạo phần CHƯA có:
-- xe_nhan_su và lich_chay_dinh_ky (DATABASE.md mục 1.5, 3.5).
-- nhan_su_van_hanh đã tồn tại từ migration 20260927_1000_...

-- Biên chế cố định/tạm thời gắn nhân sự với xe (DATABASE.md mục 1.5).
CREATE TABLE xe_nhan_su (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    xe_id                   UUID NOT NULL REFERENCES xe(id),
    nhan_su_van_hanh_id     UUID NOT NULL REFERENCES nhan_su_van_hanh(id),
    loai                    TEXT NOT NULL CHECK (loai IN ('co_dinh', 'tam_thoi')),
    trang_thai              TEXT NOT NULL DEFAULT 'dang_hoat_dong' CHECK (trang_thai IN ('dang_hoat_dong', 'tam_nghi')),
    ngay_bat_dau            TIMESTAMPTZ NOT NULL DEFAULT now(),
    ngay_ket_thuc           TIMESTAMPTZ NULL
);

-- Lịch chạy định kỳ (DATABASE.md mục 3.5) — khuôn để job sinh chuyen_xe mỗi
-- ngày (UC-18). Tuyến chạy được cả 2 chiều nên mỗi dòng lịch nói rõ chiều nào.
CREATE TABLE lich_chay_dinh_ky (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id        UUID NOT NULL REFERENCES tuyen(id),
    chieu           TEXT NOT NULL CHECK (chieu IN ('xuoi', 'nguoc')),
    gio_khoi_hanh   TIME NOT NULL,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    dang_ap_dung    BOOLEAN NOT NULL DEFAULT true,
    ngay_tao        TIMESTAMPTZ NOT NULL DEFAULT now()
);
