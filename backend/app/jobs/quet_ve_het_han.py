"""Quét vé giữ chỗ quá hạn → `het_han` (⏱) — NGHIEP_VU.md mục 6, ARCHITECTURE.md mục 5.

Chỉ áp dụng cho vé có hạn (giữ tạm lúc chọn điểm đón/trả, hoặc thanh toán ngay). Vé "thanh toán tại quầy" không có
hạn nên không bao giờ qua đây (mục 6: nó kết thúc bằng khong_den, không phải het_han). Ghế đã mở lại cho người
khác từ lúc quá hạn nhờ kiểm tra hạn ngay trong truy vấn; job chỉ dọn trạng thái cho đúng vòng đời vé.
"""

from app.repositories import ve_lock_repository as lock_repo
from app.services import thong_bao_khach_service as thong_bao


def chay() -> int:
    """Trả số vé vừa hết hạn. Mỗi lượt đặt (của 1 khách) được báo 1 thông báo, kể cả khi chỉ 1 phần vé hết hạn."""
    ve_het_han = lock_repo.danh_dau_het_han_qua_han()
    theo_luot: dict[tuple[str, str], list[dict]] = {}
    for ve in ve_het_han:
        if ve["khach_hang_id"]:
            theo_luot.setdefault((str(ve["khach_hang_id"]), ve["ma_dat_cho"]), []).append(ve)
    for (khach_hang_id, ma_dat_cho), cac_ve in theo_luot.items():
        thong_bao.gui(khach_hang_id, thong_bao.nd_het_han(ma_dat_cho, sorted(v["so_ghe"] for v in cac_ve)), ve_id=cac_ve[0]["id"])
    return len(ve_het_han)
