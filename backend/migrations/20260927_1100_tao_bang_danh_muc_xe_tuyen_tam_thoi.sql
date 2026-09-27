-- ⚠️ TẠM THỜI — đọc kỹ trước khi merge vào main.
--
-- Toàn bộ 9 bảng dưới đây (khu_vuc, diem_don_tra, nhom_tuyen, tuyen,
-- tuyen_diem_don_tra, loai_xe, xe, xe_nhan_su, lich_chay_dinh_ky) đúng ra
-- thuộc domain của Trưởng nhóm (CONTRIBUTING.md mục 2: người 1 sở hữu
-- khu_vuc/diem_don_tra/tuyen_repository, xe/loai_xe/gia_ve/xe_nhan_su_repository,
-- lich_chay_dinh_ky_service) nhưng tính đến ngày viết file này, migration
-- tương ứng nằm rải rác ở các nhánh riêng (Vanh-uc29-31, Vanh-uc32-33...)
-- chưa gộp vào nhánh này (feature/Nghia-us04-dieuDoVien).
--
-- chuyen_xe (bảng THẬT của điều độ viên — migration kế tiếp,
-- 20260927_1110_...) có khóa ngoại trỏ tới TẤT CẢ 9 bảng này, nên không
-- migrate/test được chuyen_xe_service nếu thiếu. Migration này dựng đủ
-- cột đúng theo DATABASE.md (mục 2, 3.1, 3.2, 3.5, 1.5) — không thêm/bớt
-- gì — để CÓ THỂ TỰ TEST UC-19/20/39/40/44/45 ngay trên nhánh này, không
-- phải chờ Trưởng nhóm.
--
-- TRƯỚC KHI MERGE: phải đối chiếu với migration thật của Trưởng nhóm. Nếu
-- họ cũng có "CREATE TABLE xe (...)" (hay bất kỳ bảng nào ở đây) ở migration
-- riêng của họ, 2 migration cùng tạo 1 bảng sẽ lỗi "relation already exists"
-- khi áp dụng chung trên cùng 1 nhánh — khi đó XÓA HẲN file này, giữ lại
-- đúng migration của Trưởng nhóm.

-- ─────────────────────────────────────────────────────────────────────────
-- Địa điểm & tuyến (DATABASE.md mục 2)
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE khu_vuc (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten           TEXT NOT NULL,
    tinh_thanh    TEXT NOT NULL
);

CREATE TABLE diem_don_tra (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    khu_vuc_id    UUID NOT NULL REFERENCES khu_vuc(id),
    ten           TEXT NOT NULL,
    dia_chi       TEXT NOT NULL,
    loai          TEXT NOT NULL CHECK (loai IN ('van_phong', 'diem_dung'))
);

CREATE TABLE nhom_tuyen (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten           TEXT NOT NULL
);

CREATE TABLE tuyen (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhom_tuyen_id   UUID NOT NULL REFERENCES nhom_tuyen(id),
    ten             TEXT NOT NULL
);

-- Chuỗi điểm có thứ tự của 1 tuyến (DATABASE.md mục 2.4). Dùng cho ràng buộc
-- vị trí xe (mục 3.3 NGHIEP_VU.md) và tính đoạn [thu_tu(don), thu_tu(tra))
-- chống trùng ghế (mục 6 NGHIEP_VU.md, thuộc người 2 — ở đây chỉ đọc).
CREATE TABLE tuyen_diem_don_tra (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id                  UUID NOT NULL REFERENCES tuyen(id),
    diem_don_tra_id           UUID NOT NULL REFERENCES diem_don_tra(id),
    thu_tu                    INTEGER NOT NULL,
    thoi_gian_du_kien_phut    INTEGER NOT NULL,

    UNIQUE (tuyen_id, thu_tu),
    UNIQUE (tuyen_id, diem_don_tra_id)
);

-- ─────────────────────────────────────────────────────────────────────────
-- Xe & biên chế (DATABASE.md mục 1.5, 3.1, 3.2)
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE loai_xe (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ten           TEXT NOT NULL UNIQUE,
    he_so_gia     NUMERIC(4,2) NOT NULL DEFAULT 1.0,
    so_do_ghe     JSONB NOT NULL
);

CREATE TABLE xe (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bien_so         TEXT NOT NULL UNIQUE,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    trang_thai      TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong', 'bao_tri', 'ngung_su_dung')),
    diem_goc_id     UUID NOT NULL REFERENCES diem_don_tra(id),  -- phải loai = 'van_phong', kiểm tra ở Service
    nhom_tuyen_id   UUID NULL REFERENCES nhom_tuyen(id)          -- NULL = xe dự phòng, dùng linh hoạt
);

-- Biên chế cố định/tạm thời gắn nhân sự với xe (DATABASE.md mục 1.5).
-- nhan_su_van_hanh đã tồn tại từ migration 20260927_1000_...sql (nhánh này).
CREATE TABLE xe_nhan_su (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    xe_id                   UUID NOT NULL REFERENCES xe(id),
    nhan_su_van_hanh_id     UUID NOT NULL REFERENCES nhan_su_van_hanh(id),
    loai                    TEXT NOT NULL CHECK (loai IN ('co_dinh', 'tam_thoi')),
    trang_thai              TEXT NOT NULL DEFAULT 'dang_hoat_dong' CHECK (trang_thai IN ('dang_hoat_dong', 'tam_nghi')),
    ngay_bat_dau            TIMESTAMPTZ NOT NULL DEFAULT now(),
    ngay_ket_thuc           TIMESTAMPTZ NULL
);

-- ─────────────────────────────────────────────────────────────────────────
-- Lịch chạy định kỳ (DATABASE.md mục 3.5) — khuôn để jobs/sinh_chuyen_dinh_ky.py
-- (người 4 viết, UC-18) sinh chuyen_xe mỗi ngày.
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE lich_chay_dinh_ky (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tuyen_id        UUID NOT NULL REFERENCES tuyen(id),
    gio_khoi_hanh   TIME NOT NULL,
    loai_xe_id      UUID NOT NULL REFERENCES loai_xe(id),
    dang_ap_dung    BOOLEAN NOT NULL DEFAULT true,
    ngay_tao        TIMESTAMPTZ NOT NULL DEFAULT now()
);
