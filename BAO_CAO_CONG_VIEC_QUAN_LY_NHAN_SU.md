# Báo cáo công việc — Quản lý nhân sự (Nghĩa)

> **Cập nhật 23/10/2026 — UC-36 bỏ cơ chế mời bằng OTP.** Email cán bộ do công ty cấp nên không cần xác minh. Khi tạo, tài khoản có mật khẩu ban đầu mặc định `12345678` (lưu bản băm; response trả `mat_khau_ban_dau` để nhắc người tạo) và **không gửi email**; cán bộ đổi mật khẩu sau khi đăng nhập. OTP chỉ dùng khi quên mật khẩu. Mọi chỗ bên dưới nhắc "mời/OTP/`da_gui_email`/mail lỗi" cho UC-36 là **bản cũ**; bản đúng ở `NGHIEP_VU.md` UC-36 và `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md` mục 2.4. Giữ lại `da_xac_nhan = true` lúc tạo (`dang_nhap` chặn mọi tài khoản chưa xác nhận).

> Tổng hợp những gì đã làm từ đầu đến 23/10/2026: **UC-49** (mục 2), **UC-36** (mục 2A) và **UC-37 backend + frontend** (mục 2B). Với mỗi phần: file nào **thêm mới**, file nào **sửa**, chức năng từng file/hàm, cách đã kiểm tra. Số liệu UC-49 lấy từ `git` (commit `d49d505`, merged thành `70d9368` #36); UC-36 merged ở #38; UC-37 **chưa commit**.
> Tài liệu nghiệp vụ chính thức vẫn là `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md`, `ARCHITECTURE.md`. Nhật ký chi tiết theo trình tự nằm ở `TOM_TAT_QUAN_LY_NHAN_SU.md`.

---

## 1. Tổng quan

| Hạng mục | Trạng thái |
|---|---|
| **UC-49** Quản lý hồ sơ nhân sự vận hành (tài xế/phụ xe) + cảnh báo giấy tờ hết hạn | ✅ Xong cả backend và frontend, **đã merge** vào `integration/gop-nhanh-thanh-vien` (#36). Chưa có test tự động |
| **UC-36** Tạo tài khoản cán bộ | ✅ Backend + frontend xong, **đã merge** (#38, squash `f912340`). Frontend chưa xem trên trình duyệt thật |
| Nhánh kèm theo UC-36: **đổi văn phòng** | 📐 Đã ghi nghiệp vụ + sơ đồ + kế hoạch. **Chưa code**: chờ nhóm chốt 2 quy tắc (còn đơn đang xử lý có chặn không; lý do có bắt buộc không) |
| **UC-37** Khóa / mở khóa tài khoản cán bộ | 🚧 **Backend + frontend xong** (mục 2B), **chưa commit**. 103 unit test qua; đã gọi thử API thật với tài khoản QLNS. **Còn**: test tay ca `quan_ly` gốc/thường và ca phụ xe (bước 6), xem giao diện trên trình duyệt, tài liệu + commit + PR (bước 8–9) |
| UC-51, UC-52 | 📐 Đã làm rõ nghiệp vụ trong tài liệu, chưa code |
| Nhánh hiện tại | `feature/Nghia-uc37-khoa-mo-khoa-tai-khoan` (từ `cd77d29`, integration #42) |

### Quy tắc làm việc đã thống nhất
1. Không sửa code đã có của người khác; được **thêm** hàm/dòng mới, ưu tiên không đổi tên biến, rồi không đổi tên hàm.
2. Điểm nối bắt buộc duy nhất là `main.py` (đăng ký router/job) — chỉ thêm dòng.
3. Tài liệu chính chỉ sửa khi được yêu cầu rõ; phần đề xuất viết nháp riêng.

---

## 2. Code UC-49 (đã merge, commit `d49d505` → #36)

Tổng cộng 19 file, +2110/−210 dòng (phần xóa chủ yếu là viết lại tài liệu nháp).

### 2.1. Backend — file **thêm mới**

| File | Chức năng |
|---|---|
| `backend/app/routes/nhan_su.py` | Router `/quan-ly-nhan-su/...`, chỉ cho `quan_ly_nhan_su` và `quan_ly`. Các route: `GET /ho-so` (danh sách, lọc `chi_dang_lam`), `GET /tai-khoan-phu-xe-chua-gan` (ô chọn tài khoản phụ xe), `GET /ho-so/{id}` (chi tiết), `POST /ho-so` (tạo), `PUT /ho-so/{id}` (sửa), `POST /ho-so/{id}/anh` (upload ảnh hồ sơ), `POST /ho-so/{id}/giay-to/{loai}/anh` (upload ảnh giấy tờ) |
| `backend/app/services/ho_so_nhan_su_service.py` | Toàn bộ nghiệp vụ UC-49. `danh_sach_ho_so`, `xem_chi_tiet` (gắn URL ảnh có chữ ký), `tao_ho_so`, `sua_ho_so`, `cap_nhat_anh_ho_so`, `cap_nhat_anh_giay_to`, `danh_sach_tai_khoan_phu_xe_chua_gan`; hàm nội bộ `_kiem_tra_tai_khoan_phu_xe` (phụ xe bắt buộc có tài khoản `phu_xe` chưa gắn hồ sơ khác; tài xế không có tài khoản), `_luu_giay_to`, `_ghi_nhat_ky`, `_gan_url_anh`, `_gan_url_giay_to` |
| `backend/app/schemas/nhan_su_schema.py` | Pydantic request/response: tạo/sửa hồ sơ, giấy tờ, ảnh, tóm tắt, chi tiết, tài khoản phụ xe |
| `backend/app/repositories/giay_to_nhan_su_repository.py` | SQL bảng `giay_to_nhan_su`: `tim_theo_id`, `tim_theo_nhan_su_va_loai`, `danh_sach_theo_nhan_su`, `tao`, `cap_nhat`, `cap_nhat_anh`; phục vụ job cảnh báo: `can_canh_bao_sap_het_han`, `can_canh_bao_da_het_han`, `danh_dau_da_canh_bao_sap_het_han`, `danh_dau_da_canh_bao_het_han` |
| `backend/app/repositories/nhat_ky_quan_ly_nhan_su_repository.py` | Chỉ có `ghi(...)`: ghi một dòng vào `nhat_ky_quan_ly_nhan_su` (chỉ khi actor là `quan_ly_nhan_su`) |
| `backend/app/jobs/canh_bao_giay_to.py` | Job định kỳ nhắc giấy tờ sắp/đã hết hạn: `_nguoi_nhan` (tìm người nhận thông báo), `chay(nguong_ngay)` trả về số cảnh báo sắp hết hạn và đã hết hạn. Giấy tờ hết hạn **không chặn** biên chế/gán xe, chỉ nhắc |

### 2.2. Backend — file có sẵn, **chỉ thêm**, không đổi dòng cũ

| File | Thêm gì |
|---|---|
| `backend/app/repositories/nhan_su_van_hanh_repository.py` | 6 hàm cuối file: `tim_ho_so_day_du`, `danh_sach_ho_so`, `tao_ho_so`, `cap_nhat_ho_so`, `cap_nhat_anh_ho_so`, `danh_sach_tai_khoan_phu_xe_chua_gan`. Hàm cũ (`tim_theo_id`...) giữ nguyên |
| `backend/app/config.py` | Hằng số `NGUONG_CANH_BAO_GIAY_TO_NGAY = 30` |
| `backend/app/main.py` | Đăng ký router `nhan_su` và job `canh_bao_giay_to` vào scheduler (có đổi dòng import, xem mục 5) |

### 2.3. Đã có sẵn từ trước, tôi **dùng chứ không viết lại**
`services/luu_tru_anh_service.py` (`tai_anh_len`, `lay_url_xem`, `xoa_anh` — upload Cloudinary, lưu `public_id`, phát URL có chữ ký), 3 migration bảng `nhan_su_van_hanh`, `giay_to_nhan_su`, `nhat_ky_quan_ly_nhan_su`, cấu hình `CLOUDINARY_URL`. Nhóm đã hoàn thiện phần này trong đợt merge khớp thiết kế đã bàn.

### 2.4. Frontend — thư mục **mới** `frontend/nhan-vien/quan-li-nhan-su/`

| File | Chức năng |
|---|---|
| `api-client.js`, `auth-check.js` | Gọi API và kiểm tra đăng nhập/vai trò — bản riêng của domain, không import chéo |
| `nav.js` | Menu điều hướng (mảng link, thêm UC mới thì thêm entry cuối mảng) |
| `trang-chu.html` | Tổng quan: số nhân sự đang làm / tài xế / phụ xe / đã nghỉ |
| `ho-so.html` | Trang chính UC-49: danh sách, tìm kiếm, lọc chức danh/trạng thái, modal thêm/sửa hồ sơ kèm giấy tờ, ô chọn tài khoản phụ xe, upload ảnh hồ sơ và ảnh giấy tờ, nhãn còn hạn / sắp hết hạn / đã hết hạn |

Dùng chung (tham chiếu, không copy) `/nhan-vien/quan-ly/style.css` và `data-table.js`.

---

## 2A. Code UC-36 — Tạo tài khoản cán bộ (làm 23/10, **đã merge #38**)

Cách hoạt động: `quan_ly_nhan_su` và `quan_ly` dùng chung một chức năng. Tạo tài khoản đã xác nhận (`da_xac_nhan = true`) với **mật khẩu ban đầu mặc định `12345678`** (chỉ lưu bản băm bcrypt), **không gửi email/OTP** (email do công ty cấp). Quầy vé và gửi hàng bắt buộc chọn văn phòng; tạo tài khoản và gán văn phòng nằm trong **một transaction**.

### 2A.1. Backend — toàn bộ file **thêm mới**

| File | Chức năng |
|---|---|
| `backend/app/schemas/tai_khoan_can_bo_schema.py` | `TaoTaiKhoanCanBoRequest` (email, họ tên, SĐT, vai trò, văn phòng; validator: quầy vé/gửi hàng bắt buộc có văn phòng, vai trò khác không được có, họ tên không toàn khoảng trắng), `TaoTaiKhoanCanBoResponse` (kèm `mat_khau_ban_dau`), `TaiKhoanCanBoResponse` (một dòng danh sách), `VanPhongResponse`, `VaiTroDuocTaoResponse`; hằng `VAI_TRO_CAN_VAN_PHONG` |
| `backend/app/repositories/tai_khoan_can_bo_repository.py` | `tao_tai_khoan` (INSERT `nguoi_dung` + INSERT `ho_so_can_bo_diem` cùng một kết nối, một commit; rollback khi lỗi; trùng email do `UNIQUE` thì đổi thành "Email đã tồn tại"), `la_tai_khoan_goc`, `danh_sach_tai_khoan_can_bo` (lọc vai trò, tìm email/họ tên/SĐT, JOIN văn phòng), `danh_sach_van_phong` |
| `backend/app/services/tai_khoan_can_bo_service.py` | `tao_tai_khoan` (thứ tự: quyền, chuẩn hóa SĐT, email trùng, văn phòng hợp lệ, rồi mới ghi; email chuẩn hóa chữ thường), `vai_tro_duoc_tao`, `danh_sach_tai_khoan`, `danh_sach_van_phong`; nội bộ: `_kiem_tra_quyen_tao`, `_kiem_tra_van_phong`, `_ghi_nhat_ky` (chỉ khi actor là `quan_ly_nhan_su`, không ghi mật khẩu). Bảng phân quyền `_QUYEN_TAO`/`_QUYEN_XEM`, hằng `MAT_KHAU_MAC_DINH` |
| `backend/app/routes/tai_khoan_can_bo.py` | Router `/quan-ly-nhan-su/tai-khoan` (chỉ `quan_ly_nhan_su`, `quan_ly`): `GET ""` (danh sách), `GET /van-phong`, `GET /vai-tro-duoc-tao`, `POST ""` (tạo, trả 201) |
| `backend/tests/unit/test_tai_khoan_can_bo_service.py` | 43 test (giả lập repository bằng `monkeypatch`): ma trận quyền (3 người thao tác x nhóm vai trò), quản lý gốc/không gốc, email trùng/chuẩn hóa, SĐT sai, văn phòng (thiếu, không phải văn phòng, vai trò không cần), mật khẩu mặc định chỉ lưu bản băm, nhật ký, validator schema, danh sách |

Ma trận quyền: QLNS tạo phụ xe/quầy vé/gửi hàng/điều độ viên; `quan_ly` thêm `ke_toan`; chỉ `quan_ly` **gốc** tạo `quan_ly` và `quan_ly_nhan_su`.

### 2A.2. Backend — file có sẵn, chỉ **thêm**

| File | Thêm gì |
|---|---|
| `backend/app/main.py` | 2 dòng: `import` và `include_router` của router mới |

Không đụng chuỗi hàm `gan_van_phong_can_bo` của phần gửi hàng.

### 2A.3. Frontend — thư mục `frontend/nhan-vien/quan-li-nhan-su/`

| File | Chức năng |
|---|---|
| `tai-khoan.html` (**mới**) | Danh sách tài khoản cán bộ (tìm không phân biệt dấu, lọc theo vai trò kèm số lượng); nút "+ Tạo tài khoản" mở form (email, họ tên, SĐT, vai trò, văn phòng): ô vai trò chỉ liệt kê vai trò người đăng nhập được tạo, ô văn phòng chỉ hiện với quầy vé/gửi hàng; kiểm tra email, họ tên, SĐT (dùng `/shared/so-dien-thoai.js`), văn phòng trước khi gửi; tạo xong hiện hộp thoại email + mật khẩu ban đầu và nút sao chép |
| `nav.js` (file của mình) | Thêm mục menu "Tài khoản cán bộ"; sửa ghi chú cũ "đã có sẵn ở routes/quan_ly.py? kiểm tra lại" thành đúng thực tế |

### 2A.4. Kết quả kiểm tra

- Unit test UC-36: **43/43 qua**. Cả bộ `tests/unit`: 738 qua, 2 lỗi ở `test_thong_bao_khach.py` (job no-show, không dính UC-36; chưa kiểm tra có từ trước không).
- Chạy thật trên API (đã dọn dữ liệu test): tạo quầy vé kèm văn phòng có đủ dòng ở `nguoi_dung` và `ho_so_can_bo_diem`; đăng nhập được ngay bằng mật khẩu mặc định (200), sai mật khẩu 401; email trùng 400; QLNS tạo kế toán 403; điểm không phải văn phòng 400; SĐT sai 400; thiếu văn phòng 422; nhật ký ghi đủ.
- Frontend: cú pháp JS đúng, mọi id script dùng đều có trong HTML. **Chưa xem trên trình duyệt** (Live Server tắt, máy không có Node). DB local chưa có văn phòng nào nên phải tạo một văn phòng trước khi thử quầy vé/gửi hàng.
- Chưa test tay ca `quan_ly` gốc/không gốc (không có mật khẩu admin); mới được unit test phủ.

### 2A.5. Rủi ro đã biết

- Mật khẩu mặc định chung: ai biết email công ty đều đăng nhập được cho đến khi cán bộ đổi → nhắc đổi ngay. Cờ "bắt buộc đổi mật khẩu lần đầu" cần thêm cột vào bảng `nguoi_dung` dùng chung, để làm sau.

---

## 2B. Code UC-37 — Khóa / mở khóa tài khoản cán bộ (làm 23/10, **chưa commit**)

Cách hoạt động: `quan_ly_nhan_su` và `quan_ly` dùng chung hai API. Khóa chỉ đổi cờ `dang_hoat_dong`, không xóa gì; người bị khóa không đăng nhập được, kể cả phiên đang mở. **Lý do bắt buộc** (1–500 ký tự, gõ tự do) cho cả khóa lẫn mở khóa. Chỉ áp dụng cho **cán bộ**: khách hàng không ai khóa/mở được (hệ thống tự khóa theo mục 9 `NGHIEP_VU.md`).

**Quy tắc bậc** (chỉ khóa/mở khóa người ở bậc thấp hơn mình):

| Người thao tác | Khóa / mở khóa được |
|---|---|
| `quan_ly` gốc | `quan_ly`, `ke_toan`, `quan_ly_nhan_su` và 4 vai trò vận hành |
| `quan_ly` thường | `quan_ly_nhan_su` và 4 vai trò vận hành |
| `quan_ly_nhan_su` | 4 vai trò vận hành (phụ xe, quầy vé, gửi hàng, điều độ viên) |

Luật chặn thêm: không ai khóa được tài khoản gốc; không tự khóa chính mình; khóa tài khoản đã khóa / mở tài khoản đang hoạt động trả 400. Chặt hơn spec cũ ("`quan_ly` bất kỳ khóa được mọi cán bộ").

### 2B.1. Backend — file **thêm mới**

| File | Chức năng |
|---|---|
| `backend/migrations/20261023_1000_tao_bang_nhat_ky_admin.sql` | Tạo bảng `nhat_ky_admin` đúng `DATABASE.md` mục 6.2 (trước đó chỉ mô tả, chưa có migration) + 2 index `(admin_id, thoi_gian DESC)` và `(doi_tuong_loai, doi_tuong_id, thoi_gian DESC)`. `hanh_dong` / `doi_tuong_loai` để TEXT tự do vì bảng dùng chung cho nhiều thao tác của `quan_ly` |
| `backend/app/repositories/nhat_ky_admin_repository.py` | Chỉ có `ghi(admin_id, hanh_dong, doi_tuong_loai, doi_tuong_id, ghi_chu)` (chỉ `INSERT`, không có sửa/xóa). Cùng kiểu `nhat_ky_quan_ly_nhan_su_repository` |
| `backend/tests/unit/test_tai_khoan_can_bo_schema.py` | 11 test cho `DoiTrangThaiTaiKhoanRequest` (lý do rỗng / toàn khoảng trắng / quá 500 ký tự / cắt khoảng trắng hai đầu) |

### 2B.2. Backend — file của phần UC-36 (mình viết), **thêm vào cuối**

| File | Thêm gì |
|---|---|
| `backend/app/schemas/tai_khoan_can_bo_schema.py` | `DoiTrangThaiTaiKhoanRequest` (`ly_do`), `XeThieuPhuXe`, `DoiTrangThaiTaiKhoanResponse` (`id`, `dang_hoat_dong`, `canh_bao_xe_thieu_phu_xe`) |
| `backend/app/repositories/tai_khoan_can_bo_repository.py` | `tim_tai_khoan` (thông tin tối thiểu để kiểm quyền), `dat_trang_thai_hoat_dong` (khóa/mở khóa), `xe_thieu_phu_xe` (xe mà phụ xe này thuộc biên chế **cố định** và khi bỏ người này không còn phụ xe cố định nào đang hoạt động; hồ sơ phải `dang_lam`, tài khoản `dang_hoat_dong`). Kiểm tra 17/17 trên DB thật |
| `backend/app/services/tai_khoan_can_bo_service.py` | Bảng quyền `_QUYEN_KHOA` theo bậc; `_tim_muc_tieu` (thứ tự chặn: 404, khách hàng 400, tài khoản gốc 403, tự khóa 403, vượt bậc 403); `khoa_tai_khoan`, `mo_khoa_tai_khoan`; `_bao_xe_thieu_phu_xe` (thông báo cho `quan_ly` + `dieu_do_vien` đang hoạt động, **không gửi QLNS**, bỏ người vừa khóa, chỉ nhắc, không tự đổi biên chế). Sửa `_ghi_nhat_ky` thêm tham số `hanh_dong`: QLNS ghi `nhat_ky_quan_ly_nhan_su`, `quan_ly` ghi `nhat_ky_admin`, không ghi chéo; `tao_tai_khoan` của `quan_ly` vẫn không ghi nhật ký như UC-36 |
| `backend/app/routes/tai_khoan_can_bo.py` | `POST /quan-ly-nhan-su/tai-khoan/{muc_tieu_id}/khoa` và `/mo-khoa`, body `{ "ly_do": "..." }`. Không cần sửa `main.py` (router đã đăng ký) |
| `backend/tests/unit/test_tai_khoan_can_bo_service.py` | Thêm 46 test: ma trận quyền theo bậc, luật chặn, mở khóa, nhật ký đúng bảng, cảnh báo / thông báo thiếu phụ xe |

### 2B.3. Frontend — `frontend/nhan-vien/quan-li-nhan-su/tai-khoan.html` (thêm vào trang UC-36) và `nav.js` (sửa ghi chú)

- Mỗi hàng có nút **Khóa** (đang hoạt động) hoặc **Mở khóa** (đã khóa), qua `extraActions` của `renderDataTable`. Nút hiện ở mọi hàng vì bảng dùng chung không cho ẩn nút theo hàng; quyền thật do backend quyết định, lỗi 403/400/404 hiện ngay trong hộp thoại.
- Hộp thoại xác nhận: nêu hậu quả, ô lý do nhiều dòng (tối đa 500 ký tự, có đếm), kiểm tra rỗng ngay ("Vui lòng nhập lý do.") trước khi gọi API.
- Sau khi khóa phụ xe mà có `canh_bao_xe_thieu_phu_xe`: hộp thoại chuyển sang cảnh báo, liệt kê biển số, nhắc biên chế không tự đổi, nút "Đã hiểu".
- Không sửa `data-table.js` hay `style.css` dùng chung; không thêm mục menu.

### 2B.4. Kết quả kiểm tra

- **Unit test**: 103/103 qua (UC-36 + 46 test service UC-37 + 11 test schema). Cả bộ unit còn 7 test lỗi có sẵn của phần vé lẻ (`test_ve_le.py`, `test_thong_bao_khach.py`), không do UC-37.
- **Chạy thật trên API** (tài khoản QLNS, đã dọn dữ liệu): khóa 200; khóa lại 400; đăng nhập tài khoản đã khóa 401; mở khóa với lý do toàn khoảng trắng 422; mở khóa 200; id lạ 404; nhật ký `nhat_ky_quan_ly_nhan_su` có đủ `tao_tai_khoan`, `khoa_tai_khoan`, `mo_khoa_tai_khoan` kèm lý do. Migration `nhat_ky_admin` đã áp dụng, ghi và đọc thử bảng được.
- **Frontend**: cú pháp JS đúng, mọi id script dùng đều có trong HTML. **Chưa xem trên trình duyệt.**
- **Chưa test tay**: ca `quan_ly` gốc / thường (cần đặt mật khẩu tạm cho `admin@nhaxekhach.com`), ca phụ xe thiếu xe (cần chèn xe + biên chế bằng SQL), khóa tài khoản gốc, token cũ bị chặn ngay sau khi khóa. Các ca này hiện chỉ có unit test phủ.

### 2B.5. Rủi ro đã biết

- Code `quan_ly` khóa sẽ **lỗi 500 nếu chưa chạy migration** `nhat_ky_admin`: sau khi pull, cả nhóm phải chạy `yoyo apply ./migrations`.
- `ghi` của hai bảng nhật ký tự mở kết nối và commit riêng, nên nhật ký **không nằm cùng transaction** với việc đổi cờ khóa (khác với UC-36 tạo tài khoản + văn phòng). Nếu muốn atomic thì phải đổi cả hai hàm `ghi` sang nhận cursor.
- Cảnh báo "khóa điều độ viên làm tuyến hết người phụ trách" chưa làm: chờ nhóm điều độ viên có bảng `dieu_do_vien_tuyen`.

---

## 3. File của người khác mà tôi **có sửa**

| File | Sửa gì | Lý do / mức độ |
|---|---|---|
| `frontend/nhan-vien/dang-nhap.html` | Đổi **1 giá trị** đường dẫn để `quan_ly_nhan_su` đăng nhập xong vào thẳng `quan-li-nhan-su/` | Nới quy tắc "được đổi giá trị cần thiết"; trước đó đã từng lỡ sửa rồi revert |
| `backend/app/main.py` | UC-49: thêm đăng ký router + job. UC-36: thêm 2 dòng (import + `include_router`) | Điểm nối bắt buộc. Ở UC-49 có đổi dòng import (diff `6 +-`) — nên kiểm tra lại khi báo nhóm |
| `backend/app/config.py` | Thêm 3 dòng hằng số | Chỉ thêm |
| `backend/app/repositories/nhan_su_van_hanh_repository.py` | Thêm 6 hàm cuối file (+129 dòng) | Chỉ thêm |

UC-37 **không sửa file code nào của người khác** (chỉ thêm vào file của phần UC-36 do mình viết và thêm file mới). Ngoài các file trên không có file code nào của người khác bị đụng.

---

## 4. Tài liệu đã sửa / thêm

| File | Việc | Đã commit? |
|---|---|---|
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md` | Thêm UC-49/51/52 (mục 2, 3.2, 8.9, 11, 12; sơ đồ 1.6, 1.8). Làm rõ UC-36 (họ tên + SĐT bắt buộc; bản đầu ghi mời bằng OTP, **nay đã bỏ**, xem dòng dưới), UC-37 (không tự khóa mình), UC-51 (ngày nghỉ, lý do, "thiếu người"), UC-52 (phân trang) | ✅ (#36) |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md` | **Điều độ viên không gắn văn phòng** (mục 2, 8.7 điểm 2, UC-36 bước 1, sơ đồ UC-36) | ❌ chưa |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md` | **UC-36 bỏ OTP, dùng mật khẩu ban đầu mặc định `12345678`** (nguyên tắc ở mục 2, UC-36 bước 3–4, bỏ nhánh "gửi email thất bại", sơ đồ UC-36, 2 cột `mat_khau`/`da_xac_nhan` ở `DATABASE.md`) | ❌ chưa |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md`, `ARCHITECTURE.md`, `NHAP_QUAN_LY_NHAN_SU.md`, `TOM_TAT_QUAN_LY_NHAN_SU.md`, file này | **Đồng bộ theo quyết định UC-37** (23/10): khách hàng không ai khóa, quy tắc bậc, lý do bắt buộc, `nhat_ky_admin` cho `quan_ly`, thông báo thiếu phụ xe; `DATABASE.md` 6.2 ghi migration `20261023_1000`; mục 2B của file này và `TOM_TAT` đánh dấu bước 2b/6b xong | ❌ chưa |
| `KE_HOACH_UC37_KHOA_MO_KHOA_TAI_KHOAN.md` | **Mới.** Kế hoạch UC-37 9 bước; hiện đã tích bước 1–5, 6b, 7 (còn xem trình duyệt), còn bước 6 (test tay) và 8–9 | ❌ chưa |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md` | **Thêm nhánh kèm theo UC-36 "Đổi văn phòng của cán bộ"**: bảng vai trò (đổi "gắn cố định" thành "gắn 1 văn phòng tại mỗi thời điểm, đổi được"), mục 8.7 điểm 2, nhánh mới sau UC-36 (luồng chính, rẽ nhánh, hậu điều kiện), sơ đồ PlantUML, `DATABASE.md` mục 1.3 | ❌ chưa |
| `NHAP_QUAN_LY_NHAN_SU.md` | Tài liệu tổng hợp đọc nhanh cho phần Quản lý nhân sự (mục 11.1 thiết kế UC-36/37/51/52, mục 12 "đã cân nhắc, không làm") | Một phần (#36), phần mới ❌ |
| `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md` | **Mới.** Kế hoạch UC-36: ma trận quyền, API, thứ tự làm, kiểm thử, rủi ro. Cập nhật 22/10: thêm đổi văn phòng, xóa chuỗi hàm cũ làm sau cùng | ❌ chưa |
| `TOM_TAT_QUAN_LY_NHAN_SU.md` | Nhật ký phiên làm việc; thêm mục 8–14 và đoạn "Phát hiện khi rà soát lại (22/10)" | ❌ chưa |
| `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md` | **Mới** (trước tên `UC36_THAY_THE_GAN_VAN_PHONG_VA_DOI_VAN_PHONG.md`, đã đổi tên). Sổ ghi chú mọi việc của phần Quản lý nhân sự **ảnh hưởng đến người khác trong nhóm** (gửi hàng, điều độ viên, biên chế, vé lẻ, cả nhóm): bảng tổng hợp + trạng thái báo, chuỗi hàm `gan_van_phong_can_bo`, bỏ OTP, migration `nhat_ky_admin`, quy tắc bậc UC-37, thông báo khóa phụ xe, đổi văn phòng, bản tóm tắt gửi nhóm. Việc sau này ảnh hưởng người khác thì ghi thêm vào đây | ❌ chưa |
| `BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md` | **Mới.** File này | ❌ chưa |

> Các dòng "❌ chưa" của UC-36 ở trên (OTP, điều độ viên, đổi văn phòng, `KE_HOACH_UC36`, file tác động đến người khác) đã vào commit #38; từ bảng này chỉ các dòng UC-37 mới là chưa commit. Cần `git status` để xác nhận trước khi commit.

`DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` đã vào integration cùng #38 (nên báo nhóm điều độ viên).


---

## 5. Việc đã hoàn tác / không làm (để khỏi hiểu nhầm)

- Đề xuất "hồ sơ cán bộ văn phòng" (bảng riêng cho quầy vé/gửi hàng/điều độ viên): đã ghi vào 5 tài liệu ngày 15/10 rồi **hoàn tác toàn bộ** ngày 21/10; chưa từng có bảng hay migration. Lý do: hồ sơ nhân sự các vai trò khác thuộc phòng nhân sự, nên lưu ngoài hệ thống.
- Không đưa hợp đồng, BHXH, lương, thuế, KPI vào hệ thống. Bằng lái chỉ bắt buộc với tài xế.
- Đã bắt đầu viết code UC-36/37/51/52 một lần rồi **hoàn tác theo yêu cầu**, chỉ giữ phần tài liệu.

---

## 6. Rà soát và phân tích gần đây (21–23/10)

### 6.1. UC-36 đã có ai làm chưa?
Chưa. Không có code tạo/khóa tài khoản cán bộ ở bất kỳ nhánh nào (`INSERT INTO nguoi_dung` duy nhất trong app cố định vai trò `khach_hang`). Nhánh `vanh-uc36-38-tai-khoan-can-bo` chỉ là bản cũ của integration. Sai sót đã đính chính: lúc đầu tôi đọc nhầm tên nhánh đó là "đã làm xong".

### 6.2. Chuỗi hàm `gan_van_phong_can_bo` (của phần gửi hàng)
| Tầng | Vị trí | Việc |
|---|---|---|
| Route | `routes/quan_ly.py:62` `PUT /quan-ly/ho-so-can-bo-diem/{id}` | Chỉ `quan_ly` gọi được |
| Schema | `schemas/don_hang_schema.py:190` `GanVanPhongCanBoRequest` | Body của route trên |
| Service | `services/gui_hang_service.py:86` `gan_van_phong_can_bo` | Kiểm tra vai trò (quầy vé, gửi hàng, điều độ viên) và điểm là `van_phong` |
| Repository | `repositories/nguoi_dung_repository.py:55` `gan_van_phong` | `INSERT ... ON CONFLICT DO UPDATE` vào `ho_so_can_bo_diem`, tự `commit()` |

- **Tác dụng**: ghi "cán bộ làm ở văn phòng nào". Phần gửi hàng dựa vào đó để giới hạn phạm vi (`_pham_vi_van_phong`, chưa có văn phòng thì 403) và để tìm người nhận thông báo.
- **Người viết**: phần gửi hàng, commit `2f80b79` (#26). `KE_HOACH_SUA_GUI_HANG.md` mục P1 kỳ vọng UC-36 gọi hàm này.
- **Chỉ có một đường gọi**; không frontend, không test. Bảng `ho_so_can_bo_diem` được nhiều nơi khác đọc (middleware, gửi hàng, thông báo, điều độ viên) → **không xóa bảng**.
- **Quyết định**: làm UC-36 + đổi văn phòng bằng code riêng trước, **xóa chuỗi hàm cũ sau cùng** và chỉ khi nhóm đồng ý (ưu tiên họ tự xóa). Hàm mới nhận cursor để nằm cùng transaction tạo tài khoản.

### 6.3. Bẫy kỹ thuật phát hiện được
`dang_nhap` chặn mọi tài khoản có `da_xac_nhan = false` (và `dat_lai_mat_khau` qua OTP cũng không bật cờ này). Vì vậy tài khoản cán bộ phải tạo với `da_xac_nhan = true`; UC-36 hiện tạo kèm mật khẩu mặc định nên đăng nhập được ngay. Hàm `repo.tao_tai_khoan` đã đặt đúng như vậy.

### 6.4. Tái dùng được cho UC-36
`chuan_hoa_so_dien_thoai`, `nguoi_dung_repo.tim_theo_email`, `dia_diem_repo.tim_diem_don_tra_theo_id`, `nhat_ky_quan_ly_nhan_su_repository.ghi`, `yeu_cau_vai_tro`, `/shared/so-dien-thoai.js` (frontend), các lỗi `GiaTriLoi`/`CamTruyCap`. Ban đầu dự định dùng thêm `quen_mat_khau`/`gui_mail` (OTP), nay bỏ. Không cần migration.

---

## 7. Quyết định UC-36 đã chốt

1. Người làm: Nghĩa, nhánh `feature/Nghia-uc36-tao-tai-khoan-can-bo`.
2. Ma trận tạo tài khoản đúng `NGHIEP_VU.md`: QLNS tạo phụ xe/quầy vé/gửi hàng/điều độ viên; `quan_ly` thêm `ke_toan`; chỉ `quan_ly` gốc tạo `quan_ly` và `quan_ly_nhan_su`.
3. QLNS và `quan_ly` **dùng chung một endpoint**; service quyết định theo vai trò.
4. Điều độ viên không gắn văn phòng; văn phòng bắt buộc chỉ với quầy vé và gửi hàng (hằng số duy nhất trong service).
5. Tạo tài khoản và gán văn phòng **trong cùng một transaction**.
5b. **Bỏ cơ chế mời bằng OTP** (23/10): email do công ty cấp nên không cần xác minh; tạo kèm mật khẩu ban đầu mặc định `12345678` (hằng số `MAT_KHAU_MAC_DINH`), không gửi email; cán bộ đổi mật khẩu sau khi đăng nhập. Là thay đổi so với spec cũ, cần báo nhóm.
6. **Đổi văn phòng thuộc UC-36** (nhánh kèm theo): chỉ quầy vé/gửi hàng; điểm phải là văn phòng và khác văn phòng hiện tại; chưa có dòng thì coi là gán lần đầu; ghi nhật ký khi actor là QLNS; **không** chặn khi còn đơn đang xử lý, **không** bắt buộc lý do (hai điểm này là tôi chọn, cần nhóm xác nhận).

---

## 7A. Quyết định UC-37 đã chốt (23/10)

| # | Chốt |
|---|---|
| 1 | **Khách hàng**: không ai khóa, mở khóa hay gỡ hạn chế; UC-37 chỉ cho cán bộ |
| 2 | **Quy tắc bậc**: gốc > (`quan_ly` thường = `ke_toan`) > QLNS > 4 vai trò vận hành; chỉ khóa / mở khóa bậc thấp hơn; không ai khóa gốc; không tự khóa |
| 3 | **Lý do**: bắt buộc, gõ tự do, 1–500 ký tự, cả khóa lẫn mở khóa |
| 4 | **Nhật ký**: `quan_ly` ghi `nhat_ky_admin` (migration tạo cùng đợt), QLNS ghi `nhat_ky_quan_ly_nhan_su`, không ghi chéo |
| 5 | **Khóa phụ xe làm xe thiếu phụ xe cố định**: báo `quan_ly` + `dieu_do_vien` đang hoạt động (không báo QLNS, bỏ người vừa khóa); chỉ cảnh báo, không tự đổi biên chế |
| 6 | **Khóa điều độ viên làm tuyến hết người**: làm sau, khi có bảng `dieu_do_vien_tuyen` |

Chi tiết và 9 bước ở `KE_HOACH_UC37_KHOA_MO_KHOA_TAI_KHOAN.md`.

---

## 8. Việc còn lại

1. **Báo Trưởng nhóm** (`CONTRIBUTING.md` đang giao UC-36/37 cho Người 1) và **người làm gửi hàng** (về hàm `gan_van_phong_can_bo`); báo cả nhóm điều độ viên.
2. **Hoàn tất UC-37**: (a) test tay bước 6 (ca `quan_ly` gốc / thường, ca phụ xe, token cũ sau khi khóa) rồi dọn dữ liệu và khôi phục mật khẩu admin; (b) xem `tai-khoan.html` trên trình duyệt; (c) bước 8–9: cập nhật tài liệu, commit, PR.
3. Docker đang chạy; code backend được mount nên đã có hiệu lực. Không dùng `docker-compose down -v` (mất tài khoản test `quanlynhansu@gmail.com`).
4. **Xem thử `tai-khoan.html` trên trình duyệt** (Live Server cổng 5500, đăng nhập `quanlynhansu@gmail.com`); tạo một văn phòng ở trang Điểm đón/trả trước khi thử quầy vé/gửi hàng. Báo lỗi hiển thị nếu có.
5. (Gộp vào việc 2a) Ca `quan_ly` gốc/không gốc cần đặt mật khẩu tạm cho `admin@nhaxekhach.com`; nhớ khôi phục hash cũ.
6. **Đổi văn phòng** (cùng repository/route UC-36): làm sau khi nhóm chốt 2 quy tắc ở `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md`; sửa lại nhánh trong `NGHIEP_VU.md` nếu quy tắc đổi.
7. UC-51 (nghỉ việc), UC-52 (xem nhật ký; `quan_ly` xem cả hai bảng nhật ký, nay `nhat_ky_admin` đã có).
8. **Sau cùng**: xóa chuỗi hàm `gan_van_phong_can_bo` (4 file) khi nhóm đồng ý và đổi văn phòng đã chạy được.
9. Còn nợ: test tự động cho `ho_so_nhan_su_service.py`; test frontend UC-49 và UC-36 trên trình duyệt thật; 7 test lỗi có sẵn của phần vé lẻ (đã xác minh bằng `git stash` là không do mình, cần báo người làm); cờ bắt buộc đổi mật khẩu lần đầu (cần cột mới).
10. **Báo nhóm sau khi merge UC-37**: chạy lại `yoyo apply ./migrations` (bảng `nhat_ky_admin` mới); quy tắc bậc mới chặt hơn spec cũ.

### Câu hỏi còn mở cho nhóm
- ~~`nhat_ky_admin` chưa có migration~~ — **đã xong 23/10**: migration `20261023_1000_tao_bang_nhat_ky_admin.sql` đã tạo và áp dụng ở DB local.
- ~~Khóa khách hàng (UC-37)~~ — đã chốt 23/10: không ai khóa/mở khách hàng, hệ thống tự khóa.
- Tên vai trò phụ xe: tài liệu `nhan_vien_van_hanh`, DB và code `phu_xe`.
- ~~Mã OTP 1 phút có hợp lý cho thư mời cán bộ không?~~ Không còn đặt ra: UC-36 đã bỏ OTP, dùng mật khẩu mặc định. Nhưng đây là thay đổi so với spec cũ nên **cần báo nhóm**.
- Đổi văn phòng: còn đơn đang xử lý thì có chặn không? Lý do đổi có bắt buộc không? (đang ghi: không chặn, không bắt buộc)
- Nhóm gửi hàng có đồng ý xóa chuỗi `gan_van_phong_can_bo` (ưu tiên để họ tự xóa)?
- Còn chỗ tài liệu nhắc điều độ viên gắn văn phòng (`NGHIEP_VU.md` mục 2 "Nguyên tắc xuyên suốt", phần UC-44) — thuộc nhóm điều độ viên.

---

## 9. Lệnh hay dùng

```powershell
docker-compose up -d --build
docker-compose exec backend yoyo apply ./migrations
docker-compose logs -f backend

# Test API có xác thực (né lỗi Swagger với header tùy chọn)
$login = Invoke-RestMethod -Uri "http://localhost:8000/auth/dang-nhap" -Method Post -ContentType "application/json" -Body '{"email":"quanlynhansu@gmail.com","mat_khau":"Nhansu@123"}'
Invoke-RestMethod -Uri "http://localhost:8000/quan-ly-nhan-su/ho-so" -Headers @{ Authorization = "Bearer $($login.token)" }
```
