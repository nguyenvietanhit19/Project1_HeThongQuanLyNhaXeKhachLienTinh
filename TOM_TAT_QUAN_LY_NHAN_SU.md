# Tóm tắt phiên làm việc — Quản lý nhân sự (UC-49, rồi UC-36)

> **Cập nhật 23/10/2026 — UC-36 bỏ cơ chế mời bằng OTP.** Email cán bộ do công ty cấp nên không cần xác minh. Khi tạo, tài khoản có mật khẩu ban đầu mặc định `12345678` (lưu bản băm; response trả `mat_khau_ban_dau` để nhắc người tạo) và **không gửi email**; cán bộ đổi mật khẩu sau khi đăng nhập. OTP chỉ dùng khi quên mật khẩu. Mọi chỗ bên dưới nhắc "mời/OTP/`da_gui_email`/mail lỗi" cho UC-36 là **bản cũ**; bản đúng ở `NGHIEP_VU.md` UC-36 và `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md` mục 2.4. Giữ lại `da_xac_nhan = true` lúc tạo (`dang_nhap` chặn mọi tài khoản chưa xác nhận).

> File ghi lại quá trình làm việc, không phải tài liệu nghiệp vụ chính thức. Nghiệp vụ chính thức nằm ở `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md`, `ARCHITECTURE.md`. Tổng hợp dễ đọc riêng cho phần quản lý nhân sự nằm ở [`NHAP_QUAN_LY_NHAN_SU.md`](NHAP_QUAN_LY_NHAN_SU.md).
>
> **Mục 1 đến 7 là trạng thái đến ngày 11/10/2026** (một số chỗ nay đã cũ, VD "frontend chưa test", "chưa viết UC-36"). **Từ ngày 11/10 trở đi xem mục 8 đến 13**, là phần mới nhất.

---

## 1. Bối cảnh

Người dùng (Nghĩa) phụ trách phần nghiệp vụ **Quản lý nhân sự** (`quan_ly_nhan_su`) và **Điều độ viên** (`dieu_do_vien`) trong đồ án nhóm 5 người. Dự án: FastAPI + PostgreSQL + Docker (backend), HTML/CSS/JS tĩnh không framework (frontend).

Nhánh làm việc hiện tại: **`feature/Nghia-uc49-ho-so-nhan-su`**, tạo từ `integration/gop-nhanh-thanh-vien` (nhánh backup/gộp chung của cả nhóm — không dùng `main`).

---

## 2. Diễn biến chính (theo trình tự)

1. **Hướng dẫn chạy dự án lần đầu**: Docker Desktop, tạo `backend/.env` từ `.env.example`, `docker-compose up -d --build`, chạy migration bằng `yoyo`, kiểm tra qua Swagger (`/docs`).
2. **Bàn mở rộng nghiệp vụ Quản lý nhân sự**: ngoài tạo/khóa tài khoản (đã có), đề xuất thêm — quản lý hồ sơ tài xế/phụ xe + giấy tờ, cảnh báo giấy tờ hết hạn, cho nghỉ việc, xem nhật ký thao tác. Viết nháp vào `NHAP_QUAN_LY_NHAN_SU.md` (**không sửa trực tiếp file chính** theo yêu cầu).
3. **Thiết kế database riêng** (`database_quanLyNhanSu.md`): bảng `nhan_su_van_hanh` mở rộng, `giay_to_nhan_su` (mới), `nhat_ky_quan_ly_nhan_su` (mới, **tách riêng** khỏi `nhat_ky_admin` — chỉ ghi hành động của `quan_ly_nhan_su`, không lẫn `quan_ly`).
4. **Phát hiện xung đột kiến trúc**: cột "ảnh hồ sơ" cần lưu file, nhưng `ARCHITECTURE.md` đã chủ động bỏ Cloudinary. Bàn bạc và quyết định **dùng lại Cloudinary**, chỉ riêng cho ảnh hồ sơ/giấy tờ nhân sự — lưu `public_id` (không lưu URL), ảnh phát qua URL có chữ ký (`authenticated` delivery).
5. Viết `services/luu_tru_anh_service.py` (upload/xem/xóa ảnh Cloudinary), thêm `CLOUDINARY_URL` vào `.env`/`.env.example`.
6. Viết migration tạo 3 bảng trên — lúc đó đánh dấu "tạm thời" vì sợ trùng với migration thật của Trưởng nhóm.
7. **Sang phần Điều độ viên**: giải thích bảng nào thuộc ai, phát hiện cả chuỗi bảng "danh mục" (xe, tuyến, loại xe...) chưa có migration nào trong toàn bộ repo — tạo file thiết kế `database_dieuDoVien.md` và 2 migration tạm.
8. **Cập nhật nhánh theo chỉ dẫn nhóm**: bỏ `main`, chuyển hẳn sang làm việc trên `integration/gop-nhanh-thanh-vien`. Cấu hình lại `.env` theo chuẩn mới của nhóm (Brevo API thay Gmail SMTP, VNPay sandbox/giả lập).
9. Tạo nhánh sạch `feature/Nghia-uc47-ho-so-nhan-su` (sau đổi tên) từ `integration` để làm riêng UC hồ sơ nhân sự.
10. **Phát hiện trùng số UC**: UC-47/48 đã bị nhóm dùng cho "sinh chuyến". Đánh số lại toàn bộ 4 UC nháp: UC-47→**49**, UC-48→**50**, UC-49→**51**, UC-50→**52**. Đổi tên nhánh thành `feature/Nghia-uc49-ho-so-nhan-su`.
11. **Viết chính thức vào tài liệu gốc** (theo yêu cầu, không còn là nháp): thêm UC-49/51/52 vào `NGHIEP_VU.md` (mục 2, 3.2, 8.9, 11, 12) và `UML_DIAGRAMS.md` (sơ đồ use case mục 1.6, 1.8).
12. **Pull nhánh `integration` mới nhất về, bỏ hết thay đổi cũ của nhánh mình**: `git stash` (an toàn), cập nhật `integration` (+6 commit, ~130 file — toàn bộ luồng đặt vé/thanh toán VNPay/gửi hàng mới), `git reset --hard` nhánh hiện tại về đúng `integration`.
13. **Phát hiện bất ngờ**: nhóm (có thể chính là phiên làm việc khác) **đã tự hoàn thiện chính thức UC-49/51/52** trong đợt merge đó — khớp gần như tuyệt đối với thiết kế đã bàn, chỉ khác 1 điểm: UC-50 (cảnh báo giấy tờ) được **gộp vào UC-49** làm "cơ chế kèm theo" thay vì tách UC riêng. Database, Cloudinary, migration cũng đã có sẵn, đúng y hệt. Xóa stash cũ (không còn cần).
14. **Viết lại `NHAP_QUAN_LY_NHAN_SU.md`** thành tài liệu **tổng hợp để đọc nhanh** (gom từ `NGHIEP_VU.md`/`UML_DIAGRAMS.md`/`DATABASE.md`/`ARCHITECTURE.md`/`CONTRIBUTING.md`), không còn là bản nháp chờ duyệt.
15. **Viết backend UC-49** (repository, service, schema, route, job cảnh báo giấy tờ) — test thành công qua Swagger/PowerShell (phát hiện lỗi hiển thị của Swagger UI với header tùy chọn, dùng PowerShell `Invoke-RestMethod` để test thay thế).
16. **Viết frontend UC-49**: trang tổng quan + trang quản lý hồ sơ (danh sách, thêm/sửa, giấy tờ, upload ảnh).
17. **Người dùng yêu cầu dừng, rà soát lại nguyên tắc**: *"không được sửa gì trong file đã có của người khác, chỉ được thêm"*. Phát hiện 1 lần lỡ sửa `frontend/nhan-vien/dang-nhap.html` (đổi đường dẫn sau đăng nhập) → revert. Rà soát luôn 4 file backend đã "sửa" (dù chỉ thêm hàm/dòng) → theo yêu cầu, **revert cả 4**, viết lại hoàn toàn theo kiểu tách file riêng để không đụng ai.
18. **Chốt lại quy tắc rõ ràng hơn**: *"thêm được, không được sửa"* (field/hàm thêm vào file có sẵn là OK, miễn không đổi cái cũ). Viết lại lần cuối: gộp các hàm hồ sơ vào thẳng cuối `nhan_su_van_hanh_repository.py` (file của Trưởng nhóm) dưới dạng **chỉ thêm hàm mới, không sửa hàm cũ** (hàm đọc chi tiết đặt tên mới `tim_ho_so_day_du` thay vì sửa `tim_theo_id` có sẵn). `config.py` và `main.py` cũng chỉ thêm dòng mới. Xác nhận bằng `git diff --stat`: các file này **0 dòng xóa**, chỉ có dòng thêm.

---

## 3. Quyết định nghiệp vụ đã chốt (chính thức)

| UC | Tên | Actor |
|---|---|---|
| UC-49 | Quản lý hồ sơ nhân sự vận hành (tài xế/phụ xe) — *gồm cơ chế cảnh báo giấy tờ (UC-50 cũ) làm nhánh kèm theo* | Quản lý nhân sự, Quản lý |
| UC-51 | Cho nghỉ việc nhân sự vận hành | Quản lý nhân sự, Quản lý |
| UC-52 | Xem nhật ký thao tác | Quản lý nhân sự (của mình), Quản lý (toàn bộ) |

- **Ranh giới với `quan_ly`**: quản lý nhân sự lo "ai là nhân sự, giấy tờ còn hạn không" (hồ sơ); `quan_ly` lo "người đó đi xe nào" (biên chế, UC-35).
- **Nhật ký `nhat_ky_quan_ly_nhan_su` tách riêng** khỏi `nhat_ky_admin` — chỉ ghi khi actor thật sự là `quan_ly_nhan_su`, không ghi khi `quan_ly` làm cùng việc.
- **Ảnh**: dùng Cloudinary, lưu `public_id`, phát URL có chữ ký lúc hiển thị — không lưu URL cố định trong DB.
- **Quy tắc dữ liệu**: tài xế không có tài khoản (không được gán `nguoi_dung_id`); phụ xe bắt buộc có tài khoản `phu_xe` đã tạo trước; tài xế bắt buộc có giấy tờ bằng lái lúc tạo hồ sơ; không đổi `chuc_danh`/tài khoản sau khi tạo hồ sơ.

---

## 4. Trạng thái code hiện tại

### Backend — đã có, đã test qua Swagger/PowerShell

| File | Loại | Ghi chú |
|---|---|---|
| `backend/app/repositories/nhan_su_van_hanh_repository.py` | **Sửa** (chỉ thêm) | Thêm 5 hàm cuối file: `tim_ho_so_day_du`, `danh_sach_ho_so`, `tao_ho_so`, `cap_nhat_ho_so`, `cap_nhat_anh_ho_so` |
| `backend/app/repositories/giay_to_nhan_su_repository.py` | Mới | CRUD giấy tờ + hàm phục vụ job cảnh báo |
| `backend/app/repositories/nhat_ky_quan_ly_nhan_su_repository.py` | Mới | Chỉ `INSERT` (ghi nhật ký) |
| `backend/app/schemas/nhan_su_schema.py` | Mới | Pydantic request/response |
| `backend/app/services/ho_so_nhan_su_service.py` | Mới | Toàn bộ logic nghiệp vụ UC-49 |
| `backend/app/routes/nhan_su.py` | Mới | Router `/quan-ly-nhan-su/...` |
| `backend/app/jobs/canh_bao_giay_to.py` | Mới | Job cảnh báo giấy tờ hết hạn (nhánh kèm theo UC-49) |
| `backend/app/config.py` | **Sửa** (chỉ thêm) | Thêm hằng số `NGUONG_CANH_BAO_GIAY_TO_NGAY = 30` |
| `backend/app/main.py` | **Sửa** (chỉ thêm) | Đăng ký router mới + job mới vào scheduler |

API đã có:
```
GET    /quan-ly-nhan-su/ho-so
GET    /quan-ly-nhan-su/ho-so/{id}
POST   /quan-ly-nhan-su/ho-so
PUT    /quan-ly-nhan-su/ho-so/{id}
POST   /quan-ly-nhan-su/ho-so/{id}/anh
POST   /quan-ly-nhan-su/ho-so/{id}/giay-to/{loai}/anh
```

### Frontend — mới viết, **chưa test qua trình duyệt**

Thư mục mới `frontend/nhan-vien/quan-li-nhan-su/`:
- `api-client.js`, `auth-check.js`, `nav.js` — bản riêng của domain này (nhân bản từ `quan-ly/`, không import chéo).
- `trang-chu.html` — tổng quan: thống kê số nhân sự đang làm/tài xế/phụ xe/đã nghỉ.
- `ho-so.html` — trang chính UC-49: danh sách, tìm kiếm, lọc theo chức danh/trạng thái, modal thêm/sửa hồ sơ kèm giấy tờ + upload ảnh.
- **Dùng chung** `/nhan-vien/quan-ly/style.css` và `/nhan-vien/quan-ly/data-table.js` bằng cách **tham chiếu** (không copy ~4200 dòng CSS) — quyết định thực dụng, đã nói rõ với người dùng.
- **Không sửa** `frontend/nhan-vien/dang-nhap.html` — nghĩa là sau khi đăng nhập, `quan_ly_nhan_su` vẫn chuyển tới trang của `quan_ly` như cũ. Muốn vào trang mới phải tự mở URL `/nhan-vien/quan-li-nhan-su/trang-chu.html` trực tiếp (token trong `localStorage` vẫn dùng được bình thường).

---

## 5. Quy tắc làm việc đã thống nhất với nhóm (áp dụng từ giờ)

1. **Không sửa trực tiếp các file tài liệu chính** (`NGHIEP_VU.md`, `DATABASE.md`...) khi còn là đề xuất — viết nháp riêng, chờ đồng ý. (Quy tắc này đã nới: khi được yêu cầu rõ "viết chính thức" thì sửa thẳng.)
2. **Không sửa file code đã có của người khác trong nhóm** — chỉ được **thêm** trường/hàm/dòng mới vào cuối hoặc vị trí hợp lý; **không đổi** bất cứ dòng/hàm/biến nào đã tồn tại, kể cả khi tiện hơn nếu sửa.
3. Khi cần dữ liệu khác với hàm có sẵn (VD cần thêm cột), **viết hàm mới cùng file**, không chỉnh hàm cũ — kể cả nếu trông dư thừa.
4. `backend/app/main.py` là điểm nối bắt buộc duy nhất để route/job mới chạy được — không có cách nào né được việc thêm dòng vào đây.

---

## 6. Việc còn dang dở / cần làm tiếp

- **Frontend chưa test qua trình duyệt thật** — cần `docker-compose up -d --build` lại (có file mới) rồi mở `ho-so.html`/`trang-chu.html` qua Live Server để kiểm tra.
- **UC-51 (cho nghỉ việc) và UC-52 (xem nhật ký)** — mới có backend UC-49, chưa viết 2 UC còn lại.
- **Chưa có giao diện/API tạo tài khoản `phu_xe`** (UC-36 — thuộc người khác, chưa thấy code) → ô "ID tài khoản phụ xe" trong form hiện phải tự dán UUID thủ công, chưa có danh sách chọn.
- **Chưa viết test tự động** cho `ho_so_nhan_su_service.py` (project có sẵn thư mục `backend/tests/unit` với nhiều test khác).
- **Lỗi hiển thị Swagger UI** với tham số header tùy chọn (`str | None`) — chưa sửa, biết cách né bằng PowerShell/curl.
- **`CONTRIBUTING.md`** vẫn ghi UC-49/51/52 "chưa phân công người" — nên cập nhật khi báo cáo lại với nhóm.
- Ảnh giấy tờ (`giay_to`) hiện **chưa có nút upload riêng trên frontend** (ảnh hồ sơ thì có) — backend đã có sẵn endpoint, chỉ thiếu UI.

---

## 7. Lệnh hay dùng lại

```powershell
# Dựng lại sau khi có file mới
docker-compose up -d --build

# Migrate (yoyo đã nhớ cấu hình trong backend/yoyo.ini)
docker-compose exec backend yoyo apply ./migrations

# Test nhanh API có xác thực (né lỗi Swagger UI)
$login = Invoke-RestMethod -Uri "http://localhost:8000/auth/dang-nhap" -Method Post -ContentType "application/json" -Body '{"email":"...","mat_khau":"..."}'
$token = $login.token
Invoke-RestMethod -Uri "http://localhost:8000/quan-ly-nhan-su/ho-so" -Headers @{ Authorization = "Bearer $token" }
```

---

## 8. Giai đoạn tiếp theo (11/10 → 21/10/2026): hoàn thiện UC-49, bàn mở rộng, chuẩn bị UC-36

### 8.1. Diễn biến chính (tiếp số thứ tự mục 2)

19. **Thêm comment tiếng Việt** cho toàn bộ backend UC-49 (7 file: route, service, schema, job, 3 repository). Chỉ thêm comment, không đổi dòng code.
20. **Bổ sung frontend UC-49**: ô chọn tài khoản phụ xe (thay cho dán UUID), nút upload ảnh giấy tờ (bằng lái, giấy khám), nhãn "còn hạn / sắp hết hạn / đã hết hạn". Backend thêm endpoint `GET /quan-ly-nhan-su/tai-khoan-phu-xe-chua-gan`.
21. **Đổi tên thư mục frontend** thành `frontend/nhan-vien/quan-li-nhan-su/` và cập nhật mọi đường dẫn trang (đường dẫn API backend `/quan-ly-nhan-su/...` giữ nguyên). Sửa **1 giá trị** trong `dang-nhap.html` để `quan_ly_nhan_su` đăng nhập xong vào thẳng trang của mình.
22. **Làm rõ quy tắc làm việc**: được thêm dòng/hàm và đổi giá trị cần thiết; ưu tiên **không đổi tên biến**, rồi **không đổi tên hàm** (nới so với "chỉ được thêm" ở mục 5).
23. **Tạo tài khoản test** trong DB local, không dùng migration: `quanlynhansu@gmail.com` / `Nhansu@123`, vai trò `quan_ly_nhan_su`. Đuôi email `.local` bị API từ chối nên đổi sang `@gmail.com`.
24. **Phân tích thứ bậc role** và quyền quản lý tài khoản/hồ sơ: ai tạo, khóa ai (mục 10.1).
25. **Đề xuất mở rộng "hồ sơ cán bộ văn phòng"** (quầy vé, gửi hàng, điều độ viên; kế toán chỉ xem): bảng riêng, gộp vào UC-49 (không tạo UC-53 vì số đó đã dùng cho "Xem và sửa thông tin cá nhân"), đã ghi vào 5 tài liệu gốc ngày 15/10. Sau khi cân nhắc quy mô hệ thống, **quyết định không làm** vì hồ sơ nhân sự của các vai trò khác thuộc phòng nhân sự và nên lưu ngoài hệ thống (chỉ tài xế/phụ xe ảnh hưởng vận hành). Ngày 21/10 **hoàn tác toàn bộ** phần tài liệu. DB chưa từng có bảng hay migration của phần này (đã kiểm tra cả DB lẫn thư mục migrations); lúc bàn bạc chỉ viết sẵn nội dung SQL trong tin nhắn, chưa tạo file.
26. **Hồ sơ nhân sự và giấy tờ**: không đưa hợp đồng lao động, BHXH, lương, thuế, KPI... vào hệ thống. **Bằng lái chỉ bắt buộc với tài xế**, phụ xe không bắt buộc (code đã đúng; ghi vào UC-49 trong file nháp).
27. **Làm rõ UC-36/37/51/52 trong tài liệu gốc** (đợt 1, đã vào commit #36): UC-36 thêm họ tên + SĐT bắt buộc và đổi "liên kết thư mời" thành mã OTP qua trang Quên mật khẩu; UC-37 không tự khóa chính mình; UC-51 quy tắc ngày nghỉ, lý do bắt buộc, định nghĩa "thiếu người"; UC-52 phân trang. Thiết kế chi tiết ở `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1. Một lần đã bắt đầu viết code UC-36/37/51/52 rồi **hoàn tác theo yêu cầu**, chỉ giữ phần tài liệu.
28. **Hướng dẫn vận hành**: chạy Docker, chạy migration, test trên trình duyệt (Live Server cổng 5500, địa chỉ `localhost:5500` hoặc `127.0.0.1:5500` khớp CORS), cách viết test tự động theo mẫu của nhóm (pytest + monkeypatch, chưa viết).
29. **Commit và push UC-49** (`d49d505`). Nhóm trưởng merge vào `integration/gop-nhanh-thanh-vien` thành commit `70d9368` (#36).
30. **Tạo nhánh UC-36**: `feature/Nghia-uc36-tao-tai-khoan-can-bo`, tạo trực tiếp từ bản mới nhất của `origin/integration/gop-nhanh-thanh-vien`.
31. **Rà soát xem ai đã làm UC-36 chưa** (code hiện tại, mọi nhánh remote, lịch sử git, test, tài liệu): **chưa ai làm**. Chi tiết ở mục 11.
32. **Chốt thiết kế UC-36** (mục 9) và viết `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md`.
33. **Sửa tài liệu cho khớp "điều độ viên không gắn văn phòng"** (đợt 2, chưa commit): `NGHIEP_VU.md` mục 2, mục 8.7 điểm 2, UC-36 bước 1; `UML_DIAGRAMS.md` sơ đồ UC-36; `NHAP_QUAN_LY_NHAN_SU.md` mục 11.1.

### 8.2. Các sai sót đã đính chính trong phiên

- Đọc nhầm tên nhánh `feature/vanh-uc36-38-tai-khoan-can-bo` thành "Vanh đã làm UC-36/37/38". Thực tế nhánh đó là nhánh cũ (30/09) chỉ có thay đổi tài liệu sinh chuyến, không có code tài khoản.
- Mô tả migration của phần mở rộng bị hiểu là đã tạo file. Thực tế chưa tạo file nào.

---

## 9. Quyết định đã chốt cho UC-36 (21/10/2026)

| # | Chốt |
|---|---|
| 1 | Người làm UC-36: Nghĩa (nhánh `feature/Nghia-uc36-tao-tai-khoan-can-bo`) |
| 2 | Ma trận tạo tài khoản **đúng `NGHIEP_VU.md`**: `quan_ly_nhan_su` tạo 4 vai trò vận hành (phụ xe, quầy vé, gửi hàng, điều độ viên); `quan_ly` thêm được `ke_toan`; chỉ `quan_ly` **gốc** tạo `quan_ly` và `quan_ly_nhan_su` |
| 3 | `quan_ly_nhan_su` và `quan_ly` **dùng chung một endpoint**, service quyết định theo vai trò người gọi |
| 4 | **Điều độ viên không gắn văn phòng** (nhóm đã duyệt đề xuất điều độ viên theo tuyến). Văn phòng chỉ bắt buộc với **quầy vé và gửi hàng**, ghi vào `ho_so_can_bo_diem` |
| 5 | Chuỗi hàm `gan_van_phong_can_bo` của phần gửi hàng: **làm UC-36 và đổi văn phòng trước, xóa sau cùng** khi nhóm đồng ý (cập nhật 22/10; trước đó là "giữ trước, xóa sau" hai giai đoạn) |
| 6 | **Đổi văn phòng thuộc UC-36** (nhánh kèm theo), đã ghi vào `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md` 1.3 (cập nhật 22/10; trước đó là "để làm sau"). "Gắn cố định" trong tài liệu cũ chỉ là chưa có chức năng đổi, không phải cấm |
| 7 | Cơ chế mời: tạo tài khoản `mat_khau = NULL` rồi gửi mã OTP, cán bộ đặt mật khẩu ở trang Quên mật khẩu |

Thiết kế kỹ thuật (xem `KE_HOACH_UC36...md`): service/route/repository/schema mới, tên file khớp `ARCHITECTURE.md`; quyền làm dạng bảng tra cứu; **tạo tài khoản và gán văn phòng trong cùng một transaction**; không cần migration; danh sách "vai trò cần văn phòng" là một hằng số duy nhất.

---

## 10. Phân tích đã làm

### 10.1. Thứ bậc role (tài khoản và hồ sơ)

`quan_ly` gốc, rồi `quan_ly`, rồi `quan_ly_nhan_su`, rồi `ke_toan` (khác nhánh), rồi cán bộ vận hành, rồi `khach_hang`. Tài xế không có tài khoản, chỉ có hồ sơ. Nguyên tắc: vai trò càng nhạy cảm (tiền, quyền quản trị) thì càng ít người tạo/khóa được. Quản lý nhân sự **không** tạo/khóa `ke_toan`, `quan_ly`, `quan_ly_nhan_su` khác; không có hồ sơ cho vai trò nào ngoài tài xế/phụ xe.

### 10.2. Phạm vi theo văn phòng

Quầy vé, gửi hàng gắn cố định 1 văn phòng. Kế toán, quản lý, quản lý nhân sự toàn hệ thống (không gắn). Điều độ viên: bỏ gắn văn phòng, chuyển sang theo tuyến. Tài liệu không có khái niệm "chi nhánh chính".

### 10.3. Bảng `ho_so_can_bo_diem`

Tên dễ nhầm: **không phải hồ sơ nhân sự**, chỉ có 2 cột (`nguoi_dung_id`, `van_phong_id`) = "cán bộ làm ở văn phòng nào" ("điểm" = điểm đón/trả). Được đọc ở middleware (lấy `van_phong_id` của người đăng nhập), `routes/gui_hang.py` (giới hạn nhân viên gửi hàng theo văn phòng), tìm điều độ viên/nhân viên gửi hàng của một văn phòng để báo sự cố, hàng tồn. **Không được xóa bảng này**, chỉ có thể thay chuỗi hàm *ghi*.

---

## 11. Kết quả rà soát: UC-36 đã có gì chưa

- **Chưa có** code tạo/khóa tài khoản cán bộ ở bất kỳ nhánh nào. Hàm `INSERT INTO nguoi_dung` duy nhất trong app cố định `'khach_hang'`.
- **Có một chuỗi hàm gần UC-36** (do phần gửi hàng viết để test, commit #26): route `PUT /quan-ly/ho-so-can-bo-diem/{id}` (chỉ `quan_ly`) → `gui_hang_service.gan_van_phong_can_bo` → `nguoi_dung_repository.gan_van_phong`. Chỉ **gán văn phòng cho tài khoản đã có**, không tạo tài khoản; chỉ một nơi gọi; không frontend, không test.
- **Dễ nhầm nhưng không phải UC-36**: `quan-ly/tai-khoan.js` (modal "Tài khoản của tôi", UC-53); script `backend/scripts/seed_phu_xe_demo.py` (chèn tài khoản demo trực tiếp vào DB, không phải API); nhánh `son-dieu-do-vien` (chỉ thêm hàm đọc văn phòng).
- **Phân công**: `CONTRIBUTING.md` giao UC-36/37 cho Người 1 (Trưởng nhóm) → cần báo để tránh làm trùng.
- File lạ `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` (untracked, không do phần Quản lý nhân sự tạo) là đề xuất điều độ viên theo tuyến, mục 6 nói về UC-36/37.

---

## 12. Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| UC-49 (hồ sơ tài xế/phụ xe + cảnh báo giấy tờ) | ✅ Backend + frontend xong, **đã merge vào integration (#36)**. Chưa có test tự động; frontend chưa test kỹ trên trình duyệt |
| UC-36 (tạo tài khoản cán bộ) | 📋 Có kế hoạch + tài liệu, **chưa có code** |
| UC-37, UC-51, UC-52 | 📐 Thiết kế xong (`NHAP...` mục 11.1), chưa code |
| UC-39 (thống kê) | Không thuộc phần Quản lý nhân sự |
| Tài khoản test | `quanlynhansu@gmail.com` trong DB local (mất nếu chạy `docker-compose down -v`) |
| Dữ liệu local | 2 tài khoản không phải khách (admin gốc, QLNS test), 2 hồ sơ tài xế, 3 dòng giấy tờ |

**Chưa commit (nhánh `feature/Nghia-uc36-tao-tai-khoan-can-bo`):** sửa `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `NHAP_QUAN_LY_NHAN_SU.md`; file mới `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md`. File `DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md` không phải của phần này, đừng `git add`.

---

## 13. Việc cần làm tiếp

1. **Báo Trưởng nhóm** về việc làm UC-36 (phân công đang ghi Người 1).
2. Bật Docker, `docker-compose up -d --build`, `yoyo apply` để DB khớp code mới.
3. **Code UC-36** theo thứ tự ở `KE_HOACH...` mục 7: schema, repository, service (kèm unit test), route, đăng ký `main.py`, test tay, frontend `tai-khoan.html` + menu.
4. Sau đó UC-37 (khóa/mở khóa), UC-51 (nghỉ việc), UC-52 (nhật ký).
5. **Đổi văn phòng** (nhánh kèm theo UC-36): `PUT /quan-ly-nhan-su/tai-khoan/{id}/van-phong`, dùng `INSERT ... ON CONFLICT DO UPDATE` để gán được cả tài khoản cũ chưa có văn phòng.
5b. **Sau cùng** (cần người làm gửi hàng đồng ý, ưu tiên để họ tự xóa): xóa chuỗi hàm `gan_van_phong_can_bo` ở 4 file (route + import, schema, service, repository), rồi tìm lại toàn dự án để chắc không còn nơi gọi.
6. Viết test tự động cho `ho_so_nhan_su_service.py`; test frontend UC-49 trên trình duyệt.
7. Commit và PR đợt sửa tài liệu điều độ viên + file kế hoạch.

### Phát hiện khi rà soát lại (22/10/2026)

- Không có phần nào của UC-36 được viết sẵn ở bất kỳ nhánh nào; nhánh `vanh-uc36-38-tai-khoan-can-bo` chỉ là bản cũ của integration.
- **Bẫy**: `dat_lai_mat_khau` không bật `da_xac_nhan` còn `dang_nhap` chặn nếu `da_xac_nhan = false` → tạo tài khoản cán bộ phải đặt `da_xac_nhan = true` ngay lúc INSERT.
- Người làm gửi hàng viết `gan_van_phong_can_bo` (commit `2f80b79`, PR #26) để cấp phạm vi văn phòng cho nhân viên; `KE_HOACH_SUA_GUI_HANG.md` mục P1 kỳ vọng UC-36 gọi nó. Nhân viên chưa có văn phòng bị chặn 403 toàn bộ phần gửi hàng → cần báo họ trước khi xóa.
- Hàm cũ tự `commit()` trên kết nối riêng nên không dùng được trong transaction tạo tài khoản; UC-36 tự viết SQL nhận cursor.

### Câu hỏi cần hỏi nhóm (chưa có trả lời)

- Nhóm gửi hàng có đồng ý để xóa chuỗi `gan_van_phong_can_bo` (ưu tiên họ tự xóa)? Nhóm điều độ viên cũng đã đề xuất bỏ `dieu_do_vien` khỏi hàm này.
- Đổi văn phòng không chặn khi cán bộ còn đơn đang xử lý, không bắt buộc nhập lý do — nhóm có muốn khác không?

- `nhat_ky_admin` mô tả trong `DATABASE.md` nhưng **chưa có migration**: hành động của `quan_ly` (tạo/khóa tài khoản, cho nghỉ việc) chưa có chỗ ghi, và "UC-52: quản lý thấy toàn bộ" thực chất chỉ thấy nhật ký của QLNS.
- Khóa **khách hàng** (UC-37): dùng `dang_hoat_dong` hay `bi_khoa` (no-show)? Đề xuất bản đầu chỉ làm cán bộ.
- Tên vai trò phụ xe: tài liệu ghi `nhan_vien_van_hanh`, DB và code dùng `phu_xe`.
- Mã OTP chỉ sống 1 phút có hợp lý cho thư mời cán bộ không? (Đề xuất giữ vì dùng chung cơ chế Quên mật khẩu.)
- Đổi "liên kết trong thư" thành "mã OTP + trang Quên mật khẩu" là sửa so với spec cũ, nên báo nhóm.
- Các chỗ tài liệu còn nhắc điều độ viên gắn văn phòng (`NGHIEP_VU.md` đoạn "Nguyên tắc xuyên suốt" mục 2 và "Phạm vi xem/gán" UC-44, `DATABASE.md` mục 1.3) thuộc nhóm điều độ viên cập nhật.

---

## 14. Danh sách file đã tạo/sửa trong giai đoạn này

| File | Việc | Đã commit? |
|---|---|---|
| `backend/app/**` (UC-49) | Comment + endpoint tài khoản phụ xe | ✅ (#36) |
| `frontend/nhan-vien/quan-li-nhan-su/**` | Hoàn thiện UC-49, đổi tên thư mục | ✅ (#36) |
| `frontend/nhan-vien/dang-nhap.html` | Đổi 1 giá trị đường dẫn | ✅ (#36) |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md` | Đợt 1: làm rõ UC-36/37/51/52 | ✅ (#36) |
| `NGHIEP_VU.md`, `UML_DIAGRAMS.md` | Đợt 2: điều độ viên không văn phòng | ❌ chưa |
| `NHAP_QUAN_LY_NHAN_SU.md` | Viết lại, thêm mục 11.1, mục 12 "đã cân nhắc, không làm" | Một phần (#36), phần mới ❌ chưa |
| `KE_HOACH_UC36_TAO_TAI_KHOAN_CAN_BO.md` | Mới | ❌ chưa |
| `TOM_TAT_QUAN_LY_NHAN_SU.md` | Thêm mục 8 đến 14 (file này) | ❌ chưa |
