# Kế hoạch sửa & nâng cấp — Nhân viên gửi hàng (FE + BE)

> Căn cứ: `NGHIEP_VU.md` mục 2, 8.5, 10 (10.1–10.5), UC-23/24/25/26/27/28/39/46; `DATABASE.md` mục 5; `THIET_KE_UI.md`.
> Nguồn: 4 hướng rà soát độc lập (BE, FE, checklist nghiệp vụ, tích hợp liên vai trò) ra 98 phát hiện. 68 phát hiện đã qua kiểm chứng phản biện (65 đúng, 3 bị bác). 30 phát hiện tích hợp chưa qua bước phản biện tự động. Các phát hiện mức nghiêm trọng/cao trong số này đã được đối chiếu thủ công với code và git.
> Ký hiệu công sức: **S** < 1 giờ · **M** nửa ngày · **L** ≥ 1 ngày.

> **Trạng thái (04/10/2026):** đã làm toàn bộ Đợt 0–4 và nâng cấp N1 (màn Hàng đến), N3 (in đúng vùng), N4 (đối soát tiền theo nhân viên), N6 (thông báo WebSocket + chuông). Đã làm thêm (05/10/2026): N2 mã vạch Code128, N5 lịch sử trạng thái, N7 chống tạo trùng đơn (Idempotency-Key), N8 tách app.js thành module, N9 phím tắt; cùng gợi ý khách quen theo SĐT, xuất CSV, đếm ngược mốc 7/14 ngày. Đã làm thêm: sửa tên/SĐT người gửi-nhận khi đơn chưa giao + nhật ký chỉnh sửa (migration 20261006). Chưa làm: hủy đơn (đợt B, cần nhóm chốt trạng thái `da_huy` và hoàn tiền mặt), hàng đợi khi mất mạng, chốt ca.

> **Trạng thái (07/10/2026):** bắt đầu đợt B — hủy đơn, nhánh `feature/Trinh-huy-don`. Kế hoạch chi tiết ở **mục 6**. **Đã code xong BE + FE theo đúng các đề xuất ở 6.1** (xem 6.5), `DATABASE.md` đã cập nhật (D7). **09/10: nhóm đã chốt B1–B14 đúng đề xuất**; toàn bộ nghiệp vụ của vai trò (kể cả hủy đơn) gộp ở file riêng `NGHIEP_VU_GUI_HANG.md` (không sửa `NGHIEP_VU.md`). Mục 2 (phối hợp) vẫn mở, trừ P4 đã sửa và P6 đã có cột `sdt_lien_he`.

---

## 0. Tóm tắt

| | |
|---|---|
| Mức khớp nghiệp vụ hiện tại | Khoảng 75–80%. Luồng **gửi** (UC-23) gần đúng. Luồng **nhận/giao** (UC-24) và **hàng chờ lâu** (UC-25) có lỗ hổng làm hỏng thao tác hằng ngày. |
| Nghiêm trọng | 1. Hồi quy kiểm tra phụ xe ở chất/dỡ hàng, do commit `ff17985` (của bạn). |
| Cao | 6: điểm nhận không thấy hàng đến; in ra trang trắng; `API_BASE_URL` hỏng khi deploy; XSS; thiếu tra cứu SĐT; 5 unit test fail. |
| Trung bình | Khoảng 14 |
| Thấp | Khoảng 12 |
| Thuộc role khác (cần phối hợp) | 6 |

---

## 1. Kế hoạch sửa theo đợt

Mỗi đợt nên là **1 commit/PR riêng** để dễ review. Thứ tự đợt chính là thứ tự phụ thuộc.

### Đợt 0 — Khẩn cấp: hồi quy & test hỏng (làm trước tiên)

#### S0.1 Khôi phục kiểm tra "chuyến của tôi" + "điểm đang đứng" cho phụ xe (UC-26/27) · **Nghiêm trọng** · M
- **Vấn đề:**
  - Commit `9a6fb60` (tuanhdung) đã có `lay_chuyen_cua_phu_xe()` và `diem_hien_tai()` trong `danh_sach_cho_chat`, `danh_sach_cho_do`, `xac_nhan_chat_hang` và `xac_nhan_do_hang`.
  - Commit `ff17985` ("fales --> bo", trinhvan205) đã viết lại `gui_hang_service.py` và bỏ mất toàn bộ các kiểm tra này. Thay đổi đó đã vào main qua PR #20.
  - Hậu quả: phụ xe bất kỳ chất/dỡ được đơn của chuyến bất kỳ. Đơn có thể bị dỡ ở **sai văn phòng** nhưng vẫn hiện `cho_lay` ở điểm nhận dù hàng chưa tới, khiến UC-24 giao nhầm.
- **Căn cứ:** UC-26 (tiền điều kiện: chuyến đang tại điểm gửi), UC-27 (xe tới điểm nhận), mục 3.2 (chuyến của phụ xe suy ra từ `xe_nhan_su`).
- **File:** `backend/app/services/gui_hang_service.py:196-295`, `backend/app/repositories/don_hang_repository.py:194-231`.
- **Cách sửa:**
  1. Import lại: `from app.services.chuyen_xe_service import diem_hien_tai, lay_chuyen_cua_phu_xe` (không bị import vòng, `ve_service.py` cũng làm vậy).
  2. `danh_sach_cho_chat`: `chuyen = lay_chuyen_cua_phu_xe(...)`, rồi `diem = diem_hien_tai(chuyen)`. Chỉ trả đơn có `diem_gui_id == diem["diem_don_tra_id"]` và cùng chiều.
  3. `danh_sach_cho_do`: chỉ trả đơn `da_len_xe` của chuyến này có `diem_nhan_id == điểm hiện tại`. Dùng `tim_don_can_do_tai_diem` có sẵn.
  4. `xac_nhan_chat_hang`: kiểm tra quyền chuyến. Chuyến phải ở trạng thái `chua_khoi_hanh` hoặc `dang_chay` (bỏ `den_noi`, giá trị này không còn trong CHECK). Đơn phải nằm tại điểm hiện tại.
  5. `xac_nhan_do_hang`: `lay_chuyen_cua_phu_xe(don["chuyen_id"], ...)`, và điểm hiện tại phải bằng `diem_nhan_id`.
  6. Repo: thêm điều kiện trạng thái vào UPDATE (atomic, chống bấm 2 lần hoặc 2 người cùng thao tác):
     - Chất hàng: `... WHERE id=%s AND trang_thai='cho_van_chuyen' AND chuyen_id IS NULL RETURNING id`
     - Dỡ hàng: `... WHERE id=%s AND trang_thai='da_len_xe' AND chuyen_id=%s RETURNING id`
     - Nếu không có dòng nào: rollback, trả `None` để service báo "Đơn đã được người khác xử lý".
- **Nghiệm thu:** phụ xe B gọi `/phu-xe/chuyen/{chuyến của A}/hang-cho-chat` thì nhận 403. Dỡ đơn khi xe chưa tới điểm nhận thì nhận lỗi. Hai request chất cùng 1 đơn thì chỉ 1 request thành công.
- **Test:** khôi phục hoặc chuyển các test phụ xe tương ứng từ `9a6fb60`. Thêm test "UPDATE 0 dòng thì báo lỗi".
- **Lưu ý:** báo tuanhdung (người làm phụ xe) để cùng review, vì đây là code của họ bị ghi đè.

#### S0.2 Xóa endpoint phụ xe trùng trong `/gui-hang` · Cao · S
- **Vấn đề:** `gui_hang.py:30-32, 188-211` (`QuyenPhuXe`, `/tuyen/{id}/cho-xep-xe`, `/{id}/chat-hang`, `/{id}/do-hang`) là đường vòng qua mọi kiểm tra của `/phu-xe/*` và cho cả `quan_ly` gọi. Grep cho thấy không có client nào dùng.
- **Cách sửa:** xóa 3 route này và alias `QuyenPhuXe`. Sửa `THAY_DOI_TUYEN_2_CHIEU.md:92` để trỏ sang `/phu-xe/chuyen/{id}/hang-cho-chat`. Xóa `gui_hang_service.lay_danh_sach_cho_xep_xe` nếu không còn ai gọi.
- **Nghiệm thu:** `grep -r "cho-xep-xe\|/chat-hang" frontend backend` không còn kết quả. Phụ xe vẫn chạy đủ luồng qua `/phu-xe`.

#### S0.3 Sửa unit test gửi hàng đang fail · Cao · M
- **Vấn đề:** sau khi refactor (thêm `xac_nhan_da_thu`, đổi chữ ký liên hệ, đổi hàm job) có 5 test chắc chắn fail, và 1 hàm test trùng tên bị che (`test_gui_hang_service.py:61, 143, 293, 306`).
- **Cách sửa:**
  - Fixture `du_lieu_tao_don_mau` thêm `xac_nhan_da_thu=True`.
  - Test giao hàng thêm `da_thu_tien=True` và `diem_nhan_id`. Thêm 2 test: COD chưa xác nhận thu thì báo lỗi; văn phòng khác thì `KhongDuQuyen`.
  - Viết lại 2 test liên hệ theo chữ ký mới `cap_nhat_thong_bao_nguoi_nhan(don_id, nguoi_dung_id, van_phong_id, doi_tuong, ket_qua, ghi_chu)`.
  - Test job patch `quet_bat_canh_bao_va_lay_don`, `danh_sach_nhan_vien_gui_hang_tai_diem`, `thong_bao_repository.tao`.
  - Đổi tên hàm test trùng.
- **Nghiệm thu:** `pytest tests/unit -q` xanh trong môi trường đã cài `requirements.txt`.

---

### Đợt 1 — Lỗi chặn luồng nghiệp vụ chính

#### S1.1 Văn phòng nhận không thấy hàng đến để giao (UC-24, 10.4.2 bước 1) · Cao · M
- **Vấn đề:**
  - `/gui-hang/don-gan-day` chỉ lọc `d.diem_gui_id = văn phòng mình` (`gui_hang.py:132-146`, `don_hang_repository.py:571`).
  - Tab "Giao hàng" vì vậy chỉ thấy đơn **mình gửi đi**. Nút "Giao hàng" hiện trên đơn `cho_lay` của văn phòng khác, và BE sẽ từ chối.
  - Tab "Hàng tồn" có đúng danh sách nhưng không có nút giao.
- **Cách sửa:**
  - **BE:** thêm `huong: Literal["gui","nhan","tat_ca"] = "tat_ca"` cho `/don-gan-day`. Repo chọn điều kiện theo `huong`:
    - `gui`: `diem_gui_id=%s`
    - `nhan`: `diem_nhan_id=%s`
    - `tat_ca`: `(diem_gui_id=%s OR diem_nhan_id=%s)`
  - **FE:**
    - Tách khu "Đơn gửi đi" (`huong=gui`, chỉ xem/in lại) và khu "Hàng đến chờ giao" (`/hang-cho-lau`, có nút **Giao hàng**).
    - Chỉ hiện nút Giao khi `d.diem_nhan_id === vanPhongTrucId` và trạng thái là `cho_lay` hoặc `qua_han_luu_kho`.
    - Thêm nút "Giao hàng" vào hàng của tab Hàng tồn.
- **Nghiệm thu:** tạo đơn A→B, phụ xe dỡ tại B. Nhân viên B thấy đơn trong "Hàng đến chờ giao" và giao được. Nhân viên A không thấy nút Giao cho đơn đó.

#### S1.2 Tra cứu theo SĐT + xác minh tên khi người nhận quên mã (10.3.1 điểm 5, 10.4.2 bước 2) · Cao · M
- **Vấn đề:** BE đã có `/tra-cuu-sdt` nhưng FE không gọi. Ô tìm kiếm chỉ lọc phía client trên 50 đơn (`app.js:702-736, 1100-1122`).
- **Cách sửa:**
  - **BE:** thêm tham số `muc_dich: Literal["giao","tat_ca"]`. Với `giao`, lọc `diem_nhan_id = mình AND trang_thai IN ('cho_lay','qua_han_luu_kho')`.
  - **FE:** trong `traCuuDonHang`:
    - Nếu chuỗi nhập khớp `/^[0-9]{10,11}$/` thì gọi `/tra-cuu-sdt?sdt=...&muc_dich=giao`.
    - 0 kết quả: báo "không có đơn chờ giao".
    - 1 hoặc nhiều kết quả: hiện danh sách rút gọn (tên người nhận, mã vận đơn che giữa, ngày tới) để nhân viên **đối chiếu tên** với người nhận rồi chọn. Sau đó mở modal giao.
- **Nghiệm thu:** nhập SĐT người nhận ở quầy B thì ra đúng đơn chờ giao tại B, không ra đơn B gửi đi.

#### S1.3 In biên nhận / nhãn dán / phiếu xuất kho ra trang trắng (10.4.1 bước 8, 10.3.1 điểm 1) · Cao · S
- **Vấn đề:** `@media print` ở `style.css:1516-1547` chỉ hiện `#noiDungBienNhan` và `#noiDungTemDecal`, nhưng hai ID này **không tồn tại** trong `index.html`.
- **Cách sửa:** viết lại khối `@media print`:
  - `body * {visibility:hidden}`
  - `.modal-overlay.active .modal-box, .modal-overlay.active .modal-box * {visibility:visible}`
  - Đặt modal đang mở ở `position:absolute; left:0; top:0; width:100%`
  - Ẩn `.receipt-actions` và các nút đóng.
- **Nghiệm thu:** Ctrl+P ở từng modal (biên nhận, nhãn, phiếu xuất) cho ra đúng 1 trang có nội dung.

#### S1.4 `API_BASE_URL` sai khi deploy + không xử lý 401/403 · Cao · S
- **Vấn đề:**
  - `gui-hang/api-client.js:6` luôn gọi `<host FE>:8000`. Khi deploy lên Vercel/Render thì mọi API đều hỏng. Các trang khác dùng cách nhận diện theo hostname (`quan-ly/api-client.js:9-11`, `dang-nhap.html:56-58`).
  - Token hết hạn hoặc tài khoản bị khóa thì trang chỉ báo "Lỗi kết nối".
- **Cách sửa:**
  - Chép mẫu chung: localhost/127.0.0.1/IP LAN thì dùng `http://<host>:8000`, ngược lại dùng `https://nha-xe-khach-backend.onrender.com`.
  - Trong `apiFetch`: `401` thì `dangXuatNhanVien()`. `403 "Tài khoản đã bị khóa"` thì alert rồi đăng xuất. 403 khác thì throw như cũ.
- **Nghiệm thu:** mở trang trên domain deploy thì gọi đúng backend Render. Token hết hạn thì bị đưa về trang đăng nhập.

#### S1.5 Stored XSS qua `innerHTML` · Cao · M
- **Vấn đề:**
  - Tên/SĐT người gửi và nhận, tên văn phòng/tuyến và `err.message` được chèn thẳng vào `innerHTML` (`app.js:45-52, 176-212, 862-893, 1246-1297`, ...).
  - Nhân viên có thể nhập tên người gửi là `<img src=x onerror=...>`, và nhân viên văn phòng khác mở danh sách là bị chạy script. Token đang nằm trong `localStorage` nên có thể bị lấy.
- **Cách sửa:**
  - Thêm `escapeHtml(s)` vào `api-client.js` và bọc **mọi** giá trị động trong template.
  - `showToast` dựng DOM và gán bằng `textContent`.
  - Các `onclick="...('${d.ma_van_don}')"` chuyển sang `data-*` + `addEventListener`, hoặc ít nhất escape.
  - **BE:** schema giới hạn `max_length=100` cho tên và strip ký tự điều khiển (xem S3.4).
- **Nghiệm thu:** tạo đơn có tên `<b>x</b><img src=x onerror=alert(1)>` thì chỉ hiển thị nguyên văn, không chạy script.

#### S1.6 Cờ "đã thông báo người nhận" bị bật rồi tắt (10.3.1 điểm 2–3) · Trung bình · S
- **Vấn đề:** `gui_hang_service.py:336-337` set `da_thong_bao_nguoi_nhan = (ket_qua == "da_lien_he")`. Một lần gọi lại thất bại sẽ **xóa** dấu đã báo được, làm sai nhánh UC-25 (gọi người nhận hay người gửi).
- **Cách sửa:**
  - Repo đổi thành `danh_dau_da_thong_bao_nguoi_nhan(id)` với `SET da_thong_bao_nguoi_nhan = true` (cờ chỉ đi lên).
  - Service chỉ gọi khi `doi_tuong=="nguoi_nhan" and ket_qua=="da_lien_he"`.
- **Nghiệm thu:** ghi "đã liên hệ" rồi "không liên hệ được" thì cờ vẫn là `true`.

---

### Đợt 2 — Thiếu / sai nghiệp vụ

#### S2.1 Biên nhận thiếu thông tin liên hệ điểm nhận; ghi sai cho đơn COD (10.3.1 điểm 1) · Trung bình · S
- **Vấn đề:**
  - Biên nhận chỉ có tên điểm nhận.
  - Đơn COD vẫn in "TỔNG CƯỚC THU", như thể người gửi đã thu.
  - Biên nhận hứa "tra cứu trên website" nhưng chưa có trang tra cứu.
- **Cách sửa:**
  - **BE:** thêm `dn.dia_chi AS dia_chi_diem_nhan` (và `dg.dia_chi AS dia_chi_diem_gui`) vào `SELECT_DON_HANG_FULL` và `DonHangResponse`.
  - **FE:**
    - Thêm dòng "Nơi nhận hàng: tên – địa chỉ" và câu "Vui lòng báo mã vận đơn cho người nhận".
    - COD hiển thị "Cước người nhận trả khi lấy: X đ / Đã thu: 0 đ".
    - Bỏ câu "tra cứu trên website" cho tới khi có trang tra cứu (xem P3).
  - SĐT văn phòng chưa có trong DB, xem mục 2 (Phối hợp).
- **Nghiệm thu:** biên nhận in ra có mã vận đơn, tên và địa chỉ văn phòng nhận, và đúng câu chữ theo phương thức thanh toán.

#### S2.2 Chọn điểm nhận theo 2 tầng khu vực → văn phòng; bỏ tự chọn sẵn (10.4.1 bước 3–4, UC-23 bước 2–3) · Trung bình · M
- **Vấn đề:** FE hiện danh sách văn phòng phẳng, **tự chọn sẵn** văn phòng nhận và tuyến đầu tiên (`app.js:138-147, 184-194, 300-305`). Khi lỗi thì fallback ra **toàn bộ tuyến** (`309-314`), kể cả tuyến không đi qua 2 điểm. Dễ gửi nhầm.
- **Cách sửa:**
  - **BE:** `GET /gui-hang/diem-nhan-kha-dung` (cần đăng nhập) trả `[{khu_vuc_id, ten_khu_vuc, van_phong:[{id, ten, dia_chi}]}]`. Chỉ gồm văn phòng ≠ mình và có ít nhất 1 tuyến chung với văn phòng gửi.
  - **FE:**
    - Form có 3 ô: Khu vực đến → Văn phòng nhận (disabled tới khi chọn khu vực) → Tuyến (từ `/tuyen-phu-hop`).
    - Mặc định để trống, **không** tự chọn.
    - 1 tuyến thì tự điền. Nhiều tuyến thì bắt chọn (đúng "nhân viên chọn 1"). 0 tuyến thì báo lỗi, từ chối nhận (rẽ nhánh UC-23 bước 3).
    - Xóa fallback sang toàn bộ tuyến.
- **Nghiệm thu:** mở form, không có ô nào được chọn sẵn. Chọn khu vực chỉ hiện văn phòng của khu vực đó có tuyến nối tới.

#### S2.3 Hàng cấm: hiển thị và chặn đúng như UC-23 bước 5 · Thấp · S
- **Vấn đề:** dropdown ẩn hẳn hàng cấm, nên nhân viên không thấy bước "chặn, từ chối nhận".
- **Cách sửa:**
  - Hiện đủ danh mục, hàng cấm để trong `<optgroup label="Hàng cấm – không nhận">`.
  - Khi chọn hàng cấm: hiện cảnh báo đỏ "Mặt hàng X thuộc danh mục cấm, từ chối tiếp nhận" và disable nút Tạo đơn.
  - Giữ chặn ở BE (`service:65-66`).

#### S2.4 Bước "báo giá cho khách xác nhận" trước khi tạo đơn (10.4.1 bước 6, UC-23 bước 6) · Thấp · S
- **Cách sửa (FE):** bấm "Tạo đơn" thì mở modal xác nhận tóm tắt (người gửi/nhận, văn phòng nhận, loại hàng, kg, **cước**, phương thức thanh toán, đã thu hay chưa). Chỉ gửi `POST /tao-don` sau khi bấm "Khách đồng ý".

#### S2.5 Quyền `quan_ly` lệch ma trận UC · Trung bình · S
- **Vấn đề:** UC-23/24/25 chỉ dành cho nhân viên gửi hàng, nhưng `quan_ly` đang tạo đơn và giao hàng được ở **bất kỳ** văn phòng nào (`gui_hang.py:27-29`). UC-25 còn cần quản lý **xem** được hàng tồn để thanh lý.
- **Cách sửa:**
  - `QuyenThaoTacQuay = yeu_cau_vai_tro("nhan_vien_gui_hang")` cho `tao-don`, `tuyen-phu-hop`, `giao-hang` và `lien-he-lai`.
  - `QuyenXemGuiHang = ("nhan_vien_gui_hang", "quan_ly", "quan_ly_nhan_su")` cho `thong-ke*` (UC-39), `hang-cho-lau`, `noi-bo/tra-cuu`, `tra-cuu-sdt` và `don-gan-day`.
  - **FE:** với `quan_ly` thì ẩn tab Tạo đơn và các nút Giao/Liên hệ, chỉ cho xem.
  - Nút "Đổi quầy" chỉ render cho `quan_ly`. Đồng thời sửa lỗi nút hiện lại cho nhân viên sau mỗi lần chuyển tab (`nav.js:110-137`).
- **Nghiệm thu:** token quản lý gọi `POST /tao-don` thì nhận 403. Quản lý vẫn xem được hàng tồn và thống kê toàn hệ thống.

#### S2.6 UC-25: thay `prompt()` bằng modal, ràng buộc tổ hợp, gợi ý liên hệ đúng nghiệp vụ · Trung bình · M
- **Vấn đề:**
  - `lienHeLai` dùng `prompt()` đánh số, mặc định "1". Ai cũng chọn được "Báo quản lý" trên mọi đơn.
  - Tổ hợp vô lý (`quan_ly` + `da_lien_he`) vẫn được nhận.
  - UI gợi ý "Gọi người gửi" ngay cho đơn **vừa tới** mà chưa gọi người nhận (`app.js:1242-1253`), trái 10.3.1.
- **Cách sửa:**
  - **BE:**
    - Thêm `model_validator` trong `CapNhatLienHeRequest`. Chỉ chấp nhận `{nguoi_nhan, nguoi_gui} × {da_lien_he, khong_lien_he_duoc}` và `(quan_ly, da_bao_quan_ly)`.
    - "Báo quản lý" chỉ cho khi đơn có cờ 7 ngày hoặc đang `qua_han_luu_kho`.
    - Gửi thông báo chỉ cho quản lý đang hoạt động (`dang_hoat_dong = true`).
    - Ghi lịch sử, cờ và thông báo trong **1 transaction**.
  - **FE:**
    - Modal "Xử lý liên hệ": chọn đối tượng/kết quả bằng radio, có ô ghi chú (hướng xử lý đã thỏa thuận: chờ thêm, nhờ lấy hộ, hoàn về, ...).
    - Gợi ý theo trạng thái:
      - (a) `cho_lay`, chưa báo được: "Gọi NGƯỜI NHẬN" (`tel:` link).
      - (b) Đã báo được, chưa đủ 7 ngày: "Chờ người nhận tới lấy".
      - (c) Cờ 7 ngày + đã báo được: "Gọi lại người nhận".
      - (d) Cờ 7 ngày + chưa từng báo được: "Chuyển sang gọi NGƯỜI GỬI".
      - (e) Hàng tồn: liên hệ người gửi, không liên hệ được ai thì "Báo quản lý".
- **Nghiệm thu:** đơn mới tới chỉ gợi ý gọi người nhận. Nút "Báo quản lý" chỉ bật ở trường hợp (e). Gửi tổ hợp sai thì nhận 422.

#### S2.7 Đọc thông báo UC-46 / UC-25 / UC-28 · Trung bình · M
- **Vấn đề:** job và service đã ghi vào `thong_bao`, nhưng **không có API hay UI để đọc**. Nhân viên không biết đơn nào vừa đủ 7 ngày, quản lý không biết có yêu cầu thanh lý.
- **Cách sửa:**
  - **BE:**
    - `thong_bao_repository.danh_sach_cua_toi(nguoi_nhan_id, chi_chua_doc, limit)`, `dem_chua_doc` và `danh_dau_da_doc(id, nguoi_nhan_id)`. WHERE luôn có `nguoi_nhan_id` lấy từ token để chống IDOR. Kiểm tra cột `da_doc` theo `DATABASE.md` 6.1, thiếu thì thêm migration.
    - Route chung `routes/thong_bao.py`: `GET /thong-bao/cua-toi`, `PUT /thong-bao/{id}/da-doc`, dùng `yeu_cau_dang_nhap`. Báo nhóm vì đây là route dùng chung.
  - **FE:** chuông thông báo ở topbar (`nav.js`) có badge số chưa đọc. Bấm vào một thông báo thì mở đơn tương ứng.
- **Nghiệm thu:** chạy job với đơn `cho_lay` 8 ngày thì nhân viên văn phòng nhận thấy badge, bấm vào mở đúng đơn.

#### S2.8 UC-28: báo cáo thất lạc/hư hỏng phải tới nhân viên gửi hàng và quản lý · Trung bình · S
- **Vấn đề:** `bao_that_lac` chỉ lưu báo cáo. UC-28 bước 2 yêu cầu "thông tin chuyển tới nhân viên gửi hàng/quản lý". Lúc giao hàng, nhân viên không biết đơn có sự cố.
- **Cách sửa:**
  - **BE:** sau khi lưu báo cáo, tạo thông báo cho nhân viên gửi hàng tại `diem_gui_id` (nếu đơn chưa lên xe) hoặc `diem_nhan_id` (nếu đã lên xe), và cho quản lý đang hoạt động.
  - Thêm `so_bao_cao_su_co` (subquery count) vào `SELECT_DON_HANG_FULL`.
  - Bỏ 1 trong 2 hàm repo trùng (`don_hang_repository.luu_bao_cao_su_co_hang` và `bao_cao_su_co_hang_repository`).
  - **FE:** modal giao hàng hiện cảnh báo "Đơn có N báo cáo sự cố" để nhân viên kiểm hàng cùng người nhận.

#### S2.9 Modal giao hàng: bỏ tự tick, chặn đúng trạng thái · Thấp · S
- **Cách sửa:**
  - Xóa `app.js:1030-1031` (`chk.checked = true`), để nhân viên tự tick "đã kiểm hàng".
  - `traCuuDonHang` phân nhánh theo trạng thái:
    - `cho_van_chuyen` / `da_len_xe`: "Hàng chưa tới điểm nhận".
    - `da_giao`: "Đã giao lúc ..., không giao lại".
    - Đơn thuộc văn phòng khác: báo rõ.
    - Không mở "Biên nhận gửi hàng" như hiện nay (10.4.2 bước 3).
  - Phiếu xuất kho in lại dùng `don.ngay_giao`, không dùng thời gian hiện tại (`app.js:594`).

#### S2.10 UC-39 thống kê: khoảng thời gian + mẫu số đúng · Trung bình · M
- **Vấn đề:**
  - Không chọn được khoảng thời gian (UC-39 bước 1).
  - `so_don_canh_bao_7_ngay` đếm cả đơn đã giao.
  - Tỷ lệ % lấy tử số là đơn **nhận đến** nhưng chia cho tổng đơn **gửi đi**.
  - Thống kê theo ngày tính bằng UTC.
  - Rê chuột ra khỏi cột biểu đồ gọi lại `taiThongKe()`, làm spam 2 API (`app.js:1517`).
- **Cách sửa:**
  - **BE:**
    - Thêm `tu_ngay`/`den_ngay` (mặc định 30 ngày gần nhất, kiểm tra `tu ≤ den`).
    - Chỉ số luồng (đơn tạo, đã giao, tiền thu) lọc theo `ngay_tao` / `ngay_giao` / `thoi_gian_thu`. Chỉ số tồn (`cho_lay`, tồn kho) lấy theo hiện tại.
    - Cảnh báo chỉ đếm khi `co_canh_bao_cho_lau AND trang_thai='cho_lay'`.
    - Chia ngày theo `AT TIME ZONE 'Asia/Ho_Chi_Minh'`.
  - **FE:**
    - Tách 2 khối "Hàng gửi đi" và "Hàng nhận về", mỗi khối có mẫu số riêng.
    - Bỏ KPI "khảo sát hài lòng" (không có dữ liệu).
    - Xóa lệnh gọi API trong `anTooltipBieuDo`.

#### S2.11 Thống nhất quy tắc giao đơn `qua_han_luu_kho` · Thấp · S (tài liệu)
- Code cho giao cả `qua_han_luu_kho`. Điều này hợp lý, vì UC-25 có nhánh "chờ thêm" và hàng không tự hủy.
- Spec 10.4.2 bước 3 lại ghi "chỉ `cho_lay`". Đề xuất sửa tài liệu (10.3, 10.4.2 bước 3, tiền điều kiện UC-24) thành "`cho_lay` hoặc `qua_han_luu_kho` khi người nhận tới lấy theo thỏa thuận UC-25". Khi giao, tắt `co_canh_bao_cho_lau`.
- **Cần nhóm đồng ý**, vì đây là sửa nghiệp vụ.

---

### Đợt 3 — Bảo mật & độ bền

| Mã | Vấn đề | Cách sửa | Công |
|---|---|---|---|
| S3.1 | `/gui-hang/tuyen`, `/van-phong`, `/loai-hang` không cần đăng nhập (`gui_hang.py:50-66`); route gọi thẳng repo | Gắn `QuyenThaoTacQuay`. Sau S2.2, bỏ `/tuyen` và `/van-phong`. Route chỉ gọi service. | S |
| S3.2 | `KhongDuQuyen` trả **401** nên FE tưởng là token hết hạn (`main.py:53-55`) | Đổi thành 403. **Báo nhóm** vì phụ xe cũng dùng. Kết hợp S1.4. | S |
| S3.3 | Mã vận đơn 6 hex trùng thì `UniqueViolation` thành 500; ngày trong mã theo giờ server | `datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))`. Repo bắt `UniqueViolation` rồi rollback; service sinh lại mã, tối đa 3 lần. | S |
| S3.4 | Validate thiếu: tên chỉ có khoảng trắng; không có cận trên nên tràn NUMERIC gây 500; `trang_thai` lọc tự do | `StringConstraints(strip_whitespace=True, min_length=1, max_length=100)`. `le=` cho kg, cm, cước. `trang_thai: Literal[...]`. | S |
| S3.5 | Job UC-46 không atomic (bật cờ xong mới tạo thông báo; lỗi giữa chừng thì mất thông báo vĩnh viễn); nội dung luôn "liên hệ người nhận" kể cả khi chưa từng báo được; mốc 14 ngày không có nhắc | CTE `UPDATE ... RETURNING` + `INSERT thong_bao` trong 1 transaction. Nội dung theo `da_thong_bao_nguoi_nhan` (gọi người nhận hay người gửi). Mốc 14 ngày cũng gửi thông báo cho nhân viên. | M |
| S3.6 | Double-submit: đổi loại hàng bật lại nút Tạo đơn khi request đang chạy; tra cứu tuyến không bỏ response cũ | Cờ `dangTaoDon`; bỏ bật nút trong `xuLyThayDoiLoaiHang`; dùng biến đếm phiên bản cho `xuLyThayDoiDiemNhan`. | S |
| S3.7 | Danh sách lấy `limit=50` rồi lọc/đếm phía client nên chip đếm và tìm kiếm sai khi nhiều dữ liệu | BE thêm `offset` + `COUNT(*) OVER()`, trả `{items, total}` (hoặc header `X-Total-Count`). FE gửi `tu_khoa`, `trang_thai`, `limit`, `offset` lên server. | M |
| S3.8 | Tra cứu công khai trả 400 khi không tìm thấy, alias thừa (`/don-hang/{ma}`, `/diem-nhan/{id}/cho-lay`, `PUT /{id}/lien-he`) | Thêm lỗi `KhongTimThay` dẫn tới 404. Xóa các alias không dùng (grep trước khi xóa). | S |
| S3.9 | Khởi tạo trang gọi trùng API; đăng xuất không xóa `van_phong_truc_id`, `nhan_vien_gui_hang_active_tab` | `khoiTaoTrang` async: nạp danh mục xong mới `chuyenTab`, chỉ tải dữ liệu tab đang mở. Đăng xuất xóa hết key. | S |

---

### Đợt 4 — CI, tài liệu, chất lượng

| Mã | Việc | Công |
|---|---|---|
| S4.1 | `app/db.py` tạo pool lúc import nên mọi unit test cần Postgres thật và CI dễ fail. Đổi sang **khởi tạo pool lười** (`_pool=None`, tạo trong `get_connection`). Báo nhóm. | S |
| S4.2 | `DATABASE.md` 5.2: đoạn văn chèn giữa bảng `don_hang` làm vỡ markdown. Chuyển xuống dưới, thêm mục cho `lich_su_lien_he_don_hang` và `ho_so_can_bo_diem`. | S |
| S4.3 | **Mâu thuẫn cần nhóm chốt:** NGHIEP_VU 10.3.1 ghi "chỉ lưu 1 cờ, không đếm cuộc gọi", nhưng bạn đã thêm bảng `lich_su_lien_he_don_hang`. Đề xuất giữ bảng (UC-25 cần ghi hướng xử lý đã thỏa thuận và người xử lý) và cập nhật NGHIEP_VU/DATABASE.md cho khớp. | S |
| S4.4 | Ghi rõ trong mô tả PR: migration `20261002_0900` sửa bảng dùng chung (`tim_theo_id` của xác thực JOIN `ho_so_can_bo_diem`, thêm cột `thong_bao.don_hang_id`). Mọi người phải `yoyo apply` ngay sau khi pull. Thêm hướng dẫn/seed gán văn phòng cho tài khoản test. | S |
| S4.5 | Bổ sung test: phạm vi văn phòng (`_pham_vi_van_phong`), `huong` của `/don-gan-day`, validator liên hệ, retry mã vận đơn, job atomic. | M |

---

## 2. Cần phối hợp với thành viên khác (ngoài phạm vi role)

> Trạng thái mới nhất của P1–P6 (21/10/2026): xem mục 7.4 phần D — P4 và P6 đã xong.

| # | Việc | Ai | Ghi chú |
|---|---|---|---|
| P1 | Tạo tài khoản `nhan_vien_gui_hang` **kèm** `van_phong_id` (UC-36), cho cả `quan_ly_nhan_su` gán | Người làm tài khoản cán bộ (Nghĩa) | ✅ Phần tạo đã xong (#38, 23/10): UC-36 tự ghi `ho_so_can_bo_diem` cùng transaction, không gọi `gan_van_phong_can_bo`. Còn "đổi văn phòng" chưa code — xem mục 7.6. |
| P2 | CRUD danh mục `loai_hang` / hàng cấm (mục 8.7 điểm 1, 10.5) | Người làm quản lý | Hiện chỉ có seed cứng. Không cho xóa loại đã có đơn tham chiếu. |
| P3 | Trang công khai tra cứu mã vận đơn | Người làm FE khách hàng (hoặc bạn tự làm) | BE `/gui-hang/tra-cuu/{ma}` đã có. Nên thêm rate-limit. |
| P4 | Trang đăng nhập cán bộ thiếu điều hướng `phu_xe` (bản `9a6fb60` có `phu_xe: "phu-xe/chuyen-cua-toi.html"`, nay đã mất) | tuanhdung | Bạn đang sửa `dang-nhap.html` nên có thể thêm luôn 1 dòng và báo họ. |
| P5 | Sửa tuyến (xóa và chèn lại `tuyen_diem_don_tra`) khi còn đơn chưa giao làm đơn mất khỏi danh sách chờ xếp hoặc bị đổi chiều | Người làm UC-31 | Chặn sửa nếu có đơn `cho_van_chuyen`/`da_len_xe` mà điểm gửi/nhận bị bỏ khỏi tuyến hoặc đảo thứ tự. Bạn cung cấp hàm `dem_don_dang_xu_ly_theo_tuyen`. |
| P6 | Cột SĐT cho văn phòng (`diem_don_tra.so_dien_thoai`) để in lên biên nhận | Người làm UC-30 + cả nhóm | Spec 10.3.1 nói "thông tin liên hệ điểm nhận". Tối thiểu dùng địa chỉ (S2.1). |

---

## 3. Phương án nâng cấp

Chấm điểm: Giá trị và Phù hợp BTL, cao là tốt. Công và Rủi ro, thấp là tốt. Thang 1–5.
Mọi phương án đã được lọc để **không mâu thuẫn nguyên tắc nghiệp vụ**: không tự tính cước, không SMS/email cho người gửi/nhận, không tự hủy hàng, không chống quá tải khoang hàng bằng số kg.

| # | Phương án | Giá trị | Công | Rủi ro | Phù hợp BTL |
|---|---|---|---|---|---|
| N1 | Màn "Hàng đến" 3 cột: Sắp đến → Chờ gọi báo → Đã báo/chờ lấy | 5 | 3 | 1 | 5 |
| N2 | Ô quét mã vận đơn (máy quét USB/ô nhập focus sẵn) + mã vạch Code128 trên nhãn | 4 | 2 | 1 | 5 |
| N3 | In khổ nhiệt (biên nhận 80mm, nhãn 100×75mm), "In 2 bản" một lần bấm theo 10.4.1 bước 8 | 4 | 2 | 1 | 4 |
| N4 | Đối soát tiền mặt theo nhân viên/ca: tổng cước trả trước + COD đã thu theo `nhan_vien_thu_id`, `thoi_gian_thu` | 4 | 2 | 1 | 4 |
| N5 | Lịch sử trạng thái đơn (`lich_su_trang_thai_don_hang`: ai, khi nào, từ → tới) + timeline trong chi tiết đơn | 4 | 3 | 2 | 4 |
| N6 | Thông báo realtime qua WebSocket (đã có `websocket_manager`) khi hàng vừa dỡ tại điểm mình hoặc khi đủ 7 ngày | 4 | 3 | 2 | 4 |
| N7 | Idempotency khi tạo đơn: `khoa_tao_don` UUID từ FE, cột UNIQUE | 3 | 2 | 1 | 3 |
| N8 | Tách `app.js` (1656 dòng) thành module theo tab (`tao-don.js`, `giao-hang.js`, `hang-ton.js`, `thong-ke.js`, `utils.js`) | 3 | 3 | 2 | 4 |
| N9 | Phím tắt quầy (F2 tạo đơn, F3 tra cứu, Enter xác nhận), focus tự động, gợi ý người gửi quen theo SĐT | 3 | 2 | 1 | 3 |
| N10 | Xuất báo cáo thống kê ra CSV | 2 | 1 | 1 | 3 |
| N11 | Đặt hẹn gửi hàng online | 3 | 5 | 4 | 1 |
| N12 | Gợi ý/tính cước tự động theo bảng giá | — | — | — | **Loại**: trái mục 10.1 ("không có công thức hay bảng giá nào ràng buộc/gợi ý") |
| N13 | SMS/Zalo tự động báo người nhận | — | — | — | **Loại**: trái mục 10.3.1 (không có kênh tự động) |

### Nên làm ngay (quick win)

**N1 — Màn "Hàng đến" cho văn phòng nhận.** Gộp với S1.1 và S2.6.
- **BE:**
  - `GET /gui-hang/hang-sap-den`: lấy đơn `da_len_xe AND diem_nhan_id = mình`. JOIN `chuyen_xe` + `xe` để lấy biển số và giờ khởi hành. ETA lấy từ `lich_su_diem_dung_chuyen` và `tuyen_diem_don_tra.thoi_gian_du_kien_phut` nếu có.
  - `/hang-cho-lau` thêm `chua_thong_bao=true`, sắp `da_thong_bao_nguoi_nhan ASC, thoi_gian_den_diem_nhan`.
- **FE:** tab "Hàng đến" có 3 cột.
  - "Sắp đến": chỉ xem.
  - "Chờ gọi báo": nút `tel:` + "Đã báo được" / "Chưa liên lạc được".
  - "Chờ lấy": nút Giao hàng, kèm badge 7 ngày / tồn kho.
  - Đúng thứ tự công việc ở 10.4.2 bước 1.

**N2 + N3 — Quét mã và in chuẩn.**
- **FE:**
  - Ô "Quét/nhập mã vận đơn" luôn có focus ở tab Hàng đến. Máy quét USB gõ như bàn phím + Enter, nên dùng lại `traCuuDonHang`.
  - Vẽ Code128 bằng JsBarcode (cdnjs) trên nhãn và biên nhận.
  - CSS `@page` theo khổ, nút "In nhãn + biên nhận".
- **BE:** không cần thay đổi.

**N4 — Đối soát tiền theo ca.**
- **BE:** `GET /gui-hang/doi-soat?tu=...&den=...` trả tổng `gia_cuoc` theo `nhan_vien_thu_id` trong khoảng `thoi_gian_thu`, tách trả trước và COD, kèm danh sách đơn.
- **FE:** thẻ "Tiền mặt tôi đã thu hôm nay" ở tab Thống kê, có nút In.
- Dữ liệu đã đủ (cột `da_thu_tien`, `thoi_gian_thu`, `nhan_vien_thu_id` từ migration `20261002`).

### Nên làm nếu còn thời gian
- **N5 — Lịch sử trạng thái.** Migration bảng `lich_su_trang_thai_don_hang(id, don_hang_id, tu, den, nguoi_thuc_hien_id, thoi_diem)`. Ghi trong cùng transaction ở mọi UPDATE trạng thái (tạo, chất, dỡ, giao, job). FE hiện timeline trong modal chi tiết. Giúp truy vết khi khách khiếu nại hoặc thất lạc.
- **N6 — WebSocket.** Dùng `broadcast_sync` hiện có: lúc dỡ hàng gửi cho nhân viên văn phòng nhận; lúc job 7/14 ngày gửi cho nhân viên điểm đó. FE cập nhật badge chuông (S2.7).
- **N7, N8, N9.**

### Để sau / không khuyến nghị
- **N10:** CSV giá trị thấp cho BTL.
- **N11:** đặt hẹn online. Spec cho phép mở sau nhưng công sức lớn, không ưu tiên.
- **N12, N13:** trái nghiệp vụ.

---

## 4. Lộ trình đề xuất (thứ tự commit/PR)

1. **PR-0 `fix/gui-hang-hoi-quy-phu-xe`**: S0.1, S0.2, S0.3. Mời tuanhdung review.
2. **PR-1 `fix/gui-hang-luong-giao-hang`**: S1.1, S1.2, S1.6, S2.9, phần BE của S2.5.
3. **PR-2 `fix/gui-hang-fe-an-toan`**: S1.3, S1.4, S1.5, S3.6, S3.9, phần FE của S2.5 (nút Đổi quầy).
4. **PR-3 `feat/gui-hang-du-nghiep-vu`**: S2.1, S2.2, S2.3, S2.4, S2.6, S2.8.
5. **PR-4 `feat/thong-bao-dung-chung`**: S2.7 + S3.5 (báo nhóm vì là route dùng chung).
6. **PR-5 `fix/gui-hang-thong-ke-ben-vung`**: S2.10, S3.1–S3.4, S3.7, S3.8.
7. **PR-6 `docs+ci`**: S4.x, S2.11 (sau khi nhóm chốt).
8. **Nâng cấp**: N1 (ghép vào PR-3 nếu kịp) → N2/N3 → N4 → N5/N6.

Song song: gửi danh sách mục 2 (P1–P6) cho các thành viên liên quan.

---

## 5. Phụ lục — đã kiểm tra, **không** phải lỗi

- **Index DB cho `don_hang`:** 3 index `DATABASE.md` yêu cầu đã có đủ ở migration `20260920_1600:139-146`. Thêm index khác là tối ưu tùy chọn.
- **Kiểu `Decimal` trong response:** chỉ ảnh hưởng hiển thị ("5.00 kg"), không sai nghiệp vụ. Muốn đẹp thì đổi sang `float` (tùy chọn).
- **"Việc cần làm hôm nay", "chốt ca", in biên nhận từ BE:** là nâng cấp, không phải lỗi. Riêng đối soát ca đã đưa vào N4.
- **Kiểm tra cùng chiều khi chất hàng** (`chieu_van_chuyen` so với `chuyen.chieu`) và **chặn điểm gửi/nhận phải là `van_phong`, khác nhau, cùng tuyến:** đã đúng.
- **Ràng buộc COD/trả trước khi tạo và giao** (`xac_nhan_da_thu`) và **UPDATE giao hàng có điều kiện trạng thái:** đã đúng.
- **Job UC-46 không tự hủy hàng, mốc 7/14 ngày tính từ `thoi_gian_den_diem_nhan`:** đúng nghiệp vụ. Chỉ cần sửa phần atomic/nội dung ở S3.5.

---

## 6. Đợt B — Hủy đơn gửi hàng (nhánh `feature/Trinh-huy-don`)

> Căn cứ: `NGHIEP_VU.md` chưa có luồng hủy đơn hàng — vòng đời 10.3 không có nhánh hủy, `don_hang.trang_thai` (`DATABASE.md` 5.2) chưa có `da_huy`. Câu duy nhất nhắc tới là `DATABASE.md` 5.2c: "sửa tuyến/điểm nhận/loại hàng/cước thì phải hủy đơn rồi tạo lại".
> Nguyên tắc: hủy = **trả lại kiện hàng cho người gửi tại quầy**, nên chỉ hủy khi hàng còn trong kho văn phòng gửi. Không đụng tới job 7/14 ngày ("không tự hủy" vẫn giữ nguyên).

### 6.1. Cần nhóm chốt trước khi code

| # | Nội dung | Đề xuất |
|---|---|---|
| B1 | Trạng thái được hủy | Chỉ `cho_van_chuyen` **và** `chuyen_id IS NULL` |
| B2 | Đơn `da_len_xe` / `cho_lay` / `qua_han_luu_kho` | Không hủy. Người gửi muốn lấy lại thì xử lý theo UC-25 |
| B3 | Giới hạn thời gian hủy | Không, chỉ ràng buộc theo trạng thái |
| B4 | Ai được hủy | Nhân viên gửi hàng **của văn phòng gửi** (không bắt buộc là người tạo đơn). Văn phòng nhận và `quan_ly` không hủy được |
| B5 | Quản lý duyệt | Không cần. Ghi người hủy, quản lý xem được |
| B6 | Xác minh người gửi | Người gửi có mặt, đưa biên nhận / đọc mã vận đơn. Mất biên nhận thì tra SĐT người gửi + xác minh tên |
| B7 | Lý do hủy | Bắt buộc: khách đổi ý / nhập sai thông tin, tạo lại / hàng không đủ điều kiện / khác (bắt buộc ghi chú) |
| B8 | Phí hủy | Không thu |
| B9 | Hoàn tiền | Trả trước + đã thu → hoàn 100% tiền mặt tại quầy ngay lúc hủy. COD hoặc chưa thu → hủy thẳng |
| B10 | Qua kế toán (`lich_su_hoan_tien`)? | Không — tiền mặt trả ngay tại quầy, khác luồng hoàn vé. **Người làm kế toán xác nhận** |
| B11 | Hủy để tạo lại | Hoàn đơn cũ, thu đơn mới riêng, không bù trừ chênh lệch |
| B12 | Thống kê / đối soát | Đơn hủy không tính doanh thu, khoản hoàn ghi riêng. **Người làm UC-39 xác nhận** |
| B13 | Ảnh hưởng phụ xe (UC-26) | Không phải sửa — danh sách chờ chất đã lọc `cho_van_chuyen`. **tuanhdung xác nhận** |
| B14 | Số UC mới | UC-54 "Hủy đơn gửi hàng" — kiểm tra chưa ai dùng số này |

Gộp chốt luôn 4 điểm code đã làm nhưng `NGHIEP_VU.md` chưa ghi: bảng lịch sử liên hệ (S4.3), giao đơn `qua_han_luu_kho` (S2.11), sửa tên/SĐT người gửi-nhận, đối soát tiền thu theo nhân viên (N4).

### 6.2. Sửa tài liệu (sau khi chốt)

| Mã | File / mục | Nội dung |
|---|---|---|
| D1 | `NGHIEP_VU.md` 8.5 | Thêm điểm 4 "Hủy đơn tại điểm gửi", trỏ tới 10.4.3 / UC-54 |
| D2 | `NGHIEP_VU.md` 10.3 | Thêm nhánh `cho_van_chuyen → da_huy` vào sơ đồ; ghi rõ sau `da_len_xe` không hủy được |
| D3 | `NGHIEP_VU.md` 10.4.3 (mới) | "Khi người gửi muốn hủy đơn": xác minh → kiểm tra trạng thái/văn phòng → chọn lý do → hoàn tiền nếu đã thu → `da_huy`, gỡ nhãn, thu biên nhận, trả hàng → tạo đơn mới nếu do nhập sai |
| D4 | `NGHIEP_VU.md` 11 | Thêm dòng UC-54 vào ma trận, chỉ `nhan_vien_gui_hang` |
| D5 | `NGHIEP_VU.md` 12 | Đặc tả UC-54: actor, tiền điều kiện, luồng chính, rẽ nhánh (đã lên xe / phụ xe vừa chất / đã thu tiền / COD), hậu điều kiện |
| D6 | `NGHIEP_VU.md` 10.3.1, UC-25 | Đổi "không tự hủy" thành "job **không tự động** hủy" cho khỏi lẫn với hủy thủ công |
| D7 | `DATABASE.md` 5.2 | Thêm `da_huy` vào CHECK; cột `ly_do_huy`, `ghi_chu_huy`, `nhan_vien_huy_id`, `thoi_gian_huy`, `so_tien_hoan`; ghi chú thống kê bỏ đơn hủy |
| D8 | `NGHIEP_VU.md` / `DATABASE.md` | Cập nhật 4 điểm ở cuối 6.1 nếu nhóm đồng ý |

### 6.3. Code

**BE** · M
- Migration mới `2026100x_xxxx_huy_don_hang.sql`: sửa CHECK `trang_thai`, thêm các cột ở D7. Không sửa migration cũ.
- Repo `huy_don(id, nhan_vien_id, ly_do, ghi_chu, so_tien_hoan)`: `set_config('app.nguoi_dung_id')` rồi `UPDATE ... WHERE id=%s AND trang_thai='cho_van_chuyen' AND chuyen_id IS NULL RETURNING id` (cùng kiểu S0.1 — chống tranh chấp với phụ xe chất hàng). 0 dòng → service báo "Đơn đã thay đổi, không thể hủy". Trigger `trg_lich_su_trang_thai_don` tự ghi lịch sử.
- Service: kiểm tra `diem_gui_id` = văn phòng nhân viên (`KhongDuQuyen`), tính `so_tien_hoan` = `gia_cuoc` nếu `nguoi_gui_tra_truoc AND da_thu_tien`, ngược lại `NULL`.
- Route `POST /gui-hang/{id}/huy` với `QuyenThaoTacQuay`; schema `HuyDonRequest` (`ly_do: Literal[...]`, `ghi_chu` bắt buộc khi `ly_do = 'khac'`, tối đa 200 ký tự).
- Thống kê / đối soát (N4): loại `da_huy` khỏi doanh thu, thêm dòng "Đã hoàn" theo `nhan_vien_huy_id`.
- Không cho sửa tên/SĐT đơn `da_huy` (5.2c).

**FE** · M
- Nút "Hủy đơn" trong chi tiết đơn, chỉ hiện khi `cho_van_chuyen`, chưa gắn chuyến, và `diem_gui_id === vanPhongTrucId`.
- Modal: chọn lý do, ghi chú, hiện rõ "Hoàn cho khách: X đ" hoặc "Không hoàn (COD/chưa thu)", nhắc gỡ nhãn + thu biên nhận.
- In phiếu hoàn tiền khi có hoàn.
- Danh sách "Đơn gửi đi": chip lọc "Đã hủy"; tra cứu hiện "Đã hủy" + lý do + thời điểm.
- Lý do "nhập sai thông tin": sau khi hủy mở form tạo đơn điền sẵn thông tin cũ (tùy chọn).

**Test** · S
- Hủy đúng trạng thái thành công; `da_len_xe` → lỗi; văn phòng khác → `KhongDuQuyen`; UPDATE 0 dòng → lỗi; `so_tien_hoan` đúng cho 3 trường hợp (trả trước đã thu / chưa thu / COD); `ly_do='khac'` thiếu ghi chú → 422.

### 6.4. Thứ tự

1. Gửi bảng 6.1 cho nhóm, chờ chốt.
2. Kiểm tra nhánh tạo từ đúng base `integration/gop-nhanh-thanh-vien`, kéo code mới nhất.
3. Sửa tài liệu (6.2) → code BE + test → FE (6.3).
4. PR vào base, mời người làm thống kê và tuanhdung review. Ghi trong mô tả PR: có migration mới, mọi người `yoyo apply` sau khi pull.

### 6.5. Đã làm (07/10/2026)

- Đã merge base mới nhất (`integration/gop-nhanh-thanh-vien`, gồm #27, #28) vào nhánh trước khi code.
- **Migration** `20261011_0900_huy_don_hang.sql` (ban đầu đặt `20261007_1400`, đổi tên 11/10 vì base đã có `20261008_*`): thêm `da_huy` vào CHECK, 5 cột hủy/hoàn, CHECK `don_hang_thong_tin_huy_day_du`, index đối soát hoàn.
- **BE:**
  - `POST /gui-hang/don-hang/{id}/huy` (chỉ `nhan_vien_gui_hang`), schema `HuyDonRequest`.
  - Repo `huy_don`: UPDATE có điều kiện `cho_van_chuyen` + `chuyen_id IS NULL` + đúng văn phòng gửi; `so_tien_hoan` tính trong SQL.
  - Chặn sửa tên/SĐT (cả kiểm tra sau khóa dòng, `DonDaHuy`) và chặn giao hàng với đơn `da_huy`.
  - Thống kê: thêm `so_don_huy`, `tien_da_hoan`; `tong_doanh_thu` trừ tiền hoàn. Đối soát: thêm `so_don_hoan`, `tien_hoan` theo `nhan_vien_huy_id`; `tong_tien` = thu − hoàn; thêm `tong_tien_hoan`.
- **FE:**
  - File mới `huy-don.js`: modal hủy (chọn lý do, ghi chú, số tiền hoàn, tích xác nhận đã trả hàng), phiếu hủy/hoàn tiền in được, nút "Tạo lại đơn" điền sẵn người gửi/nhận + hàng khi lý do là nhập sai.
  - Nút 🗑️ ở tab Đơn gửi đi và nút "Hủy đơn" trong chi tiết đơn (chỉ hiện khi hủy được); bộ lọc "Đã hủy"; badge "Đã hủy"; chi tiết đơn hiện lý do/người hủy/tiền hoàn; CSV thêm cột lý do hủy và tiền hoàn.
  - Thống kê: KPI "Hủy trong kỳ", chip "Đã hoàn khi hủy đơn"; bảng đối soát thêm cột "Hoàn".
- **Kiểm thử:**
  - `pytest tests/unit`: 322 test qua (thêm test hủy đơn, schema `HuyDonRequest`, đối soát có hoàn).
  - Chạy thật trên Postgres local: migration OK; gọi API thật — hủy đơn trả trước (hoàn đúng `gia_cuoc`), hủy COD (không hoàn), hủy lần 2 → 400, văn phòng khác → 403, quản lý → 403, lý do `khac` thiếu ghi chú → 422, sửa/giao đơn đã hủy bị chặn, lịch sử trạng thái ghi đúng người hủy, thống kê/đối soát trừ đúng tiền hoàn. Đã trả dữ liệu test về như cũ.
  - **Chưa** test giao diện trên trình duyệt.
- **Lưu ý khi đọc thống kê:** tiền thu và tiền hoàn ghi theo ngày của từng khoản, nên ngày chỉ có hoàn (thu từ hôm trước) thì doanh thu ngày đó có thể âm — đúng với tiền mặt thực tế trong két.

### 6.6. Việc tiếp theo (09/10/2026)

Code hủy đơn đang nằm ở working tree, chưa commit. Base `integration/gop-nhanh-thanh-vien` đã có thêm #29, #30 (đụng `DATABASE.md`, `NGHIEP_VU.md`, `thong_bao_repository.py` — không đụng code gửi hàng) và migration `20261008_*`.

| # | Việc | Ghi chú |
|---|---|---|
| T1 | **Test giao diện trên trình duyệt** | Nút 🗑️ chỉ hiện ở đơn chờ xếp xe của văn phòng mình; modal hủy (lý do, ghi chú bắt buộc khi "Khác", tích đã trả hàng); phiếu hoàn in đúng 1 trang; "Tạo lại đơn" điền sẵn; lọc/badge "Đã hủy"; chi tiết đơn đã hủy; thống kê + đối soát; tài khoản quản lý không thấy nút hủy |
| T2 | ✅ (11/10) **Đồng bộ base** — đã kéo #29, #30 (không conflict), đổi tên migration thành `20261011_0900_huy_don_hang.sql`; trên code đã gộp: unit 426/426, E2E 148/148, `yoyo apply` OK | Commit tạm → merge `origin/integration/gop-nhanh-thanh-vien` → **đổi tên migration** `20261007_1400_huy_don_hang.sql` thành `20261009_xxxx_huy_don_hang.sql` (base đã có `20261008_*`, giữ thứ tự thời gian; migration viết idempotent nên máy đã chạy bản cũ chạy lại không lỗi) → `pytest tests/unit` → `yoyo apply` |
| T3 | **Gửi nhóm chốt** | Bảng 6.1 (B1–B14) + 4 điểm tài liệu chưa ghi + 2 lưu ý cho kế toán: đối soát két = thu − hoàn; doanh thu ngày có thể âm |
| T4 | **Sau khi nhóm chốt** | ✅ (09/10) Nhóm chốt B1–B14 đúng như đề xuất → code giữ nguyên. **Không sửa `NGHIEP_VU.md`**: nội dung D1–D6 ghi vào file gộp `NGHIEP_VU_GUI_HANG.md` (UC-54, mục 5.4, 8.7); 4 điểm D8 cũng đã ghi ở đó với ký hiệu ⏳ (mục 9.2). D8 (4 điểm tài liệu chưa ghi) vẫn chờ nhóm |
| T5 | **Mở PR** vào `integration/gop-nhanh-thanh-vien` | Reviewer: người làm thống kê (UC-39), người làm kế toán, tuanhdung. Mô tả PR ghi rõ có migration mới, cần `yoyo apply` sau khi pull |
| T6 | **Sau PR hủy đơn** | Chốt ca (tổng thu − hoàn theo ca, mở rộng N4); đẩy các việc phối hợp P1–P6 (mục 2); tài liệu S2.11, S4.3; hàng đợi khi mất mạng — đề xuất bỏ (công lớn, giá trị thấp cho BTL) |

### 6.7. Kết quả test toàn bộ role (09/10/2026)

**Unit test** (`pytest tests/unit`): 322/322 qua; riêng gửi hàng 101 test.

**E2E gọi API thật trên Postgres local: 147/147 PASS.** Script tự tạo dữ liệu tạm (nhân viên gửi hàng tạm ở Mỹ Đình, nhân viên quầy vé, tài khoản chưa gán văn phòng, tài khoản bị khóa, quản lý nhân sự, phụ xe) và đã dọn sạch — số đơn theo trạng thái trong DB giữ nguyên như trước khi chạy. Các nhóm đã test:

| Nhóm | Nội dung chính (gồm cả ngoại lệ) |
|---|---|
| A. Quyền | Không token / token sai 401; quầy vé, chưa gán văn phòng, tài khoản khóa 403; quản lý chỉ xem, không tạo/giao/hủy/sửa; quản lý nhân sự chỉ thống kê; xem văn phòng khác 403 |
| B. Danh mục | Loại hàng kèm cờ cấm; điểm nhận khả dụng; tìm tuyến (đúng chiều), không có tuyến → rỗng |
| C. Tạo đơn | Trả trước / COD; hàng cấm; trùng điểm; khai điểm gửi văn phòng khác; tuyến/điểm/loại hàng không tồn tại; xác nhận thu sai; 11 lỗi dữ liệu 422 (SĐT, tên, cước, cân nặng, kích thước...); cắt khoảng trắng; tên chứa HTML; chống tạo trùng (Idempotency-Key); gợi ý khách quen |
| D. Tra cứu | Nội bộ (mã viết thường), công khai không lộ tên/SĐT, mã sai 404, theo SĐT, danh sách gửi/nhận + lọc + phân trang, tham số sai 422, lịch sử trạng thái |
| E. Sửa tên/SĐT | 2 văn phòng sửa được, thông báo văn phòng còn lại, nhật ký không ghi trùng, dữ liệu sai 422, quản lý 403, đơn đã giao/đã hủy bị chặn |
| F. Hủy đơn (UC-54) | Hoàn đúng cước / COD không hoàn; 5 lỗi lý do-ghi chú 422; quản lý và văn phòng nhận 403; đã lên xe / đã giao / đã hủy bị chặn; đơn hủy không sửa/giao/liên hệ được; lịch sử ghi người hủy; lọc "Đã hủy"; biến khỏi danh sách chờ chất; CHECK DB chặn da_huy thiếu thông tin |
| G. Sự cố (UC-28) | Báo sự cố → văn phòng gửi nhận thông báo; mô tả rỗng 400; xem báo cáo; đếm số báo cáo |
| H. Giao hàng (UC-24) | Chưa tới / đang trên xe chặn; hàng đến đúng văn phòng; tra SĐT khi quên mã; văn phòng gửi giao 403; mã sai 404 / rỗng 422; COD chưa xác nhận thu 400; giao COD và trả trước; giao lần 2 chặn |
| I. Liên hệ (UC-25) | Chưa tới chặn; văn phòng gửi 403; cờ "đã báo" một chiều; 3 tổ hợp sai 422; báo quản lý trước 7 ngày 400; lịch sử liên hệ |
| J. Job 7/14 ngày | 8 ngày → cờ cảnh báo, nội dung nhắc đúng theo cờ "đã báo"; 15 ngày → hàng tồn (không xóa); 3 ngày không đổi; chạy lại không gửi trùng; báo quản lý sau mốc 7 ngày; quản lý xem hàng tồn; giao hàng tồn |
| K. Thống kê | Số đơn tiếp nhận, hủy trong kỳ, tiền hoàn, doanh thu = trả trước + COD − hoàn, COD đã thu, đã giao; đối soát thu − hoàn từng nhân viên; khoảng ngày sai 400; quản lý toàn hệ thống |
| L. Thông báo | Nhân viên đọc được thông báo trên chuông |

**Giới hạn của lần test này:**
- Chất/dỡ hàng của phụ xe (UC-26/27) được **giả lập bằng SQL** (DB không có chuyến + phụ xe có biên chế); phần đó đã có unit test riêng của role phụ xe.
- DB chỉ có 2 văn phòng nên không test được "văn phòng thứ 3 không liên quan xem đơn" bằng API — đã có unit test.
- Tranh chấp "phụ xe chất hàng đúng lúc nhân viên bấm hủy" chỉ test bằng unit test (UPDATE có điều kiện).
- **Giao diện chưa test trên trình duyệt** (T1).

**Phát hiện nhỏ — ✅ đã sửa (09/10/2026):** đơn đã quá 14 ngày mà trước đó chưa có cờ 7 ngày (ví dụ job ngừng chạy vài ngày) nhận **2 thông báo cùng lúc** — "chờ 7 ngày" và "hàng tồn". Đã sửa `don_hang_repository.quet_canh_bao_7_ngay`: mốc 7 ngày bỏ qua đơn đã đủ 14 ngày (`thoi_gian_den_diem_nhan > now() - INTERVAL '14 days'`); đơn đó vẫn được bật cờ cảnh báo vì câu chuyển hàng tồn cũng set `co_canh_bao_cho_lau = true`. Thêm ca E2E "đơn quá 14 ngày chỉ nhận đúng 1 thông báo". Chạy lại: **E2E 148/148 PASS**, unit test 322/322.

---

## 7. Đợt C — Việc còn lại: chốt ca + hàng đợi khi mất mạng (12/10/2026)

> Nhánh `feature/Trinh-chot-ca` — **chưa commit**. Đợt B (hủy đơn) đã vào base qua PR #31.
>
> **13/10/2026:** ban đầu làm chung nhánh với phần kế toán (`feature/Trinh-hoan-thien-ke-toan`). Người 5 **không làm kế toán nữa** nên đã tách ra: phần kế toán (hoàn tiền UC-22, job 3 tiếng, tra cứu cho quầy vé, thống kê hoàn tiền, giao diện `/nhan-vien/ke-toan/`, migration `20261011_1000_lien_he_hoan_tien`, `KE_HOACH_KE_TOAN.md`, `NGHIEP_VU_KE_TOAN.md`) được cất ở nhánh local `feature/Trinh-ke-toan-luu` (commit `aa33fdf`, không push, không merge) để người nhận phần kế toán dùng lại nếu cần. Nhánh này chỉ còn chốt ca. Chốt ca không phụ thuộc gì vào phần kế toán. Chạy lại sau khi tách: unit **439/439**, E2E gửi hàng **148/148**, E2E chốt ca **31/31**; DB local đã gỡ bảng `lich_su_lien_he_hoan_tien` và bản ghi yoyo của migration `20261011_1000`.
>
> **21/10/2026:** đã commit chốt ca (`7311d20`) rồi gộp base mới (#33 phụ xe, #34 sửa quản lý, #35 hệ số loại xe) vào nhánh. Conflict duy nhất ở cuối `don_hang_schema.py`: giữ cả dòng `loai` của `BaoThatLacRequest` (#33) lẫn khối schema chốt ca. Sau khi `yoyo apply` 6 migration mới: unit **706/710** — 4 ca fail có sẵn trên base, không do chốt ca (2 test gửi hàng của #33 thiếu mock `dem_bao_cao_theo_loai` nên gọi DB thật; 2 test no-show fail vì #33 bỏ mất thông báo "không đến" cho khách trong `quet_no_show.py` — cần báo tuanhdung); E2E gửi hàng **148/148** (script thêm xe + biên chế phụ xe tạm vì #33 bắt buộc phụ xe có chuyến cùng tuyến mới được báo sự cố đơn chưa lên xe); E2E chốt ca **31/31**.
>
> **21/10/2026 — font chữ:** giao diện gửi hàng dùng chung font với trang khách hàng — `style.css` bỏ font hệ thống ở `body.nhan-vien-shell` và nhãn dán hàng, dùng `var(--font-body)` (Lexend) của `shared/design-tokens.css`; tiêu đề `h1–h6` tự nhận `--font-heading` (Be Vietnam Pro) từ file đó. Giữ monospace cho mã vận đơn / mã vạch / số trên phiếu.
>
> **21/10/2026 — thiết kế lại CSS + responsive đầy đủ:** viết lại `frontend/nhan-vien/gui-hang/style.css` từ đầu (bản cũ chồng nhiều lớp vá: 2 mục cùng số, "khôi phục style bị mất", nhiều khối `@media 880px` ghi đè nhau). **Chỉ đổi CSS, không sửa HTML/JS.** Dùng token chung của `shared/design-tokens.css` + vài token cục bộ `--gh-*` (viền, nền phụ, khoảng cách, chiều cao ô nhập 44px).
> - 4 mốc màn hình: ≥1280 thanh bên đầy đủ, bảng dạng cột; 900–1279 thanh bên thu gọn (icon + nhãn nhỏ); <900 điều hướng chuyển xuống **đáy màn hình**; <640 điện thoại (modal trượt từ dưới lên, nút giãn đều dễ bấm).
> - Bảng Hàng đến / Đơn gửi đi / Hàng chờ lâu ≤1279px chuyển thành **thẻ có nhãn từng ô** — trước đây ở 1024px bị mất cột Việc cần làm + Thao tác (không thấy nút Giao), điện thoại chỉ còn 2 cột. Bảng chốt ca ≤1279 và đối soát <640 cũng thành thẻ.
> - Sửa: thanh trên tràn ngang ở 1024px; biểu đồ tràn ở điện thoại; ô quét mã; tiêu đề lặp ở tab Tiếp nhận (ẩn bằng CSS); KPI hàng nhận về lưới không kín; cột phải form Tiếp nhận dính khi cuộn (nút "Báo giá & Tạo đơn" luôn trong tầm); hàng nút modal luôn ở đáy khi nội dung dài.
> - In ấn: vùng in bám đầu trang giấy, bỏ các trang trắng phía sau (bản cũ cũng in thừa trang trắng).
> - Kiểm tra bằng Playwright: 5 tab × 13 khổ (360–1920px) không tràn ngang, không bảng nào bị che, không lỗi JS; chụp modal giao hàng, chốt ca, bản in biên nhận / nhãn dán / phiếu chốt ca.
> - **Biểu đồ sản lượng (sửa `thong-ke.js`):** bản cũ vẽ SVG cố định 650×250 rồi kéo giãn (`preserveAspectRatio="none"`) — khung rộng thì chữ bè ngang, cột lùn; trục dọc làm tròn bước 1,25 nên mất số (0, 1, 3, 4, 5); ngày 0 đơn vẫn vẽ vạch 1px. Nay vẽ theo đúng chiều rộng khung (`ResizeObserver` vẽ lại khi đổi cỡ), bước trục là số tròn 1/2/5/10…, bỏ cột 0, ghi số trên đầu cột, nhãn ngày giãn cách ≥ 48px, cả kỳ không có đơn thì hiện chú thích. Thêm: số tiền 3 ô tiền mặt thẳng hàng; đầu thẻ thống kê không còn bóp dòng mô tả.
>
> **21/10/2026 — rà soát cảnh báo / thông báo của role, làm 3 mục trong phạm vi role** (A1, B, C chờ nhóm — xem dưới):
> - **A2 — Hàng trên chuyến có vấn đề:** `SELECT_DON_HANG_FULL` lấy thêm `trang_thai_chuyen`, `chuyen_dang_hoan`, `loai_su_co_chuyen`, `ly_do_su_co_chuyen` (thêm vào `DonHangResponse`, không có trong response tra cứu công khai). Màn "Hàng đến": đơn *Sắp đến* trên chuyến gặp sự cố / đang hoãn / bị hủy có nhãn cảnh báo + lý do, việc cần làm "Hàng sẽ tới trễ", vạch đỏ, xếp sau hàng tồn và trước hàng đang trên xe bình thường.
> - **D — Nhắc lại sau 24 giờ:** migration `20261021_0900_nhac_goi_bao_24h.sql` (cột `don_hang.da_nhac_goi_bao`); `don_hang_repository.quet_nhac_goi_bao_24h` + gắn vào job `quet_hang_ton` (mỗi giờ): đơn `cho_lay` ≥ 24 giờ, chưa báo được người nhận, chưa cờ 7 ngày → nhắc văn phòng nhận 1 lần, kèm tên + SĐT người nhận. Màn "Hàng đến" đổi việc cần làm thành "Gọi lại người nhận".
> - **E — Cảnh báo rời trang:** form Tiếp nhận đang nhập dở mà tải lại / đóng tab / đăng xuất → trình duyệt hỏi lại; tạo đơn xong (form reset) hoặc bị buộc đăng xuất vì hết phiên thì không hỏi.
> - Kiểm thử: unit 707/711 (thêm test lời nhắc 24 giờ; 4 ca fail có sẵn của #33); kiểm thử API thật D 9/9 (đúng 1 trong 4 tình huống được nhắc, chạy lần 2 không nhắc trùng), A2 5/5 (kể cả tra cứu công khai không lộ lý do sự cố); giao diện 10/10 (nhãn, thứ tự, cảnh báo rời trang); E2E gửi hàng 148/148, chốt ca 31/31.
> - **Xác nhận đăng xuất:** bấm "Đăng xuất" mở hộp xác nhận (`modalDangXuat`, cùng kiểu modal của trang — điện thoại trượt từ dưới lên), con trỏ đặt sẵn ở "Ở lại", Esc đóng; có đơn đang nhập dở ở tab Tiếp nhận thì hộp cảnh báo sẽ mất thông tin. Xác nhận thì thoát luôn, không để trình duyệt hỏi "rời trang?" thêm lần nữa. Kiểm thử giao diện 18/18 (1280px + 390px).
> - **Chờ nhóm:** A1 — tự gửi thông báo cho văn phòng nhận khi chuyến chở hàng báo sự cố (gọi từ `chuyen_xe_service.bao_su_co`, code của tuanhdung); B — hàng đã lên xe khi chuyến bị hủy (UC-19, người 4) xử lý thế nào; C — nhắc văn phòng gửi khi đơn chờ xếp xe quá lâu (mốc nghiệp vụ mới).
>
> **21/10/2026 — rà soát toàn bộ code role, sửa 6 lỗi tìm được:**
> - **Hộp xác nhận đăng xuất không đóng được khi trang khởi tạo lỗi** (`/auth/me` lỗi mạng, hoặc tài khoản chưa gán văn phòng): lúc đó `ganSuKien` / `khoiTaoPhimTat` không chạy nên "Ở lại" và Esc không có tác dụng. `nav.js` (`renderTopbar`) tự gắn sự kiện đóng cho "Ở lại" và Esc của chính hộp này.
> - **Dỡ lại hàng không reset cờ nhắc:** `cap_nhat_do_hang_tai_diem` nay đặt `da_nhac_goi_bao = false`, `co_canh_bao_cho_lau = false` cùng lúc đặt lại `thoi_gian_den_diem_nhan`. Trước đây phụ xe hoàn tác dỡ hàng ở điểm cuối của chuyến `hoan_thanh` (vẫn làm được sau nhiều ngày) rồi dỡ lại thì đơn không được nhắc 24 giờ nữa, có thể hiện ngay nhãn "quá 7 ngày".
> - **Ghi liên hệ cho đơn vừa được giao:** `don_hang_repository.ghi_lien_he` khóa dòng đơn (`FOR UPDATE`) và kiểm tra lại trạng thái trong cùng transaction; không còn `cho_lay` / `qua_han_luu_kho` thì ném `DonKhongConChoLay`, service trả 400 "vừa được giao… vui lòng tải lại", không ghi lịch sử, không báo quản lý.
> - **Tìm kiếm "Đơn gửi đi":** `%` và `_` người dùng gõ được coi là chữ thường (hàm `mau_tim_ilike`); trước đây gõ `%` ra mọi đơn.
> - **Hàng đến chạm giới hạn 500 đơn:** BE đặt tên hằng `SO_HANG_DEN_TOI_DA`; FE (`GIOI_HAN_HANG_DEN`) hiện ghi chú "Chỉ hiện 500 đơn đầu tiên… số đếm và nhóm Sắp đến có thể thiếu" (quản lý xem toàn hệ thống thì gợi ý chọn 1 văn phòng) thay vì đếm thiếu mà không báo.
> - Dọn import trùng trong `gui_hang_service.py` (sót lại từ lần gộp base); thêm mock `dem_bao_cao_theo_loai` cho 2 test `danh_sach_cho_chat/cho_do` (trước gọi DB thật nên fail).
> - Kiểm thử: unit **711/713** (thêm 2 test: đơn vừa giao khi ghi liên hệ, `mau_tim_ilike`; 2 ca fail còn lại là test no-show của #33, ngoài role); chạy thử SQL trên DB local (rollback): `%`/`_` khớp đúng chữ, UPDATE dỡ hàng + `FOR UPDATE` hợp lệ; E2E gửi hàng **148/148**, chốt ca **31/31**; giao diện 15/15 (đăng xuất khi `/auth/me` lỗi và khi chưa gán văn phòng: "Ở lại", Esc, xác nhận; ghi chú 500 đơn hiện/ẩn đúng) + hồi quy đăng xuất 18/18.
>
> **21/10/2026 — xử lý góp ý rà soát nghiệp vụ (nhóm "làm ngay")** — các điểm còn lại của góp ý (kết thúc xử lý hàng tồn, mô hình tiền trong két khi ca chỉ có hoàn, quy trình xử lý sự cố, chống tạo trùng khi tải lại trang) chưa làm, chờ quyết định:
> - **Đổi SĐT người nhận:** BE bắt buộc `ly_do` khi SĐT người nhận thật sự đổi (400 nếu thiếu); `don_hang_repository.sua_thong_tin_lien_he` hạ `da_thong_bao_nguoi_nhan` và `da_nhac_goi_bao` về `false` trong cùng UPDATE — đơn quay về "Cần gọi báo", job nhắc 24 giờ chạy lại theo cờ mới, lịch sử liên hệ giữ nguyên. Văn phòng gửi đổi số khi hàng đã tới văn phòng nhận → thông báo cho văn phòng nhận thêm câu "gọi báo lại người nhận theo số mới …". Sửa tên thì không cần lý do, giữ cờ. FE (`sua-don.js`): chặn lưu khi đổi SĐT người nhận mà trống lý do, nhãn ô lý do ghi rõ bắt buộc, toast nhắc gọi số mới.
> - **Chốt ca ở 2 cửa sổ:** `ChotCaRequest` thêm `tu_luc` bắt buộc (null = lần chốt đầu; thiếu hẳn → 422); `chot_ca_service.chot_ca` và `chot_ca_repository.tao_chot_ca` (trong khóa advisory) so `tu_luc` gửi lên với mốc lần chốt cuối, khác thì từ chối "Đã có lần chốt ca khác sau khi bạn mở màn này… tải lại" — trước đây cửa sổ thứ 2 vẫn lưu được ca với khoảng khác hẳn số nhân viên đã đếm. `chot-ca.js` gửi lại `tu_luc` của màn xem trước.
> - **Giới hạn 500 đơn hàng đến:** thứ tự cắt ở BE đổi thành hàng tồn → chờ quá 7 ngày → chờ lấy → sắp đến (trước đây chờ lấy đứng trước nên văn phòng > 500 đơn chờ lấy sẽ mất cả hàng tồn ở tab Hàng chờ lâu và CSV). Câu ghi chú trên giao diện sửa theo đúng thứ tự này.
> - **Nhãn "COD":** giao diện ghi "Người nhận trả cước (COD)" ở form tiếp nhận (kèm "nhà xe không thu hộ tiền hàng"), "Người nhận trả" trên huy hiệu, "Thu cước khi giao" ở chốt ca / đối soát / CSV, "THU CƯỚC CỦA NGƯỜI NHẬN TRƯỚC KHI GIAO" ở modal giao hàng, biên nhận, nhãn dán, phiếu bàn giao. Giá trị lưu trong DB (`cod_nguoi_nhan_tra`) không đổi.
> - Kiểm thử: unit **718/720** (thêm 7 test: đổi SĐT thiếu lý do, gõ lại SĐT cũ, nội dung thông báo theo văn phòng sửa, chốt ca khi cửa sổ khác vừa chốt / đúng mốc, schema thiếu `tu_luc`; 2 ca fail còn lại là no-show của #33); E2E gửi hàng **151/151** (thêm: đổi SĐT không lý do → 400, đổi SĐT hạ 2 cờ, sửa tên giữ cờ), chốt ca **33/33** (thêm: cửa sổ thứ 2 → 400, thiếu `tu_luc` → 422); giao diện 25/25 + hồi quy đăng xuất 18/18.

> **22/10/2026 — tạm bỏ chốt ca tiền mặt** (người 5 chưa cần): toàn bộ chốt ca được cất ở nhánh local **`feature/Trinh-chot-ca-luu`** (commit `ccaf2e0`, không push, không merge — cùng cách cất phần kế toán), rồi gỡ khỏi nhánh này:
> - Xóa `chot_ca_service.py`, `chot_ca_repository.py`, `test_chot_ca_service.py`, migration `20261012_0900_chot_ca_gui_hang.sql`, `frontend/nhan-vien/gui-hang/chot-ca.js`.
> - Gỡ 4 route `/gui-hang/chot-ca*` (`routes/gui_hang.py`), khối schema chốt ca (`don_hang_schema.py` mục 7), thẻ chốt ca ở tab Thống kê + 2 modal (chốt ca, phiếu chốt ca) + thẻ `<script>` (`index.html`), lời gọi `khoiTaoChotCa` / `taiLichSuChotCa` (`khoi-tao.js`, `thong-ke.js`), CSS chốt ca (`style.css`).
> - Tài liệu: bỏ việc thứ 7 + mục 6.1 + 2 dòng bảng 9.2 ở `NGHIEP_VU_GUI_HANG.md`, mục 5.2d ở `DATABASE.md`.
> - **Giữ nguyên** đối soát tiền theo nhân viên (`/gui-hang/doi-soat`) — tính năng riêng, không phụ thuộc chốt ca. Sửa luôn nhãn "COD" còn sót ở bảng đối soát trên điện thoại.
> - **DB local:** bảng `chot_ca_gui_hang` và bản ghi yoyo của migration `20261012_0900` vẫn còn (không xóa để khỏi mất dữ liệu); code không dùng tới nên vô hại. Muốn dọn: `DROP TABLE chot_ca_gui_hang;` + xóa dòng `20261012_0900_chot_ca_gui_hang` trong bảng `_yoyo_migration`. Migration này chưa từng vào base nên máy thành viên khác không có.
> - Lấy lại sau này: `git checkout feature/Trinh-chot-ca-luu -- <các file trên>` hoặc cherry-pick, rồi gộp lại phần sửa route / schema / `index.html`.
> - Kiểm thử sau khi gỡ: xem mục 7.4 phần A.

### 7.1. Quyết định

| Việc | Quyết định |
|---|---|
| Hàng đợi khi mất mạng | **Bỏ** — đơn tạo lúc mất mạng chưa có mã vận đơn nên không in được biên nhận / nhãn cho khách, vẫn phải chờ có mạng; lợi ích thấp, dễ sinh lỗi |
| Chốt ca | ⏸ **Tạm bỏ 22/10/2026** (cất ở `feature/Trinh-chot-ca-luu`). Trước đó chọn **Cách A**: chốt theo từng nhân viên **từ lần chốt trước**, nhập số tiền đếm thực tế, lưu chênh lệch + ghi chú, in phiếu, quản lý xem lịch sử. (Cách B — in tổng trong ngày, không lưu — bị loại vì gộp lẫn ca và không phát hiện được thiếu tiền) |

### 7.2. ✅ Chốt ca tiền mặt

**DB** — migration `20261012_0900_chot_ca_gui_hang.sql`, bảng `chot_ca_gui_hang` (DATABASE.md mục 5.2d). CHECK bảo đảm `phải có = trả trước + COD − hoàn`, `chênh lệch = đếm được − phải có`, lệch thì phải có ghi chú; UNIQUE `(nhan_vien_id, den_luc)`.

**BE** — `repositories/chot_ca_repository.py`, `services/chot_ca_service.py`, route trong `routes/gui_hang.py`:

| Method | Đường dẫn | Quyền | Việc |
|---|---|---|---|
| GET | `/gui-hang/chot-ca/xem-truoc` | nhan_vien_gui_hang | Từ lần chốt trước tới bây giờ: thu trả trước, thu COD, hoàn (số khoản + tiền), phải có, từng khoản; trả mốc `den_luc` |
| POST | `/gui-hang/chot-ca` | nhan_vien_gui_hang | `{tu_luc, den_luc, tien_thuc_dem, ghi_chu}` — chốt đúng khoảng đã xem (`tu_luc` thêm 21/10: khác mốc lần chốt cuối → 400, thiếu → 422); mốc tương lai / quá 2 tiếng / không múi giờ / không sau lần chốt trước → 400; lệch không ghi chú → 400; khóa theo nhân viên nên bấm 2 lần chỉ lưu 1 |
| GET | `/gui-hang/chot-ca` | nhan_vien_gui_hang, quan_ly | Lịch sử (nhân viên: chỉ của mình; quản lý: tất cả, lọc văn phòng), lọc khoảng ngày, chỉ ca lệch, phân trang |
| GET | `/gui-hang/chot-ca/{id}` | nhan_vien_gui_hang (của mình), quan_ly | Chi tiết + từng khoản để in lại phiếu |

Quy tắc tiền giống đối soát: thu theo `nhan_vien_thu_id` + `thoi_gian_thu`, hoàn theo `nhan_vien_huy_id` + `thoi_gian_huy`. Tiền phát sinh sau mốc xem trước tự sang ca sau.

**FE** — file mới `chot-ca.js`; tab "Thống kê & Đối soát" thêm khối **Chốt ca tiền mặt**: nút "Chốt ca" (ẩn với quản lý), lịch sử theo khoảng ngày đang chọn + "chỉ ca bị lệch" + phân trang + in lại phiếu; modal chốt ca (tổng, từng khoản, ô nhập số đếm nhận cả "140.000", chênh lệch tính ngay, ghi chú bắt buộc khi lệch, hộp xác nhận); **phiếu chốt ca** in được, có chỗ ký người nộp / người nhận.

**Kiểm thử:**
- Unit: `tests/unit/test_chot_ca_service.py` 13 test — toàn bộ **439/439** (sau khi tách phần kế toán ra, 13/10/2026).
- E2E API thật (`e2e_chot_ca.py`, nhân viên + đơn tạm, đã dọn): **31/31 PASS** — quyền (không token, quản lý không chốt hộ, chưa gán văn phòng); ca 1: thu trả trước + hoàn khi hủy, COD tính cho người thu khi giao (văn phòng nhận), lệch không ghi chú 400, số âm 422, chốt lệch có ghi chú, **đơn tạo sau mốc xem trước không lọt vào ca**, bấm 2 lần cùng mốc 400; ca 2 nối tiếp đúng mốc, khớp tiền không cần ghi chú, sau khi chốt phải có 0; 4 mốc sai; lịch sử (nhân viên chỉ thấy của mình, quản lý lọc văn phòng + chỉ ca lệch), chi tiết (403 với người khác, 404); 3 ràng buộc CHECK của DB.
- Giao diện (Playwright, dữ liệu tạm đã xóa): **17/17 PASS** — nút chỉ hiện với nhân viên, số tiền xem trước, từng khoản, chênh lệch tính ngay + ghi chú thành bắt buộc, chặn lệch không ghi chú, phiếu chốt ca đủ thông tin + chữ ký, lịch sử tô đỏ ca lệch, mở lại ngay sau chốt → 0, in lại phiếu, lọc ca lệch, quản lý chỉ xem, không lỗi JavaScript. Đã xem ảnh chụp modal và phiếu.
- Chạy lại toàn bộ sau khi thêm: E2E gửi hàng 148/148 — không ảnh hưởng.

**Tài liệu:** `NGHIEP_VU_GUI_HANG.md` thêm việc thứ 7 của nhân viên + mục 6.1 (⏳ chờ nhóm xác nhận, đã thêm vào bảng 9.2); `DATABASE.md` mục 5.2d.

### 7.3. Trạng thái role gửi hàng sau đợt C

Đã xong toàn bộ việc trong kế hoạch của role (12/10/2026). Sau rà soát + góp ý nghiệp vụ ngày 21/10/2026 còn một số việc mới — xem **mục 7.4**.

### 7.4. Việc còn lại (cập nhật 21/10/2026)

Ký hiệu: 🟢 tự làm được ngay · 🟡 cần bạn quyết trước · 🔵 cần chốt với nhóm / thành viên khác. Công: S ≈ dưới 2 giờ, M ≈ nửa ngày, L ≈ 1 ngày trở lên.

#### A. Việc phải làm trên nhánh hiện tại

| # | Việc | Công | Chi tiết |
|---|---|---|---|
| A1 ✅ | **Commit + mở PR** nhánh `feature/Trinh-chot-ca` — **xong 23/10: PR #37 đã squash-merge vào integration** | S | Working tree đang chưa commit: nhắc 24 giờ (migration `20261021_0900`), hàng trên chuyến có vấn đề, cảnh báo rời trang, xác nhận đăng xuất, CSS mới, biểu đồ, 6 sửa lỗi rà soát, nhóm "làm ngay" (đổi SĐT, chốt ca 2 cửa sổ, giới hạn 500, nhãn COD). Gợi ý tách 3 commit: (1) cảnh báo/thông báo + migration, (2) giao diện (CSS, biểu đồ, đăng xuất, nhãn), (3) sửa lỗi + góp ý. PR vào `integration/gop-nhanh-thanh-vien`, squash-merge. Trong mô tả PR ghi rõ: **thành viên khác phải `yoyo apply`** migration `20261021_0900`; **API đổi**: `PUT …/thong-tin-lien-he` bắt buộc `ly_do` khi đổi SĐT người nhận (chốt ca đã tạm bỏ 22/10 nên không còn trong PR). Chạy lại trước khi đẩy: unit, E2E gửi hàng, E2E chốt ca (bản script đã cập nhật nằm ở scratchpad phiên 21/10, bản cũ không còn đúng). |
| A2 🔵 | Báo **tuanhdung**: 2 test no-show fail | S | `tests/unit/test_thong_bao_khach.py::test_job_khong_den_*` — #33 bỏ mất thông báo "không đến" cho khách trong `quet_no_show.py`. Không thuộc role, nhưng làm CI đỏ. **23/10:** thêm 7 test vé lẻ/VNPay fail sau #39 (`test_ve_le.py` ×6, `test_thong_bao_khach.py::test_ipn_ve_le_thanh_cong_bao_khach`) — #39 thêm kiểm tra `ma_tham_chieu_vnpay` trong `_ap_dung_ket_qua_ve` nhưng vé giả trong test chưa có trường này → báo người làm quầy vé (#39). Tin nhắn mẫu: mục 7.7. |
| A3 🟢 | Kiểm thử **đồng thời** trên PostgreSQL thật | M | Góp ý nêu: test hiện tại chưa chứng minh các tình huống tranh chấp. Viết 1 script chạy 2 luồng cùng lúc cho: 2 nhân viên cùng giao 1 đơn; hủy đơn đúng lúc phụ xe chất hàng; 2 lần chốt ca cùng lúc; ghi liên hệ đúng lúc giao. Kỳ vọng: mỗi cặp chỉ 1 bên thành công, bên kia nhận 400. Không cần sửa code nếu pass. |

#### B. Trong role, cần bạn quyết trước

> ⏸ **22/10/2026:** chốt ca đã tạm bỏ (cất ở `feature/Trinh-chot-ca-luu`) nên **B1 và B3 hoãn theo** — chỉ cần xem lại khi lấy chốt ca trở lại.

**B1 🟡 — Tiền "phải có" của ca có thể âm (góp ý điểm 4)** · Công S–M

- Hiện tại: phải có = thu trả trước + thu cước khi giao − hoàn, của chính nhân viên đó từ lần chốt trước. Ví dụ A thu 100.000 hôm qua và đã chốt; hôm nay B hủy đơn đó, hoàn 100.000, không thu gì → ca B phải có **−100.000**. DB bắt `tien_thuc_dem >= 0` nên B đếm 0 đ vẫn bị tính "THỪA 100.000" và phải ghi chú.
- Phương án:
  - **(a) Ghi "tiền được cấp để hoàn"** *(khuyên dùng)*: thêm cột `tien_duoc_cap` vào `chot_ca_gui_hang` (migration mới, sửa CHECK `chot_ca_phai_co_dung` thành `phai_co = tra_truoc + cod − hoan + duoc_cap`). Màn chốt ca: khi số phải có âm thì hiện ô "Tiền quản lý/két chung đã cấp để hoàn". Đổi nhãn "Trong két lẽ ra phải có" → "Thu ròng trong ca" khi âm. Sửa: `chot_ca_repository`, `chot_ca_service`, schema, `chot-ca.js`, phiếu in, test + E2E.
  - **(b) Quản lý két đầy đủ**: tiền đầu ca, cấp thêm, nộp/rút, người nhận bàn giao — bảng mới, nhiều màn hình. Đúng thực tế hơn nhưng to so với đồ án.
  - **(c) Chỉ đổi nhãn**: "Thu ròng trong ca", cho phép số âm và giải thích trên phiếu. Ít công nhất nhưng chênh lệch vẫn sai khi ca chỉ có hoàn.

**B2 🟡 — Chống tạo trùng khi tải lại trang (góp ý điểm 6)** · Công S–M

- Hiện tại: khóa chống trùng chỉ nằm trong bộ nhớ (`state.khoaTaoDon`). Server đã tạo đơn nhưng mất phản hồi, nhân viên tải lại trang và nhập lại → khóa mới → đơn thứ 2. Cảnh báo "rời trang?" chỉ giảm bớt, không chặn được.
- Làm: lưu `{khoa, noi_dung, nguoi_dung_id}` vào `sessionStorage` lúc bấm tạo; tạo xong thì xóa. Mở lại trang thấy còn khóa → gửi lại đúng nội dung đó với khóa cũ (BE trả lại đơn đã tạo nếu có) hoặc hỏi nhân viên. Tùy chọn phía BE: lưu băm nội dung kèm khóa, cùng khóa khác nội dung → 409 (cần thêm cột).

**B3 🟡 — Khoản thu commit sau khi chốt ca (góp ý điểm 3, phần còn lại)** · Công S · ưu tiên thấp

- Khoản thu/hoàn dùng `now()` = lúc **bắt đầu** transaction. Nếu transaction bắt đầu trước mốc `den_luc` nhưng commit sau khi ca đã tính tổng thì khoản đó bị sót khỏi cả 2 ca. Chỉ xảy ra khi chính nhân viên đó vừa thu tiền vừa chốt ca trong vài mili-giây.
- Làm nếu muốn chặn hẳn: trong `tao_don_hang` (trả trước), `cap_nhat_giao_hang` (thu khi giao), `huy_don` (hoàn) lấy cùng khóa `pg_advisory_xact_lock(hashtext('chot_ca:' || nhan_vien_id))` với chốt ca.

**B4 🟡 — Phân trang hàng đến phía server (góp ý điểm 5, phần đầy đủ)** · Công M–L · để sau

- Đã giảm rủi ro bằng thứ tự cắt (hàng tồn → quá 7 ngày → chờ lấy → sắp đến) + ghi chú. Làm đầy đủ: API nhận bộ lọc/nhóm/từ khóa/limit/offset, trả `items`, `total` và số đếm từng nhóm tính trên toàn bộ dữ liệu; tab Hàng chờ lâu và CSV dùng API riêng. Chỉ cần nếu có văn phòng thực sự > 500 đơn đang mở.

#### C. Cần chốt với nhóm (đụng phần của thành viên khác)

**C1 🔵 — Bước kết thúc xử lý hàng tồn (góp ý điểm 1, ưu tiên cao)** · Công L

- Hiện tại: không liên hệ được ai thì báo quản lý "xử lý thủ công (thanh lý)" — đơn ở `qua_han_luu_kho` mãi, số tồn kho và việc cần làm sai sau khi đã xử lý ngoài thực tế.
- Cần nhóm trả lời:
  1. Ai bấm "hoàn tất xử lý": quản lý (hiện chỉ xem — phần quản lý là của người khác) hay nhân viên gửi hàng sau khi quản lý duyệt?
  2. Các kết quả: đã trả người gửi tại quầy / gửi trả về bằng xe / đã thanh lý / mất hàng (bồi thường?).
  3. Gửi trả bằng xe có tạo **đơn chiều về** liên kết đơn gốc không, ai trả cước chiều về?
- Phần code khi đã chốt: thêm trạng thái kết thúc (vd `da_xu_ly_ton`) vào CHECK `don_hang.trang_thai` + `TrangThaiDonHang`; cột `ket_qua_xu_ly_ton`, `ghi_chu_xu_ly_ton`, `nguoi_xu_ly_ton_id`, `thoi_gian_xu_ly_ton` (và `don_goc_id` nếu có đơn chiều về); endpoint + nút trên màn Hàng chờ lâu; loại khỏi `lay_hang_den`, cập nhật thống kê tồn kho, tra cứu công khai, timeline trạng thái, trigger lịch sử. Sửa `NGHIEP_VU_GUI_HANG.md` UC-25 (hậu điều kiện).

**C2 🔵 — Quy trình xử lý báo cáo hư hỏng / thất lạc khi giao (góp ý điểm 7)** · Công M

- Hiện tại: modal giao hàng hiện báo cáo của phụ xe để kiểm hàng, nhưng backend giao hàng không xét báo cáo; không có "đã xử lý".
- Đề xuất: bảng `bao_cao_su_co_hang` (phần phụ xe, #33) thêm `trang_thai_xu_ly` (`chua_xu_ly` / `nguoi_nhan_dong_y_nhan` / `da_tim_thay` / `xac_nhan_mat`), `nguoi_xu_ly_id`, `thoi_gian_xu_ly`, `ghi_chu`. Giao đơn có báo **hư hỏng** chưa xử lý → bắt nhân viên ghi "người nhận đồng ý nhận"; có báo **thất lạc** chưa xử lý → chặn giao cho tới khi xác nhận đã tìm thấy. Cần đồng ý của tuanhdung vì đụng bảng của #33.

**C3 🔵 — Tự báo văn phòng nhận khi chuyến chở hàng gặp sự cố** (A1 cũ) · Công S

- Màn Hàng đến đã có nhãn, nhưng không có thông báo chủ động. Bạn viết sẵn hàm `gui_hang_service.thong_bao_hang_tren_chuyen_su_co(chuyen_id, ly_do)` (gom đơn `da_len_xe` của chuyến theo văn phòng nhận, gửi 1 thông báo/nhân viên); tuanhdung gọi nó trong `chuyen_xe_service.bao_su_co`.

**C4 🔵 — Hàng đã lên xe khi chuyến bị hủy** (B cũ, UC-19 của người 4) · Công M

- Đơn `da_len_xe` trên chuyến `da_huy` hiện chỉ có nhãn "Chuyến đã hủy". Cần chốt: hàng được dỡ lại ở đâu, đơn trả về `cho_van_chuyen` (gỡ `chuyen_id`) để chuyến khác chất, ai thao tác, có báo văn phòng gửi/nhận không.

**C5 🔵 — Nhắc văn phòng gửi khi đơn chờ xếp xe quá lâu** (C cũ) · Công S

- Cần nhóm chốt mốc (vd 24 giờ / 48 giờ chưa có chuyến nào chất). Sau đó làm giống nhắc 24 giờ: cột cờ + hàm quét trong job `quet_hang_ton` + nội dung thông báo cho nhân viên văn phòng gửi.

**C6 🔵 — Xác nhận tài liệu** · Công S

- Bảng 9.2 của `NGHIEP_VU_GUI_HANG.md`: 10 điểm code đã làm nhưng `NGHIEP_VU.md` chưa ghi — lịch sử liên hệ, giao hàng tồn, sửa tên/SĐT, đối soát, chốt ca, nhắc 24 giờ, hàng trên chuyến có vấn đề, và 3 điểm thêm ngày 21/10 (đổi SĐT người nhận đưa đơn về "cần gọi báo" + bắt lý do; chốt ca từ chối cửa sổ cũ; COD = người nhận trả cước, không thu hộ). `NGHIEP_VU.md` là file chung → báo người giữ file sửa, **không tự sửa**.

**C7 🔵 — Mô tả kiện / số kiện** (góp ý nhỏ) · Công S–M

- Chưa có quy ước 1 đơn = 1 kiện hay nhiều kiện, chưa có mô tả bề ngoài kiện để đối chiếu khi giao. Nếu nhóm đồng ý: thêm `so_kien` (mặc định 1) + `mo_ta_kien` vào form tiếp nhận, nhãn dán ("Kiện 1/2"), modal giao hàng.

#### D. Phối hợp còn mở từ mục 2

| # | Trạng thái 21/10 | Việc còn lại |
|---|---|---|
| P1 | 🟡 Tạo kèm văn phòng ✅ (UC-36, #38); **đổi văn phòng chưa có** (cập nhật 23/10) | Chờ nhóm chốt 2 quy tắc đổi văn phòng; khi có rồi thì xóa chuỗi `gan_van_phong_can_bo` — mục 7.6. |
| P2 | 🔵 Chưa có | CRUD loại hàng / hàng cấm cho quản lý; không cho xóa loại đã có đơn. |
| P3 | 🔵 BE `/gui-hang/tra-cuu/{ma}` có, **chưa có trang** | Trang tra cứu mã vận đơn cho khách + rate-limit endpoint công khai. |
| P4 | ✅ Đã có (`dang-nhap.html` điều hướng `phu_xe`) | — |
| P5 | 🔵 Chưa có | Chặn sửa tuyến khi còn đơn `cho_van_chuyen` / `da_len_xe` mà điểm gửi/nhận bị bỏ hoặc đảo thứ tự. Bạn viết `dem_don_dang_xu_ly_theo_tuyen` cho người làm UC-31 gọi. |
| P6 | ✅ Đã có (`diem_don_tra.sdt_lien_he`, in lên biên nhận) | — |

#### Thứ tự đề xuất

1. A1 (commit + PR) → A2 (báo tuanhdung) — để code hiện tại vào base sớm.
2. C1, C2, C4, C5, C6, C7 mang ra **1 buổi họp nhóm** (gom câu hỏi ở trên).
3. Trong lúc chờ: B1 (chọn phương án a/b/c), A3 (kiểm thử đồng thời), B2.
4. Sau khi nhóm chốt: C1 → C3 → C2 → C5 → C4.
5. B3, B4: chỉ làm nếu còn thời gian.

### 7.5. Dữ liệu test trên DB local (22/10/2026)

Script `backend/scripts/seed_gui_hang_demo.py` (cùng kiểu `seed_phu_xe_demo.py`, chỉ chạy khi `DATABASE_URL` trỏ DB local):

```
docker compose exec backend python scripts/seed_gui_hang_demo.py
```

- **Hạ tầng** (giữ giữa các lần chạy): thêm VP Yên Bái, VP Sa Pa, điểm dừng Km 140, tuyến "Mỹ Đình -> Sa Pa (qua Yên Bái)" — cặp Mỹ Đình ↔ Lào Cai có 2 tuyến; 4 xe `…888.0x`; 4 tài khoản nhân viên gửi hàng (mỗi văn phòng 1, mật khẩu `GuiHang@123`) + 1 phụ xe `phuxe.guihang@demo.nhaxe.vn` (`PhuXe@123`) gắn xe đang chạy sắp tới Lào Cai.
- **Đơn** (xóa và tạo lại mỗi lần chạy — chỉ đơn do 4 tài khoản demo tạo): đủ tình huống chờ xếp xe, hủy (có/không hoàn), sắp đến (chuyến gặp sự cố / đang hoãn), chờ gọi báo, đã nhắc 24 giờ, cảnh báo 7 ngày (đã/chưa từng báo), hàng tồn (chưa/đã báo quản lý, đã thỏa thuận), báo cáo hư hỏng, sửa SĐT, đã giao hôm nay + ~75 đơn lịch sử 14 ngày cho thống kê. Cờ và thông báo dựng đúng như job UC-46 đã chạy; riêng 1 đơn mốc 24 giờ và 1 đơn mốc 7 ngày để **chờ job** (lần quét kế tiếp sẽ nhắc + đẩy real-time).
- Cuối script in mã vận đơn nổi bật theo từng văn phòng kèm việc nên thử.

### 7.6. Khớp với UC-36 của quản lý nhân sự (23/10/2026)

Sau khi gộp integration #37–#39. Nguồn: `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md`, `UC36_THAY_THE_GAN_VAN_PHONG_VA_DOI_VAN_PHONG.md`, `NGHIEP_VU.md` mục 2 + UC-36.

**Quy tắc mới phía QLNS đã chốt, ảnh hưởng gửi hàng:**
- `nhan_vien_gui_hang` bắt buộc chọn văn phòng lúc tạo (UC-36, `POST /quan-ly-nhan-su/tai-khoan`, cả `quan_ly_nhan_su` lẫn `quan_ly`); mật khẩu ban đầu mặc định, không gửi email/OTP.
- Văn phòng "1 tại mỗi thời điểm", đổi được khi điều chuyển (nhánh kèm UC-36 — **chưa code**). Đơn cũ giữ ở văn phòng cũ.
- `dieu_do_vien` **không gắn văn phòng** nữa (đề xuất điều độ theo tuyến đã duyệt).

**Đã sửa:**

| File | Sửa |
|---|---|
| `services/gui_hang_service.py` `gan_van_phong_can_bo` | Bỏ `dieu_do_vien`; dùng chung hằng số `VAI_TRO_CAN_VAN_PHONG` của `schemas/tai_khoan_can_bo_schema.py` (nhóm đổi quy tắc chỉ sửa 1 chỗ) |
| `routes/quan_ly.py`, `repositories/nguoi_dung_repository.py` | Docstring bỏ "điều độ viên" |
| `tests/unit/test_gui_hang_service.py` | +5 ca: quầy vé/gửi hàng gán được; điều độ viên/phụ xe/kế toán bị chặn |
| `frontend/nhan-vien/gui-hang/khoi-tao.js` | Màn hình chặn: "liên hệ quản lý **hoặc quản lý nhân sự**", "tải lại trang" (middleware đọc `van_phong_id` mỗi request, không cần đăng nhập lại) |
| `NGHIEP_VU_GUI_HANG.md` mục 1, mục 7 | Văn phòng chọn lúc tạo / đổi khi điều chuyển; vai trò `quan_ly_nhan_su` |
| Mục 2 (P1) và 7.4 D (P1) | Cập nhật trạng thái |

**Không cần sửa:** `_pham_vi_van_phong` (`routes/gui_hang.py`), các câu tìm nhân viên văn phòng để thông báo (`don_hang_repository.py`), `seed_gui_hang_demo.py` — chỉ đọc/ghi thẳng `ho_so_can_bo_diem`. `DATABASE.md` mục 1.3 phía QLNS đã sửa.

**Còn chờ (theo thứ tự an toàn của QLNS, mục 3.5 file UC36):**
1. **Giữ** chuỗi `gan_van_phong_can_bo` (route `PUT /quan-ly/ho-so-can-bo-diem`, `GanVanPhongCanBoRequest`, service, `nguoi_dung_repo.gan_van_phong`) — hiện là đường duy nhất sửa văn phòng gán nhầm.
2. Nhóm chốt 2 quy tắc đổi văn phòng. Góc nhìn gửi hàng: **không chặn** khi còn đơn dở (quyền theo văn phòng, chốt ca tiền mặt đã tạm bỏ nên không có tiền treo theo người); lý do đổi **bắt buộc** cho nhất quán UC-51.
3. QLNS code "đổi văn phòng" + merge → gửi hàng xóa chuỗi 4 hàm (PR nhỏ riêng), tìm lại `gan_van_phong` / `GanVanPhongCanBoRequest` toàn dự án, xóa 2 test gán văn phòng ở `test_gui_hang_service.py`.

### 7.7. Tin nhắn báo test fail ngoài role (23/10/2026)

Trạng thái unit test trên integration sau #39: **9 fail** (không có test gửi hàng nào). Tin nhắn mẫu:

**Gửi tuanhdung (#33):**
> Trên integration có 2 test no-show đang fail từ #33: `tests/unit/test_thong_bao_khach.py::test_job_khong_den_bao_khach_kem_so_lan` và `::test_job_khong_den_du_nguong_khoa_va_bao_khoa`. Test mong job `quet_no_show.py` gửi thông báo "Vé … bị ghi nhận là không đến … (hiện 2/3)" cho khách, nhưng job không gửi gì (`[]`) — có vẻ lúc sửa `quet_no_show.py` ở #33 bị mất đoạn gọi `thong_bao_khach_service` (`nd_khong_den`). Bạn xem lại giúp: nếu bỏ có chủ ý thì sửa test, còn không thì thêm lại lời gọi. Chạy thử: `python -m pytest tests/unit/test_thong_bao_khach.py -k khong_den`.

**Gửi Sơn (#39, quầy vé):**
> Sau #39 có 7 test vé lẻ / VNPay fail: `tests/unit/test_ve_le.py` (`test_ipn_ve_thanh_cong`, `test_ipn_ve_that_bai_khong_doi_gi`, `test_ipn_ve_sai_so_tien`, `test_ipn_ve_da_thanh_toan_roi`, `test_ipn_ve_da_bi_huy_trong_luc_thanh_toan_can_hoan_tien_tay`, `test_truy_van_ve_thanh_cong`) và `tests/unit/test_thong_bao_khach.py::test_ipn_ve_le_thanh_cong_bao_khach`. Nguyên nhân: `thanh_toan_service._ap_dung_ket_qua_ve` mới so `ve["ma_tham_chieu_vnpay"]` với `vnp_TxnRef`, còn vé giả trong các test cũ chưa có trường `ma_tham_chieu_vnpay` → trả `01 Transaction reference mismatch` thay vì `00`. Code đúng, chỉ cần thêm `ma_tham_chieu_vnpay` (bằng mã giao dịch test dùng) vào vé giả, và cập nhật mock `ghi_nhan_thanh_toan_ve_le` theo chữ ký mới 3 tham số. Chạy thử: `python -m pytest tests/unit/test_ve_le.py tests/unit/test_thong_bao_khach.py`.
