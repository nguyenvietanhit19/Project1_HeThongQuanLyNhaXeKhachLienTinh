"""Danh sách 34 đơn vị hành chính cấp tỉnh của Việt Nam sau sáp nhập,
hiệu lực từ 01/07/2025 (Nghị quyết 202/2025/QH15, Quốc hội khóa XV thông
qua 12/06/2025) — 28 tỉnh + 6 thành phố trực thuộc trung ương.

Dùng để validate cột khu_vuc.tinh_thanh (UC-29) — không cho nhập tự do,
chỉ chọn đúng 1 trong các giá trị này (kiểm tra lại ở server, không chỉ
tin dropdown phía client).

QUAN TRỌNG: danh sách này phải khớp 100% với
frontend/nhan-vien/shared/tinh-thanh.js — sửa 1 bên phải sửa bên kia.
"""

DANH_SACH_TINH_THANH: list[str] = [
    # 6 thành phố trực thuộc trung ương
    "Hà Nội",
    "Hải Phòng",
    "Đà Nẵng",
    "Thành phố Hồ Chí Minh",
    "Cần Thơ",
    "Huế",
    # 28 tỉnh
    "Cao Bằng",
    "Điện Biên",
    "Hà Tĩnh",
    "Lai Châu",
    "Lạng Sơn",
    "Nghệ An",
    "Quảng Ninh",
    "Thanh Hóa",
    "Sơn La",
    "Tuyên Quang",
    "Lào Cai",
    "Thái Nguyên",
    "Phú Thọ",
    "Bắc Ninh",
    "Hưng Yên",
    "Ninh Bình",
    "Quảng Trị",
    "Quảng Ngãi",
    "Gia Lai",
    "Khánh Hòa",
    "Lâm Đồng",
    "Đắk Lắk",
    "Đồng Nai",
    "Tây Ninh",
    "Vĩnh Long",
    "Đồng Tháp",
    "Cà Mau",
    "An Giang",
]
