# Thiết kế cơ sở dữ liệu — phạm vi Điều độ viên (`dieu_do_vien`, người 4)

> File riêng, phạm vi hẹp — cùng tinh thần với `database_quanLyNhanSu.md`: chỉ các bảng người 4 **sở hữu thật sự** theo `CONTRIBUTING.md` mục 2 (`chuyen_xe_repository`, `chuyen_xe_service`) phục vụ đúng 6 UC được giao (19, 20, 39, 44, 45, 40 — `CONTRIBUTING.md` mục 2), cộng với các bảng **chỉ đọc/tham chiếu** thuộc domain người khác mà điều độ viên cần dùng. Không phải bản thay thế `DATABASE.md` — 2 bảng chính ở mục 1–2 đã có sẵn nguyên văn ở `DATABASE.md` mục 3.3/3.4, gom lại đây chỉ để tiện đọc trong đúng phạm vi của vai trò này. Quy ước chung (UUID PK, `TIMESTAMPTZ`, enum bằng `TEXT + CHECK`, không xóa cứng) giữ nguyên như `DATABASE.md` mục 0 — không nhắc lại.

---

## 0. Vài điều cần đọc trước

**1. Ranh giới sở hữu (quan trọng nhất file này).** Theo `CONTRIBUTING.md` mục 2 và mục 5.6:

| Bảng | Ai sở hữu | Điều độ viên được làm gì |
|---|---|---|
| `chuyen_xe` | **Người 4 (điều độ viên)** — chủ file `chuyen_xe_repository.py`/`chuyen_xe_service.py` | Đọc + ghi (gán xe, đổi xe, đổi trạng thái, cờ hoãn/xung đột vị trí) |
| `lich_su_diem_dung_chuyen` | **Người 4** — cùng `chuyen_xe_service` | Ghi qua `xac_nhan_toi_diem()` (được người 3/phụ xe gọi vào, không tự viết SQL) |
| `xe`, `xe_nhan_su`, `loai_xe` | **Người 1 (Trưởng nhóm)** | **Chỉ đọc** — dùng để lọc "xe đủ điều kiện" (UC-44) và suy ra tài xế/phụ xe hiển thị, không tự sửa cấu trúc hay ghi đè |
| `tuyen`, `tuyen_diem_don_tra`, `nhom_tuyen`, `khu_vuc`, `diem_don_tra` | **Người 1** | **Chỉ đọc** — dùng cho ràng buộc vị trí xe (mục 3.3 `NGHIEP_VU.md`) và hiển thị lộ trình |
| `lich_chay_dinh_ky` | **Người 1** | **Chỉ đọc** — `jobs/sinh_chuyen_dinh_ky.py` (UC-18, do người 4 viết job nhưng đọc dữ liệu của người 1) dùng làm khuôn sinh `chuyen_xe` |
| `ve` | **Người 2** | **Không tự viết SQL** — chỉ gọi `ve_repository.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)` khi cần tìm vé bị ảnh hưởng lúc chuyến `da_huy` (UC-19/21) |
| `lich_su_hoan_tien` | **Người 5** | **Không chạm** — điều độ viên chỉ gọi `hoan_tien_service.tao_hoan_tien(ve_id, ly_do)`, không tự insert |
| `thong_bao` | Hạ tầng dùng chung (người 1 dựng `websocket_manager`) | Chỉ gọi `broadcast(...)`, không tự viết SQL cho bảng này |

**2. Vì sao file này vẫn có `CREATE TABLE` cho cả bảng không sở hữu?** Tính đến lúc viết file này, migration cho `xe`/`xe_nhan_su`/`loai_xe`/`tuyen`/`khu_vuc`/`diem_don_tra`/`lich_chay_dinh_ky` **chưa gộp vào nhánh này** (đang nằm rải rác ở các nhánh riêng của Trưởng nhóm/Vanh, xem `git branch -a`) — nhưng `chuyen_xe` **phụ thuộc khóa ngoại vào tất cả các bảng đó**, không thể migrate/test `chuyen_xe_service` nếu thiếu. Cách xử lý giống hệt tiền lệ đã làm với `nhan_su_van_hanh` ở `database_quanLyNhanSu.md` mục 0.2 và migration `20260927_1000_...sql`: viết 1 migration **tạm thời** dựng đúng các bảng đó (đủ cột theo `DATABASE.md`, không thêm/bớt gì) để tự test UC-19/20/39/40/44/45 ngay trên nhánh này — xem cảnh báo ⚠️ ngay đầu file migration tương ứng (mục 4 dưới). **Trước khi merge, phải đối chiếu với migration thật của Trưởng nhóm** — nếu trùng `CREATE TABLE`, xóa phần tạm này đi.

**3. Sai khác có chủ đích với `DATABASE.md` mục 9** (dòng "Cơ chế hoãn... job UC-45 nên gộp chung vào đúng `jobs/quet_het_han.py`"): `CONTRIBUTING.md` mục 5.2 đã **chốt lại** — mỗi người viết job riêng để tránh nhiều người cùng sửa 1 file, nên UC-45 nằm ở `jobs/quet_chua_gan_xe.py` (người 4 tự viết, tự đăng ký lịch chạy trong `main.py`), **không** gộp vào file chung. File này đi theo quyết định của `CONTRIBUTING.md` (mới hơn).

---

## 1. `chuyen_xe` — bảng trung tâm của điều độ viên

Nguyên văn từ `DATABASE.md` mục 3.3, không đổi cột nào — liệt kê lại để có ngữ cảnh đầy đủ khi đọc cùng mục 3 (giá trị suy luận) và mục 4 (constraint mà Service phải tự kiểm tra) dưới đây.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `xe_id` | UUID NULLABLE, FK → `xe(id)` | **Xe gốc** — quyết định biên chế tài xế/phụ xe và vị trí suy luận cho các chuyến sau. `NULL` = chưa gán xe (UC-44); tới `gio_khoi_hanh` mà vẫn `NULL` → job tự bật `dang_hoan` (UC-45) |
| `loai_xe_id` | UUID NOT NULL, FK → `loai_xe(id)` | Loại xe **cam kết** (copy từ `lich_chay_dinh_ky.loai_xe_id` lúc sinh chuyến) — Service bắt buộc `xe.loai_xe_id = chuyen_xe.loai_xe_id` khi gán `xe_id` |
| `lich_chay_dinh_ky_id` | UUID NULLABLE, FK → `lich_chay_dinh_ky(id)` | Lịch định kỳ đã sinh ra chuyến này |
| `xe_thuc_te_id` | UUID NULLABLE, FK → `xe(id)` | Phương tiện thực sự chạy nếu khác `xe_id` (UC-20, đổi xe khi hỏng). `NULL` = đúng xe gốc. Bắt buộc cùng `loai_xe` với `xe_id` |
| `gio_khoi_hanh` | TIMESTAMPTZ NOT NULL | |
| `trang_thai` | TEXT NOT NULL DEFAULT `'chua_khoi_hanh'`, CHECK IN (`chua_khoi_hanh`, `dang_chay`, `gap_su_co`, `hoan_thanh`, `da_huy`) | Không có trạng thái "hủy vì ít khách"/"hoãn" riêng — hoãn chỉ là `dang_hoan = true` trong khi vẫn `chua_khoi_hanh` |
| `dang_hoan` | BOOLEAN NOT NULL DEFAULT false | `true` khi đang chờ tìm xe trước giờ chạy — 2 nguồn: điều độ viên bật thủ công (UC-20) hoặc job tự bật (UC-45 ⏱) |
| `gio_xac_nhan_xuat_phat` | TIMESTAMPTZ NULLABLE | Do phụ xe xác nhận (người 3 gọi vào `chuyen_xe_service`) |
| `gio_hoan_thanh` | TIMESTAMPTZ NULLABLE | |
| `loai_su_co` | TEXT NULLABLE, CHECK IN (`loi_nha_xe`, `loi_khach_quan`) | Set khi chuyển `gap_su_co` (UC-17, người 3 gọi vào) — quyết định toàn bộ nhánh xử lý ở UC-19 |
| `ly_do_su_co` | TEXT NULLABLE | Mô tả sự cố hoặc lý do đang hoãn |
| `co_canh_bao_xung_dot_vi_tri` | BOOLEAN NOT NULL DEFAULT false | Bật cho mọi chuyến `chua_khoi_hanh` cùng `xe_id` ngay khi 1 chuyến trước của xe này chuyển `gap_su_co` — điều độ viên gỡ thủ công sau khi xem lại (UC-19/UC-20) |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Không có constraint DB nào cho** "không trùng lịch", "đúng vị trí xe", "đúng nhóm tuyến", "cùng `loai_xe` khi gán `xe_thuc_te_id`" — toàn bộ 4 ràng buộc này nằm ở `chuyen_xe_service`, xem mục 4.

---

## 2. `lich_su_diem_dung_chuyen`

Nguyên văn `DATABASE.md` mục 3.4 — ghi giờ thực tế phụ xe xác nhận tới từng điểm, dùng để cập nhật ETA cho khách đang chờ ở các điểm phía sau (UC-16, người 3 gọi vào `chuyen_xe_service.xac_nhan_toi_diem()`).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `chuyen_id` | UUID NOT NULL, FK → `chuyen_xe(id)` | |
| `diem_don_tra_id` | UUID NOT NULL, FK → `diem_don_tra(id)` | Phải thuộc đúng tuyến của chuyến (`tuyen_diem_don_tra`) — kiểm tra ở Service |
| `gio_thuc_te` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

`UNIQUE (chuyen_id, diem_don_tra_id)` — 1 điểm chỉ ghi nhận đúng 1 lần tới cho mỗi chuyến.

---

## 3. Giá trị suy luận — "luật chơi" thật sự của điều độ viên

Trích đúng các dòng liên quan từ `DATABASE.md` mục 7 (giá trị tính động, không lưu cột riêng) — đây là phần khó nhất của `chuyen_xe_service`, không phải constraint DB nào diễn tả được:

| Giá trị | Cách tính | Dùng ở UC |
|---|---|---|
| Vị trí dự kiến của 1 xe gốc tại 1 thời điểm | Không có `chuyen_xe` nào (`xe_id` khớp) kết thúc trước thời điểm xét → `xe.diem_goc_id`. Ngược lại → điểm cuối cùng (`thu_tu` lớn nhất, luôn `van_phong`) trong `tuyen_diem_don_tra` của `chuyen_xe` gần nhất (`gio_khoi_hanh`) đã kết thúc trước đó. Tính theo `xe_id`, **không phải** `xe_thuc_te_id` | UC-44 (điểm khởi hành chuyến mới phải trùng đúng vị trí này) |
| Phương tiện vật lý thật sự chạy 1 chuyến | `COALESCE(chuyen_xe.xe_thuc_te_id, chuyen_xe.xe_id)` | UC-20 (hiển thị biển số cho khách) |
| "Chuyến của tôi" của 1 phụ xe (chỉ để hiển thị cho họ, điều độ viên không thao tác) | `chuyen_xe` có `xe_id` khớp 1 dòng `xe_nhan_su(nhan_su_van_hanh_id = X, trang_thai = 'dang_hoat_dong')` tại thời điểm truy vấn | Tham chiếu — dùng khi điều độ viên xem "ai đang chạy chuyến này" |
| Tỷ lệ lấp đầy ghế | `COUNT(ve active)` / tổng ghế trong `loai_xe.so_do_ghe` của `chuyen_xe.loai_xe_id` — **chỉ để thống kê**, không dùng để hủy chuyến | UC-39 |

**Ràng buộc gán xe (UC-44, kiểm tra ở Service theo thứ tự, không phải constraint DB):**
1. `xe.trang_thai = 'hoat_dong'` (không phải `bao_tri`/`ngung_su_dung`).
2. `xe.loai_xe_id = chuyen_xe.loai_xe_id`.
3. Nếu `xe.nhom_tuyen_id IS NOT NULL` → phải trùng đúng `tuyen.nhom_tuyen_id` của chuyến.
4. Không trùng khung giờ với chuyến khác đã gán cho xe này (giờ khởi hành + thời gian di chuyển dự kiến + thời gian nghỉ quay đầu tối thiểu).
5. Điểm khởi hành của chuyến mới = vị trí dự kiến của xe tại giờ khởi hành đó (dòng đầu bảng trên).

**Ràng buộc đổi xe thực tế (UC-20, `xe_thuc_te_id`):** cùng `loai_xe` với `xe_id` gốc, đúng vị trí + không trùng lịch **riêng của xe thay thế** (không kiểm tra lại 4 điều kiện của `xe_id` gốc, vì `xe_id` không đổi).

---

## 4. Migration — file nào tạo bảng nào

| File | Nội dung | Ghi chú |
|---|---|---|
| `backend/migrations/20260927_1100_tao_bang_danh_muc_xe_tuyen_tam_thoi.sql` | `khu_vuc`, `diem_don_tra`, `nhom_tuyen`, `tuyen`, `tuyen_diem_don_tra`, `loai_xe`, `xe`, `xe_nhan_su`, `lich_chay_dinh_ky` | ⚠️ **Tạm thời** — thuộc domain Trưởng nhóm (mục 0.1/0.2). Đối chiếu trước khi merge |
| `backend/migrations/20260927_1110_tao_bang_chuyen_xe_lich_su_diem_dung.sql` | `chuyen_xe`, `lich_su_diem_dung_chuyen` + index | Bảng thật sự của điều độ viên (người 4) — không cần đối chiếu ai khác, chỉ cần 2 bảng phụ thuộc ở trên đã tồn tại |

---

## 5. Sơ đồ quan hệ (trong phạm vi file này)

```
nhom_tuyen 1──N tuyen
tuyen 1──N tuyen_diem_don_tra N──1 diem_don_tra
khu_vuc 1──N diem_don_tra

diem_don_tra 1──1 xe            (diem_goc_id)
nhom_tuyen 0──N xe
loai_xe 1──N xe
nhan_su_van_hanh 1──N xe_nhan_su
xe 1──N xe_nhan_su

tuyen 1──N lich_chay_dinh_ky
loai_xe 1──N lich_chay_dinh_ky
lich_chay_dinh_ky 0──N chuyen_xe

xe 0──N chuyen_xe               (xe_id — xe gốc)
xe 0──N chuyen_xe               (xe_thuc_te_id — xe chạy thay)
loai_xe 1──N chuyen_xe          (loai_xe_id — loại xe cam kết)
tuyen 1──N chuyen_xe
chuyen_xe 1──N lich_su_diem_dung_chuyen N──1 diem_don_tra

chuyen_xe 1──N ve                (chỉ đọc qua ve_repository của người 2)
```

---

## 6. Cần chốt với nhóm trước khi migrate thật

- **Đối chiếu bảng tạm thời (mục 4 dòng 1) với migration thật của Trưởng nhóm** ngay khi migration đó xuất hiện trên `main` — nếu trùng `CREATE TABLE`, xóa file tạm này, giữ lại đúng file `chuyen_xe`/`lich_su_diem_dung_chuyen`.
- **Index bắt buộc** (theo `DATABASE.md` mục 9, đưa vào migration mục 4 dòng 2): `chuyen_xe(xe_id, gio_khoi_hanh)`, `chuyen_xe(xe_id) WHERE xe_thuc_te_id IS NOT NULL` (UC-40 — liệt kê nhanh chuyến đang chạy thay), `chuyen_xe(xe_id) WHERE xe_id IS NULL` (UC-44 — danh sách chuyến cần gán xe).
- **`co_canh_bao_xung_dot_vi_tri` không tự gỡ** — chỉ điều độ viên xem lại thủ công mới gỡ được (mục 3.3 `NGHIEP_VU.md`), Service không có job tự động tắt cờ này.
- **Job `jobs/quet_chua_gan_xe.py` (UC-45)** và **`jobs/sinh_chuyen_dinh_ky.py` (UC-18)** đều thuộc người 4 viết code, nhưng đọc dữ liệu (`lich_chay_dinh_ky`) của người 1 — chỉ đọc, không sửa cấu trúc bảng đó.
