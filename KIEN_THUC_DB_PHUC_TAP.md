# Kiến thức cơ sở dữ liệu "khó" trong dự án — sổ tay đọc lại khi quên

> Viết cho chính người làm dự án (đọc lại sau một thời gian). Tổng hợp mọi thứ liên quan DB phức tạp đã làm/sửa:
> đặt chỗ, sửa giá, hệ số giá, sinh chuyến, lịch chạy, loại xe, mã tự sinh, migration.
> Mỗi phần có: **bài toán → ví dụ đời thường → cách giải trong dự án → vì sao chọn cách đó → chỗ trong code → giới hạn còn lại.**
> Cập nhật theo trạng thái code ngày 2026-10-19 (nhánh `feature/vanh-khoa-he-so-loai-xe`).

## Mục lục

1. [Khái niệm nền (đọc phần này trước)](#1-khái-niệm-nền)
   - 1.1 Giao dịch · 1.2 **Khóa bi quan vs khóa lạc quan** · 1.3 Cô lập, MVCC, snapshot · 1.4 Ba kiểu lỗi đồng thời hay gặp · 1.5 Dữ liệu bất biến và "chụp lại" · 1.6 Ràng buộc UNIQUE làm chốt chặn
2. [Bảng chọn công cụ: gặp tình huống nào dùng gì](#2-bảng-chọn-công-cụ)
3. [Từng chức năng](#3-từng-chức-năng)
   - 3.1 Giữ ghế / đặt chỗ · 3.2 Mã tự sinh · 3.3 Bộ giá vé · 3.4 Hệ số giá của lịch và "chốt vào chuyến" · 3.5 Làm tròn 10.000đ · 3.6 Hệ số giá từng ghế · 3.7 Lịch chạy theo cặp · 3.8 Sinh chuyến · 3.9 Loại xe: khóa sơ đồ + phiên bản · 3.10 Migration
4. [Một ngày trong đời hệ thống (ví dụ xuyên suốt có số)](#4-một-ngày-trong-đời-hệ-thống)
5. [Cách kiểm thử phần đồng thời](#5-cách-kiểm-thử-phần-đồng-thời)
6. [Lỗ hổng / việc còn dở (nói thẳng)](#6-lỗ-hổng--việc-còn-dở)
7. [Từ điển thuật ngữ nhanh](#7-từ-điển-thuật-ngữ-nhanh)

---

## 1. Khái niệm nền

### 1.1 Giao dịch (transaction)

Một nhóm câu lệnh SQL được coi là **một việc duy nhất**: hoặc làm hết (`COMMIT`), hoặc hủy hết (`ROLLBACK`).

**Ví dụ:** chuyển 100.000đ từ ví A sang ví B = "trừ A" + "cộng B". Nếu trừ A xong mà mất điện, không có giao dịch thì tiền biến mất. Có giao dịch thì cả hai hoặc cùng xảy ra, hoặc cùng không.

**Trong dự án:** mọi repository làm theo mẫu `conn = get_connection()` → các `cur.execute(...)` → `conn.commit()` (lỗi thì `conn.rollback()`). Ví dụ giữ 3 ghế cho một khách: tạo 3 vé trong cùng một giao dịch, có 1 ghế bị chiếm thì **không vé nào** được tạo ("giữ đủ hoặc không giữ gì").

### 1.2 Khóa bi quan vs khóa lạc quan (khái niệm khó nhất — đọc kỹ)

Hai cách đối phó với chuyện **hai người cùng sửa một dữ liệu**.

| | **Khóa bi quan** (pessimistic) | **Khóa lạc quan** (optimistic) |
|---|---|---|
| Tư tưởng | "Chắc chắn sẽ đụng nhau → **khóa trước**, làm sau" | "Hiếm khi đụng nhau → **cứ làm**, lúc ghi mới kiểm tra" |
| Cách làm trong DB | `SELECT ... FOR UPDATE` (khóa **dòng**) | Cột `phien_ban`; `UPDATE ... WHERE phien_ban = X` |
| Người đến sau | **Chờ** đến khi người trước xong | **Không chờ**, nhưng nếu dữ liệu đã đổi thì **bị từ chối**, phải làm lại |
| Khi nào xung đột lộ ra | Không bao giờ (đã xếp hàng từ đầu) | Lúc bấm Lưu |
| Tốn gì | Giữ khóa → người khác kẹt nếu giữ lâu; có nguy cơ **deadlock** | Có thể phải làm lại nếu đụng nhau nhiều |
| Hợp khi | Đụng nhau **hay xảy ra**, thao tác **ngắn**, sai là **nghiêm trọng** | Đụng nhau **hiếm**, thao tác **dài** (người dùng mở form lâu) |

> **"Khóa dòng" nói về PHẠM VI khóa** (khóa 1 dòng của bảng, không khóa cả bảng). **"Bi quan/lạc quan" nói về CÁCH TIẾP CẬN.** Khóa bi quan trong dự án chính là khóa dòng (`FOR UPDATE`/`FOR SHARE`). Khóa lạc quan thì **không khóa gì cả**, chỉ so sánh số phiên bản.

**Ví dụ đời thường — hai người sửa một file Word**
- *Bi quan* = file Word trên ổ chia sẻ: anh A mở thì file bị khóa "đang được anh A dùng", chị B phải chờ hoặc chỉ xem. Không bao giờ sửa trùng, nhưng chị B kẹt khi anh A đi ăn trưa quên đóng file.
- *Lạc quan* = Google Docs/Git: ai cũng mở sửa thoải mái, lúc lưu hệ thống báo "file đã đổi từ lúc bạn mở" nếu có xung đột. Không ai chờ, thỉnh thoảng phải làm lại.

**Ví dụ 1 trong dự án — BI QUAN: giữ ghế** (`ve_lock_repository.py`)
```
Khách A bấm "Tiếp tục" ghế A1 → khóa dòng chuyến → ghế trống → tạo vé → nhả khóa
Khách B bấm "Tiếp tục" ghế A1 → CHỜ A xong → thấy A1 có vé → báo "ghế đã có người chọn"
```
Chọn bi quan vì: tranh ghế **hay xảy ra** (giờ cao điểm), **không làm lại được** (2 vé 1 ghế là sai nghiệp vụ), thao tác **chỉ vài mili-giây** nên chờ không đáng kể.

**Ví dụ 2 trong dự án — LẠC QUAN: sửa loại xe** (cột `loai_xe.phien_ban`)
```
Cả A và B mở form "Giường 40 chỗ", cùng thấy phiên bản 3.
A sửa ghế đầu ×1,1, bấm Lưu → DB đang là 3, khớp → ghi, nâng lên 4.
B sửa ghế cuối ×0,9, bấm Lưu (sau A) → DB đã là 4, B cầm 3 → LỆCH
   → từ chối (HTTP 409): "vừa được người khác sửa — hãy tải lại".
```
Chọn lạc quan vì: form có thể **mở vài phút** (quá lâu để giữ khóa), người sửa **rất ít** nên hiếm đụng nhau, và nếu đụng chỉ cần tải lại.

**Dự án dùng CẢ HAI ở cùng một loại xe**, vì bảo vệ hai việc khác nhau:
- Lạc quan (`phien_ban`) bảo vệ khoảng **người dùng mở form lâu** (vài phút).
- Bi quan (`FOR UPDATE`) bảo vệ khoảng **"kiểm tra rồi mới ghi"** trong server (vài mili-giây). Xem 3.9.

> Quy tắc nhớ: **giữ lâu → lạc quan; giữ ngắn mà không được sai → bi quan.**

#### Hai loại khóa dòng trong PostgreSQL (dùng ở nhiều chỗ)
| Câu lệnh | Nghĩa | Ai bị chặn |
|---|---|---|
| `FOR UPDATE` | "Tôi sắp **sửa** dòng này" (khóa độc quyền) | Mọi `FOR UPDATE` và `FOR SHARE` khác trên cùng dòng |
| `FOR SHARE` | "Tôi đang **dựa vào** dòng này, đừng sửa lúc tôi dùng" (khóa chia sẻ) | Chỉ chặn `FOR UPDATE`/sửa; **nhiều người cùng `FOR SHARE` không chặn nhau** |

Ví dụ: sinh chuyến và tạo xe đều "dựa vào" dòng loại xe (`FOR SHARE`) — nhiều người làm cùng lúc được; nhưng người đang **sửa** loại xe (`FOR UPDATE`) thì phải đợi họ xong, và họ phải đợi người sửa xong.

### 1.3 Cô lập (isolation), MVCC, snapshot

- **Cô lập** = khi nhiều giao dịch chạy cùng lúc, mỗi giao dịch **nhìn thấy dữ liệu của nhau đến mức nào**. Bốn mức: Read Uncommitted (thấy cả dữ liệu chưa lưu) → **Read Committed** (chỉ thấy dữ liệu đã lưu; **mặc định của PostgreSQL và của dự án**) → Repeatable Read (chỉ thấy như lúc bắt đầu) → Serializable (như chạy lần lượt từng cái). Càng chặt càng an toàn nhưng càng dễ phải chờ/làm lại.
- **MVCC** (Multi-Version Concurrency Control) = cách PostgreSQL thực hiện việc đó: sửa một dòng **không ghi đè** mà tạo **phiên bản mới**, giữ bản cũ; mỗi giao dịch đọc bản phù hợp với "ảnh chụp" của nó. Hệ quả hay nhất: **người đọc không chặn người ghi, người ghi không chặn người đọc.** Khách xem sơ đồ ghế không làm chậm khách khác đang đặt vé.
- **Snapshot (ảnh chụp)** — **có HAI nghĩa, đừng nhầm:**
  1. *Snapshot của database*: cơ chế MVCC bên trong, tự động.
  2. *Snapshot của ứng dụng* (cách ta hay gọi): **sao chép giá trị vào chuyến lúc sinh chuyến** (`chuyen_xe.he_so_gia`, `chuyen_xe.he_so_ghe`) để sau này sửa chỗ khác không ảnh hưởng. Cùng ý "chụp lại tại một thời điểm" nhưng do **mình viết code**, không phải DB làm. Xem 1.5.

### 1.4 Ba kiểu lỗi đồng thời hay gặp

**(a) Lost update (mất cập nhật)** — hai người đọc cùng một dữ liệu, sửa, rồi ghi đè lên nhau; thay đổi của người ghi trước biến mất mà không ai biết.
*Ví dụ:* A và B cùng mở hệ số ghế, A đặt ghế đầu ×1,1 và lưu, B đặt ghế cuối ×0,9 và lưu cả cục JSON → hệ số ghế đầu của A mất. **Chữa:** khóa lạc quan (`phien_ban`).

**(b) Check-then-act (kiểm tra rồi mới làm)** — kiểm tra điều kiện ở bước 1, nhưng **giữa bước 1 và bước 2 người khác đã làm điều kiện sai đi**.
*Ví dụ:* A kiểm tra "loại xe chưa có xe nào → được sửa sơ đồ"; ngay lúc đó B tạo xe thuộc loại này; A ghi sơ đồ mới → xe vừa tạo bị đổi sơ đồ sau lưng. **Chữa:** khóa dòng để hai thao tác xếp hàng (3.9).

**(c) Non-repeatable read (đọc không lặp lại)** — trong một giao dịch đọc cùng dữ liệu hai lần ra hai kết quả khác nhau vì người khác vừa lưu ở giữa (xảy ra ở mức Read Committed).
*Ví dụ:* sinh 10 chuyến trong một giao dịch, mỗi chuyến tự đọc hệ số ghế; giữa chừng quản lý lưu hệ số mới → 5 chuyến đầu hệ số cũ, 5 chuyến sau hệ số mới. **Chữa:** đọc **một lần** ở đầu lô + `FOR SHARE` (3.8).

Ngoài ra: **deadlock** = hai giao dịch giữ khóa của nhau và cùng chờ nhau → PostgreSQL hủy một bên. Phòng bằng cách **luôn khóa theo cùng một thứ tự** (VD sinh chuyến sắp `ORDER BY id` trước khi `FOR SHARE` nhiều loại xe).

### 1.5 Dữ liệu bất biến và "chụp lại"

Dữ liệu **đã ghi rồi không bao giờ sửa** thì **không cần khóa khi đọc** — vì không ai ghi để tranh chấp.

**Ví dụ:** `chuyen_xe.he_so_gia` và `he_so_ghe` được chốt lúc sinh chuyến rồi không đổi. Khách xem sơ đồ ghế (giá lấy từ chuyến) và lúc bấm "Tiếp tục" (giá lấy từ chính chuyến đó) **luôn ra cùng một con số** — không cần khóa, không cần mức cô lập cao. Lỗi "khách xem 300.000đ rồi thành 400.000đ" biến mất **theo thiết kế**, không phải nhờ khóa.

> Bài học thiết kế: **biến dữ liệu hay đổi thành dữ liệu bất biến (chụp lại) thì loại được cả một lớp lỗi đồng thời.** Đây là lý do `ve.gia` cũng chốt lúc giữ ghế.

### 1.6 Ràng buộc UNIQUE làm chốt chặn cuối

Dù code có sót kiểm tra, **DB vẫn từ chối** dữ liệu trùng. Là "lưới an toàn" rẻ nhất.
- `bo_gia_ve UNIQUE (tuyen_id, ap_dung_tu)`: hai quản lý cùng tạo bộ giá bắt đầu cùng một ngày → người sau bị `UniqueViolation` ("Tuyến đã có bộ giá áp dụng từ ngày …").
- `chuyen_xe.ma UNIQUE`: mã chuyến dựng từ tuyến-loại xe-ngày-giờ-chiều nên **cùng một chuyến luôn ra cùng mã** → sinh trùng bị chặn.
- `loai_xe.ten UNIQUE`, `xe.bien_so UNIQUE`, `ve.ma_ve UNIQUE`.

---

## 2. Bảng chọn công cụ

| Tình huống | Công cụ | Ví dụ trong dự án |
|---|---|---|
| Nhiều người **tranh một tài nguyên**, thao tác ngắn, sai là nghiêm trọng | Khóa dòng **bi quan** `FOR UPDATE` | Giữ ghế (khóa dòng `chuyen_xe`) |
| Người dùng **mở form lâu** rồi lưu, ít khi đụng nhau | Khóa **lạc quan** (`phien_ban`) → 409 | Sửa loại xe |
| "Kiểm tra điều kiện rồi mới ghi" phải **không bị chen ngang** | `FOR UPDATE` trong **cùng giao dịch** với kiểm tra | `sua_loai_xe` |
| Đang **dựa vào** một dòng, không cho ai sửa lúc mình dùng, nhưng cho nhiều người cùng dựa | `FOR SHARE` | Tạo xe, sinh chuyến (dựa vào dòng `loai_xe`) |
| Giá trị phải **không đổi sau khi đã cam kết** với khách | **Chụp lại** vào bản ghi (snapshot ứng dụng) | `ve.gia`, `chuyen_xe.he_so_gia/he_so_ghe` |
| Nhiều bước phải **cùng thành công hoặc cùng hủy** | Một giao dịch | Giữ nhiều ghế, sinh cả cặp chuyến |
| Cấp **số/mã không trùng** | `SEQUENCE` (`nextval`) hoặc `UPDATE ... RETURNING` | Mã loại xe, mã vé, mã điểm |
| Chặn **dữ liệu trùng** dù code sót | Ràng buộc `UNIQUE` | Bộ giá, mã chuyến |
| Đọc nhiều lần cùng một dữ liệu trong 1 giao dịch mà phải **nhất quán** | Đọc **một lần** lên biến (+ `FOR SHARE`) | Sinh chuyến đọc hệ số ghế |

---

## 3. Từng chức năng

### 3.1 Giữ ghế / đặt chỗ (UC-05)

**Bài toán.** Hai khách cùng muốn ghế A1 chuyến 7h. Ai bấm "Tiếp tục" trước thì giữ được; người sau nhận thông báo "ghế đã có người". Ghế còn có thể bán **từng đoạn** (khách A đi Hà Nội→Vinh, khách B cùng ghế đó đi Vinh→Sapa).

**Luồng** (`dat_ve_service.giu_cho` → `ve_lock_repository.giu_ghe`), toàn bộ trong **một giao dịch**:
1. `SELECT ... FROM chuyen_xe WHERE id = ... FOR UPDATE` — khóa dòng chuyến → mọi lượt đặt **cùng chuyến xếp hàng**.
2. Chuyển các vé giữ tạm **đã quá hạn** của chuyến này sang `het_han` để không cản người sau.
3. Tính "thứ tự hiệu lực" (`hl`) của điểm đón/trả theo chiều chuyến.
4. Tìm các vé **đang chiếm** những ghế đó và **giao đoạn** với đoạn khách chọn, dùng `FOR UPDATE OF v`. Có → báo lỗi, **không tạo gì**.
5. `INSERT` một vé cho **từng ghế** (giá riêng từng ghế), hạn giữ 10 phút, rồi `COMMIT`.

**Đoạn nửa mở `[đón, trả)`.** Hai đoạn **giao nhau** khi `đón_của_vé_cũ < trả_mới` **và** `đón_mới < trả_của_vé_cũ`. Đi Hà Nội→Vinh là `[0,1)`, đi Vinh→Sapa là `[1,2)`: **không giao** (1 < 1 sai) → cùng ghế được bán cho hai người. Chiều ngược đảo dấu `thu_tu` (`hl = -thu_tu`) nên cùng một công thức dùng được cho cả hai chiều.

**Hạn giữ và ghế "tự mở lại".** Ghế được tính là "đang chiếm" khi vé `da_thanh_toan`, hoặc `giu_cho` mà `han_giu_cho_den > now()`. Tức là **hết hạn là ghế mở lại ngay lúc truy vấn**, không cần đợi job. Job `quet_ve_het_han` chỉ **dọn trạng thái** (đổi sang `het_han`, báo khách, tránh bị tính nhầm là no-show).

**Vì sao khóa dòng CHUYẾN chứ không khóa dòng GHẾ?**
Ghế còn trống **chưa có dòng nào trong bảng `ve`** — không có gì để khóa. Đây là bài toán "phantom" (dòng ma): kiểm tra "chưa có vé" xong, người khác chèn vé vào, mình lại chèn tiếp → trùng. Cách gọn nhất là **khóa dòng cha** (`chuyen_xe`) để tuần tự hóa mọi lượt đặt của chuyến đó. Chi phí thấp vì mỗi chuyến chỉ vài chục ghế và thao tác vài mili-giây.

**Vì sao không dùng mức cô lập `SERIALIZABLE`?** Phải viết thêm logic tự thử lại khi DB hủy giao dịch; `FOR UPDATE` đơn giản, dễ hiểu, đủ dùng.

**Giá.** `gia_theo_ghe[ghế]` tính từ chuyến (3.4–3.6) rồi **chụp vào `ve.gia`**. Sau đó đổi hệ số/bộ giá cũng không ảnh hưởng vé đã giữ. Tổng tiền, VNPay, đặt cọc, hoàn tiền, doanh thu đều **cộng từ `ve.gia`**.

**Ví dụ có số.** Chuyến 7h, ghế A1 trống. Khách A và B cùng bấm "Tiếp tục" lúc 08:00:00.100 và 08:00:00.105.
- A lấy khóa chuyến, tạo vé A1 (giữ đến 08:10). B chờ ~vài ms.
- B vào, thấy A1 đã có vé giao đoạn → "Ghế A1 đã có người chọn".
- Nếu A bỏ dở: 08:10 hết hạn → ghế mở lại; B bấm lại lúc 08:11 là giữ được.

**Chỗ trong code:** `backend/app/repositories/ve_lock_repository.py` (`giu_ghe`, `_DANG_CHIEM_GHE`), `backend/app/services/dat_ve_service.py` (`giu_cho`), `backend/app/jobs/quet_ve_het_han.py`.

---

### 3.2 Mã tự sinh

**Bài toán.** Cấp mã `LX001`, `T002`, `VE00001`… **không trùng**, kể cả khi hai người thêm cùng lúc.

**Cách làm** (`ma_repository.py`):
- **Sequence PostgreSQL** (`nextval`) cho mã loại xe, tuyến, khu vực, vé: hai người cùng gọi **không bao giờ nhận trùng số**, và số đã cấp **không dùng lại** (kể cả khi giao dịch sau đó bị hủy → mã có thể **nhảy cách**, đó là bình thường).
- **`UPDATE ... RETURNING`** cho điểm đón/trả theo khu vực (`khu_vuc.so_diem_da_cap + 1`): câu `UPDATE` **khóa dòng** khu vực nên hai người cùng thêm điểm vào một khu vực được xếp hàng.
- **Mã chuyến không dùng sequence** mà dựng từ dữ liệu: `T001-LX001-261011-0600-DI` (tuyến-loại xe-ngày-giờ-chiều). Cùng chuyến → cùng mã → `UNIQUE (ma)` chặn sinh trùng (xem 3.8).
- Mã được tạo **bằng hàm Python** (`utils/ma_tu_sinh.py`); trigger `giu_nguyen_ma` chỉ còn nhiệm vụ không cho sửa mã sau khi tạo.

**Vì sao sequence mà không `SELECT MAX(...) + 1`?** `MAX+1` là check-then-act kinh điển: hai người cùng đọc `MAX = 5` và cùng cấp 6. Sequence do DB đảm bảo.

---

### 3.3 Bộ giá vé (UC-33)

**Mô hình.** `bo_gia_ve(tuyen_id, ap_dung_tu, ap_dung_den)` + `gia_ve(bo_gia_id, diem_di_id, diem_den_id, gia_goc)`. Mỗi tuyến có **nhiều bộ nối liền nhau** (không chồng, không hở); mỗi bộ phải có giá **mọi chặng**. Chuyến khởi hành ngày nào lấy bộ bao ngày đó (chuyến về lệch +1 ngày có thể lấy bộ mới).

**Quy tắc quan trọng và lý do**
| Quy tắc | Lý do |
|---|---|
| Bộ mới **luôn bắt đầu ngày sau ngày kết thúc bộ cuối** | Không chồng, không hở → mọi ngày trong khoảng đều có đúng 1 giá |
| **Khóa theo CHUYẾN, không theo VÉ**: bộ đã dùng để sinh chuyến thì không sửa giá/ngày bắt đầu/xóa | Chuyến chưa ai đặt vẫn nhận giá mới → khách đang xem 300k có thể thành 400k. Khóa theo chuyến chặn từ gốc |
| Riêng **bộ cuối** vẫn gia hạn/rút ngắn được (không rút trước chuyến xa nhất đã sinh) | Cần cách kéo dài thời hạn bán mà không đổi giá |
| Muốn đổi giá → **tạo bộ mới** nối tiếp | Giá đã dùng là bất biến (1.5) |
| Luôn qua **bước xem trước + xác nhận** + cảnh báo giá bất thường (dưới 50.000đ / trên 5.000.000đ; giảm >50% hoặc tăng >2 lần so với bộ trước; chặng ngắn đắt hơn chặng dài) | Gõ thiếu/thừa số 0 là lỗi rất dễ; server từ chối cho tới khi `xac_nhan_canh_bao=true` |
| **Giá gốc phải là bội số của 10.000đ** | Khớp bước làm tròn giá bán (3.5), tránh quản lý thấy 135.000đ nhưng khách trả 140.000đ |
| Sinh chuyến chỉ được **trong khoảng các bộ giá** | Hết bộ cuối = hết hạn bán |

**Tranh chấp.** Hai quản lý cùng bấm "tạo bộ mới" cho một tuyến: cả hai tính ra cùng ngày bắt đầu → `UNIQUE (tuyen_id, ap_dung_tu)` chặn người sau (service bắt `UniqueViolation` và báo "Tuyến đã có bộ giá áp dụng từ ngày …"). Xem giới hạn ở mục 6.

**Theo dõi hạn.** Trang Giá vé phân loại tuyến theo hạn của bộ cuối: *Đang có giá* (còn > 14 ngày), *Sắp hết hạn* (≤ 14 ngày hoặc chưa tới ngày áp dụng), *Hết hạn / chưa có giá*. Không còn trạng thái "thiếu chặng" vì bộ luôn đủ chặng từ lúc nhập.

**Chỗ trong code:** `gia_ve_service.py`, `gia_ve_repository.py`, migration `20261016_0900_bo_gia_ve`, `20261017_0900_bo_gia_ve_co_ngay_ket_thuc`.

---

### 3.4 Hệ số giá của lịch và "chốt vào chuyến"

**Vấn đề ban đầu.** Hệ số giá nằm ở `loai_xe` và được **nhân lúc truy vấn**: sửa hệ số thì **mọi chuyến chưa chạy đổi giá ngay**, kể cả chuyến khách đang xem.

**Cách giải.** Chuyển hệ số sang **lịch chạy** (`lich_chay_dinh_ky.he_so_gia`, mặc định 1, 1 ô cho cả cặp) và **chốt vào từng chuyến lúc sinh chuyến** (`chuyen_xe.he_so_gia`). Giá vé = `gia_goc × chuyen_xe.he_so_gia`. Cột `loai_xe.he_so_gia` đã bị xóa.

**Ví dụ.**
```
Lịch "HN–Vinh 22:00" hệ số 1,5. Sinh chuyến 20→25/10: 6 chuyến đều mang 1,5.
   chặng gốc 200.000đ → giá 300.000đ.
Tuần sau sửa hệ số lịch thành 1,8. Sinh chuyến 26→30/10: chuyến mới 360.000đ.
   Chuyến 20→25/10 VẪN 300.000đ — khách đã xem/đã đặt không bị đổi giá.
```

**Vì sao chọn cách này (so với 2 cách khác đã cân nhắc)**
| Cách | Vì sao không chọn |
|---|---|
| A. Khóa hệ số khi loại xe còn chuyến chưa chạy | Lịch sinh chuyến liên tục nên hầu như luôn có chuyến tương lai → **khóa vĩnh viễn**, không bao giờ đổi được giá |
| C. Hệ số theo từng bộ giá (có ngày bắt đầu/kết thúc) | Chính xác nhất nhưng làm lại cả giao diện bộ giá — quá nặng so với lỗ hổng |
| **B. Chốt vào chuyến lúc sinh (đã chọn)** | Sửa tự do, chuyến cũ giữ nguyên, ít sửa code |

Lại thêm lợi ích: đặt hệ số **ở lịch** cho phép chuyến đêm/giờ cao điểm có hệ số riêng (hệ số ở loại xe không làm được).

**Hệ số lịch luôn sửa được**, kể cả khi cặp đã sinh chuyến (khác với giờ/loại xe bị khóa — 3.7) vì mỗi chuyến đã giữ bản chốt riêng. API: `PATCH /quan-ly/lich-chay/cap/{id}/he-so-gia`.

**Giới hạn:** chỉ áp dụng cho chuyến sinh **sau**. Muốn đổi giá chuyến đã sinh: xóa chuyến "sạch" (chưa gán xe, chưa có vé — UC-48) rồi sinh lại. Chuyến đã có vé thì không đổi — và đó là đúng.

---

### 3.5 Làm tròn 10.000đ

**Quy tắc.** Giá bán = làm tròn **nửa-lên** tới **bội số của 10.000đ**, tối thiểu 10.000đ (không bao giờ về 0). Hằng số `BUOC_LAM_TRON = 10_000` trong `backend/app/utils/gia.py` (hàm `tinh_gia_ban`). Giao diện có bản sao `lamTronGia` — **phải khớp** backend.

**Ví dụ.** 130.000 × 1,15 = 149.500 → **150.000**. 130.000 × 1,1 = 143.000 → **140.000**. 250.000 × 1,5 = 375.000 → **380.000**.

**Vì sao ở mức cuối, và làm tròn MỘT lần?** Làm tròn từng bước tích lũy sai số. Ví dụ 130.000 × 1,5 × 1,1: làm tròn một lần = 214.500 → **210.000**; nếu tròn từng bước = 195.000 → 200.000 rồi ×1,1 = **220.000** (lệch 10.000). Nên chỉ tròn **một lần ở cuối** trên tích các hệ số.

**Giá gốc không bội 10.000?** Lưu nguyên số nhập, nhưng **bị chặn từ lúc nhập** ở trang Giá vé (cả server lẫn form) để giá gốc và giá bán không lệch nhau khi hệ số = 1.

---

### 3.6 Hệ số giá từng ghế (giai đoạn 2)

**Công thức.** `giá ghế = tinh_gia_ban(gia_goc, he_so_chuyen, he_so_ghe)`, làm tròn **một lần**.
Ví dụ: chặng gốc 100.000đ, hệ số chuyến 1,5, ghế A1 ×1,2, A2 ×0,8, ghế khác 1:
A1 = 180.000đ · ghế thường = 150.000đ · A2 = 120.000đ.

**Lưu ở đâu.**
- `loai_xe.he_so_ghe` JSON `{"A1-1": 1.2, "A2-1": 0.8}` (ghế vắng mặt = 1). **Luôn sửa được**, kể cả khi sơ đồ ghế đã khóa.
- `chuyen_xe.he_so_ghe`: **bản chốt** lúc sinh chuyến, giống `he_so_gia`.

**Vì sao tách hệ số ghế khỏi `so_do_ghe`?**
Sơ đồ ghế bị **khóa** khi đã có xe/chuyến (vé trỏ tới mã ghế, đổi mã là hỏng). Nhưng hệ số ghế **không ảnh hưởng vé đã đặt** (`ve.gia` đã chốt) hay chuyến đã sinh (đã chụp bản riêng) → **không có lý do khóa**. Gộp chung vào sơ đồ thì quản lý không bao giờ chỉnh giá ghế được nữa.

**Vì sao lưu JSON mà không làm bảng?** Giống `so_do_ghe`: ít bảng hơn, đọc cả sơ đồ + hệ số một lần, quy mô nhỏ. Đổi lại phải **tự kiểm tra** ở Service (mỗi khóa phải là `ma_ghe` có trong sơ đồ; giá trị > 0, ≤ 99,99, tối đa 2 chữ số thập phân; hệ số = 1 bị bỏ vì là mặc định).

**Vì sao hệ số nhân mà không phụ thu cố định?** Hệ số cùng một khái niệm với hệ số lịch (dễ nhớ một cơ chế), và **chênh lệch tỉ lệ theo chặng** (ghế đầu ×1,1: +10.000đ ở chặng 100.000đ, +50.000đ ở chặng 500.000đ). Hạn chế duy nhất: hệ số nhỏ có thể bị làm tròn mất ở chặng ngắn (×1,05 trên 60.000đ = 63.000đ → 60.000đ, không chênh lệch) — nên trang Loại xe có **bảng xem trước** và cảnh báo.

**Hiển thị cho khách.** Thẻ chuyến ghi giá **thấp nhất** (nếu các ghế khác giá thì "Giá từ"); sơ đồ ghế ghi giá nhỏ dưới mã ghế; **tổng tiền = cộng giá từng ghế đã chọn** (không còn `số ghế × 1 giá`). Chi tiết chuyến của Quản lý ghi mỗi chặng **khoảng giá thấp nhất – cao nhất** và liệt kê ghế theo từng hệ số.

**Chỗ trong code:** `utils/gia.py` (`tinh_gia_ban`, `gia_theo_ghe`), `tim_kiem_chuyen_service.py` (`chon_gia_goc`, `_lap_the_chuyen`), `ve_lock_repository.giu_ghe` (nhận `gia_theo_ghe`), `xe_service._chuan_hoa_he_so_ghe`, `loai-xe.html` (tab Giá ghế), `dat-ve.js`.

---

### 3.7 Lịch chạy theo cặp (UC-18)

**Mô hình.** Mỗi lịch luôn là **một cặp** đi + về (cùng tuyến, **cùng loại xe**, giờ riêng từng chiều), nối bằng `cap_id`; chiều về có `ngay_lech` (chạy sau chiều đi mấy ngày). Tạo/ngừng/xóa **cả cặp trong một giao dịch**.

**Vì sao theo cặp.** Không còn tình trạng có chuyến đi mà thiếu chuyến về (xe đi rồi không có lượt về → lệch vòng xe).

**Quy tắc và lý do**
- Xe nghỉ tối thiểu 30 phút giữa lúc tới nơi và chuyến về; **chuyến đi kết thúc trong ngày thì chuyến về phải cùng ngày**; chỉ khi qua nửa đêm mới tự tính `ngay_lech`.
- `ngay_lech` **lưu cố định** lúc tạo, để sửa thời gian chạy của tuyến sau này không làm lệch các cặp đã có.
- **Cặp đã sinh chuyến thì khóa sửa giờ/loại xe**: chuyến cũ giữ giá trị lúc sinh nên lịch và chuyến sẽ lệch nhau, và những ngày đã có chuyến không bao giờ được sinh lại theo lịch mới. Muốn đổi: **ngừng** cặp (`dang_ap_dung=false`) rồi tạo cặp mới. *Riêng hệ số giá thì luôn sửa được (3.4).*
- Xóa cặp chỉ được khi chưa sinh chuyến (FK từ `chuyen_xe.lich_chay_dinh_ky_id` chặn).
- **Lập lịch không cần giá, sinh chuyến cần giá.**

---

### 3.8 Sinh chuyến (UC-47)

**Hành động chủ động**, không có job nền tự động: quản lý chọn cặp + khoảng ngày rồi bấm "Sinh chuyến" (lý do: người dùng đã hai lần từ chối thiết kế tự động; muốn tham số rõ ràng, tự chủ).

**Luồng** (`lich_chay_service.sinh_chuyen_cho_cac_cap` → `chuyen_xe_repository.sinh_nhieu_chuyen_tu_lich`):
1. Kiểm tra: khoảng ngày hợp lệ, không quá khứ, ≤ 180 ngày/lần, cặp đang áp dụng, **trong khoảng các bộ giá** (chuyến đi tối đa = ngày cuối bộ mới nhất − `ngay_lech`), mọi ngày khởi hành đều có bộ giá đủ chặng.
2. Mỗi ngày D: sinh chuyến đi D và chuyến về D + `ngay_lech`. **Nếu chuyến đi của ngày D đã quá giờ hiện tại thì bỏ cả chu kỳ** (không để thừa chuyến về lẻ).
3. **Một giao dịch** cho toàn bộ: lỗi ở đâu thì hủy hết, không bao giờ sinh dở một cặp.
4. Ngày của lịch **đã có chuyến thì bỏ qua** (an toàn khi bấm lại — *idempotent*) và được đếm riêng ("đã có sẵn").
5. Hệ số: `he_so_gia` lấy từ lịch; **`he_so_ghe` đọc MỘT LẦN cho cả lô** từ `loai_xe` với `FOR SHARE`, rồi chép vào từng chuyến.

**Vì sao đọc hệ số ghế một lần + `FOR SHARE`?** (lỗi non-repeatable read, mục 1.4c)
Nếu mỗi chuyến tự `SELECT` lại, ở mức Read Committed việc sửa hệ số giữa chừng sẽ khiến chuyến đầu và chuyến cuối của **cùng một lô** có hệ số khác nhau. Đọc một lần → cả lô nhất quán. `FOR SHARE` → người đang sửa hệ số phải chờ lô sinh xong (và ngược lại), nên không chen ngang.
*Phòng deadlock:* nhiều loại xe được khóa theo thứ tự `ORDER BY id`.

**Giờ lưu thế nào.** `gio_khoi_hanh` là `TIMESTAMPTZ` nhưng session Postgres mặc định UTC → code **gắn múi giờ VN tường minh** (`Asia/Ho_Chi_Minh`) khi ghép ngày + giờ; so ngày bằng `(gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date`.

**Giới hạn:** việc "kiểm tra đã có chuyến chưa rồi mới chèn" là check-then-act; hai người sinh **đúng cùng lúc** cùng một chuyến sẽ bị `UNIQUE (ma)` chặn người sau (mã chuyến tất định) nhưng hiện chưa bắt lỗi này thành thông báo thân thiện. Xem mục 6.

---

### 3.9 Loại xe: khóa sơ đồ + phiên bản + khóa dòng (UC-32)

Đây là chỗ dùng **cả hai loại khóa**; đọc kỹ cùng mục 1.2.

**Quy tắc 1 — sơ đồ ghế khóa khi loại xe đã được dùng.** Nếu có `xe` **hoặc** `chuyen_xe` thuộc loại xe thì **không đổi sơ đồ ghế** (mã ghế, vị trí, số tầng). Lý do: vé có thể đang trỏ tới mã ghế cũ; xóa ghế A5 khi khách đã đặt A5 là hỏng dữ liệu. Tên và **hệ số ghế** vẫn sửa được. Tạo loại xe mới có **modal xác nhận** nhắc kiểm tra lại sơ đồ (vì sau đó khóa).
- Cột trả về `khoa_so_do_ghe` = `EXISTS(xe) OR EXISTS(chuyen_xe)`.
- Server so sánh sơ đồ **đã chuẩn hóa** (sắp xếp, đổi kiểu số) nên gửi lại đúng sơ đồ cũ thì vẫn lưu được.

**Quy tắc 2 — khóa lạc quan `phien_ban`.** Mỗi lần sửa nâng `phien_ban`. PUT bắt buộc kèm `phien_ban` đang xem; lệch → `XungDot` → **HTTP 409** ("vừa được người khác sửa — hãy tải lại"); thiếu → 400.

**Quy tắc 3 — khóa dòng chống check-then-act.** Ba thao tác cùng "chạm" dòng `loai_xe`:
| Thao tác | Khóa trên dòng loại xe |
|---|---|
| `sua_loai_xe` | `FOR UPDATE` (độc quyền) — kiểm tra + ghi **trong cùng giao dịch** |
| `tao_xe`, `sua_xe` (đổi loại), sinh chuyến | `FOR SHARE` (chia sẻ) |

**Ví dụ lỗi nếu KHÔNG có khóa dòng:**
```
t1  A: kiểm tra "loại xe chưa có xe" → được sửa sơ đồ
t2  B: tạo xe 29B-123 thuộc loại này
t3  A: ghi sơ đồ mới (bỏ ghế A5, đổi mã ghế)   ← xe 29B-123 bị đổi sơ đồ SAU lưng nó
```
**Có khóa dòng:**
```
A: FOR UPDATE loại xe → kiểm tra → ghi → commit
B: tạo xe cần FOR SHARE → CHỜ A xong → rồi mới tạo (trên sơ đồ MỚI, hợp lệ)
(hoặc B vào trước: B tạo xong → A kiểm tra thấy đã có xe → bị chặn đúng luật)
```
Đã kiểm chứng bằng hai luồng thật trên DB tạm: A giữ khóa 2 giây, B (tạo xe) **chờ ~1,5 giây**, xe được tạo trên sơ đồ mới; sau đó sửa sơ đồ bị khóa đúng.

**Vì sao cần ĐỒNG THỜI cả `phien_ban` lẫn `FOR UPDATE`?**
- `phien_ban` giải quyết khoảng **người dùng mở form vài phút** (không thể giữ khóa lâu thế).
- `FOR UPDATE` giải quyết khoảng **vài mili-giây** trong server giữa "kiểm tra" và "ghi", nơi `phien_ban` không với tới (vì tạo xe không đổi `phien_ban` của loại xe).

**Kiến trúc.** Quy tắc nghiệp vụ nằm ở Service; Repository chỉ làm SQL. Để kiểm tra và ghi cùng nằm **trong một giao dịch có khóa**, Service truyền xuống Repository một **hàm `kiem_tra(hien_tai)`**; Repository khóa dòng, đọc trạng thái hiện tại, gọi `kiem_tra` (Service ném lỗi nếu không hợp lệ), rồi mới `UPDATE`.

---

### 3.10 Migration (đổi cấu trúc DB mà không mất dữ liệu)

Công cụ: **yoyo** (`backend/migrations/*.sql`, bảng theo dõi `_yoyo_migration`; chạy `yoyo apply --batch`). Tên file theo `ngày_giờ_mô_tả`.

Các migration của đợt này
| File | Làm gì |
|---|---|
| `20261011_0900_lich_chay_theo_cap` | Thêm `cap_id`, `ngay_lech` cho lịch |
| `20261016_0900_bo_gia_ve` | Chuyển giá sang bộ giá; xóa giá theo mùa |
| `20261017_0900_bo_gia_ve_co_ngay_ket_thuc` | `ap_dung_den` bắt buộc; bộ cuối cũ nhận ngày kết thúc mặc định |
| `20261018_0900_he_so_gia_theo_lich` | `he_so_gia` cho lịch + chuyến, **backfill** từ loại xe, rồi `DROP` cột ở loại xe |
| `20261019_0900_he_so_ghe` | `loai_xe.he_so_ghe`, `loai_xe.phien_ban`, `chuyen_xe.he_so_ghe` |

**Mẫu an toàn khi chuyển dữ liệu** (dùng lại được):
1. `ADD COLUMN ... NOT NULL DEFAULT ...` — thêm cột có mặc định nên dòng cũ vẫn hợp lệ.
2. `UPDATE ... SET cột_mới = (giá trị suy từ cột cũ)` — **backfill** để dữ liệu cũ giữ nguyên ý nghĩa (VD chuyến cũ nhận hệ số hiện tại của loại xe → giá **không đổi**).
3. Chỉ **sau đó** mới `DROP COLUMN` cột cũ.
4. Thêm `CHECK` (VD `he_so_gia > 0`) để DB tự từ chối giá trị vô lý.

**Lưu ý khi lên production**
- **Backend và migration phải lên cùng lúc**: code mới đọc cột mới (hoặc code cũ đọc cột đã xóa) sẽ lỗi nếu lệch.
- `DROP COLUMN` **không hoàn tác được** — thử trên bản sao trước.
- Script/test của người khác có `INSERT INTO loai_xe (..., he_so_gia, ...)` sẽ lỗi sau khi xóa cột (đã sửa `seed_phu_xe_demo.py`; kiểm tra lại script khác).

---

## 4. Một ngày trong đời hệ thống

Nối tất cả các phần trên bằng một ví dụ có số. Tuyến **Hà Nội – Vinh**, chặng gốc **200.000đ**.

1. **Quản lý tạo bộ giá** 19/10 → 31/10: chặng HN–Vinh 200.000đ (bội 10.000 ✔). Có bước xem trước, không cảnh báo.
2. **Quản lý tạo loại xe "Giường 40 chỗ"**: vẽ sơ đồ, tab *Giá ghế* đặt ghế đầu A1-1 ×1,1. Modal xác nhận nhắc kiểm tra sơ đồ. → `loai_xe` (`he_so_ghe = {"A1-1":1.1}`, `phien_ban = 1`).
3. **Quản lý tạo xe** 29B-123 loại "Giường 40 chỗ" → từ giờ **sơ đồ khóa**, hệ số ghế vẫn sửa được.
4. **Quản lý tạo cặp lịch** "đi 22:00 / về 06:00 sáng hôm sau", hệ số **1,5**. Form xem trước giá: 200.000 × 1,5 = **300.000đ**.
5. **Sinh chuyến** 20→22/10 (trong 1 giao dịch): mỗi chuyến chép `he_so_gia = 1,5` và `he_so_ghe = {"A1-1":1.1}`.
   - Giá ghế thường = tròn(200.000 × 1,5 × 1) = **300.000đ**.
   - Giá A1-1 = tròn(200.000 × 1,5 × 1,1) = tròn(330.000) = **330.000đ**.
6. **Khách A, B cùng bấm "Tiếp tục"** chuyến ngày 20 cho ghế **A1-1**: khóa dòng chuyến → A thắng, tạo vé `ve.gia = 330.000`; B nhận "ghế đã có người". B chọn ghế A2-1 → vé `ve.gia = 300.000`. Tổng đơn của B hiển thị đúng = cộng giá từng ghế.
7. **Quản lý sửa hệ số ghế đầu thành ×1,3** (`phien_ban` 1 → 2). Sinh chuyến 23→25/10 → chuyến mới A1-1 = tròn(200.000 × 1,5 × 1,3) = **390.000đ**. Chuyến ngày 20→22 **vẫn 330.000đ**; vé đã đặt của A **vẫn 330.000đ**.
8. **Hai quản lý cùng sửa loại xe**: cả hai cầm `phien_ban = 2`; người lưu sau nhận **409**.
9. **Lúc đó có người tạo xe mới** thuộc loại này đúng lúc quản lý đang sửa: tạo xe **chờ** giao dịch sửa xong (khóa dòng), không bao giờ đổi sơ đồ sau lưng xe vừa tạo.

---

## 5. Cách kiểm thử phần đồng thời

Quy tắc đã chốt: **test SQL trên DB tạm + test HTTP bằng uvicorn tạm trước khi coi tính năng backend là xong** (không dùng/đụng dữ liệu người dùng đang tạo).

1. **DB tạm:** tạo database mới, sao chép schema+dữ liệu từ DB dev rồi áp migration:
   ```
   CREATE DATABASE scratch;
   pg_dump nha_xe | psql scratch
   psql scratch < migrations/<file>.sql
   ```
   Chạy script với biến `DATABASE_URL` trỏ vào DB tạm; xong `DROP DATABASE scratch`.
2. **HTTP thật:** chạy `uvicorn app.main:app --port 8001` (cổng khác 8000) với `DATABASE_URL` tạm, gọi bằng `urllib` (token tự sinh từ `tao_token`). Nhớ **tắt tiến trình** rồi mới `DROP DATABASE` (nếu không DB "đang được dùng").
3. **Test tranh chấp bằng hai luồng (`threading`):** luồng A giữ khóa (ví dụ `kiem_tra` ngủ 2 giây), luồng B bắt đầu sau 0,5 giây rồi **đo thời gian chờ** — kỳ vọng ≈ 1,5 giây, chứng minh B thật sự bị chặn.
4. **Unit test** (`docker exec <backend> python -m pytest tests/unit -q`): logic thuần và Service với Repository giả (monkeypatch). Khóa thật **không** kiểm ở đây mà ở bước 3.
   Hiện còn **2 test lỗi có sẵn từ trước** ở `test_thong_bao_khach.py` (không liên quan các thay đổi này).
5. **Không xóa/ghi đè dữ liệu người dùng:** xóa theo `ngay_tao`, xác nhận số dòng trước; test chỉ-đọc nếu có thể.

---

## 6. Lỗ hổng / việc còn dở

Nói thẳng những chỗ **chưa** an toàn hoặc chưa làm:

| Việc | Mức độ | Gợi ý xử lý |
|---|---|---|
| Hai quản lý **sinh chuyến cùng lúc cùng một chuyến**: "kiểm tra chưa có rồi chèn" là check-then-act; người sau bị `UNIQUE(ma)` chặn (**dữ liệu không bị hỏng**) nhưng lỗi chưa được bắt thành thông báo thân thiện (có thể ra lỗi 500) | Thấp (ít quản lý, đúng cùng giây) | Bắt `UniqueViolation` trong `sinh_chuyen_cho_cac_cap` → `GiaTriLoi("…vừa có người sinh trùng, hãy thử lại")` |
| **Bộ giá** tạo đồng thời: `UNIQUE(tuyen_id, ap_dung_tu)` chỉ chặn **trùng ngày bắt đầu**; chưa khóa để đảm bảo không chồng/hở trong mọi tình huống | Thấp | Khóa dòng `tuyen` (`FOR UPDATE`) trong tạo/sửa bộ giá |
| Sửa **tuyến** (thêm khu vực) làm bộ giá cũ **thiếu chặng**: chưa chặn/nhắc | Trung bình | Chặn hoặc nhắc tạo bộ giá mới khi sửa tuyến |
| Ngưỡng cảnh báo giá (50.000đ/5.000.000đ, giảm >50%, tăng >2 lần) **cố định trong code** | Thấp | Đưa ra cấu hình nếu cần |
| Chưa kiểm tra **nhật ký thao tác** `cau_hinh_gia_ve` có được ghi khi tạo/sửa bộ giá | Thấp | Kiểm tra / bổ sung |
| Khi sửa sơ đồ lúc còn sửa được (chưa có xe): hệ số của ghế **bị xóa** phải được dọn | Đã xử lý ở giao diện (hệ số đi theo ghế); server từ chối khóa lạ | — |
| (Đã rà 2026-10-19) Mọi nơi khác chỉ đọc `ve.gia` (doanh thu, hoàn tiền, lịch sử vé, trang phụ xe, kết quả thanh toán) — giá đã chốt từng vé nên không vỡ. Chỉ `tim_kiem_chuyen_service` đọc giá chuyến và đã đổi sang `gia` (thấp nhất) + `gia_cao_nhat` | Đã xong | — |
| Giao diện **chưa test bằng trình duyệt** tự động — chỉ kiểm cú pháp + người dùng tự thử | — | Người dùng thử tay theo checklist |
| Lên production: migration xóa giá theo mùa; backend + migration lên **cùng lúc** | Lưu ý triển khai | Xem 3.10 |

---

## 7. Từ điển thuật ngữ nhanh

| Từ | Nghĩa ngắn gọn |
|---|---|
| Giao dịch (transaction) | Nhóm lệnh làm hết hoặc hủy hết |
| `COMMIT` / `ROLLBACK` | Lưu chính thức / hủy giao dịch |
| Khóa dòng (row lock) | Khóa 1 dòng, không khóa cả bảng |
| `FOR UPDATE` | Khóa độc quyền dòng ("tôi sắp sửa") |
| `FOR SHARE` | Khóa chia sẻ ("tôi đang dựa vào, đừng sửa lúc này") |
| Khóa bi quan | Khóa trước, làm sau; người sau chờ |
| Khóa lạc quan | Không khóa; lúc ghi kiểm tra phiên bản, lệch thì từ chối |
| `phien_ban` / HTTP 409 | Số phiên bản dùng cho khóa lạc quan / mã lỗi "xung đột" |
| Cô lập (isolation) | Mức độ giao dịch thấy dữ liệu của nhau |
| Read Committed | Mức mặc định: chỉ thấy dữ liệu đã lưu |
| MVCC | Giữ nhiều phiên bản dòng để người đọc không chặn người ghi |
| Snapshot (DB) | Ảnh chụp dữ liệu mà một giao dịch nhìn thấy |
| Snapshot (ứng dụng) | Sao chép giá trị vào bản ghi lúc cam kết để sau không đổi |
| Bất biến (immutable) | Ghi rồi không sửa → không cần khóa khi đọc |
| Lost update | Hai người ghi đè nhau, một thay đổi bị mất |
| Check-then-act | Kiểm tra rồi làm, nhưng giữa chừng điều kiện đã đổi |
| Non-repeatable read | Đọc 2 lần trong 1 giao dịch ra 2 kết quả khác nhau |
| Phantom (dòng ma) | Dòng mới xuất hiện giữa 2 lần đọc; chưa có dòng thì không khóa được |
| Deadlock | Hai bên giữ khóa của nhau và cùng chờ; DB hủy một bên |
| Idempotent | Làm lại nhiều lần cho cùng kết quả (bấm "Sinh chuyến" lại không tạo trùng) |
| Sequence | Bộ đếm của DB cấp số không trùng |
| `UNIQUE` | Ràng buộc chống trùng, chốt chặn cuối cùng |
| Backfill | Điền dữ liệu cho cột mới từ dữ liệu cũ khi đổi cấu trúc |
| `hl` (thứ tự hiệu lực) | `thu_tu` của điểm theo đúng chiều chuyến (chiều ngược đảo dấu) |
| Đoạn nửa mở `[đón, trả)` | Gồm điểm đón, không gồm điểm trả → hai đoạn nối đuôi nhau không giao |
