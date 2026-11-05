# Quy trình test — vai trò Nhân viên gửi hàng

> Phạm vi: toàn bộ chức năng của `nhan_vien_gui_hang` (UC-23, 24, 25, 39, 54, sửa tên/SĐT, thông báo) và các điểm phối hợp với phụ xe (UC-26, 27, 28) và quản lý (chỉ xem).
> Nghiệp vụ đối chiếu: `NGHIEP_VU_GUI_HANG.md`. Lịch sử sửa: `KE_HOACH_SUA_GUI_HANG.md`.

**Khi nào chạy**

| Lúc | Chạy phần nào |
|---|---|
| Trước khi mở PR | Bước 1 + 2 bắt buộc; bước 3: các ca liên quan tới phần vừa sửa + nhóm **[Khói]** |
| Sau khi gộp integration mới về nhánh | Bước 1 + 2 + nhóm **[Khói]** |
| Trước buổi demo / nộp bài | Toàn bộ bước 1 → 4 |

Các ca đánh dấu **[Khói]** là bộ tối thiểu (~15 phút) chứng minh role còn chạy được từ đầu tới cuối.

---

## 0. Chuẩn bị môi trường

### 0.1. Dựng hệ thống

```powershell
# 1. Bật Docker Desktop, đợi biểu tượng cá voi hết nhấp nháy
docker compose up -d
docker compose exec backend sh -c 'yoyo apply --database "$DATABASE_URL" ./migrations'

# 2. Dữ liệu demo gửi hàng (chạy lại bao nhiêu lần cũng được — xóa và tạo lại đơn demo theo giờ hiện tại)
docker compose exec backend python scripts/seed_gui_hang_demo.py
```

- Backend: `http://localhost:8000/docs` hiện Swagger là được.
- Frontend: bấm **Go Live** (VS Code Live Server). `.vscode/settings.json` của dự án đặt gốc là `frontend/` và **cổng 5501** → `http://127.0.0.1:5501/nhan-vien/dang-nhap.html`.
- **"Failed to fetch" khi đăng nhập** = trình duyệt bị CORS chặn: địa chỉ trang (`http://127.0.0.1:5501`, `http://localhost:5501`…) phải có trong `CORS_ORIGINS` của `backend/.env`. Thêm cả `localhost` lẫn `127.0.0.1` với cổng đang dùng, rồi `docker compose up -d --force-recreate backend` (`restart` không nạp lại `.env`). Kiểm tra: `docker compose logs backend` thấy `OPTIONS /auth/dang-nhap ... 400` là đúng lỗi này.
- **Lưu lại phần cuối output của script seed**: danh sách mã vận đơn nổi bật theo từng văn phòng kèm việc nên thử. Mã vận đơn đổi mỗi lần seed nên các ca bên dưới mô tả đơn theo tình huống; tìm mã tương ứng trong output đó.

### 0.2. Tài khoản

| Tài khoản | Mật khẩu | Văn phòng / vai trò |
|---|---|---|
| `guihang.mydinh@demo.nhaxe.vn` | `GuiHang@123` | VP Bến xe Mỹ Đình (khu vực Hà Nội) |
| `guihang.yenbai@demo.nhaxe.vn` | `GuiHang@123` | VP Bến xe Yên Bái (khu vực Yên Bái) |
| `guihang.laocai@demo.nhaxe.vn` | `GuiHang@123` | VP Bến xe Trung tâm Lào Cai (khu vực Lào Cai) |
| `guihang.sapa@demo.nhaxe.vn` | `GuiHang@123` | VP Sa Pa (khu vực **Lào Cai** — cùng khu vực với VP Lào Cai) |
| `phuxe.guihang@demo.nhaxe.vn` | `PhuXe@123` | Phụ xe xe 24B-888.01 (chuyến đang chạy sắp tới Lào Cai) |
| `admin@nhaxekhach.com` | hỏi trưởng nhóm | Quản lý (chỉ xem gửi hàng) |

Nên mở **2 trình duyệt** (hoặc 1 cửa sổ thường + 1 cửa sổ ẩn danh) để đăng nhập 2 văn phòng cùng lúc khi test thông báo real-time.

### 0.3. Mạng lưới demo

```
Tuyến "Mỹ Đình -> Sa Pa (qua Yên Bái)": VP Mỹ Đình → Điểm dừng Km 140 → VP Yên Bái → VP Lào Cai → VP Sa Pa
Tuyến "Mỹ Đình -> Lào Cai" (T001):     VP Mỹ Đình → VP Lào Cai
```

- Cặp Mỹ Đình ↔ Lào Cai có **2 tuyến** (phải chọn tuyến khi tạo đơn).
- Điểm dừng Km 140 **không** được chọn làm điểm nhận (không phải văn phòng).
- Lào Cai ↔ Sa Pa **cùng khu vực** → không gửi được cho nhau.
- Chuyến hôm nay: 1 chuyến **đang chạy** (xe 24B-888.01, đã qua Yên Bái, sắp tới Lào Cai), 1 chuyến **gặp sự cố** (Sa Pa → Mỹ Đình, sạt lở), 1 chuyến **đang hoãn** (đã chất hàng), 1 chuyến **đã hoàn thành** (hàng vừa tới Lào Cai, Sa Pa).

### 0.4. Chạy job thủ công (không cần chờ 1 tiếng)

```powershell
docker compose exec backend python -c "from app.jobs.quet_hang_ton import chay_job_quet_hang_ton as j; print(j())"
```

Kết quả in số đơn được nhắc 24 giờ / bật cảnh báo 7 ngày / chuyển hàng tồn 14 ngày.

---

## Bước 1. Test tự động (bắt buộc)

```powershell
# Test của role gửi hàng (+ phần phụ xe gọi sang gửi hàng)
docker compose exec backend python -m pytest tests/unit/test_gui_hang_service.py tests/unit/test_don_hang_schema.py tests/unit/test_quet_hang_ton.py tests/unit/test_phu_xe_hang.py -q

# Toàn bộ unit test (giống CI)
docker compose exec backend python -m pytest tests/unit -q

# Cú pháp JS giao diện gửi hàng (máy có Node)
Get-ChildItem frontend\nhan-vien\gui-hang\*.js | ForEach-Object { node --check $_.FullName }
```

**Đạt khi:**
- Lệnh thứ nhất: **100% pass** (05/11/2026: 181 test — thêm 7 test thống kê theo kỳ).
- Lệnh thứ hai: không có test fail **nào có tên liên quan gửi hàng**. Test fail ngoài role → ghi tên vào phiếu kết quả (mục 5) và báo người phụ trách, không tự sửa file của người khác. (05/11/2026 trên integration `24d99ba`: 25 fail có sẵn — VNPay / vé lẻ / thông báo khách / quầy vé.)
- Lệnh thứ ba: không in lỗi nào.

## Bước 2. Kiểm thử đồng thời (bắt buộc khi sửa repository / service)

```powershell
docker compose exec backend python scripts/kiem_thu_dong_thoi_gui_hang.py 30
```

Script chỉ chạy trên DB local và tự dọn đơn thử. **Đạt khi cả 5 tình huống 30/30 đúng** và mỗi tình huống có cả 2 kết cục xảy ra (không phải 1 bên luôn thắng):

| Tình huống | Kết quả đúng |
|---|---|
| 2 nhân viên cùng giao 1 đơn | Chỉ 1 người giao được |
| Hủy đúng lúc phụ xe chất hàng | Hoặc hủy, hoặc chất — dữ liệu không lai |
| Ghi liên hệ đúng lúc giao | Giao luôn thành công; liên hệ kịp hoặc bị chặn |
| 2 nhân viên cùng hủy | Hoàn tiền đúng 1 lần |
| 2 request tạo đơn cùng `Idempotency-Key` | Luôn đúng 1 đơn |

---

## Bước 3. Test trên giao diện

### 3.0. Chạy tự động (khuyên dùng)

`backend/scripts/kiem_thu_giao_dien_gui_hang.py` tự bấm các ca của bước 3 + bước 4 trên **Microsoft Edge** (Playwright, chạy ẩn) — 13 ca [Khói] + 62 ca còn lại. Chạy trên máy, từ thư mục gốc dự án, khi Docker và Live Server (cổng 5501) đang chạy:

```powershell
# Cài 1 lần vào .venv của máy (không vào Docker, không vào CI)
.\.venv\Scripts\pip install -r backend/scripts/requirements-kiem-thu-giao-dien.txt

.\.venv\Scripts\python backend/scripts/kiem_thu_giao_dien_gui_hang.py khoi     # bộ [Khói], ~1 phút
.\.venv\Scripts\python backend/scripts/kiem_thu_giao_dien_gui_hang.py day-du   # các ca còn lại, ~4 phút
.\.venv\Scripts\python backend/scripts/kiem_thu_giao_dien_gui_hang.py tat-ca   # cả hai
# thêm --hien để xem trình duyệt bấm; --anh <thư mục> để chọn nơi lưu ảnh chụp ca lỗi / CSV tải về
```

- **Chỉ dùng DB local:** đầu mỗi bộ script tự chạy lại seed, tạo rồi xóa 1 tài khoản tạm chưa gán văn phòng (A4), sinh token quản lý trong container (không cần mật khẩu quản lý), đổi rồi trả lại mật khẩu tài khoản Yên Bái (A5), và **khởi động lại backend** (I2). Xong thì dữ liệu demo đã bị thay đổi → seed lại nếu muốn test tay.
- Phần phụ xe (dỡ hàng, hoàn tác, báo hư hỏng) gọi API thay vì bấm trên giao diện phụ xe.
- Cuối cùng in bảng **ĐẠT / LỖI** từng ca, lỗi Console của trình duyệt, đường dẫn ảnh chụp ca lỗi (`*_LOI.png`). Mã thoát 0 = mọi ca đạt.
- Không tự động: **H5** (dữ liệu demo không có đơn chờ chất phù hợp) và việc **nhìn bằng mắt** bố cục / màu sắc — vẫn nên lướt qua ảnh chụp và tự bấm vài ca trước demo.
- Kết quả 05/11/2026 trên integration `24d99ba`: [Khói] 13/13; còn lại 54/55 — ca lỗi duy nhất **I1** là lỗi của PR #47 (không đánh dấu đã đọc thông báo được, xem `KE_HOACH_SUA_GUI_HANG.md` mục 9.3).
- Kết quả 05/11/2026 sau đợt F (thống kê theo kỳ, `KE_HOACH_SUA_GUI_HANG.md` mục 10): 74/75 — J7–J13 đạt; vẫn chỉ lỗi **I1** (PR #47).

### 3.1. Test tay

Cách ghi: mỗi ca đánh **Đạt / Lỗi / Bỏ qua** vào phiếu (mục 5). Ca lỗi ghi theo mẫu mục 6.

### A. Đăng nhập và quyền

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| A1 **[Khói]** | NV Mỹ Đình | Đăng nhập | Vào trang gửi hàng; topbar hiện đúng tên văn phòng; sidebar có 5 mục: Tiếp nhận, Hàng đến & Giao hàng, Đơn gửi đi, Hàng chờ lâu, Thống kê & Đối soát |
| A2 | Phụ xe | Đăng nhập phụ xe rồi gõ thẳng địa chỉ `.../nhan-vien/gui-hang/index.html` | Hộp "Bạn không có quyền truy cập vào phân hệ Nhân viên gửi hàng!" rồi bị đăng xuất về trang đăng nhập |
| A3 | Quản lý | Mở trang gửi hàng | Nhãn "Quản lý (chỉ xem)"; **không** có tab Tiếp nhận; có ô chọn văn phòng; không có nút Giao / Hủy / Sửa / Liên hệ |
| A4 | Tài khoản gửi hàng chưa gán văn phòng (tạo bằng QLNS, hoặc xóa dòng `ho_so_can_bo_diem` của 1 tài khoản thử) | Đăng nhập | Màn hình chặn "liên hệ quản lý hoặc quản lý nhân sự"; vẫn đăng xuất được |
| A5 | NV Mỹ Đình | Khối tài khoản ở đáy sidebar → Tài khoản của tôi → sửa họ tên, đổi mật khẩu | Lưu được; đổi mật khẩu xong đăng nhập lại bằng mật khẩu mới được (nhớ đổi lại `GuiHang@123` hoặc seed lại) |
| A6 | NV Mỹ Đình | Đăng xuất khi đang nhập dở form tạo đơn | Hộp xác nhận cảnh báo mất dữ liệu đang nhập |

### B. Tiếp nhận — tạo đơn (UC-23)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| B1 **[Khói]** | NV Mỹ Đình | Tạo đơn tới VP Yên Bái, hàng thông thường 3 kg, cước 50.000, **trả trước**, tích đã thu → Xác nhận | Hộp xác nhận đọc lại đúng thông tin; tạo xong in **2 bản**: nhãn dán (mã vận đơn + mã vạch + điểm đến + SĐT người nhận) và biên nhận (mã vận đơn + văn phòng nhận + SĐT văn phòng nhận); đơn ở trạng thái Chờ xếp xe |
| B2 **[Khói]** | NV Mỹ Đình | Tạo đơn **COD** (người nhận trả cước) tới VP Sa Pa | Không có ô "đã thu"; biên nhận ghi người nhận trả cước |
| B3 | NV Mỹ Đình | Chọn khu vực Lào Cai → VP Lào Cai | Có **2 tuyến** để chọn; chưa chọn tuyến thì không tạo được |
| B4 | NV Lào Cai | Mở danh sách khu vực đến | **Không** có khu vực Lào Cai (VP Sa Pa cùng khu vực không xuất hiện); Km 140 không bao giờ xuất hiện |
| B5 | NV Mỹ Đình | Mở ô Loại hàng, tìm "Chất dễ cháy nổ / Hàng cấm" | Hàng cấm **có hiện** (để đối chiếu) nhưng **bị khóa, không chọn được**; gọi API thẳng với loại hàng cấm → 400 "thuộc danh mục cấm vận chuyển" |
| B6 | NV Mỹ Đình | Trả trước nhưng **không** tích "đã thu" | Không cho xác nhận |
| B7 | NV Mỹ Đình | Nhập dữ liệu sai: SĐT 9 số / có chữ, tên rỗng, cước 0 hoặc âm, cân nặng 0, kích thước âm | Báo lỗi đúng ô, không gửi |
| B8 | NV Mỹ Đình | Nhập SĐT người gửi đã từng gửi (lấy SĐT của 1 đơn cũ) | Gợi ý họ tên khách quen |
| B9 | NV Mỹ Đình | Bấm nút xác nhận 2 lần thật nhanh | Chỉ **1** đơn được tạo |
| B10 | NV Mỹ Đình | Mở hộp xác nhận → `docker compose stop backend` → bấm tạo → F5 → `docker compose start backend` → F5 | Trang mở lại hộp xác nhận với **đúng nội dung cũ** kèm nhắc "CHƯA được tạo, hỏi lại khách"; không tự gửi; bấm tạo lại → chỉ 1 đơn |
| B11 | NV Mỹ Đình | Tên người nhận có thẻ HTML, vd `<b>Lan</b>` | Hiển thị nguyên chữ, không in đậm (không chèn được HTML) |

### C. Đơn gửi đi, tra cứu, in lại

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| C1 **[Khói]** | NV Mỹ Đình | Tab Đơn gửi đi | Thấy đơn vừa tạo ở đầu danh sách; phân trang 10 dòng |
| C2 | NV Mỹ Đình | Lọc theo từng trạng thái, theo hình thức thanh toán, gõ tìm theo mã / tên / SĐT | Kết quả đúng bộ lọc; nút Đặt lại trả về đủ |
| C3 | NV Mỹ Đình | Xuất CSV | File mở được bằng Excel, tiếng Việt không lỗi font, đúng số dòng theo bộ lọc |
| C4 | NV Mỹ Đình | In lại biên nhận 🖨️ và nhãn 🏷️ của 1 đơn | Đúng nội dung như lúc tạo |
| C5 | NV Mỹ Đình | Tra mã vận đơn của 1 đơn **Chờ xếp xe** ở ô tra cứu tab Hàng đến | Mở chi tiết, cảnh báo "Hàng chưa tới văn phòng nhận"; có hành trình (timeline trạng thái) |
| C6 | NV Yên Bái | Tra mã 1 đơn Mỹ Đình → Lào Cai (không liên quan Yên Bái) | Bị từ chối (đơn không thuộc văn phòng) |

### D. Hủy đơn (UC-54)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| D1 **[Khói]** | NV Mỹ Đình | Hủy đơn "Chờ xếp xe, trả trước — thử HỦY ĐƠN (hoàn 100.000đ)", lý do "Khách đổi ý", tích đã trả hàng | Đơn Đã hủy; hiện số tiền hoàn **100.000đ**; in được phiếu hủy / hoàn tiền |
| D2 | NV Mỹ Đình | Hủy đơn "Chờ xếp xe, người nhận trả cước" | Số tiền hoàn **0đ**, không in phiếu hoàn |
| D3 | NV Mỹ Đình | Chọn lý do "Khác" bỏ trống ghi chú | Bắt buộc ghi chú |
| D4 | NV Mỹ Đình | Hủy với lý do "Nhập sai thông tin" | Sau khi hủy mở form tạo đơn mới **điền sẵn** người gửi, người nhận, loại hàng, cân nặng; tiền đơn mới thu riêng |
| D5 | NV Mỹ Đình | Tìm nút hủy ở đơn đang trên xe / đã tới / đã giao | Không có nút hủy (gọi API thẳng → bị chặn "Hàng đã rời văn phòng gửi") |
| D6 | NV Lào Cai | Tìm nút hủy ở đơn Mỹ Đình → Lào Cai đang chờ xếp xe | Không có (chỉ văn phòng gửi mới hủy) |
| D7 | NV Mỹ Đình | Mở chi tiết đơn đã hủy | Thấy lý do, người hủy, thời điểm, tiền hoàn; không sửa / giao / liên hệ được |

### E. Sửa tên / SĐT

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| E1 | NV Mỹ Đình | Sửa chính tả tên người nhận của 1 đơn chờ xếp xe | Không bắt lý do; nhật ký chỉnh sửa có dòng mới |
| E2 | NV Mỹ Đình + NV Lào Cai (2 trình duyệt) | Mỹ Đình đổi **SĐT người nhận** của 1 đơn đang Chờ lấy ở Lào Cai | Bắt buộc lý do; Lào Cai nhận thông báo "gọi báo lại người nhận theo số mới"; đơn ở Lào Cai quay về **Chưa báo** |
| E3 | NV Lào Cai | Mở đơn "Đã SỬA SĐT người nhận" | Nhật ký: số cũ → số mới, người sửa, lý do |
| E4 | NV Mỹ Đình | Sửa đơn đã giao / đã hủy | Không có nút sửa |

### F. Hàng đến, gọi báo, giao hàng (UC-24)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| F1 **[Khói]** | NV Lào Cai | Tab Hàng đến | Có các nhóm Sắp đến / Chờ gọi báo / Chờ lấy / Quá 7 ngày / Hàng tồn với số đếm trên chip; bấm chip lọc đúng nhóm |
| F2 | NV Lào Cai | Xem đơn "Sắp đến nhưng chuyến ĐANG HOÃN" và đơn trên chuyến **gặp sự cố** (ở VP Mỹ Đình / Yên Bái) | Nhãn ⏸ / ⚠️ kèm lý do, việc cần làm "Hàng sẽ tới trễ"; không có nút Giao |
| F3 **[Khói]** | NV Lào Cai | Đơn "Vừa tới, CHỜ GỌI BÁO" → 📞 Liên hệ → "Đã gọi báo được người nhận" | Lịch sử liên hệ có dòng mới; đơn chuyển sang **Chờ lấy**, nhãn ✅ Đã báo |
| F4 | NV Lào Cai | "Gọi người nhận không được" | Ghi lịch sử; vẫn ở Chờ gọi báo |
| F5 **[Khói]** | NV Lào Cai | Giao đơn "Chờ lấy, đã báo, trả trước — thử GIAO HÀNG": nhập mã ở ô tra cứu → tích đã kiểm hàng → Giao | Đơn Đã giao; in phiếu bàn giao; biến khỏi danh sách |
| F6 | NV Lào Cai | Giao đơn COD "đã báo người nhận, COD 55.000đ" — không tích "đã thu" | Không cho giao; tích rồi mới giao được; thống kê COD đã thu tăng 55.000 |
| F7 | NV Lào Cai | Giao đơn "có BÁO CÁO HƯ HỎNG của phụ xe" | Modal giao hiện khung đỏ nội dung báo cáo hư hỏng |
| F8 | NV Lào Cai | Ô tra cứu nhập **SĐT người nhận** (10–11 số) thay vì mã | Danh sách đơn chờ giao của SĐT đó → "Đúng người — Giao" |
| F9 | NV Lào Cai | Nhập mã đơn còn trên xe / đã giao / đã hủy / của văn phòng nhận khác / mã sai | Mỗi trường hợp báo đúng lý do, không giao |
| F10 | NV Lào Cai | Quét / gõ mã viết thường | Vẫn tìm ra (tự viết hoa) |
| F11 | NV Mỹ Đình | Thử giao đơn Mỹ Đình → Lào Cai đang chờ lấy | Không giao được (chỉ văn phòng nhận) |

### G. Hàng chờ lâu và job tự động (UC-25)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| G1 | NV Lào Cai | Tab Hàng chờ lâu | Có đơn quá 7 ngày và hàng tồn; cột "Từng báo được / Chưa từng báo được"; đếm ngược mốc |
| G2 | NV Lào Cai | Đơn "Chờ quá 7 NGÀY, đã từng báo" | Việc cần làm: **gọi lại người nhận** |
| G3 | NV Lào Cai | Đơn "Chờ quá 7 NGÀY, CHƯA từng báo được" | Việc cần làm: **gọi người gửi**; có lựa chọn "báo quản lý" |
| G4 | NV Lào Cai + Quản lý | "HÀNG TỒN (16 ngày), không liên hệ được ai" → Liên hệ → Báo quản lý | Quản lý nhận thông báo trên chuông |
| G5 | NV Lào Cai | Đơn chờ lấy **dưới 7 ngày** | Không có lựa chọn báo quản lý |
| G6 | NV Lào Cai | "Đã liên hệ được người gửi" bỏ trống ghi chú | Bắt buộc ghi hướng xử lý |
| G7 | NV Lào Cai | Giao đơn "HÀNG TỒN đã thỏa thuận với người gửi" (COD 60.000đ) | Giao được, modal ghi rõ đang giao hàng tồn |
| G8 | NV Lào Cai | Chạy job (mục 0.4), rồi F5 trang và mở chuông | Lần 1 in số đơn được nhắc 24 giờ / cảnh báo 7 ngày (có thể là 0 nếu job nền của backend đã quét trước); chuông có tin tương ứng; chạy lần 2 → **toàn 0** (không nhắc trùng). *Chạy job bằng lệnh là tiến trình riêng nên **không** đẩy toast real-time — job nền chạy trong backend mới đẩy real-time* |
| G9 | NV Lào Cai | Xuất CSV hàng tồn | Đủ cột người nhận / người gửi / số ngày / đã từng báo |

### H. Phối hợp phụ xe (UC-26, 27, 28)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| H1 **[Khói]** | Phụ xe + NV Lào Cai (2 trình duyệt) | Phụ xe: xác nhận **tới VP Lào Cai** → dỡ đơn "Sắp đến trên xe 24B-888.01" | Lào Cai nhận toast real-time "vừa tới văn phòng — gọi báo người nhận …"; đơn chuyển sang Chờ gọi báo |
| H2 | Phụ xe + NV Lào Cai | Phụ xe hoàn tác dỡ khi Lào Cai **chưa** gọi báo | Lào Cai nhận "đừng gọi báo người nhận"; đơn về Sắp đến |
| H3 | Phụ xe | Hoàn tác dỡ sau khi Lào Cai đã tích "đã báo" | Bị chặn |
| H4 | Phụ xe + NV Lào Cai | Phụ xe báo **hư hỏng** 1 đơn đang trên xe tới Lào Cai | Lào Cai và quản lý nhận thông báo; khi giao hiện cảnh báo (F7) |
| H5 | NV Mỹ Đình | Tạo đơn mới tới Lào Cai rồi hủy | Đơn hủy **không** còn trong danh sách chờ chất của phụ xe |

### I. Thông báo (chuông)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| I1 | NV Lào Cai | Mở chuông | Số chưa đọc đúng; bấm 1 thông báo có mã đơn → đánh dấu đã đọc + mở chi tiết đơn |
| I2 | NV Lào Cai | `docker compose restart backend` khi đang mở trang, rồi tạo 1 thông báo (vd phụ xe báo hư hỏng) | Trong ≤ 75 giây tin mới **có trên chuông** (trang tự nối lại WebSocket rồi tải lại chuông, hoặc poll 60 giây). Tin phát ra đúng lúc đang mất kết nối không hiện toast — chỉ hiện trên chuông |

### J. Thống kê và đối soát (UC-39)

| Mã | Tài khoản | Bước | Kết quả mong đợi |
|---|---|---|---|
| J1 **[Khói]** | NV Mỹ Đình | Mở tab Thống kê | Kỳ mặc định "Tháng MM/YYYY" (tháng này); đủ chỉ số hàng gửi đi (tiếp nhận, chờ xếp xe, trên xe, hủy) và hàng nhận về; 4 biểu đồ hiện |
| J2 | NV Mỹ Đình | Đối chiếu doanh thu | **Doanh thu = trả trước đã thu + COD đã thu − tiền hoàn**; ngày chỉ có hoàn được phép âm |
| J3 | NV Mỹ Đình | Sau D1, xem đối soát hôm nay | Dòng của nhân viên hủy có tiền hoàn 100.000 (cộng với 95.000 của đơn demo "Đã hủy hôm nay"); tổng = thu − hoàn |
| J4 | NV Mỹ Đình | Chế độ **Tùy chọn**: từ ngày > đến ngày | Báo "Khoảng ngày không hợp lệ", không tải kỳ mới |
| J5 | NV Mỹ Đình | Xuất CSV / in đối soát | Đúng số liệu trên màn hình |
| J6 | Quản lý | Thống kê không chọn văn phòng / chọn 1 văn phòng | Toàn hệ thống / đúng văn phòng đó |
| J7 | NV Mỹ Đình | Tháng này: ▶ bị khóa; bấm ◀ → tháng trước; bấm ◀ 3 lần thật nhanh | Nhãn kỳ, ô số và biểu đồ luôn là của kỳ chọn sau cùng (không bị kỳ cũ về muộn đè lên) |
| J8 | NV Mỹ Đình | Đổi Tháng / Ngày / Năm | Biểu đồ: tháng đủ số ngày (ngày chưa tới để trống, không có cột), ngày 24 mốc 0h–23h, năm 12 mốc Th1–Th12 |
| J9 | — (API) | `GET /gui-hang/thong-ke-chuoi` theo giờ / ngày / tháng; NV, quản lý toàn hệ thống, quản lý 1 văn phòng | Cộng các mốc = `/gui-hang/thong-ke` cùng kỳ; mỗi mốc ngày = `/thong-ke` của riêng ngày đó; NV Mỹ Đình gọi với `diem_id` Lào Cai → 403 |
| J10 | NV Mỹ Đình | Bấm **📊 Xuất Excel** (tháng này) | Tải `thong-ke-gui-hang_YYYY-MM.xlsx`, 3 sheet Tổng quan / Theo ngày / Đối soát nhân viên; dòng TỔNG khớp ô số trên tab; ô tiền là số có phân cách nghìn |
| J11 | NV Mỹ Đình | Bấm **🖨️ In báo cáo** | Xem trước bản in A4 dọc: đầu trang văn phòng / kỳ / người in, bảng chỉ số, 4 biểu đồ có màu, bảng đối soát, ô ký "Người lập" / "Người nhận tiền"; không có sidebar |
| J12 | NV Mỹ Đình | Biểu đồ tiền mặt có mốc doanh thu âm (ngày chỉ có hoàn) | Trục dọc có phần âm, điểm "Còn lại" nằm dưới vạch 0, không tràn khung |
| J13 | NV Mỹ Đình | Tắt backend (hoặc mất mạng) rồi bấm ◀; Tùy chọn từ 01/01/2025 đến hôm nay | Ô số / tiền mặt / tổng đối soát hiện "—" (không còn số kỳ trước dưới nhãn kỳ mới); khoảng > 1 năm báo "tối đa 1 năm" và giữ nguyên kỳ đang xem |

### K. Giao diện và thiết bị

Kiểm ở **1920px, 1100px, 880px, 400px** (DevTools → Toggle device toolbar):

| Mã | Kết quả mong đợi |
|---|---|
| K1 | > 880px: sidebar dọc, nút thu gọn hoạt động và được nhớ sau F5; ≤ 880px: thanh ngang trên đầu cuộn ngang được |
| K2 | Không có thanh cuộn ngang của cả trang ở mọi cỡ |
| K3 | ≤ 1279px bảng chuyển thành thẻ; < 640px modal trượt từ dưới, nút bấm không bị che |
| K4 | Menu tài khoản và bảng thông báo mở đúng chỗ, không tràn ra ngoài màn hình ở 400px |
| K5 | Trang in (biên nhận, nhãn, phiếu hủy, phiếu bàn giao) chỉ in phần phiếu, không in sidebar |
| K6 | Console trình duyệt (F12) không có lỗi đỏ trong suốt các ca trên |

---

## Bước 4. Kiểm tra API trực tiếp (tùy chọn, trước demo)

Trên `http://localhost:8000/docs` → Authorize bằng token đăng nhập (`POST /auth/dang-nhap`):

| Mã | Gọi | Mong đợi |
|---|---|---|
| P1 | Bất kỳ API `/gui-hang/...` không token / token sai | 401 |
| P2 | `POST /gui-hang/tao-don` bằng token quản lý (hoặc tài khoản quầy vé nếu có) | 403 |
| P3 | `POST /gui-hang/tao-don` với `diem_gui_id` là văn phòng khác văn phòng của mình | 403 "Không có quyền thao tác tại văn phòng này" |
| P4 | `POST /gui-hang/tao-don` từ VP Lào Cai tới VP Sa Pa | 400 "Chỉ nhận gửi tới văn phòng ở khu vực khác…" |
| P5 | `GET /gui-hang/tra-cuu/{ma}` (công khai) | Không lộ tên / SĐT người gửi, người nhận |
| P6 | `GET /gui-hang/thong-ke-chuoi?tu_ngay=…&den_ngay=…&don_vi=gio` với 2 ngày khác nhau; `don_vi=ngay` cho khoảng > 62 ngày; `don_vi=tuan` | 400 kèm lý do ("chỉ áp dụng cho 1 ngày" / "tối đa 62 ngày" / "chỉ nhận giờ, ngày hoặc tháng") |

---

## 5. Phiếu kết quả (chép vào cuối mỗi lần test)

```
Ngày:            Người test:            Nhánh / commit:
Bước 1: test gửi hàng ___/___ pass · toàn bộ ___ pass, ___ fail (fail ngoài role: ...)
Bước 2: giao __/30 · hủy-chất __/30 · liên hệ-giao __/30 · 2 hủy __/30 · trùng khóa __/30
Bước 3: Đạt ___ · Lỗi ___ · Bỏ qua ___ (lý do bỏ qua: ...)
Ca lỗi: (mã ca + link mô tả theo mẫu mục 6)
Kết luận: [ ] Được mở PR / demo   [ ] Chưa — còn lỗi chặn
```

**Tiêu chí được mở PR / demo:** bước 1 đạt, bước 2 đạt (nếu có sửa repository/service), **không còn ca [Khói] nào lỗi**, ca lỗi còn lại đã ghi vào `KE_HOACH_SUA_GUI_HANG.md`.

## 6. Mẫu ghi lỗi

```
Mã ca:        F6
Tài khoản:    guihang.laocai@demo.nhaxe.vn
Đơn:          DH-2026xxxx-xxxxxx
Các bước:     1. ... 2. ... 3. ...
Mong đợi:     ...
Thực tế:      ... (kèm ảnh chụp màn hình, lỗi Console F12, phản hồi API ở tab Network)
Mức độ:       Chặn (không làm tiếp được) / Nặng (sai tiền, sai trạng thái) / Nhẹ (giao diện, chữ)
```

## 7. Sau khi test

- Dữ liệu bị thay đổi (đơn đã giao, đã hủy, mật khẩu đổi...) → chạy lại `seed_gui_hang_demo.py` để về trạng thái ban đầu.
- Tài khoản thử tạo thêm (A4) → khóa hoặc xóa.
- Nếu đã `docker compose stop backend` ở B10 → nhớ `docker compose start backend`.
