# Kế hoạch: mã nhân viên

> Người làm: Nghĩa (Quản lý nhân sự). Làm **trước UC-51**. Cập nhật: 23/10/2026.
> **Trạng thái (5/11/2026): backend + frontend đã làm xong và đã kiểm tra** (migration áp dụng ở DB local, unit test, API thật, trình duyệt); tài liệu đã đồng bộ; **chưa commit**. Mục 6 ghi các quyết định đã chốt.
> Tài liệu chính (`NGHIEP_VU.md`, `DATABASE.md`, `UML_DIAGRAMS.md`, `ARCHITECTURE.md`) đã sửa 5/11/2026 (mục 4.4).

---

## 1. Mục tiêu và quyết định đã chốt

**Vấn đề:** hệ thống đã có mã hiển thị cho khu vực (`KV001`), điểm đón/trả, tuyến (`T001`), loại xe (`LX001`), chuyến, vé (`VE000001`), nhưng **người thì chỉ có `id` UUID và họ tên** (họ tên không duy nhất). Danh sách đơn, vé quầy, nhật ký, thông báo chỉ hiện tên nên không phân biệt được hai người trùng tên.

**Đã chốt (Nghĩa, 23/10/2026):**

| # | Chốt |
|---|---|
| 1 | Có làm mã nhân viên, làm **trước UC-51** |
| 2 | Mã **tự động** (người dùng không nhập) |
| 3 | Mã = **tiền tố theo vai trò** + **dãy số tự tăng** (phương án B: **không** dùng CCCD) |
| 4 | Điều độ viên dùng tiền tố **`DDV`** |
| 5 | Số thứ tự **4 chữ số** (`PX0001`) |
| 6 | Tài khoản quản lý gốc có mã **`QL0000`**; các quản lý khác bắt đầu từ `QL0001` |
| 7 | Mã sinh **tự động lúc tạo** (tài khoản ở UC-36, hồ sơ tài xế ở UC-49); **không** thêm `CHECK` bắt buộc có mã |

Vì không dùng CCCD nên **không phải thu thêm CCCD** ở UC-36, không đổi quy tắc CCCD của UC-49, và mã **không còn là dữ liệu nhạy cảm** (hiện được ở mọi vai trò).

---

## 2. Hiện trạng đã kiểm tra

| Mục | Hiện có |
|---|---|
| Mã người | **Không có** ở bất kỳ bảng nào |
| Người trong hệ thống | Tài xế: chỉ có hồ sơ `nhan_su_van_hanh`. Phụ xe: có **cả hồ sơ lẫn tài khoản `nguoi_dung`**. Quầy vé, gửi hàng, điều độ viên, kế toán, QLNS, quản lý: chỉ có tài khoản. Khách hàng: ngoài phạm vi |
| Cách sinh mã của nhóm | Từ migration `20261008_1100`: **sinh bằng Python** (`utils/ma_tu_sinh.py` dựng chuỗi, `repositories/ma_repository.py` lấy số từ sequence Postgres), repository tự điền `ma` trong lệnh `INSERT`. Cột `ma` **NOT NULL + UNIQUE** nên quên điền là báo lỗi ngay. Có trigger giữ mã không sửa được. Số không tái sử dụng |
| Đường tạo `nguoi_dung` **trên môi trường thật** | Chỉ có 3: (1) khách hàng đăng ký, `nguoi_dung_repository.py:93`, kể cả đăng ký hộ tại quầy, **không có mã**; (2) **UC-36**, `tai_khoan_can_bo_repository.py:47`, là đường duy nhất tạo cán bộ; (3) tài khoản `quan_ly` gốc, seed trong migration đầu (`DATABASE.md` mục 9). Đã đối chiếu `NGHIEP_VU.md` mục 2 và `DATABASE.md` |
| Đường tạo `nguoi_dung` **chỉ để thử (dev)** | 3 script seed của người khác: `seed_gui_hang_demo.py`, `seed_nhan_vien_quay_ve_demo.py`, `seed_phu_xe_demo.py`. Đầu file ghi rõ chạy trên DB local, không dùng cho production. Chúng tạo tài khoản demo bằng `INSERT` trực tiếp, không đi qua UC-36 |
| Đổi vai trò tài khoản | **Không có code nào** `UPDATE vai_tro` → vai trò cố định sau khi tạo, tiền tố ổn định |
| Chức danh hồ sơ | Không đổi sau khi tạo hồ sơ (quy tắc UC-49) |

---

## 3. Thiết kế đề xuất

### 3.1. Định dạng
`<TIỀN TỐ><số thứ tự 4 chữ số>`, ví dụ `PX0001`, `DDV0012`. Mỗi tiền tố có **dãy số riêng** (đếm riêng từng vai trò, như `KV001`, `T001`). Quá 9999 thì số dài ra (`PX10000`), không bị cắt: đúng cách `utils/ma_tu_sinh.py` đang làm.

| Tiền tố | Ai | Nơi lưu mã | Sequence |
|---|---|---|---|
| `TX` | Tài xế | `nhan_su_van_hanh.ma` | `seq_ma_tai_xe` |
| `PX` | Phụ xe | `nguoi_dung.ma` (hồ sơ dùng lại, không sinh mã thứ hai) | `seq_ma_phu_xe` |
| `QV` | Nhân viên quầy vé | `nguoi_dung.ma` | `seq_ma_quay_ve` |
| `GH` | Nhân viên gửi hàng | `nguoi_dung.ma` | `seq_ma_gui_hang` |
| `DDV` | Điều độ viên | `nguoi_dung.ma` | `seq_ma_dieu_do_vien` |
| `KT` | Kế toán | `nguoi_dung.ma` | `seq_ma_ke_toan` |
| `NS` | Quản lý nhân sự | `nguoi_dung.ma` | `seq_ma_quan_ly_nhan_su` |
| `QL` | Quản lý. Tài khoản **gốc là `QL0000`** (gán cố định trong migration); các quản lý khác lấy từ sequence bắt đầu ở `QL0001` | `nguoi_dung.ma` | `seq_ma_quan_ly` (bắt đầu từ 1) |

Khách hàng không có mã. Mã **chốt lúc tạo, không đổi, không tái sử dụng** (kể cả khi tài khoản bị khóa hoặc người nghỉ việc), cùng quy ước các mã hiện có.

### 3.2. Phụ xe có hai bản ghi
Phụ xe có tài khoản (UC-36) và hồ sơ (UC-49, liên kết với tài khoản đó). Để **một người chỉ có một mã**:
- Mã sinh ở **tài khoản** (`PX...`).
- Hồ sơ phụ xe **không có mã riêng**; API hồ sơ lấy mã từ tài khoản liên kết (JOIN). Phụ xe bắt buộc có tài khoản nên luôn có mã.
- Hồ sơ tài xế có mã riêng `TX...` vì không có tài khoản.
- Ràng buộc: `nhan_su_van_hanh.ma` chỉ có giá trị khi `chuc_danh = 'tai_xe'`.

### 3.3. Sinh mã
- Hàm dựng chuỗi thuần trong `utils/ma_tu_sinh.py`, ví dụ `ma_nhan_vien(tien_to, so_thu_tu)`, unit test được.
- Bảng tiền tố ↔ vai trò và tên sequence đặt ở **một chỗ duy nhất** (hằng số trong `ma_repository.py`, thêm vào `_SEQUENCE`), giống cách các mã khác.
- `tai_khoan_can_bo_repository.tao_tai_khoan` lấy số từ sequence **trong cùng transaction** với `INSERT nguoi_dung` rồi điền `ma` (cùng nơi đã tạo tài khoản + gán văn phòng).
- Tạo hồ sơ tài xế ở `nhan_su_van_hanh_repository.tao_ho_so` làm tương tự với `TX`.
- Dùng trigger giữ mã không sửa được (như `giu_nguyen_ma`) cho `nguoi_dung.ma` và `nhan_su_van_hanh.ma`.

### 3.4. Hiển thị và tìm kiếm
- API trả `ma` ở: danh sách tài khoản cán bộ, danh sách và chi tiết hồ sơ, ô chọn tài khoản phụ xe chưa gán.
- Giao diện: thêm cột "Mã" ở `tai-khoan.html` và `ho-so.html`; ô tìm kiếm tìm được cả theo mã.
- Việc hiện mã ở nơi khác (đơn gửi hàng, vé quầy, thông báo, nhật ký) là của các nhóm tương ứng; mình chỉ cung cấp `ma` trong bảng.

---

## 4. Những phần cần sửa

Kết quả rà soát toàn hệ thống (23/10/2026). Đánh dấu ☐ → ✅ khi làm xong. Chi tiết kỹ thuật từng điểm ở mục 6.

### 4.1. Code của mình (bắt buộc)

| | Nơi | Sửa gì |
|---|---|---|
| ✅ | **Migration mới** (tên phải sau `20261023_1000_...`) | Thêm cột `nguoi_dung.ma`, `nhan_su_van_hanh.ma`; 8 sequence; **điền mã cho dữ liệu cũ trước** (gốc cố định `QL0000`), **sau đó** mới tạo trigger giữ mã (mục 6.7, 6.10); `CHECK` định dạng (mục 6.8); chỉ mục UNIQUE một phần |
| ✅ | `repositories/tai_khoan_can_bo_repository.py` | `tao_tai_khoan`: lấy số từ sequence trong cùng transaction rồi điền `ma` (chữ ký hàm không đổi); trả `ma` trong kết quả. `danh_sach_tai_khoan_can_bo`: thêm cột `nd.ma` và tìm theo mã (`ILIKE`) |
| ✅ | `services/tai_khoan_can_bo_service.py` | Truyền `ma` ra kết quả; thông báo khóa phụ xe ghi kèm mã (tùy chọn) |
| ✅ | `schemas/tai_khoan_can_bo_schema.py` | Thêm `ma` vào `TaoTaiKhoanCanBoResponse` và `TaiKhoanCanBoResponse` |
| ✅ | `repositories/nhan_su_van_hanh_repository.py` (hàm UC-49 mình đã thêm) | `tao_ho_so`: tài xế sinh mã `TX`. `tim_ho_so_day_du`, `danh_sach_ho_so`, `danh_sach_tai_khoan_phu_xe_chua_gan`: thêm cột mã, dùng `COALESCE(nhan_su.ma, nguoi_dung.ma)` (mục 6.11) |
| ✅ | `schemas/nhan_su_schema.py` | Thêm `ma` vào `HoSoTomTatResponse`, `HoSoNhanSuResponse`, `TaiKhoanPhuXeResponse` |
| ✅ | `services/ho_so_nhan_su_service.py` | Không cần sửa: `ma` đi theo dữ liệu repository trả về (đã kiểm tra bằng test và API thật) |
| ✅ | Test | `test_tai_khoan_can_bo_service.py`: thêm `ma` vào dict giả, thêm test điền đúng tiền tố theo vai trò. `test_ma_tu_sinh.py`: test hàm dựng mã. Chưa có test cho `ho_so_nhan_su_service` nên thêm test mới cho mã tài xế và phụ xe |

### 4.2. File dùng chung của nhóm (chỉ **thêm**, không sửa dòng cũ)

| | File | Thêm gì |
|---|---|---|
| ✅ | `repositories/ma_repository.py` | 8 khóa mới trong `_SEQUENCE` |
| ✅ | `utils/ma_tu_sinh.py` | Hàm dựng mã nhân viên (hàm thuần, bốn chữ số, không cắt khi quá 9999) |

### 4.3. Giao diện (`frontend/nhan-vien/quan-li-nhan-su/`)

| | Trang | Sửa gì |
|---|---|---|
| ✅ | `tai-khoan.html` | Thêm cột "Mã" vào bảng; thêm mã vào ô tìm kiếm phía frontend (hiện chỉ tìm theo họ tên, email, SĐT); hộp thoại "Đã tạo tài khoản" hiện mã mới |
| ✅ | `ho-so.html` | Thêm cột "Mã"; thêm mã vào ô lọc (hiện chỉ lọc theo họ tên và SĐT); ô chọn tài khoản phụ xe hiện mã cạnh tên |

### 4.4. Tài liệu

| | File | Sửa gì |
|---|---|---|
| ✅ | `DATABASE.md` | Mục 1.1 (`nguoi_dung.ma`), 1.4 (`nhan_su_van_hanh.ma`), mục 0 (danh sách mã), **mục 10** (hiện chỉ nói về 6 mã khu vực / điểm / tuyến / loại xe / chuyến / vé; thêm đoạn mã nhân viên) |
| ✅ | `NGHIEP_VU.md` | UC-36 (hệ thống sinh mã khi tạo), UC-49 (tài xế `TX`, phụ xe dùng mã tài khoản), UC-51 và UC-52 (hiển thị mã), mục 2 (mô tả mã trong bảng vai trò) |
| ✅ | `UML_DIAGRAMS.md` | Class `NguoiDung` (thêm `ma`) và `NhanSuVanHanh` (khoảng dòng 1450 trở đi) |
| ✅ | `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md` | Thêm dòng về migration mới, file dùng chung đã thêm, 3 script demo (xem mục 5) |
| ✅ | `BAO_CAO_CONG_VIEC_QUAN_LY_NHAN_SU.md`, `TOM_TAT_QUAN_LY_NHAN_SU.md` | Ghi lại công việc |
| ✅ | `ARCHITECTURE.md`, `NHAP_QUAN_LY_NHAN_SU.md`, `KE_HOACH_UC36/37` | Đồng bộ cây thư mục, trạng thái UC-36 / UC-37 (5/11/2026) |

Chỉ sửa tài liệu chính ở bước cuối, cùng lúc với code.

### 4.5. Không sửa, nhưng nên báo người khác

| Nơi | Vì sao |
|---|---|
| Chỗ chọn tài xế / phụ xe để gán biên chế xe (UC-35): `danh_sach_dang_lam`, `danh_sach_bien_che_theo_xe` trong `nhan_su_van_hanh_repository.py` | Đây là nơi mã hữu ích nhất khi hai người trùng tên. Hàm của Trưởng nhóm; mình có thể thêm cột `ma` vì chỉ thêm, nhưng nên hỏi trước |
| Màn hình đơn gửi hàng, vé quầy (`don_hang_repository`, `quay_ve_repository`, `ve_thanh_toan_repository`, `ve_lock_repository`, `don_hang_schema`) | Hiện chỉ có tên (`nhan_vien_ban`, `ten_nhan_vien_huy`...). Hiện thêm mã hay không do nhóm đó quyết định |
| 3 script seed demo (`seed_gui_hang_demo.py`, `seed_nhan_vien_quay_ve_demo.py`, `seed_phu_xe_demo.py`) | Chèn thẳng vào bảng nên tài khoản demo **mới** không có mã; chỉ ảnh hưởng DB local |
| Phản hồi đăng nhập / `NguoiDungHienTai` / thanh trên cùng | Hiện mã ở đó phải sửa code xác thực dùng chung; **không làm** trong đợt này |

### 4.6. Thứ tự làm

1. Migration (kèm điền mã cũ, trigger, `CHECK`), chạy `yoyo apply`.
2. Hàm dựng mã + `ma_repository` + unit test.
3. UC-36: repository, service, schema, test.
4. UC-49: repository, schema, service, test.
5. Frontend (`tai-khoan.html`, `ho-so.html`).
6. Test tay trên API và trình duyệt.
7. Sửa tài liệu và ghi vào `TAC_DONG_DEN_NGUOI_KHAC_QUAN_LY_NHAN_SU.md`.
8. Commit, push, báo nhóm (cả nhóm phải chạy `yoyo apply ./migrations`).

---

## 5. Ảnh hưởng đến người khác (sẽ ghi vào file tác động)

- **Cả nhóm:** migration thêm cột vào bảng dùng chung `nguoi_dung` và `nhan_su_van_hanh` → sau khi pull phải chạy `yoyo apply ./migrations`.
- **3 script seed demo của người khác** (`seed_gui_hang_demo.py`, `seed_nhan_vien_quay_ve_demo.py`, `seed_phu_xe_demo.py`): chỉ ảnh hưởng DB local của dev. Script này chèn thẳng vào bảng, không qua UC-36 nên tài khoản demo **mới** do script tạo sẽ không có mã (tài khoản demo đã có được migration điền mã). Chỉ là dữ liệu thử, không ảnh hưởng hệ thống thật; vẫn nên báo cho chủ script. Nếu muốn có mã thì họ gọi hàm `ma_repository` mình cung cấp.
- **Các nhóm hiển thị tên nhân viên** (gửi hàng, quầy vé, điều độ viên, phụ xe): có thể hiện thêm mã cạnh tên (`nhan_vien_ban`, `ten_nhan_vien_huy`, `ten_nguoi_thuc_hien`...). Mình chỉ cung cấp `ma`.
- Mã **không nhạy cảm**: không thay đổi quy tắc dữ liệu CCCD hiện có.

---

## 6. Quyết định chi tiết và điểm cần lưu ý

### 6.1. Cột `ma` và việc có bắt buộc hay không (đã chốt)
Mã **sinh tự động lúc tạo**, nên không cần `CHECK` bắt buộc có mã và không cần cơ chế "cấp bù". Cột `ma` vẫn **cho phép trống ở cấp bảng** vì cấu trúc dữ liệu, không phải đường lui:
- `nguoi_dung`: khách hàng không có mã.
- `nhan_su_van_hanh`: phụ xe không có mã riêng (dùng mã của tài khoản), chỉ tài xế có.

Đường tạo cán bộ trên môi trường thật chỉ có UC-36 (và tài khoản gốc seed trong migration), cả hai đều tự điền mã. 3 script seed demo của người khác chèn thẳng nên không có mã; chỉ ảnh hưởng DB local (mục 5).

### 6.2. Số chữ số (đã chốt)
4 chữ số: `PX0001`. Quá 9999 thì số dài ra, không bị cắt.

### 6.3. Tài khoản gốc (đã chốt)
Tài khoản quản lý gốc là **`QL0000`**, đặt cố định trong migration. Sequence `seq_ma_quan_ly` bắt đầu từ 1, nên quản lý đầu tiên tạo thêm là `QL0001`. Tài khoản test và dữ liệu cũ khác được cấp mã theo thứ tự `ngay_tao` của từng vai trò.

### 6.4. Đổi vai trò trong tương lai
Hiện không có chức năng đổi vai trò tài khoản. Nếu sau này có (ví dụ thăng điều độ viên lên quản lý) thì mã cũ giữ nguyên tiền tố cũ hay cấp mã mới? Chưa cần quyết định ngay; ghi lại để nhóm biết.

### 6.5. Nghỉ việc và khóa
Mã giữ nguyên khi khóa tài khoản hay cho nghỉ việc, và **không cấp lại** cho người khác (sequence). UC-51 và UC-52 nên hiển thị mã cùng họ tên.

### 6.6. Tài khoản phụ xe tạo trước, hồ sơ tạo sau
Mã của phụ xe sinh từ lúc tạo tài khoản (UC-36), tức có trước hồ sơ. Không ảnh hưởng gì, nhưng trong danh sách "tài khoản phụ xe chưa gán hồ sơ" cũng cần hiện mã.

---

### 6.7. Trigger giữ mã: không dùng nguyên `giu_nguyen_ma()`
Hàm `giu_nguyen_ma()` hiện có đặt `NEW.ma := OLD.ma` cho **mọi** lần `UPDATE`. Dùng nguyên cho `nguoi_dung` / `nhan_su_van_hanh` gây hai vấn đề:
1. Nếu trigger tạo **trước** lệnh `UPDATE` điền mã cũ trong migration thì chính lệnh điền mã bị hủy (mã vẫn NULL). Trong migration phải điền mã **trước**, tạo trigger **sau**.
2. Tài khoản tạo ra không có mã (do script demo, mục 5) sẽ **không bao giờ điền bù được** vì `OLD.ma` là NULL bị ghi lại.

Đề xuất: viết hàm riêng `giu_ma_nhan_vien()` chỉ giữ khi mã **đã có** (`IF OLD.ma IS NOT NULL THEN NEW.ma := OLD.ma`). Mã cấp một lần rồi không sửa được, nhưng người chưa có mã vẫn điền được sau.

### 6.8. Ràng buộc định dạng (khác với bắt buộc có mã)
Không bắt buộc có mã, nhưng **nếu có** thì phải đúng tiền tố của vai trò, tránh sai do lỗi code. Đề xuất `CHECK` ở `nguoi_dung` (theo `vai_tro`: `phu_xe` → `^PX[0-9]{4,}$`, `nhan_vien_quay_ve` → `^QV...`, `dieu_do_vien` → `^DDV...`...; `khach_hang` → phải NULL) và ở `nhan_su_van_hanh` (`ma` chỉ có khi `chuc_danh = 'tai_xe'`, dạng `^TX[0-9]{4,}$`). Cộng chỉ mục UNIQUE một phần.

### 6.9. Sequence có thể bị "cháy" số
Số lấy từ sequence (`nextval`) trong transaction tạo tài khoản. Nếu transaction hỏng sau đó (ví dụ trùng email lọt qua bước kiểm tra), số đó mất. Mã sẽ có chỗ trống (`PX0003` rồi `PX0005`). Chấp nhận được (đúng như các mã hiện có: "không tái sử dụng"), chỉ cần biết để không coi là lỗi.

### 6.10. Thứ tự điền mã dữ liệu cũ
- `nguoi_dung` có `ngay_tao` nên điền theo `(ngay_tao, id)`.
- `nhan_su_van_hanh` **không có `ngay_tao`**, chỉ có `ngay_vao_lam` (kiểu ngày, hay trùng). Điền tài xế cũ theo `(ngay_vao_lam, id)`; thứ tự giữa những người cùng ngày là tùy ý nhưng ổn định. Không ảnh hưởng nghiệp vụ.
- Tên migration phải sau `20261023_1000_...` (file mới nhất hiện tại).

### 6.11. Hồ sơ phụ xe không có tài khoản (dữ liệu cũ)
DB chỉ cấm **tài xế** có tài khoản; việc "phụ xe bắt buộc có tài khoản" chỉ do service kiểm tra. Hồ sơ phụ xe cũ không có tài khoản (nếu có) sẽ không lấy được mã khi JOIN. Hiển thị "—". Truy vấn dùng `COALESCE(nhan_su_van_hanh.ma, nguoi_dung.ma)` nên hồ sơ nào cũng có một cột `ma` thống nhất.

### 6.12. Các chỗ cần sửa nhưng dễ bỏ sót
- **Tìm kiếm:** danh sách tài khoản có tìm ở **hai nơi** (backend `ILIKE` ở `danh_sach_tai_khoan_can_bo`, và frontend `boDau(...)` ở `tai-khoan.html`); danh sách hồ sơ lọc phía frontend ở `ho-so.html`. Thêm `ma` vào cả ba.
- **Test UC-36:** repository tự điền mã bên trong `tao_tai_khoan` nên **chữ ký hàm không đổi**, các mock `tao(...)` giữ nguyên. Chỉ cần thêm `ma` vào dict giả trả về, vì response sẽ có `ma`.
- **File dùng chung của nhóm:** thêm vào `ma_repository.py` (8 sequence) và `utils/ma_tu_sinh.py` (hàm dựng mã); cả hai là file chung nên chỉ **thêm**, không sửa dòng cũ.
- **Thông báo:** các thông báo hiện dùng họ tên (khóa phụ xe, giấy tờ hết hạn); nên thêm mã vào nội dung cho dễ phân biệt. Tùy chọn.

### 6.12b. Phát hiện sau khi làm (5/11/2026)
- **`ELSE false` trong `CHECK nguoi_dung_ma_hop_le`:** thêm vai trò mới vào `nguoi_dung` thì mọi `INSERT` của vai trò đó bị từ chối (kể cả `ma` trống) cho tới khi sửa `CHECK`. Đã ghi ở `DATABASE.md` mục 10.2. Có thể đổi thành `ELSE ma IS NULL` cho dễ bảo trì (cần gỡ và áp dụng lại migration trên DB local vì chưa commit).
- **Nhật ký:** ✅ đã sửa 5/11 — UC-36, UC-37, UC-49 đều ghi: `quan_ly` → `nhat_ky_admin`, QLNS → `nhat_ky_quan_ly_nhan_su`.
- **Hồ sơ phụ xe với tài khoản đã khóa:** backend cho qua (201) dù ô chọn trên giao diện không liệt kê.

### 6.13. Ngoài phạm vi (ghi để không quên)
- **Đăng nhập / `NguoiDungHienTai`** chỉ có `id`, `vai_tro`, `van_phong_id`; thanh trên cùng lấy tên từ `localStorage`. Hiện mã ở đó phải sửa phản hồi đăng nhập (code xác thực dùng chung), nên **không làm** trong đợt này.
- **Các màn hình của nhóm khác** (đơn gửi hàng, vé quầy, phụ xe, điều độ viên) hiển thị tên nhân viên: họ tự quyết định hiện thêm mã.
- **Chưa có chức năng đổi vai trò** nên chưa cần quyết định chuyện đổi tiền tố (mục 6.4).
