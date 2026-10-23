# Kế hoạch làm UC-37 — Khóa / mở khóa tài khoản

> **File này là kế hoạch từng bước, chưa có code trên nhánh.** Nhánh làm: `feature/Nghia-uc37-khoa-mo-khoa-tai-khoan` (tạo từ `integration/gop-nhanh-thanh-vien`, commit `cd77d29`, 23/10/2026).
> Nguồn: `NGHIEP_VU.md` UC-37 (đã gộp UC-38 cũ), mục 8.7 điểm 5–6, mục 8.9, mục 9; `DATABASE.md` mục 1.1–1.3, 1.5, 6.3; `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` mục 6; code UC-36 đã merge (#38).
> **Có sẵn một bản nháp UC-37 đã viết rồi cất đi** trong `git stash@{0}` ("UC-37 nhap…"): 31 test, backend + frontend, đã chạy thật trên API. Dùng làm tham khảo khi làm lại (mục 9), không bắt buộc lấy lại.

---

## 1. UC-37 làm về cái gì

**Khóa / mở khóa tài khoản** (UC-37 khóa + UC-38 mở khóa gộp làm một): người có quyền "tắt" một tài khoản để người đó không dùng hệ thống được nữa, và "bật" lại khi cần. Dùng khi nhân viên nghỉ việc, vi phạm, hoặc nghi lộ tài khoản. **Không xóa gì**, lịch sử vẫn giữ.

| | |
|---|---|
| Actor | `quan_ly` gốc, `quan_ly` thường hoặc `quan_ly_nhan_su` — mỗi bậc chỉ khóa được bậc thấp hơn mình (mục 2); `ke_toan` không khóa ai |
| Cách khóa | Đặt `nguoi_dung.dang_hoat_dong = false` (mở khóa: `true`) |
| Hiệu lực | Đăng nhập mới bị chặn; **phiên đang mở cũng mất quyền ngay** (middleware tra DB mỗi request) |

---

## 2. Ai khóa / mở khóa được ai

**Quy tắc bậc (đã chốt 23/10/2026):** `quan_ly` gốc > (`quan_ly` thường = `ke_toan`) > `quan_ly_nhan_su` > 4 vai trò vận hành. Chỉ khóa / mở khóa được tài khoản **bậc thấp hơn** mình; **cùng bậc hoặc cao hơn thì không**. `ke_toan` cùng bậc `quan_ly` thường nên **chỉ quản lý gốc** khóa / mở khóa được kế toán.

| Người thao tác | Khóa / mở khóa được | KHÔNG được |
|---|---|---|
| `quan_ly` **gốc** | `quan_ly` thường, `ke_toan`, `quan_ly_nhan_su`, `phu_xe`, quầy vé, gửi hàng, điều độ viên | Chính mình; (không ai khóa được gốc) |
| `quan_ly` **thường** | `quan_ly_nhan_su`, `phu_xe`, quầy vé, gửi hàng, điều độ viên | `quan_ly` khác và `ke_toan` (cùng bậc), gốc, chính mình |
| `quan_ly_nhan_su` | `phu_xe`, quầy vé, gửi hàng, điều độ viên | `ke_toan`, `quan_ly_nhan_su` khác (cùng bậc), `quan_ly`, gốc |
| `ke_toan` và 4 vai trò vận hành | (không có quyền khóa ai; route chỉ mở cho `quan_ly`, `quan_ly_nhan_su`) | — |

> **Khác tài liệu cũ:** spec UC-37 cũ cho "quan_ly bất kỳ" khóa được `quan_ly` khác và `ke_toan`; quyết định mới chặt hơn (đã sửa `NGHIEP_VU.md`, `UML_DIAGRAMS.md`). Cách cài đặt: bảng "người thao tác (gốc / quan_ly thường / QLNS) → tập vai trò mục tiêu"; cần biết người thao tác có phải gốc không (`repo.la_tai_khoan_goc`).

Luật chặn (kiểm tra theo đúng thứ tự này):

| # | Luật | Thông báo | HTTP |
|---|---|---|---|
| 1 | Tài khoản `quan_ly` **gốc** (`la_tai_khoan_goc = true`) → không ai khóa được | "Không ai khóa được tài khoản quản lý gốc" | 403 |
| 2 | **Tự khóa chính mình** (chỉ khi khóa) | "Không thể tự khóa chính mình" | 403 |
| 3 | Mục tiêu có bậc **cùng hoặc cao hơn** người thao tác (theo bảng trên) | "Không đủ quyền thao tác trên tài khoản này" | 403 |
| 4 | Lý do để trống / toàn khoảng trắng | "Vui lòng nhập lý do" | 400 (hoặc 422 ở schema) |

Chặn thêm: tài khoản không tồn tại (404); khóa tài khoản đã khóa / mở khi đang hoạt động (400).

---

## 3. Đã có sẵn — không phải làm lại

| Có sẵn | Ở đâu | Dùng để |
|---|---|---|
| Cột `dang_hoat_dong` | `nguoi_dung` | Cờ khóa / mở khóa |
| Chặn đăng nhập tài khoản khóa | `mat_khau_service.dang_nhap` | Đăng nhập mới bị 401 "Tài khoản đã bị khóa" |
| Chặn phiên đang mở | `auth_middleware.yeu_cau_dang_nhap` (tra DB mỗi request) | Token cũ bị 403 ngay |
| Bảng nhật ký, đã có `khoa_tai_khoan`, `mo_khoa_tai_khoan` trong CHECK | `nhat_ky_quan_ly_nhan_su` | Ghi khi người thao tác là QLNS |
| Hàm ghi nhật ký | `nhat_ky_quan_ly_nhan_su_repository.ghi` | |
| Hàm gửi thông báo | `thong_bao_khach_service.gui` | Báo thiếu phụ xe |
| Danh sách id theo vai trò | `nguoi_dung_repository.danh_sach_id_theo_vai_tro` | Tìm quản lý / điều độ viên để báo |
| Router, schema, repository, service, trang `tai-khoan.html`, cột Trạng thái | Code UC-36 | **Làm tiếp trên các file này**, không tạo file mới |
| Mẫu test | `test_tai_khoan_can_bo_service.py` (fixture `gia_lap`, `monkeypatch`) | |

**Không cần migration.**

---

## 4. Phạm vi bản đầu và các điểm cần chốt

### 4.1. Đề xuất phạm vi bản đầu

| Làm | Không làm / chưa làm |
|---|---|
| Khóa / mở khóa tài khoản **cán bộ** bằng `dang_hoat_dong` | **Khách hàng: đã chốt 23/10 — không ai khóa/mở được**, hệ thống tự khóa theo mục 9; UC-37 không áp dụng |
| Lý do khóa / mở khóa (**bắt buộc, gõ chữ tự do**), ghi nhật ký (QLNS -> `nhat_ky_quan_ly_nhan_su`, `quan_ly` -> `nhat_ky_admin`, migration làm sau) | (không còn gì bị loại ở nhóm này) |
| Cảnh báo + thông báo khi khóa **phụ xe** làm xe thiếu phụ xe | Cảnh báo khi khóa **điều độ viên** làm tuyến hết người phụ trách |

### 4.2. Các điểm cần bàn / chốt với nhóm

| # | Câu hỏi | Đề xuất mặc định | Ảnh hưởng nếu khác |
|---|---|---|---|
| 1 | ✅ **ĐÃ CHỐT (23/10/2026): khách hàng** — không ai (kể cả `quan_ly`, `quan_ly_nhan_su`) khóa, mở khóa hay gỡ hạn chế tài khoản khách hàng. Khách vi phạm thì hệ thống tự khóa theo mục 9; bị khóa coi như mất tài khoản | UC-37 chỉ cho cán bộ; API trả 400 "chỉ áp dụng cho cán bộ" với khách hàng | Không làm gì với `ho_so_khach_hang`; đã sửa `NGHIEP_VU.md` (8.7 điểm 5–6, mục 9, UC-37), `DATABASE.md` (`bi_khoa`), `UML_DIAGRAMS.md` |
| 2 | ✅ **ĐÃ CHỐT (23/10/2026): lưu vào `nhat_ky_admin`** (đã thiết kế ở `DATABASE.md` 6.2: `admin_id`, `hanh_dong`, `doi_tuong_loai`, `doi_tuong_id`, `ghi_chu`, `thoi_gian`) | `quan_ly` (gốc hay thường) khóa / mở khóa → ghi `nhat_ky_admin`; QLNS → `nhat_ky_quan_ly_nhan_su` như cũ. **Migration tạo bảng `nhat_ky_admin` làm sau** (bước 6b) — code viết trước, chưa có bảng thì test tay ca `quan_ly` chưa chạy được | Cần `yoyo apply` cho cả nhóm khi có migration; UC-52 sau này cho `quan_ly` xem cả hai bảng |
| 3 | ✅ **ĐÃ CHỐT (23/10/2026): thông báo khi khóa phụ xe** gửi `quan_ly` + `dieu_do_vien` đang hoạt động (không lọc văn phòng), **không gửi `quan_ly_nhan_su`** (khớp UC-51 bước 5), **trừ chính người vừa khóa** | Người nhận = `quan_ly` đang hoạt động + `dieu_do_vien` đang hoạt động, bỏ `actor_id` | Thêm QLNS về sau chỉ là một dòng nếu thực tế cần |
| 4 | ✅ **ĐÃ CHỐT (23/10/2026): quy tắc bậc** — gốc khóa được tất cả; `quan_ly` thường khóa được `quan_ly_nhan_su` trở xuống; `quan_ly_nhan_su` chỉ khóa 4 vai trò vận hành; cùng bậc hoặc cao hơn thì không | Xem bảng mục 2 | Code cần biết người thao tác có phải gốc không (`la_tai_khoan_goc`) |
| 5 | ✅ **ĐÃ CHỐT: làm sau.** Cảnh báo khi khóa điều độ viên làm tuyến hết người — đợi bảng `dieu_do_vien_tuyen` của nhóm điều độ viên có rồi mới làm | Đã ghi chú ở: `NGHIEP_VU.md` UC-37 ("Ghi chú triển khai"), file này (mục 8 bên dưới), `BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md` (việc còn lại). Không sửa `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` (file của nhóm đó, mục 6 đã nêu sẵn) | Khi có bảng: thêm hàm đếm tuyến không còn điều độ viên đang hoạt động sau khi khóa; cảnh báo như phụ xe |
| 6 | ✅ **ĐÃ CHỐT: lý do bắt buộc, chỉ gõ chữ** (không chọn từ danh sách) — áp dụng cho cả khóa và mở khóa | `ly_do` bắt buộc, cắt khoảng trắng, 1–500 ký tự; giao diện dùng ô nhập nhiều dòng | Schema bắt buộc; test thêm ca lý do rỗng |

> Điểm 1 ảnh hưởng nhiều nhất đến phạm vi; điểm 2 và 3 ảnh hưởng thiết kế dữ liệu. Chốt trước khi code thì bước 1–7 bên dưới không phải làm lại.

---

## 5. Các bước làm (theo thứ tự, mỗi bước chạy kiểm tra được riêng)

### Bước 0 — Chuẩn bị
- [ ] Đang ở nhánh `feature/Nghia-uc37-khoa-mo-khoa-tai-khoan`, `git status` sạch.
- [ ] Docker chạy (`docker-compose up -d --build`), đã `yoyo apply ./migrations` sau lần pull gần nhất (có thêm migration `20261023_0900_thong_bao_duong_dan.sql`).
- [x] Mục 4.2 đã chốt đủ 6 điểm (1 khách hàng, 2 `nhat_ky_admin`, 3 thông báo, 4 bậc, 5 điều độ viên làm sau, 6 lý do bắt buộc).
- [ ] Báo nhóm trước khi làm: UC-36/37 đang giao Người 1 trong `CONTRIBUTING.md`; đã báo UC-36 thì UC-37 cùng ý.

### Bước 1 — Schema (`backend/app/schemas/tai_khoan_can_bo_schema.py`, thêm vào cuối) — ✅ XONG 23/10, 11 test trong `test_tai_khoan_can_bo_schema.py`
- [x] `DoiTrangThaiTaiKhoanRequest`: `ly_do: str` **bắt buộc**, cắt khoảng trắng hai đầu, độ dài 1–500 (validator báo "Vui lòng nhập lý do").
- [x] `XeThieuPhuXe`: `xe_id: UUID`, `bien_so: str`.
- [x] `DoiTrangThaiTaiKhoanResponse`: `id`, `dang_hoat_dong`, `canh_bao_xe_thieu_phu_xe: list[XeThieuPhuXe]` (mặc định rỗng).

### Bước 2 — Repository (`backend/app/repositories/tai_khoan_can_bo_repository.py`, thêm vào cuối) — ✅ XONG 23/10, đã kiểm tra 17/17 trên DB thật
- [x] `tim_tai_khoan(nguoi_dung_id)` → `id, email, ho_ten, vai_tro, dang_hoat_dong, la_tai_khoan_goc` (`None` nếu không có).
- [x] `dat_trang_thai_hoat_dong(nguoi_dung_id, dang_hoat_dong)` — chỉ `UPDATE` cờ, commit trong hàm.
- [x] `xe_thieu_phu_xe(nguoi_dung_id)` — các xe mà phụ xe này thuộc biên chế **cố định** (`xe_nhan_su.loai = 'co_dinh'`, `trang_thai = 'dang_hoat_dong'`) và khi không tính người này không còn phụ xe cố định nào: hồ sơ `dang_lam` **và** tài khoản `dang_hoat_dong`. Gọi **sau** khi khóa để người bị khóa tự bị loại khỏi phép đếm. Kết quả `DISTINCT`, sắp theo biển số.

### Bước 2b — Repository nhật ký admin (file **mới** `backend/app/repositories/nhat_ky_admin_repository.py`)
- [x] `ghi(admin_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu=None)` — chỉ `INSERT` vào `nhat_ky_admin` (`DATABASE.md` mục 6.2), **không** có hàm sửa / xóa (nhật ký chỉ thêm), cùng kiểu với `nhat_ky_quan_ly_nhan_su_repository.ghi`.
- [x] Bảng `nhat_ky_admin` đã có migration (làm cùng lúc, xem bước 6b). Unit test (giả lập) không cần bảng; test tay ca `quan_ly` thì cần.

### Bước 3 — Service (`backend/app/services/tai_khoan_can_bo_service.py`, thêm vào cuối)
- [x] Thêm import: `thong_bao_khach_service as thong_bao`, `KhongTimThay`.
- [x] Bảng `_QUYEN_KHOA` theo **quy tắc bậc** (mục 2): gốc → `quan_ly`, `ke_toan`, `quan_ly_nhan_su` + 4 vai trò vận hành; `quan_ly` thường → `quan_ly_nhan_su` + 4 vai trò vận hành; `quan_ly_nhan_su` → 4 vai trò vận hành. Người gọi là `quan_ly` thì tra `repo.la_tai_khoan_goc(actor_id)` để chọn dòng gốc hay thường.
- [x] `_tim_muc_tieu(actor_id, actor_vai_tro, muc_tieu_id, la_khoa)`: tìm tài khoản (404 nếu không) → khách hàng (400, nếu chọn phạm vi bản đầu) → luật 1 gốc → luật 2 tự khóa (chỉ khi `la_khoa`) → luật 3 vai trò ngoài tập được phép của bậc người gọi.
- [x] `khoa_tai_khoan(...)`: gọi `_tim_muc_tieu`; đã khóa → 400; `dat_trang_thai_hoat_dong(False)`; ghi nhật ký `khoa_tai_khoan`; **nếu mục tiêu là `phu_xe`** thì `xe_thieu_phu_xe` và báo.
- [x] `mo_khoa_tai_khoan(...)`: tương tự; đang hoạt động → 400; `True`; nhật ký `mo_khoa_tai_khoan`; không cảnh báo gì.
- [x] `_bao_xe_thieu_phu_xe(muc_tieu, xe_thieu)`: thông báo (tên phụ xe + danh sách biển số) cho `quan_ly` + `dieu_do_vien` đang hoạt động, **bỏ chính người vừa khóa, không gửi `quan_ly_nhan_su`**. **Chỉ nhắc, không tự đổi biên chế** (UC-35 / UC-51 là việc người).
- [x] Sửa `_ghi_nhat_ky` thêm tham số `hanh_dong` (mặc định `"tao_tai_khoan"` để UC-36 không đổi hành vi): actor `quan_ly_nhan_su` → `nhat_ky_quan_ly_nhan_su_repository.ghi`; actor `quan_ly` (gốc hay thường) → `nhat_ky_admin_repository.ghi`. Lý do **bắt buộc** nên luôn có `ghi_chu`. **Không ghi mật khẩu hay dữ liệu nhạy cảm.** (Tuỳ chọn: `tao_tai_khoan` của `quan_ly` cũng ghi `nhat_ky_admin` cho nhất quán — hiện UC-36 chưa ghi.)

### Bước 4 — Unit test (`backend/tests/unit/test_tai_khoan_can_bo_service.py`, thêm vào cuối)
Mục tiêu khoảng 30 test, giả lập repository bằng `monkeypatch`:
- [x] Ma trận quyền theo bậc: cả 3 bậc khóa được 4 vai trò vận hành; QLNS bị chặn với `ke_toan`/`quan_ly`/`quan_ly_nhan_su` khác; `quan_ly` thường khóa được QLNS nhưng bị chặn với `quan_ly` khác, `ke_toan`; gốc khóa được `quan_ly` thường, `ke_toan`, QLNS.
- [x] Luật chặn: tài khoản gốc (với cả QLNS lẫn `quan_ly`); tự khóa; đã khóa; mở khi đang hoạt động; không tồn tại; khách hàng.
- [x] Mở khóa: thành công; cùng quy tắc bậc như khóa (QLNS bị chặn với `ke_toan`/`quan_ly`/QLNS khác; `quan_ly` thường bị chặn với `ke_toan`).
- [x] Lý do: rỗng / toàn khoảng trắng bị từ chối (cả khóa và mở khóa); quá 500 ký tự bị từ chối.
- [x] Nhật ký: QLNS khóa → ghi `nhat_ky_quan_ly_nhan_su` kèm lý do đã `strip`; `quan_ly` (gốc và thường) khóa → ghi `nhat_ky_admin`; không ghi chéo bảng.
- [x] Phụ xe: thiếu xe → có cảnh báo và thông báo đúng người (`quan_ly`, rồi các điều độ viên, **không có QLNS, không có người vừa khóa**); không thiếu → không thông báo; vai trò khác phụ xe **không** tra biên chế.
- [x] Chạy: `docker-compose exec -T backend python -m pytest tests/unit/test_tai_khoan_can_bo_service.py -q`.

### Bước 5 — Route (`backend/app/routes/tai_khoan_can_bo.py`, thêm vào cuối)
- [x] `POST /quan-ly-nhan-su/tai-khoan/{muc_tieu_id}/khoa`
- [x] `POST /quan-ly-nhan-su/tai-khoan/{muc_tieu_id}/mo-khoa`
- [x] Cả hai: body `DoiTrangThaiTaiKhoanRequest`, kiểm quyền `QuyenQuanLyNhanSu` (đã có), trả `DoiTrangThaiTaiKhoanResponse`.
- [x] Chuyển `from uuid import UUID` lên cùng nhóm import chuẩn. Không cần sửa `main.py` (router đã đăng ký).

### Bước 6 — Test tay trên API thật (PowerShell hoặc `curl`)
Đăng nhập `quanlynhansu@gmail.com` / `Nhansu@123`, rồi:
- [ ] Tạo tài khoản điều độ viên thử qua UC-36 (mật khẩu `12345678`).
- [ ] Khóa → 200; khóa lại → 400; **đăng nhập tài khoản đó bị 401**; **token cũ gọi `/auth/me` bị 403 ngay**.
- [ ] Mở khóa → 200; mở khi đang hoạt động → 400; đăng nhập lại được.
- [ ] QLNS khóa tài khoản gốc → 403; tự khóa → 403; id lạ → 404.
- [ ] Nhật ký có đủ `khoa_tai_khoan`, `mo_khoa_tai_khoan` và lý do.
- [ ] Ca phụ xe: tạo xe + 2 phụ xe cố định (chèn SQL tạm). Khóa người thứ nhất → không cảnh báo; khóa người thứ hai → cảnh báo đúng biển số, thông báo xuất hiện cho quản lý, biên chế vẫn còn 2 dòng `dang_hoat_dong`.
- [ ] **Dọn dữ liệu test** (nhật ký, thông báo, `xe_nhan_su`, `nhan_su_van_hanh`, `nguoi_dung`, `xe`, `loai_xe`, `diem_don_tra`, `khu_vuc` đã chèn).
- [ ] Ca `quan_ly` gốc / thường / bậc: chưa test tay vì chưa có mật khẩu `admin@nhaxekhach.com`. Muốn test thì đặt mật khẩu tạm qua "Quên mật khẩu" hoặc lấy mã OTP từ DB. Cần làm **sau bước 6b** (cần bảng `nhat_ky_admin`).

### Bước 6b — Migration `nhat_ky_admin` ✅ (làm xong 23/10 cùng bước 2b: `20261023_1000_tao_bang_nhat_ky_admin.sql`)
- [x] File mới trong `backend/migrations/` (đặt tên theo ngày giờ như các migration khác): tạo bảng `nhat_ky_admin` đúng `DATABASE.md` mục 6.2 (`id`, `admin_id` FK `nguoi_dung`, `hanh_dong`, `doi_tuong_loai`, `doi_tuong_id`, `ghi_chu`, `thoi_gian`) + index `(admin_id, thoi_gian DESC)` và `(doi_tuong_loai, doi_tuong_id, thoi_gian DESC)` giống bảng nhật ký của QLNS.
- [x] Chạy `docker-compose exec backend yoyo apply ./migrations`; **báo nhóm chạy lại sau khi pull**.
- [ ] Rồi test tay ca `quan_ly` khóa / mở khóa: dòng nhật ký xuất hiện ở `nhat_ky_admin`, không xuất hiện ở bảng của QLNS.

### Bước 7 — Frontend (`frontend/nhan-vien/quan-li-nhan-su/tai-khoan.html`)
- [x] Mỗi hàng thêm nút **Khóa** (tài khoản đang hoạt động) hoặc **Mở khóa** (đã khóa), qua `extraActions` của `renderDataTable`.
- [x] Hộp thoại xác nhận: mô tả hậu quả (người này sẽ không đăng nhập được kể cả phiên đang mở), ô **lý do bắt buộc** (ô nhập nhiều dòng, gõ chữ tự do, không chọn danh sách, tối đa 500 ký tự; kiểm tra trước khi gửi, rỗng thì báo "Vui lòng nhập lý do"), nút Hủy / Xác nhận.
- [x] Sau khi **khóa phụ xe** mà có `canh_bao_xe_thieu_phu_xe`: đổi hộp thoại sang trạng thái cảnh báo, liệt kê biển số, nhắc "biên chế không tự đổi; nghỉ việc hẳn dùng cho nghỉ việc ở Hồ sơ nhân sự", nút "Đã hiểu".
- [x] Lỗi từ backend (403/400/404) hiện ngay trong hộp thoại.
- [x] Cập nhật ghi chú đầu `nav.js` (UC-37 nay cùng trang `tai-khoan.html`). Không cần thêm mục menu.
- [ ] (id và cú pháp JS đã kiểm; CÒN xem thử trên trình duyệt) Kiểm tra: mọi `id` script dùng đều có trong HTML; cú pháp JS (VS Code kèm Node: `ELECTRON_RUN_AS_NODE=1 "/d/Software/Microsoft VS Code/Code.exe" <file kiểm tra>`); **xem thử trên trình duyệt** (Live Server cổng 5500).

### Bước 8 — Tài liệu
- [ ] `NGHIEP_VU.md` UC-37: thêm "Ghi chú triển khai" — bản đầu chỉ cán bộ; lý do chỉ vào nhật ký khi QLNS thao tác; cảnh báo điều độ viên chờ bảng `dieu_do_vien_tuyen`.
- [ ] `BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md`: thêm mục UC-37 (file, hàm, kết quả test) và cập nhật bảng tổng quan, "việc còn lại".
- [ ] Nếu đổi điểm nào ở mục 4.2: sửa `NGHIEP_VU.md`/`UML_DIAGRAMS.md` cho khớp **trước khi** code.

### Bước 9 — Chạy cả bộ test, commit, PR
- [ ] `docker-compose exec -T backend python -m pytest tests/unit -q`. Hiện có **7 test lỗi sẵn trên integration** (`test_ve_le.py`, `test_thong_bao_khach.py::test_ipn_ve_le_thanh_cong_bao_khach`, không dính UC-37; đã kiểm bằng `git stash`). Chỉ cần đảm bảo không thêm lỗi mới.
- [ ] Commit (không `git add .`): chỉ các file UC-37 và tài liệu liên quan.
  ```powershell
  git add backend/app/schemas/tai_khoan_can_bo_schema.py backend/app/repositories/tai_khoan_can_bo_repository.py backend/app/services/tai_khoan_can_bo_service.py backend/app/routes/tai_khoan_can_bo.py backend/tests/unit/test_tai_khoan_can_bo_service.py frontend/nhan-vien/quan-li-nhan-su/tai-khoan.html frontend/nhan-vien/quan-li-nhan-su/nav.js NGHIEP_VU.md BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md
  git commit -m "Them UC-37 khoa/mo khoa tai khoan can bo (BE + FE)"
  ```
- [ ] Push, mở PR vào `integration/gop-nhanh-thanh-vien` (**không** vào `main`). Mô tả PR nêu: phạm vi bản đầu, 3 điểm chưa làm (khách hàng, lý do của `quan_ly`, cảnh báo điều độ viên), 7 test lỗi có sẵn.

---

## 6. Dữ liệu và API tóm tắt

```
POST /quan-ly-nhan-su/tai-khoan/{id}/khoa      body: { "ly_do": "..." | null }
POST /quan-ly-nhan-su/tai-khoan/{id}/mo-khoa   body: { "ly_do": "..." | null }
→ 200 { "id": "...", "dang_hoat_dong": false|true,
        "canh_bao_xe_thieu_phu_xe": [ { "xe_id": "...", "bien_so": "..." } ] }
→ 400 đã khóa / đang hoạt động / khách hàng (bản đầu)
→ 403 tài khoản gốc / tự khóa / không đủ quyền
→ 404 không tồn tại
```

---

## 7. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Khóa nhầm quản lý duy nhất khiến không ai quản trị | Tài khoản gốc không ai khóa được; không tự khóa mình |
| Khóa phụ xe giữa lúc xe đang chạy | Chỉ cảnh báo, không tự đổi biên chế; nghỉ việc hẳn dùng UC-51 |
| Code ghi `nhat_ky_admin` nhưng migration chưa có → `quan_ly` khóa sẽ lỗi 500 trên DB thật | Làm migration (bước 6b) **trước khi** merge / trước khi test tay ca `quan_ly`; trong lúc chưa có, chỉ chạy unit test và ca QLNS |
| Điều độ viên bị khóa mà tuyến hết người | Chưa có cảnh báo (cần bảng `dieu_do_vien_tuyen` của nhóm điều độ viên) |
| Nút Khóa hiện cho cả tài khoản gốc / chính mình | Backend chặn và trả lỗi rõ ràng; có thể ẩn nút ở frontend sau nếu API trả cờ gốc |
| Làm trùng việc người khác (`CONTRIBUTING.md` giao Người 1) | Báo nhóm ở bước 0 |

---

## 8. Việc làm liền sau UC-37

0. **Cảnh báo khi khóa điều độ viên làm tuyến hết người phụ trách** — chờ nhóm điều độ viên có bảng `dieu_do_vien_tuyen` (`DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` mục 5–6). Khi có: thêm `tuyen_thieu_dieu_do_vien(nguoi_dung_id)` ở repository (đếm tuyến mà người này phụ trách và không còn điều độ viên nào khác đang hoạt động), gọi sau khi khóa vai trò `dieu_do_vien`, trả thêm `canh_bao_tuyen_thieu_dieu_do` ở response và hiện cảnh báo ở hộp thoại như phụ xe. Chỉ cảnh báo, không chặn.

1. **UC-51 — Cho nghỉ việc:** dùng lại logic "xe thiếu người" và hàm báo thiếu người (gom chung nếu chốt điểm 3 mục 4.2).
2. **UC-52 — Xem nhật ký thao tác:** `nhat_ky_admin` sẽ có sau bước 6b của UC-37, UC-52 cho `quan_ly` xem cả hai bảng.
3. **Đổi văn phòng** (nhánh kèm UC-36): cần nhóm chốt 2 quy tắc ở `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md`.
4. Xóa chuỗi hàm `gan_van_phong_can_bo` khi nhóm đồng ý.

---

## 9. Tham khảo: bản nháp đã cất

`git stash list` → `stash@{0}: … UC-37 nhap (khoa/mo khoa tai khoan can bo)…`. Xem nội dung mà không lấy về:
```powershell
git stash show -p stash@{0} --stat
git show stash@{0}:backend/app/services/tai_khoan_can_bo_service.py
```
Lấy về (khi cần): `git stash pop`. Bản nháp theo đúng phạm vi bản đầu ở mục 4.1 (chỉ cán bộ; thông báo gửi tất cả `quan_ly` và `dieu_do_vien`; lý do tùy chọn).
