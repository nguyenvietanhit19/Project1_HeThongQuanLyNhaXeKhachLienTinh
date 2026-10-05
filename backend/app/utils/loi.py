"""Các lớp lỗi nghiệp vụ dùng chung — Service raise, main.py bắt và đổi
thành đúng mã HTTP (xem exception_handler trong main.py). Route không cần
tự viết try/except, giữ đúng nguyên tắc "route mỏng" (ARCHITECTURE.md mục 2).
"""


class GiaTriLoi(Exception):
    """Dữ liệu/trạng thái không hợp lệ — main.py đổi thành HTTP 400."""


class KhongDuQuyen(Exception):
    """Sai thông tin đăng nhập, token hỏng, tài khoản bị khóa... — HTTP 401/403."""


class CamTruyCap(Exception):
    """Đã đăng nhập hợp lệ nhưng thao tác ngoài phạm vi được giao (VD nhân
    viên gửi hàng xem đơn của văn phòng khác) — HTTP 403. Tách khỏi
    KhongDuQuyen (401) để frontend không hiểu nhầm thành hết phiên đăng nhập."""


class KhongTimThay(Exception):
    """Không tìm thấy bản ghi được yêu cầu — HTTP 404."""


class LoiHeThong(Exception):
    """Lỗi hạ tầng (gửi email thất bại...) — HTTP 500."""
