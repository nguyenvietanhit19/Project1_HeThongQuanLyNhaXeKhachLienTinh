# Thiết kế — Thống kê theo Ngày / Tháng / Năm, biểu đồ và xuất báo cáo (role gửi hàng)

Ngày: 05/11/2026 · Phạm vi: tab **Thống kê & đối soát** của trang nhân viên gửi hàng (`frontend/nhan-vien/gui-hang/`) và API `/gui-hang/*` (UC-39).

Nhánh: làm tiếp trên `feature/Trinh-gui-hang-su-co-xe` (người dùng chọn). Cả nhánh — tài liệu sự cố xe phần B, quy trình test, script test giao diện và tính năng này — đi chung một PR vào `integration/gop-nhanh-thanh-vien`.

## 1. Mục đích

Hiện tab Thống kê chỉ chọn được "khoảng ngày" (Hôm nay / 7 / 30 ngày / tự nhập), có 1 biểu đồ sản lượng chạy **độc lập** với bộ lọc (7/14/30 ngày gần nhất), và chỉ xuất được CSV bảng đối soát.

Người dùng (nhân viên gửi hàng, quản lý) cần:

- Xem số liệu theo **kỳ quen thuộc**: một ngày, một tháng, một năm — và lùi/tiến từng kỳ để so sánh.
- **Nhìn bằng biểu đồ**: sản lượng, dòng tiền, cơ cấu cách trả cước, tiền theo nhân viên.
- **Xuất báo cáo** của kỳ đó: file Excel để nộp/tính tiếp, bản in/PDF có biểu đồ để ký nộp.

## 2. Mục tiêu / Không làm / Không được xảy ra

**Mục tiêu**
- Bộ chọn kỳ Ngày / Tháng / Năm / Tùy chọn; **mọi** phần trong tab (ô số liệu, khung tiền mặt, biểu đồ, bảng đối soát) dùng chung một kỳ.
- 4 biểu đồ (mục 5).
- Xuất Excel (.xlsx, 3 trang tính) và In báo cáo (có biểu đồ, lưu PDF bằng hộp thoại in của trình duyệt).

**Không làm**
- Không nhúng biểu đồ vào file Excel (Excel chỉ có bảng số).
- Không thêm thư viện vẽ biểu đồ — tiếp tục vẽ SVG tay như biểu đồ hiện có.
- Không đổi cách tính tiền/số đơn đang có (NGHIEP_VU_GUI_HANG.md mục 6).
- Không thêm kỳ theo tuần, không so sánh với kỳ trước, không gửi báo cáo tự động.
- Không đụng thống kê của role khác.

**Không được xảy ra** (coi là hỏng dù chạy được)
- Số trên biểu đồ / file xuất **lệch** với ô số liệu của cùng kỳ (tổng các mốc ≠ tổng kỳ) do **cách tính** khác nhau. *(Quyết định của Claude: bất biến này xét trên dữ liệu đứng yên. Tab vẫn gọi 3 API riêng; nếu có đơn mới chen giữa các lần gọi thì lệch tạm thời được chấp nhận, bấm tải lại là khớp. Xuất Excel và In báo cáo **dùng lại đúng dữ liệu đang hiện trên tab**, không gọi API lại, nên file xuất luôn khớp với màn hình.)*
- Nhân viên xuất/xem được số liệu văn phòng khác (phạm vi phải đi qua `_pham_vi_van_phong` như hiện tại).
- Lệch ngày do múi giờ (mọi mốc tính theo giờ Việt Nam, `MUI_GIO_VN`).

## 3. Bộ chọn kỳ (giao diện)

Thay nhóm nút `#tkPreset` (Hôm nay / 7 ngày / 30 ngày) bằng 4 chế độ:

| Chế độ | Ô chọn | Kỳ gửi lên API | Biểu đồ chia theo |
|---|---|---|---|
| **Ngày** | `<input type="date">` | tu = den = ngày chọn | **giờ** (0h–23h, 24 mốc) |
| **Tháng** (mặc định, tháng hiện tại) | `<input type="month">` | ngày 1 → ngày cuối tháng | **ngày** |
| **Năm** | ô chọn năm (năm hiện tại và 4 năm trước) | 01/01 → 31/12 | **tháng** (12 mốc) |
| **Tùy chọn** | Từ – đến (2 ô date, như hiện có) | tu, den | **ngày** nếu ≤ 62 ngày, **tháng** nếu dài hơn |

- Nút **◀ ▶** cạnh ô chọn để lùi/tiến 1 kỳ (ngày/tháng/năm). ▶ bị khóa khi kỳ đang xem đã chứa hôm nay. Chế độ Tùy chọn không có ◀ ▶.
- Kỳ chưa kết thúc (vd tháng này): trục vẫn đủ cả kỳ, các mốc sau thời điểm hiện tại **không vẽ** cột/điểm (để trống, không vẽ cột 0).
- Giới hạn khoảng tối đa 1 năm (`SO_NGAY_THONG_KE_TOI_DA = 366`) giữ nguyên; năm nhuận vẫn lọt.
- Bỏ nhóm nút 7/14/30 ngày riêng của biểu đồ (`#tkBieuDoRange`, `state.bieuDoSoNgay`).
- Tiêu đề tab hiện rõ kỳ đang xem, vd "Tháng 11/2026", "Ngày 05/11/2026", "Năm 2026", "01/10/2026 – 05/11/2026".
- Các chỉ số **tồn** (đang chờ xếp xe, đang trên xe, sắp đến, chờ lấy, chưa báo, chờ > 7 ngày, tồn > 14 ngày) vẫn là ảnh chụp **hiện tại**, không theo kỳ — giữ như cũ, ghi chú nhỏ "tính tại thời điểm xem".

## 4. Backend — API mới

`GET /gui-hang/thong-ke-chuoi` — quyền `QuyenThongKe`, phạm vi `_pham_vi_van_phong(nguoi_dung, diem_id)`.

Tham số: `tu_ngay` (date, bắt buộc), `den_ngay` (date, bắt buộc), `don_vi` ∈ `gio | ngay | thang` (bắt buộc), `diem_id` (tùy chọn, như các API thống kê khác).

Kiểm tra (service, ném `GiaTriLoi`):
- `_kiem_tra_khoang_ngay(tu, den)` như hiện có.
- `don_vi = gio` chỉ khi `tu == den`.
- `don_vi = ngay` chỉ khi khoảng ≤ 62 ngày.
- `diem_id` không tồn tại → lỗi, giống `thong_ke_hang_tai_diem`.

Trả về danh sách **đủ mọi mốc** trong kỳ (mốc không có dữ liệu = 0), sắp theo thời gian:

```json
[{ "moc": "2026-11-01", "tiep_nhan": 12, "da_giao": 9, "so_huy": 1,
   "tien_tra_truoc": 450000, "tien_cod": 300000, "tien_hoan": 50000, "doanh_thu": 700000 }]
```

- `moc`: giờ → `"2026-11-05T14:00"`; ngày → `"2026-11-05"`; tháng → `"2026-11-01"` (ngày đầu tháng).
- Mỗi trường dùng **đúng mốc thời gian và đúng phía văn phòng** như `thong_ke_hang_tai_diem`:

| Trường | Mốc thời gian | Phía văn phòng | Điều kiện |
|---|---|---|---|
| `tiep_nhan` | `ngay_tao` | gửi | — |
| `da_giao` | `ngay_giao` | nhận | `trang_thai = 'da_giao'` |
| `so_huy` | `thoi_gian_huy` | gửi | `trang_thai = 'da_huy'` |
| `tien_tra_truoc` | `thoi_gian_thu` | gửi | `nguoi_gui_tra_truoc` và `da_thu_tien` |
| `tien_cod` | `thoi_gian_thu` | nhận | `cod_nguoi_nhan_tra` và `da_thu_tien` |
| `tien_hoan` | `thoi_gian_huy` | gửi | `so_tien_hoan` |
| `doanh_thu` | — | — | `tien_tra_truoc + tien_cod − tien_hoan` (có thể âm) |

- **Bất biến**: tổng mọi mốc của mỗi trường = trường tương ứng của `GET /gui-hang/thong-ke` cùng kỳ, cùng phạm vi (`tong_don_gui_di`, `so_don_da_giao`, `so_huy`↔`so_don_huy`, `tien_cuoc_gui_tra_truoc`, `tien_cod_da_thu`, `tien_da_hoan`, `tong_doanh_thu`).
- Gợi ý cài đặt: một truy vấn — `generate_series` sinh mốc, `date_trunc(don_vi, … AT TIME ZONE MUI_GIO_VN)` cho từng cột thời gian, gộp bằng `count/sum … FILTER`. Đặt ở `don_hang_repository.py` cạnh `thong_ke_hang_theo_ngay`.
- **Gỡ** API cũ `GET /gui-hang/thong-ke-theo-ngay` (route, service, repo) — chỉ tab này dùng (đã grep, không chỗ nào khác gọi).
- `/thong-ke` và `/doi-soat` giữ nguyên, frontend gửi `tu_ngay/den_ngay` của kỳ.

## 5. Biểu đồ (SVG vẽ tay)

Tách phần vẽ chung từ `veBieuDo()` hiện có (trục, lưới, bước chia "tròn" `buocTrucDoc`, nhãn thưa dần, vẽ lại khi đổi rộng bằng `ResizeObserver`, tooltip bằng `<title>`) thành các hàm dùng lại. Nhãn trục X theo đơn vị: giờ "14h", ngày "05/11", tháng "Th11".

1. **Sản lượng** — cột đôi Tiếp nhận / Đã giao theo mốc (giữ màu và chú thích hiện có).
2. **Tiền mặt theo thời gian** — cột chồng Trả trước + Thu khi giao; một đường **Còn lại** (`doanh_thu`). Trục dọc có phần âm khi có mốc doanh thu âm. Tooltip mỗi mốc ghi đủ: trả trước, thu khi giao, hoàn, còn lại. Trục tiền rút gọn (vd "1,2tr", "500k").
3. **Cơ cấu cách trả cước** — biểu đồ tròn (vành khuyên) theo **tiền** của kỳ: trả trước (`tien_cuoc_gui_tra_truoc`) và người nhận trả (`tien_cod_da_thu`); giữa vòng ghi tổng; chú thích ghi tiền, % và số đơn (cộng `so_don_tra_truoc` / `so_don_cod` từ dữ liệu đối soát). Cả hai = 0 → chữ "Chưa có khoản thu trong kỳ".
4. **Tiền theo nhân viên** — cột ngang `tong_tien` theo nhân viên từ dữ liệu `/doi-soat`, xếp giảm dần; quá 10 người thì gộp phần còn lại thành "Khác"; giá trị âm (chỉ có hoàn) vẽ màu khác. Đặt cạnh bảng đối soát.

Bố cục: (1) và (2) mỗi cái một hàng rộng; (3) và (4) chung một hàng hai cột, xuống một cột ở màn hình hẹp. Kỳ không có dữ liệu → chữ báo trống trong khung, không vẽ trục rỗng. Mỗi biểu đồ tải lỗi thì báo lỗi riêng trong khung của nó.

## 6. Xuất báo cáo

Thêm hai nút ở đầu tab, cạnh bộ chọn kỳ: **⬇️ Xuất Excel** và **🖨️ In báo cáo**. Nút "Xuất CSV" và "In" của riêng bảng đối soát giữ nguyên.

**Excel (.xlsx)** — dùng SheetJS bản community, **lưu vào `frontend/nhan-vien/gui-hang/vendor/`** (giống `JsBarcode` đang để ở đó, không phụ thuộc CDN), chỉ tải khi bấm nút (lazy load). 3 trang tính:

1. **Tổng quan** — văn phòng (hoặc "Toàn hệ thống"), kỳ, người xuất, thời điểm xuất; toàn bộ chỉ số của `/thong-ke` có nhãn tiếng Việt như trên giao diện; ghi chú các chỉ số tồn tính tại thời điểm xuất.
2. **Theo giờ / Theo ngày / Theo tháng** (tên theo đơn vị) — mỗi mốc một dòng với đủ các cột của mục 4, dòng **TỔNG** cuối.
3. **Đối soát nhân viên** — cùng cột như CSV hiện có, dòng TỔNG.

Tiền là **số** (định dạng `#,##0`), không phải chuỗi. Giữ chống chèn công thức như `xuatCsv` (tên nhân viên bắt đầu bằng `= + - @`). Tên file: `thong-ke-gui-hang_<kỳ>.xlsx`, `<kỳ>` = `2026-11-05` / `2026-11` / `2026` / `2026-10-01_2026-11-05`.

**In báo cáo** — dựng một vùng báo cáo riêng (ẩn trên màn hình) rồi in bằng `inPhanTu` sẵn có:
- Đầu trang: tên báo cáo, văn phòng, kỳ, người in, thời điểm in.
- Bảng chỉ số tổng quan, khung tiền mặt.
- 4 biểu đồ vẽ lại ở chiều rộng cố định vừa khổ A4 dọc, giữ màu khi in (`print-color-adjust: exact`).
- Bảng đối soát nhân viên, cuối trang hai ô ký "Người lập" / "Người nhận tiền".
- Lưu PDF bằng "Lưu dưới dạng PDF" của hộp thoại in.

## 7. Tài liệu và kiểm thử

- `NGHIEP_VU_GUI_HANG.md` mục 6 và 8.6: chọn kỳ Ngày/Tháng/Năm/Tùy chọn, 4 biểu đồ, xuất Excel/In báo cáo.
- `KE_HOACH_SUA_GUI_HANG.md`: thêm mục mới cho đợt này (theo quy ước của role — mọi thay đổi ghi vào đây).
- Unit test (`backend/tests/unit/test_gui_hang_service.py`, giả lập repo như các test thống kê hiện có): kiểm tra tham số (`gio` khi tu ≠ den, `ngay` > 62 ngày, khoảng ngược, quá 1 năm, `don_vi` lạ, `diem_id` không tồn tại), truyền đúng phạm vi xuống repo.
- Kiểm tra trên DB thật (thêm vào Bước 4 "kiểm tra API" của `QUY_TRINH_TEST_GUI_HANG.md`): bất biến tổng mốc = `/thong-ke` cho cả 3 đơn vị, một văn phòng và toàn hệ thống.
- Ca test giao diện mới trong `QUY_TRINH_TEST_GUI_HANG.md` và `backend/scripts/kiem_thu_giao_dien_gui_hang.py`: đổi chế độ kỳ, ◀ ▶, biểu đồ có dữ liệu, xuất Excel tải được file, nút In mở hộp thoại.

## 8. Để người làm tự quyết

Tên hàm/biến, cách chia file JS (có thể tách phần vẽ biểu đồ ra `bieu-do.js`), màu biểu đồ 2–4 (lấy từ `design-tokens.css`), chi tiết bố cục bản in, bản SheetJS cụ thể.
