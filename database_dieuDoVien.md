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
| `tuyen`, `tuyen_diem_don_tra`, `khu_vuc`, `diem_don_tra` | **Người 1** | **Chỉ đọc** — dùng cho ràng buộc vị trí xe (mục 3.3 `NGHIEP_VU.md`) và hiển thị lộ trình. Mỗi `tuyen` chạy được cả 2 chiều; **không còn bảng `nhom_tuyen`** (`DATABASE.md` mục 2.3) |
| `lich_chay_dinh_ky` | **Người 1** | **Chỉ đọc** — `quan_ly` thiết lập (UC-18) và tự bấm "Sinh chuyến" (UC-47); **không còn job nền** sinh chuyến. Điều độ viên chỉ nhận các chuyến đã sinh sẵn để gán xe (UC-44) |
| `ve` | **Người 2** | **Không tự viết SQL** — chỉ gọi `ve_repository.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)` khi cần tìm vé bị ảnh hưởng lúc chuyến `da_huy` (UC-19) |
| `lich_su_hoan_tien` | **Người 5** | **Không chạm** — điều độ viên chỉ gọi `hoan_tien_service.tao_hoan_tien(ve_id, ly_do)`, không tự insert |
| `thong_bao` | Hạ tầng dùng chung (người 1 dựng `websocket_manager`) | Chỉ gọi `broadcast(...)`, không tự viết SQL cho bảng này |

**2. Migration.** Các bảng danh mục (`khu_vuc`, `diem_don_tra`, `tuyen`, `tuyen_diem_don_tra`, `loai_xe`, `xe`, `xe_nhan_su`, `lich_chay_dinh_ky`) đã do Trưởng nhóm tạo trong migration thật; **không còn migration tạm** nào (bản nháp cũ nhắc tới `..._tam_thoi.sql` đã bỏ). `chuyen_xe` đã được mở rộng thêm `loai_xe_id`, `lich_chay_dinh_ky_id`, `chieu`, `ma` — xem mục 4.

**3. Sai khác có chủ đích với `DATABASE.md` mục 9** (dòng "Cơ chế hoãn... job UC-44 nên gộp chung vào đúng `jobs/quet_het_han.py`"): `CONTRIBUTING.md` mục 5.2 đã **chốt lại** — mỗi người viết job riêng để tránh nhiều người cùng sửa 1 file, nên UC-44 nằm ở `jobs/quet_chua_gan_xe.py` (người 4 tự viết, tự đăng ký lịch chạy trong `main.py`), **không** gộp vào file chung. File này đi theo quyết định của `CONTRIBUTING.md` (mới hơn). **Hiện chưa viết** — `backend/app/jobs/` mới có `quet_no_show.py` và `quet_hang_ton.py`.

---

## 1. `chuyen_xe` — bảng trung tâm của điều độ viên

Theo `DATABASE.md` mục 3.3 (đã gồm `ma`, `chieu`) — liệt kê lại để có ngữ cảnh đầy đủ khi đọc cùng mục 3 (giá trị suy luận) và mục 4 (constraint mà Service phải tự kiểm tra) dưới đây.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `ma` | TEXT NOT NULL UNIQUE | Mã tự sinh `<mã tuyến>-<mã loại xe>-<yymmdd>-<hhmm>-<DI\|VE>` (trigger, `DATABASE.md` mục 10). Chỉ tính lại khi `quan_ly` sửa giờ (UC-48); điều độ viên dời giờ lúc `dang_hoan` **giữ nguyên mã** |
| `tuyen_id` | UUID NOT NULL, FK → `tuyen(id)` | |
| `chieu` | TEXT NOT NULL, CHECK IN (`xuoi`, `nguoc`) | Chiều chạy của đúng lần chạy này (copy từ `lich_chay_dinh_ky.chieu`) — quyết định thứ tự điểm dừng hiệu lực và vị trí kết thúc của chuyến |
| `xe_id` | UUID NULLABLE, FK → `xe(id)` | **Xe gốc** — quyết định biên chế tài xế/phụ xe và vị trí suy luận cho các chuyến sau. `NULL` = chưa gán xe (UC-44); tới `gio_khoi_hanh` mà vẫn `NULL` → job tự bật `dang_hoan` (UC-44) |
| `loai_xe_id` | UUID NOT NULL, FK → `loai_xe(id)` | Loại xe **cam kết** (copy từ `lich_chay_dinh_ky.loai_xe_id` lúc sinh chuyến) — Service bắt buộc `xe.loai_xe_id = chuyen_xe.loai_xe_id` khi gán `xe_id` |
| `lich_chay_dinh_ky_id` | UUID NULLABLE, FK → `lich_chay_dinh_ky(id)` | Lịch định kỳ đã sinh ra chuyến này |
| `xe_thuc_te_id` | UUID NULLABLE, FK → `xe(id)` | Phương tiện thực sự chạy nếu khác `xe_id` (UC-20, đổi xe khi hỏng). `NULL` = đúng xe gốc. Bắt buộc cùng `loai_xe` với `xe_id` |
| `gio_khoi_hanh` | TIMESTAMPTZ NOT NULL | |
| `trang_thai` | TEXT NOT NULL DEFAULT `'chua_khoi_hanh'`, CHECK IN (`chua_khoi_hanh`, `dang_chay`, `gap_su_co`, `hoan_thanh`, `da_huy`) | Không có trạng thái "hủy vì ít khách"/"hoãn" riêng — hoãn chỉ là `dang_hoan = true` trong khi vẫn `chua_khoi_hanh` |
| `dang_hoan` | BOOLEAN NOT NULL DEFAULT false | `true` khi đang chờ tìm xe trước giờ chạy — 2 nguồn: điều độ viên bật thủ công (UC-20) hoặc job tự bật (UC-44 ⏱) |
| `gio_xac_nhan_xuat_phat` | TIMESTAMPTZ NULLABLE | Do phụ xe xác nhận (người 3 gọi vào `chuyen_xe_service`) |
| `gio_hoan_thanh` | TIMESTAMPTZ NULLABLE | |
| `loai_su_co` | TEXT NULLABLE, CHECK IN (`loi_nha_xe`, `loi_khach_quan`) | Set khi chuyển `gap_su_co` (UC-17, người 3 gọi vào) — quyết định toàn bộ nhánh xử lý ở UC-19 |
| `ly_do_su_co` | TEXT NULLABLE | Mô tả sự cố hoặc lý do đang hoãn |
| `co_canh_bao_xung_dot_vi_tri` | BOOLEAN NOT NULL DEFAULT false | Bật cho mọi chuyến `chua_khoi_hanh` cùng `xe_id` ngay khi 1 chuyến trước của xe này chuyển `gap_su_co` — điều độ viên gỡ thủ công sau khi xem lại (UC-19/UC-20) |
| `ngay_tao` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Không có constraint DB nào cho** "không trùng lịch", "đúng vị trí xe", "đúng nhóm tuyến", "cùng `loai_xe` khi gán `xe_thuc_te_id`" — toàn bộ 4 ràng buộc này nằm ở `chuyen_xe_service`, xem mục 4.

---

## 2. `lich_su_diem_dung_chuyen`

Nguyên văn `DATABASE.md` mục 3.4 — ghi giờ thực tế phụ xe xác nhận tới từng điểm, dùng để cập nhật ETA cho khách đang chờ ở các điểm phía sau (UC-15, người 3 gọi vào `chuyen_xe_service.xac_nhan_toi_diem()`).

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
| Vị trí dự kiến của 1 xe gốc tại 1 thời điểm | Không có `chuyen_xe` nào (`xe_id` khớp) kết thúc trước thời điểm xét → `xe.diem_goc_id`. Ngược lại → điểm cuối cùng theo hướng chạy của `chuyen_xe` gần nhất (`gio_khoi_hanh`) đã kết thúc trước đó: **`thu_tu` lớn nhất nếu `chieu = xuoi`, nhỏ nhất nếu `chieu = nguoc`** (luôn `van_phong` ở cả 2 trường hợp). Tính theo `xe_id`, **không phải** `xe_thuc_te_id` | UC-44 (điểm khởi hành chuyến mới phải trùng đúng vị trí này) |
| Phương tiện vật lý thật sự chạy 1 chuyến | `COALESCE(chuyen_xe.xe_thuc_te_id, chuyen_xe.xe_id)` | UC-20 (hiển thị biển số cho khách) |
| "Chuyến của tôi" của 1 phụ xe (chỉ để hiển thị cho họ, điều độ viên không thao tác) | `chuyen_xe` có `xe_id` khớp 1 dòng `xe_nhan_su(nhan_su_van_hanh_id = X, trang_thai = 'dang_hoat_dong')` tại thời điểm truy vấn | Tham chiếu — dùng khi điều độ viên xem "ai đang chạy chuyến này" |
| Tỷ lệ lấp đầy ghế | `COUNT(ve active)` / tổng ghế trong `loai_xe.so_do_ghe` của `chuyen_xe.loai_xe_id` — **chỉ để thống kê**, không dùng để hủy chuyến | UC-39 |
| Chuyến chưa gán xe | `xe_id IS NULL` — vẫn bán vé theo `loai_xe_id`; chưa có vị trí suy luận. Tới `gio_khoi_hanh` mà còn `NULL` → bật `dang_hoan` (UC-44) | UC-44 |

**Ràng buộc gán xe (UC-44, kiểm tra ở Service theo thứ tự, không phải constraint DB):**
1. `xe.trang_thai = 'hoat_dong'` (không phải `bao_tri`/`ngung_su_dung`).
2. `xe.loai_xe_id = chuyen_xe.loai_xe_id`.
3. Nếu `xe.tuyen_id IS NOT NULL` → phải trùng đúng `chuyen_xe.tuyen_id` (xe cố định chạy được cả 2 chiều của tuyến đó).
4. Không trùng khung giờ với chuyến khác đã gán cho xe này (giờ khởi hành + thời gian di chuyển dự kiến + thời gian nghỉ quay đầu tối thiểu).
5. Điểm khởi hành của chuyến mới = vị trí dự kiến của xe tại giờ khởi hành đó (dòng đầu bảng trên).

**Ràng buộc đổi xe thực tế (UC-20, `xe_thuc_te_id`):** cùng `loai_xe` với `xe_id` gốc, đúng vị trí + không trùng lịch **riêng của xe thay thế** (không kiểm tra lại 4 điều kiện của `xe_id` gốc, vì `xe_id` không đổi).

---

## 4. Migration — file nào tạo bảng nào

| File | Nội dung |
|---|---|
| `20260920_1600_tao_bang_gui_hang_va_hoan_tien.sql` | Tạo `chuyen_xe` (bản đầu) |
| `20260920_1810_bo_sung_chuyen_xe_cho_phu_xe.sql` | Bổ sung cột cho phụ xe (`gio_xac_nhan_xuat_phat`...), tạo `lich_su_diem_dung_chuyen` |
| `20260927_1100_tao_bang_xe_nhan_su_lich_chay_dinh_ky.sql` | `xe_nhan_su`, `lich_chay_dinh_ky`; thêm `chuyen_xe.loai_xe_id`, `lich_chay_dinh_ky_id`; index `chuyen_xe(xe_id)`... |
| `20260927_1110_tao_bang_chuyen_xe_lich_su_diem_dung.sql` | Chỉnh ràng buộc/index của `chuyen_xe` và `lich_su_diem_dung_chuyen` cho điều độ viên |
| `20260928_1000_bo_nhom_tuyen_gop_vao_tuyen.sql` | Bỏ `nhom_tuyen`; `xe.nhom_tuyen_id` → `xe.tuyen_id`; thêm `chuyen_xe.chieu` |
| `20260930_1000_them_ma_tu_sinh.sql`, `20260930_1100_ma_chuyen_doi_theo_gio.sql` | `chuyen_xe.ma` tự sinh |

## 5. Sơ đồ quan hệ (trong phạm vi file này)

```
tuyen 1──N tuyen_diem_don_tra N──1 diem_don_tra
khu_vuc 1──N diem_don_tra

diem_don_tra 1──1 xe            (diem_goc_id)
tuyen 0──N xe                   (xe cố định theo tuyến, NULL = xe dự phòng)
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

## 6. Đã chốt và còn lại

- **Index** đã có trong migration: `chuyen_xe(xe_id, gio_khoi_hanh)`, `chuyen_xe(xe_id) WHERE xe_thuc_te_id IS NOT NULL` (UC-20), `chuyen_xe(xe_id) WHERE xe_id IS NULL` (UC-44).
- **`co_canh_bao_xung_dot_vi_tri` không tự gỡ** — chỉ điều độ viên xem lại thủ công mới gỡ được (mục 3.3 `NGHIEP_VU.md`).
- **Job `jobs/quet_chua_gan_xe.py` (UC-44)**: người 4 viết, **chưa có**. **Không còn job `sinh_chuyen_dinh_ky.py`** — sinh chuyến là thao tác thủ công của `quan_ly` (UC-47).
