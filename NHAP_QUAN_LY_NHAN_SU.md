# BẢN NHÁP — mở rộng vai trò Quản lý nhân sự (`quan_ly_nhan_su`)

> **Đây là file nháp, chưa thuộc bộ tài liệu chính.** Nội dung nằm trong các khối ` ```` ` bên dưới là văn bản sẵn sàng dán vào file thật, viết theo đúng văn phong và cách đánh số của file đó. Mỗi khối có ghi rõ **dán vào file nào, vị trí nào, thay hay thêm**. Sau khi cả nhóm đồng ý và đã dán xong, xóa file này.

**Phạm vi đợt này (3 việc):**
1. Hồ sơ tài xế/phụ xe kèm giấy tờ, và cảnh báo giấy tờ sắp hết hạn → **UC-47, UC-48**.
2. Cho nghỉ việc nhân sự vận hành, có cảnh báo xe thiếu biên chế → **UC-49** (bổ sung nhẹ vào UC-37).
3. Xem nhật ký thao tác → **UC-50**.

UC mới đánh số từ **UC-47** vì UC-46 là số cao nhất hiện có (UC-06/07 đã retire, không dùng lại).

---

## 0. Quyết định cần nhóm xác nhận TRƯỚC khi dán

| # | Quyết định (bản nháp đã chọn sẵn) | Vì sao chọn |
|---|---|---|
| 1 | **Hồ sơ nhân sự** (`nhan_su_van_hanh`) do `quan_ly_nhan_su` (và `quan_ly`) quản lý. **Biên chế** (`xe_nhan_su`, UC-35) vẫn chỉ của `quan_ly`. | Tách "ai là nhân sự của công ty" khỏi "người đó đi xe nào". Không đụng vào UC-35 của trưởng nhóm. |
| 2 | Tạo tài khoản phụ xe (UC-36) và tạo hồ sơ (UC-47) là **2 bước riêng**; hồ sơ phụ xe chọn tài khoản `phu_xe` đã có để liên kết. | Không phải sửa UC-36. |
| 3 | Cho nghỉ việc **không tự gỡ** dòng `xe_nhan_su` cố định — chỉ chuyển sang `tam_nghi`, để `quan_ly` gỡ hẳn/biên chế người mới (UC-35). | Đúng nguyên tắc mục 3.2: đổi biên chế cố định là việc của `quan_ly`; `tam_nghi` làm hệ thống ngừng suy ra chuyến cho người đó ngay. |
| 4 | Giấy tờ theo dõi: **bằng lái** (tài xế bắt buộc) và **giấy khám sức khỏe**. Ngưỡng cảnh báo mặc định **30 ngày**. | Đủ dùng cho đồ án; ngưỡng cấu hình được như các ngưỡng khác (mục 8.7 điểm 3). |
| 5 | Job cảnh báo **chỉ nhắc**, không khóa/không gỡ biên chế/không chặn gán xe. | Cùng nguyên tắc UC-46: chỉ nhắc con người xử lý. |
| 6 | Lưu số CCCD (dữ liệu nhạy cảm). | Cần bỏ nếu nhóm không muốn lưu — xóa cột `so_cccd` ở mục 2.1. |

---

## 1. NGHIEP_VU.md

### 1.1. Mục 2 (bảng vai trò) — THAY dòng `quan_ly_nhan_su`

````markdown
| `quan_ly_nhan_su` | Được **quản lý gốc** tạo trực tiếp, **không gắn văn phòng nào** (phạm vi toàn hệ thống) | Tạo/khóa/mở khóa tài khoản cho `nhan_vien_van_hanh` (phụ xe), `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien` — **không** quản lý tài khoản `ke_toan`, `quan_ly`, hay `quan_ly_nhan_su` khác (mục 8.9). **Quản lý hồ sơ nhân sự vận hành** (tài xế + phụ xe: thông tin, giấy tờ, cho nghỉ việc — mục 8.9). Xem nhật ký thao tác của chính mình. Xem thống kê toàn hệ thống. Không có quyền nghiệp vụ nào khác (tuyến, giá, xe, **biên chế xe**, khuyến mãi) |
````

### 1.2. Mục 8.9 — THAY TOÀN BỘ nội dung mục

````markdown
### 8.9. Quản lý nhân sự (`quan_ly_nhan_su`)

Phạm vi **toàn hệ thống** (không gắn văn phòng, giống `ke_toan`/`quan_ly`, mục 2) — sinh ra để san bớt việc quản lý nhân sự vận hành khỏi `quan_ly` khi quy mô công ty lớn (nhiều văn phòng, hàng trăm nhân sự). Chỉ xử lý **tài khoản và hồ sơ** nhân sự cấp vận hành — **không có quyền nghiệp vụ nào khác** (không sửa tuyến, giá, xe, biên chế xe, khuyến mãi, lịch chạy định kỳ).

1. Tạo tài khoản cho đúng **4 vai trò**: `nhan_vien_van_hanh` (phụ xe), `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien` — qua đúng cơ chế mời như `quan_ly` (mục 8.7 điểm 2). **Không** tạo được tài khoản `ke_toan`, `quan_ly`, hay `quan_ly_nhan_su` khác — các vai trò này nhạy cảm hơn (tiền, hoặc chính quyền quản trị), chỉ `quan_ly` (với `ke_toan`) hoặc `quan_ly` gốc (với `quan_ly`/`quan_ly_nhan_su`) mới tạo được.
2. Khóa/mở khóa tài khoản cho đúng 4 vai trò trên — không đụng được tới `ke_toan`/`quan_ly`/`quan_ly_nhan_su` khác.
3. Xem thống kê toàn hệ thống (UC-39), cùng phạm vi như `quan_ly`.
4. Chỉ **tài khoản `quan_ly` gốc** (mục 2, mục 8.7 điểm 2) mới tạo được tài khoản `quan_ly_nhan_su` — không tự đăng ký, không được `quan_ly_nhan_su` khác hay `quan_ly` không phải gốc tạo hộ.
5. **Quản lý hồ sơ nhân sự vận hành** (UC-47): tạo/sửa hồ sơ **tài xế và phụ xe** (họ tên, SĐT, CCCD, ngày sinh, ngày vào làm) kèm **giấy tờ** (bằng lái, giấy khám sức khỏe, ngày hết hạn). Tài xế không có tài khoản (mục 3.2), nên đây là nơi duy nhất lưu thông tin của họ. Hệ thống tự nhắc khi giấy tờ sắp hết hạn (UC-48).
6. **Cho nghỉ việc** nhân sự vận hành (UC-49): đóng hồ sơ (không xóa, giữ lịch sử), khóa tài khoản nếu là phụ xe, và **báo ngay** cho `quan_ly` + điều độ viên biết xe nào vừa thiếu người để bổ sung. Quản lý nhân sự **không** tự gỡ/thay biên chế xe — đó là việc của `quan_ly` (UC-35).
7. Xem **nhật ký thao tác của chính mình** (UC-50) — mọi thao tác tạo/khóa/mở khóa tài khoản, tạo/sửa hồ sơ, cho nghỉ việc đều được ghi lại. `quan_ly` xem được nhật ký của mọi người, dùng để giám sát người có quyền cao này.

**Ranh giới với `quan_ly`**: quản lý nhân sự trả lời câu hỏi "**ai** là nhân sự của công ty, giấy tờ còn hạn không" (hồ sơ); `quan_ly` trả lời "người đó **đi xe nào**" (biên chế, UC-35). `quan_ly` làm được cả hai; quản lý nhân sự chỉ làm được phần hồ sơ.
````

### 1.3. Mục 3.2 — THÊM 1 gạch đầu dòng (đặt sau gạch "Tài xế chỉ là hồ sơ nhân sự trong `xe_nhan_su`…")

````markdown
- **Hồ sơ nhân sự vận hành (`nhan_su_van_hanh`) và biên chế (`xe_nhan_su`) do 2 vai trò khác nhau quản lý** (mục 8.9): hồ sơ (thông tin, giấy tờ, trạng thái làm việc) do `quan_ly_nhan_su` hoặc `quan_ly`; biên chế cố định do `quan_ly` (UC-35). **Chỉ hồ sơ đang làm việc (`dang_lam`) mới được đưa vào biên chế xe.** Giấy tờ (bằng lái, giấy khám sức khỏe) hết hạn **không chặn** việc biên chế hay gán xe — hệ thống chỉ nhắc người quản lý nhân sự xử lý (UC-48), quyết định cuối cùng là của con người.
````

### 1.4. Mục 11 (ma trận UC) — THÊM 4 dòng ngay sau dòng UC-46

````markdown
| UC-47 | Quản lý hồ sơ nhân sự vận hành (tài xế/phụ xe) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| UC-48 | Tự động cảnh báo giấy tờ nhân sự vận hành sắp hết hạn/đã hết hạn ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-49 | Cho nghỉ việc nhân sự vận hành | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| UC-50 | Xem nhật ký thao tác | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (của mình) | ✅ (toàn bộ) |
````

### 1.5. Mục 12 (đặc tả UC) — THÊM 4 đặc tả sau UC-46 (hoặc cuối mục 12, trước mục 13)

````markdown
### UC-47. Quản lý hồ sơ nhân sự vận hành (tài xế/phụ xe)

- **Actor**: Quản lý nhân sự, hoặc Quản lý.
- **Tiền điều kiện**: Với hồ sơ phụ xe: tài khoản `phu_xe` đã được tạo (UC-36). Tài xế không cần tài khoản (mục 3.2).
- **Luồng chính** (mục 8.9 điểm 5, mục 3.2):
  1. Chọn "Thêm hồ sơ", hoặc chọn 1 hồ sơ có sẵn để sửa.
  2. Nhập họ tên, số điện thoại, chức danh (`tai_xe`/`phu_xe`), số CCCD, ngày sinh, ngày vào làm; nếu là phụ xe thì chọn tài khoản `phu_xe` tương ứng.
  3. Nhập/cập nhật giấy tờ: bằng lái và giấy khám sức khỏe — mỗi giấy tờ gồm số, hạng (chỉ bằng lái), ngày cấp, ngày hết hạn.
  4. Hệ thống kiểm tra, lưu hồ sơ và ghi nhật ký thao tác (UC-50).
- **Luồng rẽ nhánh**:
  - Tại bước 2: chức danh `phu_xe` nhưng tài khoản được chọn không phải vai trò `phu_xe`, hoặc đã gắn với hồ sơ khác → chặn, báo lỗi → chọn lại.
  - Tại bước 2: chức danh `tai_xe` mà có chọn tài khoản → chặn (tài xế không có tài khoản, mục 3.2).
  - Tại bước 3: hồ sơ `tai_xe` chưa có bằng lái → chặn, báo "tài xế bắt buộc có thông tin bằng lái".
  - Tại bước 3: ngày hết hạn đã qua → **vẫn cho lưu** (cập nhật hồ sơ cũ), hệ thống hiển thị cờ "đã hết hạn" — UC-48 sẽ nhắc ngay ở lần quét kế tiếp.
  - Tại bước 3: gia hạn giấy tờ (nhập ngày hết hạn mới) → hệ thống xóa cờ đã cảnh báo, chu kỳ nhắc bắt đầu lại từ đầu.
  - Không có thao tác xóa hồ sơ, không đổi chức danh sau khi tạo; nhân sự thôi việc dùng UC-49.
- **Hậu điều kiện**: Hồ sơ đầy đủ; nhân sự đang làm việc có thể được `quan_ly` đưa vào biên chế xe (UC-35).

### UC-48. Tự động cảnh báo giấy tờ nhân sự vận hành sắp hết hạn/đã hết hạn ⏱

- **Actor**: Hệ thống (job định kỳ — không phải actor người dùng thao tác trực tiếp).
- **Tiền điều kiện**: Hồ sơ nhân sự `dang_lam` có giấy tờ với ngày hết hạn còn ≤ 30 ngày (ngưỡng do `quan_ly` cấu hình, mục 8.7 điểm 3) hoặc đã qua.
- **Luồng chính** (mục 8.9 điểm 5):
  1. Job quét giấy tờ của toàn bộ nhân sự đang làm việc, mỗi ngày 1 lần.
  2. Giấy tờ còn ≤ 30 ngày mà chưa có cờ "đã cảnh báo sắp hết hạn" → bật cờ, gửi thông báo tới mọi tài khoản `quan_ly_nhan_su` đang hoạt động (nêu họ tên, loại giấy tờ, ngày hết hạn).
  3. Giấy tờ đã qua ngày hết hạn mà chưa có cờ "đã cảnh báo hết hạn" → bật cờ, gửi thông báo mức khẩn tới cùng nhóm người nhận.
- **Luồng rẽ nhánh**:
  - Không có tài khoản `quan_ly_nhan_su` nào đang hoạt động → gửi cho `quan_ly`.
  - Nhân sự đã `da_nghi_viec` → bỏ qua.
  - Giấy tờ được gia hạn (UC-47) → 2 cờ được xóa, giấy tờ quay lại chu kỳ cảnh báo từ đầu.
  - Không có nhánh nào tự khóa tài khoản, tự gỡ biên chế hay chặn gán xe — cả 2 mốc chỉ **nhắc con người xử lý** (cùng nguyên tắc UC-46).
- **Hậu điều kiện**: Người quản lý nhân sự nhận được nhắc; giấy tờ có cờ tương ứng. Hồ sơ và biên chế giữ nguyên, chờ xử lý thủ công (UC-47).

### UC-49. Cho nghỉ việc nhân sự vận hành

- **Actor**: Quản lý nhân sự, hoặc Quản lý.
- **Tiền điều kiện**: Hồ sơ đang `dang_lam`. Chỉ áp dụng cho nhân sự vận hành (tài xế, phụ xe); tài khoản quầy vé/gửi hàng/điều độ viên nghỉ việc thì dùng UC-37 (khóa tài khoản).
- **Luồng chính** (mục 8.9 điểm 6, mục 3.2):
  1. Chọn hồ sơ cần cho nghỉ việc, nhập ngày nghỉ và lý do.
  2. Hệ thống liệt kê các dòng biên chế `xe_nhan_su` mà người này đang thuộc, kèm xe nào sẽ **thiếu người** sau khi họ nghỉ (so với quy tắc 2 tài xế + ≥1 phụ xe cố định mỗi xe).
  3. Người thao tác xem cảnh báo và xác nhận.
  4. Hệ thống: đặt hồ sơ `da_nghi_viec` (kèm ngày, lý do); nếu là phụ xe thì khóa tài khoản (đặt `dang_hoat_dong = false`, như UC-37); chuyển mọi dòng `xe_nhan_su` của người này sang `tam_nghi` để hệ thống ngừng suy ra chuyến cho họ ngay.
  5. Hệ thống gửi thông báo tới `quan_ly` (để gỡ hẳn/biên chế người mới, UC-35) và tới các điều độ viên (để dùng nguồn dự phòng tạm thời, mục 3.2), nêu rõ xe nào đang thiếu tài xế/phụ xe.
  6. Ghi nhật ký thao tác (UC-50).
- **Luồng rẽ nhánh**:
  - Tại bước 1: xe mà người này thuộc biên chế đang có chuyến `dang_chay` → chặn, báo "chờ chuyến kết thúc rồi thực hiện lại" → kết thúc.
  - Tại bước 2: người này không thuộc biên chế xe nào → bỏ qua bước 2 và bước 5, chuyển thẳng sang bước 4 (không khóa thêm gì nếu là tài xế).
  - Hệ thống **không xóa cứng** hồ sơ và **không tự gỡ** dòng biên chế cố định — việc gỡ hẳn và biên chế người mới thuộc `quan_ly` (UC-35, mục 8.7), giữ đúng ranh giới ở mục 8.9.
- **Hậu điều kiện**: Hồ sơ `da_nghi_viec` (giữ lịch sử); tài khoản phụ xe (nếu có) không đăng nhập được; các xe bị ảnh hưởng đã được báo cho `quan_ly` và điều độ viên.

### UC-50. Xem nhật ký thao tác

- **Actor**: Quản lý nhân sự (chỉ thấy các dòng do chính mình thực hiện), hoặc Quản lý (thấy toàn bộ).
- **Luồng chính** (mục 8.9 điểm 7):
  1. Mở màn hình nhật ký.
  2. Lọc theo khoảng thời gian, loại hành động (tạo/khóa/mở khóa tài khoản, tạo/sửa hồ sơ, cho nghỉ việc, …), đối tượng bị tác động; riêng `quan_ly` lọc thêm được theo người thực hiện.
  3. Hệ thống hiển thị danh sách, dòng mới nhất trước.
- **Luồng rẽ nhánh**: Nhật ký **chỉ xem** — không có thao tác sửa hay xóa dòng nào (bảng chỉ thêm mới).
- **Hậu điều kiện**: Không thay đổi dữ liệu.
````

### 1.6. Mục 12, UC-35 — THÊM 1 dòng vào luồng rẽ nhánh

````markdown
  - Tại bước chọn nhân sự đưa vào biên chế: hồ sơ đang `da_nghi_viec` → chặn, chỉ hồ sơ `dang_lam` mới được biên chế (mục 3.2).
````

### 1.7. Mục 12, UC-37 — THÊM vào cuối "Hậu điều kiện"

````markdown
  Nếu tài khoản bị khóa là `phu_xe` đang thuộc biên chế xe (`xe_nhan_su`), hệ thống hiển thị cảnh báo "xe X thiếu phụ xe" và gửi thông báo như UC-49 bước 5 — nhưng **không tự đổi biên chế** (khóa tạm thời chưa chắc là nghỉ việc; nếu là nghỉ việc thì dùng UC-49).
````

---

## 2. DATABASE.md

### 2.0. Tổng hợp: cần thêm gì, ở bảng nào

| Bảng | Thay đổi | Mức độ | Dán ở |
|---|---|---|---|
| `nhan_su_van_hanh` (mục 1.4) | **Thêm 6 cột**: `so_cccd`, `ngay_sinh`, `ngay_vao_lam`, `trang_thai`, `ngay_nghi_viec`, `ly_do_nghi_viec`. **Thêm 3 ràng buộc**: `UNIQUE (nguoi_dung_id)`, 2 `CHECK` | Bắt buộc | 2.1 |
| `giay_to_nhan_su` (**bảng mới**, mục 1.6) | 9 cột như 2.2, `UNIQUE (nhan_su_van_hanh_id, loai)`, index `ngay_het_han` | Bắt buộc | 2.2 |
| `nhat_ky_admin` (mục 6.2) | **Không thêm cột.** Chỉ bổ sung quy ước giá trị `hanh_dong`/`doi_tuong_loai` và 2 index | Bắt buộc (index + quy ước) | 2.3 |
| `thong_bao` (mục 6.1) | Thêm 2 cột tùy chọn: `nhan_su_van_hanh_id`, `xe_id` | **Tùy chọn** — bỏ đi vẫn chạy được, nội dung chữ đủ | 2.5 |
| Sơ đồ quan hệ (mục 8) | Thêm 1 dòng, sửa 1 dòng | Bắt buộc | 2.4 |
| Mục 9 (bổ sung cần làm rõ) | Thêm 3 gạch đầu dòng: phân quyền đọc CCCD, ngưỡng cảnh báo, lý do khóa | Bắt buộc | 2.6 |

**Các bảng KHÔNG cần đổi** (đã đối chiếu với mục 1.1, 1.2, 1.3, 1.5 của DATABASE.md):
- `nguoi_dung`: không thêm cột. Khóa tài khoản dùng lại `dang_hoat_dong`. **Lý do khóa** của cán bộ (UC-37) ghi vào `nhat_ky_admin.ghi_chu` (cột đã có), UC-38 "xem lý do khóa trước đó" đọc dòng `khoa_tai_khoan` mới nhất của tài khoản đó. Nếu nhóm muốn tra nhanh hơn thì mới thêm `nguoi_dung.ly_do_khoa` — bản nháp không thêm để khỏi trùng với `ho_so_khach_hang.ly_do_khoa` (mục 1.2).
- `xe_nhan_su`: không thêm cột. UC-49 chỉ chuyển `trang_thai` sang `tam_nghi` (giá trị có sẵn). Muốn biết "tạm nghỉ vì nghỉ việc hay nghỉ phép" thì join sang `nhan_su_van_hanh.trang_thai = 'da_nghi_viec'`.
- `ho_so_can_bo_diem`, `ho_so_khach_hang`: không liên quan.
- **Bảng cấu hình tham số**: DATABASE.md hiện **không có** bảng nào lưu ngưỡng cấu hình (các ngưỡng 6 tiếng, 48 tiếng, no-show… cũng chưa có chỗ lưu). Ngưỡng "30 ngày" của UC-48 sẽ theo cách nhóm chọn cho các ngưỡng đó; tạm thời để hằng số trong `backend/app/config.py`.

### 2.1. Mục 1.4 `nhan_su_van_hanh` — THÊM 6 dòng vào cuối bảng cột

````markdown
| `so_cccd` | TEXT NULLABLE | Dữ liệu nhạy cảm — chỉ `quan_ly_nhan_su`/`quan_ly` xem được, không trả ra API của vai trò khác. Nên đánh partial unique index `WHERE so_cccd IS NOT NULL` |
| `ngay_sinh` | DATE NULLABLE | |
| `ngay_vao_lam` | DATE NOT NULL DEFAULT current_date | |
| `trang_thai` | TEXT NOT NULL DEFAULT `'dang_lam'`, CHECK IN (`dang_lam`, `da_nghi_viec`) | **Khác** `xe_nhan_su.trang_thai` (mục 1.5): đây là trạng thái làm việc **của cả hồ sơ**. `da_nghi_viec` không được đưa vào biên chế mới (UC-35) và bị job UC-48 bỏ qua |
| `ngay_nghi_viec` | DATE NULLABLE | Chỉ có giá trị khi `trang_thai = 'da_nghi_viec'` (UC-49) |
| `ly_do_nghi_viec` | TEXT NULLABLE | |
````

Cột đã có sẵn từ trước (`id`, `ho_ten`, `so_dien_thoai`, `chuc_danh`, `nguoi_dung_id`) giữ nguyên. **THÊM đoạn ràng buộc này ngay sau bảng cột:**

````markdown
**Ràng buộc** (thực hiện ở DB được vì diễn tả được bằng `CHECK`/`UNIQUE` đơn giản):
- `UNIQUE (nguoi_dung_id)` — mỗi tài khoản chỉ gắn với 1 hồ sơ (`NULL` không xung đột nhau nên tài xế không bị ảnh hưởng).
- `CHECK (chuc_danh = 'phu_xe' OR nguoi_dung_id IS NULL)` — tài xế **không bao giờ** có tài khoản (mục 3.2/8.3 `NGHIEP_VU.md`).
- `CHECK ((trang_thai = 'da_nghi_viec') = (ngay_nghi_viec IS NOT NULL))` — trạng thái nghỉ việc và ngày nghỉ luôn đi đôi với nhau.

**Kiểm tra ở Service** (không diễn tả được bằng constraint DB): tài khoản được chọn cho hồ sơ `phu_xe` phải có `nguoi_dung.vai_tro = 'phu_xe'` (UC-47).
````

### 2.2. THÊM mục mới 1.6 (sau mục 1.5)

````markdown
### 1.6. `giay_to_nhan_su` (giấy tờ của tài xế/phụ xe — phục vụ UC-47/UC-48)

Mỗi nhân sự có **tối đa 1 dòng cho mỗi loại giấy tờ** (giấy tờ hiện hành) — gia hạn thì cập nhật dòng đó, không lưu lịch sử các lần gia hạn cũ (đủ cho mục đích nhắc hết hạn, không phải hồ sơ pháp lý đầy đủ).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `nhan_su_van_hanh_id` | UUID NOT NULL, FK → `nhan_su_van_hanh(id)` | |
| `loai` | TEXT NOT NULL, CHECK IN (`bang_lai`, `giay_kham_suc_khoe`) | `UNIQUE (nhan_su_van_hanh_id, loai)`. "Tài xế bắt buộc có `bang_lai`" kiểm tra ở Service (UC-47), không phải constraint DB |
| `so_giay_to` | TEXT NULLABLE | |
| `hang` | TEXT NULLABLE | Chỉ dùng cho `bang_lai` (VD D, E). Hệ thống **chỉ lưu**, không kiểm tra hạng bằng có phù hợp `loai_xe` hay không |
| `ngay_cap` | DATE NULLABLE | |
| `ngay_het_han` | DATE NOT NULL | Mốc để job UC-48 quét |
| `da_canh_bao_sap_het_han` | BOOLEAN NOT NULL DEFAULT false | Bật khi job gửi nhắc "còn ≤ N ngày"; tránh nhắc trùng mỗi ngày |
| `da_canh_bao_het_han` | BOOLEAN NOT NULL DEFAULT false | Bật khi job gửi nhắc "đã hết hạn" |

**Gia hạn (đổi `ngay_het_han` sang ngày mới) phải đặt lại cả 2 cờ về `false`** để chu kỳ nhắc bắt đầu lại — làm trong cùng câu `UPDATE` ở Service.

**Index nên đánh thêm**: `giay_to_nhan_su(ngay_het_han)` — job UC-48 quét theo mốc ngày.
````

### 2.3. Mục 6.2 `nhat_ky_admin` — THÊM đoạn ghi chú sau bảng

````markdown
**Quy ước ghi nhật ký** (phục vụ UC-50):
- `hanh_dong` dùng các giá trị cố định: `tao_tai_khoan`, `khoa_tai_khoan`, `mo_khoa_tai_khoan` (UC-36/37/38), `tao_ho_so_nhan_su`, `sua_ho_so_nhan_su`, `cho_nghi_viec` (UC-47/49), cùng các giá trị của `quan_ly` đã liệt kê ở trên.
- `doi_tuong_loai` = `nguoi_dung` (thao tác lên tài khoản) hoặc `nhan_su_van_hanh` (thao tác lên hồ sơ), `doi_tuong_id` là id tương ứng.
- Dòng nhật ký ghi **trong cùng transaction** với thao tác nghiệp vụ — thao tác thành công thì có log, thất bại thì không có log "ma".
- Bảng **chỉ INSERT**, không có `UPDATE`/`DELETE` ở bất kỳ tầng nào (Repository không viết hàm sửa/xóa).
- Index nên đánh: `nhat_ky_admin(admin_id, thoi_gian DESC)` — `quan_ly_nhan_su` chỉ xem dòng của chính mình (lọc `admin_id`); và `nhat_ky_admin(doi_tuong_loai, doi_tuong_id, thoi_gian DESC)` — tra lịch sử của 1 tài khoản/hồ sơ, gồm cả lý do khóa gần nhất (UC-38).
- **Lý do khóa tài khoản cán bộ** (UC-37 bước 3) lưu ở cột `ghi_chu` của dòng `khoa_tai_khoan` — không thêm cột riêng vào `nguoi_dung`.
````

### 2.4. Mục 8 (sơ đồ quan hệ dạng liệt kê) — THÊM 1 dòng và SỬA 1 dòng

THÊM (cạnh dòng `nhan_su_van_hanh 1──N xe_nhan_su`):

````markdown
nhan_su_van_hanh 1──N giay_to_nhan_su  (tối đa 1 dòng mỗi loai giấy tờ)
````

SỬA dòng cuối `nguoi_dung(quan_ly) 1──N nhat_ky_admin` thành:

````markdown
nguoi_dung(quan_ly | quan_ly_nhan_su) 1──N nhat_ky_admin
````

### 2.5. Mục 6.1 `thong_bao` — THÊM 2 cột (TÙY CHỌN)

Chỉ cần nếu muốn bấm vào thông báo để nhảy thẳng tới hồ sơ/xe liên quan (giống cách `ve_id` đang làm). Không thêm thì `noi_dung` (chữ) vẫn đủ cho UC-48/UC-49.

````markdown
| `nhan_su_van_hanh_id` | UUID NULLABLE, FK → `nhan_su_van_hanh(id)` | Liên kết ngữ cảnh nếu thông báo về giấy tờ sắp hết hạn (UC-48) hoặc nhân sự nghỉ việc (UC-49) |
| `xe_id` | UUID NULLABLE, FK → `xe(id)` | Liên kết ngữ cảnh nếu thông báo "xe X thiếu tài xế/phụ xe" (UC-49, UC-37) |
````

Và THÊM vào sơ đồ quan hệ mục 8: `nhan_su_van_hanh 0──N thong_bao`, `xe 0──N thong_bao`.

### 2.6. Mục 9 (bổ sung cần làm rõ với nhóm) — THÊM 3 gạch đầu dòng

````markdown
- **Phân quyền đọc hồ sơ nhân sự**: `nhan_su_van_hanh.so_cccd`, `ngay_sinh` và toàn bộ `giay_to_nhan_su` là dữ liệu nhạy cảm — chỉ `quan_ly_nhan_su`/`quan_ly` đọc được. Phụ xe/điều độ viên khi xem biên chế xe chỉ thấy `ho_ten`, `so_dien_thoai`, `chuc_danh`, không thấy các cột này (cùng nguyên tắc với `lich_su_hoan_tien`, xem bullet ngay trên).
- **Job cảnh báo giấy tờ hết hạn (UC-48)**: chạy mỗi ngày 1 lần; ngưỡng "còn ≤ N ngày" (mặc định 30) là tham số hệ thống — hiện chưa có bảng cấu hình, tạm để hằng số trong `config.py` cho đến khi nhóm chốt chỗ lưu chung cho mọi ngưỡng. Khi gia hạn giấy tờ phải đặt lại cả 2 cờ `da_canh_bao_*` về `false` trong cùng câu `UPDATE` (mục 1.6).
- **Cho nghỉ việc (UC-49) là 1 transaction**: đặt `nhan_su_van_hanh.trang_thai = 'da_nghi_viec'`, khóa `nguoi_dung.dang_hoat_dong` (nếu là phụ xe), chuyển các dòng `xe_nhan_su` sang `tam_nghi`, và ghi `nhat_ky_admin` — hoặc cả 4 cùng thành công, hoặc không làm gì. Kiểm tra "xe đang có chuyến `dang_chay`" (điều kiện chặn) làm **trước** khi mở transaction.
````

---

## 3. ARCHITECTURE.md

### 3.1. Mục 5 (bảng "Việc cần làm / Khi nào / Cơ chế") — THÊM 1 dòng cuối bảng

````markdown
| Cảnh báo giấy tờ nhân sự vận hành sắp hết hạn (30 ngày) và đã hết hạn (UC-48) | `giay_to_nhan_su.ngay_het_han` còn ≤ ngưỡng cấu hình (mặc định 30 ngày) hoặc đã qua, hồ sơ `nhan_su_van_hanh.trang_thai = 'dang_lam'` (`NGHIEP_VU.md` mục 8.9) | **Job định kỳ, mỗi ngày 1 lần** (mốc tính theo ngày nên không cần quét 1 phút như các job khác) — bật cờ `da_canh_bao_sap_het_han`/`da_canh_bao_het_han` rồi gửi `thong_bao` cho `quan_ly_nhan_su` (không có ai đang hoạt động thì gửi `quan_ly`). **Không** khóa tài khoản, gỡ biên chế hay chặn gán xe — chỉ nhắc con người xử lý |
````

### 3.2. Cây thư mục backend — file GỢI Ý thêm (đối chiếu lại tên với cây hiện có trước khi thêm)

````markdown
repositories/giay_to_nhan_su_repository.py     # SQL bảng giay_to_nhan_su (mục 1.6 DATABASE.md)
repositories/nhat_ky_admin_repository.py       # chỉ INSERT + SELECT, không có hàm sửa/xóa
services/ho_so_nhan_su_service.py              # UC-47, UC-49: quy tắc hồ sơ, nghỉ việc, cảnh báo thiếu biên chế
services/nhat_ky_service.py                    # ghi nhật ký (gọi từ mọi service thao tác của quan_ly/quan_ly_nhan_su) + UC-50
jobs/canh_bao_giay_to.py                       # UC-48
routes/nhan_su.py                              # UC-47, UC-49, UC-50
````

`nhan_vien_van_hanh_repository.py` (đã có ở cây thư mục, mục "hồ sơ tài xế/phụ xe + xe_nhan_su") **dùng lại** cho `nhan_su_van_hanh` — chỉ bổ sung hàm cho các cột mới ở mục 2.1.

---

## 4. Chưa làm ở đợt này (ghi lại để khỏi quên)

- **UML_DIAGRAMS.md / USE_CASE.puml**: mục 1.8 (use case Quản lý nhân sự) cần thêm UC-47/49/50, và cần vẽ activity diagram cho 4 UC mới. Nên làm **sau** khi nhóm chốt mục 0.
- **CONTRIBUTING.md**: cần xác định **ai nhận UC-47→UC-50** (cùng người làm UC-36/37/38 hay người khác) rồi cập nhật bảng mục 2 và danh sách UC (đang "44 UC" → 48).
- **Migration SQL** cho mục 2.1, 2.2 — viết sau khi tài liệu được chốt.
- **Chưa hỗ trợ**: hoàn tác nghỉ việc (nghỉ nhầm), sửa thông tin/đổi văn phòng/đổi vai trò/gửi lại email mời cho cán bộ, thống kê hiệu suất nhân sự, quản lý nguồn nhân sự dự phòng. Có thể làm đợt sau.

## 5. Câu hỏi mở cho nhóm

1. Mục 0 các dòng 1–6: nhóm có đồng ý với lựa chọn của bản nháp không?
2. Phụ xe có cần **giấy khám sức khỏe** như tài xế không, hay chỉ tài xế cần bằng lái?
3. Khi không có `quan_ly_nhan_su` nào đang hoạt động, thông báo gửi cho `quan_ly` (đang chọn) hay bỏ qua?
4. Điều độ viên nhận thông báo thiếu biên chế: **tất cả** điều độ viên (đang chọn, vì xe di chuyển giữa nhiều điểm — mục 8.6) hay chỉ điều độ viên ở văn phòng gốc của xe?
5. Lỗi nhỏ có sẵn trong tài liệu, nên thống nhất tên: `NGHIEP_VU.md` mục 3.2 viết `xe_nhan_su(xe_id, nhan_vien_id, …)` còn `DATABASE.md` mục 1.5 viết `nhan_su_van_hanh_id`; và `NGHIEP_VU.md` đặt tên vai trò `nhan_vien_van_hanh` nhưng cột `nguoi_dung.vai_tro` trong DB là `phu_xe`. Bản nháp này dùng tên trong DB.
