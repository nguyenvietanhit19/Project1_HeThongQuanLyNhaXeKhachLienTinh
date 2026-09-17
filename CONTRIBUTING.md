# Hướng dẫn chia việc & làm việc nhóm (CONTRIBUTING)

Tài liệu này mô tả cách nhóm 5 người chia việc code cho nhau sao cho **chuyên nghiệp**, **mỗi người chỉ cần hiểu sâu đúng phần nghiệp vụ của mình**, và **ít xung đột nhất có thể trong phạm vi cho phép** — đọc trước khi bắt đầu code, cùng với 6 tài liệu nghiệp vụ/kỹ thuật đã có ở `README.md`.

---

## 1. Nguyên tắc chia việc: theo vai trò (role/nghiệp vụ)

Nhóm đã cân nhắc 2 cách:

1. **Chia theo domain (dọc theo bảng dữ liệu)** — 1 người sở hữu trọn 1 nhóm bảng (VD "tuyến/chuyến" thuộc 1 người, bất kể phục vụ vai trò nào). Ưu điểm: gần như zero conflict kỹ thuật. Nhược điểm đã gặp phải khi thử: 1 người phải làm nhiều giao diện khác phong cách hẳn nhau (khách hàng, quản lý, điều độ viên...), và phải hiểu nghiệp vụ của nhiều vai trò cùng lúc — khó cho người chưa nắm hết `NGHIEP_VU.md`.
2. **Chia theo vai trò (actor thật trong `UML_DIAGRAMS.md`)** — 1 người = 1-2 vai trò trọn vẹn, đúng như `NGHIEP_VU.md` mục 8 đã chia sẵn theo từng vai trò (8.1 Khách hàng, 8.2 Phụ xe, 8.6 Điều độ viên...). Mỗi người chỉ cần đọc kỹ đúng 1-2 mục 8.x liên quan tới mình, không phải hiểu toàn bộ nghiệp vụ hệ thống. **Chọn cách này.**

**Đánh đổi cần biết trước** (không né tránh): vài bảng dữ liệu (`ve`, `chuyen_xe`) bị nhiều vai trò khác nhau cùng cần đọc/sửa ở các giai đoạn khác nhau trong vòng đời của nó — VD Khách hàng đặt vé, Phụ xe xác nhận lên xe, Điều độ viên xử lý sự cố đều chạm `ve`/`chuyen_xe`. Cách xử lý: **đúng 1 người sở hữu file thật của bảng đó, người khác chỉ được gọi hàm có sẵn, không tự viết SQL/logic riêng** — chi tiết ở mục 5. Đây là phần quan trọng nhất tài liệu, đọc kỹ trước khi code bất kỳ chỗ nào đụng tới 2 bảng này.

---

## 2. 5 người & vai trò phụ trách

| # | Người | Vai trò | UC | Ghi chú |
|---|---|---|---|---|
| **1** | **Trưởng nhóm** | Đăng ký/Đăng nhập + toàn bộ **Quản lý** | 01,02,03,18,29,30,31,32,33,34,35,36,37,38,39 (15 UC) | Người tạo khu vực/điểm/tuyến/lịch chạy định kỳ/loại xe/giá vé/xe/biên chế/tài khoản — đúng người hiểu sâu nhất cấu trúc dữ liệu nền |
| **2** | | **Khách hàng + Nhân viên quầy vé** | 04,05,08,09,10,11,14,41,42 (9 UC) | Ôm luôn thuật toán chống trùng ghế (phần khó/nhạy cảm nhất hệ thống — xem mục 5.1) |
| **3** | | **Phụ xe** | 12,13,15,16,17,26,27,28,39 (9 UC) | Chỉ gọi hàm có sẵn từ người 1, 4, 5 — không tự viết logic |
| **4** | | **Điều độ viên** | 19,20,40,44,45,39 (6 UC) | |
| **5** | | **Nhân viên gửi hàng + Kế toán** | 21,22,23,24,25,43,46 (7 UC) | |

Tổng 44 UC (đúng số UC còn hiệu lực, UC-06/07 đã retire — xem `NGHIEP_VU.md` mục 11). UC-39 (thống kê) xuất hiện ở nhiều người vì mỗi vai trò chỉ xem đúng phạm vi của mình (`NGHIEP_VU.md` UC-39) — phần này nhẹ, không tính là điểm nóng.

### Chi tiết backend/frontend từng người

**1 — Đăng ký/đăng nhập + Quản lý** (Trưởng nhóm)
- Backend: `nguoi_dung_repository`, `mat_khau_service`, `tai_khoan_can_bo_service`, `email_service`, `auth_middleware`, `khu_vuc/diem_don_tra/tuyen_repository`, `lich_chay_dinh_ky_service`, `xe/loai_xe/gia_ve/xe_nhan_su_repository`, `websocket_manager` (hạ tầng, xem mục 5.3), routes: `auth.py`, `tai_khoan_can_bo.py`, `quan_ly.py`.
- Frontend: đăng ký/đăng nhập/quên mật khẩu (`frontend/khach-hang/`), toàn bộ `frontend/nhan-vien/quan-ly/`, và **`frontend/nhan-vien/shared/`** (nav, api-client, auth-check dùng chung cho mọi người).
- Cũng là người dựng **khung dự án ngày đầu tiên** — xem mục 5.4.

**2 — Khách hàng + Nhân viên quầy vé**
- Backend: `tim_kiem_chuyen_service` (UC-04), `ve_lock_repository` (thuật toán khóa ghế — mục 5.1), `ve_repository`, `dat_ve_service`, `thanh_toan_service`, `thanh_toan_callback.py`, `jobs/quet_ve_het_han.py` (UC-14), routes: `chuyen.py`, `ve.py`, `quay_ve.py`.
- Frontend: `frontend/khach-hang/` (tra cứu, chọn ghế, thanh toán, lịch sử vé), `frontend/nhan-vien/quay-ve/`.

**3 — Phụ xe**
- Backend: chỉ route `phu_xe.py` — **không tự viết logic**, chỉ gọi hàm có sẵn từ người 4 (`chuyen_xe_service`), người 2 (`ve_repository`), người 5 (`gui_hang_service`).
- Frontend: `frontend/nhan-vien/phu-xe/` (giao diện di động).

**4 — Điều độ viên**
- Backend: `chuyen_xe_repository`, `chuyen_xe_service` (vòng đời chuyến, vị trí xe, gán xe, đổi xe, sự cố), `jobs/sinh_chuyen_dinh_ky.py` (UC-18, đọc lịch định kỳ của người 1), `jobs/quet_chua_gan_xe.py` (UC-45), route `dieu_do.py`.
- Frontend: `frontend/nhan-vien/dieu-do/` (gán xe, xử lý sự cố, đổi xe).

**5 — Nhân viên gửi hàng + Kế toán**
- Backend: `don_hang_repository`, `gui_hang_service`, `lich_su_hoan_tien_repository`, `hoan_tien_service`, `jobs/quet_hang_ton.py` (UC-46), `jobs/quet_hoan_tien_tu_dong.py` (UC-43), routes: `gui_hang.py`, `ke_toan.py`.
- Frontend: `frontend/nhan-vien/gui-hang/`, `frontend/nhan-vien/ke-toan/`.

---

## 3. Sơ đồ phụ thuộc giữa 5 người — đọc kỹ trước khi bắt đầu

```
1 (auth, danh mục Quản lý) ──── nền tảng bắt buộc cho MỌI người, không phụ thuộc ai
   │
   ├──> 2 cần 1: đăng nhập, đọc gia_ve/loai_xe (tính giá, sơ đồ ghế),
   │           đọc tuyen_diem_don_tra (thu_tu — dùng cho thuật toán chống trùng ghế)
   ├──> 3 cần 1: đăng nhập
   ├──> 4 cần 1: đăng nhập, đọc xe/loai_xe (điều kiện gán xe), đọc tuyen_diem_don_tra (vị trí xe)
   └──> 5 cần 1: đăng nhập

2 (ve_lock, ve_repository) ──── bị 3 và 4 gọi vào
   │
   ├──> 3 GỌI 2: xác nhận lên/xuống xe (UC-12/13) — đổi ve.trang_thai
   └──> 4 GỌI 2: khi 1 chuyến bị hủy do sự cố khách quan (UC-19/21), cần tìm các vé
               đã trả tiền bị ảnh hưởng để chuyển hoàn tiền — 4 ĐỌC dữ liệu vé qua
               hàm của 2, không tự truy vấn bảng ve

4 (chuyen_xe_service) ──── bị 3 gọi vào, và tự gọi ngược lại 2 + 5
   │
   ├──> 3 GỌI 4: xác nhận xuất phát/tới điểm/báo sự cố (UC-15,16,17) —
   │           đổi chuyen_xe.trang_thai, 3 không tự viết SQL cho việc này
   └──> 4 GỌI 5: khi chuyến bị hủy do sự cố khách quan (UC-19/21), gọi
               hoan_tien_service.tao_hoan_tien() của 5 cho từng vé bị ảnh hưởng
               (5 chỉ tạo bản ghi hoàn tiền, không biết gì về xử lý sự cố)

2 (ve_repository) ──── bị 5 gọi vào khi khách hủy vé nhận hoàn
   │
   └──> 5 GỌI 2: khi khách hủy vé nhận hoàn (UC-41/42, do 2 tự xử lý là chính —
               xem ghi chú dưới) cần đổi ve.trang_thai = 'da_huy'

3 (phu_xe.py) ──── GỌI 5: xác nhận chất/dỡ hàng (UC-26/27) — nút bấm nằm trên
               màn hình 3 sở hữu (chuyen-dang-chay.html) nhưng gọi API của 5
```

**Ghi chú UC-41/42**: đây là 2 UC do Khách hàng/Quầy vé (người 2) chủ động thực hiện (mục 11 `NGHIEP_VU.md`), nên phần lớn logic (đổi `ve.trang_thai`, gọi tạo hoàn tiền) nằm gọn trong code của người 2 — người 2 tự gọi `hoan_tien_service` của người 5, không cần người 5 chủ động làm gì. Chỉ UC-21 (tự động, do sự cố khách quan — người 4 xác nhận) mới thực sự là người 4 chủ động gọi sang người 2 và người 5.

### Tóm tắt: ai phải xong trước, ai chỉ cần gọi hàm

| Người | Người khác phụ thuộc vào mình | Mình gọi vào người nào |
|---|---|---|
| 1 | 2, 3, 4, 5 đều cần đăng nhập; 2 và 4 còn cần đọc dữ liệu tuyến/xe/giá | Không gọi ai |
| 2 | 3 (đổi trạng thái vé), 4 (đọc vé bị ảnh hưởng), 5 (không — 5 không gọi 2) | Gọi 1 (auth, dữ liệu), gọi 5 (tạo hoàn tiền khi UC-41/42) |
| 3 | Không ai phụ thuộc 3 | Gọi 1 (auth), gọi 2, gọi 4, gọi 5 |
| 4 | 3 (đổi trạng thái chuyến) | Gọi 1 (auth, dữ liệu), gọi 2 (đọc vé), gọi 5 (tạo hoàn tiền) |
| 5 | 3 (chất/dỡ hàng) | Gọi 1 (auth) |

**Kết luận thứ tự làm việc**: **Người 1 đi trước tiên** (nền tảng đăng nhập + danh mục — xem mục 5.4). Sau đó **2 và 4 nên làm sớm** (vì 3 và 5 đều gọi vào 2/4 khá nhiều). **3 là người phụ thuộc nhiều nhất** (gọi cả 4 người kia) — nên để 3 làm sau cùng, hoặc dựng giao diện tĩnh trước rồi nối API sau (mục 9).

---

## 4. Trang HTML: chia theo màn hình thực tế dùng, không phải theo UC

**Không phải 1 UC = 1 file** — nhiều UC chỉ là 1 nút bấm nằm chung trên 1 màn hình đang mở. VD người 3 (phụ xe) lúc xe đang chạy chỉ mở **1 màn hình `chuyen-dang-chay.html`**, trên đó có đủ nút cho UC-12 (lên xe), UC-13 (xuống xe), UC-16 (tới điểm), UC-17 (báo sự cố), UC-26/27 (chất/dỡ hàng, gọi API người 5) — gộp nhiều UC vào 1 file vì đó là đúng cách phụ xe thao tác thực tế.

Nhờ chia theo vai trò, **mỗi người giờ chỉ cần dựng đúng 1-2 giao diện nhất quán** (không còn tình trạng 1 người phải làm 3 phong cách UI khác hẳn nhau như bản chia theo domain trước) — nhưng vẫn áp dụng nguyên tắc "chia theo màn hình thực tế dùng" ở trong phạm vi của từng người.

### Cấu trúc file gợi ý

```
frontend/khach-hang/
  dang-ky.html  dang-nhap.html  quen-mat-khau.html      # người 1
  tim-kiem.html  chon-ghe.html  thanh-toan.html  lich-su-ve.html   # người 2

frontend/nhan-vien/
  shared/              # người 1 dựng (nav, auth-check, api-client, css chung)
  quan-ly/             # người 1 — toàn bộ, không còn bị ai khác chạm
  quay-ve/             # người 2
  phu-xe/
    chuyen-dang-chay.html   # người 3 — gộp UC-12,13,16,17,26,27
    bao-that-lac.html       # người 3 — UC-28
  dieu-do/             # người 4
  gui-hang/  ke-toan/  # người 5
```

---

## 5. Các điểm dễ xảy ra conflict hoặc cần thống nhất "hợp đồng" (contract) trước khi code

### 5.1. Bảng `ve` bị nhiều người cùng chạm — tách file rõ ràng để không ai sửa nhầm phần người khác

- `ve_lock_repository.py` (**người 2 sở hữu duy nhất**) — đúng 1 hàm: `khoa_va_kiem_tra_trung_ghe(chuyen_id, so_ghe, diem_don_id, diem_tra_id)` — phần `SELECT ... FOR UPDATE` + kiểm tra overlap (`NGHIEP_VU.md` mục 6). Đây là phần khó/nhạy cảm nhất hệ thống — bug ở đây có thể gây bán trùng ghế thật. Tách file riêng dù chỉ 1 người dùng, để dễ viết `tests/integration` riêng cho đúng phần này.
- `ve_repository.py` (**người 2 sở hữu**) — mọi thứ còn lại của vé: đọc/tra cứu, đổi trạng thái (`da_thanh_toan`, `da_len_xe`, `khong_den`, `da_huy`...).

**Quy tắc**: người 3, 4, 5 chỉ gọi hàm người 2 cung cấp (`xac_nhan_len_xe()`, `xac_nhan_xuong_xe()`, `huy_ve_nhan_hoan()`, `tim_ve_da_thanh_toan_theo_chuyen()`), **không ai khác được tự viết SQL cho bảng `ve`**.

### 5.2. `jobs/` — mỗi người viết job riêng, KHÔNG dùng chung 1 file `quet_het_han.py`

Bản kế hoạch kỹ thuật gốc (`ARCHITECTURE.md`) gộp hết tác vụ định kỳ vào 1 file — nếu giữ vậy, nhiều người cùng phải sửa chung 1 file → đúng kiểu rủi ro "merge sạch nhưng logic dẫm chân nhau" ở mục 1. **Đổi cách chia**: mỗi người viết 1 file job riêng, tự đăng ký lịch chạy độc lập trong `main.py`:

```
jobs/quet_ve_het_han.py          # người 2 — UC-14 (no-show, hết hạn giữ chỗ)
jobs/sinh_chuyen_dinh_ky.py      # người 4 — UC-18 (đọc lich_chay_dinh_ky của người 1)
jobs/quet_chua_gan_xe.py         # người 4 — UC-45 (dang_hoan khi chưa gán xe)
jobs/quet_hang_ton.py            # người 5 — UC-46
jobs/quet_hoan_tien_tu_dong.py   # người 5 — UC-43 (chỉ ĐỌC chuyen_xe của người 4, tự ghi bảng của mình)
```

### 5.3. `websocket_manager.py` — hạ tầng dùng chung, xây 1 lần, không ai sửa lại

Người 1 xây file này lúc dựng khung dự án (mục 5.4), với 1 hàm duy nhất kiểu `broadcast(nguoi_dung_id, noi_dung)`. Các người khác chỉ **gọi hàm này**, không sửa file — giống hệt cách dùng `auth_middleware`.

### 5.4. `main.py`, `db.py`, `config.py`, migration đầu tiên — người 1 dựng khung dự án ngày đầu tiên

Người 1 dựng bộ khung này trong buổi làm việc đầu tiên (vì cần bảng `nguoi_dung` + tài khoản `quan_ly` gốc sớm nhất — `DATABASE.md` mục 9): `docker-compose.yml`, `Dockerfile`, migration `0001_init_schema.sql` (kèm `CREATE EXTENSION pgcrypto`, seed tài khoản `quan_ly` gốc), `main.py`/`db.py`/`config.py` cơ bản chạy được `"OK"`. Sau đó **`main.py` chỉ còn bị chạm để thêm 1 dòng `include_router(...)`** mỗi khi 1 người xong route đầu tiên — luôn thêm cuối danh sách, gần như không conflict.

### 5.5. Sidebar/khung giao diện dùng chung

Người 1 dựng `shared/nav-*.js` (mảng link, mỗi người tự thêm entry vào cuối mảng, không sửa dòng người khác). Vì giờ mỗi người có khu vực riêng biệt trong `frontend/nhan-vien/` (mục 4), việc này chỉ còn cần cho thanh điều hướng chung, không còn tình trạng 2 người cùng viết trang trong 1 thư mục như bản chia theo domain trước.

### 5.6. Thống nhất chữ ký hàm (function signature) TRƯỚC khi code

Vì 3/4/5 sẽ gọi hàm của 1/2/4 — **thống nhất tên hàm + tham số + kiểu trả về ngay từ đầu tuần 1** (viết ra giấy/Discord/Notion, chưa cần code thật). Tối thiểu cần chốt trước:

- `chuyen_xe_service.xac_nhan_xuat_phat(chuyen_id)`, `.xac_nhan_toi_diem(chuyen_id, diem_id)`, `.bao_su_co(chuyen_id, loai_su_co, ly_do)` (người 4 cung cấp cho người 3).
- `ve_lock_repository.khoa_va_kiem_tra_trung_ghe(...)` (nội bộ người 2 dùng, không ai khác gọi).
- `ve_repository.xac_nhan_len_xe(ve_id)`, `.xac_nhan_xuong_xe(ve_id)`, `.huy_ve_nhan_hoan(ve_id, ly_do)`, `.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)` (người 2 cung cấp cho người 3 và người 4).
- `hoan_tien_service.tao_hoan_tien(ve_id, ly_do)` (người 5 cung cấp cho người 2 và người 4).
- `gui_hang_service.xac_nhan_chat_hang(don_hang_id, chuyen_id)` (người 5 cung cấp cho người 3).

---

## 6. Tái sử dụng UI mà không cần framework ("component" viết tay)

Dự án dùng HTML/CSS/JS tĩnh, chưa cần framework (`ARCHITECTURE.md` mục 3) — nhưng vẫn nên tránh copy-paste UI lặp lại, bằng 2 kỹ thuật JS thuần:

1. **HTML partial qua `fetch()`** — cho phần tĩnh giống hệt nhau mọi nơi (nav, header, footer). Người 1 dựng khung ban đầu, các người khác chỉ **thêm entry vào cuối mảng**, không sửa dòng người khác.
2. **JS render-function** — cho phần lặp lại nhưng khác dữ liệu. VD người 2 viết 1 hàm `renderVeCard(ve)` dùng chung cho cả trang "lịch sử vé" (khách hàng) lẫn "bán vé tại quầy" (nhân viên quầy vé) — vì cả 2 đều thuộc người 2 nên không phát sinh vấn đề gì; người 1 viết 1 hàm `renderDataTable(columns, rows, onEdit, onDelete)` dùng chung cho các trang danh mục trong `quan-ly/`.

Không dùng Web Components (custom element gốc trình duyệt) — đường học (Shadow DOM, lifecycle) không đáng cho quy mô 1 tháng.

---

## 7. Quy ước Git

### 7.1. Chiến lược nhánh (GitHub Flow — không cần GitFlow)

Vì `main` tự động deploy lên Render/Vercel mỗi khi có push (`CI_CD_VA_DEPLOY.md`), không có chu kỳ release riêng, nên không cần GitFlow (`develop`/`release`/`hotfix`) — chỉ cần `main` luôn ở trạng thái chạy được + nhánh feature ngắn hạn:

1. **`main` được bảo vệ** (GitHub Settings → Branches → protect `main`): cấm push trực tiếp, bắt buộc qua Pull Request (PR), bắt buộc CI (`backend-ci.yml`) xanh mới merge được, bắt buộc ít nhất 1 approve.
2. **Nhánh feature tạo từ `main`**, đặt tên `feature/<người>-<uc>` — VD `feature/nguoi2-uc05-dat-ve`. Thêm 2 loại: `fix/<mô tả>` (sửa bug phát hiện sau), `chore/<mô tả>` (việc không phải tính năng).
3. **Nhánh sống ngắn**: 1 PR ≈ 1 UC (hoặc vài UC nhỏ liên quan), không gom cả vai trò vào 1 PR khổng lồ.
4. **Kéo `main` về nhánh mình thường xuyên** trong lúc code, không đợi tới lúc mở PR mới biết có conflict.
5. **Merge PR bằng "Squash and merge"** — gộp toàn bộ commit lặt vặt thành đúng 1 commit sạch trên `main`.
6. **Không dùng fork** — cả 5 người cùng 1 repo, push nhánh thẳng lên `origin`.
7. **Ai mở PR, người đó tự resolve conflict** trước khi xin review lại.

### 7.2. Review PR

- PR đụng vào `ve_lock_repository.py` (người 2, mục 5.1) bắt buộc **2 người review** — logic khóa dòng/overlap khó thấy sai bằng mắt, hậu quả nặng nếu sai (bán trùng ghế thật).
- Các PR khác: 1 người review là đủ.
- Không tự merge PR của chính mình.
- **PR nào gọi vào hàm của người khác** (mục 5.6) nên xin đúng người sở hữu review, dù không bắt buộc — để xác nhận gọi đúng hợp đồng đã thống nhất.

### 7.3. (Tùy chọn nâng cao) File `CODEOWNERS`

```
# .github/CODEOWNERS
backend/app/**/ve_lock_*      @nguoi-2
backend/app/**/ve_repository* @nguoi-2
backend/app/**/chuyen_xe_*    @nguoi-4
backend/app/**/nguoi_dung_*   @nguoi-1
```

---

## 8. Quy ước Migration

Đổi từ số thứ tự (`0003_x.sql`) sang **timestamp** để tránh 2 người cùng lúc đặt trùng số: `20260920_1400_them_cot_xxx.sql`. Mỗi người tự viết migration cho bảng thuộc phần mình. Migration đầu tiên (`0001_init_schema.sql`) do người 1 dựng (mục 5.4).

---

## 9. Quy trình code: API-contract-first + vertical slice

Không code "hết backend rồi mới code frontend" (waterfall) — làm theo từng lát mỏng xuyên suốt (vertical slice):

1. **Chốt schema trước** (Pydantic request/response) — `DATABASE.md`/`NGHIEP_VU.md` đã mô tả sẵn từng cột/quy tắc, chỉ cần dịch sang class Python.
2. **Viết route trả dữ liệu giả (hardcode)** ngay, chưa cần logic thật — FastAPI tự sinh Swagger (`/docs`) ngay từ bước này, test được API mà chưa cần frontend.
3. **Nối frontend gọi route giả đó** — dựng giao diện, thấy chạy được với dữ liệu giả.
4. **Quay lại viết logic thật** (Service + Repository) đằng sau route, thay dữ liệu giả bằng dữ liệu thật — frontend không cần sửa gì vì shape response không đổi.

---

## 10. Thứ tự làm việc gợi ý (mốc thời gian)

| Thời điểm | Việc cần xong |
|---|---|
| Ngày 1 | Người 1 dựng khung dự án (Docker, migration đầu, `main.py`/`db.py` chạy `"OK"`, seed tài khoản `quan_ly` gốc, `auth_middleware` tối thiểu) |
| Tuần 1 | Người 1: đăng nhập + danh mục xe/loại xe/giá vé/tuyến cơ bản. Người 2 và 4: bắt đầu song song (2 viết `tests/unit` cho thuật toán khóa ghế bằng mock; 4 viết `chuyen_xe_service` theo `NGHIEP_VU.md` mục 3.3). Người 5: viết schema + Service + `tests/unit`, chưa cần chờ ai |
| Cuối tuần 1 – đầu tuần 2 | Người 2 và 4 có bản nháp ổn định → thống nhất chữ ký hàm với người 3 (mục 5.6) nếu chưa chốt từ đầu |
| Từ tuần 2 | Người 3 bắt đầu nối thật (wiring) với người 2/4/5; mọi người chạy `tests/integration` trên Postgres thật thay vì chỉ mock |

---

## 11. Quản lý công việc

1 Issue GitHub = 1 UC, theo đúng số trong `NGHIEP_VU.md` mục 11 (bảng ma trận use case) — không cần nghĩ lại mô tả, không ai vô tình làm trùng UC.
