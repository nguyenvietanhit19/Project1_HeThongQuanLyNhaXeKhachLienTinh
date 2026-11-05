# Thống kê theo Ngày / Tháng / Năm + biểu đồ + xuất báo cáo — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tab "Thống kê & đối soát" của nhân viên gửi hàng chọn được kỳ Ngày/Tháng/Năm/Tùy chọn, có 4 biểu đồ, xuất được Excel 3 trang tính và in báo cáo có biểu đồ.

**Architecture:** Backend thêm 1 API `GET /gui-hang/thong-ke-chuoi` trả số liệu chia theo giờ/ngày/tháng (một truy vấn SQL, đúng quy tắc mốc thời gian + phía văn phòng của `thong_ke_hang_tai_diem`), gỡ API cũ `/thong-ke-theo-ngay`. Frontend giữ kiến trúc script thường (không bundler): `thong-ke.js` lo kỳ + tải dữ liệu + render số; file mới `bieu-do.js` lo vẽ SVG; file mới `bao-cao.js` lo Excel + In. Xuất/In dùng lại dữ liệu đang hiện (`state.thongKe`), không gọi API lại.

**Tech Stack:** FastAPI + psycopg (PostgreSQL), vanilla JS + SVG tay, SheetJS CE 0.20.3 (vendored), Playwright (Edge) cho kiểm thử giao diện.

**Spec:** `docs/superpowers/specs/2026-11-05-thong-ke-theo-ky-gui-hang-design.md` — đọc trước khi làm bất kỳ task nào.

## Global Constraints

- Nhánh: làm tiếp trên `feature/Trinh-gui-hang-su-co-xe`, không tạo nhánh mới.
- Mọi mốc thời gian theo giờ Việt Nam: dùng hằng `MUI_GIO_VN` đã có trong `don_hang_repository.py`.
- Khoảng tối đa 1 năm: `SO_NGAY_THONG_KE_TOI_DA = 366` (giữ nguyên, kiểm bằng `_kiem_tra_khoang_ngay`).
- `don_vi = "ngay"` chỉ khi khoảng ≤ **62** ngày; `don_vi = "gio"` chỉ khi `tu_ngay == den_ngay`.
- Phạm vi văn phòng luôn qua `_pham_vi_van_phong(nguoi_dung, diem_id)`; quyền `QuyenThongKe`.
- Không thêm thư viện biểu đồ. SheetJS để ở `frontend/nhan-vien/gui-hang/vendor/xlsx.mini.min.js`, chỉ nạp khi bấm Xuất Excel.
- Chữ trên giao diện, tên sheet, tên cột: tiếng Việt có dấu, giống nhãn đang có trên tab.
- Không sửa `NGHIEP_VU.md` chung; nghiệp vụ role ghi trong `NGHIEP_VU_GUI_HANG.md`. Mọi thay đổi ghi vào `KE_HOACH_SUA_GUI_HANG.md`.
- Commit message kết thúc bằng dòng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Trên PowerShell 5.1, message nhiều dòng / có dấu `"` thì ghi ra file tạm rồi `git commit -F <file>`.
- Lệnh test backend chạy trong Docker: `docker compose exec backend python -m pytest ...` (từ thư mục gốc dự án).

## Review Focus

1. **Bấm ◀ ▶ liên tục** — phản hồi cũ về sau không được ghi đè kỳ mới: nhãn kỳ, ô số và biểu đồ luôn cùng một kỳ. (Task 2, ca J7)
2. **Kỳ chưa hết** (tháng/năm hiện tại, hôm nay) — mốc sau thời điểm hiện tại không có cột/điểm, nhưng tổng vẫn khớp ô số liệu. (Task 2–3, ca J8)
3. **Đơn sát nửa đêm** (vd 23:30 giờ VN) — phải rơi vào đúng ngày giờ VN; mỗi mốc ngày phải bằng `/thong-ke` của riêng ngày đó. (Task 1 bước kiểm DB, ca J9)
4. **Ngày chỉ có hoàn tiền** — doanh thu âm: trục dọc có phần âm, đường "Còn lại" đi xuống dưới 0, không vẽ ra ngoài khung. (Task 3, ca J12)
5. **Nhân viên gọi `/thong-ke-chuoi` với `diem_id` văn phòng khác** → 403, không lộ số liệu. (Task 1 bước kiểm, ca J9)

---

### Task 0: Commit phần đang dở + tài liệu thiết kế

**Files:**
- Commit: `KE_HOACH_SUA_GUI_HANG.md`, `QUY_TRINH_TEST_GUI_HANG.md`, `backend/scripts/kiem_thu_giao_dien_gui_hang.py`, `backend/scripts/requirements-kiem-thu-giao-dien.txt`, `docs/superpowers/specs/2026-11-05-thong-ke-theo-ky-gui-hang-design.md`, `docs/superpowers/plans/2026-11-05-thong-ke-theo-ky-gui-hang.md`

- [ ] **Step 1: Kiểm script test không chứa mật khẩu/đường dẫn riêng máy**

Run (PowerShell): `Select-String -Path backend/scripts/kiem_thu_giao_dien_gui_hang.py -Pattern 'C:\\Users|D:\\|5501|password'`
Expected: chỉ thấy mật khẩu demo đã công khai trong seed (`PhuXe@123`, `Tam@12345`, hằng `MK`) và cổng FE mặc định — không có đường dẫn ổ đĩa của máy.

- [ ] **Step 2: Commit thành 2 commit**

1. `Gui hang: quy trinh test chuan + script kiem thu giao dien tu dong` — 4 file đầu.
2. `Gui hang: thiet ke + ke hoach thong ke theo ngay/thang/nam` — spec + plan.

---

### Task 1: API `GET /gui-hang/thong-ke-chuoi` (gỡ `/thong-ke-theo-ngay`)

**Files:**
- Modify: `backend/app/repositories/don_hang_repository.py` (thay `thong_ke_hang_theo_ngay` ở ~1198–1224)
- Modify: `backend/app/services/gui_hang_service.py` (thay `thong_ke_hang_theo_ngay` ở ~835–838; thêm hằng cạnh `SO_NGAY_THONG_KE_TOI_DA` dòng 32)
- Modify: `backend/app/routes/gui_hang.py` (thay route ~284–290)
- Test: `backend/tests/unit/test_gui_hang_service.py` (thêm sau `test_doi_soat_tien_cong_tong_tien_hoan`, ~dòng 939)

**Interfaces:**
- Produces:
  - Repo: `thong_ke_chuoi_thoi_gian(diem_id: str | None, tu_ngay: date, den_ngay: date, don_vi: str) -> list[dict]`
  - Service: `thong_ke_chuoi(diem_id: str | None, tu_ngay: date, den_ngay: date, don_vi: str) -> list[dict]`; hằng `DON_VI_CHUOI = ("gio", "ngay", "thang")`, `SO_NGAY_CHUOI_THEO_NGAY_TOI_DA = 62`
  - HTTP: `GET /gui-hang/thong-ke-chuoi?tu_ngay=YYYY-MM-DD&den_ngay=YYYY-MM-DD&don_vi=gio|ngay|thang[&diem_id=uuid]` → `[{moc: str, tiep_nhan: int, da_giao: int, so_huy: int, tien_tra_truoc: int, tien_cod: int, tien_hoan: int, doanh_thu: int}]`, đủ mọi mốc, sắp tăng dần. `moc`: giờ `"2026-11-05T14:00"`, ngày `"2026-11-05"`, tháng `"2026-11-01"`.

- [ ] **Step 1: Viết test hỏng**

Các test (giả lập repo bằng `patch("app.repositories.don_hang_repository.thong_ke_chuoi_thoi_gian")` / `patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id")` như các test thống kê bên trên):

```python
def test_thong_ke_chuoi_truyen_dung_tham_so_xuong_repo():
    # tu=2026-11-01, den=2026-11-30, "ngay", diem_id=None → repo gọi đúng (None, tu, den, "ngay"), trả nguyên kết quả repo

def test_thong_ke_chuoi_gio_chi_cho_mot_ngay():
    # tu=2026-11-01, den=2026-11-02, "gio" → GiaTriLoi match "theo giờ"

def test_thong_ke_chuoi_ngay_toi_da_62_ngay():
    # 2026-09-01..2026-11-01 (62 ngày, (den-tu).days == 61) "ngay" → OK (repo được gọi)
    # 2026-09-01..2026-11-02 (63 ngày) "ngay" → GiaTriLoi match "62 ngày"

def test_thong_ke_chuoi_don_vi_khong_hop_le():
    # "tuan" → GiaTriLoi match "Đơn vị"

def test_thong_ke_chuoi_khoang_nguoc_va_qua_mot_nam():
    # 2026-11-05..2026-11-01 → match "Ngày bắt đầu"; 2025-01-01..2026-01-01 "thang" → match "tối đa 1 năm"

def test_thong_ke_chuoi_nam_nhuan_theo_thang_hop_le():
    # 2028-01-01..2028-12-31 "thang" → OK

def test_thong_ke_chuoi_diem_khong_ton_tai():
    # tim_diem_don_tra_theo_id trả None → GiaTriLoi match "không tồn tại"
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `docker compose exec backend python -m pytest tests/unit/test_gui_hang_service.py -k thong_ke_chuoi -q`
Expected: FAIL — `AttributeError: module 'app.services.gui_hang_service' has no attribute 'thong_ke_chuoi'`

- [ ] **Step 3: Service `thong_ke_chuoi` trong `gui_hang_service.py`**

Thứ tự kiểm: `don_vi` ∈ `DON_VI_CHUOI` ("Đơn vị thống kê chỉ nhận giờ, ngày hoặc tháng") → `_kiem_tra_khoang_ngay` → `gio` cần `tu == den` ("Thống kê theo giờ chỉ áp dụng cho 1 ngày") → `ngay` cần `(den - tu).days < 62` ("Thống kê theo ngày tối đa 62 ngày") → `diem_id` tồn tại (cùng câu lỗi như `thong_ke_hang_tai_diem`) → gọi repo. Xóa `thong_ke_hang_theo_ngay`.

- [ ] **Step 4: Repo `thong_ke_chuoi_thoi_gian`**

Một truy vấn, cấu trúc:

```sql
WITH p AS (SELECT %(vp)s::uuid AS vp, %(tu)s::date AS tu, %(den)s::date AS den),
moc AS (  -- đủ mốc trong kỳ, giờ VN (timestamp không múi giờ)
  SELECT generate_series(date_trunc(%(trunc)s, p.tu::timestamp),
                         date_trunc(%(trunc)s, (p.den + 1)::timestamp - interval '1 second'),
                         %(buoc)s::interval) AS m FROM p
),
su_kien AS (  -- mỗi dòng: (thời điểm giờ VN, loại, số tiền) — điều kiện từng loại đúng bảng mục 4 của spec
  SELECT d.ngay_tao AT TIME ZONE '{MUI_GIO_VN}' AS t, 'tiep_nhan' AS loai, 0 AS tien FROM don_hang d, p WHERE (p.vp IS NULL OR d.diem_gui_id = p.vp)
  UNION ALL ... 'da_giao' (ngay_giao, diem_nhan_id, trang_thai='da_giao')
  UNION ALL ... 'huy' (thoi_gian_huy, diem_gui_id, trang_thai='da_huy')
  UNION ALL ... 'tra_truoc' (thoi_gian_thu, diem_gui_id, nguoi_gui_tra_truoc AND da_thu_tien, gia_cuoc)
  UNION ALL ... 'cod' (thoi_gian_thu, diem_nhan_id, cod_nguoi_nhan_tra AND da_thu_tien, gia_cuoc)
  UNION ALL ... 'hoan' (thoi_gian_huy, diem_gui_id, so_tien_hoan IS NOT NULL, so_tien_hoan)
)
SELECT moc.m, count(*) FILTER (WHERE loai='tiep_nhan') AS tiep_nhan, ..., COALESCE(sum(tien) FILTER (WHERE loai='hoan'),0) AS tien_hoan
FROM moc LEFT JOIN su_kien s
  ON date_trunc(%(trunc)s, s.t) = moc.m AND s.t::date BETWEEN (SELECT tu FROM p) AND (SELECT den FROM p)
GROUP BY moc.m ORDER BY moc.m
```

Tham số theo `don_vi`: `gio → trunc 'hour', buoc '1 hour'`; `ngay → 'day', '1 day'`; `thang → 'month', '1 month'`. Hai đầu chuỗi dùng `date_trunc` nên kỳ tùy chọn bắt đầu/kết thúc giữa tháng vẫn đủ mốc (vd 15/09–02/11 theo tháng → Th9, Th10, Th11); điều kiện `s.t::date BETWEEN tu AND den` cắt đúng hai đầu kỳ. Python: đổi mọi số sang `int`, `doanh_thu = tien_tra_truoc + tien_cod - tien_hoan`, `moc` định dạng `"%Y-%m-%dT%H:00"` / `"%Y-%m-%d"` / `"%Y-%m-01"`. Xóa `thong_ke_hang_theo_ngay`.

- [ ] **Step 5: Route trong `gui_hang.py`**

`@router.get("/thong-ke-chuoi")` với `nguoi_dung: QuyenThongKe`, `tu_ngay: date = Query(...)`, `den_ngay: date = Query(...)`, `don_vi: str = Query(..., description="gio | ngay | thang")`, `diem_id: UUID | None = Query(None)` → `gui_hang_service.thong_ke_chuoi(_pham_vi_van_phong(nguoi_dung, diem_id), tu_ngay, den_ngay, don_vi)`. Xóa route `/thong-ke-theo-ngay`.

- [ ] **Step 6: Chạy test role**

Run: `docker compose exec backend python -m pytest tests/unit/test_gui_hang_service.py tests/unit/test_don_hang_schema.py tests/unit/test_quet_hang_ton.py tests/unit/test_phu_xe_hang.py -q`
Expected: tất cả PASS (174 cũ + 7 mới).

- [ ] **Step 7: Kiểm bất biến trên DB thật (seed demo)**

Run: `docker compose restart backend` rồi `docker compose exec -T backend python -` với đoạn mã: với `diem_id` ∈ {None, id VP Mỹ Đình}: (a) tháng hiện tại `ngay` và năm hiện tại `thang` — tổng mỗi trường = trường tương ứng của `don_hang_repo.thong_ke_hang_tai_diem` cùng kỳ (`tiep_nhan↔tong_don_gui_di`, `da_giao↔so_don_da_giao`, `so_huy↔so_don_huy`, `tien_tra_truoc↔tien_cuoc_gui_tra_truoc`, `tien_cod↔tien_cod_da_thu`, `tien_hoan↔tien_da_hoan`, `doanh_thu↔tong_doanh_thu`); (b) hôm nay `gio` cộng lại = hôm nay `ngay`; (c) mỗi mốc ngày có dữ liệu trong tháng = `thong_ke_hang_tai_diem` của riêng ngày đó; (d) số mốc: hôm nay `gio` = 24, tháng hiện tại = số ngày của tháng, năm = 12, `thang` cho 2026-09-15..2026-11-02 = 3 mốc.
Expected: in `OK` cho mọi kiểm tra.

Thêm: gọi HTTP `GET /gui-hang/thong-ke-chuoi?...&diem_id=<id VP Lào Cai>` bằng token NV Mỹ Đình → 403.

- [ ] **Step 8: Commit**

`Gui hang: API thong-ke-chuoi theo gio/ngay/thang, go thong-ke-theo-ngay`

---

### Task 2: Bộ chọn kỳ + tải dữ liệu theo kỳ + biểu đồ sản lượng mới

**Files:**
- Modify: `frontend/nhan-vien/gui-hang/index.html` (khối `#tab-thong-ke` 334–419; thêm `<script src="bieu-do.js">` trước `thong-ke.js`)
- Modify: `frontend/nhan-vien/gui-hang/thong-ke.js` (viết lại phần kỳ + tải; bỏ `veBieuDo`, `buocTrucDoc`, `theoDoiKichThuocBieuDo` — chuyển sang `bieu-do.js`)
- Create: `frontend/nhan-vien/gui-hang/bieu-do.js`
- Modify: `frontend/nhan-vien/gui-hang/khoi-tao.js` (129–147 sự kiện; 223 `datKhoangNgay(30)`)
- Modify: `frontend/nhan-vien/gui-hang/core.js` (state: bỏ `bieuDoSoNgay`, `doiSoat`; thêm `ky`, `thongKe`, `phienThongKe`)
- Modify: `frontend/nhan-vien/gui-hang/style.css` (bộ chọn kỳ; giữ các lớp `.chart-*` hiện có)

**Interfaces:**
- Consumes: API Task 1.
- Produces (dùng ở Task 3–5):
  - `state.ky = { cheDo: "ngay"|"thang"|"nam"|"tuy_chon", tu: "YYYY-MM-DD", den: "YYYY-MM-DD", donVi: "gio"|"ngay"|"thang", nhan: string, slug: string }` — `nhan`: `"Ngày 05/11/2026"`, `"Tháng 11/2026"`, `"Năm 2026"`, `"01/10/2026 – 05/11/2026"`; `slug`: `"2026-11-05"`, `"2026-11"`, `"2026"`, `"2026-10-01_2026-11-05"`.
  - `state.thongKe = { ky, tk, chuoi, doiSoat, vanPhong: string }` — gán **một lần** sau khi cả 3 API về, chỉ khi phiên còn mới; `vanPhong` là tên văn phòng đang xem hoặc `"Toàn hệ thống"`.
  - `thong-ke.js`: `taoKy(cheDo, tu, den) -> ky` (thuần, tự suy `donVi`: ngay→gio, thang→ngay, nam→thang, tuy_chon→ngay nếu ≤ 62 ngày, ngược lại thang); `dichKy(ky, buoc /* -1|1 */) -> ky`; `kyChuaHomNay(ky) -> bool`; `taiThongKe() -> Promise<void>`; `renderThongKe()` (vẽ lại toàn tab từ `state.thongKe`).
  - `bieu-do.js`:
    - `nhanMoc(moc: string, donVi) -> string` — `"14h"`, `"05/11"`, `"Th11"`.
    - `rutGonTien(n: number) -> string` — `1250000 → "1,3tr"`, `500000 → "500k"`, `-95000 → "−95k"`, `0 → "0"`.
    - `veBieuDoCot(container, cauHinh, rong?)` — `cauHinh = { nhan: string[], moc: string[], soMocDaQua: number, cot: [{ten, lop, giaTri: number[]}], chong: bool, duong?: {ten, lop, giaTri: number[]}, dinhDangTruc: (n)=>string, tieuDeMoc: (i)=>string, chuTrong: string }`. Mỗi mốc là `<g data-moc="...">`; mốc có chỉ số `>= soMocDaQua` thêm `data-tuong-lai` và không vẽ cột/điểm. Trục dọc có phần âm khi giá trị nhỏ nhất < 0. `rong` cho bản in (bỏ qua `clientWidth`).
    - `theoDoiKichThuoc(container, ve: () => void)` — tổng quát hóa `theoDoiKichThuocBieuDo` cũ.
  - DOM: `#tkCheDo [data-che-do]`, `#tkNgay` (date), `#tkThang` (month), `#tkNam` (select), `#tkTuNgay`/`#tkDenNgay` (giữ), `#tkLui`, `#tkToi`, `#tkNhanKy`, `#bdSanLuong` (thay `#columnChartContainer`).

- [ ] **Step 1: State + hàm kỳ thuần trong `thong-ke.js` / `core.js`**

Mặc định khi mở trang: `taoKy("thang", <ngày 1 tháng này>, <ngày cuối tháng này>)` (thay `datKhoangNgay(30)` ở `khoi-tao.js:223`). `kyChuaHomNay` so `den >= hôm nay` (giờ máy, `ngayISO(new Date())`). Ô năm: năm hiện tại và 4 năm trước.

- [ ] **Step 2: Kiểm hàm thuần bằng Node**

Run: `node -e "<nạp thong-ke.js qua vm với stub $ / state rỗng>; assert taoKy('nam','2028-01-01','2028-12-31').donVi==='thang'; assert dichKy(taoKy('thang','2026-01-01','2026-01-31'),-1).tu==='2025-12-01'; assert dichKy(taoKy('thang','2026-01-31'...),1).den==='2026-02-28'; assert taoKy('tuy_chon','2026-09-01','2026-11-01').donVi==='ngay'; assert taoKy('tuy_chon','2026-09-01','2026-11-02').donVi==='thang'"` (ghi đoạn kiểm vào scratchpad, không vào repo).
Expected: không lỗi assert.

- [ ] **Step 3: HTML + sự kiện**

Thanh lọc: 4 nút chế độ; chỉ hiện ô nhập của chế độ đang chọn; ◀ ▶ ẩn ở `tuy_chon`, ▶ `disabled` khi `kyChuaHomNay`. Đổi ô nhập / bấm chế độ / ◀ ▶ / đổi văn phòng (quản lý) → `taiThongKe()`. Ô Từ > Đến giữ thông báo cũ "Khoảng ngày không hợp lệ". Tiêu đề khối biểu đồ: "📈 Sản lượng — " + `ky.nhan`. Bỏ `#tkBieuDoRange`. Dưới 2 khung "Hàng gửi đi" / "Hàng nhận về" thêm chú thích nhỏ: các ô đang chờ / trên xe / sắp đến / chờ lấy / chưa báo / chờ > 7 ngày / tồn "tính tại thời điểm xem, không theo kỳ".

- [ ] **Step 4: `taiThongKe` có chống phản hồi cũ**

Tăng `state.phienThongKe`; gọi `/thong-ke`, `/thong-ke-chuoi`, `/doi-soat` bằng `Promise.allSettled` (tham số `tu_ngay`, `den_ngay`, `don_vi`, `...phamViQuery()`); phiên đã cũ khi về thì bỏ. Phần nào lỗi thì trường đó trong `state.thongKe` là `null`, khu vực phụ thuộc hiện "Không tải được …: <lỗi>" trong khung của nó (ô số → toast như hiện tại; biểu đồ → chữ trong khung), các phần khác vẫn hiện. `soMocDaQua` = số mốc có thời điểm bắt đầu ≤ bây giờ.

- [ ] **Step 5: `bieu-do.js` + biểu đồ sản lượng**

Chuyển logic `veBieuDo` cũ sang `veBieuDoCot` (giữ nguyên bước chia tròn, nhãn thưa ≥ 48px, số trên đầu cột khi đủ chỗ, `<title>` tooltip). Biểu đồ sản lượng: 2 cột `chart-cot--tiep-nhan`, `chart-cot--da-giao`. Kỳ không có đơn → `chuTrong` "Chưa có đơn nào trong kỳ".

- [ ] **Step 6: Kiểm cú pháp + bấm thử**

Run: `Get-ChildItem frontend\nhan-vien\gui-hang\*.js | ForEach-Object { node --check $_.FullName }` → không lỗi.
Mở trang bằng NV Mỹ Đình (Live Server): mặc định "Tháng 11/2026"; biểu đồ 30 mốc, mốc sau hôm nay trống; ◀ sang tháng 10, ▶ mở lại; Ngày → 24 mốc "0h…23h"; Năm → 12 mốc "Th1…Th12"; Console không lỗi đỏ.

- [ ] **Step 7: Commit**

`Gui hang: thong ke chon ky ngay/thang/nam, bieu do san luong theo ky`

---

### Task 3: Ba biểu đồ còn lại

**Files:**
- Modify: `frontend/nhan-vien/gui-hang/bieu-do.js`, `frontend/nhan-vien/gui-hang/thong-ke.js` (`renderThongKe`), `frontend/nhan-vien/gui-hang/index.html`, `frontend/nhan-vien/gui-hang/style.css`

**Interfaces:**
- Consumes: `state.thongKe`, `veBieuDoCot`, `rutGonTien`, `nhanMoc` (Task 2).
- Produces: `veBieuDoTron(container, { phan: [{ten, lop, giaTri, phu: string}], giua: string, chuTrong }, rong?)`, `veBieuDoNgang(container, { hang: [{ten, giaTri}], dinhDang, chuTrong }, rong?)`; DOM `#bdTienMat`, `#bdCoCauTien`, `#bdTienNhanVien`.

- [ ] **Step 1: Biểu đồ tiền mặt `#bdTienMat`**

`veBieuDoCot` với `chong: true`, cột `tien_tra_truoc` + `tien_cod`, `duong` = `doanh_thu` (nhãn "Còn lại"), trục `rutGonTien`; `tieuDeMoc` ghi đủ "trả trước, thu khi giao, hoàn, còn lại" bằng `dinhDangTien`. Chú thích 3 mục.

- [ ] **Step 2: Biểu đồ tròn `#bdCoCauTien`**

`phan` = trả trước (`tk.tien_cuoc_gui_tra_truoc`, phụ: % + số đơn = Σ`doiSoat.nhan_vien[].so_don_tra_truoc`) và người nhận trả (`tk.tien_cod_da_thu`, Σ`so_don_cod`); `giua` = tổng hai khoản. Cả hai 0 → "Chưa có khoản thu trong kỳ".

- [ ] **Step 3: Cột ngang `#bdTienNhanVien`**

Từ `doiSoat.nhan_vien` theo `tong_tien` giảm dần; > 10 người → 9 người đầu + "Khác" (cộng phần còn lại); giá trị âm dùng lớp màu riêng (`chart-cot--am`), cột đi sang trái từ trục 0.

- [ ] **Step 4: Bố cục**

Sản lượng và Tiền mặt mỗi cái một hàng rộng; Cơ cấu + Tiền theo nhân viên chung hàng hai cột trong `.dashboard-chart-grid`, ≤ 880px xuống một cột; bảng đối soát giữ ngay dưới. Màu lấy từ `design-tokens.css`.

- [ ] **Step 5: Kiểm**

`node --check` toàn bộ JS → không lỗi. Bấm thử ở 1920 / 880 / 400px: không cuộn ngang trang; ngày demo có hủy đơn hiện tiền hoàn trong tooltip.
Kiểm trục âm trong Console: `veBieuDoCot(document.querySelector('#bdTienMat'), {...cauHinh với doanh_thu [-95000, 50000]...})` → có vạch trục âm và điểm đường nằm dưới vạch 0, trong khung SVG.

- [ ] **Step 6: Commit**

`Gui hang: bieu do tien mat, co cau cach tra cuoc, tien theo nhan vien`

---

### Task 4: Xuất Excel + In báo cáo

**Files:**
- Create: `frontend/nhan-vien/gui-hang/vendor/xlsx.mini.min.js` (SheetJS CE 0.20.3: `https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.mini.min.js`)
- Create: `frontend/nhan-vien/gui-hang/bao-cao.js` (script thường, nạp sau `thong-ke.js`)
- Modify: `frontend/nhan-vien/gui-hang/index.html` (2 nút đầu tab; vùng `<section id="baoCaoThongKe" class="bao-cao-in">` ẩn), `frontend/nhan-vien/gui-hang/khoi-tao.js` (gắn nút), `frontend/nhan-vien/gui-hang/style.css` (mục 17 in ấn), `frontend/nhan-vien/gui-hang/thong-ke.js` (`xuatCsvDoiSoat` đọc `state.thongKe.doiSoat`)

**Interfaces:**
- Consumes: `state.thongKe`, `veBieuDoCot/Tron/Ngang(..., rong)`, `inPhanTu`, `nguoiDungHienTai.hoTen`, `dinhDangTien`.
- Produces: `taiThuVienExcel() -> Promise<XLSX>` (chèn `<script>` một lần, dùng lại promise); `xuatExcelThongKe() -> Promise<void>`; `dungBaoCaoThongKe() -> boolean` (dựng nội dung `#baoCaoThongKe`, `false` nếu thiếu dữ liệu); `inBaoCaoThongKe()` (= `dungBaoCaoThongKe()` rồi `inPhanTu`); nút `#btnXuatExcelThongKe`, `#btnInBaoCaoThongKe`.

- [ ] **Step 1: Tải SheetJS về `vendor/`**

Run: `Invoke-WebRequest https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.mini.min.js -OutFile frontend/nhan-vien/gui-hang/vendor/xlsx.mini.min.js`
Expected: file ~ 250–300 KB, dòng đầu có `/*! xlsx.js (C) 2013-present SheetJS`.

- [ ] **Step 2: `xuatExcelThongKe`**

Chưa có `state.thongKe` hoặc một trong `tk/chuoi/doiSoat` là `null` → toast cảnh báo "Chưa đủ dữ liệu của kỳ để xuất — tải lại thống kê" (áp dụng cả In báo cáo). Sheet và nội dung đúng spec mục 6:
- `"Tổng quan"`: dòng Văn phòng / Kỳ (`ky.nhan`) / Người xuất / Thời điểm xuất; rồi từng chỉ số `[nhãn như trên tab, giá trị]`; dòng ghi chú "Các chỉ số đang chờ / trên xe / chờ lấy / tồn tính tại thời điểm xuất".
- `"Theo giờ"` | `"Theo ngày"` | `"Theo tháng"`: cột `Mốc, Tiếp nhận, Đã giao, Hủy, Trả trước (VNĐ), Thu khi giao (VNĐ), Hoàn (VNĐ), Còn lại (VNĐ)`, mốc ghi bằng `nhanMoc` đầy đủ (vd "05/11/2026", "14h 05/11/2026", "11/2026"), dòng `TỔNG` cuối.
- `"Đối soát nhân viên"`: cùng cột như `xuatCsvDoiSoat`, dòng `TỔNG`.
Ô tiền là số với `z = "#,##0"`; tên người là ô chuỗi (`t: "s"`), không bao giờ thành công thức. Tên file `thong-ke-gui-hang_${ky.slug}.xlsx`. Lỗi nạp thư viện → toast "Không tải được thư viện xuất Excel".

- [ ] **Step 3: `inBaoCaoThongKe`**

Dựng nội dung `#baoCaoThongKe` từ `state.thongKe`: tiêu đề "BÁO CÁO GỬI HÀNG", văn phòng, kỳ, người in, thời điểm in; bảng chỉ số; khung tiền mặt; 4 biểu đồ vẽ với `rong = 680`; bảng đối soát; hai ô ký "Người lập" / "Người nhận tiền". Rồi `inPhanTu($("baoCaoThongKe"))`. CSS: `.bao-cao-in { display: none }` trên màn hình; trong `@media print` khi là `.print-target` thì hiện, `print-color-adjust: exact`, `@page { size: A4 portrait }`, biểu đồ không bị cắt giữa trang (`break-inside: avoid`).

- [ ] **Step 4: Kiểm**

`node --check` → không lỗi. Bấm Xuất Excel ở chế độ Tháng → mở file bằng Excel: 3 sheet, ô tiền là số có phân cách nghìn, dòng TỔNG khớp ô số trên tab. Bấm In báo cáo → xem trước bản in: 1–2 trang A4, không có sidebar, đủ 4 biểu đồ có màu. Đổi sang kỳ khác rồi xuất lại → nội dung theo kỳ mới. Tab Network: bấm xuất/in **không** phát sinh request API mới (chỉ tải `xlsx.mini.min.js` lần đầu).

- [ ] **Step 5: Commit**

`Gui hang: xuat Excel 3 sheet va in bao cao thong ke co bieu do`

---

### Task 5: Kiểm thử giao diện tự động + tài liệu

**Files:**
- Modify: `backend/scripts/kiem_thu_giao_dien_gui_hang.py` (nhóm J ~905–956, `k_j1` ~1128, `chay_khoi` ~1240, `chay_day_du` ~1305)
- Modify: `backend/scripts/requirements-kiem-thu-giao-dien.txt` (thêm `openpyxl`)
- Modify: `QUY_TRINH_TEST_GUI_HANG.md` (mục J 239–248, Bước 4, số ca ở 3.0)
- Modify: `NGHIEP_VU_GUI_HANG.md` (mục 6 dòng 164–168, mục 8.6 dòng 265)
- Modify: `KE_HOACH_SUA_GUI_HANG.md` (thêm mục `## 10. Đợt F — Thống kê theo ngày/tháng/năm, biểu đồ, xuất báo cáo (05/11/2026)` sau mục 9)

**Interfaces:**
- Consumes: DOM và API của Task 1–4; tiện ích script sẵn có `ca`, `mo_tab`, `so`, `api`, `toast_cuoi`, `xoa_toast`, `chon`, `ANH`.

- [ ] **Step 1: Sửa ca cũ theo DOM mới**

- `j3`: thay `#tkPreset [data-so-ngay='1']` bằng chọn chế độ Ngày (`#tkCheDo [data-che-do='ngay']`, `#tkNgay` = hôm nay).
- `j4`: chọn chế độ Tùy chọn trước khi điền `#tkTuNgay` > `#tkDenNgay`; cuối ca quay về chế độ Tháng.
- `k_j1`: giữ phép kiểm doanh thu; thêm: tiêu đề `#tkNhanKy` dạng "Tháng MM/YYYY".

- [ ] **Step 2: Thêm ca mới**

```python
@ca("J7", "Kỳ: mặc định tháng này, ◀ lùi đúng 1 tháng, ▶ khóa ở tháng hiện tại, bấm ◀ 3 lần nhanh vẫn khớp")
# assert #tkToi disabled; click #tkLui → #tkNhanKy = tháng trước; 3 click liên tiếp không chờ → chờ networkidle
# → page.evaluate("state.thongKe.ky.nhan") == #tkNhanKy.innerText và #tkTongGuiDi == api /thong-ke cùng kỳ; quay về tháng này

@ca("J8", "Số mốc theo đơn vị: Ngày 24, Tháng = số ngày của tháng, Năm 12; mốc tương lai không có cột")
# đếm "#bdSanLuong g[data-moc]"; tháng hiện tại: mọi g[data-tuong-lai] không chứa rect.chart-cot

@ca("J9", "API thong-ke-chuoi: tổng mốc = /thong-ke (giờ/ngày/tháng, 1 VP và toàn hệ thống), mốc ngày = /thong-ke của ngày đó, NV gọi VP khác 403")
# def j9(tk_md, tk_ql, ids) — chỉ gọi api(), như p_api

@ca("J10", "Xuất Excel: 3 sheet, dòng TỔNG khớp màn hình")
# expect_download click #btnXuatExcelThongKe; openpyxl.load_workbook → sheetnames == ["Tổng quan", "Theo ngày", "Đối soát nhân viên"];
# ô TỔNG cột "Tiếp nhận" của sheet 2 == so(page, "#tkTongGuiDi"); ô tiền là int

@ca("J11", "In báo cáo: chỉ vùng báo cáo, đủ 4 biểu đồ, không sidebar")
# như k5: page.evaluate("dungBaoCaoThongKe()") (không gọi window.print thật), thêm print-target cho #baoCaoThongKe + body.dang-in,
# emulate_media print → "#baoCaoThongKe svg" đếm 4, sidebar ẩn, có chữ "Người lập"

@ca("J12", "Biểu đồ tiền mặt vẽ được doanh thu âm trong khung")
# page.evaluate gọi veBieuDoCot trên div tạm với duong [-95000, 50000] → điểm âm có cy > y của vạch 0 và < chiều cao SVG
```

Đăng ký: `chay_khoi` giữ `k_j1`; `chay_day_du` thêm `j7(md); j8(md); j9(tk_md, tk_ql, ids); j10(md); j11(md); j12(md)` sau `j6`.

- [ ] **Step 3: Chạy**

Run: `.\.venv\Scripts\pip install -r backend/scripts/requirements-kiem-thu-giao-dien.txt` rồi `.\.venv\Scripts\python backend/scripts/kiem_thu_giao_dien_gui_hang.py tat-ca`
Expected: [Khói] 13/13; các ca còn lại đều ĐẠT trừ I1 (lỗi đã biết của PR #47); J7–J12 ĐẠT; không có lỗi Console mới.

- [ ] **Step 4: Tài liệu**

- `QUY_TRINH_TEST_GUI_HANG.md`: J1 bỏ "biểu đồ 7/14/30 ngày", thay bằng chọn kỳ; thêm J7–J12 (tài khoản, bước, kết quả mong đợi); Bước 4 thêm dòng P6 cho `GET /gui-hang/thong-ke-chuoi`; cập nhật số ca ở 3.0 và kết quả ngày chạy.
- `NGHIEP_VU_GUI_HANG.md` mục 6: "chọn khoảng ngày" → chọn kỳ Ngày/Tháng/Năm/Tùy chọn (biểu đồ chia giờ/ngày/tháng); 4 biểu đồ; xuất Excel 3 trang tính và in báo cáo có biểu đồ, ký "Người lập / Người nhận tiền". Mục 8.6 luồng chính: "chọn kỳ thống kê".
- `KE_HOACH_SUA_GUI_HANG.md` mục 10: việc đã làm theo task, API mới / API đã gỡ, quyết định trong spec mục "Quyết định của Claude", kết quả test.

- [ ] **Step 5: Commit**

`Gui hang: ca kiem thu J7-J12 cho thong ke theo ky, cap nhat tai lieu`
