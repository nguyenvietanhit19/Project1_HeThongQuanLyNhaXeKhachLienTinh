# Đề xuất: điều độ viên phụ trách theo TUYẾN

> **Trạng thái:** đề xuất để cả nhóm bàn bạc, **chưa code gì** trên nhánh `feature/vanh-dieu-do-theo-tuyen`. Ngày 2026-10-21.
> **Đọc phần nào:** ai chỉ cần biết "mình bị ảnh hưởng gì" đọc mục 1, 3 và 7. Người làm UC-36/37/38 (tạo/khóa tài khoản cán bộ) đọc kỹ **mục 6**.

## 1. Tóm tắt một đoạn

Hiện tài liệu quy định điều độ viên **gắn với một văn phòng** và chỉ gán xe cho chuyến *xuất phát từ* văn phòng đó. Chúng tôi đề xuất đổi thành: điều độ viên **phụ trách một hoặc nhiều tuyến**, và gán xe theo **chu trình** (chuyến đi + chuyến về cùng ngày của một cặp lịch, cùng một xe). Quản lý chọn điều độ viên phụ trách ngay ở trang **Tuyến**. Hồ sơ cán bộ (`ho_so_can_bo_diem`) **không cần văn phòng** cho điều độ viên nữa; các vai trò khác (quầy vé, gửi hàng) giữ nguyên.

## 2. Vì sao phải đổi

Cách phân công theo văn phòng gặp bốn vấn đề đã thấy rõ khi thử:

| # | Vấn đề | Ví dụ với dữ liệu hiện có |
|---|---|---|
| 1 | Chuyến đi và chuyến về thuộc **hai** điều độ viên khác nhau, phải phối hợp | Xe X1 chạy Mỹ Đình → Bắc Hà thì chuyến về Bắc Hà → Mỹ Đình thuộc điều độ viên Bắc Hà. Nếu họ gán chuyến về cho xe khác, X1 bị kẹt lại Bắc Hà |
| 2 | Văn phòng ở điểm cuối hoặc giữa tuyến **không có việc** | Sân bay Nội Bài nằm giữa tuyến T002; Thị Trấn Bắc Hà là điểm cuối |
| 3 | Một khu vực có **nhiều văn phòng**, không chia việc được | TP. Hà Nội có Mỹ Đình và Nội Bài; SaPa có Bảo Hà và 120 Điện Biên Phủ |
| 4 | Khối lượng không đều | Văn phòng là điểm đầu của nhiều tuyến thì quá tải, văn phòng khác rảnh |

Gốc của vấn đề: **văn phòng không phải đơn vị của công việc**. Công việc thật của điều độ viên là gán xe cho chuyến, mà lịch chạy, giá vé, chuyến và xe cố định (`xe.tuyen_id`) đều xoay quanh **tuyến**.

## 3. Mô hình đề xuất

### 3.1. Khái niệm

- **Tuyến**: giữ nguyên (đã có).
- **Chu trình**: chuyến đi ngày D và chuyến về của đúng chu kỳ đó (ngày D + `ngay_lech` của cặp lịch). Hai chuyến này luôn sinh cùng nhau (UC-47) nên ghép được chắc chắn.
- **Điều độ viên phụ trách tuyến**: quan hệ nhiều–nhiều. Một điều độ viên có thể lo nhiều tuyến, một tuyến có thể có nhiều điều độ viên (chia ca).

Ví dụ với tuyến T002 (Mỹ Đình → Bắc Hà, chạy 6 tiếng), cặp lịch đi 08:00 / về 16:00:

```
Chu trình 22/10:   Đi  Mỹ Đình → Bắc Hà   08:00 22/10 ┐ cùng một xe, gán 1 lần
                   Về  Bắc Hà → Mỹ Đình   16:00 22/10 ┘
Chu trình 23/10:   Đi  ...                08:00 23/10 ┐
                   Về  ...                16:00 23/10 ┘
```

### 3.2. Phạm vi quyền

| Vai trò | Thấy và gán xe được |
|---|---|
| `dieu_do_vien` | Chu trình của **các tuyến mình phụ trách** |
| `quan_ly` | Mọi tuyến (thay điều độ viên khi tuyến chưa có ai) |

Tuyến chưa có điều độ viên: trang Tuyến hiện cảnh báo cho quản lý; quản lý tạm xử lý. Cảnh báo sự cố của tuyến đó gửi **tất cả điều độ viên đang hoạt động**, nếu không có ai thì tới quản lý.

### 3.3. Gán xe theo chu trình

Điều độ viên mở danh sách chu trình **khởi hành trong 3 ngày tới** (chọn được 3, 5 hoặc 7 ngày), bấm "Gán xe", chọn một xe: **cả chuyến đi và chuyến về nhận cùng xe** trong một giao dịch. Đổi xe cũng đổi cả hai.

Quy tắc kiểm tra (một xe không hợp lệ thì hiển thị kèm **mọi** lý do, không chỉ lý do đầu tiên):

1. Cùng `loai_xe` đã cam kết trong lịch chạy.
2. Xe đang `hoat_dong`.
3. Xe cố định tuyến (`xe.tuyen_id` khác trống) chỉ chạy đúng tuyến đó.
4. Không trùng lịch: khung của một chuyến = từ giờ khởi hành đến giờ khởi hành + thời gian chạy cả tuyến, cộng khoảng nghỉ tối thiểu hai đầu.
5. Đúng vị trí: tại giờ khởi hành chuyến đi, xe phải đang ở điểm xuất phát (suy ra từ chuyến gần nhất đã gán cho xe, hoặc điểm gốc của xe nếu chưa có chuyến nào).
6. Không phá chuyến kế tiếp của xe: sau chu trình xe sẽ đứng ở đâu thì chuyến sau đó của xe phải xuất phát từ đó.
7. Chỉ chuyến chưa khởi hành, giờ còn ở tương lai.

Hai điều độ viên cùng gán một xe cho hai chu trình chồng giờ: hệ thống khóa dòng xe trong giao dịch, nên đúng một người thành công, người kia nhận lý do "trùng lịch".

Xe chạy hết một chu trình kết thúc ở chính điểm xuất phát, nên chu trình sau của xe tự khớp quy tắc vị trí.

### 3.4. Ngoại lệ và sự cố (rất hiếm, giữ nhẹ)

Xe đã được bảo trì bên ngoài hệ thống trước khi chạy, nên sự cố hiếm; không dựng bộ máy phức tạp quanh nó. Chỉ có:

- **Danh sách "Cần chú ý"**: chu trình sắp chạy chưa gán xe, chuyến `gap_su_co`, chuyến bị gắn cờ xung đột vị trí. Trong phạm vi các tuyến của mình.
- **Đổi xe thay thế**: chọn một **xe dự phòng** (xe không cố định tuyến, đặt sẵn ở các văn phòng). Dùng đúng bộ quy tắc gán ở trên nên chặn như thường; xe dự phòng rảnh và đúng vị trí nên đi qua được. Xe gốc giữ nguyên, chỉ đổi `xe_thuc_te_id` như tài liệu đã mô tả (UC-20).
- **Hệ quả với khách tự động**: đổi biển số, hoãn, hoàn tiền theo mốc, vé vẫn hợp lệ. Không phải quyết định nên tự động là đúng.
- **Thang xử lý khi hết xe**: xe dự phòng → xe thuê ngoài → đổi chuyến hoặc ghép chuyến cho khách → hoãn. Không bao giờ hủy chỉ vì hết xe (nguyên tắc sẵn có).

**Không làm**: nhận xử lý, leo thang nhiều tầng, bảng điều khiển sự cố riêng, quyền riêng cho điều độ viên điểm cuối.

## 4. So sánh với tài liệu hiện tại

| | Hiện tại (theo văn phòng) | Đề xuất (theo tuyến) |
|---|---|---|
| Đơn vị gán | Từng chuyến | **Chu trình** (đi + về cùng xe) |
| Phạm vi điều độ viên | Văn phòng xuất phát của chuyến | **Các tuyến được giao** |
| Chuyến về | Do điều độ viên điểm cuối gán | Cùng xe với chuyến đi, cùng một người lo |
| Tuyến mới tạo | Tự có chủ (văn phòng đầu) | Quản lý chọn điều độ viên (một ô ở form tuyến) |
| Gắn văn phòng cho điều độ viên | Bắt buộc | Không cần |
| Sự cố | Báo điều độ viên điểm xuất phát | Báo điều độ viên của tuyến |

## 5. Thay đổi dữ liệu

```
chuyen_xe
  + chu_trinh_id UUID NULL          -- chung cho chuyến đi và chuyến về; NULL = chuyến không sinh từ lịch
  + chỉ mục (chu_trinh_id)

dieu_do_vien_tuyen                  -- bảng mới, quan hệ nhiều–nhiều
  nguoi_dung_id UUID FK nguoi_dung (ON DELETE CASCADE)
  tuyen_id      UUID FK tuyen
  PRIMARY KEY (nguoi_dung_id, tuyen_id)
```

- Sinh chuyến (UC-47): hai chuyến của một chu kỳ dùng chung `chu_trinh_id`; nếu sinh bù một chuyến đã bị xóa thì nhận lại id của chuyến còn lại.
- Các chuyến đã sinh trước đó: điền `chu_trinh_id` bằng cách ghép theo `cap_id` của lịch và `ngày đi = ngày về − ngay_lech`.
- **Không** đổi `ho_so_can_bo_diem` (vẫn một dòng cho quầy vé và gửi hàng).

## 6. Ảnh hưởng tới phần UC-36/37/38 (người làm tài khoản cán bộ)

| Chỗ | Hiện tại | Đề xuất |
|---|---|---|
| UC-36 bước 1, `NGHIEP_VU.md` | Văn phòng bắt buộc trừ `ke_toan`, `quan_ly`, `quan_ly_nhan_su` | Thêm `dieu_do_vien` vào nhóm **không gắn văn phòng** |
| Tạo tài khoản `dieu_do_vien` | Phải có `van_phong_id` | Không cần; không tạo dòng `ho_so_can_bo_diem` cho vai trò này |
| `gui_hang_service.gan_van_phong_can_bo` (`backend/app/services/gui_hang_service.py`, đang cho phép `dieu_do_vien`) | Gán văn phòng cho điều độ viên | Bỏ `dieu_do_vien` khỏi danh sách vai trò hợp lệ |
| Gán tuyến cho điều độ viên | Chưa có | Làm ở trang **Tuyến** của quản lý (chọn một hoặc nhiều điều độ viên phụ trách) |
| UC-37 khóa tài khoản `dieu_do_vien` | Chưa có cảnh báo | Nếu sau khi khóa có tuyến **không còn điều độ viên nào hoạt động** thì hiện cảnh báo "tuyến X chưa có người phụ trách" (tương tự cảnh báo "xe thiếu phụ xe" khi khóa phụ xe) |
| `quan_ly_nhan_su` | Tạo/khóa tài khoản điều độ viên | Giữ nguyên quyền tạo/khóa; **gán tuyến** chỉ `quan_ly` làm, vì tuyến là danh mục của quản lý (câu hỏi 3) |

Ngoài các dòng trên, UC-36/37/38 **không đổi**: cơ chế mời qua email, đặt mật khẩu lần đầu, phân quyền theo vai trò đều như cũ.

## 7. Các câu hỏi cần thống nhất

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| 1 | Điều độ viên không còn gắn văn phòng khi tạo tài khoản? | Có |
| 2 | Gán điều độ viên ↔ tuyến ở đâu? | Trang Tuyến (chọn một hoặc nhiều điều độ viên); trang tài khoản chỉ **xem** danh sách tuyến |
| 3 | Ai được gán tuyến cho điều độ viên? | Chỉ `quan_ly`; `quan_ly_nhan_su` chỉ tạo/khóa tài khoản |
| 4 | Tuyến chưa có điều độ viên thì sao? | Quản lý tạm xử lý + cảnh báo ở trang Tuyến |
| 5 | Khóa điều độ viên cuối cùng của một tuyến thì chặn hay chỉ cảnh báo? | Chỉ cảnh báo, như UC-37 hiện tại với phụ xe |
| 6 | Khoảng nghỉ tối thiểu giữa hai chuyến liên tiếp của một xe | 30 phút (khớp quy tắc lập cặp; tài liệu cũ ghi "VD 60 phút") |
| 7 | Cửa sổ làm việc mặc định | 3 ngày, chọn được 3, 5, 7 |
| 8 | Quy tắc vị trí xe so khớp **từng điểm** hay nới thành "cùng khu vực" | Giữ từng điểm (đơn giản, đúng lịch); nới sau nếu thực tế cần |

## 8. Lộ trình làm (đề xuất, mỗi bước chạy được riêng)

1. **Nền**: bảng `dieu_do_vien_tuyen`, ô chọn điều độ viên ở trang Tuyến, cột `chu_trinh_id` và sinh chuyến gắn chu trình, sửa UC-36 (văn phòng không bắt buộc cho điều độ viên).
2. **Gán xe theo chu trình**: API và trang Gán xe (phạm vi theo tuyến, cửa sổ 3 ngày, quy tắc mục 3.3).
3. **Ngoại lệ**: danh sách "Cần chú ý", đổi xe thay thế bằng xe dự phòng, báo sự cố theo tuyến, nhắc chu trình chưa gán xe.
4. **Gán hàng loạt** theo khoảng ngày, xe luân phiên.
5. *(Tùy chọn)* Cho khách tự đổi chuyến khi chuyến bị hoãn hoặc sự cố.

Sau mỗi bước cập nhật tài liệu cũ liên quan (`NGHIEP_VU.md` mục 2, 3.3, 3.5, 8.6, UC-17/19/20/44; `DATABASE.md`; `ERD.dbml`; `UML_DIAGRAMS.md`; `ARCHITECTURE.md`).

## 9. Đã có sẵn để tái dùng

Một bản thử nghiệm của hướng cũ (theo văn phòng) đã làm và kiểm tra xong, lưu ở nhánh `feature/vanh-dieu-do-huong-c-luu` (commit `231b2e4`, `1493cb7`, chưa push). Tái dùng được gần hết: cột `chu_trinh_id` và sinh chuyến, bộ quy tắc gán xe (`danh_gia_xe`), khóa dòng chống tranh chấp, trang Gán xe, 29 test. Chỉ cần đổi hàm tính phạm vi (từ văn phòng sang tuyến) và người nhận cảnh báo sự cố.

## 10. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Quên chọn điều độ viên khi tạo tuyến mới → tuyến vô chủ | Cảnh báo ở trang Tuyến; quản lý xử lý thay |
| Một điều độ viên lo quá nhiều tuyến | Một tuyến có nhiều điều độ viên; có thể thêm "nhóm tuyến" sau mà không phải làm lại |
| Nhiều điều độ viên cùng một tuyến làm trùng việc | Khóa dòng ở DB; người sau thấy chu trình đã có xe |
| Đổi hướng đụng phần đang làm của người khác | Mục 6 liệt kê chính xác; bàn trước khi tiến hành |
