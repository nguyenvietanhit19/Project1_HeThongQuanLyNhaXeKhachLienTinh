# Phong cách thiết kế UI — tham khảo từ Dribbble

Tài liệu này ghi lại phong cách thiết kế cả nhóm thống nhất tham khảo (từ 1 bộ giao diện app đặt vé xe khách trên Dribbble), để **mọi người vẽ giao diện theo cùng 1 gu**, không ai tự chọn màu/bo góc/đổ bóng khác nhau. Giá trị thật (mã màu, bo góc, đổ bóng) nằm ở file [`frontend/shared/design-tokens.css`](./frontend/shared/design-tokens.css) — **luôn dùng qua file đó, không tự gõ mã hex/px riêng trong file khác**.

---

## 1. Phong cách chủ đạo: "Soft Card UI" + minh họa isometric 3D

- **Bố cục dạng thẻ nổi**: mọi nội dung nằm trong card bo góc lớn, đặt trên nền pastel trung tính (không phải trắng thuần) — tạo cảm giác thẻ "nổi lên" khỏi nền.
- **Tương phản sáng-tối có chủ đích**: nút chức năng phụ (đóng, chia sẻ, zoom, cài đặt) dùng hình tròn **đen tuyệt đối** làm điểm neo thị giác, đối lập với nền pastel tím nhạt.
- **Pill/chip tràn ngập giao diện**: hầu hết nhãn (thời gian, số lượng, đơn vị tiền, tag) đều bo tròn hoàn toàn — không có nhãn hình chữ nhật vuông góc nào.
- **Đổ bóng luôn mềm, lan tỏa** — không dùng bóng cứng/sắc nét ở đâu cả, tạo cảm giác "nhấc nhẹ" thay vì phẳng.
- **Chữ tiêu đề lớn, đậm** — tương phản rõ với nội dung phụ cỡ nhỏ, phân cấp thị giác rõ ràng.

## 2. Bảng màu

| Vai trò | Biến CSS | Giá trị | Dùng khi nào |
|---|---|---|---|
| Chủ đạo | `--color-primary` | Cam `#F5A623` | CTA, tab/trạng thái đang chọn, badge nổi bật |
| Phụ (thương hiệu) | `--color-secondary` | Tím `#5B3E96` | Card hero, header, minh họa bản đồ |
| Nền tổng thể | `--color-bg-canvas` | Xám-tím `#DAD7E3` | Nền ngoài cùng của trang |
| Nền card | `--color-bg-surface` | Trắng `#FFFFFF` | Card nội dung, danh sách |
| Nền tương phản | `--color-bg-dark` | Đen `#1A1A1E` | Nút icon phụ |
| Thành công | `--color-success` | Xanh lá `#22C55E` | Đúng giờ, hoàn thành, khả dụng |
| Cảnh báo/đã dùng | `--color-danger` | Đỏ-cam `#EF4444` (chỉ viền, không fill đặc) | Ghế/chỗ đã có người — dùng viền để không gây cảm giác "báo động gắt" |

*Mã hex là ước lượng từ quan sát ảnh tham khảo, không phải lấy mẫu pixel tuyệt đối — nếu cần tinh chỉnh, cả nhóm cùng thống nhất sửa 1 lần trong `design-tokens.css`, không tự đổi riêng ở trang mình.*

## 3. Thành phần UI tiêu bản

| Thành phần | Đặc điểm | Class dùng sẵn trong `design-tokens.css` |
|---|---|---|
| Nút icon | Hình tròn ~44px, đổ bóng nhẹ | `.btn-icon-circle`, `.btn-icon-circle--dark` |
| Pill/chip | Bo tròn hoàn toàn (`border-radius: 999px`) | `.pill`, `.pill--primary`, `.pill--dark`, `.pill--success` |
| Card lớn | Bo góc ~24px, chỉ đổ bóng, không viền | `.card`, `.card--hero` |
| Ghế trong sơ đồ chọn ghế | Ô tròn nhỏ, 3 trạng thái màu | `.seat--trong`, `.seat--da-chon`, `.seat--da-dat` |

### Áp dụng đúng nghiệp vụ, không chỉ đẹp mắt

3 trạng thái `.seat--*` map thẳng vào đúng khái niệm "còn trống / đã khóa / đã có người" ở `NGHIEP_VU.md` mục 6 (chống trùng ghế) — khi domain 2 (Khách hàng + Quầy vé) dựng sơ đồ ghế thật, dùng đúng 3 class này, không tự nghĩ màu khác.

## 4. Cách dùng trong trang HTML

Mọi trang (cả `frontend/khach-hang/` và `frontend/nhan-vien/`) nhúng file dùng chung này **trước** CSS riêng của trang:

```html
<link rel="stylesheet" href="/shared/design-tokens.css">
<link rel="stylesheet" href="trang-cua-toi.css">
```

Trong CSS riêng, luôn tham chiếu qua biến, không tự viết lại mã hex:

```css
/* Đúng */
.gia-ve { color: var(--color-primary); }

/* Sai — không tự gõ lại mã hex */
.gia-ve { color: #F5A623; }
```

## 5. Khi cần đổi/thêm màu hoặc component mới

Chỉ sửa đúng `frontend/shared/design-tokens.css` — file này do người 1 (trưởng nhóm) quản lý chung (giống `nav-*.js`/`api-client.js` đã bàn ở `CONTRIBUTING.md` mục 6), người khác cần thêm màu/component mới thì **thêm biến/class mới vào cuối file**, không sửa giá trị đã có nếu chưa hỏi cả nhóm — tránh 1 người đổi màu chủ đạo làm lệch giao diện của người khác đang code song song.
