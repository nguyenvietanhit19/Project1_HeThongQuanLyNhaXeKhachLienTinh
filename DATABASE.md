# Thiết kế cơ sở dữ liệu — Hệ thống Quản lý Nhà xe Khách

Tài liệu này mô tả đầy đủ cấu trúc bảng của cơ sở dữ liệu (PostgreSQL), bám sát đúng nghiệp vụ đã chốt trong `NGHIEP_VU.md`. Đọc cùng `NGHIEP_VU.md` để hiểu vì sao mỗi bảng/cột tồn tại — file này chỉ tập trung vào **cấu trúc dữ liệu**.

---

## 0. Quy ước chung

- **Khóa chính**: dùng `UUID` (sinh bằng `gen_random_uuid()`) thay vì số tự tăng — tránh lộ tổng số bản ghi (VD tổng số vé đã bán) và tránh đoán ID liên tiếp để dò dữ liệu.
- **Thời gian**: dùng `TIMESTAMPTZ` (có timezone), không dùng `TIMESTAMP` thường.
- **Enum trạng thái**: triển khai bằng `TEXT` kèm ràng buộc `CHECK`, không dùng kiểu `ENUM` gốc của Postgres — vì hệ thống migrate bằng file `.sql` thuần (không có ORM), thêm 1 giá trị enum mới vào kiểu `ENUM` gốc đòi hỏi `ALTER TYPE` chạy tách rời transaction, bất tiện khi viết migration; dùng `CHECK` thì chỉ cần `ALTER TABLE ... DROP/ADD CONSTRAINT` như mọi thay đổi khác.
- **Mật khẩu**: cột `mat_khau` luôn lưu giá trị đã băm (bcrypt, giữ nguyên thư viện từ bản v1), không bao giờ lưu plaintext.
- **Xóa dữ liệu**: hệ thống không xóa cứng (`DELETE`) tài khoản/vé/đơn hàng — khóa/vô hiệu hóa bằng cờ boolean hoặc chuyển trạng thái, giữ lại lịch sử (`NGHIEP_VU.md` mục 8.7 điểm 5: "không xóa vĩnh viễn, giữ lịch sử").
- **Class Table Inheritance cho `nguoi_dung`**: bảng `nguoi_dung` là bảng cha chung cho mọi vai trò **có tài khoản đăng nhập**; mỗi vai trò có bảng con riêng chứa cột chỉ áp dụng cho vai trò đó — tránh một bảng khổng lồ với hàng loạt cột `NULL` tùy vai trò. **Tài xế không có bảng con trong `nguoi_dung`** vì không có tài khoản (`NGHIEP_VU.md` mục 3.2/8.3) — xem mục 1.3.
- **Không có bảng gán nhân sự theo từng chuyến** (`phan_cong_chuyen`) — quyết định có chủ đích của `NGHIEP_VU.md` mục 3.2: tài xế/phụ xe của 1 chuyến luôn suy ra từ `xe_nhan_su` tại thời điểm truy vấn, không lưu tĩnh.
- **Không có ràng buộc `UNIQUE(chuyen_id, so_ghe)` trên bảng `ve`** — cố ý: 1 ghế hợp lệ có nhiều vé cùng lúc nếu chặng không giao nhau (`NGHIEP_VU.md` mục 6). Chống trùng ghế thực hiện bằng khóa dòng (`SELECT ... FOR UPDATE`) + kiểm tra overlap ở tầng Service, không phải constraint của DB.

---

## 1. Tài khoản & nhân sự

### 1.1. `nguoi_dung` (bảng cha — mọi vai trò **có** tài khoản)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `email` | TEXT NOT NULL UNIQUE | Định danh đăng nhập — kế thừa nguyên cơ chế từ bản v1 (`GiaoThongAnToan_API/routes/auth.py`), `NGHIEP_VU.md` mục 2.1 |
| `mat_khau` | TEXT NULLABLE | Hash bcrypt; **NULL** với cán bộ vừa được mời, chưa tự đặt mật khẩu lần đầu |
| `ho_ten` | TEXT NOT NULL | |
| `so_dien_thoai` | TEXT NOT NULL | Bắt buộc với mọi vai trò từ bản viết lại này (khác bản v1) — dùng để nhân viên quầy vé tra cứu (mục 8.4), liên hệ khi cần; **không dùng để đăng nhập/xác thực** (mục 2.1) |
| `vai_tro` | TEXT NOT NULL, CHECK IN (`khach_hang`, `phu_xe`, `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien`, `ke_toan`, `quan_ly_nhan_su`, `quan_ly`) | Quyết định bảng con nào áp dụng. `phu_xe` là 1 trong 2 `chuc_danh` của `nhan_vien_van_hanh` — chỉ `chuc_danh = phu_xe` có tài khoản (mục 3.2). `ke_toan` phụ trách hoàn tiền, phạm vi toàn hệ thống (mục 2 `NGHIEP_VU.md`). `quan_ly_nhan_su` chỉ quản lý tài khoản/nhân sự cấp vận hành (không `ke_toan`/`quan_ly`), cũng phạm vi toàn hệ thống (mục 8.9 `NGHIEP_VU.md`) |
| `dang_hoat_dong` | BOOLEAN NOT NULL DEFAULT true | `false` = tài khoản bị khóa (mục 8.7 điểm 5) |
| `la_tai_khoan_goc` | BOOLEAN NOT NULL DEFAULT false | Chỉ có ý nghĩa khi `vai_tro = 'quan_ly'` — đánh dấu tài khoản `quan_ly` gốc, seed lúc khởi tạo hệ thống (`NGHIEP_VU.md` mục 2). Tài khoản này **không thể bị khóa** (UC-37) và là `quan_ly` **duy nhất** tạo thêm được `quan_ly`/`quan_ly_nhan_su` khác (UC-36) — kiểm tra quyền ở Service. Ràng buộc "tối đa 1 dòng `true`" thực hiện bằng partial unique index: `CREATE UNIQUE INDEX ... ON nguoi_dung ((true)) WHERE la_tai_khoan_goc = true` |
| `da_xac_nhan` | BOOLEAN NOT NULL DEFAULT false | `true` sau khi `khach_hang` xác thực OTP, hoặc cán bộ đã tự đặt mật khẩu lần đầu qua liên kết mời |
| `ma_xac_nhan` | TEXT NULLABLE | Mã OTP 6 số — tên cột giữ nguyên như bản v1 để tái dùng thẳng `email_service.py`/`mat_khau_service.py` |
| `ma_het_han` | TIMESTAMPTZ NULLABLE | Hạn hiệu lực của `ma_xac_nhan` — mặc định 1 phút (mục 2.1) |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

### 1.2. `ho_so_khach_hang` (con — vai_tro = `khach_hang`)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `nguoi_dung_id` | UUID PK, FK → `nguoi_dung(id)` ON DELETE CASCADE | |
| `khoa_thanh_toan_tai_quay` | BOOLEAN NOT NULL DEFAULT false | Đủ N lần vi phạm no-show (mục 9) → tự động `true`, chỉ còn đặt được vé kiểu "thanh toán ngay" |
| `bi_khoa` | BOOLEAN NOT NULL DEFAULT false | Vi phạm nghiêm trọng hơn ngưỡng thứ 2 (mục 9) — khóa tạm, khác `nguoi_dung.dang_hoat_dong` (khóa hẳn do quản lý) |
| `ly_do_khoa` | TEXT NULLABLE | |

Số lần vi phạm no-show **không lưu thành cột đếm riêng** (mục 7) — tính động bằng đếm `ve` của khách có `trang_thai = 'khong_den'`, theo đúng định nghĩa 1 loại vi phạm duy nhất ở mục 9 `NGHIEP_VU.md`.

### 1.3. `ho_so_can_bo_diem` (con dùng chung — `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien`)

Cả 3 vai trò chỉ cần thêm đúng 1 thông tin giống nhau: văn phòng cố định phụ trách — gộp chung 1 bảng con, phân biệt qua `nguoi_dung.vai_tro`.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `nguoi_dung_id` | UUID PK, FK → `nguoi_dung(id)` ON DELETE CASCADE | |
| `van_phong_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | Bắt buộc `loai = 'van_phong'` (kiểm tra ở Service) — phạm vi thao tác của cán bộ này (mục 2) |

`phu_xe`, `ke_toan`, `quan_ly_nhan_su`, và `quan_ly` **không có bảng con** — phụ xe gắn với xe qua `xe_nhan_su` (mục 1.5), không gắn 1 văn phòng; `ke_toan`/`quan_ly_nhan_su`/`quan_ly` phạm vi toàn hệ thống, không cần cột phạm vi nào thêm.

### 1.4. `nhan_su_van_hanh` (hồ sơ tài xế + phụ xe — **không phải** bảng tài khoản)

Tách riêng khỏi `nguoi_dung` vì tài xế không có tài khoản (mục 3.2/8.3) nhưng vẫn cần lưu hồ sơ (họ tên, SĐT) để biên chế xe và liên hệ.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ho_ten` | TEXT NOT NULL | |
| `so_dien_thoai` | TEXT NOT NULL | |
| `chuc_danh` | TEXT NOT NULL, CHECK IN (`tai_xe`, `phu_xe`) | |
| `nguoi_dung_id` | UUID NULLABLE, FK → `nguoi_dung(id)` | **Chỉ có giá trị khi `chuc_danh = 'phu_xe'`** — tài xế luôn `NULL` (không có tài khoản) |

### 1.5. `xe_nhan_su` (biên chế — gắn `nhan_su_van_hanh` với `xe`)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `xe_id` | UUID NOT NULL, FK → `xe(id)` | |
| `nhan_su_van_hanh_id` | UUID NOT NULL, FK → `nhan_su_van_hanh(id)` | |
| `loai` | TEXT NOT NULL, CHECK IN (`co_dinh`, `tam_thoi`) | `co_dinh` do `quan_ly` quản lý; `tam_thoi` do `dieu_do_vien` thêm khi có người nghỉ (mục 3.2) |
| `trang_thai` | TEXT NOT NULL DEFAULT `'dang_hoat_dong'`, CHECK IN (`dang_hoat_dong`, `tam_nghi`) | `tam_nghi` khiến hệ thống **ngừng suy ra chuyến** cho phụ xe này (mục 3.2) — chỉ có ý nghĩa vận hành thật với `phu_xe`, với `tai_xe` chỉ mang tính ghi nhận hồ sơ |
| `ngay_bat_dau` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `ngay_ket_thuc` | TIMESTAMPTZ NULLABLE | Set khi gỡ dòng `tam_thoi`/chuyển `tam_nghi` về `dang_hoat_dong` |

**"Chuyến của phụ xe X" không lưu thành bảng riêng** — suy ra bằng truy vấn: `chuyen_xe` có `xe_id` khớp 1 dòng `xe_nhan_su(nhan_su_van_hanh_id = X, trang_thai = 'dang_hoat_dong')` tại **thời điểm truy vấn** (mục 3.2). Ràng buộc "mỗi xe đúng 2 tài xế + ≥1 phụ xe `co_dinh`" và "1 nhân sự chỉ thuộc 1 xe tại 1 thời điểm" kiểm tra ở tầng Service, không phải constraint DB (vì phụ thuộc điều kiện lọc theo `loai`/`trang_thai`, CHECK constraint đơn giản không diễn tả được).

---

## 2. Địa điểm & tuyến

### 2.1. `khu_vuc`

Tầng thô, dùng để tìm kiếm (`NGHIEP_VU.md` mục 3.1).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ten` | TEXT NOT NULL | VD `"Lào Cai (TP Lào Cai, Bến Đền, Xuân Giao, Phố Lu)"` |
| `tinh_thanh` | TEXT NOT NULL | Chỉ để hiển thị/lọc thô — cùng 1 tỉnh có thể có nhiều `khu_vuc` tách biệt (VD Sapa, Bắc Hà cùng tỉnh Lào Cai nhưng khác `khu_vuc`) |

### 2.2. `diem_don_tra`

Tầng chi tiết, nằm trong 1 `khu_vuc` — mọi điểm ở đây đều là địa chỉ **xe thật sự đi qua** (mục 3.1, không còn điểm hẹn trung chuyển).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `khu_vuc_id` | UUID NOT NULL, FK → `khu_vuc(id)` | |
| `ten` | TEXT NOT NULL | |
| `dia_chi` | TEXT NOT NULL | |
| `loai` | TEXT NOT NULL, CHECK IN (`van_phong`, `diem_dung`) | `van_phong`: có quầy vé/nhân viên, hợp lệ làm điểm đón lẫn điểm trả, trung bình 1 điểm/`khu_vuc`. `diem_dung`: điểm dừng dọc đường không có nhân viên, **chỉ hợp lệ làm điểm trả** (kiểm tra ở Service, mục 3.1) |

Không có bảng `ben_xe` riêng — `loai = 'van_phong'` chính là "văn phòng/bến xe" (mục 3.1, tránh trùng lặp dữ liệu).

### 2.3. `nhom_tuyen` và `tuyen`

| `nhom_tuyen` | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ten` | TEXT NOT NULL | VD `"Hà Nội – Sapa"` — gộp các `tuyen` chạy trên cùng 1 hành trình vật lý (2 chiều), dùng cho ràng buộc xe cố định theo tuyến (mục 3.2) |

| `tuyen` | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `nhom_tuyen_id` | UUID NOT NULL, FK → `nhom_tuyen(id)` | |
| `ten` | TEXT NOT NULL | VD `"Yên Nghĩa → Sapa"` — 1 chiều duy nhất (mục 3.1) |

### 2.4. `tuyen_diem_don_tra`

Chuỗi điểm có thứ tự của 1 tuyến — chứa **mọi** điểm xe thực sự đi qua (`van_phong` lẫn `diem_dung`, mục 3.1).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `diem_don_tra_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | |
| `thu_tu` | INTEGER NOT NULL | Dùng cho cơ chế chống trùng ghế theo khoảng `[thu_tu, thu_tu)` (mục 6) |
| `thoi_gian_du_kien_phut` | INTEGER NOT NULL | Số phút lệch so với `chuyen_xe.gio_khoi_hanh` |

UNIQUE: (`tuyen_id`, `thu_tu`) và (`tuyen_id`, `diem_don_tra_id`) — 1 điểm không xuất hiện 2 lần trong cùng 1 tuyến. Điểm có `thu_tu` nhỏ nhất và lớn nhất của mỗi tuyến bắt buộc `loai = 'van_phong'` (kiểm tra ở Service).

### 2.5. `gia_ve`

**Giá gốc** — chỉ phụ thuộc `(tuyến, cặp điểm đi/điểm đến)`, không phụ thuộc điểm đón/trả cụ thể (mục 3.1) và **không phụ thuộc loại xe** — nhập tay, không tính tự động theo km. Loại xe được nhân vào **lúc tính giá thực tế** qua `loai_xe.he_so_gia` (mục 3.1 file này), không lưu thành cột/dòng riêng ở đây — tránh phải nhập `(số tuyến) × (số cặp điểm) × (số loại xe)` dòng.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `diem_di_id` | UUID NOT NULL, FK → `khu_vuc(id)` | |
| `diem_den_id` | UUID NOT NULL, FK → `khu_vuc(id)` | |
| `gia_goc` | NUMERIC(12,0) NOT NULL | Giá ứng với `loai_xe.he_so_gia = 1` (hệ số chuẩn) — giá thực tế bán ra = `gia_goc × he_so_gia` của xe đang chạy chuyến đó (mục 7) |
| `ap_dung_tu` | DATE NULLABLE | Cho giá theo mùa/dịp lễ; `NULL` = áp dụng vô thời hạn |
| `ap_dung_den` | DATE NULLABLE | |

UNIQUE: (`tuyen_id`, `diem_di_id`, `diem_den_id`, `ap_dung_tu`).

---

## 3. Xe & chuyến xe

### 3.1. `loai_xe`

Danh mục loại xe — **`quan_ly` tự thêm/sửa tùy ý** (VD "Ghế ngồi", "Giường đơn", "Giường cabin đôi", "Limousine phòng đơn"...), không giới hạn số lượng, không hard-code như bản trước (`xe.loai` cũ). **2 xe cùng `loai_xe` phải giống hệt nhau về mọi mặt** — sơ đồ ghế, hệ số giá — chỉ khác biển số (mục 3.3 `NGHIEP_VU.md`, phục vụ đổi xe khi hỏng mà không ảnh hưởng gì tới vé đã đặt). Vì vậy sơ đồ ghế đặt ở **`loai_xe`**, không phải ở `xe`. **Không có cột sức chứa khoang hàng** — đã bỏ hẳn cơ chế tính sức chứa tự động (`NGHIEP_VU.md` mục 10.2): việc xe còn chỗ chứa hàng hay không do phụ xe tự đánh giá trực tiếp lúc chất hàng, không thể tính đúng chỉ bằng 1 con số kg (khác ghế, vốn là vị trí rời rạc đếm được).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ten` | TEXT NOT NULL UNIQUE | |
| `he_so_gia` | NUMERIC(4,2) NOT NULL DEFAULT 1.0 | Hệ số nhân với `gia_ve.gia_goc` để ra giá bán thực tế — cấu hình **1 lần cho toàn hệ thống**, dùng chung cho mọi tuyến |
| `so_do_ghe` | JSONB NOT NULL | Sơ đồ ghế thật (số ghế + cách bố trí) — dùng JSON thay vì bảng `ghe_xe` riêng, đơn giản hơn cho quy mô BTL. Mọi xe cùng `loai_xe` dùng chung đúng 1 sơ đồ này |

### 3.2. `xe`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `bien_so` | TEXT NOT NULL UNIQUE | |
| `loai_xe_id` | UUID NOT NULL, FK → `loai_xe(id)` | Quyết định sơ đồ ghế, hệ số giá (mục 3.1 file này) — **đây là thuộc tính duy nhất phân biệt "loại" của 1 xe** |
| `trang_thai` | TEXT NOT NULL DEFAULT `'hoat_dong'`, CHECK IN (`hoat_dong`, `bao_tri`, `ngung_su_dung`) | Xe `bao_tri`/`ngung_su_dung` không được gán chuyến mới (Service kiểm tra) |
| `diem_goc_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | Phải `loai = 'van_phong'` — vị trí khởi điểm khi chưa chạy chuyến nào (mục 3.3 `NGHIEP_VU.md`) |
| `nhom_tuyen_id` | UUID NULLABLE, FK → `nhom_tuyen(id)` | `NULL` = xe dự phòng, dùng linh hoạt cho mọi tuyến (mục 3.1/3.2 `NGHIEP_VU.md`) |

**Vị trí hiện tại của xe không lưu thành cột** — suy ra động từ `diem_goc_id` + chuyến gần nhất đã hoàn thành của xe đó (mục 3.3 `NGHIEP_VU.md`, xem mục 7 file này).

### 3.3. `chuyen_xe`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `xe_id` | UUID NULLABLE, FK → `xe(id)` | **Xe gốc** — quyết định biên chế tài xế/phụ xe (mục 3.2) và vị trí suy luận cho các chuyến sau (mục 3.3). **Không đổi** khi xe hỏng — xem `xe_thuc_te_id`. **`NULL`** = chuyến đã sinh sẵn từ lịch chạy định kỳ nhưng **chưa được gán xe cụ thể** (mục 3.5 `NGHIEP_VU.md`, UC-44) — vẫn bán vé bình thường dựa vào `loai_xe_id` bên dưới, biên chế tài xế/phụ xe và vị trí suy luận chỉ có ý nghĩa từ lúc gán xe. Nếu còn `NULL` khi tới đúng `gio_khoi_hanh` → job tự động bật `dang_hoan` (UC-45, mục 3.3) — không tự hủy |
| `loai_xe_id` | UUID NOT NULL, FK → `loai_xe(id)` | Loại xe **cam kết** phục vụ chuyến này (copy từ `lich_chay_dinh_ky.loai_xe_id` lúc sinh chuyến) — dùng để hiển thị sơ đồ ghế + tính giá **ngay cả khi chưa gán `xe_id`** (mục 3.5 `NGHIEP_VU.md`). Khi gán `xe_id`, Service bắt buộc `xe.loai_xe_id = chuyen_xe.loai_xe_id` |
| `lich_chay_dinh_ky_id` | UUID NULLABLE, FK → `lich_chay_dinh_ky(id)` | Lịch chạy định kỳ đã sinh ra chuyến này (mục 3.5) — `NULL` nếu chuyến được tạo cách khác (không bắt buộc phải qua lịch định kỳ, dự phòng cho các trường hợp đặc biệt) |
| `xe_thuc_te_id` | UUID NULLABLE, FK → `xe(id)` | Phương tiện vật lý thực sự chạy chuyến này, nếu khác `xe_id` (mục 3.3 — đổi xe khi hỏng đột xuất). `NULL` = đúng xe gốc đang chạy. Bắt buộc cùng `loai_xe` với `xe_id` khi có giá trị (Service kiểm tra) |
| `gio_khoi_hanh` | TIMESTAMPTZ NOT NULL | |
| `trang_thai` | TEXT NOT NULL DEFAULT `'chua_khoi_hanh'`, CHECK IN (`chua_khoi_hanh`, `dang_chay`, `gap_su_co`, `hoan_thanh`, `da_huy`) | Không có trạng thái "hủy vì ít khách" **và không có trạng thái riêng cho "hoãn"** — chuyến luôn chạy (mục 1, mục 4); khi hoãn trước giờ chạy do hết xe thay thế (mục 3.3), chuyến vẫn ở `chua_khoi_hanh`, chỉ đổi `gio_khoi_hanh` + bật cờ `dang_hoan` dưới đây. `da_huy` **không dùng** cho hết xe thay thế trước giờ chạy, và **không dùng** cho `gap_su_co` do `loai_su_co = 'loi_nha_xe'` (luôn tìm được xe thay thế) — chỉ dùng cho `gap_su_co` do `loai_su_co = 'loi_khach_quan'` khi điều độ viên xác nhận thực sự không thể tiếp tục |
| `dang_hoan` | BOOLEAN NOT NULL DEFAULT false | `true` khi chuyến đang chờ tìm xe trước giờ khởi hành — 2 nguồn gốc dùng chung cờ này (mục 3.3): (a) xe đã gán (`xe_id` có giá trị) hỏng đột xuất, chưa tìm được xe thay thế kịp (lệch >30 phút, điều độ viên bật thủ công qua UC-20); (b) chưa từng gán được xe (`xe_id` vẫn `NULL`), tới đúng `gio_khoi_hanh` mà vẫn chưa có (job tự động bật qua UC-45 ⏱). Cả 2 đều mở quyền hủy nhận hoàn 100% cho vé `da_thanh_toan` (UC-41, ngoại lệ duy nhất). Tắt lại khi điều độ viên tìm được xe (gán `xe_id` nếu trường hợp (b), hoặc `xe_thuc_te_id` nếu trường hợp (a)) và cập nhật `gio_khoi_hanh` chính thức |
| `gio_xac_nhan_xuat_phat` | TIMESTAMPTZ NULLABLE | Phụ xe xác nhận (mục 8.2 điểm 2) |
| `gio_hoan_thanh` | TIMESTAMPTZ NULLABLE | |
| `loai_su_co` | TEXT NULLABLE, CHECK IN (`loi_nha_xe`, `loi_khach_quan`) | Set khi chuyển `gap_su_co` (UC-17) — quyết định toàn bộ cách xử lý và quyền hoàn tiền của khách trong lúc chờ (mục 3.3/4/7). `loi_nha_xe` luôn tìm được xe thay thế cuối cùng (không có nhánh hủy); chỉ `loi_khach_quan` mới có thể dẫn tới `da_huy` |
| `ly_do_su_co` | TEXT NULLABLE | Mô tả chi tiết sự cố (VD "nổ lốp", "sạt lở km 45") khi chuyển `gap_su_co`/`da_huy`, hoặc lý do đang `dang_hoan` |
| `co_canh_bao_xung_dot_vi_tri` | BOOLEAN NOT NULL DEFAULT false | Set `true` cho mọi chuyến `chua_khoi_hanh` cùng `xe_id` ngay khi 1 chuyến trước đó của xe này chuyển `gap_su_co` giữa đường (mục 3.3) — bất kể sau đó tự khắc phục, delay dài, hay `da_huy`. Điều độ viên xem lại thủ công sau khi sự cố resolve: nếu xe vẫn tới kịp thì chỉ chỉnh giờ rồi gỡ cờ; nếu không tới kịp thì xử lý qua UC-20 (tìm xe thay thế/hoãn) trước khi gỡ cờ. **Không dùng cho trường hợp đổi xe thực tế trước giờ chạy** (đã có `xe_thuc_te_id` xử lý riêng, không làm lệch vị trí suy luận của `xe_id`) |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

Ràng buộc "không trùng lịch", "đúng vị trí xe", "đúng nhóm tuyến" (mục 3.2/3.3) đều kiểm tra ở Service lúc `INSERT`/`UPDATE xe_id`, không phải constraint DB. Ràng buộc "cùng `loai_xe`" khi gán `xe_thuc_te_id` cũng kiểm tra ở Service. **Xe thuê ngoài** (mục 3.3, khi hết xe dự phòng nội bộ) không cần cột/bảng riêng — chỉ là 1 bản ghi `xe` bình thường được điều độ viên thêm tạm vào hệ thống, đủ điều kiện `loai_xe`/vị trí như xe nội bộ.

### 3.4. `lich_su_diem_dung_chuyen`

Ghi nhận giờ thực tế phụ xe xác nhận đến từng điểm trung gian (mục 8.2 điểm 5) — dùng cập nhật ETA cho khách chờ ở các điểm phía sau.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `chuyen_id` | UUID NOT NULL, FK → `chuyen_xe(id)` | |
| `diem_don_tra_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | Phải thuộc đúng tuyến của chuyến (`tuyen_diem_don_tra`) |
| `gio_thuc_te` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

UNIQUE: (`chuyen_id`, `diem_don_tra_id`).

### 3.5. `lich_chay_dinh_ky`

Do `quan_ly` thiết lập (mục 3.5/8.7 `NGHIEP_VU.md`, UC-18) — nguồn duy nhất sinh ra `chuyen_xe` mới trong hệ thống. Tách "lên lịch chuyến chạy khi nào, loại xe gì" (kế hoạch dài hạn) khỏi "xe cụ thể (biển số) nào chạy" (vận hành ngắn hạn, `dieu_do_vien` xử lý riêng qua UC-44).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `gio_khoi_hanh` | TIME NOT NULL | Giờ khởi hành trong ngày (không phải ngày cụ thể) — dùng làm mẫu để job định kỳ sinh `chuyen_xe.gio_khoi_hanh` (kèm ngày cụ thể) mỗi ngày |
| `loai_xe_id` | UUID NOT NULL, FK → `loai_xe(id)` | Loại xe dự kiến phục vụ khung giờ này — copy sang `chuyen_xe.loai_xe_id` mỗi lần sinh chuyến |
| `dang_ap_dung` | BOOLEAN NOT NULL DEFAULT true | `false` = ngừng sinh chuyến mới từ lịch này — **không xóa/ảnh hưởng** các `chuyen_xe` đã sinh sẵn trước đó |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Job định kỳ sinh chuyến** (`ARCHITECTURE.md` mục 5): với mỗi `lich_chay_dinh_ky` có `dang_ap_dung = true`, tạo `chuyen_xe` cho các ngày còn thiếu trong cửa sổ N ngày tới (N = tham số hệ thống `quan_ly` cấu hình, mục 8.7 `NGHIEP_VU.md`) — kiểm tra tránh sinh trùng ngày đã có sẵn (VD `UNIQUE(lich_chay_dinh_ky_id, ngày)` tính từ `gio_khoi_hanh`, hoặc job tự truy vấn chuyến gần nhất đã sinh rồi tiếp tục từ đó).

**Index nên đánh thêm**: `chuyen_xe(xe_id) WHERE xe_id IS NULL` — dùng cho danh sách "chuyến cần gán xe" của điều độ viên (UC-44), đặc biệt lọc thêm theo ngưỡng cảnh báo 48 tiếng (mục 3.5 `NGHIEP_VU.md`).

---

## 4. Vé

### `ve`

Bảng trung tâm của toàn hệ thống — chịu trách nhiệm cho cơ chế chống trùng ghế (mục 6) và toàn bộ vòng đời đặt vé (mục 3.4, 5).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `chuyen_id` | UUID NOT NULL, FK → `chuyen_xe(id)` | |
| `so_ghe` | TEXT NOT NULL | Khớp `loai_xe.so_do_ghe` của xe đang gán cho chuyến — **không** `UNIQUE` cùng `chuyen_id` (mục 0) |
| `diem_don_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | Điểm khách chọn — bắt buộc `loai = 'van_phong'` (mục 3.4 bước 5) |
| `diem_tra_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | `van_phong` hoặc `diem_dung` |
| `khach_hang_id` | UUID NULLABLE, FK → `nguoi_dung(id)` | `NULL` nếu vé vãng lai (mua tại quầy/hotline không tài khoản) |
| `ten_khach_vang_lai` | TEXT NULLABLE | Bắt buộc nếu `khach_hang_id IS NULL` (kiểm tra Service) |
| `sdt_khach_vang_lai` | TEXT NULLABLE | |
| `gia` | NUMERIC(12,0) NOT NULL | Lấy từ `gia_ve` tại thời điểm đặt (không tính lại nếu `gia_ve` đổi sau đó) |
| `ma_dat_cho` | TEXT NOT NULL | Nhóm các vé cùng 1 lần đặt (mục 3.4) |
| `la_ve_dat_coc` | BOOLEAN NOT NULL DEFAULT false | `true` với các vé bị bắt buộc "thanh toán ngay" trong lô >600.000đ (mục 3.4) |
| `loai_hinh_thanh_toan` | TEXT NOT NULL, CHECK IN (`thanh_toan_ngay`, `thanh_toan_tai_quay`) | Mô tả **kênh/thời điểm trả tiền**, chọn ngay lúc đặt vé — tách biệt khỏi `phuong_thuc_thanh_toan` bên dưới (trả bằng gì). `thanh_toan_tai_quay` dùng chung cho **cả 3 trường hợp**: khách đặt online chọn trả sau, nhân viên quầy vé bán trực tiếp (UC-09), và bán qua hotline (UC-10) — cả 3 đều không áp dụng hạn giữ chỗ nào (mục 3.4/6 `NGHIEP_VU.md`) |
| `phuong_thuc_thanh_toan` | TEXT NULLABLE, CHECK IN (`tien_mat`, `chuyen_khoan`) | Mô tả **trả bằng gì** — chỉ có giá trị khi vé đã thực sự thu tiền (`gio_thanh_toan` được set). Với `loai_hinh_thanh_toan = 'thanh_toan_ngay'` luôn tự động `= 'chuyen_khoan'` (bản chất qua VNPay); với `'thanh_toan_tai_quay'` do nhân viên quầy chọn lúc thu tiền (tiền mặt hoặc đưa QR VNPay cho khách quét) |
| `ma_giao_dich_cong_thanh_toan` | TEXT NULLABLE | Mã giao dịch phía VNPay, set ngay khi `phuong_thuc_thanh_toan = 'chuyen_khoan'` và thanh toán thành công (webhook trả về) — dùng để gọi API hoàn tiền của VNPay sau này (mục 7), kết hợp với `gio_thanh_toan` làm ngày giao dịch gốc. `NULL` nếu trả tiền mặt |
| `trang_thai` | TEXT NOT NULL DEFAULT `'giu_cho'`, CHECK IN (`giu_cho`, `het_han`, `da_thanh_toan`, `da_len_xe`, `da_xuong_xe`, `khong_den`, `da_huy`) | Đúng vòng đời ở mục 5 |
| `gio_bat_dau_dem_han` | TIMESTAMPTZ NULLABLE | Set khi khách **tới màn thanh toán** (mục 3.4 bước 6) — `NULL` nghĩa là ghế đã khóa nhưng chưa bắt đầu tính giờ |
| `han_giu_cho_den` | TIMESTAMPTZ NULLABLE | Chỉ có giá trị khi `loai_hinh_thanh_toan = 'thanh_toan_ngay'`: 5 phút sau `gio_bat_dau_dem_han` (hạn chót an toàn, thực tế thường được webhook cổng thanh toán xử lý sớm hơn, `ARCHITECTURE.md` mục 5). **`NULL` với `thanh_toan_tai_quay`** — không có hạn nào, giữ tới giờ khởi hành (mục 3.4/6 `NGHIEP_VU.md`) |
| `gio_thanh_toan` | TIMESTAMPTZ NULLABLE | |
| `gio_len_xe` | TIMESTAMPTZ NULLABLE | |
| `gio_xuong_xe` | TIMESTAMPTZ NULLABLE | |
| `gio_huy` | TIMESTAMPTZ NULLABLE | |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Index bắt buộc**: `(chuyen_id, so_ghe)` — không unique, chỉ để câu `SELECT ... FOR UPDATE` trong `dat_ve_service` quét nhanh đúng các dòng cần khóa (mục 6, `ARCHITECTURE.md` mục 4).

**Không có cột nào đánh dấu "đã hoàn tiền" trên `ve`** — cố ý: 1 vé có tồn tại dòng `lich_su_hoan_tien` (mục 4.1) hay không chính là câu trả lời, tránh 2 nguồn dữ liệu có thể lệch nhau.

### 4.1. `lich_su_hoan_tien`

Ghi lại **mỗi lần hoàn tiền thực sự xảy ra** — tách khỏi vòng đời `ve` để không làm rối bảng chính, và là nguồn dữ liệu duy nhất cho thống kê hoàn tiền của `quan_ly` (mục 8.7 `NGHIEP_VU.md`), đồng thời đóng vai trò **hàng đợi xử lý của `ke_toan`** cho phần không tự động hoàn được (mục 7/8.8 `NGHIEP_VU.md`).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ve_id` | UUID NOT NULL, FK → `ve(id)` | |
| `ly_do` | TEXT NOT NULL, CHECK IN (`bat_kha_khang_khong_hoan_thanh`, `loi_nha_xe_giua_duong`, `hoan_truoc_gio_chay`, `tu_dong_hoan_qua_3_tieng`) | `bat_kha_khang_khong_hoan_thanh` = UC-21 (chuyến `gap_su_co` do `loai_su_co = 'loi_khach_quan'`, điều độ viên xác nhận không thể tiếp tục — dịch vụ chắc chắn không được cung cấp), `loi_nha_xe_giua_duong` = UC-42 (khách tự hủy lúc chuyến đang `gap_su_co` do `loai_su_co = 'loi_nha_xe'`), `hoan_truoc_gio_chay` = UC-41 (khách tự hủy lúc chuyến đang `dang_hoan` trước giờ chạy), `tu_dong_hoan_qua_3_tieng` = UC-43 (hệ thống tự động hoàn khi `gap_su_co` do `loai_su_co = 'loi_nha_xe'` kéo dài ≥3 tiếng, khách không chủ động hủy — **duy nhất trường hợp này vé không chuyển `da_huy`**, vẫn `da_thanh_toan` bình thường). Lưu thẳng thay vì suy ra qua join mỗi lần thống kê — dùng để `quan_ly` lọc/gộp nhanh theo lý do (mục 8.7 `NGHIEP_VU.md`) |
| `so_tien` | NUMERIC(12,0) NOT NULL | Luôn bằng `ve.gia` tại thời điểm hoàn — hoàn đúng 100%, không có mức khác (mục 7) |
| `trang_thai` | TEXT NOT NULL DEFAULT `'cho_xu_ly'`, CHECK IN (`cho_xu_ly`, `da_hoan_tu_dong`, `da_hoan_chuyen_khoan_thu_cong`) | `cho_xu_ly` = đã xác định phải hoàn nhưng tiền chưa tới tay khách — hàng đợi cho `ke_toan` xử lý (UC-22). `da_hoan_tu_dong` = hoàn qua API VNPay; `da_hoan_chuyen_khoan_thu_cong` = `ke_toan` tự chuyển khoản thủ công (khách trả tiền mặt ban đầu, hoặc API VNPay thất bại) |
| `ma_giao_dich_hoan_tien` | TEXT NULLABLE | Mã giao dịch hoàn phía VNPay — chỉ có giá trị khi `trang_thai = 'da_hoan_tu_dong'` |
| `nhan_vien_xu_ly_id` | UUID NULLABLE, FK → `nguoi_dung(id)` | `ke_toan` đã thực hiện chuyển khoản thủ công — chỉ có giá trị khi `trang_thai = 'da_hoan_chuyen_khoan_thu_cong'` (UC-22) |
| `so_tai_khoan_nhan` | TEXT NULLABLE | Số tài khoản ngân hàng khách cung cấp qua điện thoại, `ke_toan` nhập vào trước khi chuyển khoản — chỉ có giá trị khi `trang_thai = 'da_hoan_chuyen_khoan_thu_cong'`. Lưu lại để đối soát nếu phát sinh tranh chấp (khách khiếu nại chưa nhận được tiền, hoặc kế toán cần đối chiếu với sao kê ngân hàng) |
| `ten_ngan_hang_nhan` | TEXT NULLABLE | Tên ngân hàng tương ứng `so_tai_khoan_nhan` |
| `ten_chu_tai_khoan_nhan` | TEXT NULLABLE | Tên chủ tài khoản khách đọc qua điện thoại — không nhất thiết trùng tên khách trên vé (khách có thể nhờ chuyển vào tài khoản người khác), lưu lại để đối chiếu đúng người nhận |
| `thoi_gian_xac_dinh` | TIMESTAMPTZ NOT NULL DEFAULT now() | Lúc UC-21/UC-41/UC-42/UC-43 xác định vé này phải hoàn |
| `thoi_gian_hoan_xong` | TIMESTAMPTZ NULLABLE | Lúc tiền thực sự tới tay khách — `NULL` khi còn `cho_xu_ly` |

**Có lưu thông tin tài khoản ngân hàng nhận tiền** (khác quyết định ban đầu) — phục vụ đối soát khi có tranh chấp/khiếu nại sau này, đối chiếu được với sao kê ngân hàng thật của công ty. Đây là dữ liệu nhạy cảm — chỉ `ke_toan`/`quan_ly` được xem các cột `so_tai_khoan_nhan`/`ten_ngan_hang_nhan`/`ten_chu_tai_khoan_nhan` (kiểm tra ở tầng Service/phân quyền, không phải ai có quyền đọc bảng này cũng thấy được các cột này).

UNIQUE: (`ve_id`) — 1 vé chỉ hoàn tiền đúng 1 lần (không có cơ chế hoàn nhiều đợt). Ràng buộc này cũng là lưới an toàn cho UC-43 (job chạy lại không hoàn trùng) và cho UC-42 khi khách hủy sau khi đã được UC-43 tự động hoàn trước đó (Service kiểm tra tồn tại trước khi tạo mới, mục 12 `NGHIEP_VU.md`).

**Index nên đánh thêm**: `(trang_thai) WHERE trang_thai = 'cho_xu_ly'` — dùng cho màn hình "danh sách hoàn tiền đang chờ xử lý" của `ke_toan`, phạm vi toàn hệ thống (mục 8.8 `NGHIEP_VU.md`).

---

## 5. Gửi hàng

### 5.1. `loai_hang`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ten` | TEXT NOT NULL UNIQUE | VD "thường", "dễ vỡ", "hàng lạnh", "tài liệu" |
| `la_hang_cam` | BOOLEAN NOT NULL DEFAULT false | Chặn ngay khi tạo đơn nếu `true` (mục 10.1) |

### 5.2. `don_hang`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | Tuyến khách muốn gửi qua — chọn lúc nhận hàng, **không phải** 1 chuyến cụ thể (mục 10.2) |
| `chuyen_id` | UUID NULLABLE, FK → `chuyen_xe(id)` | **`NULL`** = đơn đang chờ, chưa được phụ xe chọn xếp lên chuyến nào. Chỉ có giá trị **sau khi** chuyển `da_len_xe` (UC-26, mục 10.2) — không ràng buộc `loai_xe` hay bất kỳ điều kiện nào khác ngoài đúng `tuyen_id` |
| `diem_gui_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | |
| `diem_nhan_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | |
| `can_nang_kg` | NUMERIC(8,2) NOT NULL | Vẫn cân thực tế lúc nhận hàng, nhưng chỉ để nhân viên tham khảo lúc định giá cước — **không dùng để tính/chặn sức chứa xe** (mục 10.2, đã bỏ `loai_xe.suc_chua_hang_kg`) |
| `dai_cm`, `rong_cm`, `cao_cm` | NUMERIC(8,2) NULLABLE | Tùy chọn, dùng tham khảo khi cân/đo (mục 10.1) |
| `loai_hang_id` | UUID NOT NULL, FK → `loai_hang(id)` | |
| `gia_cuoc` | NUMERIC(12,0) NOT NULL | **Nhân viên gửi hàng tự nhập tay** — không có công thức/bảng giá tự động (mục 10.1) |
| `ten_nguoi_gui`, `sdt_nguoi_gui` | TEXT NOT NULL | Không cần tài khoản, không thu email (mục 10.1) |
| `ten_nguoi_nhan`, `sdt_nguoi_nhan` | TEXT NOT NULL | |
| `phuong_thuc_thanh_toan` | TEXT NOT NULL, CHECK IN (`nguoi_gui_tra_truoc`, `cod_nguoi_nhan_tra`) | |
| `ma_van_don` | TEXT NOT NULL UNIQUE | In trên biên nhận đưa người gửi — không gửi SMS/email tự động (mục 10.3.1) |
| `trang_thai` | TEXT NOT NULL DEFAULT `'cho_van_chuyen'`, CHECK IN (`cho_van_chuyen`, `da_len_xe`, `cho_lay`, `da_giao`, `qua_han_luu_kho`) | Vòng đời ở mục 10.3. `qua_han_luu_kho` ("hàng tồn") không phải trạng thái tự hủy — chỉ đánh dấu cần xử lý thủ công (UC-25/46) |
| `nhan_vien_gui_id` | UUID NOT NULL, FK → `nguoi_dung(id)` | Người tạo đơn (mục 10.4.1) |
| `nhan_vien_nhan_id` | UUID NULLABLE, FK → `nguoi_dung(id)` | Người xác nhận giao (mục 10.4.2), `NULL` cho tới khi `da_giao` |
| `thoi_gian_den_diem_nhan` | TIMESTAMPTZ NULLABLE | Set khi phụ xe xác nhận dỡ hàng, chuyển `cho_lay` (UC-27) — mốc để tính 7/14 ngày cho UC-46 (mục 10.3.1). `NULL` trước đó |
| `da_thong_bao_nguoi_nhan` | BOOLEAN NOT NULL DEFAULT false | Nhân viên gửi hàng tích khi gọi điện báo người nhận **thành công** (mục 10.3.1/10.4.2) — hệ thống chỉ lưu đúng 1 cờ này, không đếm số cuộc gọi. `false` khi tới mốc 7 ngày (UC-46) nghĩa là chưa từng liên lạc được, cần gọi thẳng người gửi thay vì tiếp tục thử người nhận |
| `co_canh_bao_cho_lau` | BOOLEAN NOT NULL DEFAULT false | Tự động bật bởi job khi `cho_lay` đủ 7 ngày mà chưa `da_giao` (UC-46 ⏱) — nhắc nhân viên gửi hàng xử lý (UC-25). Không liên quan tới việc hủy/thanh lý, chỉ để nhắc |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `ngay_giao` | TIMESTAMPTZ NULLABLE | |

**Index nên đánh thêm**: `(tuyen_id) WHERE chuyen_id IS NULL` — dùng cho danh sách "đơn hàng đang chờ chất lên chuyến" của phụ xe tại 1 điểm (UC-26), sắp theo `ngay_tao` (thứ tự thời gian, mục 10.2). `(chuyen_id)` — dùng khi tra cứu đơn hàng theo chuyến cụ thể (VD danh sách cần dỡ ở UC-27). `(trang_thai, thoi_gian_den_diem_nhan) WHERE trang_thai = 'cho_lay'` — dùng cho job quét mốc 7/14 ngày (UC-46).

---

## 6. Thông báo & nhật ký

### 6.1. `thong_bao` *(bảng bổ sung — không có tên tường minh trong `NGHIEP_VU.md`, cần thiết để không mất thông báo khi khách offline)*

`NGHIEP_VU.md` mô tả đẩy thông báo qua WebSocket (mục 8.1, 8.2) nhưng không nói nơi lưu trữ — nếu chỉ đẩy real-time, khách không online lúc sự kiện xảy ra sẽ mất thông báo vĩnh viễn.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `nguoi_nhan_id` | UUID NOT NULL, FK → `nguoi_dung(id)` | |
| `noi_dung` | TEXT NOT NULL | |
| `ve_id` | UUID NULLABLE, FK → `ve(id)` | Liên kết ngữ cảnh nếu gắn với 1 vé cụ thể (đổi xe, sự cố, sắp tới giờ) |
| `da_doc` | BOOLEAN NOT NULL DEFAULT false | |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

### 6.2. `nhat_ky_admin`

Nhật ký thao tác của `quan_ly`/`quan_ly_nhan_su` — phục vụ tra soát.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `admin_id` | UUID NOT NULL, FK → `nguoi_dung(id)` | |
| `hanh_dong` | TEXT NOT NULL | VD `tao_tai_khoan`, `khoa_tai_khoan`, `sua_bien_che_co_dinh`, `cau_hinh_gia_ve`, `go_han_che_khach_hang`... |
| `doi_tuong_loai` | TEXT NOT NULL | Bảng/loại đối tượng bị tác động |
| `doi_tuong_id` | UUID NOT NULL | |
| `ghi_chu` | TEXT NULLABLE | |
| `thoi_gian` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

---

## 7. Các giá trị tính động — cố ý không lưu thành cột/bảng riêng

Nhất quán với nguyên tắc "tính động qua query, không cache số liệu" — tránh rủi ro lệch với dữ liệu gốc:

| Giá trị | Cách tính |
|---|---|
| Vị trí suy luận theo lịch trình của 1 xe gốc (mục 3.3) | Tính theo `chuyen_xe.xe_id` (**không phải** `xe_thuc_te_id`) — nếu chưa có `chuyen_xe` nào kết thúc trước thời điểm xét → `xe.diem_goc_id`. Ngược lại → điểm cuối cùng (`thu_tu` lớn nhất trong `tuyen_diem_don_tra` của tuyến chuyến đó, luôn `loai = 'van_phong'`) của `chuyen_xe` gần nhất (theo `gio_khoi_hanh`) có `xe_id` khớp, kết thúc trước thời điểm xét. Dùng để kiểm tra tính liên tục khi **gán xe** cho chuyến (UC-44) — **không đổi** dù chuyến đang chạy bằng xe thực tế khác. Chỉ tính được cho chuyến đã có `xe_id` — chuyến `xe_id IS NULL` (chưa gán xe, mục 3.5 `NGHIEP_VU.md`) chưa có vị trí nào để suy luận |
| Phương tiện vật lý thực sự chạy 1 chuyến cụ thể (mục 3.3) | `COALESCE(chuyen_xe.xe_thuc_te_id, chuyen_xe.xe_id)` — dùng để hiển thị biển số cho khách và theo dõi vị trí vật lý thật. Kết quả `NULL` = chuyến chưa gán xe, hệ thống hiển thị tên `loai_xe` thay vì biển số |
| "Chuyến của tôi" của 1 phụ xe (mục 3.2) | `chuyen_xe` có `xe_id` khớp 1 dòng `xe_nhan_su(nhan_su_van_hanh_id = X, trang_thai = 'dang_hoat_dong')` tại thời điểm truy vấn — chuyến `xe_id IS NULL` chưa thuộc về phụ xe nào |
| Ghế còn trống cho 1 đoạn `[don, tra)` (mục 6) | Không tồn tại `ve` nào cùng `(chuyen_id, so_ghe)`, trạng thái `giu_cho`/`da_thanh_toan`, có khoảng `[thu_tu(diem_don), thu_tu(diem_tra))` giao với đoạn đang xét — dùng `chuyen_xe.loai_xe_id.so_do_ghe` để biết tổng số ghế, không cần `xe_id` đã gán hay chưa |
| Số lần vi phạm no-show của 1 khách hàng (mục 9) | Đếm `ve` của khách có `trang_thai = 'khong_den'` — nhóm theo `khach_hang_id`, lọc theo khoảng thời gian gần nhất (không còn cần xét `het_han`, vì "thanh toán tại quầy" không có `het_han` do hết hạn nữa, mục 3.4/6 `NGHIEP_VU.md`) |
| Tỷ lệ lấp đầy ghế của 1 chuyến (mục 8.6 điểm 2) | `COUNT(ve active)` / tổng số ghế trong `loai_xe.so_do_ghe` của `chuyen_xe.loai_xe_id` — chỉ để thống kê, **không** dùng để hủy chuyến |
| Giá vé thực tế của 1 chuyến cho 1 cặp điểm (mục 2.5, mục 3.1 file này) | `gia_ve.gia_goc × loai_xe.he_so_gia` của **`chuyen_xe.loai_xe_id`** (loại xe cam kết, mục 3.5 `NGHIEP_VU.md`) — nhân lúc truy vấn, **không lưu thành cột riêng** cho từng tổ hợp (tuyến × cặp điểm × loại xe), tránh bùng nổ số dòng cần nhập tay khi có nhiều loại xe. Tính được **ngay từ khi chuyến được sinh ra**, không cần đợi gán `xe_id` |
| Còn được tự hủy giữ chỗ hay không (mục 7/8.1/9 `NGHIEP_VU.md`) | `now() < (chuyen_xe.gio_khoi_hanh + tuyen_diem_don_tra.thoi_gian_du_kien_phut của diem_don_id − X phút cấu hình)` — **dùng chung đúng 1 mốc** với việc xác định no-show (không phải 2 mốc riêng); qua mốc này API hủy trả lỗi, không xóa/sửa DB |
| Hoàn tiền tự động qua cổng hay do kế toán xử lý thủ công (mục 7 `NGHIEP_VU.md`, UC-21/UC-41/UC-42) | `ve.ma_giao_dich_cong_thanh_toan IS NOT NULL` → gọi API hoàn tiền của VNPay (kèm `gio_thanh_toan` làm ngày giao dịch gốc) — thành công thì tạo `lich_su_hoan_tien` với `trang_thai = 'da_hoan_tu_dong'` luôn. `NULL` (trả tiền mặt), hoặc API hoàn tiền gọi thất bại → tạo `lich_su_hoan_tien` với `trang_thai = 'cho_xu_ly'`, chờ `ke_toan` xử lý (UC-22) |
| Danh sách hoàn tiền đang chờ `ke_toan` xử lý (mục 8.8 `NGHIEP_VU.md`) | `lich_su_hoan_tien` có `trang_thai = 'cho_xu_ly'` — phạm vi **toàn hệ thống**, không lọc theo văn phòng (vì `ke_toan` không gắn văn phòng nào, mục 2) |

---

## 8. Sơ đồ quan hệ (dạng liệt kê)

```
nguoi_dung 1──1 ho_so_khach_hang     (vai_tro = khach_hang)
nguoi_dung 1──1 ho_so_can_bo_diem    (vai_tro = nhan_vien_quay_ve | nhan_vien_gui_hang | dieu_do_vien)
nguoi_dung 0──1 nhan_su_van_hanh     (vai_tro = phu_xe — chiều ngược lại nullable)
ho_so_can_bo_diem N──1 diem_don_tra  (van_phong_id)

nhan_su_van_hanh 1──N xe_nhan_su
xe 1──N xe_nhan_su

khu_vuc 1──N diem_don_tra
nhom_tuyen 1──N tuyen
tuyen 1──N tuyen_diem_don_tra N──1 diem_don_tra
khu_vuc 1──N gia_ve (diem_di_id), khu_vuc 1──N gia_ve (diem_den_id)
tuyen 1──N gia_ve

diem_don_tra 1──1 xe (diem_goc_id)
nhom_tuyen 0──N xe
loai_xe 1──N xe

xe 0──N chuyen_xe        (xe_id — xe gốc, nullable tới khi gán xe)
xe 0──N chuyen_xe        (xe_thuc_te_id — xe chạy thay, nullable)
loai_xe 1──N chuyen_xe   (loai_xe_id — loại xe cam kết)
tuyen 1──N chuyen_xe
tuyen 1──N lich_chay_dinh_ky
loai_xe 1──N lich_chay_dinh_ky
lich_chay_dinh_ky 0──N chuyen_xe
chuyen_xe 1──N lich_su_diem_dung_chuyen N──1 diem_don_tra

chuyen_xe 1──N ve
diem_don_tra 1──N ve (diem_don_id), diem_don_tra 1──N ve (diem_tra_id)
nguoi_dung(khach_hang) 0──N ve

ve 1──1 lich_su_hoan_tien
nguoi_dung 0──N lich_su_hoan_tien (nhan_vien_xu_ly_id)

tuyen 1──N don_hang        (tuyen_id — chọn lúc nhận hàng)
chuyen_xe 0──N don_hang    (chuyen_id — nullable, chỉ gán lúc phụ xe chọn xếp lên xe, mục 10.2)
diem_don_tra 1──N don_hang (diem_gui_id), diem_don_tra 1──N don_hang (diem_nhan_id)
loai_hang 1──N don_hang
nguoi_dung 1──N don_hang (nhan_vien_gui_id)

nguoi_dung 1──N thong_bao
ve 0──N thong_bao
nguoi_dung(quan_ly) 1──N nhat_ky_admin
```

---

## 9. Bổ sung cần làm rõ với nhóm trước khi migrate thật

- **Câu lệnh `CREATE EXTENSION "pgcrypto"`** cần chạy trong migration đầu tiên để có hàm `gen_random_uuid()`.
- Index nên đánh thêm: `ve(chuyen_id, so_ghe)` (mục 4 — bắt buộc vì bị `SELECT ... FOR UPDATE` quét thường xuyên, khác `don_hang` vốn không còn cơ chế khóa dòng tương tự từ khi bỏ chống quá tải tự động, mục 10.2), `don_hang(tuyen_id) WHERE chuyen_id IS NULL` (danh sách đơn chờ chất lên xe theo tuyến, UC-26, mục 10.2), `chuyen_xe(xe_id, gio_khoi_hanh)` (dùng cho truy vấn vị trí xe, mục 7), `chuyen_xe(xe_id) WHERE xe_thuc_te_id IS NOT NULL` (dùng để liệt kê nhanh mọi chuyến đang chạy thay của 1 xe gốc, UC-40), `chuyen_xe(xe_id) WHERE xe_id IS NULL` (danh sách "chuyến cần gán xe", UC-44, mục 3.5), `ho_so_can_bo_diem(van_phong_id)` (điều độ viên/nhân viên quầy vé lọc theo phạm vi mình phụ trách gần như mọi truy vấn).
- **Job sinh `chuyen_xe` từ `lich_chay_dinh_ky`** (`NGHIEP_VU.md` mục 3.5, UC-18): chạy định kỳ (VD hàng ngày), với mỗi lịch `dang_ap_dung = true`, sinh thêm chuyến cho các ngày còn thiếu trong cửa sổ N ngày cấu hình — cần logic tránh sinh trùng (kiểm tra đã có chuyến cho ngày đó của đúng `lich_chay_dinh_ky_id` chưa) và xử lý khi `quan_ly` sửa giờ/loại xe của lịch định kỳ đang áp dụng (chỉ ảnh hưởng các chuyến sinh **sau** thời điểm sửa, không đổi ngược các chuyến đã sinh/đã bán vé).
- **Bảng `thong_bao`** là đề xuất bổ sung của tôi (giống bản v1) — xác nhận lại có cần hay chấp nhận mất thông báo khi khách offline trước khi đưa vào migration chính thức.
- **Cơ chế "đặt cọc" cho lô nhiều vé** (`NGHIEP_VU.md` mục 3.4): khi lô >600.000đ chưa đủ số vé `la_ve_dat_coc` được thanh toán trong 5 phút, toàn bộ lô (cùng `ma_dat_cho`) phải chuyển `het_han` — đây là logic Service quét theo `ma_dat_cho`, không có constraint DB nào diễn tả trực tiếp được, cần test kỹ ở tầng integration test.
- **Cơ chế "hoãn" chuyến (`chuyen_xe.dang_hoan`) + ngưỡng cảnh báo 6 tiếng** (`NGHIEP_VU.md` mục 3.3): việc bật/tắt `dang_hoan`, dời `gio_khoi_hanh` nhiều lần, và mở quyền hủy-hoàn-100% cho vé `da_thanh_toan` (UC-41) đều là logic Service, không phải constraint DB — đặc biệt lưu ý chuyến **không bao giờ** được phép tự động chuyển `da_huy` chỉ vì hết xe thay thế, kể cả khi vượt ngưỡng cảnh báo. Có **2 đường bật cờ `dang_hoan`** cần cài đặt riêng: điều độ viên bật thủ công (UC-20, xe đã gán rồi hỏng) và job định kỳ tự bật (UC-45 ⏱, chưa từng gán được xe mà đã tới `gio_khoi_hanh`) — job UC-45 nên gộp chung vào đúng `jobs/quet_het_han.py` (`ARCHITECTURE.md` mục 5), quét `chuyen_xe` có `xe_id IS NULL AND gio_khoi_hanh <= now() AND trang_thai = 'chua_khoi_hanh'`.
- **Xử lý sự cố giữa đường theo `chuyen_xe.loai_su_co`** (`NGHIEP_VU.md` mục 3.3/4, UC-19): ngưỡng 1 tiếng (`loi_nha_xe`) và 3 tiếng (`loi_khach_quan`) chỉ mang tính hướng dẫn cho điều độ viên đánh giá mức độ, **không có ngưỡng nào tự động set `da_huy`** — luôn cần điều độ viên xác nhận thủ công là thực sự không thể tiếp tục (chỉ áp dụng cho `loai_su_co = 'loi_khach_quan'`, UC-21). Riêng ngưỡng **≥3 tiếng cho `loi_nha_xe`** LÀ một mốc hệ thống tự động xử lý thật — nhưng chỉ để **tự động hoàn tiền** (UC-43, `lich_su_hoan_tien`), **không đổi `chuyen_xe.trang_thai` hay `ve.trang_thai`** gì cả.
- **Chuyển khoản thủ công của `ke_toan` (UC-22) chỉ ghi nhận kết quả, không tích hợp ngân hàng**: hệ thống không có API/webhook nào với ngân hàng cho bước này (khác VNPay dùng cho thanh toán/hoàn tự động) — `ke_toan` tự chuyển khoản ngoài hệ thống rồi mới quay lại nhập `so_tai_khoan_nhan`/`ten_ngan_hang_nhan`/`ten_chu_tai_khoan_nhan` và đánh dấu `trang_thai = 'da_hoan_chuyen_khoan_thu_cong'` — chỉ để lưu vết đối soát, hệ thống không tự động xác minh các thông tin này đúng hay không.
- **Phân quyền đọc `lich_su_hoan_tien`**: các cột `so_tai_khoan_nhan`/`ten_ngan_hang_nhan`/`ten_chu_tai_khoan_nhan` là dữ liệu nhạy cảm — chỉ `ke_toan`/`quan_ly` đọc được, các vai trò khác (kể cả nhân viên quầy vé tra cứu tình trạng hoàn tiền, mục 8.4 `NGHIEP_VU.md`) chỉ thấy `trang_thai`/`thoi_gian_hoan_xong`, không thấy thông tin tài khoản.
- **Seed tài khoản `quan_ly` gốc**: migration khởi tạo phải insert đúng 1 dòng `nguoi_dung` với `vai_tro = 'quan_ly'`, `la_tai_khoan_goc = true` — kèm partial unique index (mục 1.1) để không ai (kể cả bug ở tầng Service) vô tình tạo thêm dòng `true` thứ 2. Phân quyền tạo/khóa `quan_ly`/`quan_ly_nhan_su` (UC-36/37/38 `NGHIEP_VU.md`) kiểm tra hoàn toàn ở Service dựa trên cột này, không có `CHECK` constraint nào diễn tả được logic "chỉ actor X mới thao tác được vai trò Y".
