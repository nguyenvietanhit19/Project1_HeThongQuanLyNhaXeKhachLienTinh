# Nghiệp vụ hệ thống — Quản lý Nhà xe Khách

Tài liệu này mô tả đầy đủ nghiệp vụ, vai trò, và luồng hoạt động (kèm ngoại lệ) của hệ thống. Đọc cùng `ARCHITECTURE.md` (chiến lược kỹ thuật — **cần cập nhật lại** cho khớp domain mới, xem ghi chú cuối file) — file này tập trung vào **nghiệp vụ**, không phải công nghệ.

> Đổi đề tài từ "Báo cáo sự cố giao thông cộng đồng" sang **quản lý nhà xe khách liên tỉnh** (mô hình 1 doanh nghiệp vận tải duy nhất, kiểu Phương Trang/FUTA, Hà Sơn — không phải nền tảng tổng hợp nhiều nhà xe). Giữ nguyên công nghệ: FastAPI + raw SQL + PostgreSQL + WebSocket, kiến trúc 3 lớp Route → Service → Repository.

---

## 1. Bài toán tổng quan

Một nhà xe khách liên tỉnh vận hành nhiều **tuyến cố định** (VD: Hà Nội – Đà Nẵng, TP.HCM – Đà Lạt) giữa các bến của chính hãng, chạy nhiều **chuyến/ngày** theo lịch, mỗi chuyến dùng 1 xe cụ thể với tài xế + phụ xe cụ thể. Khách hàng đặt vé online chọn ghế theo sơ đồ thật của xe, hoặc mua trực tiếp tại quầy. Bài toán cốt lõi hệ thống phải giải quyết:

1. **Không bán trùng ghế** khi nhiều khách cùng thao tác một lúc (race condition khi đặt vé).
2. **Không xếp chồng lịch** xe/tài xế/phụ xe giữa các chuyến, và **vị trí xe phải liên tục** giữa 2 chuyến kế tiếp (xe chạy A→B thì chuyến sau chỉ có thể xuất phát từ B).
3. **Bán vé theo chặng trên cùng 1 chuyến** — 1 chuyến A→C thật ra đi qua nhiều điểm đón/trả trung gian (VD A→B→C); phải bán được vé A→C, A→B, và B→C **trên cùng những chỗ ngồi**, miễn hành trình của 2 vé không giẫm lên nhau trên xe.
4. **Xử lý phát sinh vận hành thực tế**: xe hỏng giữa đường, xe hỏng trước giờ chạy, tài xế nghỉ đột xuất, khách không lên xe (no-show). **Chuyến đã lên lịch luôn chạy, không hủy vì lý do ít khách** dù chỉ bán được 1 vé hay không vé nào — đảm bảo uy tín, khách đặt vé luôn tin tưởng chuyến sẽ chạy đúng giờ. **Kể cả khi xe hỏng trước giờ chạy hoặc giữa đường do lỗi nhà xe mà chưa xử lý được kịp, chuyến cũng chỉ hoãn/chờ để tiếp tục tìm xe, LUÔN tìm được cuối cùng, không bao giờ hủy toàn bộ** (mục 3.3, mục 4) — vé được xem như 1 cam kết chắc chắn với khách, đặc biệt quan trọng vào dịp cao điểm khi khách không còn lựa chọn nào khác (nhà xe khác cũng hết vé) nếu bị hủy hẳn. Chỉ **sự cố khách quan giữa đường** (thiên tai, sạt lở...) mới có khả năng thực sự không thể hoàn thành (mục 4).
5. **Tiền**: giữ chỗ có thời hạn trước khi thanh toán (hủy tự do nếu chưa trả tiền), giá vé tính theo cặp điểm đi/điểm đến (không đổi theo điểm đón/trả cụ thể), **vé đã thanh toán không hủy/không đổi để lấy lại tiền** — chỉ hoàn 100% trong 3 trường hợp ngoại lệ: chuyến hoãn trước giờ chạy, chuyến gặp sự cố do lỗi nhà xe giữa đường, hoặc sự cố khách quan giữa đường thực sự không thể hoàn thành (mục 7).

---

## 2. Tổng quan vai trò

| Vai trò | Cách có tài khoản | Mô tả ngắn |
|---|---|---|
| `khach_hang` | Tự đăng ký công khai bằng **email + mật khẩu + họ tên + SĐT**, xác nhận qua mã OTP gửi email (mục 2.1), **hoặc mua tại quầy không cần tài khoản** (vé vãng lai gắn SĐT) | Tìm chuyến, đặt vé, thanh toán, theo dõi vé, hủy giữ chỗ trước khi thanh toán |
| `nhan_vien_van_hanh` | `chuc_danh = phu_xe`: được **quản lý** tạo tài khoản trực tiếp. `chuc_danh = tai_xe`: chỉ là hồ sơ trong biên chế xe (`xe_nhan_su`, mục 3.2), **không có tài khoản** | Phụ xe: soát vé/hỗ trợ hành khách, chất/dỡ hàng gửi (mục 10), và thay tài xế xác nhận mọi mốc trạng thái chuyến (mục 8.2). Tài xế: chỉ lái xe, không thao tác hệ thống (mục 8.3) |
| `nhan_vien_quay_ve` | Được **quản lý** tạo trực tiếp, gắn cố định 1 văn phòng | Bán vé tại quầy/qua hotline, in vé cứng cho khách đặt online/hotline |
| `nhan_vien_gui_hang` | Được **quản lý** tạo trực tiếp, gắn cố định 1 văn phòng | Nhận/gửi hàng, tính cước, giao hàng cho người nhận, thu COD (mục 10) — tách riêng khỏi bán vé hành khách |
| `dieu_do_vien` | Được **quản lý** tạo trực tiếp, gắn cố định 1 văn phòng (nơi xuất phát) | Gán xe cho các chuyến đã được hệ thống tự sinh sẵn từ lịch chạy định kỳ, xử lý phát sinh vận hành |
| `ke_toan` | Được **quản lý** tạo trực tiếp, **không gắn văn phòng nào** (phạm vi toàn hệ thống, giống `quan_ly`) | Xử lý hoàn tiền cho khách trả tiền mặt (mục 7) — trường hợp không tự động hoàn được qua cổng thanh toán. Không bán vé, không vận hành xe |
| `quan_ly_nhan_su` | Được **quản lý gốc** tạo trực tiếp, **không gắn văn phòng nào** (phạm vi toàn hệ thống) | Tạo/khóa/mở khóa tài khoản cho `nhan_vien_van_hanh` (phụ xe), `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien` — **không** quản lý tài khoản `ke_toan`, `quan_ly`, hay `quan_ly_nhan_su` khác (mục 8.9). Xem thống kê toàn hệ thống. Không có quyền nghiệp vụ nào khác (tuyến, giá, xe, khuyến mãi) |
| `quan_ly` | Tài khoản **gốc** (`la_tai_khoan_goc = true`), seed lúc khởi tạo hệ thống — **không thể bị khóa bởi bất kỳ ai**, và là `quan_ly` **duy nhất** tạo thêm được `quan_ly` khác hoặc `quan_ly_nhan_su`. Các `quan_ly` tạo thêm sau (không phải gốc) toàn quyền nghiệp vụ ngang tài khoản gốc, trừ 2 việc trên | Toàn quyền: tuyến, giá, đội xe, nhân sự, khuyến mãi, thống kê toàn hệ thống |

**Nguyên tắc xuyên suốt**: cán bộ (nhân viên vận hành, nhân viên quầy vé, nhân viên gửi hàng, điều độ viên, kế toán, quản lý, quản lý nhân sự) luôn được **cấp tài khoản** qua cơ chế mời (email + vai trò, tự đặt mật khẩu lần đầu) — không ai tự đăng ký rồi được thăng cấp; chỉ `khach_hang` tự đăng ký công khai. Người cấp cụ thể theo từng vai trò: `quan_ly` (bất kỳ, gốc hay không) cấp cho `nhan_vien_van_hanh`/`nhan_vien_quay_ve`/`nhan_vien_gui_hang`/`dieu_do_vien`/`ke_toan`; `quan_ly_nhan_su` cũng cấp được cho 4 vai trò đầu (không `ke_toan`); riêng tài khoản `quan_ly` mới và `quan_ly_nhan_su` **chỉ `quan_ly` gốc** mới tạo được — tránh trường hợp 1 tài khoản cấp cao bị lộ vẫn tự mint thêm tài khoản ngang hàng (mục 8.9). Khác với bản trước: đây là **1 công ty duy nhất** (không chia theo tỉnh/thành hành chính) nên `quan_ly`/`quan_ly_nhan_su` thấy **toàn bộ hệ thống**, còn `dieu_do_vien`/`nhan_vien_quay_ve`/`nhan_vien_gui_hang` bị giới hạn theo **điểm đón/trả** họ được gán (không phải theo tỉnh) — riêng `ke_toan` cũng thấy toàn bộ hệ thống vì hoàn tiền có thể phát sinh ở bất kỳ chuyến nào.

### 2.1. Đăng ký/đăng nhập của khách hàng — kế thừa cơ chế OTP qua email của bản trước

Giữ nguyên cơ chế xác thực bằng **email** (không phải SĐT) từ bản v1 (`GiaoThongAnToan_API/routes/auth.py` + `quen_mat_khau.py`) — đã chạy ổn định, gửi qua Gmail SMTP (miễn phí, không phát sinh chi phí như SMS), chỉ bổ sung thêm **SĐT + họ tên bắt buộc** lúc đăng ký cho đúng nhu cầu nghiệp vụ mới (nhân viên quầy vé tra cứu theo SĐT — mục 8.4; liên hệ khách khi cần):

1. **Gửi mã đăng ký**: khách nhập **email + mật khẩu + họ tên + SĐT** → hệ thống validate, tạo bản ghi tài khoản ở trạng thái **chưa kích hoạt**, sinh mã OTP 6 số ngẫu nhiên, lưu kèm hạn (**1 phút**, theo đúng thay đổi gần nhất của nhóm ở bản trước — ngắn vì gửi lại qua email gần như tức thời, không như SMS), gửi qua email (Gmail SMTP, tái dùng nguyên `email_service.py` không đổi gì).
2. **Xác nhận mã**: khách nhập mã OTP → đúng & còn hạn → kích hoạt tài khoản. Sai hoặc hết hạn → báo lỗi, cho phép yêu cầu gửi lại (không giới hạn số lần gửi lại về mặt nghiệp vụ, nhưng nên có rate limit chặn spam ở tầng kỹ thuật — checklist bảo mật, `ARCHITECTURE.md`).
3. **Đăng nhập**: email + mật khẩu (so khớp hash) → JWT — **không cần OTP mỗi lần**, chỉ cần đúng lúc đăng ký và quên mật khẩu.
4. **Quên mật khẩu**: gửi OTP qua email tương tự (hạn 1 phút) → xác nhận mã → đặt mật khẩu mới. Giữ nguyên chi tiết bảo mật hay của bản trước: nếu email không tồn tại, vẫn trả về "đã gửi mã nếu tồn tại" thay vì báo lỗi rõ ràng — tránh lộ thông tin email nào đã đăng ký trong hệ thống (chống dò quét danh sách khách hàng).
5. **Đổi mật khẩu khi đã đăng nhập**: mật khẩu cũ + mật khẩu mới, không cần OTP (đã xác thực qua JWT).
6. **SĐT không dùng để đăng nhập/xác thực** — chỉ là thông tin hồ sơ bắt buộc, phục vụ tra cứu tại quầy (mã đặt chỗ/SĐT, mục 8.4) và liên hệ khi cần, không cần xác minh riêng qua SMS.

---

## 3. Mô hình tổ chức nền tảng

### 3.1. Đúng 2 tầng địa điểm: điểm đi/đến chứa điểm đón/trả

Toàn hệ thống chỉ có **2 tầng địa điểm**, không hơn:

- **Điểm đi / Điểm đến** (bảng `khu_vuc`) — tầng thô, dùng để **tìm kiếm**. Bản thân 1 `khu_vuc` **không phải 1 địa điểm cụ thể để đón/trả khách** — nó là 1 vùng gộp nhiều địa điểm gần nhau (VD "Lào Cai" gồm TP Lào Cai, Bến Đền, Xuân Giao, Phố Lu). **Vai trò đi/đến mang tính đối xứng, không cố định theo từng `khu_vuc`**: 1 `khu_vuc` là "điểm đi" hay "điểm đến" hoàn toàn phụ thuộc chiều của `tuyen` đang xét (VD "Hà Nội" là điểm đi của tuyến Hà Nội→Sapa nhưng là điểm đến của tuyến Sapa→Hà Nội) — không có cột nào đánh dấu cố định 1 chiều cho `khu_vuc`. 1 chuyến giữa 2 tỉnh thực tế đi qua **nhiều điểm đi/đến khác nhau dọc đường** (không chỉ đúng 2 đầu tuyến) — VD chuyến "Yên Nghĩa – Sapa" đi qua điểm "Hà Nội", rồi điểm "Lào Cai (TP Lào Cai, Bến Đền, Xuân Giao, Phố Lu)", rồi điểm "Sapa, Lào Cai". Cùng 1 tỉnh có thể có **nhiều điểm tách biệt** (quan sát thực tế từ app Futa/Hà Sơn: tỉnh Lào Cai có ít nhất 3 điểm riêng ở trên, vì chúng ở xa nhau, không đi chung 1 đoạn đường).
- **Điểm đón / Điểm trả** (bảng `diem_don_tra`) — tầng chi tiết, **nằm trong** 1 điểm đi/đến (`khu_vuc_id`), là địa chỉ cụ thể **xe khách thật sự đi qua** — không có điểm ảo/điểm hẹn trung chuyển nào khác. Không có bảng `ben_xe` riêng — "văn phòng" chỉ là 1 loại điểm đón/trả cụ thể (`loai = 'van_phong'`), tách riêng ra sẽ trùng lặp dữ liệu.

`diem_don_tra` có **2 loại**, phân biệt bởi việc có được dùng làm điểm đón hay không:

- **`van_phong`**: có quầy vé + nhân viên (nơi `nhan_vien_quay_ve`/`nhan_vien_gui_hang`/`dieu_do_vien` có thể gắn cố định) — nơi khách **lấy vé cứng / gửi-nhận hàng**, cũng thường là nơi xe xuất phát/kết thúc/đỗ qua đêm. **Trung bình mỗi `khu_vuc` chỉ có đúng 1 văn phòng** (không phải ràng buộc cứng trong DB — chỉ là thực tế phổ biến; 1 `khu_vuc` chỉ là điểm trung gian tuyến đi ngang qua có thể không có văn phòng nào). Hợp lệ làm **cả điểm đón lẫn điểm trả**. `xe.diem_goc_id` và 2 đầu (điểm đầu tiên/cuối cùng) của mọi `tuyen` bắt buộc phải là `van_phong` (mục dưới).
- **`diem_dung`**: điểm dừng dọc đường xe thật sự đi qua nhưng **không có quầy vé/nhân viên** (trạm nghỉ, cây xăng, hoặc 1 điểm tiện tuyến để trả khách trước khi xe chạy tiếp về văn phòng) — **chỉ hợp lệ làm điểm trả, không hợp lệ làm điểm đón** (khách không thể lấy vé cứng ở đây — mục 8.1 điểm 5).

**Điểm đón luôn phải là `van_phong`** (vì vé cứng bắt buộc lấy tại văn phòng trước khi lên xe — mục 8.1); **điểm trả có thể là `van_phong` hoặc `diem_dung`** — khớp đúng quan sát thực tế: nhiều chuyến trả khách dọc đường tại các điểm tiện tuyến trước khi xe chạy tiếp về văn phòng cuối cùng.

- `tuyen`: 1 hành trình cố định **1 chiều** gồm **nhiều điểm đón/trả có thứ tự** (`van_phong` lẫn `diem_dung`), mỗi điểm thuộc 1 điểm đi/đến (`khu_vuc`) bất kỳ (không nhất thiết đầu/cuối tuyến mới có — tuyến có thể chạy xuyên qua nhiều điểm đi/đến dọc đường, ví dụ ở trên). Quản lý qua bảng trung gian `tuyen_diem_don_tra(tuyen_id, diem_don_tra_id, thu_tu, thoi_gian_du_kien_phut)` — chứa **mọi** điểm xe thực sự đi qua theo đúng thứ tự (không còn khái niệm điểm hẹn trung chuyển cần loại trừ); điểm đầu tiên và cuối cùng (`thu_tu` nhỏ/lớn nhất) bắt buộc là `van_phong`. `thoi_gian_du_kien_phut` là số phút lệch so với giờ khởi hành, cộng với `gio_khoi_hanh` thật của từng `chuyen_xe` để ra giờ dự kiến cụ thể tại từng điểm (VD "23:00 Bến xe Nước Ngầm", "04:30 Bến xe Trung tâm Lào Cai"). Một tuyến có thể chạy nhiều chuyến/ngày theo khung giờ khác nhau.
- `nhom_tuyen`: gộp các `tuyen` cùng chạy trên **1 hành trình vật lý** (thường là 2 `tuyen` ngược chiều nhau — VD "Yên Nghĩa→Sapa" và "Sapa→Yên Nghĩa" cùng thuộc `nhom_tuyen` "Hà Nội – Sapa"; có thể nhiều hơn 2 nếu có biến thể tuyến nhanh/chậm trên cùng hành trình). Mỗi `tuyen.nhom_tuyen_id` trỏ vào đúng 1 nhóm. Dùng để ràng buộc xe cố định theo tuyến (mục 3.2) — vì xe chạy khứ hồi giữa 2 chiều của cùng 1 nhóm vẫn thỏa ràng buộc vị trí liên tục (mục 3.3), không phải "chạy sang tuyến khác".
- **`khu_vuc`, `diem_don_tra`, `tuyen`/`tuyen_diem_don_tra`, `gia_ve`, `lich_chay_dinh_ky` (mục 3.5) do `quan_ly` tạo/sửa qua giao diện quản trị — không hardcode trong code.** Thời gian dự kiến giữa các điểm do quản lý **nhập tay** (dựa trên số liệu thực tế nhà xe đã chạy), không tính tự động qua API bản đồ — giữ đơn giản vì tuyến cố định, ít thay đổi. `dieu_do_vien` không tạo tuyến hay lịch chạy — chỉ **gán xe cụ thể** cho các chuyến đã được hệ thống tự sinh sẵn từ lịch chạy định kỳ (mục 3.5, mục 8.6).
- **Giá vé chỉ phụ thuộc cặp điểm đi/điểm đến, không phụ thuộc điểm đón/trả cụ thể**: quan sát thực tế — 2 vé cùng tuyến, khác điểm trả ("Văn phòng 025 Nguyễn Huệ Cửa Khẩu" và "Văn phòng Km 224 Phố Lu") — nhưng cùng giá 290.000đ vì cùng thuộc điểm đến "Lào Cai (TP...)". Mô hình: `gia_ve(tuyen_id, diem_di_id, diem_den_id) → gia_goc`, `quan_ly` **nhập tay** theo từng cặp điểm đi/đến — không suy ra tự động từ khoảng cách km, không hard-code.
- **Nhiều loại xe khác nhau cùng chạy 1 tuyến, giá khác nhau — xử lý bằng hệ số, không nhân dòng dữ liệu**: `loai_xe(ten, he_so_gia)` là danh mục `quan_ly` **tự thêm/sửa tùy ý** (VD "Ghế ngồi", "Giường đơn", "Giường cabin đôi"...), mỗi loại có 1 hệ số nhân giá cấu hình **1 lần dùng chung cho toàn hệ thống** (không phải theo từng tuyến). Mỗi `xe` gắn với đúng 1 `loai_xe`. **Giá bán thực tế của 1 chuyến = `gia_ve.gia_goc × loai_xe.he_so_gia` của xe đang chạy chuyến đó** — tính lúc hiển thị/bán vé, không lưu thành cột riêng. Nhờ vậy `quan_ly` chỉ cần nhập giá gốc theo `(tuyến, cặp điểm)` như trên (không nhân thêm theo loại xe) + hệ số theo từng loại xe (không nhân thêm theo tuyến) — tổng số lượt nhập là **phép cộng**, không phải phép nhân giữa 3 chiều (tuyến × cặp điểm × loại xe). Khi nhà xe bổ sung 1 loại xe mới: chỉ cần thêm 1 dòng `loai_xe` (hệ số) — `quan_ly` chọn loại xe này khi thiết lập lịch chạy định kỳ (mục 3.5), giá tự động áp dụng đúng hệ số ngay từ lúc chuyến được sinh ra, không cần cấu hình gì thêm cho từng tuyến.
- **Tách biệt rõ với chống trùng ghế (mục 6)**: chống trùng ghế vẫn phải tính theo vị trí vật lý thật của khách trên xe (`thu_tu` của đúng điểm đón/trả khách chọn) — vì đó là câu hỏi "khách ngồi ghế này từ lúc nào đến lúc nào", khác hẳn câu hỏi "khách trả bao nhiêu tiền". Hai cơ chế độc lập, không dùng chung 1 công thức.
- `xe`: biển số, `loai_xe` (danh mục do `quan_ly` tự quản trị — **quyết định luôn cả hệ số giá và sơ đồ ghế thật**; 2 xe cùng `loai_xe` giống hệt nhau về mọi mặt, chỉ khác biển số, xem mục 3.3), trạng thái `hoat_dong` / `bao_tri` / `ngung_su_dung`, `diem_goc_id` (điểm `loai = 'van_phong'` được gán khi thêm xe vào hệ thống — dùng làm vị trí khởi điểm, xem mục 3.3), `nhom_tuyen_id` (**nullable** — nếu có, xe chỉ chạy cố định trong nhóm tuyến này, xem mục 3.2; để trống nếu xe dùng linh hoạt cho nhiều tuyến, VD xe dự phòng). Xe `bao_tri`/`ngung_su_dung` không thể được gán vào chuyến mới.

### 3.2. Biên chế cố định theo xe

Thực tế vận hành: mỗi xe có **biên chế cố định** — đúng **2 tài xế** (thay phiên nhau, đặc biệt cần thiết với tuyến dài phải đổi ca giữa đường) và **tối thiểu 1 phụ xe** — không phải mỗi chuyến được gán ngẫu nhiên nhân sự từ toàn bộ danh sách như suy nghĩ ban đầu.

- `xe_nhan_su(xe_id, nhan_vien_id, vai_tro, loai, trang_thai)`: bảng biên chế **duy nhất** gắn nhân sự với xe — **không có bảng `phan_cong_chuyen` gán riêng theo từng chuyến cho tài xế/phụ xe** (khác thiết kế ban đầu). Cả tài xế lẫn phụ xe đều thuộc về 1 xe theo đúng 1 cách như nhau; sự khác biệt duy nhất giữa 2 `chuc_danh` là **phụ xe có tài khoản, tài xế thì không** (mục dưới).
  - Mỗi xe có đúng 2 dòng `vai_tro = tai_xe` và ≥1 dòng `vai_tro = phu_xe` với `loai = co_dinh` — `quan_ly` quản lý trực tiếp (mục 8.7), cùng tính chất cấu hình ổn định lâu dài như `xe.nhom_tuyen_id` (mục 3.1). 1 nhân viên vận hành chỉ thuộc biên chế cố định của **1 xe duy nhất** tại 1 thời điểm.
  - `loai = tam_thoi` + `trang_thai` (`dang_hoat_dong`/`tam_nghi`): dùng khi cần thay người, xem mục "Xử lý nghỉ" dưới đây.
  - **"Chuyến của tôi" của phụ xe được suy ra trực tiếp** (không lưu riêng): 1 chuyến thuộc về phụ xe X nếu `chuyen_xe.xe_id` khớp với 1 dòng `xe_nhan_su(nhan_vien_id = X, vai_tro = phu_xe, trang_thai = dang_hoat_dong)` — tính tại **thời điểm truy vấn** (không phải thời điểm tạo chuyến), nên khi biên chế đổi (mục dưới), mọi chuyến chưa chạy của xe đó **tự động cập nhật đúng người** mà không cần sửa từng chuyến.
- **Tài xế chỉ là hồ sơ nhân sự trong `xe_nhan_su`, không có tài khoản đăng nhập hệ thống** (mục 8.3) — việc **2 tài xế thay phiên nhau lái** hoàn toàn do họ **tự thu xếp nội bộ**, hệ thống không theo dõi ai lái chuyến nào, không tính giờ nghỉ tối thiểu theo từng tài xế. Ngược lại, **phụ xe bắt buộc có tài khoản** vì là người duy nhất thao tác trên hệ thống trong đội vận hành (mục 8.2 — bao gồm cả các xác nhận trạng thái chuyến trước đây gán cho tài xế, xem mục 8.3).
- Khi điều độ viên tạo `chuyen_xe` (mục 8.6), **chỉ cần chọn xe** — không chọn/gán bất kỳ nhân sự nào (kể cả phụ xe): ai là phụ xe của chuyến đó luôn được suy ra live như trên.
- **Ràng buộc không trùng lịch** đơn giản hơn hẳn nhờ nhân sự đi theo xe:
  - Xe không được gán 2 chuyến có khung giờ chồng nhau (giờ khởi hành + thời gian di chuyển dự kiến + thời gian nghỉ quay đầu tối thiểu, VD 60 phút) — như cũ.
  - **Phụ xe tự động không trùng lịch** — vì luôn đi theo đúng xe của mình, xe rảnh thì phụ xe rảnh, không cần kiểm tra riêng nữa.
  - Tài xế: không có ràng buộc nào do hệ thống kiểm tra (ngoài phạm vi hệ thống, mục trên).
- **Ràng buộc xe cố định theo nhóm tuyến**: nếu `xe.nhom_tuyen_id` khác null, chỉ được gán xe đó cho chuyến có `tuyen.nhom_tuyen_id` **trùng đúng** giá trị này — không được gán sang chuyến của nhóm tuyến khác, dù đang rảnh và đúng vị trí. Vi phạm → hệ thống chặn ngay lúc gán, báo rõ lý do (xe đang cố định cho nhóm tuyến nào). Ràng buộc này **độc lập** với ràng buộc vị trí (mục 3.3) — 1 xe có thể đang đứng đúng vị trí khởi hành của 1 chuyến nhưng vẫn bị chặn nếu chuyến đó thuộc nhóm tuyến khác; xe không gán `nhom_tuyen_id` (dự phòng/linh hoạt) thì chỉ cần thỏa ràng buộc vị trí như bình thường.
- **Nghỉ phép định kỳ của tài xế (VD 2 ngày/tháng theo quy định) — hoàn toàn ngoài phạm vi hệ thống**: 1 trong 2 tài xế nghỉ, người còn lại tự lái 1 mình những ngày đó — xe vẫn đủ biên chế tối thiểu để chạy bình thường, không cần ai can thiệp, không cần ghi nhận gì trong hệ thống. Việc tính lương gấp đôi cho tài xế lái một mình thuộc **hệ thống chấm công/kế toán riêng của công ty**, ngoài phạm vi tính toán của hệ thống này.
- **Xử lý nghỉ (tài xế dài ngày, hoặc phụ xe bất kỳ thời lượng — ngắn/đột xuất lẫn dài ngày)**: cùng **1 cơ chế duy nhất**, do **điều độ viên** thực hiện (thuộc "Xử lý phát sinh nhân sự", mục 8.6) — không cần phân biệt ngắn/dài ngày về mặt thao tác, vì phụ xe đã suy ra live (mục trên) nên sửa biên chế 1 lần là đủ áp dụng cho mọi chuyến, kể cả chuyến sắp chạy trong vài giờ tới:
  1. Điều độ viên chuyển dòng `xe_nhan_su` của người vắng sang `trang_thai = tam_nghi`.
  2. Thêm 1 dòng mới `loai = tam_thoi`, `trang_thai = dang_hoat_dong` cho người thay thế (mượn từ nguồn dự phòng hoặc xe khác đang ít việc).
  3. Nếu không tìm được người thay (hết nguồn dự phòng) → báo lên `quan_ly` (mục 8.6, điểm 4).
  4. Khi người gốc quay lại: gỡ dòng `tam_thoi`, chuyển người gốc về `trang_thai = dang_hoat_dong`.
  - Với **phụ xe**: hiệu lực ngay lập tức vì suy ra live — không cần đụng tới bất kỳ chuyến cụ thể nào, kể cả chuyến chỉ còn vài giờ nữa khởi hành.
  - Với **tài xế**: chỉ mang tính ghi nhận hồ sơ (không ảnh hưởng vận hành, vì tài xế vốn không được hệ thống theo dõi theo chuyến) — báo cáo luôn là thủ công (qua phụ xe hoặc trực tiếp) vì tài xế không có tài khoản.
  - `quan_ly` chỉ can thiệp trực tiếp khi thay đổi biên chế **cố định lâu dài** (`loai = co_dinh` — VD nhân viên nghỉ việc hẳn, cần biên chế lại xe với người mới hoàn toàn), không phải các thay đổi `tam_thoi` mang tính phản ứng nhanh hàng ngày.

### 3.3. Vị trí xe — ràng buộc nối chuyến

Một xe không "dịch chuyển tức thời" — chuyến tiếp theo gán cho 1 xe **bắt buộc phải xuất phát đúng từ nơi xe đó đang/sẽ có mặt**, không phải xuất phát từ điểm gốc hay bất kỳ điểm nào điều độ viên muốn.

- **Vị trí dự kiến của xe tại 1 thời điểm** được suy ra, không lưu tĩnh:
  - Nếu chưa có chuyến nào được gán cho xe kết thúc trước thời điểm đó → vị trí = `diem_goc_id`.
  - Ngược lại → vị trí = **điểm cuối cùng (`thu_tu` lớn nhất trong `tuyen_diem_don_tra`, luôn có `loai = 'van_phong'`) của chuyến gần nhất (theo giờ) đã gán cho xe đó, kết thúc trước thời điểm đang xét**.
- **Ràng buộc khi gán xe cho 1 chuyến mới** (kiểm tra ở Service, cùng lúc với kiểm tra trùng giờ ở mục 3.2): điểm khởi hành của chuyến mới phải **trùng đúng** vị trí dự kiến của xe tại giờ khởi hành đó. Ví dụ xe vừa chạy (hoặc đã được lên lịch chạy) A→B thì chuyến kế tiếp gán cho xe này chỉ có thể là B→C hoặc B→A — không thể là 1 chuyến xuất phát từ A hay từ điểm khác.
  - Vi phạm → hệ thống chặn ngay lúc gán, báo rõ lý do (xe đang/sẽ ở đâu, lúc mấy giờ, khác với điểm khởi hành chuyến đang định gán).
- **Khi có sự cố** (`gap_su_co`/`da_huy` giữa đường, mục 4): vị trí thực tế của xe lệch khỏi dự kiến ban đầu — **áp dụng ngay khi chuyến chuyển `gap_su_co`, bất kể sau đó tự khắc phục nhanh, delay dài, hay `da_huy`**, vì trong lúc chưa rõ kết quả, vị trí suy luận theo lịch trình (dựa trên "chuyến gần nhất hoàn thành", mục trên) không còn đáng tin. Điều độ viên xử lý sự cố phải cập nhật lại vị trí thực tế của xe; mọi chuyến `chua_khoi_hanh` đã lên lịch sẵn cùng `xe_id` (xe gốc) đó bị hệ thống **gắn cờ cảnh báo xung đột vị trí**, cần điều độ viên xem lại thủ công (không tự động hủy dây chuyền). Khi sự cố đã resolve (chuyến quay lại `dang_chay`/`hoan_thanh`, hoặc chuyển `da_huy`), điều độ viên xem lại từng chuyến bị gắn cờ:
  - Xe vẫn tới kịp đúng vị trí cho chuyến kế tiếp (chỉ trễ nhẹ) → chỉ cần dời nhẹ giờ khởi hành chuyến đó cho khớp thực tế, gỡ cờ.
  - Xe không thể tới kịp đúng vị trí/giờ (delay quá lớn, hoặc chuyến trước đã `da_huy` giữa đường khiến xe mắc kẹt nơi khác) → áp dụng **đúng cơ chế UC-20** (tìm xe thay thế nội bộ/thuê ngoài, hoặc hoãn) cho chuyến đó — bản chất vấn đề giống hệt "xe hỏng đột xuất trước giờ chạy", chỉ khác nguyên nhân là do chuyến trước của cùng xe gây ra chứ không phải sự cố mới; áp dụng tiếp cho các chuyến sau nữa trong chuỗi nếu vẫn còn ảnh hưởng dây chuyền.
- **Phạm vi xem/gán**: điều độ viên chỉ **gán xe cho chuyến** (mục 3.5, UC-44) trong phạm vi văn phòng mình phụ trách (mục 2) — chuyến đã được hệ thống tự sinh sẵn từ lịch chạy định kỳ, không phải điều độ viên tự tạo. Vì xe di chuyển qua nhiều điểm khác nhau theo tuyến, **danh sách "xe đang ở đâu, còn trống lịch lúc nào" là dữ liệu dùng chung toàn hệ thống** — điều độ viên ở điểm B phải xem được xe có điểm gốc là A nhưng hiện đang/sắp có mặt tại B, để gán tiếp cho chuyến của mình.
- **Đổi xe trước giờ khởi hành — dùng "xe thực tế" tạm thời, KHÔNG đổi xe gốc của chuyến** (VD xe A hỏng đột xuất, cần xe B chạy thay): đây là điểm khác biệt quan trọng so với thiết kế ban đầu — `chuyen_xe.xe_id` (xe gốc, quyết định biên chế tài xế/phụ xe theo mục 3.2 và vị trí suy luận ở trên) **không hề thay đổi**. Chỉ thêm 1 giá trị riêng — **"xe thực tế"** (`xe_thuc_te_id`, mặc định `NULL` nghĩa là đúng xe gốc đang chạy) — ghi nhận phương tiện vật lý nào thật sự chở khách, tách biệt khỏi việc "chuyến này thuộc về xe nào" về mặt lịch trình/nhân sự. **Nguyên tắc quan trọng nhất: chuyến KHÔNG BAO GIỜ bị hủy chỉ vì lý do hết xe thay thế** — vé được xem như 1 cam kết chắc chắn với khách (mục 1), nhất là dịp cao điểm khi khách không còn lựa chọn nào khác nếu bị hủy hẳn; hết xe ngay lúc đó chỉ khiến chuyến **hoãn** giờ khởi hành, không bao giờ chuyển `da_huy`:
  1. Điều độ viên tìm xe thay thế theo **2 nguồn, ưu tiên theo thứ tự**: (a) **xe dự phòng cùng `loai_xe`** đang rảnh trong đội xe (`nhom_tuyen_id = null` hoặc xe khác đang trống lịch, mục 3.2); (b) nếu (a) không có ngay — **xe thuê/mượn ngoài đội xe** (từ garage/nhà xe đối tác, thực tế phổ biến của nhà xe khi cần gấp) — điều độ viên thêm 1 bản ghi `xe` bình thường vào hệ thống (không cần cột đánh dấu nguồn gốc riêng, đơn giản hóa — chỉ cần đủ thông tin để hoạt động như 1 xe thật), rồi xử lý y hệt xe nội bộ. Cả 2 nguồn đều **bắt buộc cùng `loai_xe` với xe A** (mục 3.1, không cho phép khác loại) — nhờ vậy giữ nguyên toàn bộ lợi ích đã có: không cần kiểm tra riêng "đủ ghế" hay ánh xạ lại số ghế, luôn khớp y hệt xe A — và hệ thống vẫn kiểm tra đúng vị trí + không trùng lịch riêng của xe được chọn.
  2. Chọn 1 xe tìm được (dù nguồn a hay b), gán làm "xe thực tế" cho chuyến hiện tại **và toàn bộ chuỗi các chuyến tương lai (`chua_khoi_hanh`) hiện đang gán cho xe A** — không chỉ đúng 1 chuyến — vì các chuyến đó vẫn thuộc đúng biên chế/lịch trình xe A (`xe_id` không đổi), chỉ là "cưỡi tạm" trên thân xe khác cho tới khi có quyết định khác. Nhờ vậy: **biên chế tài xế/phụ xe không hề bị xáo trộn** (vẫn suy ra từ `xe_id` = A như cũ, đúng người vẫn làm đúng ca của họ), và **không phát sinh cảnh báo xung đột vị trí dây chuyền** cho các chuyến sau — vì chuỗi chuyến của xe A vẫn nối liền nhau bình thường, chỉ đổi phương tiện.
  3. **Mọi chuyến đang có `xe_thuc_te_id` khác `NULL` được gắn cờ hiển thị rõ** (VD "đang chạy thay bằng xe B") — điều độ viên dễ dàng nhìn thấy chuyến nào đang mượn xe, không cần dò từng chuyến.
  4. Khách có vé trên các chuyến này nhận thông báo qua WebSocket (mục 8.1) về việc đổi xe thực tế (chỉ đổi biển số hiển thị, ghế **luôn** giữ nguyên).
  5. Vị trí vật lý thật của xe A (đang hỏng) cần điều độ viên cập nhật thủ công khi biết được (VD "đang ở xưởng sửa chữa Y") — **tách biệt hoàn toàn** với vị trí suy luận theo lịch trình ở trên (vốn vẫn tính bình thường theo chuỗi chuyến `xe_id = A`, dù thực tế do xe B chạy).
  6. **Khi xe A chuyển trạng thái từ `bao_tri` về `hoat_dong`** (sửa xong) → hệ thống tự gửi thông báo cho điều độ viên: "Xe A đã sẵn sàng hoạt động — đang có N chuyến chạy thay bằng xe khác, xem lại để gán lại nếu phù hợp". Đây chỉ là **nhắc nhở**, không tự động đổi gì cả.
  7. **Việc gán lại xe A** (đặt `xe_thuc_te_id` về lại `NULL` từ 1 chuyến trở đi trong chuỗi) **hoàn toàn do điều độ viên thao tác thủ công** — tự quyết định thời điểm hợp lý (thường là khi xe thay thế vừa hay đang kết thúc 1 chuyến đúng tại nơi xe A đang đỗ, tiện bàn giao), hệ thống không tự động thực hiện.
  8. **Kiểm tra chênh lệch giờ khởi hành khi tìm được xe thay thế (bước 1-2)**: nếu xe thay thế chỉ có thể sẵn sàng trễ hơn giờ đã lên lịch của chuyến:
     - **≤ 30 phút**: coi là không đáng kể — xử lý bình thường như trên (điều chỉnh nhẹ giờ khởi hành nếu cần), không có gì đặc biệt thêm.
     - **> 30 phút, hoặc chưa tìm được xe nào ở cả 2 nguồn ngay lúc xử lý** → chuyển sang cơ chế **"đang hoãn"** ở điểm 9, thay vì hủy.
  9. **Cơ chế "đang hoãn" — thay thế hoàn toàn cho việc hủy chuyến trước giờ chạy**: chuyến vẫn giữ `chua_khoi_hanh`, chỉ cập nhật `gio_khoi_hanh` sang thời điểm dự kiến mới tốt nhất hiện có (mục 4) — có thể cập nhật lại nhiều lần khi có thông tin mới, cho tới khi thực sự tìm được xe (nguồn a hoặc b ở bước 1). Nhà xe đặt mục tiêu vận hành **tối đa 6 tiếng** để tìm được xe thay thế — ngưỡng này `quan_ly` cấu hình được, chỉ dùng để **cảnh báo lên `quan_ly`** khi vượt quá (biết mà hỗ trợ thêm nguồn xe), **không** dùng để tự động hủy hay ép buộc hành động gì — điều độ viên tiếp tục tìm xe tới khi có, không có giới hạn cứng nào buộc phải dừng lại. Trong suốt thời gian "đang hoãn": mọi vé `da_thanh_toan` của chuyến (bất kể trả qua kênh nào) được khách **chủ động hủy nhận hoàn 100%** nếu không muốn/không thể chờ (mục 7, UC-41) — đây là ngoại lệ **duy nhất** phá vỡ quy tắc "vé đã thanh toán không hủy"; khách không hủy thì giữ nguyên vé, chờ chuyến chạy theo giờ mới. Hệ thống chỉ hoàn đúng 100% **giá vé** — không có cơ chế bồi thường thiệt hại phát sinh khác (lỡ chuyến bay, chi phí phát sinh...), theo đúng giới hạn trách nhiệm tiêu chuẩn của hợp đồng vận chuyển hành khách, ngoài phạm vi hệ thống. Khi cuối cùng tìm được xe: cập nhật `gio_khoi_hanh` chính thức, tắt cờ "đang hoãn", chuyến tiếp tục vòng đời bình thường — khách chưa hủy giữ nguyên đúng ghế/đoạn đã đặt.

- **Chuyến chưa từng được gán xe mà đã tới giờ khởi hành (`xe_id` vẫn `NULL`)** — nguồn gốc **khác hẳn** tình huống trên: không có "xe gốc" nào để giữ nguyên, vì lịch chạy định kỳ sinh chuyến ra với `xe_id = NULL` ngay từ đầu, chỉ được điều độ viên gán trong cửa sổ trước giờ chạy (mục 3.5) — nếu tìm mãi không ra xe, tới đúng giờ khởi hành mà vẫn chưa gán được. Đây là 1 tình huống khác về **trigger** (thời gian, không phải sự cố hay hành động điều độ viên) nhưng bản chất vấn đề giống hệt trên ("chuyến sắp/đã tới giờ mà không có xe") nên **dùng chung 100% cơ chế "đang hoãn"** vừa mô tả — hệ thống **tự động** (không cần điều độ viên thao tác) chuyển sang "đang hoãn" ngay khi tới `gio_khoi_hanh` mà `xe_id` vẫn `NULL` (UC-45 ⏱): dời giờ, cảnh báo `quan_ly` sau 6 tiếng, khách được chủ động hủy nhận hoàn 100% qua UC-41 — y hệt như trên. Khác biệt duy nhất: khi điều độ viên cuối cùng tìm được xe qua UC-44, gán **thẳng vào `xe_id`** (không qua `xe_thuc_te_id` — không có xe gốc nào để giữ nguyên cả).

### 3.4. Luồng tìm & đặt vé — chọn ghế trước, điểm đón/trả sau

1. **Tìm kiếm**: khách chọn **điểm đi** + **điểm đến** (cả hai tham chiếu `khu_vuc`, mục 3.1) + ngày — Service tìm mọi `chuyen_xe` chạy ngày đó có ít nhất 1 điểm **`van_phong`** thuộc khu_vực điểm đi (vì điểm đón bắt buộc là văn phòng, mục 3.1), đứng trước (theo `thu_tu`) ít nhất 1 điểm đón/trả bất kỳ (`van_phong` hoặc `diem_dung`) thuộc khu_vực điểm đến.
2. **Kết quả**: danh sách chuyến (mỗi thẻ = 1 `chuyen_xe` cụ thể) — loại xe, giá "từ" (theo `gia_ve(chuyến, điểm đi, điểm đến)`, mục 3.1), số ghế trống, giờ dự kiến.
3. **Chọn 1 chuyến** → hệ thống hiển thị **sơ đồ ghế** của đúng chuyến đó. Vì điểm đón/trả cụ thể **chưa được chọn** ở bước này, "còn trống" tính theo đoạn **rộng nhất có thể**: từ điểm `van_phong` đầu tiên hợp lệ làm điểm đón trong khu_vực điểm đi, tới điểm cuối cùng hợp lệ làm điểm trả (`van_phong`/`diem_dung`) trong khu_vực điểm đến — đoạn bảo thủ nhất, đảm bảo ghế hiện "còn trống" ở bước này chắc chắn còn trống cho **mọi** cặp điểm đón/trả cụ thể nằm trong 2 khu_vực đã tìm.
4. **Chọn 1 hoặc nhiều ghế** → bấm **"Cập nhật điểm đón trả"** — đây là **mốc khóa ghế** (chống trùng, mục 6): hệ thống tạo `ve` trạng thái `giu_cho` cho từng ghế đã chọn ngay lúc bấm (dùng đoạn rộng ở bước 3) — **ai bấm trước, người bấm sau cho cùng ghế đó bị chặn ngay** (ghế lập tức hiện "đã có người giữ" cho người khác), **vĩnh viễn cho tới khi khách này thanh toán xong hoặc hết hạn** — không liên quan tới việc hạn giữ chỗ dài hay ngắn. **Lưu ý: đây chưa phải mốc bắt đầu tính hạn giữ chỗ** — xem bước 6.
5. **Chọn điểm đón + điểm trả cụ thể** (`diem_don_tra` do `quan_ly` tạo/quản lý trước, mục 3.1; khách chỉ **chọn**, không tự nhập/tạo mới địa điểm — **điểm đón**: chỉ hiện các `van_phong` thuộc khu_vực điểm đi; **điểm trả**: hiện mọi điểm (`van_phong` lẫn `diem_dung`) thuộc khu_vực điểm đến, đứng sau điểm đón theo `thu_tu`; dùng chung cho tất cả ghế đã chọn trong lần đặt này — không hỗ trợ mỗi ghế 1 cặp điểm đón/trả khác nhau, đơn giản hóa cho BTL vì thường đi cùng nhóm) → hệ thống **thu hẹp lại** đoạn `giu_cho` của từng vé về đúng `[diem_don, diem_tra)` cụ thể — đoạn mới luôn hẹp hơn hoặc bằng đoạn đã khóa ở bước 4 nên không thể phát sinh xung đột mới, chỉ cần cập nhật `diem_don_id`/`diem_tra_id`, không cần khóa lại. Đây là bước chọn nhanh từ danh sách nên không giới hạn thời gian riêng.
6. **Tới màn hình thanh toán**, chọn phương thức (mục 6): "thanh toán ngay" hoặc "thanh toán tại quầy khi nhận vé" (**không có hạn/mốc chốt nào** — coi như đặt vé thành công ngay, giữ nguyên tới giờ khởi hành, chỉ mất khi khách tự hủy hoặc không lên xe đúng giờ, mục 6/9) — **có thể bị bắt buộc đặt cọc một phần nếu đặt nhiều vé giá trị cao**, xem ngay dưới đây. Nếu chọn "thanh toán ngay": **hạn 5 phút được tính từ đúng lúc này** (khi tới màn thanh toán) — không tính từ bước 4 — nhưng nếu cổng thanh toán báo kết quả sớm hơn (thành công/hủy) thì xử lý ngay, không đợi hết 5 phút. Chỉ khi không có tín hiệu gì trả về và quá 5 phút mới `het_han`, ghế mở lại.

Toàn bộ vé cùng 1 lần đặt (nhiều ghế) nhóm theo **`ma_dat_cho`** chung — dùng để nhân viên quầy vé tra cứu (mục 8.4) và khách xem lịch sử (mục 8.1).

**Bắt buộc đặt cọc khi chọn "thanh toán tại quầy" cho lô nhiều vé giá trị cao** (chống lạm dụng giữ nhiều ghế dài hạn mà không cam kết gì):

- **1 vé**: không bao giờ yêu cầu đặt cọc, dù giá bao nhiêu — giữ nguyên tới giờ khởi hành (mục 6), không tới lên xe đúng giờ thì tính `khong_den` (mục 9), không có `het_han` cho trường hợp này.
- **≥ 2 vé và tổng giá trị cả lô ≤ 600.000đ** (ngưỡng `quan_ly` cấu hình): không yêu cầu đặt cọc, toàn bộ vé đều được "tại quầy" bình thường.
- **≥ 2 vé và tổng giá trị cả lô > 600.000đ**: bắt buộc thanh toán ngay **`floor(so_ve × 50%)`** vé trong lô (tỷ lệ 50% `quan_ly` cấu hình, làm tròn **xuống** theo số lượng vé, không phải theo tiền) — VD đặt 5 vé → phải trả ngay 2 vé, đặt 6 vé → phải trả ngay 3 vé. Số vé "cọc" này theo đúng hạn "thanh toán ngay" (5 phút, mục 6); nếu không hoàn tất trong hạn đó → **toàn bộ lô** (kể cả các vé định để "tại quầy") chuyển `het_han`, không chỉ riêng phần cọc.
- Vé đã trả trước theo diện "cọc" tuân theo đúng chính sách hoàn tiền của vé `da_thanh_toan` (mục 7 — không hoàn nếu khách đổi ý sau đó, vì thực chất là thanh toán đủ trước cho đúng số vé đó, không phải khoản cọc riêng có thể hoàn).

### 3.5. Lịch chạy định kỳ và gán xe — tách rời việc lên lịch khỏi việc chọn xe cụ thể

Thực tế vận hành (quan sát từ app Futa/Hà Sơn): khách đặt được vé cho chuyến tận nhiều tuần/tháng sau, nhưng biển số xe cụ thể chỉ xuất hiện gần ngày chạy. Vì vậy việc "chuyến này chạy khi nào, dùng loại xe gì" (kế hoạch dài hạn) phải tách rời khỏi việc "xe cụ thể nào (biển số) sẽ chạy" (quyết định vận hành ngắn hạn).

- `lich_chay_dinh_ky(tuyen_id, gio_khoi_hanh, loai_xe_id, dang_ap_dung)`: do **`quan_ly`** thiết lập — chọn 1 `tuyen` có sẵn, nhập giờ khởi hành trong ngày, chọn `loai_xe` dự kiến phục vụ khung giờ này. 1 tuyến có thể có nhiều dòng `lich_chay_dinh_ky` (nhiều khung giờ/loại xe khác nhau trong ngày).
- Hệ thống (job định kỳ) tự động sinh sẵn `chuyen_xe` cho mỗi `lich_chay_dinh_ky` đang `dang_ap_dung`, cuốn chiếu **N ngày tới** (N do `quan_ly` cấu hình) — mỗi `chuyen_xe` sinh ra có `tuyen_id`, `gio_khoi_hanh` (ngày cụ thể + giờ từ template), `loai_xe_id` (copy từ template) — **`xe_id` để trống (`NULL`)**, chưa gán xe cụ thể.
- **Nhờ đúng nguyên tắc "2 xe cùng `loai_xe` giống hệt nhau"** (mục 3.1) — chỉ cần `loai_xe_id` đã có, hệ thống **đã đủ để bán vé** (hiển thị đúng sơ đồ ghế, tính đúng giá `gia_ve.gia_goc × loai_xe.he_so_gia`) — khách đặt vé bình thường dù chưa biết xe nào (biển số) sẽ chạy. **Biển số xe chỉ hiển thị cho khách sau khi đã gán xe** — trước đó khách chỉ thấy tên loại xe (VD "Giường nằm 40 chỗ").
- **`dieu_do_vien` thực hiện gán xe** (mục 8.6, UC-44) cho từng `chuyen_xe` đã sinh sẵn — chọn 1 xe cụ thể **bắt buộc đúng `loai_xe_id`** đã cam kết ở lịch định kỳ, kiểm tra trùng lịch/vị trí liên tục như bình thường (mục 3.2/3.3). Có thể gán lại (đổi xe) **bất cứ lúc nào** trước giờ khởi hành, miễn xe mới vẫn đúng `loai_xe_id` — không giới hạn số lần đổi.
- **Ngưỡng nhắc gán xe**: hệ thống cảnh báo `dieu_do_vien` nếu chuyến còn ≤ 48 tiếng (mặc định, `quan_ly` cấu hình được) mà vẫn chưa gán xe (`xe_id IS NULL`) — chỉ là **nhắc nhở**, không tự động chặn hay hủy gì cả (giống các cơ chế cảnh báo khác trong hệ thống, VD mục 3.3).
- Khi `quan_ly` ngừng áp dụng 1 `lich_chay_dinh_ky` (`dang_ap_dung = false`): chỉ ngừng **sinh chuyến mới** từ thời điểm đó — các `chuyen_xe` đã sinh sẵn trước đó (có thể đã có khách đặt vé) **không bị xóa/hủy**, vẫn chạy bình thường theo đúng vòng đời (mục 4).
- **Vị trí suy luận theo lịch trình và biên chế tài xế/phụ xe** (mục 3.2/3.3) chỉ có ý nghĩa **từ lúc `xe_id` đã được gán** — chuyến chưa gán xe hiển thị rõ "chưa gán xe" cho điều độ viên, không phải lỗi.

---

## 4. Vòng đời chuyến xe

```
chua_khoi_hanh   ← KHÔNG BAO GIỜ hủy vì lý do kinh doanh (ít/không có khách, mục 1) VÀ KHÔNG BAO GIỜ hủy vì hết xe thay thế (mục 3.3)
  ├─ [Xe hỏng đột xuất, chưa tìm được xe thay thế kịp (lệch >30 phút) — mục 3.3 điểm 9] → vẫn chua_khoi_hanh, chỉ dời gio_khoi_hanh + gắn cờ "đang hoãn"
  │      ├─ [Khách đã thanh toán không muốn/không thể chờ — mục 7, UC-41] → vé đó chuyển da_huy, hoàn 100% (chuyến vẫn tiếp tục hoãn cho các khách khác)
  │      └─ [Cuối cùng tìm được xe (nội bộ hoặc thuê ngoài) — mục 3.3] → tắt cờ "đang hoãn", tiếp tục bình thường
  ├─ [Tới giờ khởi hành mà chưa từng gán được xe, xe_id vẫn NULL — mục 3.3, UC-45 ⏱] → vẫn chua_khoi_hanh, TỰ ĐỘNG gắn cờ "đang hoãn" (dùng chung nhánh xử lý y hệt trên; khi có xe thì gán thẳng xe_id, không qua xe_thuc_te_id)
  └─ [Đến giờ khởi hành, phụ xe xác nhận xuất phát] → dang_chay
                                                         ├─ [Phụ xe báo sự cố, phân loại nguyên nhân — UC-17] → gap_su_co (loai_su_co = loi_nha_xe / loi_khach_quan)
                                                         │      ├─ [loi_nha_xe, ≤1 tiếng tự khắc phục — UC-19] → quay lại dang_chay, không hoàn
                                                         │      ├─ [loi_nha_xe, >1 tiếng — điều xe thay thế, LUÔN tìm được cuối cùng, không có khái niệm "không thể tiếp tục" — UC-19]
                                                         │      │      ├─ [Khách chủ động yêu cầu hủy nhận hoàn — mục 7, UC-42] → vé đó chuyển da_huy, hoàn 100%, HẾT nghĩa vụ phục vụ (chuyến vẫn tiếp tục xử lý cho khách khác)
                                                         │      │      ├─ [Khách đồng ý chờ, đạt mốc ≥3 tiếng vẫn chưa xong — UC-43 ⏱] → tự động hoàn 100%, vé VẪN da_thanh_toan (không hủy, vẫn được chở tiếp miễn phí)
                                                         │      │      └─ [Điều được xe thay thế] → quay lại dang_chay
                                                         │      ├─ [loi_khach_quan, ≤3 tiếng, hoặc >3 tiếng nhưng vẫn còn khả năng hoàn thành] → chờ tại chỗ, KHÔNG có lựa chọn hoàn nào (bất khả kháng) → khi xong quay lại dang_chay, không hoàn
                                                         │      └─ [loi_khach_quan, >3 tiếng, điều độ viên xác nhận thực sự không thể hoàn thành nữa] → da_huy → UC-21 (hoàn 100% cho vé đã thanh toán, không tính theo đoạn đã đi — dù lỗi khách quan, vì dịch vụ chắc chắn không được cung cấp)
                                                         └─ [Phụ xe xác nhận đến điểm cuối] → hoan_thanh
```

## 5. Vòng đời vé

Mỗi `ve` gắn với 1 chuyến + 1 ghế + **1 cặp điểm đón (`diem_don_id`) / điểm trả (`diem_tra_id`)** — tham chiếu thẳng tới `diem_don_tra`, là đúng điểm khách chọn ở bước 5 của mục 3.4 (`diem_don_id` luôn là `van_phong`; `diem_tra_id` là `van_phong` hoặc `diem_dung`, mục 3.1). Ràng buộc hợp lệ: cả hai phải nằm trong `tuyen_diem_don_tra` của tuyến mà chuyến đó chạy, và điểm đón phải đứng trước điểm trả theo `thu_tu`. Vòng đời trạng thái không đổi so với trước, chỉ khác ở cách kiểm tra ghế trống (mục 6):

```
giu_cho (bản ghi tạo ngay khi bấm "Cập nhật điểm đón trả" — mục 3.4 bước 4; ghế coi như bị khóa từ đây, nhưng CHƯA tính giờ)
  ├─ [Khách tự hủy trước khi thanh toán, VÀ trước mốc chốt lên xe tại điểm đón — mục 7] → da_huy (mở ghế lại ngay, không mất gì vì chưa trả tiền)
  ├─ [Chọn "Thanh toán ngay"] → tới màn thanh toán (mục 3.4 bước 6) — **hạn 5 phút bắt đầu tính từ đây** (hạn chót an toàn), không phải từ lúc khóa ghế ở bước 4
  │     ├─ [Cổng thanh toán báo thành công — xử lý ngay, không đợi hết hạn] → da_thanh_toan
  │     └─ [Cổng báo hủy/thất bại, hoặc hết 5 phút không có tín hiệu gì] → het_han (tự động giải phóng ghế, không mất gì vì chưa trả tiền)
  └─ [Chọn "Thanh toán tại quầy khi nhận vé"] → **coi như đặt vé thành công ngay, không có hạn/mốc chốt nào** — giữ nguyên tới giờ khởi hành tại điểm đón (mục 6)
        ├─ [Ra quầy trả tiền + lấy vé cứng, bất kỳ lúc nào trước khi lên xe] → da_thanh_toan
        └─ [Đến giờ lên xe tại điểm đón mà vẫn chưa ra quầy trả tiền] → khong_den trực tiếp (mục 9 — không qua `het_han`, vì không còn mốc chốt nào để "hết hạn")

da_thanh_toan   ← từ đây KHÔNG còn đường quay lại het_han/hủy do khách yêu cầu, TRỪ đúng 3 ngoại lệ (mục 7)
  ├─ [Phụ xe xác nhận khách xuất trình vé cứng lúc lên xe — mục 8.2] → da_len_xe
  │     └─ [Phụ xe xác nhận khách đã xuống đúng điểm trả — mục 8.2] → da_xuong_xe (kết thúc vòng đời vé)
  ├─ [Đến giờ lên xe tại điểm đón mà khách chưa lên xe] → khong_den (không hoàn tiền)
  ├─ [Chuyến gặp sự cố khách quan giữa đường, điều độ viên xác nhận không thể hoàn thành được nữa — UC-19/21] → da_huy (hoàn 100%, mục 7 — chuyến không bao giờ bị hủy vì lý do ít khách hay vì hết xe thay thế, mục 1)
  ├─ [Ngoại lệ: chuyến gặp sự cố do lỗi nhà xe giữa đường, đang chờ xử lý, khách chủ động không muốn/không thể chờ — UC-42] → da_huy (hoàn 100%)
  ├─ [Ngoại lệ: chuyến đang "hoãn" trước giờ chạy do hết xe thay thế (mục 3.3), khách chủ động không muốn/không thể chờ — UC-41] → da_huy (hoàn 100%)
  └─ [Chuyến gặp sự cố lỗi nhà xe giữa đường ≥3 tiếng chưa xong, khách không chủ động hủy — UC-43 ⏱] → VẪN da_thanh_toan (không đổi trạng thái) — chỉ tự động hoàn 100%, tiếp tục được chở miễn phí khi có xe
```

---

## 6. Cơ chế giữ ghế & bán vé theo chặng — chống bán trùng vé

Đây là bài toán kỹ thuật-nghiệp vụ trung tâm của hệ thống (đóng vai trò tương đương cơ chế đối chiếu EXIF GPS ở bản trước). Vì 1 chuyến có thể bán vé cho nhiều chặng khác nhau trên cùng 1 ghế (mục 5), "ghế trống hay không" **không còn là true/false cố định cho cả chuyến**, mà phụ thuộc vào đoạn hành trình khách định mua.

- Biểu diễn hành trình của mỗi vé bằng khoảng **`[thu_tu(diem_don), thu_tu(diem_tra))`** (nửa mở — khách xuống ở đâu thì từ điểm đó ghế coi như trống lại). 2 vé trên cùng `(chuyen_id, so_ghe)` **được phép cùng tồn tại** khi và chỉ khi 2 khoảng này **không giao nhau**: `ve_moi.tra ≤ ve_cu.don` HOẶC `ve_cu.tra ≤ ve_moi.don`.
  - VD ghế 5: khách 1 đặt A(0)→B(1) chiếm `[0,1)`; khách 2 đặt B(1)→C(2) chiếm `[1,2)` → không giao nhau, **cả hai đặt được cùng ghế 5**. Khách 3 muốn đặt A→C chiếm `[0,2)` → giao với cả hai vé trên → **bị chặn**, phải chọn ghế khác.
- Khi khách bấm **"Cập nhật điểm đón trả"** cho 1/nhiều ghế đã chọn (mục 3.4 bước 4 — đây là mốc khóa, không phải lúc mới bôi đen/xem thử ghế trên sơ đồ), hệ thống tạo `ve` trạng thái `giu_cho` cho đoạn `[don, tra)` **trong 1 transaction**: khóa toàn bộ dòng `ve` đang `giu_cho`/`da_thanh_toan` cùng `(chuyen_id, so_ghe)` (`SELECT ... FOR UPDATE`), kiểm tra không giao với bất kỳ dòng nào trong số đó rồi mới insert — ràng buộc unique đơn giản `(chuyen_id, so_ghe)` **không đủ** vì giờ 1 ghế hợp lệ có nhiều vé cùng lúc, nên bắt buộc phải khóa + kiểm tra overlap ở tầng Service/Repository, không thể phó mặc cho constraint của DB. Đoạn dùng để khóa lúc này là đoạn **rộng nhất** theo tìm kiếm (mục 3.4 bước 3); sau khi khách chọn điểm đón/trả cụ thể từ danh sách có sẵn (bước 5), đoạn được thu hẹp lại — không cần khóa lại vì đoạn hẹp hơn không thể tạo xung đột mới. **Ở bước này ghế đã bị khóa nhưng chưa bắt đầu tính hạn giữ chỗ** — xem bullet dưới.
- **Sơ đồ ghế trả về cho khách phải theo đúng đoạn họ đang tìm**: 1 ghế hiển thị "còn trống" cho đoạn `[don, tra)` khi không có vé active nào (kể cả `giu_cho` của người khác) overlap đoạn đó — nghĩa là cùng 1 chuyến, 2 khách tìm 2 đoạn khác nhau có thể thấy **cùng 1 ghế** với 2 trạng thái "trống"/"đã có người giữ" khác nhau.
- **Quan trọng: tính độc quyền của ghế và thời hạn giữ chỗ là 2 việc tách biệt.** Ghế đã bị khóa độc quyền cho đúng khách đó ngay từ lúc bấm "Cập nhật điểm đón trả" (bước 4) — **không ai khác chọn được ghế đó kể từ giây đó**, bất kể hạn giữ chỗ là bao lâu. Hạn giữ chỗ (mục dưới) chỉ quyết định "nếu khách này không hoàn tất thì đợi bao lâu mới nhả ghế cho người khác" — không ảnh hưởng gì tới việc chống trùng ghế.
- **Hạn giữ chỗ chỉ áp dụng cho "thanh toán ngay"** — "thanh toán tại quầy" **không có hạn nào cả**:
  - **Thanh toán ngay**: hạn mặc định **5 phút** (đủ thời gian cho 1 lượt thanh toán qua cổng online thật — chuyển hướng sang app ngân hàng/ví điện tử, nhập OTP, quay lại — thực tế thường lâu hơn 1 phút), tính từ lúc khách **tới màn hình thanh toán** (mục 3.4 bước 6) — không tính từ lúc khóa ghế (bước 4) hay lúc chọn điểm đón/trả (bước 5). **Không cần đợi tới hết 5 phút mới biết kết quả**: khi cổng thanh toán gọi webhook/callback báo giao dịch thành công hoặc thất bại/hủy, hệ thống xử lý **ngay lập tức** (chuyển `da_thanh_toan` hoặc `het_han` luôn, không chờ hết hạn) — 5 phút chỉ là **hạn chót an toàn** cho trường hợp khách bỏ dở mà không có tín hiệu gì trả về (đóng tab, mất mạng...). Quá hạn chưa thanh toán → chuyển `het_han`, đoạn hành trình đó mở lại. `quan_ly` cấu hình được giá trị 5 phút này.
  - **Thanh toán tại quầy khi nhận vé**: **coi như đặt vé thành công ngay lập tức, không có mốc chốt/hạn giữ nào** — ghế/đoạn hành trình đó thuộc về khách này liên tục cho tới giờ khởi hành tại điểm đón, bất kể bao lâu. Chỉ có đúng 2 cách kết thúc: (1) khách chủ động hủy trước khi thanh toán **và trước mốc chốt lên xe tại điểm đón** (mục 7) → mở đoạn ngay; qua mốc chốt đó không tự hủy được nữa; (2) đến giờ lên xe tại điểm đón mà khách chưa ra quầy trả tiền → chuyển thẳng `khong_den` (mục 9), **không** qua trạng thái `het_han` vì không có "hạn" nào để hết. Đây là điểm khác biệt cố ý so với "thanh toán ngay": không đặt áp lực thời gian nào lên khách chọn trả sau, đổi lại rủi ro chiếm ghế lâu dài được xử lý bằng cơ chế đặt cọc (mục 3.4) + đếm vi phạm no-show (mục 9), không phải bằng 1 mốc chốt cứng.
- Khách mua tại quầy (`nhan_vien_quay_ve`) đi thẳng `giu_cho` → `da_thanh_toan` gần như ngay lập tức, không áp dụng hạn giữ chỗ nào ở trên (tiền mặt trả ngay tại chỗ).
- **Điểm đón/trả hợp lệ**: `diem_don`/`diem_tra` phải nằm trong tập điểm của đúng tuyến chuyến đó chạy qua (`tuyen_diem_don_tra`), `diem_don` phải có `loai = 'van_phong'`, và `diem_don` phải đứng trước `diem_tra` theo `thu_tu` — Service chặn nếu khách gửi lên cặp điểm không hợp lệ (ví dụ điểm trả đứng trước điểm đón, điểm không thuộc tuyến, hoặc chọn điểm đón là `diem_dung`).

---

## 7. Chính sách hoàn tiền

**Không có cơ chế đổi vé.** Vé đã `da_thanh_toan` **không thể hủy hoặc đổi để lấy lại tiền**, bất kể còn bao lâu tới giờ khởi hành — khách đổi ý sau khi đã trả tiền coi như mất vé. **Chuyến đã lên lịch luôn chạy — không có khái niệm nhà xe chủ động hủy vì ít khách, và cũng không bao giờ hủy hẳn vì hết xe thay thế (trước giờ chạy lẫn giữa đường do lỗi nhà xe)** (mục 1, mục 3.3, mục 4) — hết xe chỉ khiến chuyến hoãn/chờ để tiếp tục tìm xe, luôn tìm được cuối cùng. Chỉ **sự cố khách quan giữa đường** (thiên tai, sạt lở...) mới có khả năng thực sự không thể hoàn thành. Vì vậy hệ thống có **4 trường hợp hoàn tiền** — 3 trường hợp đầu đi kèm hủy vé, riêng trường hợp thứ 4 hoàn tiền nhưng **vẫn tiếp tục phục vụ**:

| Trường hợp | Hoàn tiền | Vé có bị hủy không |
|---|---|---|
| Chuyến gặp sự cố **khách quan** giữa đường (thiên tai, sạt lở...), điều độ viên xác nhận thực sự không thể hoàn thành được nữa (mục 3.3/4, UC-19/21) | Hoàn 100% — dịch vụ chắc chắn không được cung cấp, khác với việc "không bồi thường vì trễ" | Có, `da_huy` |
| Chuyến gặp sự cố do **lỗi nhà xe** giữa đường, khách chủ động không muốn/không thể chờ (UC-42) | Hoàn 100%, hết nghĩa vụ phục vụ | Có, `da_huy` |
| Chuyến đang **"hoãn"** trước giờ chạy do chưa tìm được xe thay thế kịp (mục 3.3), khách chủ động không muốn/không thể chờ (UC-41) | Hoàn 100% | Có, `da_huy` |
| Chuyến gặp sự cố do **lỗi nhà xe** giữa đường kéo dài **≥ 3 tiếng** vẫn chưa xử lý xong, khách **không** chủ động yêu cầu hủy (UC-43, tự động) | Hoàn 100% — bù đắp vì để khách chờ quá lâu do lỗi nhà xe | **Không** — vé vẫn `da_thanh_toan`, tiếp tục được chở miễn phí khi có xe |

**Cả 4 trường hợp trên đều hoàn đúng 100% — không có cơ chế hoàn theo tỷ lệ chặng đường đã đi/chưa đi.** Kể cả khi chuyến đã đi được một phần hành trình trước khi gặp sự cố, khách vẫn được hoàn đủ 100%, không trừ theo đoạn đã đi — đơn giản hóa có chủ đích: không cần tính toán phức tạp theo từng đoạn. 3 trường hợp đầu là ngoại lệ **duy nhất** cho phép hủy vé `da_thanh_toan`.

**Riêng sự cố khách quan giữa đường**: trong lúc đang chờ xử lý (chưa xác nhận là không thể hoàn thành), khách **không có lựa chọn hủy nhận hoàn** dù muốn — đây là bất khả kháng, khác hẳn lỗi nhà xe (khách được chủ động hủy bất cứ lúc nào trong lúc chờ, mục 3.3/4). Nguyên tắc "khách quan thì không hoàn" chỉ áp dụng cho việc **không bồi thường vì trễ**, không áp dụng khi dịch vụ chắc chắn sẽ không bao giờ được cung cấp nữa.

**Cách thực hiện hoàn tiền — 2 luồng tùy khách trả bằng gì ban đầu**: cả 4 trường hợp trên đều xử lý theo đúng 1 trong 2 cách sau, không có ngoại lệ nào khác:
- **Khách trả qua chuyển khoản (VNPay)**: hoàn **tự động** qua cổng thanh toán, ngay khi hệ thống xác định phải hoàn — không cần ai thao tác.
- **Khách trả tiền mặt**: không thể hoàn tự động (không có giao dịch điện tử nào để đảo ngược) — vai trò `ke_toan` (mục 2) chủ động gọi điện khách xin thông tin chuyển khoản, thực hiện chuyển khoản (ngoài phạm vi hệ thống — qua ứng dụng ngân hàng công ty), rồi đánh dấu hoàn tất trên hệ thống (UC-22).

- Trước khi thanh toán (`giu_cho`), khách hủy tự do không mất gì — vì chưa trả tiền (mục 5), không tính là "hoàn tiền". **Chỉ được hủy trước mốc chốt lên xe tại điểm đón** (X phút/giờ trước giờ khởi hành, cùng mốc dùng để xác định no-show — mục 8.2 điểm 6, mục 9): qua mốc đó, hệ thống **ẩn nút hủy**, khách chỉ còn 2 lựa chọn — ra quầy trả tiền lên xe, hoặc bị tính `khong_den`. Lý do: hủy sát giờ chạy gây thiệt hại cho nhà xe gần như y hệt no-show (ghế bị chiếm tới sát giờ, không kịp bán lại cho khách khác) — nếu cho hủy miễn phí vô thời hạn, khách có thể cố tình chờ tới sát giờ mới hủy để né hẳn vi phạm.
- Ở mọi trường hợp hoàn tiền, hệ thống chỉ hoàn đúng **giá vé đã trả** — **không có cơ chế bồi thường thiệt hại phát sinh** (lỡ chuyến bay, chi phí phát sinh khác do trễ chuyến...), theo đúng giới hạn trách nhiệm tiêu chuẩn của hợp đồng vận chuyển hành khách thực tế, nằm ngoài phạm vi hệ thống.

---

## 8. Luồng nghiệp vụ theo vai trò

### 8.1. Khách hàng (`khach_hang`)

1. Tra cứu chuyến công khai theo **điểm đi + điểm đến + ngày** (mục 3.4, không cần đăng nhập) → chọn 1 chuyến trong danh sách kết quả (giá "từ", số ghế trống, giờ dự kiến).
2. Đăng nhập → **chọn 1 hoặc nhiều ghế** trên sơ đồ (mục 3.4 bước 3) → bấm "Cập nhật điểm đón trả" (**mốc khóa ghế**, mục 6) → **chọn** điểm đón (văn phòng) + điểm trả cụ thể (văn phòng hoặc điểm dừng dọc đường) từ danh sách có sẵn (chung cho các ghế đã chọn — khách không tự nhập/tạo địa điểm mới, mục 3.1).
3. Tới màn thanh toán, chọn phương thức: **"Thanh toán ngay"** (hạn 5 phút tính từ khi tới màn này — xử lý ngay nếu cổng thanh toán báo kết quả sớm hơn, không cần đợi hết hạn, mục 6) hoặc **"Thanh toán tại quầy khi nhận vé"** (**coi như đặt vé thành công ngay, không có hạn/mốc chốt nào** — giữ nguyên tới giờ khởi hành; chỉ nên chọn nếu chắc chắn sẽ ra quầy, vì không ra quầy trước giờ lên xe tính là vi phạm no-show, mục 9). Đặt ≥ 2 vé với tổng giá trị vượt ngưỡng (mặc định 600.000đ) → bị yêu cầu trả ngay 1 phần vé trong lô trước khi hoàn tất (mục 3.4).
4. Xem lịch sử vé, trạng thái từng vé, nhận thông báo qua WebSocket khi: vé được xác nhận, chuyến gặp sự cố/đổi xe/**đang hoãn** (kèm giờ dự kiến mới, mục 3.3), chuyến bị hủy giữa đường do bất khả kháng (kèm tự động hoàn tiền — hiếm khi xảy ra, chuyến không bao giờ hủy hẳn vì ít khách hay vì hết xe thay thế, mục 1), sắp đến giờ khởi hành.
5. **Trước giờ khởi hành, ra đúng văn phòng tại điểm đón đã chọn để nhận vé cứng** (`nhan_vien_quay_ve` tra theo mã đặt chỗ/SĐT rồi in — mục 8.4) — bắt buộc với **mọi kênh đặt** (tự đặt online, đặt qua hotline, hay mua trực tiếp tại quầy); nếu chọn "thanh toán tại quầy" thì đây cũng chính là lúc trả tiền. Phụ xe chỉ xác nhận lên xe dựa trên vé cứng xuất trình (mục 8.2), không dựa vào điện thoại/tài khoản của khách.
6. Tự hủy giữ chỗ (`giu_cho`) nếu đổi ý **trước khi thanh toán VÀ trước mốc chốt lên xe tại điểm đón** — không mất gì. Qua mốc chốt đó, nút hủy biến mất, không tự hủy được nữa (mục 7). Vé đã `da_thanh_toan` không tự hủy/đổi được nữa ở bất kỳ thời điểm nào (mục 7), **trừ 2 ngoại lệ**: chuyến đang "hoãn" trước giờ chạy do chưa tìm được xe thay thế (mục 3.3, UC-41), hoặc chuyến đang gặp sự cố do lỗi nhà xe giữa đường (mục 3.3/4, UC-42) — cả 2 đều được chủ động hủy nhận hoàn 100%.

**Ngoại lệ:**
- Bị hạn chế đặt vé giữ chỗ trả sau nếu no-show quá nhiều lần (mục 9) — chỉ được thanh toán ngay khi đặt.
- Không thấy được sơ đồ ghế/giá của chuyến đã `da_huy`/`hoan_thanh` theo cách hiển thị chọn ghế thông thường (chỉ xem trong lịch sử vé của chính mình).

### 8.2. Nhân viên vận hành — phụ xe (`chuc_danh = phu_xe`)

Phụ xe là **người duy nhất trong đội vận hành thao tác trực tiếp trên hệ thống** — gồm cả các xác nhận trạng thái chuyến trước đây gán cho tài xế (mục 8.3), vì tài xế không có tài khoản (mục 3.2).

1. Xem danh sách chuyến mình được phân công; tại **mỗi điểm** của tuyến, xem danh sách khách cần **lên** tại điểm đó (`diem_don_id` = điểm hiện tại) và khách cần **xuống** tại điểm đó (`diem_tra_id` = điểm hiện tại), không chỉ danh sách chung cho cả chuyến.
2. Xác nhận xuất phát đúng giờ tại điểm đầu tuyến → chuyến chuyển `dang_chay`.
3. **Khi khách lên xe**: khách xuất trình **vé cứng** (đã lấy tại văn phòng — mục 8.1 điểm 5) cho phụ xe → phụ xe xác nhận trên hệ thống → đánh dấu `da_len_xe`.
4. **Khi khách xuống xe**: phụ xe **chủ động xác nhận trên hệ thống** khi khách xuống đúng điểm trả (không chỉ nhắc miệng) → đánh dấu `da_xuong_xe` — giúp phụ xe đối chiếu đúng số khách còn lại trên xe sau mỗi điểm dừng, tránh sót khách ngủ quên/xuống nhầm điểm.
5. **Xác nhận đã đến từng điểm trung gian** trên hành trình (không chỉ điểm cuối) → ghi nhận giờ thực tế, dùng để cập nhật ETA cho khách đang chờ đón ở các điểm phía sau (báo qua WebSocket, mục 8.1) và kích hoạt đúng danh sách lên/xuống của điểm đó (điểm 1).
6. Trước giờ khởi hành tại **điểm đón của từng khách** X phút (cấu hình được, VD 5 phút), với **mọi vé chưa `da_len_xe` tại điểm đó** — dù đã `da_thanh_toan` hay đang `giu_cho` (chọn "thanh toán tại quầy" nhưng chưa từng ra quầy trả tiền) — → đánh dấu `khong_den` (mục 9). **Cùng mốc X phút này cũng là hạn chót để khách tự hủy giữ chỗ** (mục 7, mục 8.1 điểm 6) — qua mốc đó khách không tự hủy được nữa.
7. **Báo sự cố giữa đường** (hỏng xe, tai nạn, tắc đường nghiêm trọng — theo thông tin tài xế cung cấp, phụ xe là người thao tác trên hệ thống) → chuyến chuyển `gap_su_co`, điều độ viên nhận cảnh báo ngay; báo các bất thường khác chưa tới mức sự cố cho điều độ viên khi cần.
8. Xác nhận đến điểm cuối cùng của tuyến → chuyến chuyển `hoan_thanh`.
9. Xác nhận đã chất/dỡ hàng gửi (`don_hang`, mục 10) tại từng điểm dừng, song song với soát vé hành khách — báo thất lạc/hư hỏng nếu có.

**Ngoại lệ:**
- Không tự ý hủy chuyến — mọi quyết định hủy/điều xe thay thế thuộc về điều độ viên (mục 8.6), phụ xe chỉ báo cáo tình trạng thực tế.

**Giao diện & cách thao tác trên hệ thống** (chỉ phụ xe dùng — tài xế không có tài khoản, mục 3.2/8.3 — 1 giao diện di động riêng, khác hẳn giao diện khách hàng):

- Dùng **điện thoại thông thường của nhân viên**, không cần thiết bị quét chuyên dụng — giao diện web di động (responsive), đăng nhập bằng tài khoản cá nhân (`nhan_vien_van_hanh`).
- Sau đăng nhập, hệ thống **tự hiển thị đúng chuyến đang/sắp chạy của xe mình thuộc biên chế** (mục 3.2) — không cần tự tìm/chọn chuyến giữa hàng loạt chuyến của toàn hệ thống.
- **Không quét mã (không QR, không camera)** — khách xuất trình **vé cứng** (in tại văn phòng khi khách tới lấy, mục 8.1 điểm 5), phụ xe nhìn thông tin trên vé (số ghế, họ tên) rồi **thao tác trực tiếp trên màn hình**: danh sách khách cần lên/xuống tại điểm hiện tại (điểm 1) đã hiển thị sẵn theo số ghế — phụ xe tìm đúng dòng khớp với vé, bấm xác nhận → hệ thống tự đánh dấu `da_len_xe`/`da_xuong_xe` tương ứng. Nếu không tìm thấy đúng dòng ngay (VD trùng tên), tra thêm theo mã vé dạng chữ in trên vé cứng để chắc chắn đúng người.
- Cách này đơn giản hơn cơ chế quét (không cần camera hoạt động tốt/ánh sáng đủ), phù hợp thao tác nhanh khi khách xếp hàng lên xe — chỉ cần màn hình hiển thị danh sách và vài lần chạm.
- **Chất hàng gửi (mục 10.2, UC-26) dùng đúng kiểu thao tác này, chỉ khác thứ để khớp**: màn hình hiển thị danh sách đơn hàng đang chờ tại điểm hiện tại, cùng `tuyen_id` với chuyến mình đang chạy, sắp theo thời gian nhận hàng (đơn cũ hiện trước, chỉ để tham khảo thứ tự ưu tiên). Mỗi dòng hiện `mã vận đơn` + tên người nhận + điểm đến + cân nặng (tham khảo khi ước lượng còn chỗ). Phụ xe cầm từng kiện hàng, đọc **mã vận đơn in trên nhãn dán** (mục 10.4.1), tìm đúng dòng khớp trong danh sách — không bắt buộc theo đúng thứ tự hiển thị, có thể bỏ qua 1 đơn không xếp vừa để chọn đơn khác — bấm xác nhận ngay khi đã đặt lên xe, hệ thống tự gán `chuyen_id` = đúng chuyến mình đang chạy cho đơn đó.
- **Giả định có sóng di động dọc tuyến** (hợp lý với hạ tầng viễn thông hiện tại) — không làm đồng bộ offline phức tạp trong phạm vi BTL; nếu nhóm dư thời gian có thể nâng cấp cache danh sách vé trước khi xuất phát + đồng bộ lại khi có mạng.

### 8.3. Tài xế (`chuc_danh = tai_xe`) — không có tài khoản

**Tài xế không đăng nhập/thao tác trên hệ thống.** Chỉ là 1 dòng hồ sơ nhân sự trong biên chế xe (`xe_nhan_su`, mục 3.2), do `quan_ly` quản lý — dùng để nhà xe biết ai đang lái xe nào (liên hệ, hồ sơ nhân sự), không phục vụ đăng nhập.

- **Việc 2 tài xế thay phiên lái** hoàn toàn do họ tự thu xếp nội bộ — hệ thống không theo dõi/ràng buộc giờ nghỉ theo từng tài xế (mục 3.2).
- **Mọi xác nhận trạng thái chuyến** (xuất phát, đến từng điểm, báo sự cố, hoàn thành) đều do **phụ xe** thao tác trên hệ thống (mục 8.2) — tài xế chỉ cung cấp thông tin bằng lời cho phụ xe khi cần (VD mô tả sự cố), lý do: tài xế không nên thao tác điện thoại khi đang lái, và phụ xe đã sẵn có tài khoản/thiết bị cho việc soát vé.

### 8.4. Nhân viên quầy vé (`nhan_vien_quay_ve`)

Chỉ thao tác trong phạm vi văn phòng mình được gán.

1. Bán vé trực tiếp cho khách vãng lai tại quầy (không cần tài khoản khách hàng) — nhập tên + SĐT, chọn ghế, thu tiền (tiền mặt hoặc chuyển khoản QR VNPay), tạo vé `da_thanh_toan` ngay, in vé cứng đưa khách luôn.
2. **Bán vé qua hotline**: nhận cuộc gọi, thực hiện y hệt luồng bán tại quầy (điểm 1) thay khách qua điện thoại — khác biệt duy nhất là khách **chưa cầm vé cứng ngay** (họ sẽ ra đúng văn phòng đã chọn làm điểm đón để nhận trước giờ khởi hành, theo điểm 3 dưới).
3. **In vé cứng cho khách đã đặt online/hotline khi họ ra văn phòng nhận** (mục 8.1 điểm 5) — tra theo mã đặt chỗ hoặc SĐT, xác minh đúng người. Nếu vé đang ở `giu_cho` (khách chọn "thanh toán tại quầy", mục 3.4/6) → **thu tiền trước** (tiền mặt hoặc chuyển khoản QR VNPay), chuyển `da_thanh_toan`, rồi mới in; nếu vé đã `da_thanh_toan` từ trước (thanh toán ngay online, hoặc đã thu qua hotline) → in thẳng. Đây là bước bắt buộc trước khi khách có thể lên xe (phụ xe chỉ xác nhận dựa trên vé cứng, mục 8.2).
4. **Hỗ trợ đăng ký tài khoản cho khách tại quầy** (mục 2.1) — dành cho khách không rành thao tác email/OTP (VD người lớn tuổi): nhập giúp thông tin đăng ký, đọc/nhập hộ mã OTP nếu khách đọc được mã trên điện thoại/hộp thư của họ. Với khách hoàn toàn không muốn/không thể dùng email, vẫn luôn có lựa chọn **mua vé không cần tài khoản** (điểm 1) — không bắt buộc ai cũng phải có tài khoản mới mua được vé.

**Không xử lý hoàn tiền** (kể cả khi khách ra quầy/gọi hotline hỏi) — vé trả qua chuyển khoản được hoàn tự động qua cổng, còn vé trả tiền mặt do `ke_toan` chủ động liên hệ và chuyển khoản (mục 7, UC-22, mục 8.8). Nhân viên quầy vé chỉ có quyền **tra cứu (xem, không sửa)** tình trạng hoàn tiền theo mã đặt chỗ/SĐT để trả lời khách khi được hỏi (VD "đang chờ kế toán xử lý" / "đã chuyển khoản ngày X") — không tự xử lý hay đổi trạng thái; nếu khách phàn nàn chờ quá lâu thì báo lên `quan_ly`.

### 8.5. Nhân viên gửi hàng (`nhan_vien_gui_hang`)

Vai trò **tách riêng** khỏi `nhan_vien_quay_ve` — không bán vé, không soát vé hành khách. Chỉ thao tác trong phạm vi văn phòng mình được gán.

1. **Tại điểm gửi**: nhận hàng từ người gửi, cân/đo, kiểm tra không thuộc danh mục hàng cấm (mục 10.1), chọn **tuyến** (không phải chuyến cụ thể, mục 10.2) + điểm nhận, **tự quyết định và nhập giá cước** dựa trên cân nặng/loại hàng/điểm đến, tạo `don_hang` trạng thái `cho_van_chuyen`, in mã vận đơn, thu tiền nếu `nguoi_gui_tra_truoc`.
2. **Tại điểm nhận**: **chủ động gọi điện thoại báo người nhận** khi hàng vừa tới (mục 10.3.1 — không còn SMS, đây là kênh báo tin duy nhất). Khi người nhận tới lấy, nhập `ma_van_don` họ đọc lại để xác minh, thu COD nếu `cod_nguoi_nhan_tra`, đánh dấu `da_giao`.
3. Xử lý hàng chờ quá lâu tại điểm nhận (mục 10.3/10.3.1, UC-25) — theo cờ cảnh báo (7 ngày) hoặc "hàng tồn" (14 ngày) hệ thống tự bật, gọi lại người nhận hoặc người gửi tùy tình huống, báo lên `quan_ly` nếu không liên hệ được ai.

### 8.6. Điều độ viên (`dieu_do_vien`)

Chỉ thao tác chuyến **xuất phát từ** văn phòng mình được gán.

1. **Gán xe cho chuyến** (UC-44, mục 3.5): các chuyến đã được hệ thống tự sinh sẵn từ lịch chạy định kỳ do `quan_ly` thiết lập (UC-18) — điều độ viên **chọn 1 xe cụ thể** đúng `loai_xe` đã cam kết, trong số xe đủ điều kiện — hệ thống chặn nếu trùng lịch (mục 3.2), sai nhóm tuyến (mục 3.2), hoặc xe không có mặt đúng điểm khởi hành (mục 3.3). Có thể gán lại (đổi xe) bất cứ lúc nào trước giờ khởi hành. Hệ thống nhắc nếu chuyến còn ≤48 tiếng mà chưa gán xe. **Không cần chọn tài xế/phụ xe** — cả hai đều tự suy ra từ biên chế cố định của xe (mục 3.2), không phải thao tác của điều độ viên. Điều độ viên **không tự tạo chuyến hay tuyến mới**. Nếu tìm mãi không ra xe và chuyến đã tới đúng giờ khởi hành mà vẫn chưa gán được → hệ thống **tự động** chuyển sang "đang hoãn" (UC-45 ⏱, mục 3.3) — điều độ viên tiếp tục gán xe qua UC-44 như bình thường cho tới khi có, không có gì thay đổi trong thao tác gán, chỉ khác lúc gán thành công thì tắt luôn cờ "đang hoãn".
2. **Theo dõi tỷ lệ lấp đầy ghế**: chỉ mang tính thống kê/tham khảo (VD để cân nhắc điều xe lớn/nhỏ hơn cho các chuyến sau) — **không dùng để hủy chuyến**, vì chuyến đã lên lịch luôn phải chạy dù ít khách đến đâu (mục 1). Khối lượng hàng **không do điều độ viên theo dõi** — việc xếp hàng hoàn toàn do phụ xe tự đánh giá trực tiếp lúc chất hàng (mục 10.2).
3. **Cho xe khác chạy thay trước giờ khởi hành** (VD xe hỏng đột xuất khi chuyến còn `chua_khoi_hanh`): gán `chuyen_xe.xe_thuc_te_id` sang xe khác đủ điều kiện, bắt buộc cùng `loai_xe` — **không đổi `xe_id` gốc**, nên biên chế tài xế/phụ xe không đổi. Áp dụng cho cả chuỗi chuyến tương lai của xe hỏng, tới khi điều độ viên chủ động gán lại — chi tiết cơ chế (ưu tiên xe dự phòng nội bộ, sau đó xe thuê ngoài, chưa tìm được kịp thì hoãn giờ khởi hành chứ **không bao giờ hủy chuyến**) ở mục 3.3.
3b. **Gán lại xe gốc khi đã sửa xong**: khi xe hỏng chuyển lại `hoat_dong` (UC-34), điều độ viên nhận thông báo, tự xem lại các chuyến đang gắn cờ "chạy thay" và chọn thời điểm phù hợp để trả `xe_thuc_te_id` về đúng xe gốc — hoàn toàn thủ công, hệ thống chỉ nhắc, không tự đổi.
4. **Xử lý sự cố giữa đường** (`gap_su_co`, chuyến đã `dang_chay`): đánh giá theo nguyên nhân (`loi_nha_xe`/`loi_khach_quan`) và mức độ (nhẹ tự khắc phục, hay cần điều xe thay thế) — chi tiết đầy đủ cơ chế ở mục 3.3/4. Lỗi nhà xe luôn tìm được xe thay thế cuối cùng, chỉ khách quan mới có thể phải hủy phần còn lại (hoàn 100%, mục 7) khi thực sự không thể tiếp tục.
5. **Xử lý phát sinh nhân sự**: phụ xe báo nghỉ (dù đột xuất sát giờ hay biết trước dài ngày), hoặc cả 2 tài xế cố định của xe đều không thu xếp được (báo qua phụ xe) → sửa `xe_nhan_su` để tìm người thay thế tạm thời (mục 3.2 — chuyển người vắng sang `tam_nghi`, thêm dòng `tam_thoi` cho người thay), hoặc báo lên `quan_ly` nếu không đủ nhân sự khả dụng.
6. Xem thống kê vận hành của các điểm/tuyến mình phụ trách.

### 8.7. Quản lý (`quan_ly`)

1. Quản lý danh mục: `khu_vuc` (điểm đi/đến), `diem_don_tra` (điểm đón/trả, kể cả văn phòng), `tuyen`/`nhom_tuyen` (kể cả thứ tự + thời gian dự kiến từng điểm trong `tuyen_diem_don_tra`), `loai_xe` (danh mục loại xe — quyết định chung hệ số giá, sơ đồ ghế cho mọi xe cùng loại, tự thêm tùy ý — mục 3.1), `gia_ve` theo từng cặp điểm đi/điểm đến (giá gốc, không phân biệt loại xe — nhân với hệ số của `loai_xe` lúc bán, mục 3.1; kể cả giá theo mùa/dịp lễ; **không áp dụng cho hàng gửi**, mục 10.1, do nhân viên gửi hàng tự quyết định giá), danh mục `loai_hang` (kể cả hàng cấm), `xe` (thêm/sửa/đổi trạng thái bảo trì, gán/gỡ `nhom_tuyen_id` cố định, gán `loai_xe`, quản lý biên chế **cố định** `xe_nhan_su` (`loai = co_dinh`) — 2 tài xế + phụ xe mỗi xe; các thay đổi **tạm thời** (`loai = tam_thoi`, khi có người nghỉ) do điều độ viên tự xử lý (mục 3.2, mục 8.6), chỉ báo lên `quan_ly` khi không tìm được người thay).
1b. **Thiết lập lịch chạy định kỳ** (UC-18, mục 3.5): chọn tuyến + giờ khởi hành + loại xe dự kiến — hệ thống tự động sinh sẵn chuyến cho N ngày tới (N do `quan_ly` cấu hình), chưa gán xe cụ thể. Đây là cách duy nhất để có chuyến mới trong hệ thống — điều độ viên không tự tạo chuyến, chỉ gán xe (mục 8.6).
2. Tạo tài khoản cán bộ (nhân viên vận hành, nhân viên quầy vé, nhân viên gửi hàng, điều độ viên, kế toán) — riêng `ke_toan` không cần gán văn phòng (mục 2). **Chỉ tài khoản `quan_ly` gốc** (`la_tai_khoan_goc = true`, seed lúc khởi tạo, mục 2) mới tạo thêm được tài khoản `quan_ly` khác hoặc `quan_ly_nhan_su` — các `quan_ly` không phải gốc không tạo được 2 loại tài khoản này (mục 8.9).
3. Cấu hình các tham số nghiệp vụ: 2 mốc hạn giữ ghế (thanh toán ngay / thanh toán tại quầy — mục 6), ngưỡng giá trị + tỷ lệ bắt buộc đặt cọc cho lô nhiều vé (mặc định 600.000đ / 50%, mục 3.4), ngưỡng no-show, **số ngày sinh chuyến trước và ngưỡng nhắc gán xe (mặc định 48 tiếng, mục 3.5)**.
4. Xem thống kê toàn hệ thống: doanh thu theo tuyến/điểm/ngày, tỷ lệ lấp đầy trung bình, chuyến bị hủy/sự cố, hiệu suất tài xế, **tổng tiền đã/đang chờ hoàn theo lý do** (từ `lich_su_hoan_tien`, mục 7) — biết được có bao nhiêu khoản còn tồn đọng chưa xử lý.
5. Xử lý khiếu nại nghiêm trọng, khóa/mở khóa tài khoản (khách hàng lẫn cán bộ) — không xóa vĩnh viễn, giữ lịch sử. **Tài khoản `quan_ly` gốc không thể bị khóa bởi bất kỳ ai, kể cả `quan_ly` khác** — tránh trường hợp toàn bộ `quan_ly` lỡ khóa lẫn nhau, không còn ai vào được hệ thống.
6. Xem xét gỡ hạn chế đặt vé cho khách hàng bị khóa do no-show (mục 9) — thao tác thủ công, tương tự cơ chế "xem xét gỡ cấm" ở bản trước.

### 8.8. Kế toán (`ke_toan`)

Phạm vi **toàn hệ thống** (không gắn văn phòng, mục 2) — chỉ xử lý phần hoàn tiền không tự động được qua cổng thanh toán.

1. Xem **danh sách hoàn tiền đang chờ xử lý** (`lich_su_hoan_tien.trang_thai = 'cho_xu_ly'`) trên toàn hệ thống — phát sinh khi khách trả tiền mặt (hoặc API hoàn tiền VNPay thất bại) ở bất kỳ trường hợp nào: chuyến hoãn trước giờ chạy (UC-41), sự cố lỗi nhà xe giữa đường (UC-42/43), hoặc sự cố khách quan không thể hoàn thành (UC-21).
2. **Chủ động gọi điện khách** (theo số đã lưu — tài khoản hoặc `sdt_khach_vang_lai`) xin thông tin tài khoản ngân hàng, thực hiện chuyển khoản qua ứng dụng ngân hàng công ty (**ngoài phạm vi hệ thống**), sau đó **nhập lại số tài khoản/tên ngân hàng/tên chủ tài khoản vào hệ thống** để lưu vết đối soát nếu sau này phát sinh tranh chấp, rồi đánh dấu hoàn tất (UC-22).
3. Không bán vé, không thao tác gì liên quan vận hành xe/chuyến.

**Kế toán không có hotline riêng, không nhận cuộc gọi đến từ khách** — chỉ **gọi đi** theo đúng số đã lưu sẵn trong hệ thống. Khách muốn hỏi về hoàn tiền vẫn gọi vào hotline của nhân viên quầy vé như bình thường (mục 8.4) — nhân viên quầy vé tra cứu tình trạng trả lời khách, không chuyển máy hay đưa số kế toán cho khách. Thiết kế này vừa giữ đúng 1 đầu mối liên hệ duy nhất cho khách, vừa tránh bị mạo danh gọi tới yêu cầu chuyển khoản.

### 8.9. Quản lý nhân sự (`quan_ly_nhan_su`)

Phạm vi **toàn hệ thống** (không gắn văn phòng, giống `ke_toan`/`quan_ly`, mục 2) — sinh ra để san bớt việc tạo/khóa tài khoản nhân sự vận hành khỏi `quan_ly` khi quy mô công ty lớn (nhiều văn phòng, hàng trăm nhân sự). Chỉ xử lý tài khoản/nhân sự cấp vận hành — **không có quyền nghiệp vụ nào khác** (không sửa tuyến, giá, xe, khuyến mãi, lịch chạy định kỳ).

1. Tạo tài khoản cho đúng **4 vai trò**: `nhan_vien_van_hanh` (phụ xe), `nhan_vien_quay_ve`, `nhan_vien_gui_hang`, `dieu_do_vien` — qua đúng cơ chế mời như `quan_ly` (mục 8.7 điểm 2). **Không** tạo được tài khoản `ke_toan`, `quan_ly`, hay `quan_ly_nhan_su` khác — các vai trò này nhạy cảm hơn (tiền, hoặc chính quyền quản trị), chỉ `quan_ly` (với `ke_toan`) hoặc `quan_ly` gốc (với `quan_ly`/`quan_ly_nhan_su`) mới tạo được.
2. Khóa/mở khóa tài khoản cho đúng 4 vai trò trên — không đụng được tới `ke_toan`/`quan_ly`/`quan_ly_nhan_su` khác.
3. Xem thống kê toàn hệ thống (UC-39), cùng phạm vi như `quan_ly`.
4. Chỉ **tài khoản `quan_ly` gốc** (mục 2, mục 8.7 điểm 2) mới tạo được tài khoản `quan_ly_nhan_su` — không tự đăng ký, không được `quan_ly_nhan_su` khác hay `quan_ly` không phải gốc tạo hộ.

---

## 9. Cơ chế no-show và hạn chế

- **1 loại vi phạm duy nhất** cho `khach_hang` (vé vãng lai tại quầy không tính, vì không gắn tài khoản để theo dõi được): đến giờ khởi hành tại điểm đón mà vé vẫn chưa `da_len_xe` → chuyển `khong_den` (mục 8.2 điểm 6). Áp dụng như nhau cho cả 2 trường hợp — vé đã `da_thanh_toan` nhưng không lên xe, lẫn vé chọn "thanh toán tại quầy" nhưng chưa từng ra quầy trả tiền (vì không còn `het_han` cho trường hợp này, mục 3.4/5/6 — thẳng tới `khong_den`).
- Đủ N lần trong M ngày gần nhất (mặc định 3 lần / 30 ngày, `quan_ly` cấu hình) → tự động **khóa lựa chọn "thanh toán tại quầy"** — khách chỉ còn được đặt vé với **"thanh toán ngay"** (hạn giữ 5 phút), không thể đặt vé "chiếm chỗ tự do không hạn" nữa; **khóa tạm** tài khoản nếu vi phạm nghiêm trọng hơn ngưỡng thứ 2.
- Gỡ hạn chế: `quan_ly` xem xét thủ công theo từng trường hợp.

---

## 10. Dịch vụ gửi hàng (không kèm hành khách)

Ngoài chở khách, nhà xe còn nhận gửi hàng hóa độc lập — người gửi mang hàng tới quầy, **không cần đi cùng chuyến**; người nhận là người khác, ra nhận tại điểm đến. Không nói tới hành lý xách tay của khách đi xe (mặc định đi kèm miễn phí, ngoài phạm vi hệ thống) — mục này chỉ nói tới hàng gửi độc lập. Đây là mảng nghiệp vụ **tách biệt khỏi vé hành khách** nhưng **dùng chung hạ tầng tuyến/chuyến/điểm đi-đến/điểm đón-trả** đã có, không tạo khái niệm địa điểm mới.

### 10.1. Mô hình dữ liệu

- `don_hang`: `tuyen_id` (tuyến khách muốn gửi qua — chọn lúc nhận hàng, **thay vì** chọn 1 chuyến cụ thể, mục 10.2), `chuyen_id` (**nullable** — chỉ có giá trị **sau khi** phụ xe thực sự chất hàng lên 1 chuyến cụ thể, mục 10.2/UC-26; `NULL` nghĩa là đơn còn đang chờ, chưa biết đi chuyến nào), `diem_gui_id`/`diem_nhan_id` (tham chiếu `diem_don_tra` — **khác vé hành khách**: cả 2 đầu **bắt buộc là `van_phong`**, không được là `diem_dung`, vì gửi/nhận hàng luôn cần nhân viên gửi hàng thao tác tại quầy ở cả 2 đầu, mục 3.1), `can_nang_kg`, kích thước (dài×rộng×cao hoặc quy đổi thể tích — vẫn cân đo để nhân viên tham khảo lúc định giá, mục 10.2, **không** dùng để tính sức chứa xe), `loai_hang` (thường/dễ vỡ/hàng lạnh/tài liệu — `quan_ly` cấu hình danh mục; hàng cấm bị chặn ngay khi tạo đơn), `gia_cuoc`, `nguoi_gui`/`nguoi_nhan` (tên + SĐT, không cần tài khoản — **không thu email**, vì đây là người vãng lai không đăng ký tài khoản, khác khách hàng ở mục 2.1), `phuong_thuc_thanh_toan` (`nguoi_gui_tra_truoc` / `cod_nguoi_nhan_tra`), `ma_van_don` (mã tra cứu **duy nhất mỗi đơn**, in trên biên nhận đưa cho người gửi lúc tạo đơn — không gửi qua SMS/email tự động, vì không có kênh nào phù hợp cho người nhận không có tài khoản; dùng làm mã xác minh khi giao hàng, mục 10.3), `trang_thai`.
- **Chỉ tạo được tại quầy** (`nhan_vien_gui_hang`, mục 8.5 — tách riêng khỏi `nhan_vien_quay_ve`) — không có luồng khách tự đặt gửi hàng online, vì cần cân/đo/kiểm tra hàng thực tế trước khi nhận (quyết định đơn giản hóa có chủ đích, cùng tinh thần với mục 3.4 — nếu nhóm dư thời gian có thể mở thêm luồng "đặt hẹn gửi hàng online" sau, không đổi mô hình dữ liệu ở trên).
- **Không còn khái niệm "sức chứa khoang hàng" tính bằng hệ thống** (bỏ hẳn `loai_xe.suc_chua_hang_kg` so với thiết kế trước, mục 10.2) — xếp hàng lên xe thực tế phụ thuộc hình dạng/thể tích, không thể tính đúng chỉ bằng số kg cộng dồn (khác ghế, vốn là 1 vị trí rời rạc đếm được); việc "còn chỗ hay không" giao hẳn cho phụ xe đánh giá trực tiếp lúc chất hàng, hệ thống không tự động chặn/tính toán gì cả.
- **Giá cước KHÔNG tính tự động** (khác hẳn `gia_ve` — mục 3.1, vốn cố định do `quan_ly` cấu hình): `nhan_vien_gui_hang` **tự nhập tay** `gia_cuoc` trực tiếp khi tạo đơn, dựa trên kinh nghiệm về cân nặng/kích thước/loại hàng/điểm đến — hệ thống chỉ lưu lại đúng số nhân viên nhập, không có công thức hay bảng giá nào ràng buộc/gợi ý.

### 10.2. Chất hàng lên xe — chọn tuyến trước, xác định chuyến cụ thể lúc xếp hàng thực tế

Khác với ghế (mục 6 — hệ thống tự tính chống trùng chính xác bằng số liệu vì ghế là vị trí rời rạc, đếm được), việc "xe còn chỗ chứa hàng hay không" **không tính đúng được chỉ bằng số kg cộng dồn** — 2 kiện hàng nặng bằng nhau có thể khác hẳn về hình dạng/thể tích, chỉ con người đứng trước khoang hàng thực tế mới biết có xếp vừa hay không. Vì vậy hệ thống **không tự động chống quá tải** như với ghế — toàn bộ quyết định "được xếp hay không, xếp được bao nhiêu" thuộc về con người (phụ xe):

- **Lúc nhận hàng (UC-23, nhân viên gửi hàng)**: khách chỉ cần cho biết muốn gửi tới đâu — nhân viên chọn **tuyến** phù hợp (không phải 1 chuyến cụ thể với giờ chạy nhất định). Đơn hàng tạo ra ở trạng thái `cho_van_chuyen`, gắn `tuyen_id`, **`chuyen_id` để trống** — chưa biết sẽ đi chuyến nào, xe gì, loại xe gì; **bất kỳ xe nào, loại xe nào chạy đúng tuyến này đều hợp lệ để chở**, không ràng buộc gì thêm.
- **Lúc chất hàng thực tế (UC-26, phụ xe)**: mỗi khi có 1 chuyến (bất kỳ xe/loại xe nào) chuẩn bị xuất phát hoặc đi qua điểm đang đứng, phụ xe xem danh sách đơn hàng đang `cho_van_chuyen` cùng đúng `tuyen_id` với chuyến này, sắp theo **thứ tự thời gian tạo đơn (đơn cũ hiện trước)** — đây là **thứ tự ưu tiên hiển thị để tham khảo, không phải ràng buộc cứng**: phụ xe có thể bỏ qua 1 đơn không xếp vừa (hàng cồng kềnh) để lấy đơn tiếp theo trong danh sách, tùy đánh giá thực tế của mình. Xếp được bao nhiêu đơn hoàn toàn do phụ xe tự quyết theo khoang hàng thực tế của xe đang chạy chuyến đó.
- Với mỗi đơn phụ xe xác nhận đã xếp lên xe → hệ thống mới gán `chuyen_id` = chuyến đó, chuyển `da_len_xe` (UC-26). Đơn chưa được chọn vẫn giữ nguyên `cho_van_chuyen`, `chuyen_id` vẫn để trống, tự động còn hợp lệ cho chuyến tiếp theo cùng tuyến — **không cần thao tác "dời chuyến" nào**, vì đơn chưa từng gắn với 1 chuyến cụ thể để phải dời.
- Vẫn cân/đo hàng lúc nhận (`can_nang_kg`, kích thước, mục 10.1) — chỉ để nhân viên gửi hàng tham khảo khi tự định giá cước, **không** dùng để tính toán/chặn sức chứa nào cả.

### 10.3. Vòng đời đơn hàng

```
cho_van_chuyen (đã nhận hàng tại quầy gửi, chuyen_id còn để trống, chờ 1 chuyến bất kỳ cùng tuyen_id có chỗ)
  └─ [Phụ xe chọn xếp lên 1 chuyến cụ thể — mục 10.2/UC-26, lúc này chuyen_id mới được gán] → da_len_xe
                                                       └─ [Xe tới điểm nhận, phụ xe xác nhận đã dỡ hàng — mục 8.2] → cho_lay (bắt đầu tính mốc thời gian chờ, mục 10.3.1)
                                                                                   ├─ [Người nhận ra lấy, giao đúng theo mục 10.3.1] → da_giao
                                                                                   ├─ [Đủ 7 ngày kể từ lúc tới điểm nhận, vẫn chưa ai lấy — UC-46 ⏱] → vẫn cho_lay, chỉ bật cờ cảnh báo, nhắc nhân viên gọi lại (mục 10.3.1)
                                                                                   └─ [Đủ 14 ngày kể từ lúc tới điểm nhận, vẫn chưa ai lấy — UC-46 ⏱] → qua_han_luu_kho ("hàng tồn", KHÔNG tự hủy — nhân viên xử lý thủ công qua UC-25, liên hệ người gửi/thanh lý)
```

#### 10.3.1. Thông báo & xác minh khi giao hàng — không còn kênh tự động (SMS/email), toàn bộ thủ công

Khác với khách hàng (có tài khoản + email, mục 2.1), **người gửi/người nhận hàng không có tài khoản và không thu email** — hệ thống không có kênh nào để tự động báo tin cho họ. Toàn bộ khâu thông báo đổi thành thủ công, dựa trên 2 điểm chạm đã có sẵn:

1. **Lúc tạo đơn** (mục 10.4.1): ngoài nhãn dán lên kiện hàng, hệ thống in thêm **1 biên nhận riêng đưa cho người gửi**, ghi rõ `ma_van_don` + điểm nhận + thông tin liên hệ điểm nhận. Người gửi **tự báo mã này cho người nhận** qua liên lạc cá nhân của họ (điện thoại, tin nhắn riêng...) — ngoài phạm vi hệ thống, đúng thói quen thực tế phổ biến khi gửi hàng qua xe khách.
2. **Khi hàng tới điểm nhận** (`cho_lay`): `nhan_vien_gui_hang` **chủ động gọi điện thoại** cho người nhận theo SĐT trên đơn để báo hàng đã tới (không còn là bước "dự phòng khi cần" như trước — giờ là bước bắt buộc duy nhất để báo tin, vì không còn kênh tự động nào khác). Nhân viên có thể đọc lại `ma_van_don` qua điện thoại nếu người nhận chưa có/quên mã từ người gửi. **Gọi thành công thì tích xác nhận "đã thông báo được người nhận" trên hệ thống** — hệ thống chỉ lưu đúng 1 cờ này (đã/chưa), không đếm số cuộc gọi cụ thể; nếu chưa gọi được ngay, nhân viên tự chủ động thử gọi lại thêm vài lần trong 1-2 ngày đầu theo kinh nghiệm thực tế (không phải quy tắc cứng của hệ thống) trước khi tích được.
3. **Nếu quá 7 ngày kể từ lúc hàng tới mà vẫn chưa có ai tới lấy** (UC-46 ⏱, tự động): hệ thống bật cờ cảnh báo, nhắc nhân viên xử lý tiếp — nếu **đã** tích "đã thông báo được" trước đó → gọi lại người nhận hỏi khi nào tới lấy, hoặc gọi người gửi nếu cần; nếu **chưa từng** thông báo được (mất liên lạc hoàn toàn với người nhận ngay từ đầu) → chuyển hẳn sang gọi **người gửi** để hỏi hướng xử lý luôn, không cần tiếp tục cố liên lạc người nhận nữa.
4. **Nếu quá 14 ngày** vẫn chưa ai tới lấy (UC-46 ⏱) → đơn chuyển hẳn "hàng tồn" (`qua_han_luu_kho`) — **không tự hủy**, chờ nhân viên xử lý thủ công theo đúng UC-25 (liên hệ người gửi theo thỏa thuận, hoặc báo `quan_ly` thanh lý nếu không liên hệ được ai).
5. Khi người nhận tới quầy, họ đọc `ma_van_don` (đã biết từ người gửi hoặc từ cuộc gọi của nhân viên) cho `nhan_vien_gui_hang` để tra đúng đơn — nếu quên mã, tra theo SĐT + xác minh thêm tên.
6. Nếu `phuong_thuc_thanh_toan = cod_nguoi_nhan_tra` → thu tiền COD trước khi giao; nếu `nguoi_gui_tra_truoc` → giao thẳng, không thu thêm.
7. Xác nhận giao → `da_giao`, ghi nhận thời điểm + nhân viên xử lý.

### 10.4. Thao tác cụ thể của nhân viên gửi hàng trên hệ thống

#### 10.4.1. Khi khách tới **gửi** hàng

1. Đăng nhập bằng tài khoản `nhan_vien_gui_hang` — hệ thống tự biết điểm gửi = văn phòng nhân viên đang gắn (mục 2), không cần chọn lại.
2. Vào màn "Tạo đơn gửi hàng" → nhập người gửi (tên + SĐT) và người nhận (tên + SĐT, dùng để nhân viên điểm nhận gọi điện báo khi hàng tới — mục 10.3.1) — cả hai không cần có tài khoản, không thu email.
3. Chọn **điểm đến** (khu_vực) rồi **văn phòng nhận cụ thể** (`diem_nhan_id`, chỉ được chọn `loai = 'van_phong'`, mục 10.1) trong khu_vực đó — cùng cơ chế 2 tầng điểm đi/đến → điểm đón/trả như đặt vé (mục 3.4).
4. Hệ thống xác định **tuyến** đi từ đúng điểm gửi tới điểm nhận đã chọn (nếu có nhiều tuyến cùng nối 2 điểm này, nhân viên chọn 1) — **không chọn chuyến cụ thể nào cả** (mục 10.2): bất kỳ chuyến nào sau này chạy đúng tuyến này, dù xe gì, loại xe gì, cũng hợp lệ để chở đơn hàng.
5. Cân/đo hàng thực tế, nhập `can_nang_kg` + kích thước + chọn `loai_hang` từ danh mục có sẵn → hệ thống **tự chặn ngay** nếu là hàng cấm (mục 10.2 — **không** còn kiểm tra sức chứa gì ở bước này, việc đó để phụ xe tự đánh giá lúc chất hàng thực tế).
6. Nhân viên **tự nhập `gia_cuoc`** dựa trên cân nặng, loại hàng, điểm đến vừa chọn (kinh nghiệm cá nhân — hệ thống không tự tính, không gợi ý), rồi báo giá cho khách xác nhận trước khi tạo đơn.
7. Chọn `phuong_thuc_thanh_toan`: `nguoi_gui_tra_truoc` (thu tiền mặt ngay tại đây) hoặc `cod_nguoi_nhan_tra` (không thu, để người nhận trả).
8. Xác nhận tạo đơn → hệ thống sinh `ma_van_don`, đơn chuyển `cho_van_chuyen`, in **2 bản**: (a) nhãn dán lên kiện hàng (mã vận đơn + điểm đến + SĐT người nhận) để phụ xe và nhân viên điểm nhận đối chiếu, và (b) **biên nhận riêng đưa cho người gửi** (mục 10.3.1) để họ tự báo mã vận đơn cho người nhận.
9. Nhân viên dán nhãn, xếp hàng vào khu vực chờ đúng **tuyến** (chưa biết chuyến cụ thể nào, mục 10.2) — chờ phụ xe chọn xếp lên 1 chuyến bất kỳ đi tuyến này (UC-26).

#### 10.4.2. Khi khách tới **nhận** hàng

1. Đăng nhập bằng tài khoản `nhan_vien_gui_hang` tại điểm nhận. Xem "Danh sách đơn đang chờ lấy tại điểm mình" (trạng thái `cho_lay`, có đánh dấu riêng đơn nào đang cảnh báo chờ quá 7 ngày — mục 10.3.1) — với đơn vừa chuyển sang trạng thái này, **chủ động gọi điện báo người nhận ngay** (mục 10.3.1, không còn kênh tự động nào khác) thay vì chờ họ tự tới, rồi **tích xác nhận "đã thông báo được"** trên hệ thống nếu gọi thành công.
2. Vào màn "Tra cứu / Giao hàng" → nhập `ma_van_don` người nhận đọc (đã biết từ người gửi hoặc từ cuộc gọi ở điểm 1). Nếu người nhận làm mất/quên mã, tra theo SĐT + xác minh thêm tên để tìm đúng đơn.
3. Hệ thống hiện chi tiết đơn (người gửi/nhận, cân nặng, cước, phương thức thanh toán) — chỉ cho giao tiếp nếu trạng thái đúng là `cho_lay` (chặn nếu hàng chưa tới hoặc đã giao rồi, tránh giao nhầm/giao 2 lần).
4. Nếu `cod_nguoi_nhan_tra` → hệ thống hiện số tiền cần thu, nhân viên thu tiền mặt, xác nhận đã thu trên hệ thống trước khi cho giao.
5. Bấm "Xác nhận giao hàng" → đơn chuyển `da_giao`, ghi nhận thời điểm + nhân viên xử lý, in biên nhận nếu cần.

### 10.5. Luồng theo vai trò

Trách nhiệm cụ thể theo từng vai trò đã mô tả tại đúng mục của vai trò đó, không lặp lại ở đây: `nhan_vien_gui_hang` (mục 8.5, và chi tiết thao tác ở mục 10.4 — nhận/giao hàng, tính cước, xử lý quá hạn lưu kho), `nhan_vien_van_hanh`/phụ xe (mục 8.2, điểm 9 — xác nhận chất/dỡ hàng song song soát vé, **tự quyết định chọn đơn nào lên xe** theo mục 10.2), `quan_ly` (mục 8.7, điểm 1 — cấu hình danh mục hàng cấm/loại hàng; **không còn cấu hình sức chứa** vì đã bỏ cơ chế tính tự động, mục 10.2).

---

## 11. Ma trận use case tổng hợp

**Nguyên tắc đánh số lại (quan trọng)**: mỗi use case dưới đây chỉ ứng với **đúng 1 trigger và 1 luồng liên tục** — không gộp nhiều sự kiện độc lập (khác thời điểm/khác actor kích hoạt) vào chung 1 use case, để mỗi use case vẽ được **đúng 1 activity diagram hoàn chỉnh**, không bị rẽ nhánh không cùng phiên hoặc lai giữa nhiều đích khác nhau. Ký hiệu `⏱` = trigger là thời gian (job hệ thống), không phải actor người dùng bấm — không nối actor nào trên sơ đồ use case, nhưng vẫn cần 1 activity diagram riêng (mục 12). Ký hiệu `⚠` = **use case ngoại lệ**: chỉ xảy ra khi có sự cố bất thường (xe hỏng, tai nạn...), **không phải thao tác thường ngày** của actor — vẫn vẽ như use case bình thường trên sơ đồ (actor có thực hiện), chỉ khác ở chỗ tần suất/điều kiện kích hoạt, đã ghi rõ trong "Tiền điều kiện" của từng UC.

| # | Use case | khách hàng | phụ xe | tài xế | nhân viên quầy vé | nhân viên gửi hàng | điều độ viên | kế toán | quản lý nhân sự | quản lý |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| UC-01 | Đăng ký tài khoản | ✅ | — | — | — | — | — | — | — | — |
| UC-02 | Đăng nhập | ✅ | ✅ | — (không có tài khoản) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| UC-03 | Quên mật khẩu | ✅ | ✅ | — (không có tài khoản) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| UC-04 | Tra cứu chuyến công khai | ✅ (không cần đăng nhập) | — | — | — | — | — | — | — | — |
| UC-05 | Đặt vé online (chọn ghế, giữ chỗ, thanh toán) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-08 | Hủy giữ chỗ trước khi thanh toán | ✅ (của mình) | ❌ | ❌ | ✅ (thay khách hotline) | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-09 | Bán vé tại quầy | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-10 | Bán vé qua hotline | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-11 | In vé cứng cho khách đặt online/hotline | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-12 | Xác nhận khách lên xe | ❌ | ✅ | — (không có tài khoản) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-13 | Xác nhận khách xuống xe | ❌ | ✅ | — (không có tài khoản) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-14 | Đánh dấu no-show tự động ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-15 | Xác nhận xuất phát | ❌ | ✅ | — (không có tài khoản) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-16 | Xác nhận đến điểm (trung gian/cuối cùng) | ❌ | ✅ | — (không có tài khoản) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-17 | Báo sự cố giữa đường | ❌ | ✅ | — (không có tài khoản) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-18 | Thiết lập lịch chạy định kỳ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-19 | Xử lý sự cố giữa đường ⚠ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| UC-20 | Đổi xe trước giờ khởi hành ⚠ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| UC-21 | Tự động tính & thông báo hoàn tiền ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-22 | Kế toán chuyển khoản hoàn tiền | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| UC-23 | Nhận/gửi hàng tại quầy, tính cước | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-24 | Giao hàng cho người nhận, thu COD | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-25 | Xử lý hàng quá hạn lưu kho | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| UC-26 | Xác nhận chất hàng lên xe | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-27 | Xác nhận dỡ hàng khỏi xe | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-28 | Báo thất lạc/hư hỏng hàng | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-29 | Quản lý khu vực | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-30 | Quản lý điểm đón/trả | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-31 | Tạo tuyến | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-32 | Quản lý loại xe | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-33 | Cấu hình giá vé | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-34 | Quản lý xe | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-35 | Quản lý biên chế xe | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| UC-36 | Tạo tài khoản cán bộ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (4 vai trò vận hành, không `ke_toan`/`quan_ly`/`quan_ly_nhan_su`) | ✅ (mọi vai trò; `quan_ly`/`quan_ly_nhan_su` chỉ tài khoản gốc tạo được) |
| UC-37 | Khóa tài khoản | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (4 vai trò vận hành, không `ke_toan`/`quan_ly`/`quan_ly_nhan_su`) | ✅ (mọi tài khoản; riêng `quan_ly` gốc không ai khóa được) |
| UC-38 | Mở khóa tài khoản | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (4 vai trò vận hành, không `ke_toan`/`quan_ly`/`quan_ly_nhan_su`) | ✅ (mọi tài khoản) |
| UC-39 | Xem thống kê doanh thu/vận hành | ❌ | ✅ (chuyến mình) | — (không có tài khoản) | ✅ (vé, điểm mình) | ✅ (hàng, điểm mình) | ✅ (điểm/tuyến mình) | ❌ | ✅ (toàn hệ thống) | ✅ (toàn hệ thống) |
| UC-40 | Gán lại xe gốc cho chuyến đang chạy thay ⚠ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| UC-41 | Hủy vé nhận hoàn toàn bộ khi chuyến đang hoãn ⚠ | ✅ (của mình) | ❌ | ❌ | ✅ (thay khách hotline) | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-42 | Hủy vé nhận hoàn toàn bộ khi chuyến gặp sự cố do lỗi nhà xe giữa đường ⚠ | ✅ (của mình) | ❌ | ❌ | ✅ (thay khách hotline) | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-43 | Tự động hoàn tiền cho khách chờ quá 3 tiếng do lỗi nhà xe (vẫn phục vụ) ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-44 | Gán xe cho chuyến | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| UC-45 | Tự động chuyển "đang hoãn" khi tới giờ chạy mà chưa gán được xe ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UC-46 | Tự động cảnh báo và chuyển "hàng tồn" khi hàng chờ quá lâu tại điểm nhận ⏱ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Về "tài xế"**: không có dòng nào tài xế thực hiện — đúng như mục 8.3, chỉ cung cấp thông tin bằng lời cho phụ xe trong UC-17.

**Số UC-06 và UC-07 không còn dùng** (đã gộp vào UC-05) — giữ nguyên số các UC còn lại (UC-08 trở đi) thay vì đánh số lại toàn bộ, để không phải sửa hàng loạt tham chiếu chéo. Lý do gộp: "chọn ghế và giữ chỗ" một mình không phải 1 mục đích có giá trị đứng riêng được (elementary business process) — chỉ khi gộp với bước thanh toán mới thành 1 mục đích hoàn chỉnh ("khách đặt vé thành công"). Bên trong UC-05, "thanh toán ngay" và "thanh toán tại quầy" là 2 **nhánh rẽ của cùng 1 activity diagram** (decision node bình thường), không phải 2 use case riêng.

---

## 12. Đặc tả luồng hoạt động theo use case (dùng để vẽ activity diagram)

Mỗi use case dưới đây viết theo cùng khuôn: **Actor / Tiền điều kiện / Luồng chính (đánh số tuần tự) / Luồng rẽ nhánh (điều kiện rõ ràng + điểm đến) / Hậu điều kiện**. Đánh số khớp đúng mục 11 — **mỗi use case chỉ có đúng 1 trigger và 1 luồng liên tục**, không gộp nhiều sự kiện độc lập.

### UC-01. Đăng ký tài khoản

- **Actor**: Khách hàng (chưa có tài khoản).
- **Tiền điều kiện**: Chưa đăng nhập.
- **Luồng chính** (mục 2.1):
  1. Nhập email + mật khẩu + họ tên + SĐT.
  2. Hệ thống validate định dạng dữ liệu.
  3. Hệ thống tạo bản ghi tài khoản trạng thái "chưa kích hoạt", sinh mã OTP 6 số, lưu hạn 1 phút.
  4. Hệ thống gửi email chứa mã OTP.
  5. Khách nhập mã OTP.
  6. Hệ thống kiểm tra mã.
- **Luồng rẽ nhánh**:
  - Tại bước 2: email đã tồn tại và đã kích hoạt → báo lỗi "email đã được sử dụng" → kết thúc, quay lại form.
  - Tại bước 6: mã sai hoặc hết hạn → báo lỗi → khách chọn "gửi lại mã" → quay lại bước 3 (sinh mã mới); hoặc khách bỏ dở → kết thúc.
  - Tại bước 6: mã đúng & còn hạn → tài khoản chuyển "đã kích hoạt" → kết thúc, chuyển sang UC-02.
- **Hậu điều kiện**: Tài khoản khách hàng ở trạng thái hoạt động, đăng nhập được.

### UC-02. Đăng nhập

- **Actor**: Khách hàng hoặc cán bộ (mọi vai trò có tài khoản).
- **Tiền điều kiện**: Đã có tài khoản.
- **Luồng chính**:
  1. Nhập email + mật khẩu.
  2. Hệ thống so khớp mật khẩu đã băm.
- **Luồng rẽ nhánh**:
  - Sai mật khẩu → báo lỗi → quay lại bước 1.
  - Đúng mật khẩu nhưng tài khoản bị khóa (`dang_hoat_dong = false` hoặc `bi_khoa = true`, mục 8.7/9) → báo lỗi "tài khoản bị khóa" → kết thúc.
  - Đúng mật khẩu, tài khoản hoạt động bình thường → cấp JWT, vào hệ thống theo đúng vai trò (`nguoi_dung.vai_tro`) → kết thúc.
- **Hậu điều kiện**: Có JWT hợp lệ cho các use case tiếp theo.

### UC-03. Quên mật khẩu

- **Actor**: Khách hàng hoặc cán bộ.
- **Luồng chính** (mục 2.1 điểm 4):
  1. Nhập email, yêu cầu gửi mã.
  2. Hệ thống luôn trả về "đã gửi mã nếu tồn tại" (không tiết lộ email có tồn tại hay không).
  3. (Nếu email tồn tại, ẩn với người dùng) hệ thống sinh OTP, gửi email.
  4. Người dùng nhập mã OTP nhận được.
  5. Hệ thống kiểm tra mã.
- **Luồng rẽ nhánh**:
  - Tại bước 5: sai/hết hạn → báo lỗi → quay lại bước 1 (gửi lại).
  - Tại bước 5: đúng → cho nhập mật khẩu mới → cập nhật → kết thúc.
- **Hậu điều kiện**: Mật khẩu mới có hiệu lực.

### UC-04. Tra cứu chuyến công khai

- **Actor**: Khách hàng (kể cả chưa đăng nhập).
- **Tiền điều kiện**: Không cần đăng nhập.
- **Luồng chính** (mục 3.4 bước 1–3, mục 8.1 điểm 1):
  1. Nhập điểm đi + điểm đến (khu_vực) + ngày.
  2. Hệ thống tìm mọi `chuyen_xe` có tuyến đi qua đúng cặp khu_vực theo đúng thứ tự (điểm đón hợp lệ = văn phòng thuộc khu_vực đi, đứng trước ≥1 điểm thuộc khu_vực đến).
  3. Hiển thị danh sách chuyến (loại xe, giá "từ", số ghế trống, giờ dự kiến).
  4. Chọn 1 chuyến → xem sơ đồ ghế (đoạn rộng nhất có thể).
- **Luồng rẽ nhánh**:
  - Tại bước 2: không có chuyến nào khớp → hiển thị "không tìm thấy chuyến phù hợp" → kết thúc.
- **Hậu điều kiện**: Khách xem được sơ đồ ghế của 1 chuyến cụ thể — có thể tiếp tục UC-05 nếu đã đăng nhập.

### UC-05. Đặt vé online (chọn ghế, giữ chỗ, thanh toán)

- **Actor**: Khách hàng (đã đăng nhập), Cổng thanh toán (nhánh "thanh toán ngay").
- **Tiền điều kiện**: Đã đăng nhập, đã hoàn tất UC-04.
- **Mục đích**: khách đặt được 1 vé hoàn chỉnh — kết thúc ở trạng thái `da_thanh_toan` (đã trả tiền xong) hoặc "đặt thành công, cam kết trả tiền tại quầy" (`giu_cho` không hạn) — cả hai đều là kết quả có giá trị, khác với việc chỉ dừng ở "giữ ghế" nửa chừng.
- **Luồng chính** (mục 3.4, mục 6, mục 9):
  1. Chọn 1 hoặc nhiều ghế trên sơ đồ.
  2. Bấm "Cập nhật điểm đón trả".
  3. Hệ thống khóa ghế trong 1 transaction (`SELECT ... FOR UPDATE` + kiểm tra overlap theo đoạn rộng nhất) → tạo `ve` trạng thái `giu_cho`.
  4. Chọn điểm đón (chỉ hiện văn phòng thuộc khu_vực đi) + điểm trả (văn phòng hoặc điểm dừng thuộc khu_vực đến, đứng sau điểm đón).
  5. Hệ thống thu hẹp đoạn `giu_cho` về đúng `[điểm đón, điểm trả)`.
  6. Tới màn thanh toán — hệ thống kiểm tra `ho_so_khach_hang.khoa_thanh_toan_tai_quay` (mục 9).
  7. Chọn **loại hình thanh toán** (`loai_hinh_thanh_toan`, mục 6): "Thanh toán ngay" hoặc "Thanh toán tại quầy khi nhận vé".
- **Luồng rẽ nhánh**:
  - Tại bước 3: ghế đã bị người khác giữ (đoạn giao nhau) → báo lỗi "ghế đã có người chọn" → quay lại bước 1 (chọn ghế khác).
  - Tại bước 6: nếu `khoa_thanh_toan_tai_quay = true` (đã vi phạm no-show đủ ngưỡng) → chỉ hiển thị "Thanh toán ngay", ẩn "Thanh toán tại quầy" → bắt buộc đi nhánh A.
  - **Nhánh A — "Thanh toán ngay"** (từ bước 7):
    1. Bắt đầu tính hạn 5 phút, tính từ lúc tới bước này.
    2. Backend gọi API VNPay tạo giao dịch, trả về `payUrl` — khách được chuyển hướng sang thẳng trang thanh toán VNPay (không phải hệ thống nhà xe tự sinh QR), tại đó khách quét QR bằng app ngân hàng hoặc nhập thẻ trực tiếp.
    3. VNPay báo thành công qua webhook (kèm mã giao dịch, xác thực chữ ký) — xử lý ngay, không đợi hết hạn → vé chuyển `da_thanh_toan`, `phuong_thuc_thanh_toan = 'chuyen_khoan'`, lưu `ma_giao_dich_cong_thanh_toan` → **kết thúc UC** (dẫn sang UC-12 khi lên xe).
    4. VNPay báo thất bại/hủy (webhook), hoặc hết 5 phút không có tín hiệu gì → vé chuyển `het_han`, ghế/đoạn mở lại → **kết thúc UC**.
  - **Nhánh B — "Thanh toán tại quầy"** (từ bước 7):
    1. Hệ thống kiểm tra điều kiện đặt cọc: 1 vé → không cọc; ≥2 vé và tổng giá trị ≤600.000đ → không cọc; ≥2 vé và tổng giá trị >600.000đ → bắt buộc thực hiện nhánh A (ngay bên trên) cho riêng `floor(số vé×50%)` vé trong lô — không hoàn tất trong 5 phút → **toàn bộ lô** (cùng `ma_dat_cho`) chuyển `het_han`, không chỉ phần cọc → **kết thúc UC**.
    2. Qua được bước cọc (hoặc không cần cọc) → **coi như đặt vé thành công ngay** — giữ nguyên tới giờ khởi hành tại điểm đón, không có mốc chốt/hạn nào → **kết thúc UC** (dẫn sang UC-11 khi khách ra quầy trả tiền, hoặc UC-14 nếu đến giờ lên xe vẫn chưa ra quầy).
  - Tại bất kỳ bước nào trước khi hoàn tất thanh toán: khách tự hủy → xem UC-08.
- **Hậu điều kiện**: Vé `da_thanh_toan`, `het_han`, "đặt thành công chờ thanh toán tại quầy" (`giu_cho` không hạn), hoặc `da_huy` (nếu hủy).

### UC-08. Hủy giữ chỗ trước khi thanh toán

- **Actor**: Khách hàng (của chính mình) hoặc Nhân viên quầy vé (thay khách hotline chưa thanh toán).
- **Tiền điều kiện**: Vé đang ở trạng thái `giu_cho` (từ UC-05/UC-10).
- **Luồng chính** (mục 7):
  1. Chọn "Hủy giữ chỗ".
  2. Hệ thống kiểm tra trạng thái vé và mốc chốt lên xe tại điểm đón.
- **Luồng rẽ nhánh**:
  - Vé đã `da_thanh_toan` → không cho hủy qua UC này, báo lỗi "vé đã thanh toán không thể hủy" → kết thúc (trừ khi chuyến đang "hoãn" trước giờ chạy — UC-41, hoặc đang gặp sự cố do lỗi nhà xe giữa đường — UC-42).
  - Vé đang `giu_cho` nhưng đã qua mốc chốt lên xe tại điểm đón → ẩn nút hủy, không cho hủy nữa → kết thúc (khách chỉ còn ra quầy trả tiền hoặc bị tính `khong_den`).
  - Vé đang `giu_cho` và còn trước mốc chốt → chuyển `da_huy`, ghế mở lại ngay, không mất gì → kết thúc.
- **Hậu điều kiện**: Đoạn hành trình khả dụng lại cho khách khác (nếu hủy thành công).

### UC-09. Bán vé tại quầy

- **Actor**: Nhân viên quầy vé.
- **Tiền điều kiện**: Đã đăng nhập, đang ở đúng văn phòng phụ trách; khách có mặt trực tiếp tại quầy.
- **Luồng chính** (mục 8.4 điểm 1):
  1. Khách yêu cầu mua vé tại quầy.
  2. Tìm chuyến theo điểm đi/đến/ngày.
  3. Chọn chuyến, chọn ghế trên sơ đồ.
  4. Nhập tên + SĐT khách vãng lai (hoặc tra theo tài khoản nếu khách đã có).
  5. Chọn điểm đón + điểm trả cụ thể.
  6. Hỏi khách trả bằng tiền mặt hay chuyển khoản QR (VNPay) — thu tiền, vé chuyển `da_thanh_toan` (`loai_hinh_thanh_toan = 'thanh_toan_tai_quay'`, `phuong_thuc_thanh_toan` ghi đúng lựa chọn của khách; nếu chuyển khoản thì đợi webhook VNPay xác nhận trước khi chuyển trạng thái, lưu `ma_giao_dich_cong_thanh_toan`).
  7. In vé cứng, đưa cho khách (dẫn sang UC-12 khi khách lên xe).
- **Hậu điều kiện**: Vé `da_thanh_toan`, khách cầm vé cứng ngay.

### UC-10. Bán vé qua hotline

- **Actor**: Nhân viên quầy vé.
- **Tiền điều kiện**: Đã đăng nhập; khách gọi điện đặt vé, không có mặt trực tiếp.
- **Luồng chính** (mục 8.4 điểm 2):
  1. Nhận cuộc gọi từ khách.
  2. Tìm chuyến theo điểm đi/đến/ngày.
  3. Chọn chuyến, chọn ghế trên sơ đồ.
  4. Nhập tên + SĐT khách.
  5. Chọn điểm đón + điểm trả cụ thể.
  6. Thỏa thuận với khách qua điện thoại: trả ngay hay hẹn ra quầy trả sau — vé luôn tạo với `loai_hinh_thanh_toan = 'thanh_toan_tai_quay'` (kênh nhân viên hỗ trợ, không phải khách tự đặt online) bất kể chọn nhánh nào dưới đây.
- **Luồng rẽ nhánh**:
  - Khách đồng ý trả ngay qua điện thoại → nhân viên gửi link/mã QR thanh toán VNPay cho khách (SMS/Zalo) → khách tự bấm/quét từ xa → VNPay báo thành công (webhook) → vé `da_thanh_toan`, `phuong_thuc_thanh_toan = 'chuyen_khoan'`, lưu `ma_giao_dich_cong_thanh_toan` → kết thúc, dẫn sang UC-11.
  - Khách hẹn trả tiền khi ra lấy vé → vé `giu_cho`, `phuong_thuc_thanh_toan` để trống (chọn lúc UC-11 khi thực sự thu tiền) → kết thúc, dẫn sang UC-11 (nơi thu tiền).
- **Hậu điều kiện**: Vé được tạo (`giu_cho` hoặc `da_thanh_toan`), khách chưa cầm vé cứng.

### UC-11. In vé cứng cho khách đặt online/hotline

- **Actor**: Nhân viên quầy vé.
- **Tiền điều kiện**: Vé đang `giu_cho` (từ UC-05 nhánh B hoặc UC-10, chưa thanh toán) hoặc `da_thanh_toan` (từ UC-05 nhánh A hoặc UC-10 đã trả qua điện thoại).
- **Luồng chính** (mục 8.1 điểm 5, mục 8.4 điểm 3):
  1. Khách ra đúng văn phòng điểm đón đã chọn, cung cấp mã đặt chỗ hoặc SĐT.
  2. Nhân viên tra cứu vé.
  3. Xác minh đúng người (đối chiếu tên/SĐT).
  4. Kiểm tra trạng thái vé.
  5. In vé cứng, đưa cho khách.
- **Luồng rẽ nhánh**:
  - Tại bước 2: không tìm thấy → xác minh lại thông tin → kết thúc/thử lại.
  - Tại bước 4: vé đang `giu_cho` → hỏi khách trả bằng tiền mặt hay chuyển khoản QR, thu tiền → ghi nhận `phuong_thuc_thanh_toan` tương ứng (và `ma_giao_dich_cong_thanh_toan` nếu chuyển khoản) → chuyển `da_thanh_toan` → sang bước 5.
  - Tại bước 4: vé đã `da_thanh_toan` → sang thẳng bước 5.
  - Tại bước 4: vé đã `het_han`/`khong_den` → báo khách vé không còn hiệu lực, không thể lấy → kết thúc (khách phải đặt lại từ đầu).
- **Hậu điều kiện**: Khách cầm vé cứng, đủ điều kiện lên xe (UC-12).

### UC-12. Xác nhận khách lên xe

- **Actor**: Phụ xe.
- **Tiền điều kiện**: Chuyến `dang_chay`, vé `da_thanh_toan`.
- **Luồng chính** (mục 8.2 điểm 1, 3):
  1. Hệ thống hiển thị danh sách khách cần lên tại điểm hiện tại.
  2. Khách xuất trình vé cứng.
  3. Phụ xe tìm đúng dòng khớp (số ghế/họ tên, hoặc tra thêm mã vé nếu trùng tên).
  4. Bấm xác nhận.
- **Luồng rẽ nhánh**:
  - Tại bước 3: không tìm thấy/vé không hợp lệ (VD vé của chuyến khác) → từ chối, báo lỗi → kết thúc.
  - Tại bước 4: hợp lệ → hệ thống đánh dấu `da_len_xe`.
- **Hậu điều kiện**: Vé `da_len_xe`, sẵn sàng cho UC-13.

### UC-13. Xác nhận khách xuống xe

- **Actor**: Phụ xe.
- **Tiền điều kiện**: Vé `da_len_xe`, xe tới đúng điểm trả của vé đó.
- **Luồng chính** (mục 8.2 điểm 4):
  1. Khách xuống đúng điểm trả.
  2. Phụ xe chủ động xác nhận trên hệ thống (không chỉ nhắc miệng).
  3. Hệ thống đánh dấu `da_xuong_xe`.
- **Hậu điều kiện**: Vé `da_xuong_xe` — kết thúc vòng đời vé.

### UC-14. Đánh dấu no-show tự động ⏱

- **Actor**: Hệ thống (job quét theo thời gian — không phải actor người dùng).
- **Tiền điều kiện**: Đến X phút trước giờ khởi hành tại điểm đón của 1 vé (mục 8.2 điểm 6).
- **Luồng chính** (mục 9):
  1. Quét mọi vé chưa `da_len_xe` tại điểm đón đó.
  2. Với mỗi vé — dù `da_thanh_toan` hay đang `giu_cho` (chọn "thanh toán tại quầy" nhưng chưa từng trả tiền, UC-05 nhánh B) — đánh dấu `khong_den`.
  3. Ghi nhận 1 lần vi phạm no-show cho khách hàng đó (nếu có tài khoản).
- **Hậu điều kiện**: Vé `khong_den`; bộ đếm vi phạm no-show cập nhật.

### UC-15. Xác nhận xuất phát

- **Actor**: Phụ xe.
- **Tiền điều kiện**: Chuyến `chua_khoi_hanh`, tới giờ khởi hành tại điểm đầu tuyến.
- **Luồng chính** (mục 8.2 điểm 2):
  1. Phụ xe xác nhận xuất phát đúng giờ tại điểm đầu tuyến.
  2. Chuyến chuyển `dang_chay`.
- **Hậu điều kiện**: Chuyến `dang_chay`.

### UC-16. Xác nhận đến điểm (trung gian/cuối cùng)

- **Actor**: Phụ xe.
- **Tiền điều kiện**: Chuyến `dang_chay`, xe vừa tới 1 điểm dừng trên tuyến.
- **Luồng chính** (mục 8.2 điểm 5, 8):
  1. Phụ xe xác nhận đã đến điểm hiện tại.
  2. Hệ thống ghi giờ thực tế, cập nhật ETA cho khách chờ ở các điểm phía sau (WebSocket).
  3. Hệ thống kích hoạt đúng danh sách lên/xuống của điểm đó (UC-12/UC-13).
- **Luồng rẽ nhánh**:
  - Điểm này là điểm cuối cùng của tuyến → chuyến chuyển `hoan_thanh` → kết thúc.
  - Điểm này là điểm trung gian → kết thúc (1 lần thực hiện UC này); khi xe tới điểm kế tiếp, thực hiện lại UC này 1 lần nữa.
- **Hậu điều kiện**: Giờ tới được ghi nhận; `hoan_thanh` nếu là điểm cuối.

### UC-17. Báo sự cố giữa đường

- **Actor**: Phụ xe (nhận thông tin bằng lời từ Tài xế — actor phụ, không thao tác hệ thống).
- **Tiền điều kiện**: Chuyến `dang_chay`, phát sinh sự cố (hỏng xe, tai nạn, tắc đường nghiêm trọng, thiên tai/sạt lở...).
- **Luồng chính** (mục 8.2 điểm 7):
  1. Phụ xe nhập thông tin sự cố (theo mô tả của tài xế) trên hệ thống.
  2. Chọn **nguyên nhân**: `loi_nha_xe` (hỏng xe, thủng lốp, tai nạn do nhà xe gây ra) hoặc `loi_khach_quan` (thiên tai, sạt lở, sự cố ngoại cảnh không do nhà xe) — quyết định quyền hoàn tiền của khách sau này (mục 3.3/4/7).
  3. Chuyến chuyển `gap_su_co`, lưu `loai_su_co` tương ứng.
  4. Điều độ viên nhận cảnh báo ngay.
- **Hậu điều kiện**: Chuyến `gap_su_co` kèm phân loại nguyên nhân, dẫn sang UC-19.

### UC-18. Thiết lập lịch chạy định kỳ

- **Actor**: Quản lý.
- **Tiền điều kiện**: Tuyến đã tồn tại (UC-31), có ít nhất 1 `gia_ve` cấu hình cho tuyến đó (UC-33), `loai_xe` cần dùng đã tồn tại (UC-32).
- **Luồng chính** (mục 8.7 điểm 1, mục 3.5):
  1. Chọn 1 tuyến có sẵn.
  2. Nhập giờ khởi hành trong ngày.
  3. Chọn 1 `loai_xe` dự kiến phục vụ khung giờ này.
  4. Xác nhận tạo → hệ thống lưu `lich_chay_dinh_ky` (`dang_ap_dung = true`).
  5. Job định kỳ tự động sinh `chuyen_xe` cho N ngày tới (N cấu hình được, UC-33 hoặc cấu hình hệ thống) — mỗi chuyến có `tuyen_id`/`gio_khoi_hanh`/`loai_xe_id`, **chưa gán `xe_id`**.
- **Luồng rẽ nhánh**:
  - Quản lý ngừng áp dụng 1 lịch chạy định kỳ (`dang_ap_dung = false`) → chỉ ngừng sinh chuyến mới, các chuyến đã sinh sẵn trước đó (có thể đã bán vé) giữ nguyên, không bị hủy.
- **Hậu điều kiện**: Có `lich_chay_dinh_ky` đang áp dụng; các chuyến tương ứng đã/sẽ được sinh sẵn, sẵn sàng cho khách tìm kiếm và đặt vé (UC-04/05) dù chưa gán xe cụ thể.

### UC-44. Gán xe cho chuyến

- **Actor**: Điều độ viên.
- **Tiền điều kiện**: Chuyến `chua_khoi_hanh`, xuất phát từ văn phòng mình phụ trách, `xe_id` đang `NULL` (chưa gán) hoặc muốn đổi sang xe khác.
- **Lưu ý về nhân sự**: điều độ viên **chỉ chọn xe, không phân tài xế/phụ xe** — mỗi xe đã có biên chế cố định sẵn (`xe_nhan_su`, do `quan_ly` quản lý ở UC-35, mục 3.2), nên chọn xe nào là tự khắc biết nhân sự của chuyến đó, suy ra live tại thời điểm truy vấn.
- **Luồng chính** (mục 8.6 điểm 1, mục 3.2, mục 3.3, mục 3.5):
  1. Xem danh sách chuyến đã sinh sẵn từ lịch chạy định kỳ, xuất phát từ văn phòng mình phụ trách — kèm cảnh báo nếu chuyến còn ≤48 tiếng mà chưa gán xe.
  2. Chọn 1 chuyến cần gán xe.
  3. Hệ thống liệt kê xe đủ điều kiện: **đúng `loai_xe` đã cam kết ở lịch chạy định kỳ**, đúng nhóm tuyến (hoặc xe dự phòng), đang/sẽ có mặt đúng điểm khởi hành đúng giờ, và không trùng lịch.
  4. Chọn 1 xe cụ thể.
  5. Hệ thống cập nhật `xe_id` cho chuyến — tài xế/phụ xe **tự suy ra** từ biên chế cố định của xe, không có bước chọn người nào. Biển số xe từ đây hiển thị cho khách đã đặt vé trên chuyến này.
- **Luồng rẽ nhánh**:
  - Tại bước 3: không có xe nào đủ điều kiện → báo lỗi, gợi ý chờ xe khác rảnh → kết thúc/thử lại. Nếu đã tới đúng `gio_khoi_hanh` mà vẫn chưa gán được → hệ thống tự động chuyển "đang hoãn" (UC-45 ⏱) — điều độ viên tiếp tục quay lại bước 1 cho tới khi có xe.
  - Chuyến đã có `xe_id` từ trước (điều độ viên muốn đổi xe) → thực hiện lại bước 3-5 để gán xe khác, không giới hạn số lần đổi, miễn còn trước giờ khởi hành và đúng `loai_xe`.
  - Chuyến đang "đang hoãn" do UC-45 (chưa từng có `xe_id`) → gán xe vẫn qua đúng bước 3-5, chỉ khác lúc thành công thì tắt luôn cờ "đang hoãn" thay vì chỉ cập nhật `xe_id` đơn thuần.
- **Hậu điều kiện**: Chuyến có `xe_id` cụ thể, sẵn sàng cho các bước vận hành tiếp theo (UC-15 trở đi).

### UC-45. Tự động chuyển "đang hoãn" khi tới giờ chạy mà chưa gán được xe ⏱

- **Actor**: Hệ thống (job định kỳ — không phải actor người dùng thao tác trực tiếp).
- **Tiền điều kiện**: Chuyến `chua_khoi_hanh`, đã tới đúng `gio_khoi_hanh` đã lên lịch mà `xe_id` vẫn `NULL` (điều độ viên chưa gán được xe nào qua UC-44, dù đã có nhắc từ ngưỡng 48 tiếng, mục 3.5).
- **Mục đích**: đảm bảo chuyến chưa từng có xe cũng được đối xử công bằng như chuyến có xe rồi hỏng (UC-20) — không âm thầm trễ vô thời hạn mà không ai biết, khách đã trả tiền vẫn có quyền lợi hủy nhận hoàn rõ ràng như mọi trường hợp "đang hoãn" khác.
- **Luồng chính** (mục 3.3):
  1. Job quét các chuyến `chua_khoi_hanh` có `gio_khoi_hanh ≤ now()` và `xe_id IS NULL`.
  2. Bật cờ `dang_hoan = true`, cập nhật `gio_khoi_hanh` sang thời điểm dự kiến mới (tạm thời — điều độ viên cập nhật lại khi có ước tính cụ thể hơn).
  3. Gửi thông báo WebSocket cho khách đã có vé trên chuyến này.
- **Hậu điều kiện**: Chuyến ở đúng trạng thái "đang hoãn" như UC-20 — điều độ viên tiếp tục tìm xe qua UC-44; khi tìm được, gán **thẳng vào `xe_id`** (không qua `xe_thuc_te_id` — chưa từng có xe gốc nào để giữ nguyên), tắt cờ "đang hoãn". Vé `da_thanh_toan` trên chuyến này có quyền chủ động hủy nhận hoàn 100% trong lúc chờ (UC-41).

### UC-19. Xử lý sự cố giữa đường ⚠

- **Actor**: Điều độ viên. **Use case ngoại lệ ⚠** — chỉ chạy khi có sự cố giữa đường, không phải thao tác thường ngày.
- **Tiền điều kiện**: Chuyến `gap_su_co` (từ UC-17), đã có `loai_su_co`.
- **Nguyên tắc chung**: chuyến **không bao giờ bị bỏ dở giữa đường vì lỗi nhà xe** — luôn tìm cách hoàn thành (tự khắc phục hoặc điều xe thay thế, dù mất bao lâu). Chỉ **sự cố khách quan** mới có khả năng thực sự không thể hoàn thành (thiên tai chặn đường không còn lối nào khác). Quyền hoàn tiền của khách trong lúc chờ khác nhau tùy nguyên nhân (mục 7).
- **Luồng chính** (mục 8.6 điểm 4, mục 4):
  1. Nhận cảnh báo sự cố, trao đổi qua điện thoại với phụ xe/tài xế để đánh giá mức độ và thời gian dự kiến khắc phục.
  2. Xử lý theo `loai_su_co`.
- **Luồng rẽ nhánh**:
  - **`loi_nha_xe`, ước tính khắc phục ≤ 1 tiếng** (tự sửa tại chỗ được) → không cần thao tác gì thêm, chỉ cập nhật ETA cho các điểm phía sau (mục 8.2 điểm 5) → khi tài xế sửa xong, phụ xe xác nhận tiếp tục → chuyến quay lại `dang_chay`, **không hoàn tiền** → kết thúc, tiếp tục UC-16.
  - **`loi_nha_xe`, > 1 tiếng hoặc chưa rõ** → điều xe/tài xế thay thế đang rảnh tới đúng vị trí xe hỏng (ưu tiên xe dự phòng nội bộ, sau đó xe thuê ngoài — biến thể mục 3.3; **không bắt buộc tuyệt đối cùng `loai_xe`** như đổi xe trước giờ khởi hành, vì đây là tình huống khẩn cấp hơn — chấp nhận sắp xếp lại chỗ ngồi thủ công nếu khác loại xe) — **luôn tìm được xe cuối cùng, không có khái niệm "không thể tiếp tục" cho lỗi nhà xe** (mục tiêu nội bộ tối đa 6 tiếng, chỉ để cảnh báo `quan_ly` nếu vượt quá, không ép buộc gì, giống mục 3.3).
    - Khách có vé `da_thanh_toan` **chủ động yêu cầu hủy nhận hoàn 100% bất cứ lúc nào** nếu không muốn chờ (UC-42) → **hết nghĩa vụ phục vụ vé đó** (khách tự thu xếp phương tiện khác, vé kết thúc ở `da_huy`, dù sau đó có xe thay thế cũng không còn được lên xe này nữa).
    - Khách không yêu cầu hủy, đồng ý chờ tiếp, **và xử lý xong trước khi đạt mốc 3 tiếng** → không mất gì.
    - Khách không yêu cầu hủy, nhưng **đạt mốc ≥ 3 tiếng mà vẫn chưa xử lý xong** → hệ thống **tự động hoàn 100%** cho mọi vé `da_thanh_toan` chưa tự hủy trên chuyến (UC-43, không cần khách yêu cầu) — nhưng vé **vẫn giữ nguyên `da_thanh_toan`, KHÔNG chuyển `da_huy`** — nhà xe vẫn tiếp tục tìm xe và **chở khách miễn phí** khi có xe (coi như "free" chuyến đó, bù đắp vì để khách chờ quá lâu do lỗi của nhà xe).
    - Khi điều được xe (ở bất kỳ thời điểm nào) → cập nhật vị trí thực tế, chuyến quay lại `dang_chay` (các chuyến sau của xe cũ bị gắn cờ cảnh báo xung đột vị trí, cần xem lại thủ công) → kết thúc, tiếp tục UC-16.
  - **`loi_khach_quan`, ≤ 3 tiếng, hoặc > 3 tiếng nhưng vẫn còn khả năng hoàn thành** (đường sẽ thông trong ngày/hôm sau) → chờ tại chỗ, cập nhật ETA — **khách không có lựa chọn hủy nhận hoàn nào**, kể cả muốn (bất khả kháng, mục 7) → khi xong, phụ xe xác nhận tiếp tục, chuyến quay lại `dang_chay`, không hoàn tiền → kết thúc, tiếp tục UC-16.
  - **`loi_khach_quan`, > 3 tiếng, điều độ viên xác nhận thực sự không thể hoàn thành được nữa** → hủy phần còn lại → chuyến chuyển `da_huy` → dẫn sang UC-21 → kết thúc.
- **Hậu điều kiện**: Chuyến quay lại `dang_chay` (xử lý xong, dù nhẹ hay đã điều được xe thay thế), hoặc chuyển `da_huy` (chỉ xảy ra với `loai_su_co = loi_khach_quan`). Các chuyến `chua_khoi_hanh` khác cùng `xe_id` đang gắn cờ cảnh báo xung đột vị trí (mục 3.3) vẫn cần điều độ viên xem lại riêng, không tự động gỡ theo.

### UC-20. Đổi xe trước giờ khởi hành ⚠

- **Actor**: Điều độ viên. **Use case ngoại lệ ⚠** — chỉ chạy khi xe gán cho chuyến không thể có mặt đúng vị trí/giờ khởi hành, không phải thao tác thường ngày (chuyến bình thường giữ nguyên xe đã gán ở UC-44).
- **Tiền điều kiện**: Chuyến `chua_khoi_hanh`, **đã có `xe_id`** (đã từng gán xe qua UC-44) nhưng xe gốc không thể có mặt đúng vị trí/giờ khởi hành — do **xe hỏng đột xuất** (trực tiếp), hoặc do **chuyến trước đó của cùng xe gặp sự cố giữa đường** khiến xe bị delay/lệch vị trí không tới kịp (mục 3.3, gắn cờ cảnh báo xung đột vị trí). Trường hợp chuyến **chưa từng được gán xe** (`xe_id` vẫn `NULL`) mà đã tới giờ khởi hành xem UC-45 — không dùng UC này vì không có "xe gốc" nào để giữ nguyên.
- **Mục đích**: gán 1 **xe thực tế** (`xe_thuc_te_id`) tạm thời chạy thay — **không đổi xe gốc** (`chuyen_xe.xe_id`) của chuyến, để biên chế tài xế/phụ xe (suy ra từ xe gốc, mục 3.2) không bị xáo trộn. **Chuyến không bao giờ bị hủy vì lý do này** (mục 1, mục 3.3) — chỉ hoãn giờ khởi hành nếu chưa tìm được xe kịp.
- **Luồng chính** (mục 3.3):
  1. Hệ thống liệt kê xe thay thế đủ điều kiện theo thứ tự ưu tiên: xe dự phòng cùng `loai_xe` trong đội xe trước, rồi tới xe thuê/mượn ngoài đội xe (điều độ viên thêm tạm nếu cần) — cả 2 đều bắt buộc cùng `loai_xe` với xe gốc, đúng vị trí, không trùng lịch riêng.
  2. Chọn 1 xe trong danh sách.
  3. Gán `xe_thuc_te_id` = xe vừa chọn cho chuyến hiện tại **và mọi chuyến tương lai (`chua_khoi_hanh`) khác đang cùng thuộc xe gốc này** — ghế giữ nguyên hoàn toàn (chắc chắn cùng sơ đồ vì cùng `loai_xe`), không cần ánh xạ lại gì.
  4. Chuyến (và các chuyến liên quan) được gắn cờ hiển thị "đang chạy thay bằng xe khác".
  5. Hệ thống gửi thông báo WebSocket cho khách có vé trên các chuyến này (báo đổi biển số xe, ghế giữ nguyên).
  6. Điều độ viên cập nhật thủ công vị trí vật lý thật của xe gốc (đang hỏng) khi biết được — tách biệt với vị trí suy luận theo lịch trình (vẫn tính bình thường theo `xe_id` gốc, mục 3.3).
- **Luồng rẽ nhánh**:
  - Tại bước 1-2: xe thay thế tìm được chỉ sẵn sàng trễ **≤ 30 phút** so với giờ đã lên lịch → coi như không đáng kể, tiếp tục bình thường từ bước 3 (chỉ chỉnh nhẹ giờ khởi hành nếu cần), không có gì khác thêm.
  - Tại bước 1-2: xe thay thế chỉ sẵn sàng trễ **> 30 phút**, hoặc **chưa tìm được xe nào** (cả 2 nguồn) ngay lúc xử lý → chuyến chuyển sang **"đang hoãn"**: dời `gio_khoi_hanh` sang thời điểm dự kiến mới, gắn cờ "đang hoãn", thông báo khách — **không hủy chuyến**. Điều độ viên quay lại bước 1 định kỳ cho tới khi tìm được xe (mục tiêu nội bộ tối đa 6 tiếng, chỉ để cảnh báo `quan_ly` nếu vượt quá, không ép hủy). Trong lúc "đang hoãn", khách có vé `da_thanh_toan` có thể chủ động hủy nhận hoàn 100% (UC-41) nếu không muốn chờ.
- **Hậu điều kiện**: Chuyến (và chuỗi chuyến tương lai cùng xe gốc) có `xe_thuc_te_id` trỏ vào xe thay thế, gắn cờ hiển thị, khách được thông báo — hoặc chuyến chuyển "đang hoãn" (vẫn `chua_khoi_hanh`, giờ khởi hành mới) nếu chưa tìm được xe thay thế kịp. Xem UC-40 để gán lại xe gốc khi sửa xong, UC-41 nếu khách chủ động hủy trong lúc hoãn.

### UC-21. Tự động tính & thông báo hoàn tiền ⏱

- **Actor**: Hệ thống (kích hoạt bởi sự kiện chuyến `da_huy` từ UC-19 — không phải actor người dùng thao tác trực tiếp).
- **Tiền điều kiện**: Chuyến chuyển `da_huy` do `gap_su_co` **khách quan giữa đường**, điều độ viên xác nhận thực sự không thể hoàn thành được nữa (mục 3.3/4 — chỉ `loai_su_co = 'loi_khach_quan'` mới tới được đây, vì lỗi nhà xe luôn tìm được xe thay thế cuối cùng, không có nhánh hủy, mục 1/UC-19). Trường hợp khách chủ động hủy vé giữa chừng do lỗi nhà xe (UC-42) hoặc khi chuyến đang hoãn trước giờ chạy (UC-41) xử lý hoàn tiền riêng, không qua UC này — cả 3 luôn hoàn đúng 100%, không khác nhau về mức hoàn.
- **Luồng chính** (mục 7):
  1. Xác định các vé `da_thanh_toan` bị ảnh hưởng.
  2. Tạo 1 dòng `lich_su_hoan_tien` cho mỗi vé (`ly_do = 'bat_kha_khang_khong_hoan_thanh'`, `so_tien = gia`, `trang_thai = 'cho_xu_ly'`).
  3. Gửi thông báo WebSocket cho khách.
- **Luồng rẽ nhánh**:
  - Vé có `ma_giao_dich_cong_thanh_toan` (đã trả qua VNPay) → gọi API hoàn tiền của VNPay (toàn bộ giá vé) → thành công thì cập nhật dòng vừa tạo thành `trang_thai = 'da_hoan_tu_dong'` → kết thúc.
  - Vé không có `ma_giao_dich_cong_thanh_toan` (trả tiền mặt), hoặc API hoàn tiền VNPay gọi thất bại → giữ nguyên `trang_thai = 'cho_xu_ly'`, dẫn sang UC-22 để `ke_toan` xử lý.
- **Hậu điều kiện**: Khách biết đã được hoàn 100%, vé kết thúc vòng đời ở `da_huy`.

### UC-22. Kế toán chuyển khoản hoàn tiền

- **Actor**: Kế toán.
- **Mục đích**: xử lý phần hoàn tiền **không tự động được** qua cổng thanh toán (khách trả tiền mặt ban đầu, hoặc API hoàn tiền VNPay gọi thất bại) — phần này không thể tự động hóa vì tiền mặt không có giao dịch điện tử nào để đảo ngược.
- **Tiền điều kiện**: Có dòng `lich_su_hoan_tien` với `trang_thai = 'cho_xu_ly'` (từ UC-21, UC-41, UC-42, hoặc UC-43).
- **Luồng chính** (mục 7):
  1. Xem **danh sách hoàn tiền đang chờ xử lý** (`trang_thai = 'cho_xu_ly'`) — phạm vi toàn hệ thống.
  2. Chủ động gọi điện cho khách theo đúng số điện thoại đã lưu trong hệ thống (tài khoản, hoặc `sdt_khach_vang_lai` nếu là khách vãng lai) — không xử lý theo cuộc gọi đến tự xưng là khách, tránh bị mạo danh.
  3. Thông báo khoản hoàn, xin số tài khoản ngân hàng + tên ngân hàng + tên chủ tài khoản của khách.
  4. Thực hiện chuyển khoản qua ứng dụng ngân hàng của công ty (ngoài phạm vi hệ thống).
  5. Xác nhận chuyển khoản thành công → nhập `so_tai_khoan_nhan`/`ten_ngan_hang_nhan`/`ten_chu_tai_khoan_nhan` vào hệ thống (lưu vết đối soát nếu sau này phát sinh tranh chấp) → cập nhật dòng `lich_su_hoan_tien`: `trang_thai = 'da_hoan_chuyen_khoan_thu_cong'`, `nhan_vien_xu_ly_id`, `thoi_gian_hoan_xong`.
- **Luồng rẽ nhánh**:
  - Tại bước 2: không liên lạc được khách → giữ nguyên `cho_xu_ly`, thử lại sau.
  - Tại bước 3: khách chưa cung cấp được tài khoản ngay → hẹn gọi lại, giữ nguyên `cho_xu_ly`.
- **Hậu điều kiện**: Khách nhận đủ tiền hoàn qua chuyển khoản, `lich_su_hoan_tien` chuyển `da_hoan_chuyen_khoan_thu_cong`, kèm thông tin tài khoản đã chuyển để đối soát khi cần.

### UC-23. Nhận/gửi hàng tại quầy, tính cước

- **Actor**: Nhân viên gửi hàng.
- **Tiền điều kiện**: Đã đăng nhập, tại đúng văn phòng phụ trách.
- **Luồng chính** (mục 8.5 điểm 1, mục 10.4.1):
  1. Nhập thông tin người gửi + người nhận (tên + SĐT).
  2. Chọn điểm đến (khu_vực) → chọn văn phòng nhận cụ thể.
  3. Hệ thống xác định **tuyến** đi từ điểm gửi tới điểm nhận (nếu có nhiều tuyến cùng nối 2 điểm này, nhân viên chọn 1) — **không chọn chuyến cụ thể** (mục 10.2).
  4. Cân/đo hàng thực tế, nhập cân nặng + kích thước, chọn loại hàng.
  5. Hệ thống kiểm tra hàng cấm.
  6. Nhập giá cước, báo giá cho khách xác nhận.
  7. Chọn phương thức thanh toán.
  8. Tạo `don_hang` trạng thái `cho_van_chuyen` (gắn `tuyen_id`, `chuyen_id` để trống), in biên nhận + mã vận đơn cho người gửi.
- **Luồng rẽ nhánh**:
  - Tại bước 3: không có tuyến nào nối 2 điểm này → báo lỗi, từ chối nhận → kết thúc.
  - Tại bước 5: hàng cấm → chặn ngay, từ chối nhận → kết thúc.
  - Tại bước 7: người gửi trả trước → thu tiền mặt ngay.
  - Tại bước 7: COD → không thu, để người nhận trả sau.
- **Hậu điều kiện**: Đơn hàng `cho_van_chuyen`, chưa gắn chuyến cụ thể nào, sẵn sàng chờ phụ xe chọn xếp lên 1 chuyến cùng tuyến bất kỳ (UC-26).

### UC-24. Giao hàng cho người nhận, thu COD

- **Actor**: Nhân viên gửi hàng (tại điểm nhận).
- **Tiền điều kiện**: Đơn hàng `cho_lay` (từ UC-27), người nhận có mặt tại quầy.
- **Luồng chính** (mục 8.5 điểm 2, mục 10.3.1):
  1. Người nhận tới quầy, đọc mã vận đơn (hoặc SĐT + xác minh tên nếu quên mã).
  2. Tra đúng đơn hàng.
  3. Kiểm tra phương thức thanh toán.
  4. Xác nhận giao → đơn hàng chuyển `da_giao`, ghi nhận thời điểm + nhân viên xử lý.
- **Luồng rẽ nhánh**:
  - Tại bước 2: không khớp/không tìm thấy → xác minh lại thông tin → kết thúc/thử lại.
  - Tại bước 3: COD → thu tiền trước khi giao → sang bước 4.
  - Tại bước 3: người gửi đã trả trước → giao thẳng, không thu thêm → sang bước 4.
- **Hậu điều kiện**: Đơn hàng `da_giao`.

### UC-25. Xử lý hàng chờ quá lâu tại điểm nhận

- **Actor**: Nhân viên gửi hàng.
- **Tiền điều kiện**: Đơn hàng `cho_lay` đang có cờ cảnh báo (đủ 7 ngày, UC-46) hoặc đã chuyển `qua_han_luu_kho`/"hàng tồn" (đủ 14 ngày, UC-46) mà chưa ai tới lấy (mục 10.3/10.3.1).
- **Luồng chính**:
  1. Xem danh sách đơn đang cảnh báo/hàng tồn tại điểm mình.
  2. Kiểm tra đơn này trước đó đã từng thông báo được người nhận chưa (mục 10.3.1).
  3. Liên hệ theo đúng tình huống (xem luồng rẽ nhánh).
- **Luồng rẽ nhánh**:
  - Đã từng thông báo được người nhận → gọi lại người nhận, hỏi khi nào tới lấy hoặc hướng xử lý khác (VD nhờ người khác lấy hộ).
  - Chưa từng thông báo được người nhận (mất liên lạc hoàn toàn từ đầu) → gọi thẳng người gửi để hỏi hướng xử lý.
  - Liên hệ được (người nhận hoặc người gửi), có hướng xử lý rõ ràng → xử lý theo thỏa thuận (chờ thêm, gửi lại, hoàn, hoặc hủy hàng) → kết thúc.
  - Không liên hệ được ai (cả người nhận lẫn người gửi) → báo `quan_ly` xử lý thủ công (thanh lý) → kết thúc.
- **Hậu điều kiện**: Đơn hàng được xử lý theo thỏa thuận, hoặc chờ `quan_ly` thanh lý nếu không liên hệ được ai.

### UC-46. Tự động cảnh báo và chuyển "hàng tồn" khi hàng chờ quá lâu tại điểm nhận ⏱

- **Actor**: Hệ thống (job định kỳ — không phải actor người dùng thao tác trực tiếp).
- **Tiền điều kiện**: Đơn hàng `cho_lay`, đã đủ 7 ngày hoặc 14 ngày kể từ lúc hàng thực sự tới điểm nhận (phụ xe xác nhận dỡ hàng, UC-27) mà vẫn chưa `da_giao`.
- **Luồng chính** (mục 10.3/10.3.1):
  1. Job quét các đơn hàng `cho_lay` đã đủ 7 ngày kể từ lúc tới điểm nhận, chưa có cờ cảnh báo → bật cờ cảnh báo, gửi thông báo nhắc nhân viên gửi hàng tại điểm đó xử lý (dẫn sang UC-25).
  2. Job quét các đơn hàng `cho_lay` đã đủ 14 ngày kể từ lúc tới điểm nhận → chuyển hẳn `qua_han_luu_kho` ("hàng tồn").
- **Luồng rẽ nhánh**: Không có nhánh nào tự động hủy hay thanh lý — cả 2 mốc trên chỉ đổi cờ/trạng thái để **nhắc con người xử lý** (UC-25), đúng nguyên tắc không tự động hủy hàng của khách.
- **Hậu điều kiện**: Đơn có cờ cảnh báo (mốc 7 ngày) hoặc chuyển `qua_han_luu_kho` (mốc 14 ngày) — hàng vẫn được giữ nguyên, không mất, chờ xử lý thủ công.

### UC-26. Xác nhận chất hàng lên xe

- **Actor**: Phụ xe. **Lưu ý**: việc bê/chất hàng lên xe là hành động vật lý ngoài hệ thống (do phụ xe hoặc nhân viên bốc xếp thực hiện tay chân) — thao tác **trên hệ thống** chỉ là bấm xác nhận sau khi đã chất xong, y hệt cách UC-12 không phải là hành động khách tự bước lên xe. **Đây cũng là bước duy nhất xác định đơn hàng đi chuyến nào** (mục 10.2) — trước đó đơn chỉ gắn `tuyen_id`, chưa có `chuyen_id`.
- **Tiền điều kiện**: Chuyến `chua_khoi_hanh`/`dang_chay` đang tại hoặc chuẩn bị đi qua điểm gửi, có đơn hàng `cho_van_chuyen` cùng `tuyen_id` đang chờ tại điểm đó.
- **Luồng chính** (mục 8.2 điểm 9, mục 10.2, mục 10.3):
  1. Xem danh sách đơn hàng đang `cho_van_chuyen` cùng `tuyen_id` với chuyến này, còn chờ tại điểm đang đứng — sắp theo thứ tự thời gian tạo đơn (đơn cũ hiện trước, chỉ mang tính tham khảo).
  2. Phụ xe tự đánh giá khoang hàng thực tế, chọn lần lượt từng đơn để chất lên xe (có thể bỏ qua 1 đơn không xếp vừa, chọn đơn khác trong danh sách).
  3. Với mỗi đơn đã chất xong ngoài thực tế → bấm xác nhận trên hệ thống.
  4. Hệ thống gán `chuyen_id` = chuyến này cho đơn đó, chuyển `da_len_xe`.
- **Luồng rẽ nhánh**:
  - Phát hiện hư hỏng ngay lúc chất hàng → xem UC-28 (không chặn luồng chính).
  - Đơn hàng không được chọn (hết chỗ, hoặc không xếp vừa) → giữ nguyên `cho_van_chuyen`, `chuyen_id` vẫn để trống, tiếp tục hợp lệ cho chuyến sau cùng tuyến — không cần thao tác gì thêm.
- **Hậu điều kiện**: Đơn hàng được chọn chuyển `da_len_xe`, gắn đúng `chuyen_id`; đơn chưa được chọn vẫn `cho_van_chuyen`, chờ chuyến tiếp theo.

### UC-27. Xác nhận dỡ hàng khỏi xe

- **Actor**: Phụ xe. **Lưu ý**: tương tự UC-26, dỡ hàng vật lý là hành động ngoài hệ thống — trên hệ thống chỉ bấm xác nhận sau khi đã dỡ xong.
- **Tiền điều kiện**: Đơn hàng `da_len_xe`, xe tới điểm nhận, hàng đã được dỡ khỏi xe trên thực tế.
- **Luồng chính** (mục 8.2 điểm 9, mục 10.3):
  1. Xác nhận dỡ hàng khỏi xe.
  2. Đơn hàng chuyển `cho_lay`, ghi nhận thời điểm này (mốc bắt đầu tính 7/14 ngày cho UC-46, mục 10.3.1) — dẫn sang UC-24.
- **Luồng rẽ nhánh**:
  - Phát hiện thất lạc/hư hỏng lúc dỡ hàng → xem UC-28 (không chặn luồng chính).
- **Hậu điều kiện**: Đơn hàng `cho_lay`.

### UC-28. Báo thất lạc/hư hỏng hàng

- **Actor**: Phụ xe.
- **Tiền điều kiện**: Phát hiện thất lạc/hư hỏng trong lúc UC-26 hoặc UC-27.
- **Luồng chính**:
  1. Ghi nhận báo cáo thất lạc/hư hỏng trên hệ thống.
  2. Thông tin chuyển tới nhân viên gửi hàng/`quan_ly` xử lý tiếp (ngoài phạm vi luồng hệ thống chính).
- **Hậu điều kiện**: Sự cố được ghi nhận, không chặn UC-26/UC-27.

### UC-29. Quản lý khu vực

- **Actor**: Quản lý.
- **Luồng chính** (mục 8.7 điểm 1, mục 3.1):
  1. Chọn tạo mới hoặc sửa 1 `khu_vuc`.
  2. Nhập tên, tỉnh/thành.
  3. Lưu.
- **Hậu điều kiện**: Danh mục `khu_vuc` cập nhật, sẵn sàng dùng cho UC-30.

### UC-30. Quản lý điểm đón/trả

- **Actor**: Quản lý.
- **Tiền điều kiện**: `khu_vuc` liên quan đã tồn tại (UC-29).
- **Luồng chính** (mục 8.7 điểm 1, mục 3.1):
  1. Chọn tạo mới hoặc sửa 1 `diem_don_tra`.
  2. Gắn `khu_vuc_id`, nhập địa chỉ, chọn `loai` (`van_phong`/`diem_dung`).
  3. Lưu.
- **Hậu điều kiện**: Danh mục `diem_don_tra` cập nhật, sẵn sàng dùng cho UC-31.

### UC-31. Tạo tuyến

- **Actor**: Quản lý.
- **Tiền điều kiện**: Các `diem_don_tra` liên quan đã tồn tại (UC-30).
- **Luồng chính** (mục 8.7 điểm 1, mục 3.1):
  1. Tạo `nhom_tuyen` (nếu là hành trình vật lý mới) hoặc chọn nhóm có sẵn.
  2. Tạo `tuyen` (1 chiều), gắn `nhom_tuyen_id`.
  3. Thêm các dòng `tuyen_diem_don_tra` theo đúng thứ tự (`thu_tu`, `thoi_gian_du_kien_phut`).
- **Luồng rẽ nhánh**:
  - Điểm có `thu_tu` nhỏ nhất hoặc lớn nhất không phải `van_phong` → chặn, báo lỗi → sửa lại danh sách điểm.
- **Hậu điều kiện**: Tuyến sẵn sàng cho UC-33 (giá) và UC-18 (thiết lập lịch chạy định kỳ).

### UC-32. Quản lý loại xe

- **Actor**: Quản lý.
- **Luồng chính** (mục 3.1):
  1. Chọn tạo mới hoặc sửa 1 `loai_xe`.
  2. Nhập tên + hệ số giá (`he_so_gia`).
  3. Lưu.
- **Hậu điều kiện**: Danh mục `loai_xe` cập nhật, dùng cho UC-33/UC-34.

### UC-33. Cấu hình giá vé

- **Actor**: Quản lý.
- **Tiền điều kiện**: Tuyến đã tồn tại (UC-31).
- **Luồng chính** (mục 3.1):
  1. Chọn 1 tuyến.
  2. Chọn cặp điểm đi/điểm đến muốn bán.
  3. Nhập giá gốc (`gia_goc`).
  4. Lưu vào `gia_ve`.
- **Hậu điều kiện**: `gia_ve` sẵn sàng — giá bán thực tế = `gia_goc × loai_xe.he_so_gia` của `loai_xe` chuyến đó cam kết (mục 3.5), dùng ngay từ lúc chuyến được sinh ra (UC-18), UC-04 hiển thị giá.

### UC-34. Quản lý xe

- **Actor**: Quản lý.
- **Tiền điều kiện**: `loai_xe` và `diem_don_tra` (văn phòng) liên quan đã tồn tại.
- **Luồng chính** (mục 3.1):
  1. Thêm mới hoặc sửa 1 `xe`: biển số, gán `loai_xe`, `diem_goc_id`, `nhom_tuyen_id` (nếu cố định tuyến).
  2. Lưu.
- **Luồng rẽ nhánh**:
  - `diem_goc_id` không phải `van_phong` → chặn, báo lỗi.
  - Sửa `trang_thai` sang `bao_tri`/`ngung_su_dung` → xe không còn được gán vào chuyến mới cho tới khi đổi lại `hoat_dong`.
  - Sửa `trang_thai` từ `bao_tri` về `hoat_dong` (xe sửa xong) và xe này đang có ≥1 chuyến chạy thay bằng xe khác (`xe_thuc_te_id` của chuyến đó, mục 3.3) → hệ thống tự thông báo cho điều độ viên biết xe đã sẵn sàng, nhắc xem lại để gán lại nếu phù hợp (UC-40).
- **Hậu điều kiện**: Xe sẵn sàng gán vào biên chế (UC-35) và chuyến (UC-44).

### UC-35. Quản lý biên chế xe

- **Actor**: Quản lý.
- **Tiền điều kiện**: Xe đã tồn tại (UC-34), nhân sự (tài xế/phụ xe) đã có hồ sơ/tài khoản.
- **Luồng chính** (mục 3.2, mục 8.7 điểm 1):
  1. Chọn 1 xe.
  2. Gán/gỡ tài xế + phụ xe cố định (`xe_nhan_su`, `loai = co_dinh`).
  3. Lưu.
- **Hậu điều kiện**: Biên chế cố định cập nhật — "chuyến của tôi" của phụ xe (UC-12/13/15/16/17) tự động phản ánh ngay, không cần sửa từng chuyến.

### UC-36. Tạo tài khoản cán bộ

- **Actor**: Quản lý (bất kỳ, gốc hay không), hoặc Quản lý nhân sự (phạm vi hẹp hơn).
- **Luồng chính** (mục 8.7 điểm 2, mục 8.9):
  1. Nhập email + vai trò muốn tạo (nhân viên vận hành/quầy vé/gửi hàng/điều độ viên/kế toán/quản lý/quản lý nhân sự) + văn phòng phụ trách (bắt buộc trừ `ke_toan`/`quan_ly`/`quan_ly_nhan_su` — không gắn văn phòng, mục 2).
  2. Hệ thống kiểm tra actor đang đăng nhập có quyền tạo đúng vai trò vừa chọn hay không (xem luồng rẽ nhánh).
  3. Hệ thống tạo tài khoản trạng thái "chưa đặt mật khẩu", gửi email mời.
  4. Cán bộ nhận email, bấm liên kết, tự đặt mật khẩu lần đầu.
- **Luồng rẽ nhánh**:
  - Tại bước 1: email đã tồn tại → báo lỗi → nhập lại.
  - Tại bước 2: actor là `quan_ly_nhan_su` nhưng vai trò muốn tạo là `ke_toan`/`quan_ly`/`quan_ly_nhan_su` → chặn, báo "không đủ quyền" → kết thúc.
  - Tại bước 2: actor là `quan_ly` **không phải tài khoản gốc** nhưng vai trò muốn tạo là `quan_ly` hoặc `quan_ly_nhan_su` → chặn, báo "chỉ tài khoản quản lý gốc mới tạo được" → kết thúc.
  - Tại bước 2: các trường hợp còn lại (đúng quyền) → tiếp tục bước 3.
- **Hậu điều kiện**: Cán bộ có tài khoản, đăng nhập được (UC-02).

### UC-37. Khóa tài khoản

- **Actor**: Quản lý (bất kỳ), hoặc Quản lý nhân sự (phạm vi hẹp hơn).
- **Luồng chính** (mục 8.7 điểm 5, mục 8.9):
  1. Tìm tài khoản (khách hàng hoặc cán bộ) cần khóa.
  2. Hệ thống kiểm tra actor có quyền khóa đúng tài khoản mục tiêu hay không (xem luồng rẽ nhánh).
  3. Nhập lý do (nếu có).
  4. Đặt `dang_hoat_dong = false` (hoặc `bi_khoa = true` với khách hàng no-show, mục 9).
- **Luồng rẽ nhánh**:
  - Tại bước 2: tài khoản mục tiêu là `quan_ly` gốc (`la_tai_khoan_goc = true`) → chặn tuyệt đối, không ai khóa được, kể cả `quan_ly` khác → kết thúc.
  - Tại bước 2: actor là `quan_ly_nhan_su` nhưng mục tiêu là `ke_toan`/`quan_ly`/`quan_ly_nhan_su` khác → chặn, báo "không đủ quyền" → kết thúc.
  - Tại bước 2: các trường hợp còn lại → tiếp tục bước 3.
- **Hậu điều kiện**: Tài khoản không đăng nhập được nữa; lịch sử vẫn được giữ (không xóa cứng).

### UC-38. Mở khóa tài khoản

- **Actor**: Quản lý (bất kỳ), hoặc Quản lý nhân sự (phạm vi hẹp hơn).
- **Tiền điều kiện**: Tài khoản đang bị khóa (UC-37 hoặc tự động do no-show, mục 9).
- **Luồng chính** (mục 8.7 điểm 6, mục 8.9):
  1. Tìm tài khoản đang khóa.
  2. Hệ thống kiểm tra actor có quyền mở khóa đúng tài khoản mục tiêu hay không (cùng quy tắc UC-37).
  3. Xem xét lý do bị khóa trước đó.
  4. Đặt lại `dang_hoat_dong = true`/`bi_khoa = false`.
- **Luồng rẽ nhánh**:
  - Tại bước 2: actor là `quan_ly_nhan_su` nhưng tài khoản mục tiêu là `ke_toan`/`quan_ly`/`quan_ly_nhan_su` khác → chặn, báo "không đủ quyền" → kết thúc.
- **Hậu điều kiện**: Tài khoản đăng nhập lại được.

### UC-39. Xem thống kê doanh thu/vận hành

- **Actor**: Phụ xe, Nhân viên quầy vé, Nhân viên gửi hàng, Điều độ viên, Quản lý, hoặc Quản lý nhân sự (phạm vi khác nhau).
- **Luồng chính**:
  1. Chọn khoảng thời gian + loại báo cáo muốn xem.
  2. Hệ thống lọc dữ liệu theo phạm vi của vai trò đang đăng nhập.
  3. Hệ thống tính động các chỉ số (doanh thu, tỷ lệ lấp đầy, số chuyến hủy/sự cố...) — không cache sẵn.
  4. Hiển thị báo cáo.
- **Luồng rẽ nhánh** (tại bước 2, theo vai trò):
  - Phụ xe → chỉ chuyến mình.
  - Nhân viên quầy vé → chỉ vé, điểm mình.
  - Nhân viên gửi hàng → chỉ hàng, điểm mình.
  - Điều độ viên → điểm/tuyến mình phụ trách.
  - Quản lý, Quản lý nhân sự → toàn hệ thống.
- **Hậu điều kiện**: Không thay đổi dữ liệu, chỉ đọc.

### UC-40. Gán lại xe gốc cho chuyến đang chạy thay ⚠

- **Actor**: Điều độ viên. **Use case ngoại lệ ⚠** — chỉ chạy khi có chuyến đang dùng xe thực tế khác xe gốc (kết quả của UC-20) và xe gốc đã sửa xong.
- **Tiền điều kiện**: Có ≥1 chuyến `chua_khoi_hanh` đang gắn cờ "chạy thay bằng xe khác" (`xe_thuc_te_id` khác `NULL`), xe gốc đã chuyển `trang_thai = hoat_dong` (UC-34, kèm thông báo nhắc).
- **Luồng chính** (mục 3.3):
  1. Điều độ viên xem danh sách các chuyến đang gắn cờ chạy thay.
  2. Chọn thời điểm phù hợp (thường là chuyến mà xe thay thế vừa/đang kết thúc đúng tại nơi xe gốc đang đỗ).
  3. Đặt lại `xe_thuc_te_id = NULL` cho chuyến đó trở đi trong chuỗi — từ đây các chuyến này dùng lại đúng xe gốc.
  4. Bỏ cờ "chạy thay" khỏi các chuyến vừa gán lại.
  5. Xe thay thế được giải phóng — quay lại vai trò dự phòng hoặc lịch trình riêng của nó (nếu có).
- **Hậu điều kiện**: Chuyến dùng lại đúng xe gốc, không còn gắn cờ.

### UC-41. Hủy vé nhận hoàn toàn bộ khi chuyến đang hoãn ⚠

- **Actor**: Khách hàng (hủy vé của mình) hoặc Nhân viên quầy vé (thao tác thay khi khách gọi hotline/ra quầy yêu cầu). **Use case ngoại lệ ⚠** — chỉ xảy ra khi chuyến đang trong tình trạng "hoãn" (kết quả nhánh rẽ của UC-20), không phải thao tác thường ngày.
- **Tiền điều kiện**: Vé ở trạng thái `da_thanh_toan`, thuộc 1 chuyến đang gắn cờ "đang hoãn" (mục 3.3 — xe hỏng trước giờ chạy, chưa tìm được xe thay thế kịp).
- **Luồng chính** (mục 3.3, mục 7):
  1. Khách xem thông báo chuyến đang hoãn + giờ dự kiến mới (từ UC-20), quyết định không muốn/không thể chờ.
  2. Chọn "Hủy vé nhận hoàn tiền" trên vé thuộc chuyến đang hoãn.
  3. Hệ thống xác nhận vé đủ điều kiện (đúng `da_thanh_toan`, đúng chuyến đang gắn cờ "đang hoãn").
  4. Vé chuyển `da_huy`, tạo 1 dòng `lich_su_hoan_tien` (`ly_do = 'hoan_truoc_gio_chay'`, `so_tien = gia`, `trang_thai = 'cho_xu_ly'`).
  5. Xử lý hoàn tiền: vé có `ma_giao_dich_cong_thanh_toan` (đã trả qua VNPay) → gọi API hoàn tiền VNPay → thành công thì cập nhật `trang_thai = 'da_hoan_tu_dong'`, về thẳng nguồn khách đã trả; nếu trả tiền mặt hoặc API hoàn tiền thất bại → giữ `trang_thai = 'cho_xu_ly'`, dẫn sang UC-22 để `ke_toan` xử lý.
- **Luồng rẽ nhánh**:
  - Tại bước 3: vé không thuộc chuyến đang hoãn (chuyến đã tìm được xe, hết hoãn) → từ chối, giải thích chuyến đã có xe chạy bình thường → kết thúc.
- **Hậu điều kiện**: Vé kết thúc vòng đời ở `da_huy`, khách nhận đủ 100% giá vé — không bao gồm bồi thường thiệt hại phát sinh khác (mục 7). Chuyến vẫn tiếp tục "đang hoãn" bình thường cho các khách khác chưa hủy.

### UC-42. Hủy vé nhận hoàn toàn bộ khi chuyến gặp sự cố do lỗi nhà xe giữa đường ⚠

- **Actor**: Khách hàng (hủy vé của mình) hoặc Nhân viên quầy vé (thao tác thay khi khách gọi hotline/ra quầy yêu cầu). **Use case ngoại lệ ⚠** — chỉ xảy ra khi chuyến đang `gap_su_co` do lỗi nhà xe và đang chờ xử lý (nhánh của UC-19), không phải thao tác thường ngày.
- **Tiền điều kiện**: Vé ở trạng thái `da_thanh_toan`, thuộc 1 chuyến đang `gap_su_co` với `loai_su_co = 'loi_nha_xe'`, chưa quay lại `dang_chay`.
- **Mục đích**: khách chủ động chấm dứt nghĩa vụ phục vụ của nhà xe với vé này — nhận hoàn 100% và **tự thu xếp phương tiện khác**, khác với UC-43 (hệ thống tự động hoàn nhưng vẫn tiếp tục chở khách).
- **Luồng chính** (mục 3.3, mục 7):
  1. Khách xem thông báo chuyến đang gặp sự cố xe, quyết định không muốn/không thể chờ (dù đã được tự động hoàn theo UC-43 hay chưa).
  2. Chọn "Hủy vé nhận hoàn tiền" trên vé thuộc chuyến này.
  3. Hệ thống xác nhận vé đủ điều kiện (đúng `da_thanh_toan`, đúng chuyến đang `gap_su_co` với `loai_su_co = 'loi_nha_xe'`).
  4. Vé chuyển `da_huy`. Nếu **chưa có** dòng `lich_su_hoan_tien` cho vé này (chưa được UC-43 tự động hoàn trước đó) → tạo mới (`ly_do = 'loi_nha_xe_giua_duong'`, `so_tien = gia`, `trang_thai = 'cho_xu_ly'`) và xử lý hoàn tiền như bước 5; nếu **đã có** (đã được hoàn từ UC-43 rồi) → chỉ cần chuyển vé `da_huy`, không hoàn thêm gì nữa (tiền đã hoàn từ trước).
  5. Xử lý hoàn tiền (chỉ khi tạo dòng mới ở bước 4): vé có `ma_giao_dich_cong_thanh_toan` (đã trả qua VNPay) → gọi API hoàn tiền VNPay → thành công thì cập nhật `trang_thai = 'da_hoan_tu_dong'`, về thẳng nguồn khách đã trả; nếu trả tiền mặt hoặc API hoàn tiền thất bại → giữ `trang_thai = 'cho_xu_ly'`, dẫn sang UC-22 để `ke_toan` xử lý.
- **Luồng rẽ nhánh**:
  - Tại bước 3: chuyến không còn `gap_su_co` (đã điều được xe, quay lại `dang_chay`), hoặc `loai_su_co = 'loi_khach_quan'` → từ chối, giải thích → kết thúc (sự cố khách quan không có lựa chọn hủy trong lúc chờ, mục 3.3/4/7).
- **Hậu điều kiện**: Vé kết thúc vòng đời ở `da_huy`, khách nhận đủ 100% giá vé, **hết nghĩa vụ phục vụ** (không còn được lên xe này nữa dù sau đó có xe thay thế). Chuyến vẫn tiếp tục xử lý sự cố bình thường cho các khách khác chưa hủy.

### UC-43. Tự động hoàn tiền cho khách chờ quá 3 tiếng do lỗi nhà xe (vẫn tiếp tục phục vụ) ⏱

- **Actor**: Hệ thống (job định kỳ — không phải actor người dùng thao tác trực tiếp).
- **Mục đích**: bù đắp cho khách khi nhà xe để sự cố lỗi nhà xe kéo dài quá lâu (≥ 3 tiếng) mà vẫn chưa xử lý xong — hoàn 100% tiền vé như một hình thức xin lỗi, nhưng **khác hẳn UC-42**: nhà xe **vẫn tiếp tục nghĩa vụ phục vụ**, chở khách miễn phí khi có xe, không hủy vé.
- **Tiền điều kiện**: Chuyến đang `gap_su_co` với `loai_su_co = 'loi_nha_xe'`, đã ≥ 3 tiếng kể từ lúc báo sự cố (UC-17) mà vẫn chưa quay lại `dang_chay`.
- **Luồng chính** (mục 3.3/4, mục 7):
  1. Xác định các vé `da_thanh_toan` trên chuyến này **chưa tự hủy** (chưa qua UC-42) và **chưa có** dòng `lich_su_hoan_tien` nào (tránh hoàn trùng nếu job chạy lại).
  2. Với mỗi vé, tạo 1 dòng `lich_su_hoan_tien` (`ly_do = 'tu_dong_hoan_qua_3_tieng'`, `so_tien = gia`, `trang_thai = 'cho_xu_ly'`) — vé **vẫn giữ nguyên `da_thanh_toan`**, không đổi trạng thái.
  3. Gửi thông báo WebSocket cho khách: đã được hoàn 100% tiền vé do chờ quá lâu, nhà xe vẫn tiếp tục phục vụ chuyến này miễn phí khi có xe.
- **Luồng rẽ nhánh**:
  - Vé có `ma_giao_dich_cong_thanh_toan` → gọi API hoàn tiền VNPay → thành công thì cập nhật `trang_thai = 'da_hoan_tu_dong'`.
  - Vé không có (tiền mặt), hoặc API hoàn tiền thất bại → giữ `trang_thai = 'cho_xu_ly'`, dẫn sang UC-22 để `ke_toan` xử lý — vé vẫn còn hiệu lực đi xe bình thường, không liên quan tới việc đã hoàn tiền hay chưa.
- **Hậu điều kiện**: Vé vẫn `da_thanh_toan`, đã hoàn 100% tiền. Khách vẫn có thể chủ động chuyển sang hủy hẳn sau đó nếu đổi ý (UC-42 — lúc này không hoàn thêm gì vì đã hoàn từ bước này).

---

## 13. Việc cần làm tiếp (chưa nằm trong file này)

- ~~`ARCHITECTURE.md` cần viết lại theo domain mới~~ — **đã cập nhật xong** (repository/service/route theo domain nhà xe, thêm cơ chế xử lý hết hạn giữ chỗ/no-show, bỏ Cloudinary).
- ~~`DATABASE.md` cần viết lại theo domain mới~~ — **đã cập nhật xong** (đầy đủ bảng theo mục 2.1, 3–6, 9–10 của file này, kèm sơ đồ quan hệ và các giá trị tính động).
- `ERD.dbml`/`ERD.md` vẫn còn mô tả domain cũ — cần vẽ lại theo đúng các bảng trong `DATABASE.md`.
- `CI_CD_VA_DEPLOY.md` không cần đổi gì (không phụ thuộc domain).
