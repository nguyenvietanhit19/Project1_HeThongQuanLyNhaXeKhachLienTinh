# Nghiệp vụ Nhân viên gửi hàng (`nhan_vien_gui_hang`)

> **File gộp toàn bộ nghiệp vụ của vai trò nhân viên gửi hàng** vào một chỗ:
> - Phần gốc chép từ `NGHIEP_VU.md` (mục 2, 8.5, 10, 11, 12 — UC-23, 24, 25, 26, 27, 28, 39). **`NGHIEP_VU.md` không bị sửa**; mỗi mục ở đây ghi rõ nguồn.
> - Phần bổ sung đã làm sau này, ký hiệu:
>   - 🆕 **đã chốt** — nhóm đã đồng ý (hủy đơn, UC-54, chốt ngày 09/10/2026).
>   - ⏳ **đã có trong code, chờ nhóm xác nhận** — chưa có trong `NGHIEP_VU.md` (KE_HOACH_SUA_GUI_HANG.md, điểm D8).
>
> Cơ sở dữ liệu: `DATABASE.md` mục 5. Tiến độ và kế hoạch code: `KE_HOACH_SUA_GUI_HANG.md`.

---

## 1. Vai trò và nguyên tắc chung

*(Nguồn: `NGHIEP_VU.md` mục 2, 8.5, 10)*

Vai trò **tách riêng** khỏi `nhan_vien_quay_ve` — không bán vé, không soát vé hành khách. Mỗi nhân viên được gán **1 văn phòng**, chỉ thao tác trong phạm vi văn phòng đó: điểm gửi khi tạo đơn tự lấy theo văn phòng của tài khoản, không chọn lại.

Dịch vụ gửi hàng là hàng hóa **độc lập**: người gửi mang hàng tới quầy, không cần đi cùng chuyến; người nhận là người khác, ra nhận tại điểm đến. Không nói tới hành lý xách tay của hành khách. Mảng này tách khỏi vé nhưng **dùng chung tuyến/chuyến/điểm đi-đến/điểm đón-trả** đã có.

**Các nguyên tắc cố định** (giữ từ bản thiết kế đầu tới giờ):

1. **Cước do nhân viên tự nhập tay** — không có công thức hay bảng giá nào tính/gợi ý (khác hẳn `gia_ve`).
2. **Không có kênh báo tin tự động** (SMS/email) cho người gửi/người nhận — họ không có tài khoản, không thu email. Báo tin hoàn toàn bằng gọi điện thủ công.
3. **Hai đầu gửi/nhận bắt buộc là văn phòng** (`loai = 'van_phong'`), không được là điểm dừng dọc đường — vì cả 2 đầu đều cần nhân viên thao tác tại quầy.
4. **Chỉ tạo đơn tại quầy** — không có luồng khách tự đặt gửi hàng online (cần cân/đo/kiểm tra hàng thực tế).
5. **Chọn tuyến, không chọn chuyến** lúc nhận hàng; hệ thống **không tính sức chứa** khoang hàng theo kg — phụ xe tự đánh giá lúc chất hàng.
6. **Không bao giờ tự động hủy/thanh lý hàng** — các mốc 7/14 ngày chỉ nhắc con người xử lý.

**Việc của nhân viên gửi hàng** (mục 8.5, bổ sung 🆕 ⏳):

1. **Tại điểm gửi**: nhận hàng, cân/đo, chặn hàng cấm, chọn tuyến + điểm nhận, tự nhập cước, tạo đơn `cho_van_chuyen`, in mã vận đơn, thu tiền nếu người gửi trả trước (mục 5.1, UC-23).
2. **Tại điểm nhận**: chủ động gọi điện báo người nhận khi hàng tới; khi người nhận tới lấy thì xác minh mã vận đơn, thu COD nếu có, đánh dấu `da_giao` (mục 5.2, UC-24).
3. **Xử lý hàng chờ quá lâu** tại điểm nhận theo cờ cảnh báo 7 ngày / hàng tồn 14 ngày; gọi người nhận hoặc người gửi tùy tình huống, báo `quan_ly` nếu không liên hệ được ai (mục 5.3, UC-25).
4. 🆕 **Hủy đơn tại điểm gửi** khi hàng còn trong kho, hoàn cước trả trước bằng tiền mặt (mục 5.4, UC-54).
5. ⏳ **Sửa tên/SĐT người gửi, người nhận** khi đơn chưa giao (mục 5.5).
6. **Xem thống kê và đối soát tiền mặt** của văn phòng mình (mục 6, UC-39).

---

## 2. Đơn hàng — dữ liệu chính

*(Nguồn: `NGHIEP_VU.md` mục 10.1; chi tiết cột ở `DATABASE.md` mục 5.2)*

- `tuyen_id`: tuyến khách muốn gửi qua, chọn lúc nhận hàng.
- `chuyen_id`: **để trống** cho tới khi phụ xe thực sự chất hàng lên 1 chuyến (UC-26). Trống = đơn đang chờ, chưa biết đi chuyến nào.
- `diem_gui_id` / `diem_nhan_id`: đều là văn phòng.
- `can_nang_kg`, kích thước dài×rộng×cao: cân/đo thực tế, **chỉ để tham khảo khi định giá**, không dùng tính sức chứa xe.
- `loai_hang`: theo danh mục do `quan_ly` cấu hình (thường/dễ vỡ/hàng lạnh/tài liệu...); hàng cấm bị chặn ngay khi tạo đơn.
- `gia_cuoc`: số nhân viên nhập tay.
- Người gửi / người nhận: **chỉ tên + SĐT**, không cần tài khoản, không thu email.
- `phuong_thuc_thanh_toan`: `nguoi_gui_tra_truoc` hoặc `cod_nguoi_nhan_tra`.
- `ma_van_don`: mã tra cứu duy nhất mỗi đơn, in trên biên nhận cho người gửi; dùng để xác minh khi giao hàng.
- Cờ `da_thong_bao_nguoi_nhan` (đã gọi báo được người nhận — chỉ bật, không tắt), cờ `co_canh_bao_cho_lau` (đủ 7 ngày).
- ⏳ Thông tin thu tiền: đã thu chưa, ai thu, lúc nào (để đối soát két).
- 🆕 Thông tin hủy: lý do, ghi chú, ai hủy, lúc nào, số tiền hoàn.

---

## 3. Vòng đời đơn hàng

*(Nguồn: `NGHIEP_VU.md` mục 10.3; nhánh `da_huy` 🆕)*

```
cho_van_chuyen (đã nhận hàng tại quầy gửi, chuyen_id còn để trống, chờ 1 chuyến bất kỳ cùng tuyến)
  ├─ 🆕 [Người gửi hủy tại quầy gửi, hàng chưa lên xe — UC-54] → da_huy (trả hàng, hoàn cước nếu đã thu)
  └─ [Phụ xe chọn xếp lên 1 chuyến cụ thể — UC-26, lúc này mới gán chuyen_id] → da_len_xe
        └─ [Xe tới điểm nhận, phụ xe xác nhận đã dỡ hàng — UC-27] → cho_lay (bắt đầu tính mốc chờ)
              ├─ [Người nhận ra lấy, giao đúng quy trình — UC-24] → da_giao
              ├─ [Đủ 7 ngày chưa ai lấy — UC-25 ⏱] → vẫn cho_lay, bật cờ cảnh báo, nhắc nhân viên gọi lại
              └─ [Đủ 14 ngày chưa ai lấy — UC-25 ⏱] → qua_han_luu_kho ("hàng tồn", KHÔNG tự hủy)
                    └─ ⏳ [Người nhận tới lấy theo thỏa thuận UC-25] → da_giao
```

- Đơn chưa được phụ xe chọn vẫn `cho_van_chuyen`, tự còn hợp lệ cho chuyến sau cùng tuyến — không cần thao tác "dời chuyến".
- 🆕 Từ `da_len_xe` trở đi **không hủy được**. `da_huy` là trạng thái cuối: không sửa, không giao, không chất lên xe được nữa. Đơn hủy không bị xóa, mã vận đơn không dùng lại.
- ⏳ Code cho giao cả đơn `qua_han_luu_kho` (hàng tồn) khi người nhận tới lấy theo hướng xử lý đã thỏa thuận ở UC-25 — `NGHIEP_VU.md` 10.4.2 bước 3 hiện chỉ ghi `cho_lay` (KE_HOACH S2.11).
- Mọi lần đổi trạng thái đều được ghi lịch sử (ai chuyển, lúc nào) để tra cứu khi khiếu nại.

---

## 4. Chất hàng lên xe — vì sao chọn tuyến chứ không chọn chuyến

*(Nguồn: `NGHIEP_VU.md` mục 10.2 — phần này do phụ xe thao tác, ghi lại để hiểu luồng)*

- "Xe còn chỗ chứa hàng hay không" **không tính đúng được bằng số kg cộng dồn**: 2 kiện nặng bằng nhau có thể khác hẳn thể tích. Chỉ người đứng trước khoang hàng mới biết xếp vừa hay không → hệ thống không tự chống quá tải.
- **Lúc nhận hàng (UC-23)**: nhân viên chọn **tuyến**; xe nào, loại xe nào chạy đúng tuyến (đúng chiều) đều hợp lệ để chở.
- **Lúc chất hàng (UC-26)**: phụ xe xem đơn `cho_van_chuyen` cùng tuyến, đang chờ tại điểm xe đứng, cùng chiều chuyến, đơn cũ hiện trước (chỉ để tham khảo); tự chọn đơn nào lên xe. Đơn được chọn mới gán `chuyen_id`, chuyển `da_len_xe`.

---

## 5. Thao tác của nhân viên trên hệ thống

### 5.1. Khi khách tới **gửi** hàng (UC-23)

*(Nguồn: `NGHIEP_VU.md` mục 10.4.1)*

1. Đăng nhập — hệ thống tự biết điểm gửi = văn phòng của nhân viên.
2. Nhập người gửi (tên + SĐT) và người nhận (tên + SĐT — dùng để văn phòng nhận gọi báo khi hàng tới).
3. Chọn **khu vực đến** rồi **văn phòng nhận** trong khu vực đó (chỉ văn phòng có tuyến nối với văn phòng gửi).
4. Hệ thống tìm **tuyến** đi qua cả 2 văn phòng: 1 tuyến thì tự điền, nhiều tuyến thì nhân viên chọn 1, không có tuyến thì từ chối nhận. **Không chọn chuyến.**
5. Cân/đo hàng, nhập cân nặng + kích thước, chọn loại hàng → hệ thống **chặn ngay nếu là hàng cấm**.
6. Nhân viên **tự nhập cước**, đọc lại thông tin và **báo giá cho khách xác nhận** trước khi tạo đơn.
7. Chọn hình thức thanh toán: người gửi trả trước (thu tiền mặt ngay, nhân viên xác nhận đã thu) hoặc COD (không thu, người nhận trả).
8. Xác nhận tạo đơn → sinh mã vận đơn, đơn `cho_van_chuyen`, in **2 bản**: (a) nhãn dán kiện hàng (mã vận đơn + mã vạch + điểm đến + SĐT người nhận), (b) **biên nhận cho người gửi** (mã vận đơn + văn phòng nhận + thông tin liên hệ văn phòng nhận) để họ tự báo mã cho người nhận.
9. Dán nhãn, xếp hàng vào khu chờ đúng tuyến.

Hỗ trợ tại quầy (đã có trong code): gợi ý tên khách quen theo SĐT, chống tạo trùng đơn khi bấm 2 lần / mạng chậm.

### 5.2. Khi hàng tới và người nhận tới **nhận** hàng (UC-24)

*(Nguồn: `NGHIEP_VU.md` mục 10.3.1, 10.4.2)*

1. Màn **"Hàng đến"** của văn phòng nhận chia 3 nhóm: *Sắp đến* (đang trên xe), *Chờ gọi báo*, *Chờ lấy*; đánh dấu riêng đơn chờ quá 7 ngày và hàng tồn. Khi phụ xe dỡ hàng, nhân viên văn phòng nhận nhận thông báo.
2. Với đơn vừa tới: **chủ động gọi điện báo người nhận ngay** (kênh báo tin duy nhất). Gọi được thì **tích "đã thông báo được"**. Chưa gọi được thì tự thử lại vài lần trong 1–2 ngày đầu. Có thể đọc lại mã vận đơn qua điện thoại nếu người nhận chưa có mã.
3. Người nhận tới quầy, đọc **mã vận đơn** (hoặc quét mã vạch). Quên mã → tra theo **SĐT người nhận**, đối chiếu thêm họ tên.
4. Hệ thống chỉ cho giao khi đơn đang ở đúng văn phòng mình và ở trạng thái chờ lấy (⏳ hoặc hàng tồn theo thỏa thuận UC-25); chặn nếu hàng chưa tới, đã giao, hoặc 🆕 đã hủy. Nếu đơn có báo cáo thất lạc/hư hỏng của phụ xe (UC-28), hệ thống cảnh báo để kiểm hàng cùng người nhận.
5. Đơn COD → thu tiền mặt, xác nhận đã thu trước khi giao. Đơn trả trước → giao thẳng.
6. Xác nhận giao → `da_giao`, ghi thời điểm + nhân viên; in phiếu bàn giao nếu cần.

### 5.3. Xử lý hàng chờ quá lâu (UC-25)

*(Nguồn: `NGHIEP_VU.md` mục 10.3.1 điểm 3–4, UC-25)*

- **Mốc 7 ngày** (job tự động): bật cờ cảnh báo, nhắc nhân viên văn phòng nhận:
  - Đã từng báo được người nhận → gọi lại người nhận hỏi khi nào tới lấy (hoặc nhờ người lấy hộ...).
  - Chưa từng báo được → chuyển sang gọi **người gửi** hỏi hướng xử lý.
- **Mốc 14 ngày** (job tự động): chuyển **hàng tồn** (`qua_han_luu_kho`), **không tự hủy**; nhắc nhân viên liên hệ người gửi.
- Liên hệ được → xử lý theo thỏa thuận (chờ thêm, nhờ lấy hộ, gửi lại...). Không liên hệ được ai → **báo `quan_ly`** xử lý thủ công (thanh lý). Nút "báo quản lý" chỉ dùng được khi đơn đã có cờ 7 ngày hoặc đã là hàng tồn.
- ⏳ Mỗi lần liên hệ được ghi vào **lịch sử liên hệ** (gọi ai, kết quả, hướng xử lý đã thỏa thuận, ai gọi) — cần khi quản lý thanh lý hàng tồn. `NGHIEP_VU.md` 10.3.1 hiện ghi "chỉ lưu 1 cờ, không đếm số cuộc gọi" (KE_HOACH S4.3).

### 5.4. 🆕 Khi người gửi muốn **hủy** đơn (UC-54)

*(Nhóm chốt 09/10/2026 — xem mục 9)*

1. Người gửi tới quầy **văn phòng gửi**, đưa biên nhận hoặc đọc mã vận đơn. Mất biên nhận → tra theo SĐT người gửi, xác minh họ tên.
2. Hệ thống chỉ cho hủy khi đơn đang `cho_van_chuyen`, **chưa gắn chuyến**, và điểm gửi là văn phòng của nhân viên. Đơn đã rời văn phòng gửi → không hủy, hướng dẫn xử lý ở văn phòng nhận theo UC-25.
3. Chọn lý do hủy (bắt buộc): khách đổi ý / nhập sai thông tin, cần tạo lại / hàng không đủ điều kiện / khác (bắt buộc ghi chú).
4. Số tiền hoàn: trả trước đã thu → **hoàn đủ cước, tiền mặt**. COD hoặc chưa thu → không hoàn. Không thu phí hủy.
5. Gỡ nhãn khỏi kiện, thu lại biên nhận, trả kiện hàng (kèm tiền hoàn) cho người gửi, tích xác nhận "đã trả hàng", xác nhận hủy.
6. Đơn `da_huy`, ghi lý do, người hủy, thời điểm, tiền hoàn. Có hoàn tiền thì in **phiếu hủy đơn / hoàn tiền** cho người gửi ký.
7. Hủy vì nhập sai → tạo đơn mới ngay (điền sẵn người gửi, người nhận, loại hàng, cân nặng; chọn lại văn phòng nhận, tuyến, cước, thanh toán), thu tiền đơn mới riêng — không bù trừ với tiền hoàn.

### 5.5. ⏳ Sửa tên / SĐT người gửi, người nhận

- Văn phòng gửi lẫn văn phòng nhận đều sửa được, khi đơn **chưa giao và chưa hủy**. Gõ nhầm SĐT là lý do chính khiến không gọi được người nhận.
- **Chỉ sửa tên và SĐT.** Đổi tuyến, điểm nhận, loại hàng hoặc cước ảnh hưởng chuyến xe và tiền → phải **hủy đơn rồi tạo lại** (mục 5.4).
- Mỗi lần sửa ghi **nhật ký** (trường nào, cũ → mới, ai sửa, lúc nào, lý do). Văn phòng còn lại nhận thông báo để gọi đúng số.

---

## 6. Tiền, thống kê và đối soát

*(Nguồn: `NGHIEP_VU.md` UC-39; phần tiền ⏳ 🆕)*

- Tiền mặt thu tại quầy: **cước trả trước** thu ở văn phòng gửi lúc tạo đơn; **cước COD** thu ở văn phòng nhận lúc giao. Mỗi khoản ghi người thu và thời điểm thu.
- 🆕 **Tiền hoàn khi hủy đơn** chi ở văn phòng gửi, ghi vào người hủy, theo ngày hủy. Không đi qua kế toán.
- **Doanh thu** gửi hàng trong kỳ = trả trước đã thu + COD đã thu − tiền đã hoàn. Mỗi khoản tính theo đúng ngày của nó, nên ngày chỉ có hoàn (thu từ hôm trước) có thể có doanh thu **âm** — đúng tiền mặt thực tế.
- ⏳ **Đối soát két cuối ca** theo từng nhân viên: tiền đã thu − tiền đã hoàn trong kỳ; xuất CSV / in được.
- **Thống kê (UC-39)** — nhân viên chỉ xem văn phòng mình, `quan_ly` / `quan_ly_nhan_su` xem toàn hệ thống; chọn khoảng ngày:
  - Hàng gửi đi: đơn tiếp nhận trong kỳ, đang chờ xếp xe, đang trên xe, 🆕 hủy trong kỳ.
  - Hàng nhận về: tới văn phòng trong kỳ, đã giao, sắp đến, chờ lấy, chưa gọi báo được, chờ quá 7 ngày, hàng tồn.
  - Biểu đồ sản lượng theo ngày (tiếp nhận / đã giao).
- Chỉ đọc, không thay đổi dữ liệu.

---

## 7. Phối hợp với vai trò khác

*(Nguồn: `NGHIEP_VU.md` mục 10.5, 8.2, 8.7)*

| Vai trò | Liên quan tới gửi hàng |
|---|---|
| Phụ xe | Chất hàng (UC-26), dỡ hàng (UC-27), báo thất lạc/hư hỏng (UC-28) — tự quyết đơn nào lên xe. Đơn đã hủy tự biến mất khỏi danh sách chờ chất |
| `quan_ly` | Cấu hình danh mục loại hàng / hàng cấm; **chỉ xem** đơn, hàng đến, hàng tồn, thống kê (không tạo/giao/hủy); nhận báo cáo hàng tồn để thanh lý; nhận báo cáo sự cố hàng |
| `quan_ly_nhan_su` | Tạo/khóa tài khoản nhân viên gửi hàng; xem thống kê |
| Kế toán | **Không liên quan.** Hoàn tiền hủy đơn hàng trả tiền mặt ngay tại quầy, khác luồng hoàn tiền vé (UC-22) |
| Điều độ viên | Không theo dõi khối lượng hàng (đã bỏ từ thiết kế lại 16/09) |

---

## 8. Use case

### 8.1. Ma trận

*(Cùng thứ tự cột với `NGHIEP_VU.md` mục 11)*

| # | Use case | khách hàng | phụ xe | tài xế | nhân viên quầy vé | nhân viên gửi hàng | điều độ viên | kế toán | quản lý nhân sự | quản lý |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| UC-23 | Nhận/gửi hàng tại quầy, tính cước | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-24 | Giao hàng cho người nhận, thu COD | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-25 | Xử lý hàng quá hạn lưu kho *(gồm cơ chế UC-46 cũ)* | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-26 | Xác nhận chất hàng lên xe | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-27 | Xác nhận dỡ hàng khỏi xe | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-28 | Báo thất lạc/hư hỏng hàng | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-39 | Xem thống kê doanh thu/vận hành | ❌ | ✅ (chuyến mình) | — | ✅ (vé, điểm mình) | ✅ (hàng, điểm mình) | ✅ (điểm/tuyến mình) | ❌ | ✅ (toàn hệ thống) | ✅ (toàn hệ thống) |
| 🆕 UC-54 | Hủy đơn gửi hàng (hoàn cước trả trước tại quầy) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |

### 8.2. UC-23. Nhận/gửi hàng tại quầy, tính cước

- **Actor**: Nhân viên gửi hàng.
- **Tiền điều kiện**: Đã đăng nhập, tại đúng văn phòng phụ trách.
- **Luồng chính**:
  1. Nhập thông tin người gửi + người nhận (tên + SĐT).
  2. Chọn điểm đến (khu vực) → chọn văn phòng nhận cụ thể.
  3. Hệ thống xác định **tuyến** đi từ điểm gửi tới điểm nhận (nhiều tuyến thì nhân viên chọn 1) — **không chọn chuyến cụ thể**.
  4. Cân/đo hàng thực tế, nhập cân nặng + kích thước, chọn loại hàng.
  5. Hệ thống kiểm tra hàng cấm.
  6. Nhập giá cước, báo giá cho khách xác nhận.
  7. Chọn phương thức thanh toán.
  8. Tạo đơn `cho_van_chuyen` (gắn tuyến, chưa gắn chuyến), in biên nhận + mã vận đơn cho người gửi.
- **Luồng rẽ nhánh**:
  - Tại bước 3: không có tuyến nào nối 2 điểm → báo lỗi, từ chối nhận → kết thúc.
  - Tại bước 5: hàng cấm → chặn ngay, từ chối nhận → kết thúc.
  - Tại bước 7: người gửi trả trước → thu tiền mặt ngay. COD → không thu, để người nhận trả sau.
- **Hậu điều kiện**: Đơn `cho_van_chuyen`, chưa gắn chuyến, chờ phụ xe chọn xếp lên 1 chuyến cùng tuyến (UC-26).

### 8.3. UC-24. Giao hàng cho người nhận, thu COD

- **Actor**: Nhân viên gửi hàng (tại điểm nhận).
- **Tiền điều kiện**: Đơn `cho_lay` (từ UC-27) — ⏳ hoặc hàng tồn khi người nhận tới lấy theo thỏa thuận UC-25; người nhận có mặt tại quầy.
- **Luồng chính**:
  1. Người nhận đọc mã vận đơn (hoặc SĐT + xác minh tên nếu quên mã).
  2. Tra đúng đơn hàng.
  3. Kiểm tra phương thức thanh toán.
  4. Xác nhận giao → `da_giao`, ghi thời điểm + nhân viên xử lý.
- **Luồng rẽ nhánh**:
  - Tại bước 2: không khớp / không tìm thấy → xác minh lại → kết thúc hoặc thử lại.
  - Tại bước 2: hàng chưa tới, đã giao, đơn thuộc văn phòng nhận khác, hoặc 🆕 đơn đã hủy → không cho giao → kết thúc.
  - Tại bước 3: COD → thu tiền trước khi giao → bước 4. Trả trước → giao thẳng → bước 4.
- **Hậu điều kiện**: Đơn `da_giao`.

### 8.4. UC-25. Xử lý hàng chờ quá lâu tại điểm nhận *(gồm cơ chế UC-46 cũ)*

- **Actor**: Nhân viên gửi hàng.
- **Tiền điều kiện**: Đơn `cho_lay` có cờ cảnh báo (đủ 7 ngày) hoặc đã là hàng tồn (đủ 14 ngày) mà chưa ai tới lấy.
- **Luồng chính**:
  1. Xem danh sách đơn đang cảnh báo / hàng tồn tại điểm mình.
  2. Kiểm tra đơn đã từng thông báo được người nhận chưa.
  3. Liên hệ theo đúng tình huống.
- **Luồng rẽ nhánh**:
  - Đã từng thông báo được người nhận → gọi lại người nhận hỏi khi nào tới lấy hoặc hướng xử lý khác.
  - Chưa từng thông báo được → gọi thẳng người gửi.
  - Liên hệ được, có hướng xử lý → xử lý theo thỏa thuận (chờ thêm, gửi lại, hoàn, hoặc hủy hàng) → kết thúc.
  - Không liên hệ được ai → báo `quan_ly` xử lý thủ công (thanh lý) → kết thúc.
- **Hậu điều kiện**: Đơn được xử lý theo thỏa thuận, hoặc chờ `quan_ly` thanh lý.

**Nhánh kèm theo — job tự động (UC-46 cũ)**: actor là hệ thống. Đơn `cho_lay` đủ 7 ngày kể từ lúc tới điểm nhận → bật cờ cảnh báo, nhắc nhân viên (nội dung nhắc tùy đã/chưa báo được người nhận). Đủ 14 ngày → chuyển hàng tồn, nhắc liên hệ người gửi. **Không có nhánh nào tự hủy hay thanh lý.**

### 8.5. UC-26, UC-27, UC-28 (phụ xe — tóm tắt)

- **UC-26 Chất hàng lên xe**: chuyến chưa khởi hành/đang chạy, đang đứng tại điểm gửi. Phụ xe xem đơn chờ cùng tuyến, cùng chiều, tại điểm đang đứng (cũ trước), tự chọn đơn chất lên → gán chuyến, `da_len_xe`. Đơn không chọn giữ nguyên chờ chuyến sau.
- **UC-27 Dỡ hàng**: xe tới đúng điểm nhận của đơn → xác nhận dỡ → `cho_lay`, ghi thời điểm tới (mốc tính 7/14 ngày), thông báo nhân viên văn phòng nhận gọi báo người nhận.
- **UC-28 Báo thất lạc/hư hỏng**: ghi báo cáo, chuyển thông báo tới nhân viên gửi hàng (văn phòng gửi nếu chưa lên xe, văn phòng nhận nếu đã lên xe) và `quan_ly`. Không đổi trạng thái đơn, không chặn UC-26/27.

### 8.6. UC-39. Xem thống kê (phần nhân viên gửi hàng)

- **Actor**: Nhân viên gửi hàng (chỉ hàng, văn phòng mình); `quan_ly`, `quan_ly_nhan_su` (toàn hệ thống).
- **Luồng chính**: chọn khoảng thời gian → hệ thống lọc theo phạm vi vai trò → tính động các chỉ số (mục 6) → hiển thị.
- **Hậu điều kiện**: chỉ đọc.

### 8.7. 🆕 UC-54. Hủy đơn gửi hàng

- **Actor**: Nhân viên gửi hàng tại văn phòng gửi của đơn.
- **Tiền điều kiện**: Đã đăng nhập, đúng văn phòng gửi. Đơn `cho_van_chuyen`, chưa gắn chuyến. Người gửi có mặt tại quầy.
- **Luồng chính**:
  1. Người gửi đưa biên nhận / đọc mã vận đơn.
  2. Nhân viên tra đúng đơn.
  3. Chọn lý do hủy.
  4. Hệ thống hiện số tiền phải hoàn.
  5. Trả kiện hàng (kèm tiền hoàn nếu có), gỡ nhãn, thu lại biên nhận.
  6. Xác nhận hủy → `da_huy`, ghi lý do, người hủy, thời điểm, tiền hoàn.
  7. In phiếu hủy / hoàn tiền cho người gửi ký (nếu có hoàn).
- **Luồng rẽ nhánh**:
  - Tại bước 1: mất biên nhận → tra SĐT người gửi, xác minh họ tên → bước 2.
  - Tại bước 2: đơn đã lên xe / đã tới điểm nhận / đã giao → từ chối, hướng dẫn xử lý ở văn phòng nhận theo UC-25 → kết thúc.
  - Tại bước 2: đơn của văn phòng gửi khác → từ chối → kết thúc.
  - Tại bước 2: đơn đã bị hủy → báo đã hủy → kết thúc.
  - Tại bước 3: chọn "Khác" mà không ghi chú → yêu cầu ghi chú → bước 3.
  - Tại bước 4: trả trước đã thu → hoàn đủ cước tiền mặt. COD / chưa thu → không hoàn.
  - Tại bước 6: phụ xe vừa chất đơn lên xe đúng lúc đó (hoặc người khác vừa hủy) → báo "đơn đã thay đổi", không hủy → kết thúc.
  - Sau bước 7: lý do "nhập sai thông tin" → tạo đơn mới (UC-23) với thông tin điền sẵn.
- **Hậu điều kiện**: Đơn `da_huy`, đủ lý do, người hủy, thời điểm, tiền hoàn. Biến mất khỏi danh sách chờ chất hàng. Không xóa đơn, mã vận đơn không dùng lại.

---

## 9. Quyết định đã chốt và điểm chờ xác nhận

### 9.1. 🆕 Hủy đơn — nhóm chốt 09/10/2026

| # | Nội dung | Đã chốt |
|---|---|---|
| B1 | Trạng thái được hủy | Chỉ `cho_van_chuyen` **và** chưa gắn chuyến |
| B2 | Đơn đã lên xe / chờ lấy / hàng tồn / đã giao | Không hủy; người gửi muốn lấy lại thì xử lý theo UC-25 |
| B3 | Giới hạn thời gian | Không có, chỉ theo trạng thái |
| B4 | Ai được hủy | Nhân viên gửi hàng của văn phòng gửi (không bắt buộc là người tạo đơn); văn phòng nhận và `quan_ly` không hủy |
| B5 | Quản lý duyệt | Không cần; ghi người hủy, quản lý xem được |
| B6 | Xác minh người gửi | Có mặt, đưa biên nhận / đọc mã; mất biên nhận thì tra SĐT + họ tên |
| B7 | Lý do | Bắt buộc, 4 lựa chọn; "Khác" bắt buộc ghi chú |
| B8 | Phí hủy | Không thu |
| B9 | Hoàn tiền | Trả trước đã thu → hoàn 100% tiền mặt tại quầy; COD / chưa thu → không hoàn |
| B10 | Qua kế toán | Không |
| B11 | Hủy để tạo lại | Hoàn đơn cũ, thu đơn mới riêng, không bù trừ |
| B12 | Thống kê / đối soát | Tiền hoàn ghi riêng, trừ vào doanh thu theo ngày hủy, tại văn phòng gửi |
| B13 | Ảnh hưởng phụ xe | Không phải sửa UC-26 |
| B14 | Số UC | UC-54 |

### 9.2. ⏳ Đã có trong code, chờ nhóm xác nhận (KE_HOACH D8)

| Điểm | Code đang làm | `NGHIEP_VU.md` đang ghi |
|---|---|---|
| Lịch sử liên hệ (S4.3) | Lưu từng lần gọi: đối tượng, kết quả, hướng xử lý, người gọi | "Chỉ lưu 1 cờ, không đếm số cuộc gọi" (10.3.1) |
| Giao hàng tồn (S2.11) | Giao được cả đơn `qua_han_luu_kho` theo thỏa thuận UC-25 | "Chỉ cho giao nếu `cho_lay`" (10.4.2 bước 3) |
| Sửa tên/SĐT | Sửa được khi chưa giao/chưa hủy, có nhật ký | Chưa có |
| Đối soát tiền theo nhân viên | Thu − hoàn theo người thu/người hoàn | Chưa có |
