# UC-36: tạo tài khoản cán bộ, thay thế `gan_van_phong_can_bo`, và vì sao có "đổi văn phòng"

> **Cập nhật 23/10/2026 — UC-36 bỏ cơ chế mời bằng OTP.** Email cán bộ do công ty cấp nên không cần xác minh. Khi tạo, tài khoản có mật khẩu ban đầu mặc định `12345678` (lưu bản băm; response trả `mat_khau_ban_dau` để nhắc người tạo) và **không gửi email**; cán bộ đổi mật khẩu sau khi đăng nhập. OTP chỉ dùng khi quên mật khẩu. Mọi chỗ bên dưới nhắc "mời/OTP/`da_gui_email`/mail lỗi" cho UC-36 là **bản cũ**; bản đúng ở `NGHIEP_VU.md` UC-36 và `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md` mục 2.4. Giữ lại `da_xac_nhan = true` lúc tạo (`dang_nhap` chặn mọi tài khoản chưa xác nhận).

> File ghi lại hướng làm UC-36 của Nghĩa (Quản lý nhân sự): UC-36 sẽ tự gán văn phòng và thay chuỗi hàm `gan_van_phong_can_bo` của phần gửi hàng; nếu xóa chuỗi hàm đó thì phần gửi hàng cần làm gì; và vì sao phải có chức năng đổi văn phòng.
> **Chưa có code.** Đây là tài liệu thiết kế/thống nhất để gửi nhóm. Chi tiết kỹ thuật của UC-36 nằm ở `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md`; nghiệp vụ ở `NGHIEP_VU.md` (UC-36 và nhánh "Đổi văn phòng của cán bộ").
> Cập nhật: 23/10/2026. Nhánh: `feature/Nghia-uc36-tao-tai-khoan-can-bo`.

---

## 1. Phần Nghĩa đang làm: tạo tài khoản cán bộ (UC-36)

**Mục tiêu:** `quan_ly_nhan_su` và `quan_ly` dùng chung một chức năng để tạo tài khoản đăng nhập cho cán bộ; hệ thống quyết định ai tạo được vai trò nào.

| Việc | Cách làm |
|---|---|
| Ai tạo được vai trò nào | `quan_ly_nhan_su`: phụ xe, quầy vé, gửi hàng, điều độ viên. `quan_ly`: thêm `ke_toan`. Chỉ `quan_ly` **gốc** tạo `quan_ly` và `quan_ly_nhan_su` |
| Gán văn phòng | **Bắt buộc với quầy vé và gửi hàng**, ghi vào `ho_so_can_bo_diem`. Điều độ viên, phụ xe, kế toán, quản lý, QLNS không gắn văn phòng |
| Mật khẩu ban đầu | Tạo `nguoi_dung` với mật khẩu **mặc định `12345678`** (lưu bản băm) và **`da_xac_nhan = true`**; **không gửi email/OTP** |
| Độ an toàn dữ liệu | Tạo tài khoản và gán văn phòng trong **cùng một transaction** |
| Nhật ký | Ghi `nhat_ky_quan_ly_nhan_su` khi người tạo là `quan_ly_nhan_su` |
| Đổi văn phòng | Nhánh kèm theo UC-36, cùng repository và route |

**File sẽ thêm mới** (không sửa file của ai, trừ 1–2 dòng đăng ký ở `main.py`):
`routes/tai_khoan_can_bo.py`, `services/tai_khoan_can_bo_service.py`, `repositories/tai_khoan_can_bo_repository.py`, `schemas/tai_khoan_can_bo_schema.py`, `frontend/nhan-vien/quan-li-nhan-su/tai-khoan.html` (+ một mục trong `nav.js`). Không cần migration.

**API dự kiến**
```
GET   /quan-ly-nhan-su/tai-khoan?vai_tro=&tu_khoa=   danh sách tài khoản cán bộ
GET   /quan-ly-nhan-su/tai-khoan/van-phong           danh sách văn phòng cho ô chọn
POST  /quan-ly-nhan-su/tai-khoan                     tạo tài khoản (UC-36)
PUT   /quan-ly-nhan-su/tai-khoan/{id}/van-phong      đổi văn phòng
```

---

## 2. Hiện trạng: chuỗi hàm `gan_van_phong_can_bo` của phần gửi hàng

| Tầng | Vị trí | Việc |
|---|---|---|
| Route | `backend/app/routes/quan_ly.py:62` `PUT /quan-ly/ho-so-can-bo-diem/{nguoi_dung_id}` (+ import dòng 15) | Chỉ `quan_ly` gọi; nhận `van_phong_id` |
| Schema | `backend/app/schemas/don_hang_schema.py:190` `GanVanPhongCanBoRequest` | Body của route |
| Service | `backend/app/services/gui_hang_service.py:86` `gan_van_phong_can_bo` | Cho quầy vé, gửi hàng, **điều độ viên**; kiểm tra điểm là `van_phong` |
| Repository | `backend/app/repositories/nguoi_dung_repository.py:55` `gan_van_phong` | `INSERT ... ON CONFLICT DO UPDATE` vào `ho_so_can_bo_diem`, tự `commit()` |

- Do phần gửi hàng viết (commit `2f80b79`, PR #26) để có cách gán văn phòng khi test, vì chưa có UC-36.
- **Chỉ có một đường gọi.** Không frontend, không test, không script dùng.
- `KE_HOACH_SUA_GUI_HANG.md` mục P1 (dòng 287) ghi: UC-36 sẽ tạo tài khoản kèm `van_phong_id`; "bạn có thể đưa sẵn hàm `gan_van_phong_can_bo` để họ gọi".

### Vì sao UC-36 không gọi lại hàm này
1. Hàm repository **tự `commit()` trên kết nối riêng**, không nằm được trong transaction "tạo tài khoản + gán văn phòng".
2. Danh sách vai trò của nó còn có `dieu_do_vien`, trái quyết định mới (điều độ viên không gắn văn phòng).
3. Route chỉ cho `quan_ly`, không cho `quan_ly_nhan_su`.
4. Nghĩa quyết định làm đúng phần của mình, không phụ thuộc code của người khác.

---

## 3. Nếu xóa chuỗi hàm đó: ai phải làm gì

### 3.1. Phần cần xóa (4 file của phần gửi hàng — nên để **họ** xóa, hoặc xóa khi họ đồng ý rõ)
Thứ tự từ ngoài vào trong để không vỡ import:
1. `routes/quan_ly.py`: route `PUT /ho-so-can-bo-diem/{id}` (dòng 62–66) và dòng import `GanVanPhongCanBoRequest` (dòng 15).
2. `schemas/don_hang_schema.py`: class `GanVanPhongCanBoRequest` (khoảng dòng 190).
3. `services/gui_hang_service.py`: hàm `gan_van_phong_can_bo` (dòng 86–94).
4. `repositories/nguoi_dung_repository.py`: hàm `gan_van_phong` (dòng 55–71).

Sau khi xóa: tìm lại toàn dự án `gan_van_phong` và `GanVanPhongCanBoRequest` để chắc không còn nơi gọi; gọi thử `PUT` cũ phải ra 404/405.

### 3.2. **Không** được xóa
- Bảng `ho_so_can_bo_diem` và migration `20261002_0900`.
- Mọi nơi **đọc** bảng này, vì phần gửi hàng và thông báo dựa vào đó:
  `nguoi_dung_repository.tim_theo_id` (JOIN lấy `van_phong_id` cho middleware), `don_hang_repository.py` (khoảng dòng 914, 931: tìm nhân viên gửi hàng của văn phòng), `chuyen_xe_repository.py` (khoảng dòng 285–293: tìm điều độ viên theo văn phòng — việc của nhóm điều độ viên), `scripts/seed_phu_xe_demo.py` (INSERT thẳng).

### 3.3. Phần gửi hàng cần **làm lại hoặc thêm** gì
Kết quả rà soát code: **gần như không phải viết lại gì**, chỉ cập nhật vài chỗ.

| # | Việc | Mức |
|---|---|---|
| 1 | **Xóa** chuỗi 4 hàm ở 3.1 (hoặc đồng ý cho Nghĩa xóa) | Xóa, không viết mới |
| 2 | **Sửa tài liệu** `DATABASE.md` mục 1.3 (dòng 60): hiện ghi "Quản lý gán/cập nhật qua `PUT /quan-ly/ho-so-can-bo-diem/...`" → đổi thành gán qua UC-36 và nhánh đổi văn phòng | Sửa 1 câu |
| 3 | **Sửa `KE_HOACH_SUA_GUI_HANG.md` mục P1**: UC-36 đã tự gán văn phòng, không cần "đưa sẵn hàm" | Sửa 1 dòng |
| 4 | **Xác nhận không có test/script/E2E nào gọi `PUT /ho-so-can-bo-diem`**. Rà soát của tôi: test unit và tài liệu E2E (147/147) không gọi endpoint này (không tìm thấy chỗ gọi); nếu script E2E riêng của họ có gọi thì phải đổi sang chèn thẳng DB hoặc dùng API mới | Kiểm tra |
| 5 | Không cần đổi frontend: màn hình chặn "Tài khoản chưa được gán văn phòng… liên hệ quản lý" (`frontend/nhan-vien/gui-hang/khoi-tao.js:3`) vẫn đúng, vì quản lý nay gán qua UC-36/đổi văn phòng | Không |
| 6 | Không cần đổi gì ở `_pham_vi_van_phong` (`routes/gui_hang.py`), `_kiem_tra_don_thuoc_van_phong` hay phần thông báo; chúng chỉ **đọc** `van_phong_id` | Không |
| 7 | Tài khoản test cũ chưa có văn phòng: sau khi xóa, gán lại bằng **chức năng đổi văn phòng** của UC-36 (chấp nhận cả trường hợp chưa có dòng nào) hoặc seed | Dùng cái mới |

### 3.4. Nhóm điều độ viên
`DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md:112` đã đề xuất bỏ `dieu_do_vien` khỏi `gan_van_phong_can_bo`. Khi hàm bị xóa hẳn thì đề xuất đó tự được thực hiện; hai nhóm nên nghe cùng một thông báo.

### 3.5. Thứ tự an toàn (không có lúc nào mất khả năng gán văn phòng)
1. Báo nhóm gửi hàng + Trưởng nhóm + nhóm điều độ viên, xin đồng ý.
2. Nghĩa làm xong UC-36 và đổi văn phòng, test, merge.
3. **Sau đó mới** xóa chuỗi cũ (PR nhỏ riêng), kèm sửa hai dòng tài liệu ở bảng 3.3.

---

## 4. Vì sao phải thêm "đổi văn phòng"

**Tóm tắt:** hiện tại cách duy nhất để sửa văn phòng là chuỗi hàm cũ. Xóa nó mà không có thứ thay thế thì văn phòng chỉ ghi được **một lần lúc tạo tài khoản**, không sửa được nữa.

Tài liệu cũ ghi "gắn cố định 1 văn phòng" (`NGHIEP_VU.md` mục 2), nhưng chỉ là **chưa có chức năng đổi**, chứ không có câu nào cấm đổi. Cụ thể nếu không có đổi văn phòng:

| # | Vấn đề | Hệ quả |
|---|---|---|
| 1 | **Gán nhầm văn phòng lúc tạo** | Nhân viên chỉ thấy và thao tác đơn của văn phòng sai; không sửa được, chỉ có khóa tài khoản rồi tạo mới với email khác (email là duy nhất) hoặc sửa DB |
| 2 | **Nhân viên điều chuyển** sang văn phòng khác (chuyện bình thường khi có nhiều văn phòng) | Phải cho nghỉ rồi tạo tài khoản mới → lịch sử bị chia đôi (nhật ký thao tác, `nhan_vien_thu_id`, người hủy đơn gắn vào tài khoản cũ) |
| 3 | **Tài khoản cũ chưa có văn phòng** (seed hoặc tạo tay trước đây) | Bị chặn 403 toàn bộ phần gửi hàng; xóa chuỗi cũ xong là hết cách gán, trừ sửa DB |
| 4 | **Đóng/gộp văn phòng** | Nhiều nhân viên phải đổi cùng lúc |
| 5 | **Phát triển và test** | Phải sửa DB tay mỗi lần cần đổi văn phòng tài khoản thử |

Vì vậy đổi văn phòng là **phần bù** cho việc xóa chuỗi hàm cũ, đồng thời là chức năng nghiệp vụ hợp lý. Không có đổi văn phòng thì chỉ nên **giữ** chuỗi cũ như "lối thoát quản trị".

### Luật đổi văn phòng đã ghi trong `NGHIEP_VU.md`
- Actor: `quan_ly` (bất kỳ) hoặc `quan_ly_nhan_su`. Áp dụng quầy vé và gửi hàng.
- Điểm mới phải là `van_phong` và **khác** văn phòng hiện tại; chưa có văn phòng thì coi là gán lần đầu (`INSERT ... ON CONFLICT DO UPDATE`).
- Ghi nhật ký (cũ → mới) khi actor là `quan_ly_nhan_su`.
- Đơn/vé đã xử lý **giữ nguyên ở văn phòng cũ** (đơn thuộc văn phòng, không thuộc người); từ lúc đổi, cán bộ chỉ thấy dữ liệu văn phòng mới.

### Hai quy tắc do Nghĩa/Claude tự chọn, **cần nhóm xác nhận**
| Quy tắc | Đang ghi | Phương án khác |
|---|---|---|
| Khi cán bộ còn đơn đang xử lý | **Không chặn** (quyền xem đơn tính theo văn phòng nên đơn vẫn có người ở văn phòng cũ tiếp nhận) | Chặn đến khi xử lý xong, hoặc cho đổi kèm cảnh báo "còn N đơn" |
| Lý do đổi | **Không bắt buộc** | Bắt buộc, giống UC-51 (cho nghỉ việc) để nhật ký rõ hơn — Claude đề xuất cách này |

### ⚠️ NOTE — chưa chốt, đổi văn phòng làm sau (23/10/2026)

Hai quy tắc trên **chưa được nhóm xác nhận**, nên **chưa code phần đổi văn phòng**. Cách làm:

- **Code UC-36 (tạo tài khoản) trước.** Phần này không phụ thuộc hai quy tắc trên: schema, repository, service kèm unit test, route, frontend `tai-khoan.html`.
- **Đổi văn phòng để sau**, chỉ viết khi đã chốt hai quy tắc.
- Khi chốt xong: sửa lại nhánh "Đổi văn phòng của cán bộ" trong `NGHIEP_VU.md` (phần "Luồng chính", "Luồng rẽ nhánh" và "Ghi chú") cho khớp, sửa sơ đồ trong `UML_DIAGRAMS.md`, rồi mới code.
- Trong lúc chưa có đổi văn phòng thì **không xóa chuỗi hàm `gan_van_phong_can_bo`** (xem mục 3.5): xóa trước sẽ làm mất đường sửa văn phòng gán nhầm. Chỉ xóa sau khi đổi văn phòng đã chạy được và nhóm đồng ý.

Tác động của từng lựa chọn lên code đổi văn phòng sau này:

| Quy tắc | Nếu chọn | Việc code thêm |
|---|---|---|
| Khi còn đơn đang xử lý | Không chặn (đang ghi) | Không thêm gì |
| | Chặn | Thêm hàm đếm đơn dở của nhân viên ở repository, thêm nhánh lỗi trong service, thêm test |
| | Cho đổi kèm cảnh báo | Thêm hàm đếm đơn, API trả số đơn dở để giao diện cảnh báo |
| Lý do đổi | Không bắt buộc (đang ghi) | Trường `ly_do` tùy chọn |
| | Bắt buộc (Claude đề xuất, nhất quán UC-51) | Trường `ly_do` bắt buộc ở schema, ghi vào nhật ký |

**Cần chốt:** (1) có chặn khi còn đơn dở không; (2) lý do có bắt buộc không.

---

## 5. Tóm tắt gửi nhóm (có thể copy)

> Mình đang làm UC-36 (tạo tài khoản cán bộ). UC-36 sẽ tự gán văn phòng cho quầy vé/gửi hàng lúc tạo (cùng transaction với tạo tài khoản) và có thêm chức năng đổi văn phòng (đã ghi vào `NGHIEP_VU.md`). Vì vậy chuỗi `gan_van_phong_can_bo` (route `PUT /quan-ly/ho-so-can-bo-diem`, schema `GanVanPhongCanBoRequest`, `gui_hang_service.gan_van_phong_can_bo`, `nguoi_dung_repository.gan_van_phong`) sẽ không còn cần. Mình đề xuất **xóa sau khi UC-36 merge**, và ưu tiên bạn phần gửi hàng tự xóa. Phía gửi hàng chỉ cần sửa 2 dòng tài liệu (`DATABASE.md` mục 1.3, `KE_HOACH_SUA_GUI_HANG.md` mục P1) và kiểm tra không script E2E nào gọi endpoint cũ; không cần đổi code đọc `ho_so_can_bo_diem`. Bảng `ho_so_can_bo_diem` giữ nguyên. Mọi người xác nhận giúp: (1) đồng ý xóa; (2) đổi văn phòng có chặn khi còn đơn dở không; (3) lý do đổi có bắt buộc không.
