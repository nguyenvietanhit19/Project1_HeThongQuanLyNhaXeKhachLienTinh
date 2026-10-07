# Kế hoạch sửa & nâng cấp — Nhân viên gửi hàng (FE + BE)

> Căn cứ: `NGHIEP_VU.md` mục 2, 8.5, 10 (10.1–10.5), UC-23/24/25/26/27/28/39/46; `DATABASE.md` mục 5; `THIET_KE_UI.md`.
> Nguồn: 4 hướng rà soát độc lập (BE, FE, checklist nghiệp vụ, tích hợp liên vai trò) ra 98 phát hiện. 68 phát hiện đã qua kiểm chứng phản biện (65 đúng, 3 bị bác). 30 phát hiện tích hợp chưa qua bước phản biện tự động. Các phát hiện mức nghiêm trọng/cao trong số này đã được đối chiếu thủ công với code và git.
> Ký hiệu công sức: **S** < 1 giờ · **M** nửa ngày · **L** ≥ 1 ngày.

> **Trạng thái (04/10/2026):** đã làm toàn bộ Đợt 0–4 và nâng cấp N1 (màn Hàng đến), N3 (in đúng vùng), N4 (đối soát tiền theo nhân viên), N6 (thông báo WebSocket + chuông). Đã làm thêm (05/10/2026): N2 mã vạch Code128, N5 lịch sử trạng thái, N7 chống tạo trùng đơn (Idempotency-Key), N8 tách app.js thành module, N9 phím tắt; cùng gợi ý khách quen theo SĐT, xuất CSV, đếm ngược mốc 7/14 ngày. Đã làm thêm: sửa tên/SĐT người gửi-nhận khi đơn chưa giao + nhật ký chỉnh sửa (migration 20261006). Chưa làm: hủy đơn (đợt B, cần nhóm chốt trạng thái `da_huy` và hoàn tiền mặt), hàng đợi khi mất mạng, chốt ca. Mục 2 (phối hợp) vẫn mở, trừ P4 đã sửa và P6 đã có cột `sdt_lien_he`.

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

| # | Việc | Ai | Ghi chú |
|---|---|---|---|
| P1 | Tạo tài khoản `nhan_vien_gui_hang` **kèm** `van_phong_id` (UC-36), cho cả `quan_ly_nhan_su` gán | Người làm tài khoản cán bộ | Hiện chỉ có `PUT /quan-ly/ho-so-can-bo-diem` không có UI. Nhân viên chưa được gán văn phòng thì bị khóa hoàn toàn. Bạn có thể đưa sẵn hàm `gan_van_phong_can_bo` để họ gọi. |
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
