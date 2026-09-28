# Thiết kế cơ sở dữ liệu — phạm vi Quản lý nhân sự (`quan_ly_nhan_su`)

> File riêng, phạm vi hẹp: chỉ các bảng mà vai trò `quan_ly_nhan_su` **tạo/sửa/đọc** trong nghiệp vụ đã bàn ở `NHAP_QUAN_LY_NHAN_SU.md` (UC-47→50). Không phải bản thay thế `DATABASE.md` — khi nhóm chốt xong, nội dung ở đây được dán vào đúng vị trí đã chỉ trong `NHAP_QUAN_LY_NHAN_SU.md`. Quy ước chung (UUID PK, `TIMESTAMPTZ`, enum bằng `TEXT + CHECK`, không xóa cứng) giữ nguyên như `DATABASE.md` mục 0 — không nhắc lại.

---

## 0. Vài điều cần đọc trước

**1. Bảng nào kế thừa từ `nguoi_dung`?** Theo đúng kiểu Class Table Inheritance (`DATABASE.md` mục 0 và mục 1), chỉ có **2 bảng con thật sự** — khóa chính của bảng con **chính là** khóa ngoại trỏ về `nguoi_dung`:

| Bảng con | Áp dụng cho `vai_tro` |
|---|---|
| `ho_so_khach_hang` | `khach_hang` |
| `ho_so_can_bo_diem` | `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien` (dùng chung 1 bảng, phân biệt qua `nguoi_dung.vai_tro`) |

`nhan_su_van_hanh` (mục 1 dưới đây) **không phải kiểu kế thừa này** — khóa chính là `id` riêng của nó, còn `nguoi_dung_id` chỉ là khóa ngoại **nullable** trỏ ngược lại, và **chỉ có giá trị với `chuc_danh = phu_xe`** (tài xế không có tài khoản nên không kế thừa gì cả). `phu_xe`, `ke_toan`, `quan_ly_nhan_su`, `quan_ly` đều **không có bảng con kế thừa**.

**2. ⚠️ Cột "ảnh hồ sơ" — xung đột với quyết định kiến trúc đã chốt.** `ARCHITECTURE.md` mục 1 (dòng "File/ảnh") ghi rõ: **"Không dùng — bỏ Cloudinary so với bản v1"**, lý do "domain mới không có nhu cầu khách/nhân viên upload ảnh". Thêm cột ảnh cho hồ sơ nhân sự là **quay lại nhu cầu upload file** mà quyết định đó đã loại bỏ. Mình vẫn thêm cột theo yêu cầu, nhưng đây là **quyết định kiến trúc mới cần cả nhóm đồng ý**, không chỉ riêng phần quản lý nhân sự — xem mục 6 để biết cần chốt gì trước khi migrate thật.

**3. Nhật ký ghi TOÀN BỘ lịch sử thao tác của `quan_ly_nhan_su`, không riêng gì khóa tài khoản.** Bảng `nhat_ky_quan_ly_nhan_su` ở mục 3 ghi đủ **6 loại hành động** người này được phép làm: tạo tài khoản, khóa tài khoản, mở khóa tài khoản, tạo hồ sơ, sửa hồ sơ, cho nghỉ việc — mỗi lần thao tác nào trong 6 loại này xảy ra đều có 1 dòng log riêng, không chỉ mỗi lúc khóa. Ví dụ **"xóa tài khoản"** bạn nhắc tới ban đầu là 1 trong các thao tác đó — nhưng vì `DATABASE.md` mục 0 quy định *"hệ thống không xóa cứng (`DELETE`) tài khoản... khóa/vô hiệu hóa bằng cờ boolean... giữ lại lịch sử"* (xóa cứng dòng `nguoi_dung` sẽ làm vỡ/mất vé, đơn hàng, nhật ký cũ liên kết tới người đó), nên hành động tương ứng được đặt tên `hanh_dong = 'khoa_tai_khoan'` (khóa mềm) thay vì `xoa_tai_khoan` — cùng 1 việc, chỉ khác tên gọi cho khớp với cách hệ thống thật sự vận hành.

---

## 1. `nhan_su_van_hanh` — hồ sơ tài xế + phụ xe

Bảng đã có trong `DATABASE.md` mục 1.4, liệt kê lại đầy đủ (cột cũ + cột mới) để thấy toàn cảnh.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ho_ten` | TEXT NOT NULL | *(cột có sẵn)* |
| `so_dien_thoai` | TEXT NOT NULL | *(cột có sẵn)* |
| `chuc_danh` | TEXT NOT NULL, CHECK IN (`tai_xe`, `phu_xe`) | *(cột có sẵn)* |
| `nguoi_dung_id` | UUID NULLABLE, FK → `nguoi_dung(id)` | *(cột có sẵn)* — chỉ có giá trị khi `chuc_danh = 'phu_xe'` |
| `so_cccd` | TEXT NULLABLE | **Mới.** Dữ liệu nhạy cảm — chỉ `quan_ly_nhan_su`/`quan_ly` đọc được (không trả ra API cho vai trò khác) |
| `ngay_sinh` | DATE NULLABLE | **Mới** |
| `anh_ho_so` | TEXT NULLABLE | **Mới — cột bạn yêu cầu.** Không lưu ảnh trực tiếp trong DB, chỉ lưu **đường dẫn/URL** tới nơi lưu file thật (xem cảnh báo mục 0.2 và câu hỏi mục 6) |
| `ngay_vao_lam` | DATE NOT NULL DEFAULT current_date | **Mới** |
| `trang_thai` | TEXT NOT NULL DEFAULT `'dang_lam'`, CHECK IN (`dang_lam`, `da_nghi_viec`) | **Mới.** Trạng thái làm việc của cả hồ sơ — khác `xe_nhan_su.trang_thai` (biên chế, mục 4.3 dưới) |
| `ngay_nghi_viec` | DATE NULLABLE | **Mới** — chỉ có giá trị khi `trang_thai = 'da_nghi_viec'` |
| `ly_do_nghi_viec` | TEXT NULLABLE | **Mới** |

**Ràng buộc** (đặt được ở DB vì diễn tả đơn giản bằng `CHECK`/`UNIQUE`, không cần join bảng khác):

```sql
UNIQUE (nguoi_dung_id)
CHECK (chuc_danh = 'phu_xe' OR nguoi_dung_id IS NULL)
CHECK ((trang_thai = 'da_nghi_viec') = (ngay_nghi_viec IS NOT NULL))
```

**Kiểm tra ở Service** (không diễn tả được bằng constraint DB): tài khoản được chọn gắn cho hồ sơ `phu_xe` phải có `nguoi_dung.vai_tro = 'phu_xe'`.

---

## 2. `giay_to_nhan_su` — giấy tờ của tài xế/phụ xe *(bảng mới)*

Mỗi nhân sự có tối đa **1 dòng cho mỗi loại giấy tờ** — gia hạn thì cập nhật dòng đó, không giữ lịch sử các lần gia hạn cũ.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `nhan_su_van_hanh_id` | UUID NOT NULL, FK → `nhan_su_van_hanh(id)` | |
| `loai` | TEXT NOT NULL, CHECK IN (`bang_lai`, `giay_kham_suc_khoe`) | `UNIQUE (nhan_su_van_hanh_id, loai)`. "Tài xế bắt buộc có `bang_lai`" kiểm tra ở Service, không phải constraint DB |
| `so_giay_to` | TEXT NULLABLE | |
| `hang` | TEXT NULLABLE | Chỉ dùng cho `bang_lai` (VD D, E) — hệ thống chỉ lưu, không kiểm tra hạng có phù hợp `loai_xe` hay không |
| `ngay_cap` | DATE NULLABLE | |
| `ngay_het_han` | DATE NOT NULL | Mốc để job cảnh báo (UC-48) quét |
| `anh_giay_to` | TEXT NULLABLE | **Thêm cùng lý do với `anh_ho_so` ở mục 1** — ảnh scan bằng lái/giấy khám sức khỏe. Cùng vướng hạ tầng lưu file như mục 0.2, cân nhắc thêm nếu nhóm đồng ý lưu ảnh |
| `da_canh_bao_sap_het_han` | BOOLEAN NOT NULL DEFAULT false | Bật khi job gửi nhắc "còn ≤ N ngày" — tránh nhắc trùng mỗi lần quét |
| `da_canh_bao_het_han` | BOOLEAN NOT NULL DEFAULT false | Bật khi job gửi nhắc "đã hết hạn" |

Gia hạn (đổi `ngay_het_han`) phải đặt lại **cả 2 cờ về `false`** trong cùng câu `UPDATE` để chu kỳ nhắc bắt đầu lại.

**Index nên đánh thêm**: `giay_to_nhan_su(ngay_het_han)` — job quét theo mốc ngày.

---

## 3. `nhat_ky_quan_ly_nhan_su` — nhật ký thao tác *(bảng mới, TÁCH RIÊNG khỏi `nhat_ky_admin`)*

Theo đúng yêu cầu: bảng này **chỉ ghi hành động do chính `quan_ly_nhan_su` thực hiện**. Nó **không dùng chung** với `quan_ly` — khác với bản nháp trước (`NHAP_QUAN_LY_NHAN_SU.md` mục 2.3, lúc đó vẫn định dùng chung `nhat_ky_admin`). Với thiết kế này:
- `nhat_ky_admin` (đã có sẵn ở `DATABASE.md` mục 6.2) **giữ nguyên nghĩa gốc ban đầu của nó** — chỉ ghi hành động của `quan_ly` (tuyến, giá, xe, biên chế, tài khoản do `quan_ly` tạo/khóa...).
- `nhat_ky_quan_ly_nhan_su` là bảng **hoàn toàn tách biệt**, chỉ ghi 6 loại hành động mà `quan_ly_nhan_su` được phép làm — không lẫn hành động của `quan_ly` hay bất kỳ vai trò nào khác, kể cả khi 2 vai trò cùng làm 1 việc giống nhau (VD cả `quan_ly` và `quan_ly_nhan_su` đều tạo được tài khoản `phu_xe` — nhưng chỉ dòng do `quan_ly_nhan_su` tạo mới vào bảng này).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `quan_ly_nhan_su_id` | UUID NOT NULL, FK → `nguoi_dung(id)` | Người thực hiện. Phải có `vai_tro = 'quan_ly_nhan_su'` — kiểm tra ở Service lúc ghi (không dùng `CHECK` được vì phải join sang `nguoi_dung`) |
| `hanh_dong` | TEXT NOT NULL, CHECK IN (`tao_tai_khoan`, `khoa_tai_khoan`, `mo_khoa_tai_khoan`, `tao_ho_so_nhan_su`, `sua_ho_so_nhan_su`, `cho_nghi_viec`) | 6 hành động đúng phạm vi UC-36/37/38 (khi actor là `quan_ly_nhan_su`) + UC-47/49. Không có `xoa_tai_khoan` — xem mục 0.3 |
| `doi_tuong_loai` | TEXT NOT NULL, CHECK IN (`nguoi_dung`, `nhan_su_van_hanh`) | `nguoi_dung` khi thao tác lên tài khoản (`tao_tai_khoan`/`khoa_tai_khoan`/`mo_khoa_tai_khoan`); `nhan_su_van_hanh` khi thao tác lên hồ sơ (`tao_ho_so_nhan_su`/`sua_ho_so_nhan_su`/`cho_nghi_viec`) |
| `doi_tuong_id` | UUID NOT NULL | id tương ứng với `doi_tuong_loai` |
| `ghi_chu` | TEXT NULLABLE | VD lý do khóa tài khoản, lý do nghỉ việc |
| `thoi_gian` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Quy ước:**
- Bảng **chỉ `INSERT`**, không có `UPDATE`/`DELETE` ở bất kỳ tầng nào (Repository không viết hàm sửa/xóa) — đảm bảo nhật ký không bị chỉnh sửa sau khi ghi.
- Ghi trong **cùng transaction** với thao tác nghiệp vụ — thao tác thành công thì có log, thất bại thì không có log "ma".
- Index nên đánh: `nhat_ky_quan_ly_nhan_su(quan_ly_nhan_su_id, thoi_gian DESC)` (xem nhật ký của chính mình — UC-50) và `nhat_ky_quan_ly_nhan_su(doi_tuong_loai, doi_tuong_id, thoi_gian DESC)` (tra lịch sử 1 tài khoản/hồ sơ cụ thể, kể cả lý do khóa gần nhất cho UC-38).

---

## 4. Bảng liên quan — chỉ tham chiếu, KHÔNG đổi cấu trúc

`quan_ly_nhan_su` đọc/ghi các bảng này khi thao tác UC-36/37/38/47/49, nhưng bản thân các bảng không cần thêm cột nào. Liệt kê lại để tiện thiết kế API, không phải thay đổi.

### 4.1. `nguoi_dung` (đã có, `DATABASE.md` mục 1.1)
Các cột `quan_ly_nhan_su` dùng: `id`, `email`, `ho_ten`, `so_dien_thoai`, `vai_tro`, `dang_hoat_dong`, `ngay_tao`. Phạm vi thao tác giới hạn ở `vai_tro IN ('phu_xe', 'nhan_vien_quay_ve', 'nhan_vien_gui_hang', 'dieu_do_vien')` — kiểm tra ở Service, không phải cột riêng.

### 4.2. `ho_so_can_bo_diem` (đã có, `DATABASE.md` mục 1.3)
Cần khi tạo tài khoản 3 trong 4 vai trò (`nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien`) — bắt buộc gán `van_phong_id`. Riêng `phu_xe` **không** dùng bảng này (gắn với xe qua `xe_nhan_su`, không gắn văn phòng).

### 4.3. `xe_nhan_su` (đã có, `DATABASE.md` mục 1.5)
`quan_ly_nhan_su` chỉ **đọc** bảng này (không sửa — biên chế là việc của `quan_ly`, UC-35), dùng để: khi cho nghỉ việc (UC-49), tìm các dòng biên chế của người đó để hiển thị cảnh báo xe nào sắp thiếu người, và chuyển các dòng đó sang `trang_thai = 'tam_nghi'`.

### 4.4. `thong_bao` (đã có, `DATABASE.md` mục 6.1)
Dùng để gửi cảnh báo giấy tờ sắp hết hạn (UC-48) và cảnh báo thiếu biên chế khi cho nghỉ việc (UC-49) tới `quan_ly`/điều độ viên. Có thể thêm 2 cột tùy chọn `nhan_su_van_hanh_id`, `xe_id` (FK nullable) để bấm vào thông báo nhảy thẳng tới đúng hồ sơ/xe — không bắt buộc, nội dung chữ trong `noi_dung` vẫn đủ dùng nếu không thêm.

---

## 5. Sơ đồ quan hệ (trong phạm vi file này)

```
nguoi_dung 0──1 nhan_su_van_hanh        (nguoi_dung_id — chỉ khi chuc_danh = phu_xe)
nhan_su_van_hanh 1──N giay_to_nhan_su   (tối đa 1 dòng mỗi loai)
nhan_su_van_hanh 1──N xe_nhan_su        (tham chiếu, không đổi — DATABASE.md mục 1.5)

nguoi_dung(quan_ly_nhan_su) 1──N nhat_ky_quan_ly_nhan_su
nhat_ky_quan_ly_nhan_su ⇢ nguoi_dung     (doi_tuong_id, khi doi_tuong_loai = 'nguoi_dung')
nhat_ky_quan_ly_nhan_su ⇢ nhan_su_van_hanh (doi_tuong_id, khi doi_tuong_loai = 'nhan_su_van_hanh')

ho_so_can_bo_diem N──1 diem_don_tra     (tham chiếu, không đổi — DATABASE.md mục 1.3)

nhan_su_van_hanh 0──N thong_bao         (tùy chọn, nếu thêm cột)
xe 0──N thong_bao                       (tùy chọn, nếu thêm cột)
```

Lưu ý: `doi_tuong_id` của `nhat_ky_quan_ly_nhan_su` không đặt `FOREIGN KEY` cứng tới 1 bảng cụ thể (vì trỏ tới 2 bảng khác nhau tùy `doi_tuong_loai`, giống cách `nhat_ky_admin` đã làm) — toàn vẹn dữ liệu kiểm tra ở Service.

---

## 6. Cần chốt với nhóm trước khi migrate thật

- **⚠️ Việc lưu ảnh (`anh_ho_so`, `anh_giay_to`) cần hạ tầng mà `ARCHITECTURE.md` đã chủ động bỏ** (mục 0.2) — **đã có đề xuất cụ thể**: dùng lại **Cloudinary**, chỉ riêng cho ảnh hồ sơ nhân sự vận hành (không mở rộng mục đích khác ở đợt này). Lý do: không nên lưu trên ổ đĩa backend vì Render/Fly.io free tier có ổ đĩa tạm thời, dữ liệu mất sau mỗi lần redeploy; Cloudinary có free tier phù hợp quy mô BTL và hỗ trợ delivery kiểu `authenticated` (URL có chữ ký) hợp với ảnh giấy tờ nhạy cảm. Đoạn dán cụ thể để thay dòng "File/ảnh" ở `ARCHITECTURE.md` mục 1 đã viết sẵn ở `NHAP_QUAN_LY_NHAN_SU.md` mục 3.0 — cần cả nhóm đồng ý trước khi dán, vì đây là quyết định kiến trúc chung, không riêng phần quản lý nhân sự.
- **Ngưỡng cảnh báo giấy tờ (mặc định 30 ngày, UC-48)**: `DATABASE.md` hiện chưa có bảng lưu tham số cấu hình nào (các ngưỡng 6 tiếng, 48 tiếng, no-show... cũng đang là hằng số, chưa có bảng). Tạm để trong `backend/app/config.py` cho tới khi nhóm chốt chỗ lưu chung.
- **`so_cccd` có nên `UNIQUE`?** Nếu có, cần `UNIQUE ... WHERE so_cccd IS NOT NULL` (partial index, vì nhiều dòng `NULL` không nên xung đột nhau).
- Việc **cho nghỉ việc (UC-49)** nên chạy trong 1 transaction duy nhất: đặt `nhan_su_van_hanh.trang_thai`, khóa `nguoi_dung.dang_hoat_dong` (nếu là phụ xe), chuyển `xe_nhan_su.trang_thai` sang `tam_nghi`, và ghi `nhat_ky_quan_ly_nhan_su` — hoặc cả 4 cùng thành công, hoặc không làm gì.
