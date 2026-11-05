# Hàng gửi khi chuyến bị hủy giữa đường — tài liệu để nhóm chốt

> **Trạng thái: CHƯA CHỐT.** Tài liệu này liệt kê các trường hợp và đề xuất phương án để nhóm thảo luận.
> Khi nhóm chốt xong, nội dung sẽ được chép vào `NGHIEP_VU_GUI_HANG.md` (ký hiệu 🆕) và các quyết định ghi vào mục 6 dưới đây.
>
> Người soạn: nhân viên gửi hàng (người 5), 05/11/2026. Liên quan: người 3 (phụ xe), người 4 (điều độ viên), người 1 (quản lý).

---

## 1. Vấn đề

`NGHIEP_VU.md` đã quy định đầy đủ việc **hành khách** khi chuyến gặp sự cố (UC-17, UC-19, UC-41, mục 7), nhưng **chưa nói gì về hàng gửi** đang nằm trên xe.

Với 3 kết cục của UC-19, chỉ có 1 kết cục gây vấn đề cho hàng:

| Kết cục UC-19 | Với hàng trên xe | Cần chốt? |
|---|---|---|
| Sửa tại chỗ, chuyến chạy tiếp | Đơn vẫn `da_len_xe`, chỉ tới trễ | Không |
| Điều xe khác tới thay, **vẫn là chuyến đó** | Phụ xe chuyển hàng sang xe mới, đơn vẫn thuộc chuyến cũ | Không (chỉ cần kiểm đếm, xem 2.2) |
| **Hủy phần còn lại** (chỉ `loi_khach_quan`, điều độ viên xác nhận không thể hoàn thành) | Đơn kẹt ở `da_len_xe` trên 1 chuyến `da_huy`: **không ai dỡ được, không ai giao được** | **Có — tài liệu này** |

Theo UC-19, sự cố **lỗi nhà xe không bao giờ bị hủy** (luôn tìm được xe thay thế), nên vấn đề chỉ xảy ra với **sự cố khách quan** (thiên tai, sạt lở…).

## 2. Hiện trạng trong code (05/11/2026)

### 2.1. Đã có
- Phụ xe báo sự cố (UC-17) → chuyến `gap_su_co`, báo khách có vé + điều độ viên.
- Màn "Hàng đến" của văn phòng nhận gắn nhãn "⚠️ Chuyến gặp sự cố" / "⛔ Chuyến đã hủy" cho đơn đang trên chuyến đó (chỉ hiển thị, không có thông báo).
- *Đã làm thử rồi bỏ (05/11/2026), lưu ở nhánh local `feature/Trinh-gui-hang-su-co-xe-luu`:* báo văn phòng gửi + nhận khi chuyến chở hàng gặp sự cố / chạy lại / bị hủy, nút ghi cuộc gọi báo trễ, nhãn + bộ lọc ở "Đơn gửi đi". Có thể lấy lại nếu nhóm cần.

### 2.2. Chưa có (thuộc người khác)
- **UC-19 chưa có code**: chưa có thao tác điều xe thay thế, cho chuyến chạy tiếp, hay hủy chuyến giữa đường. Hiện chuyến vào `gap_su_co` là đứng luôn ở đó.
- Khi đổi xe giữa đường: chưa có bước phụ xe **kiểm đếm hàng** khi chuyển sang xe mới (kiện thiếu → báo thất lạc theo UC-28 đã có).

### 2.3. Trong lúc chờ chốt
Đơn nằm trên chuyến `da_huy` **không bị tự động đổi trạng thái gì**. Văn phòng nhận (và quản lý khi xem màn "Hàng đến") thấy đơn đó gắn nhãn "⛔ Chuyến đã hủy" để xử lý thủ công (gọi điện); văn phòng gửi hiện chưa có nhãn này.

## 3. Các yếu tố làm phát sinh nhiều trường hợp

| # | Yếu tố | Các khả năng |
|---|---|---|
| Y1 | Vị trí xe khi bị hủy | Gần văn phòng gửi · giữa đường · gần văn phòng nhận |
| Y2 | Xe còn quay đầu được không | Quay về văn phòng phía sau được · kẹt hẳn tại chỗ |
| Y3 | Chuyến sau cùng tuyến có đi qua được không | Đường thông lại trong 1–2 ngày · chặn lâu, không biết bao giờ |
| Y4 | Loại hàng | Thường · dễ vỡ · **hàng lạnh / dễ hỏng** (không chờ lâu được) · tài liệu |
| Y5 | Ý người gửi | Muốn chờ chở tiếp · muốn lấy lại hàng |
| Y6 | Cước | Trả trước (đã thu ở văn phòng gửi) · người nhận trả (COD, chưa thu) |
| Y7 | Mỗi chuyến chở nhiều đơn | Các đơn có thể có văn phòng nhận khác nhau, người gửi khác nhau |

## 4. Câu hỏi cần nhóm chốt

### Q1. Hàng trên xe đi đâu ngay sau khi hủy chuyến?

| Phương án | Mô tả | Ưu | Nhược / tác động code |
|---|---|---|---|
| **A. Về văn phòng gần nhất** (đề xuất) | Xe (hoặc phương tiện khác) đưa hàng về **văn phòng gần nhất trên tuyến** mà đi tới được; văn phòng đó giữ hàng tạm | Hàng có người trông giữ, có quầy để người gửi/nhận tới; khớp quy tắc "2 đầu đều là văn phòng" | Cần thêm khái niệm **"văn phòng đang giữ hàng"** khác `diem_gui_id` (vì UC-26 chỉ cho chất hàng tại `diem_gui_id`) — 1 cột mới + sửa điều kiện chất hàng của phụ xe |
| B. Phụ xe giữ, bàn giao thẳng cho chuyến sau | Hàng ở lại trên xe hỏng / với phụ xe, chuyến sau cùng tuyến tới thì chuyển sang | Không cần văn phòng trung gian | Không ai trông hàng nếu chờ lâu; chuyến sau có thể cũng không qua được (Y3); khó kiểm soát |
| C. Luôn trả về văn phòng gửi | Mọi hàng quay về nơi gửi | Đơn giản nhất, dùng lại được UC-54 (hủy + hoàn cước) | Có thể rất xa (xe gần tới nơi nhận vẫn phải quay về); hàng lạnh không kịp |

### Q2. Sau khi hàng đã về văn phòng giữ tạm (nếu chọn A), xử lý từng đơn thế nào?

Đề xuất: văn phòng giữ hàng **gọi người gửi** (kênh duy nhất là điện thoại, nguyên tắc 2) và chọn 1 trong 2:

| Lựa chọn của người gửi | Xử lý | Đơn |
|---|---|---|
| **Chờ chở tiếp** | Đơn quay lại hàng chờ chất, **chờ tại văn phòng đang giữ hàng**; chuyến sau cùng tuyến (khi đường thông) chất lên như bình thường | `cho_van_chuyen` (bỏ `chuyen_id`) — tới nơi thì giao như thường |
| **Lấy lại hàng** | Người gửi tới văn phòng đang giữ hàng (hoặc văn phòng gửi nếu hàng đã về đó) nhận lại | `da_huy` với lý do mới "chuyến bị hủy giữa đường" |

Không liên hệ được người gửi → giữ hàng chờ, áp dụng mốc nhắc giống UC-25 (7 ngày nhắc, 14 ngày báo quản lý).

**Hàng lạnh / dễ hỏng (Y4):** đề xuất ưu tiên gọi người gửi **ngay khi chuyến báo sự cố** (không chờ tới lúc hủy), để người gửi quyết sớm.

### Q3. Tiền cước

| Trường hợp | Đề xuất | Lý do |
|---|---|---|
| Lấy lại hàng, cước **trả trước** | Hoàn **100% cước tiền mặt** tại văn phòng trả hàng | Giống vé khách: dịch vụ chắc chắn không hoàn thành thì hoàn 100% (`NGHIEP_VU.md` mục 7), không tính theo đoạn đường đã đi |
| Lấy lại hàng, cước **COD** | Không thu, không hoàn | Chưa thu đồng nào |
| Chờ chở tiếp | Không thu thêm, không hoàn | Dịch vụ vẫn được hoàn thành, chỉ trễ — giống nguyên tắc "khách quan thì không bồi thường vì trễ" |
| Trễ do **lỗi nhà xe** (đổi xe, ≥ 3 tiếng) | **Cần nhóm chốt**: có hoàn cước như vé (UC-19 nhánh ≥ 3 tiếng) không? Đề xuất **không** — cước hàng không cam kết giờ tới, hàng vẫn tới nơi | Khác vé: người gửi không phải ngồi chờ trên xe |

Tiền hoàn đi theo luồng tiền mặt tại quầy như UC-54 (không qua kế toán), ghi vào văn phòng chi tiền.

### Q4. Ai quyết định?

| Việc | Đề xuất người làm |
|---|---|
| Hủy chuyến, chọn văn phòng giữ hàng cho cả chuyến | **Điều độ viên** (cùng lúc thao tác hủy ở UC-19) |
| Chở hàng về văn phòng giữ tạm, bàn giao + kiểm đếm | **Phụ xe** (xác nhận "đã bàn giao" từng kiện, kiện thiếu → UC-28) |
| Gọi người gửi, chọn chờ tiếp / lấy lại, trả hàng, hoàn cước | **Nhân viên gửi hàng** tại văn phòng đang giữ hàng |
| Báo người nhận hàng sẽ tới trễ / không tới | **Nhân viên gửi hàng** văn phòng nhận (đã có thông báo ở phần A) |

### Q5. Đổi xe giữa đường (không hủy) — có bắt phụ xe kiểm đếm hàng khi chuyển xe không?

Đề xuất **có**: màn phụ xe hiện danh sách đơn đang trên chuyến, phụ xe tích từng kiện đã chuyển sang xe mới; kiện không tích → báo thất lạc (UC-28 đã có). Việc này thuộc người 3 + người 4.

## 5. Tác động tới từng người (nếu chọn đúng các phương án đề xuất)

| Người | Việc phải làm thêm |
|---|---|
| Người 4 (điều độ viên) | UC-19 nhánh hủy: chọn văn phòng giữ hàng; gọi hàm của người 5 để báo văn phòng + chuyển đơn |
| Người 3 (phụ xe) | Màn bàn giao hàng về văn phòng giữ tạm (kiểm đếm); màn kiểm đếm khi đổi xe (Q5) |
| Người 5 (gửi hàng) | Cột "văn phòng đang giữ hàng" + sửa điều kiện chất hàng; màn "Hàng giữ tạm" tại văn phòng; 2 lựa chọn chờ tiếp / lấy lại + hoàn cước; lý do hủy mới |
| Người 1 (quản lý) | Không đổi (chỉ xem); nhận báo cáo khi không liên hệ được ai (đã có) |

## 6. Quyết định của nhóm

| # | Câu hỏi | Nhóm chốt | Ngày |
|---|---|---|---|
| Q1 | Hàng đi đâu sau khi hủy | | |
| Q2 | Xử lý từng đơn tại văn phòng giữ tạm | | |
| Q3 | Tiền cước (kể cả lỗi nhà xe ≥ 3 tiếng) | | |
| Q4 | Ai quyết định từng việc | | |
| Q5 | Kiểm đếm hàng khi đổi xe giữa đường | | |
