"""Quét vé giữ chỗ quá hạn → `het_han` (⏱) — NGHIEP_VU.md mục 6, ARCHITECTURE.md mục 5.

Chỉ áp dụng cho vé có hạn (giữ tạm lúc chọn điểm đón/trả, hoặc thanh toán ngay). Vé "thanh toán tại quầy" không có
hạn nên không bao giờ qua đây (mục 6: nó kết thúc bằng khong_den, không phải het_han). Ghế đã mở lại cho người
khác từ lúc quá hạn nhờ kiểm tra hạn ngay trong truy vấn; job chỉ dọn trạng thái cho đúng vòng đời vé.
"""

from app.repositories import ve_lock_repository as lock_repo


def chay() -> int:
    return lock_repo.danh_dau_het_han_qua_han()
