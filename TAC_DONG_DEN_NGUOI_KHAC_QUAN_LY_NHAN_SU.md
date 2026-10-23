# Những việc của phần Quản lý nhân sự ảnh hưởng đến người khác trong nhóm

> **Mục đích:** file này là sổ ghi chú của Nghĩa (Quản lý nhân sự). Mỗi khi một phần việc của mình **đụng đến, thay đổi, hoặc đòi hỏi người khác phải làm gì**, ghi vào đây để báo nhóm. Việc chỉ nằm gọn trong phần mình thì không cần ghi (xem `BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md`).
>
> **Cách dùng:** thêm một dòng vào bảng mục 1 (kèm mục chi tiết bên dưới nếu cần), và đổi cột "Trạng thái" khi đã báo / đã được xác nhận / đã xong.
>
> *File này trước đây tên `UC36_THAY_THE_GAN_VAN_PHONG_VA_DOI_VAN_PHONG.md`, nay mở rộng cho toàn bộ nhiệm vụ của mình.*
>
> Cập nhật lần cuối: 23/10/2026 (đến UC-36 đã merge #38 và UC-37 đang làm trên nhánh `feature/Nghia-uc37-khoa-mo-khoa-tai-khoan`).

Ký hiệu trạng thái: ⏳ chưa báo · 📣 đã báo, chờ trả lời · ✅ đã xong / đã xác nhận · ❓ cần nhóm quyết định.

---

## 1. Bảng tổng hợp

| # | Việc của mình | Ảnh hưởng đến ai | Họ cần làm gì | UC | Trạng thái |
|---|---|---|---|---|---|
| 1 | Tạo tài khoản + gán văn phòng nằm trong UC-36; chuỗi hàm `gan_van_phong_can_bo` không còn cần | Phần **gửi hàng** (người viết hàm), Trưởng nhóm | Đồng ý để xóa 4 hàm (ưu tiên họ tự xóa); sửa 2 dòng tài liệu; kiểm tra script E2E | UC-36 | ❓ ⏳ |
| 2 | **Điều độ viên không gắn văn phòng** (sửa tài liệu cho khớp đề xuất theo tuyến) | Nhóm **điều độ viên** | Sửa code còn lệch: `seed_phu_xe_demo.py`, `danh_sach_dieu_do_vien_tai_diem`; làm bảng `dieu_do_vien_tuyen` | UC-36/37 | ⏳ |
| 3 | UC-36 **bỏ OTP**, dùng mật khẩu ban đầu mặc định `12345678` (đổi so với spec cũ) | **Cả nhóm** (spec đã duyệt), Trưởng nhóm | Biết và đồng ý; không dựa vào luồng "mời bằng OTP" | UC-36 | ⏳ |
| 4 | Thêm migration mới **`nhat_ky_admin`** | **Cả nhóm** (mọi người chạy DB local) | Sau khi pull phải chạy `yoyo apply ./migrations` | UC-37 | ⏳ |
| 5 | **Quy tắc bậc** của khóa / mở khóa (chặt hơn spec cũ "`quan_ly` bất kỳ khóa được mọi cán bộ") | Trưởng nhóm, ai dùng tài khoản `quan_ly` | Biết và đồng ý | UC-37 | ⏳ |
| 6 | Khóa **phụ xe** gửi thông báo cho `quan_ly` + `dieu_do_vien` (dùng lại hàm chung) | Nhóm **điều độ viên**, nhóm **thông báo / biên chế phụ xe** | Cho điều độ viên chỗ xem thông báo; xem cách xử lý phụ xe đã khóa trong biên chế (mục 6) | UC-37 | ⏳ |
| 7 | **Đổi văn phòng** (chưa code) | Phần gửi hàng, Trưởng nhóm | Chốt 2 quy tắc: còn đơn dở có chặn không; lý do có bắt buộc không | UC-36 (nhánh kèm) | ❓ |
| 8 | Thêm file dùng chung / điểm nối | Người sở hữu các file đó | Biết khi sửa lại các file này (mục 8) | UC-49/36/37 | ✅ |
| 9 | 7 test lỗi **có sẵn** ở integration (không do mình) | Người làm **vé lẻ / thanh toán** | Sửa test | — | ⏳ |

---

## 2. Phần gửi hàng: chuỗi hàm `gan_van_phong_can_bo` (việc #1)

### 2.1. Mình làm gì ở UC-36
`quan_ly_nhan_su` và `quan_ly` dùng chung một chức năng tạo tài khoản cán bộ. **Quầy vé và gửi hàng bắt buộc chọn văn phòng**, hệ thống ghi vào `ho_so_can_bo_diem` ngay lúc tạo, **cùng một transaction** với tạo tài khoản. Code đã merge (#38). Mình **không sửa, không gọi** chuỗi hàm cũ của phần gửi hàng.

### 2.2. Hiện trạng chuỗi hàm của phần gửi hàng

| Tầng | Vị trí | Việc |
|---|---|---|
| Route | `backend/app/routes/quan_ly.py:62` `PUT /quan-ly/ho-so-can-bo-diem/{nguoi_dung_id}` (+ import dòng 15) | Chỉ `quan_ly` gọi; nhận `van_phong_id` |
| Schema | `backend/app/schemas/don_hang_schema.py:190` `GanVanPhongCanBoRequest` | Body của route |
| Service | `backend/app/services/gui_hang_service.py:86` `gan_van_phong_can_bo` | Cho quầy vé, gửi hàng, **điều độ viên**; kiểm tra điểm là `van_phong` |
| Repository | `backend/app/repositories/nguoi_dung_repository.py:55` `gan_van_phong` | `INSERT ... ON CONFLICT DO UPDATE` vào `ho_so_can_bo_diem`, tự `commit()` |

- Do phần gửi hàng viết (commit `2f80b79`, PR #26) để có cách gán văn phòng khi test, vì chưa có UC-36.
- **Chỉ có một đường gọi.** Không frontend, không test, không script dùng.
- `KE_HOACH_SUA_GUI_HANG.md` mục P1 (dòng 287) ghi: UC-36 sẽ tạo tài khoản kèm `van_phong_id`; "bạn có thể đưa sẵn hàm `gan_van_phong_can_bo` để họ gọi".

**Vì sao UC-36 không gọi lại hàm này:**
1. Hàm repository **tự `commit()` trên kết nối riêng**, không nằm được trong transaction "tạo tài khoản + gán văn phòng".
2. Danh sách vai trò của nó còn có `dieu_do_vien`, trái quyết định mới (điều độ viên không gắn văn phòng).
3. Route chỉ cho `quan_ly`, không cho `quan_ly_nhan_su`.
4. Làm đúng phần của mình, không phụ thuộc code của người khác.

### 2.3. Nếu xóa chuỗi hàm đó: ai phải làm gì

**Phần cần xóa** (4 file của phần gửi hàng, nên để **họ** xóa hoặc xóa khi họ đồng ý rõ). Thứ tự từ ngoài vào trong để không vỡ import:
1. `routes/quan_ly.py`: route `PUT /ho-so-can-bo-diem/{id}` (dòng 62–66) và dòng import `GanVanPhongCanBoRequest` (dòng 15).
2. `schemas/don_hang_schema.py`: class `GanVanPhongCanBoRequest` (khoảng dòng 190).
3. `services/gui_hang_service.py`: hàm `gan_van_phong_can_bo` (dòng 86–94).
4. `repositories/nguoi_dung_repository.py`: hàm `gan_van_phong` (dòng 55–71).

Sau khi xóa: tìm lại toàn dự án `gan_van_phong` và `GanVanPhongCanBoRequest` để chắc không còn nơi gọi; gọi thử `PUT` cũ phải ra 404/405.

**Không được xóa:** bảng `ho_so_can_bo_diem` và migration `20261002_0900`; mọi nơi **đọc** bảng này vì phần gửi hàng và thông báo dựa vào đó: `nguoi_dung_repository.tim_theo_id` (JOIN lấy `van_phong_id` cho middleware), `don_hang_repository.py` (khoảng dòng 914, 931: tìm nhân viên gửi hàng của văn phòng), `chuyen_xe_repository.py` (khoảng dòng 285–293: tìm điều độ viên theo văn phòng, việc của nhóm điều độ viên), `scripts/seed_phu_xe_demo.py` (INSERT thẳng).

**Phần gửi hàng cần làm lại hoặc thêm gì:** kết quả rà soát code là **gần như không phải viết lại gì**.

| # | Việc | Mức |
|---|---|---|
| 1 | **Xóa** chuỗi 4 hàm ở trên (hoặc đồng ý cho Nghĩa xóa) | Xóa, không viết mới |
| 2 | **Sửa tài liệu** `DATABASE.md` mục 1.3 (dòng 60): hiện ghi "Quản lý gán/cập nhật qua `PUT /quan-ly/ho-so-can-bo-diem/...`" thành gán qua UC-36 và nhánh đổi văn phòng | Sửa 1 câu |
| 3 | **Sửa `KE_HOACH_SUA_GUI_HANG.md` mục P1**: UC-36 đã tự gán văn phòng, không cần "đưa sẵn hàm" | Sửa 1 dòng |
| 4 | **Xác nhận không có test/script/E2E nào gọi `PUT /ho-so-can-bo-diem`**. Rà soát của mình: test unit và tài liệu E2E (147/147) không gọi endpoint này; nếu script E2E riêng của họ có gọi thì đổi sang chèn thẳng DB hoặc dùng API mới | Kiểm tra |
| 5 | Không cần đổi frontend: màn hình chặn "Tài khoản chưa được gán văn phòng… liên hệ quản lý" (`frontend/nhan-vien/gui-hang/khoi-tao.js:3`) vẫn đúng | Không |
| 6 | Không cần đổi `_pham_vi_van_phong` (`routes/gui_hang.py`), `_kiem_tra_don_thuoc_van_phong` hay phần thông báo; chúng chỉ **đọc** `van_phong_id` | Không |
| 7 | Tài khoản test cũ chưa có văn phòng: sau khi xóa, gán lại bằng **chức năng đổi văn phòng** (chấp nhận cả trường hợp chưa có dòng nào) hoặc seed | Dùng cái mới |

**Thứ tự an toàn** (không có lúc nào mất khả năng gán văn phòng):
1. Báo nhóm gửi hàng + Trưởng nhóm + nhóm điều độ viên, xin đồng ý.
2. Nghĩa làm xong đổi văn phòng, test, merge.
3. **Sau đó mới** xóa chuỗi cũ (PR nhỏ riêng), kèm sửa hai dòng tài liệu ở bảng trên.

> ⚠️ Trong lúc **chưa có đổi văn phòng** thì **không xóa** chuỗi hàm cũ: xóa trước sẽ làm mất đường sửa văn phòng gán nhầm.

---

## 3. Nhóm điều độ viên: điều độ viên không gắn văn phòng (việc #2)

**Mình làm gì:** sửa tài liệu cho khớp quyết định "điều độ viên không gắn văn phòng, phụ trách theo tuyến" (đề xuất của chính nhóm điều độ viên, `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md`):
- `DATABASE.md` mục 1.3 + sơ đồ quan hệ.
- `NGHIEP_VU.md` mục 2, 3.3, 3.6, UC-44 (chỉ đổi chữ phạm vi "văn phòng" thành "tuyến").
- `UML_DIAGRAMS.md` class diagram.
- Code UC-36 mình viết: điều độ viên tạo **không** có văn phòng (văn phòng chỉ bắt buộc với quầy vé / gửi hàng).

**Họ cần làm:** mình **không** sửa code hay dữ liệu của họ. Những chỗ vẫn còn lệch:
- `backend/scripts/seed_phu_xe_demo.py` dòng 158: gán điều độ viên demo vào văn phòng A.
- `danh_sach_dieu_do_vien_tai_diem` (tìm điều độ viên theo văn phòng; có đường lui gửi cho tất cả điều độ viên).
- `gan_van_phong_can_bo` còn cho `dieu_do_vien` (sẽ hết khi hàm bị xóa, mục 2).
- Cơ chế gán theo chu trình và bảng `dieu_do_vien_tuyen` vẫn là việc của họ.

**Cần chú ý:** file `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` của họ đã **vào integration cùng commit UC-36 (#38)** do mình lỡ `git add` chung. Nội dung không bị sửa, nhưng nên báo để họ biết.

**Liên quan UC-37 (làm sau):** khi khóa điều độ viên mà tuyến hết người phụ trách thì nên cảnh báo. Chờ họ có bảng `dieu_do_vien_tuyen` mới làm được (xem `KE_HOACH_UC37_KHOA_MO_KHOA_TAI_KHOAN.md` mục 8).

---

## 4. Cả nhóm: UC-36 bỏ OTP, đổi so với spec cũ (việc #3)

Spec đã duyệt: tạo tài khoản với mật khẩu rỗng rồi gửi mã OTP để cán bộ đặt mật khẩu ở trang Quên mật khẩu. **Đã đổi:**
- Email cán bộ do công ty cấp nên không cần xác minh.
- Tài khoản mới có **mật khẩu ban đầu mặc định `12345678`** (chỉ lưu bản băm bcrypt), `da_xac_nhan = true`, **không gửi email**; response trả `mat_khau_ban_dau` để người tạo báo cho cán bộ.
- OTP chỉ còn dùng khi quên mật khẩu.

**Rủi ro:** ai biết email công ty đều đăng nhập được cho đến khi cán bộ đổi mật khẩu. Muốn chặt hơn cần cờ "bắt buộc đổi mật khẩu lần đầu": phải **thêm cột vào bảng `nguoi_dung` dùng chung**, nên để làm sau và hỏi nhóm.

**Tài liệu đã sửa:** `NGHIEP_VU.md` (nguyên tắc ở mục 2, UC-36 bước 3–4, bỏ nhánh "gửi email thất bại"), `UML_DIAGRAMS.md`, `DATABASE.md` (2 cột `mat_khau` / `da_xac_nhan`).

---

## 5. Cả nhóm: migration `nhat_ky_admin` và quy tắc bậc UC-37 (việc #4, #5)

### 5.1. Migration mới (bắt buộc chạy)
- File: `backend/migrations/20261023_1000_tao_bang_nhat_ky_admin.sql`. Tạo bảng `nhat_ky_admin` (trước đó `DATABASE.md` mục 6.2 chỉ mô tả, **chưa từng có migration**).
- **Sau khi pull, mọi người phải chạy** `docker-compose exec backend yoyo apply ./migrations`. Nếu quên, `quan_ly` khóa / mở khóa tài khoản sẽ **lỗi 500**.
- Bảng chỉ có `INSERT`; hiện UC-37 là nơi duy nhất ghi vào. Ai làm chức năng khác của `quan_ly` (tuyến, giá, xe, biên chế...) và muốn ghi nhật ký có thể dùng `repositories/nhat_ky_admin_repository.ghi(...)`, nhưng đây là lựa chọn, không bắt buộc.

### 5.2. Quy tắc bậc của UC-37 (chặt hơn spec cũ)
Spec cũ cho "`quan_ly` bất kỳ" khóa được mọi cán bộ. Bản đã chốt: gốc > (`quan_ly` thường = `ke_toan`) > `quan_ly_nhan_su` > 4 vai trò vận hành; chỉ khóa / mở khóa bậc **thấp hơn** mình.

| Người thao tác | Khóa / mở khóa được |
|---|---|
| `quan_ly` gốc | `quan_ly`, `ke_toan`, `quan_ly_nhan_su`, 4 vai trò vận hành |
| `quan_ly` thường | `quan_ly_nhan_su`, 4 vai trò vận hành |
| `quan_ly_nhan_su` | 4 vai trò vận hành |

Khách hàng: không ai khóa / mở; hệ thống tự khóa theo `NGHIEP_VU.md` mục 9. Lý do khóa / mở khóa **bắt buộc**.

Tài liệu đã sửa: `NGHIEP_VU.md` (8.7 điểm 5–6, mục 9, UC-37), `UML_DIAGRAMS.md`, `DATABASE.md` (6.2, `bi_khoa`), `ARCHITECTURE.md`.

---

## 6. Khóa phụ xe: thông báo và biên chế (việc #6)

**Mình làm gì:** khi khóa tài khoản `phu_xe` làm cho một xe không còn phụ xe **cố định** nào đang hoạt động, hệ thống:
- Trả `canh_bao_xe_thieu_phu_xe` (danh sách biển số) cho người khóa.
- Gửi thông báo cho `quan_ly` và `dieu_do_vien` đang hoạt động (không gửi `quan_ly_nhan_su`, bỏ người vừa khóa).
- **Không tự đổi biên chế**: chỉ nhắc.

**Dùng lại code của nhóm, không sửa:** `thong_bao_khach_service.gui(...)` (ghi bảng `thong_bao` rồi đẩy WebSocket, không ném lỗi) và `nguoi_dung_repository.danh_sach_id_theo_vai_tro(vai_tro, chi_dang_hoat_dong=True)`.

**Cần người khác xem lại:**
1. **Điều độ viên có chỗ nào để thấy thông báo không?** `quan_ly` có chuông (`frontend/nhan-vien/quan-ly/thong-bao.js`). Trong `frontend/nhan-vien/` chưa thấy thư mục riêng cho điều độ viên. Thông báo vẫn được lưu đúng cho họ, nhưng hiển thị là việc của nhóm điều độ viên.
2. **Thông báo không có `duong_dan`** (bấm vào chỉ đánh dấu đã đọc), vì hai vai trò dùng giao diện khác nhau. Nếu nhóm chốt được trang đích thì mình bổ sung.
3. **Phụ xe đã khóa vẫn nằm trong biên chế `xe_nhan_su`** (mình chỉ đổi cờ `nguoi_dung.dang_hoat_dong`, không đụng biên chế). Người làm biên chế (UC-35) và sinh / gán chuyến nên kiểm tra: gán phụ xe cho chuyến và danh sách "phụ xe của xe" có loại tài khoản đã khóa không? Mình chưa kiểm tra phần này trong code của họ.
4. Hàm đếm của mình `xe_thieu_phu_xe` coi phụ xe là "còn" khi: biên chế `co_dinh` + `dang_hoat_dong`, hồ sơ `dang_lam`, tài khoản `dang_hoat_dong`. Nếu nhóm định nghĩa "thiếu phụ xe" khác thì báo để thống nhất.

---

## 7. Đổi văn phòng của cán bộ: vì sao có và điều cần chốt (việc #7)

**Tóm tắt:** hiện tại cách duy nhất để sửa văn phòng là chuỗi hàm cũ của phần gửi hàng. Xóa nó mà không có thứ thay thế thì văn phòng chỉ ghi được **một lần lúc tạo tài khoản**.

Tài liệu cũ ghi "gắn cố định 1 văn phòng" (`NGHIEP_VU.md` mục 2), nhưng chỉ là **chưa có chức năng đổi**, không có câu nào cấm đổi. Nếu không có đổi văn phòng:

| # | Vấn đề | Hệ quả |
|---|---|---|
| 1 | **Gán nhầm văn phòng lúc tạo** | Nhân viên chỉ thấy và thao tác đơn của văn phòng sai; chỉ còn cách khóa rồi tạo mới với email khác hoặc sửa DB |
| 2 | **Nhân viên điều chuyển** sang văn phòng khác | Phải cho nghỉ rồi tạo tài khoản mới, lịch sử bị chia đôi (nhật ký, `nhan_vien_thu_id`, người hủy đơn gắn vào tài khoản cũ) |
| 3 | **Tài khoản cũ chưa có văn phòng** (seed hoặc tạo tay trước đây) | Bị chặn 403 toàn bộ phần gửi hàng; xóa chuỗi cũ xong là hết cách gán, trừ sửa DB |
| 4 | **Đóng / gộp văn phòng** | Nhiều nhân viên phải đổi cùng lúc |
| 5 | **Phát triển và test** | Phải sửa DB tay mỗi lần đổi văn phòng của tài khoản thử |

Vì vậy đổi văn phòng là **phần bù** cho việc xóa chuỗi hàm cũ. Không có thì chỉ nên **giữ** chuỗi cũ như "lối thoát quản trị".

**Luật đã ghi trong `NGHIEP_VU.md`:** actor `quan_ly` hoặc `quan_ly_nhan_su`, áp dụng quầy vé và gửi hàng; điểm mới phải là `van_phong` và khác văn phòng hiện tại (chưa có thì coi là gán lần đầu, `INSERT ... ON CONFLICT DO UPDATE`); ghi nhật ký (cũ → mới) khi actor là `quan_ly_nhan_su`; đơn / vé đã xử lý giữ nguyên ở văn phòng cũ, từ lúc đổi cán bộ chỉ thấy dữ liệu văn phòng mới.

### ❓ Hai quy tắc chưa chốt, cần nhóm xác nhận (chưa code)

| Quy tắc | Đang ghi | Phương án khác |
|---|---|---|
| Khi cán bộ còn đơn đang xử lý | **Không chặn** (quyền xem đơn tính theo văn phòng nên đơn vẫn có người ở văn phòng cũ tiếp nhận) | Chặn đến khi xử lý xong, hoặc cho đổi kèm cảnh báo "còn N đơn" |
| Lý do đổi | **Không bắt buộc** | Bắt buộc, giống UC-51 và UC-37 để nhật ký rõ hơn (đề xuất) |

Tác động lên code đổi văn phòng sau này: chặn hoặc cảnh báo thì thêm hàm đếm đơn dở ở repository, nhánh lỗi / API trả số đơn ở service, thêm test; lý do bắt buộc thì thêm `ly_do` bắt buộc ở schema và ghi vào nhật ký.

Khi chốt xong: sửa nhánh "Đổi văn phòng của cán bộ" trong `NGHIEP_VU.md` (luồng chính, luồng rẽ nhánh, ghi chú) và sơ đồ trong `UML_DIAGRAMS.md`, rồi mới code.

---

## 8. File dùng chung / điểm nối mình có đụng (việc #8)

Quy tắc của mình: không sửa code đã có của người khác; được **thêm** hàm / dòng mới, ưu tiên không đổi tên biến rồi không đổi tên hàm.

| File | Mình làm gì | Nên biết |
|---|---|---|
| `backend/app/main.py` | Thêm đăng ký router `nhan_su` + job `canh_bao_giay_to` (UC-49), router `tai_khoan_can_bo` (UC-36). UC-49 có đổi dòng import (diff `6 +-`) | Điểm nối bắt buộc duy nhất. UC-37 **không** sửa |
| `backend/app/config.py` | Thêm `NGUONG_CANH_BAO_GIAY_TO_NGAY = 30` | Chỉ thêm |
| `backend/app/repositories/nhan_su_van_hanh_repository.py` | Thêm 6 hàm cuối file (UC-49) | Hàm cũ giữ nguyên |
| `frontend/nhan-vien/dang-nhap.html` | Đổi **1 giá trị** đường dẫn để `quan_ly_nhan_su` đăng nhập xong vào `quan-li-nhan-su/` | Nếu ai sửa luồng chuyển trang sau đăng nhập, giữ lại nhánh này |
| `/nhan-vien/quan-ly/style.css`, `data-table.js` | Chỉ **tham chiếu**, không sửa, không copy | Trang `quan-li-nhan-su/*` dùng chung hai file này: ai sửa class `nv-*` hoặc `renderDataTable` sẽ ảnh hưởng cả trang của mình |

Mình không sửa file code nào khác của người khác. Các bảng dùng chung: `nguoi_dung` (UC-36 INSERT; UC-37 UPDATE `dang_hoat_dong`), `ho_so_can_bo_diem` (UC-36 INSERT), `nhan_su_van_hanh` / `giay_to_nhan_su` (UC-49); không đổi cấu trúc bảng nào của người khác.

---

## 9. Lỗi có sẵn không do mình (việc #9)

Cả bộ `tests/unit` trên integration có **7 test lỗi có sẵn**: `test_ve_le.py` (6 test) và `test_thong_bao_khach.py::test_ipn_ve_le_thanh_cong_bao_khach`. Mình đã xác minh bằng `git stash` rằng chúng lỗi cả khi không có code của mình. Thuộc phần vé lẻ / thanh toán, cần báo người làm.

---

## 10. Tóm tắt gửi nhóm (có thể copy)

> Mình (Nghĩa, Quản lý nhân sự) báo các thay đổi ảnh hưởng đến mọi người, chi tiết ở `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md`:
> 1. **Cả nhóm:** sau khi pull cần chạy `yoyo apply ./migrations` (bảng `nhat_ky_admin` mới, UC-37). Quên thì `quan_ly` khóa tài khoản sẽ lỗi 500.
> 2. **UC-36 đã đổi so với spec:** bỏ mời bằng OTP, tạo tài khoản kèm mật khẩu mặc định `12345678`, không gửi email. **UC-37:** khóa / mở khóa theo bậc (gốc > `quan_ly` thường = kế toán > QLNS > cán bộ vận hành), lý do bắt buộc, khách hàng không khóa được. Mọi người xác nhận giúp.
> 3. **Phần gửi hàng:** UC-36 tự gán văn phòng cho quầy vé / gửi hàng lúc tạo tài khoản. Chuỗi `gan_van_phong_can_bo` (route `PUT /quan-ly/ho-so-can-bo-diem`, schema `GanVanPhongCanBoRequest`, `gui_hang_service.gan_van_phong_can_bo`, `nguoi_dung_repository.gan_van_phong`) sẽ không còn cần. Đề xuất **xóa sau khi đổi văn phòng chạy được**, ưu tiên bạn tự xóa; phía gửi hàng chỉ sửa 2 dòng tài liệu (`DATABASE.md` mục 1.3, `KE_HOACH_SUA_GUI_HANG.md` mục P1) và kiểm tra script E2E. Bảng `ho_so_can_bo_diem` giữ nguyên.
> 4. **Nhóm điều độ viên:** điều độ viên không gắn văn phòng (tài liệu đã sửa). Còn lệch ở `seed_phu_xe_demo.py:158` và `danh_sach_dieu_do_vien_tai_diem`. File `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` của bạn đã lỡ vào integration cùng commit UC-36. Khóa phụ xe gửi thông báo cho `quan_ly` + `dieu_do_vien`: điều độ viên cần có chỗ xem thông báo.
> 5. **Biên chế / sinh chuyến:** khóa phụ xe không tự đổi `xe_nhan_su`; phụ xe đã khóa vẫn nằm trong biên chế. Nhờ kiểm tra việc gán phụ xe cho chuyến có loại tài khoản đã khóa không.
> 6. **Cần chốt (đổi văn phòng):** (a) còn đơn đang xử lý thì có chặn không; (b) lý do đổi có bắt buộc không.
> 7. **Vé lẻ / thanh toán:** 7 test lỗi có sẵn ở `test_ve_le.py` và `test_thong_bao_khach.py`, không do phần mình.
