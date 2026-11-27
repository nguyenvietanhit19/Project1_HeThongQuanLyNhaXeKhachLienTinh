"""Khách "không đến" (no-show) — NGHIEP_VU.md mục 8.2 điểm 6, mục 9.

KHÔNG có job tự đánh dấu theo giờ: vé chỉ thành "không đến" khi phụ xe bấm "Bắt đầu di chuyển" rời điểm đón và tích xác nhận từng
khách chưa lên (di_chuyen_service). Phụ xe linh động đợi khách bao lâu tùy tình hình thực tế; chuyến chưa chạy / đang hoãn thì
không ai bị tính. Phụ xe tích nhầm hoặc khách đuổi kịp xe thì hoàn tác được khi xe CHƯA tới điểm kế tiếp.
"""

from app.repositories import ho_so_khach_hang_repository as ho_so_repo
from app.repositories import ve_repository as ve_repo
from app.services import thong_bao_khach_service as thong_bao

NGUONG_SO_LAN_VI_PHAM = 3  # mục 9 — mặc định 3 lần / 30 ngày
NGUONG_SO_NGAY_VI_PHAM = 30


def se_bi_danh_dau(ve: dict) -> bool:
    """Vé nào bị tính "không đến" khi xe rời điểm đón: vé đã trả tiền, hoặc vé trả tại quầy chưa trả (không có hạn giữ).
    Vé đang giữ tạm có hạn (khách đang thanh toán dở) KHÔNG tính — tự hết hạn theo job quet_ve_het_han."""
    return ve["trang_thai"] == "da_thanh_toan" or (ve["trang_thai"] == "giu_cho" and ve.get("han_giu_cho_den") is None)


def danh_dau_khong_den(ve: dict) -> bool:
    """Đánh dấu 1 vé "không đến" + tính vi phạm + báo khách. `ve` cần có id, khach_hang_id, ma_ve, so_ghe, ma_dat_cho.
    Trả False (không phạt, không báo) nếu vé không còn đủ điều kiện, ví dụ vừa được người khác xử lý."""
    if not ve_repo.danh_dau_khong_den(ve["id"]):
        return False
    if ve.get("ma_dat_cho"):
        thong_bao.don_nhac_quay_ve(ve["ma_dat_cho"])  # vé trả tại quầy đã khép → gỡ chuông nhắc quầy liên hệ khách
    if ve["khach_hang_id"]:
        so_lan = _kiem_tra_va_khoa_neu_vi_pham_qua_nguong(ve["khach_hang_id"])
        thong_bao.gui(
            ve["khach_hang_id"],
            thong_bao.nd_khong_den(ve.get("ma_ve", ""), ve.get("so_ghe", ""), so_lan, NGUONG_SO_LAN_VI_PHAM, NGUONG_SO_NGAY_VI_PHAM),
            ve_id=ve["id"],
        )
    return True


def _kiem_tra_va_khoa_neu_vi_pham_qua_nguong(khach_hang_id: str) -> int:
    """Khóa thanh toán tại quầy nếu đủ ngưỡng; trả số lần vi phạm hiện tại (để báo khách)."""
    so_lan = ve_repo.dem_vi_pham_no_show(khach_hang_id, NGUONG_SO_NGAY_VI_PHAM)
    if so_lan >= NGUONG_SO_LAN_VI_PHAM:
        ho_so_repo.khoa_thanh_toan_tai_quay(khach_hang_id)
    return so_lan


def hoan_tac_khong_den(ve: dict) -> bool:
    """Khách đã trả tiền được ghi nhận lại là ĐÃ LÊN XE; gỡ vi phạm vừa tính. Chỉ gỡ khóa "thanh toán tại quầy" khi chính vé này
    nằm trong số làm đủ ngưỡng (trước khi hoàn tác đủ ngưỡng, sau đó không đủ) — khóa cũ do các lần vi phạm đã quá 30 ngày giữ nguyên.
    `ve` cần có id, khach_hang_id, ma_ve, so_ghe. Điều kiện về chuyến do nơi gọi kiểm tra."""
    khach = ve.get("khach_hang_id")
    truoc = ve_repo.dem_vi_pham_no_show(khach, NGUONG_SO_NGAY_VI_PHAM) if khach else 0
    if not ve_repo.hoan_tac_khong_den(ve["id"]):
        return False
    if khach:
        sau = ve_repo.dem_vi_pham_no_show(khach, NGUONG_SO_NGAY_VI_PHAM)
        if truoc >= NGUONG_SO_LAN_VI_PHAM > sau:
            ho_so_repo.mo_khoa_thanh_toan_tai_quay(khach)
        thong_bao.gui(khach, thong_bao.nd_hoan_tac_khong_den(ve.get("ma_ve", ""), ve.get("so_ghe", "")), ve_id=ve["id"])
    return True
