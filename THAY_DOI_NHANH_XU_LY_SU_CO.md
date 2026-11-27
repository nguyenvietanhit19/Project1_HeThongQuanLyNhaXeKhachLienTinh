# Thay đổi trên nhánh `feature/vanh-xu-ly-su-co`

- **Người thực hiện:** Vanh (cùng Claude Code)
- **Tạo nhánh từ:** `main` tại commit `6cde8b3` (PR #67), lúc 08:34 ngày 26/11/2026
- **Cập nhật tài liệu này:** 17:40 ngày 27/11/2026
- **Giờ ghi trong tài liệu:** giờ Việt Nam (UTC+7)

Nhánh này ban đầu mở để làm phần **xử lý khi xe gặp sự cố, trước giờ chạy và khi đang chạy**. Trong lúc rà soát, chúng tôi phát hiện cách hệ thống tự tính khách **"không đến"** theo giờ trên lịch gây phạt oan khi chuyến trễ. Phần này được ưu tiên sửa trước. Phần sự cố còn lại mới dừng ở mức đề xuất (xem [mục 5](#5-đã-bàn-nhưng-chưa-làm)).

**Ai cần đọc:**
- Người phụ trách **quầy vé** và **phụ xe**: mục 3 và mục 6. Code của hai phần này bị sửa.
- Người phụ trách **điều độ viên**: mục 2.

---

## 1. Lịch sử thay đổi và trao đổi

| Thời gian | Việc | Kết quả |
|---|---|---|
| 26/11 08:34 | Tạo nhánh, rà soát nghiệp vụ sự cố (UC-17, 19, 20, 41) so với code | Lập bảng những gì đã có và còn thiếu (mục 5) |
| 26/11 08:46 – 08:51 | Dữ liệu mẫu trên **DB dev** không theo lịch chạy và chu trình | Sinh lại theo đúng lịch. Chỉ sửa DB dev, **không có trong git** (mục 4) |
| 26/11 08:57 | Thắc mắc vì sao chuyến ngày 06/11 đã gán xe không hiện ở trang Gán xe | Đúng thiết kế: trang chỉ hiện chu trình sắp chạy hoặc đang hoãn. Không sửa code |
| 26/11 09:03 – 09:05 | Trang Gán xe chưa có tìm kiếm và bộ lọc | **Đã làm** thanh tìm kiếm và bộ lọc (mục 2) |
| 26/11 09:07 | Cảnh báo của chuyến đã qua lâu không còn tác dụng | Đề xuất mục "Quá hạn, chờ chốt" và chức năng "Dời giờ" |
| 26/11 09:47 | Vanh **không muốn có "Dời giờ"**: xe không có khách vẫn phải chạy, nên điều độ viên luôn phải gán xe | Bỏ đề xuất "Dời giờ" và "Quá hạn". Liệt kê ngoại lệ A–D. Phát hiện **2 lỗi** của job tự động |
| 26/11 09:58 | Chạy lại 2 lỗi trên bản sao DB, với ví dụ An, Bình, Chi | **Cả hai lỗi xảy ra thật** (mục 3.1) |
| 26/11 10:03 | Vanh đề xuất: **phụ xe thao tác xong mới tính "không đến"**, không dựa vào mốc giờ cứng | Đồng ý. Kế hoạch: bỏ 2 job, đánh dấu khi xe tới điểm kế tiếp |
| 26/11 10:06 | Vanh chốt: tính "không đến" **ngay khi phụ xe bấm "Bắt đầu di chuyển" và tích từng người**, vì phụ xe có thể linh động đợi (VD 10:00 → 10:10) | Đồng ý. Đề xuất thêm nút **Hoàn tác** và **chặn đi sớm** |
| 27/11 13:46 | Kiểm tra các job tự động liên quan tới phụ xe | 10 job, trong đó 2 job tự đổi vé khách |
| 27/11 13:55 | Vanh chốt: chỉ bỏ 2 job, giữ các job khác. **Đồng ý** nút Hoàn tác và chặn đi sớm | Bắt đầu code |
| 27/11 13:57 – 14:01 | Sửa code, tài liệu và test | **Đã làm** (mục 3). 14/14 kiểm tra trên bản sao DB đạt |
| 27/11 14:13 – 17:35 | Giải thích 3 chỗ phải sửa theo: thu tiền mặt, vé giữ tạm, thống kê quầy vé | Vanh **đồng ý bỏ mốc 5 phút** khi thu tiền mặt. Không sửa thêm |
| 27/11 17:39 | Viết tài liệu này, commit và push | |

---

## 2. Trang Gán xe: tìm kiếm và bộ lọc (26/11 09:05)

**Vấn đề:** điều độ viên phải cuộn qua toàn bộ chu trình mới tìm được chuyến cần xử lý.

**Đã làm:**
- **Ô tìm kiếm** theo mã chuyến, biển số (kể cả xe chạy thay), tên hoặc mã tuyến, điểm đi/đến, loại xe.
  - Không cần gõ dấu: "bac ha" tìm ra "Bắc Hà".
  - Không cần gạch ngang hay khoảng trắng: "29k177777" tìm ra "29K1 - 77777".
  - Gõ nhiều từ thì kết quả phải khớp tất cả các từ. Bấm Esc để xóa.
- **Ô chọn:** tuyến (chỉ hiện khi phụ trách từ 2 tuyến), loại xe, khoảng ngày (3/5/7 ngày tới), ngày khởi hành.
- **Nút lọc theo tình trạng, kèm số lượng:** Tất cả · Cần chú ý · Chưa gán xe · Đang hoãn · Đã gán xe · Xe chạy thay.
- **Khi đang lọc:** có nút "✕ Xóa lọc" và dòng "Đang hiện X / Y chu trình".
- **Không tìm thấy** khi đang xem 3 hoặc 5 ngày: có nút "Tìm trong 7 ngày tới".
- **Nhớ bộ lọc** trong cùng tab trình duyệt.
- **Bấm vào thông báo** về một chuyến đang bị lọc ẩn thì trang tự bỏ lọc để hiện chuyến đó.
- Mục "Cần chú ý" lọc theo từ khóa, tuyến, loại xe và ngày, nhưng không lọc theo nút tình trạng.

**Giới hạn:** chỉ tìm trong dữ liệu trang đang tải, gồm chuyến sắp chạy trong tối đa 7 ngày và chuyến đang hoãn. Chuyến đã chạy qua thì không tìm được ở đây.

**File:** `frontend/nhan-vien/dieu-do/gan-xe.html`, `gan-xe.js`, `gan-xe.css`. Chỉ sửa giao diện, không sửa backend.

**Kiểm tra:** 25 kiểm tra bằng trình duyệt giả lập (jsdom) với dữ liệu dev, đều đạt.

---

## 3. "Không đến" do phụ xe xác nhận, bỏ 2 job tự động (27/11 13:57 – 14:01)

### 3.1. Vấn đề

**Ví dụ:** chuyến 11:30 tuyến Hà Nội – Bắc Hà, đón ở Mỹ Đình lúc 11:30 và Nội Bài lúc 12:00. Tới 11:30 chưa có xe nên chuyến chuyển **"đang hoãn"**, tới 13:00 mới có xe.

| Khách | Vé | Đón ở |
|---|---|---|
| An | Đã trả tiền | Mỹ Đình |
| Bình | Đã trả tiền | Nội Bài |
| Chi | Giữ chỗ, trả tiền tại quầy | Nội Bài |

**Lỗi 1, job `quet_no_show`** (mỗi phút): còn 5 phút tới giờ đón ở một điểm mà khách chưa lên xe thì đánh dấu "không đến". Job chỉ nhìn **giờ trên lịch**, không xét xe đã chạy hay chưa.
- 11:55, **Bình bị tính "không đến"** dù xe chưa được gán.
- Bình nhận thông báo, bị cộng 1 lần vi phạm (đủ 3 lần trong 30 ngày thì bị khóa thanh toán tại quầy), và mất quyền hủy để nhận hoàn tiền.

**Lỗi 2, job `quet_ve_qua_gio_chay`** (mỗi phút): chuyến qua giờ khởi hành thì hủy mọi vé giữ chỗ chưa trả tiền.
- 11:30, **vé của Chi bị hủy** và ghế được mở bán lại.
- Kể cả khi chuyến chạy đúng giờ, Chi bị hủy từ 11:30, trong khi 12:00 xe mới tới điểm của Chi. Điều này trái với `NGHIEP_VU.md`, nơi ghi vé được giữ tới giờ tại điểm đón.

Cả hai lỗi đã được **chạy lại trên bản sao DB dev** lúc 26/11 09:58 và đều xảy ra thật.

### 3.2. Quyết định đã chốt

| Quyết định | Lý do |
|---|---|
| **Không có job tự đánh dấu "không đến"** | Chỉ người trên xe biết khách có tới hay không. Giờ trên lịch sai khi xe trễ hoặc hoãn |
| Đánh dấu **ngay lúc phụ xe bấm "Bắt đầu di chuyển" và tích từng khách** | Phụ xe linh động đợi khách (VD xe 10:00 đợi tới 10:10). Khi tích là phụ xe đã quyết định bỏ khách lại |
| Vé **trả tại quầy chưa trả tiền** cũng chuyển "không đến" | Trước đây job hủy vé xử lý những vé này. Bỏ job thì phải có chỗ xử lý thay, đúng như `NGHIEP_VU.md` |
| Vé đang **giữ tạm có hạn** (khách đang thanh toán dở) **không** bị tính | Những vé này tự hết hạn |
| **Có nút Hoàn tác** khi xe chưa tới điểm kế tiếp | Để sửa khi phụ xe tích nhầm hoặc khách đuổi kịp xe |
| **Chặn đi sớm:** ở điểm đón dọc đường, còn khách chưa lên thì chưa được rời trước giờ đón dự kiến | Để khách đến đúng hẹn không bị phạt. Sau giờ đó phụ xe đợi bao lâu tùy ý. Điểm xuất phát không bị ảnh hưởng vì vốn không được chạy trước giờ |
| Chỉ bỏ 2 job trên, **giữ các job khác** | Các job khác không tự đổi vé theo giờ khởi hành |
| **Không có "Dời giờ"** | Chuyến trễ đã có luồng sẵn: đang hoãn → gán xe → phụ xe xác nhận xuất phát muộn |
| **Bỏ mốc 5 phút khi thu tiền mặt**, kể cả với chuyến đúng giờ (chốt 27/11 17:31) | Phụ xe linh động đợi, nên quầy thu được cho tới khi phụ xe rời điểm |

**Khác so với đề xuất ban đầu:** nút Hoàn tác **chỉ dùng được cho vé đã trả tiền**. Vé chưa trả tiền không được ghi nhận lên xe, và khi xe đang chạy thì khách cũng không ra quầy trả được. Phụ xe cần cẩn thận khi tích khách chưa trả tiền.

### 3.3. Cách chạy sau khi sửa

| Tình huống | Kết quả |
|---|---|
| Chuyến chưa chạy hoặc đang hoãn | Không ai bị tính "không đến". Vé giữ chỗ không bị hủy |
| Bấm "Bắt đầu di chuyển" khi còn khách chưa lên | Phải tích từng người. Người được tích chuyển "không đến" ngay, bị ghi 1 lần vi phạm (nếu có tài khoản) và được báo |
| Bấm "Ở lại xử lý tiếp" | Không ai bị tính |
| Điểm đón dọc đường, chưa tới giờ đón dự kiến, còn khách chưa lên | Nút đi bị khóa, kèm giờ được đi. Backend cũng chặn |
| Xe đang đi, chưa tới điểm kế tiếp, vé đã trả tiền | "Hoàn tác, khách đã lên xe": vé chuyển "đã lên xe", gỡ vi phạm, gỡ khóa thanh toán tại quầy nếu khóa do chính lần này, báo khách |
| Bấm "Đã đến" ở điểm kế tiếp | Không đánh dấu ai nữa |

### 3.4. Ba chỗ phải sửa theo khi bỏ 2 job

Nếu chỉ bỏ job mà không sửa ba chỗ này, hệ thống sẽ sai ở nơi khác.

**a) Thu tiền mặt tại quầy (phần quầy vé)**
- **Trước:** chỉ thu được khi chuyến chưa tới giờ khởi hành **và** còn hơn 5 phút tới giờ đón.
- **Vấn đề:** Chi giữ được vé (vì không còn job hủy) nhưng quầy lại không thu được tiền. Lúc 13:00 xe tới, Chi không được lên xe.
- **Sau:** thu được khi vé còn "giữ chỗ" và chuyến chưa hoàn thành, chưa hủy. Các điều kiện khác giữ nguyên: đúng văn phòng tại điểm đón, đã trả cọc nếu lượt đặt yêu cầu cọc.

**b) Vé giữ tạm có hạn**
- **Vé này là gì:** khách bấm "Tiếp tục" thì ghế được giữ 10 phút. Khi đang thanh toán VNPay thì giữ theo hạn của cổng thanh toán.
- **Trước:** hai job chia việc. Job `quet_ve_het_han` lo chuyến **chưa** qua giờ khởi hành, job hủy vé lo chuyến **đã** qua.
- **Ví dụ:** 11:22 An giữ ghế chuyến 11:30 rồi bỏ đi. 11:32 hết hạn, lúc này chuyến đã qua giờ. Bỏ job hủy vé thì **không job nào dọn**, vé nằm ở "giữ chỗ" mãi.
- **Sau:** `quet_ve_het_han` dọn mọi vé quá hạn giữ, không xét giờ khởi hành.

**c) Thống kê và in vé ở quầy**
- **Trước:** chỉ vé đã trả tiền mới có thể thành "không đến", nên quầy coi mọi vé "không đến" là đã bán.
- **Vấn đề:** giờ vé chưa trả tiền cũng có thể "không đến". Ví dụ Bình (đã trả 200.000đ) và Chi (chưa trả) cùng "không đến": cách cũ tính 2 vé và 400.000đ, thừa 200.000đ không có thật. Nhân viên cũng in được vé của Chi dù Chi chưa trả đồng nào.
- **Sau:** vé "không đến" chỉ tính là đã bán và in được khi **có ghi nhận giờ thu tiền** (`gio_thanh_toan`). Trang Thống kê của quản lý vốn đã tính theo cách này.

### 3.5. Chưa thay đổi

Khi chuyến trễ, ba thao tác sau **vẫn tính theo giờ trên lịch**:
- quầy tạo mã QR;
- khách tự trả online;
- khách tự hủy vé giữ chỗ.

Vì vậy khách của chuyến trễ hiện chỉ trả được bằng **tiền mặt tại quầy**.

### 3.6. File đã sửa

| Nhóm | File | Thay đổi |
|---|---|---|
| Job | `backend/app/main.py` | Bỏ đăng ký 2 job |
| | `backend/app/jobs/quet_no_show.py`, `quet_ve_qua_gio_chay.py` | **Xóa** |
| | `backend/app/jobs/quet_nhac_sap_di.py` | Sửa chú thích |
| Phụ xe | `backend/app/services/khong_den_service.py` | **Mới.** Đánh dấu và hoàn tác "không đến", ghi và gỡ vi phạm, khóa và mở khóa thanh toán tại quầy (3 lần trong 30 ngày) |
| | `backend/app/services/di_chuyen_service.py` | Đánh dấu khi "Bắt đầu di chuyển", chặn đi sớm, hàm hoàn tác |
| | `backend/app/services/chuyen_xe_service.py` | Bỏ đánh dấu khi "Đã đến". Thêm hàm giờ đón dự kiến tại điểm |
| | `backend/app/routes/phu_xe.py` | API mới `POST /phu-xe/chuyen/{chuyen_id}/ve/{ve_id}/hoan-tac-khong-den`. Thông báo xuất phát kèm số khách "không đến" |
| | `backend/app/schemas/chuyen_xe_schema.py` | Thêm `da_tra_tien` vào danh sách khách |
| | `frontend/nhan-vien/phu-xe/chuyen-dang-chay.html` | Nút Hoàn tác, khóa nút đi sớm, sửa câu nhắc (không còn "hệ thống sẽ tự đánh dấu") |
| Vé | `backend/app/repositories/ve_repository.py` | Đánh dấu cả vé trả tại quầy chưa trả, hàm hoàn tác |
| | `backend/app/repositories/ho_so_khach_hang_repository.py` | Mở khóa thanh toán tại quầy |
| | `backend/app/services/thong_bao_khach_service.py` | Thông báo hoàn tác, bỏ thông báo hủy vé quá giờ |
| Quầy vé | `backend/app/repositories/ve_lock_repository.py` | Thu tiền mặt không chặn theo giờ. Job hết hạn dọn mọi chuyến |
| | `backend/app/services/quay_ve_service.py` | Bỏ chặn theo giờ khi thu tiền mặt |
| | `backend/app/repositories/quay_ve_repository.py` | 14 câu truy vấn: "không đến" chỉ tính khi đã thu tiền |
| | `backend/app/routes/quay_ve.py` | Chỉ in vé khi đã thu tiền |
| Tài liệu | `NGHIEP_VU.md` | Sơ đồ trạng thái vé, mục 8.2 điểm 6, mục 9, nhánh UC-14 |
| | `ARCHITECTURE.md` | Mục 5: bảng chuyển trạng thái vé và job |
| Test | `test_quet_no_show.py`, `test_quay_ve_tu_huy_qua_gio.py` | **Xóa** (test của 2 job đã bỏ) |
| | `test_quay_ve_thanh_toan_ve_tre.py` | **Mới.** Giữ lại phần kiểm tra VNPay vẫn đúng từ file cũ |
| | `test_di_chuyen_service.py`, `test_chuyen_xe_service.py`, `test_phu_xe_chieu_nguoc.py`, `test_thong_bao_khach.py`, `test_quay_ve_bieu_do_thong_ke.py` | Cập nhật theo quy tắc mới |

---

## 4. Dữ liệu mẫu trên DB dev (26/11 08:46 – 08:51, không có trong git)

**Vấn đề:** dữ liệu mẫu cũ không theo giờ của lịch chạy và không theo chu trình đi–về.

**Đã làm:** chạy một script tạm (đã xóa sau khi chạy).
- **Xóa:** dữ liệu mẫu cũ (38 chuyến, 360 vé, các đơn hàng và thông báo đi kèm).
- **Sinh lại** cho mỗi cặp lịch chạy, từ 16 ngày trước tới 4 ngày sau: 80 chu trình (160 chuyến), 1.494 vé, 14 đơn hàng, 13 khoản hoàn, 3 biên chế.
- **Có thêm các tình huống:** chuyến hủy giữa đường, chuyến gặp sự cố, chu trình đang hoãn, chu trình chưa gán xe, chu trình có xe chạy thay.
- **Giữ nguyên:** 80 chuyến Vanh tự sinh. Mọi dòng mẫu có id bắt đầu bằng `de000000-`.

---

## 5. Đã bàn nhưng chưa làm

**Sự cố trước giờ chạy** (đề xuất 26/11 09:48):

| Ngoại lệ | Hiện tại | Đề xuất | Trạng thái |
|---|---|---|---|
| A. Chưa tìm được xe | Giữ "đang hoãn" | Hoãn quá 6 tiếng thì báo quản lý | Chưa làm |
| B. Đã gán xe, tới giờ thì xe hỏng | **Bị kẹt:** quá giờ khởi hành thì không đổi xe được | Cho đổi xe khi chuyến chưa xuất phát, kể cả đã quá giờ. Cảnh báo "quá giờ 30 phút chưa xuất phát" | Chưa làm |
| C. Bất khả kháng (bão lũ, sạt lở) | Chưa có cách hủy | Chỉ quản lý được hủy, bắt buộc ghi lý do, hoàn 100% | Chờ Vanh chốt "chỉ quản lý" |
| D. Xe đã chạy nhưng không ghi nhận được | Chuyến treo ở "Chưa khởi hành" | Quản lý xác nhận đã chạy | Chờ chốt có làm hay không |

**Sự cố khi đang chạy** (rà soát 26/11 08:35):
- Chuyến đã báo sự cố **bị kẹt ở `gap_su_co`**, không có thao tác chạy tiếp.
- Chưa có điều xe thay giữa đường.
- Chưa có hủy chuyến vì sự cố khách quan kèm hoàn tiền.
- Chưa có job tự hoàn tiền khi lỗi nhà xe kéo dài từ 3 tiếng, và chưa có cột lưu giờ báo sự cố.
- Khách tự hủy vé đã trả tiền (UC-41) đang bị từ chối, dù thông báo gửi khách ghi là được hủy.
- 4 câu hỏi chờ chốt: ai xác nhận chạy tiếp, chặn cứng hay chỉ cảnh báo mốc 3 tiếng, phạm vi xe thay, làm theo đợt hay làm liền.

**Khác:**
- Mở QR và trả online cho chuyến trễ (mục 3.5).
- Trang tra cứu chuyến đã chạy cho điều độ viên.

---

## 6. Kiểm tra

- **Bản sao DB dev, code thật, ví dụ An/Bình/Chi:** 14/14 đạt.
  - Vé giữ chỗ còn nguyên khi chuyến hoãn.
  - Thu được tiền mặt sau giờ khởi hành.
  - Rời điểm khác không đánh dấu nhầm.
  - Chặn đi sớm. Bắt buộc tích xác nhận.
  - Đánh dấu đúng người.
  - Doanh thu quầy không tính vé chưa trả.
  - Các câu truy vấn quầy vé chạy được.
  - Quy tắc hoàn tác đúng.
  - Vé giữ tạm quá hạn được dọn.
- **Unit test:** 1.306 đạt, 19 lỗi. 19 lỗi này **có từ trước khi sửa**, cùng số lượng và cùng 4 file: `test_lich_su_ve`, `test_thong_bao_khach` (IPN), `test_ve_le`, `test_vnpay_truy_van`. 30 test của các phần vừa sửa đều đạt (chạy lại 27/11 17:36).
- **Chưa kiểm tra:**
  - Trang phụ xe chưa thử trên trình duyệt thật, mới kiểm tra cú pháp.
  - API in vé chưa có test riêng.

**Cách thử trên trình duyệt** (đăng nhập phụ xe, mở chuyến đã tới giờ chạy và còn khách chưa lên):
1. Bấm Xuất phát, tích khách chưa lên, xác nhận. Khách đó phải hiện "Không đến".
2. Khi xe đang chạy, bấm "Hoàn tác, khách đã lên xe" ở khách vừa tích (vé đã trả tiền).
3. Tới một điểm đón dọc đường sớm hơn giờ dự kiến khi còn khách chưa lên. Nút đi phải bị khóa.

**Trước khi merge:** cần báo người phụ trách **quầy vé** và **phụ xe**, vì code của hai phần này bị sửa (mục 3.4 và 3.6).
