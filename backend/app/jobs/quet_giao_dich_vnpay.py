"""Hỏi VNPay (querydr) kết quả các lượt đang chờ thanh toán — dự phòng khi IPN không tới (⏱, NGHIEP_VU.md mục 6).

Chỉ chạy ở chế độ VNPAY_CHE_DO=sandbox (chế độ giả lập đã tự gọi IPN). Khách thanh toán xong rồi đóng trình duyệt
thì không có trang kết quả nào gọi xác nhận; job này bắt các ca đó trước khi vé hết hạn.
"""

from app.services import thanh_toan_service


def chay() -> int:
    return thanh_toan_service.quet_giao_dich_dang_cho()
