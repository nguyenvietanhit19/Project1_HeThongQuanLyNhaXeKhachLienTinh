# Tóm tắt phiên làm việc — Quản lý nhân sự (UC-49)

> File ghi lại quá trình làm việc, không phải tài liệu nghiệp vụ chính thức. Nghiệp vụ chính thức nằm ở `NGHIEP_VU.md`, `UML_DIAGRAMS.md`, `DATABASE.md`, `ARCHITECTURE.md`. Tổng hợp dễ đọc riêng cho phần quản lý nhân sự nằm ở [`NHAP_QUAN_LY_NHAN_SU.md`](NHAP_QUAN_LY_NHAN_SU.md).

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
