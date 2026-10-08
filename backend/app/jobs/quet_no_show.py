"""UC-14 (⏱) — đánh dấu no-show tự động, NGHIEP_VU.md mục 8.2 điểm 6, mục 9.

Job chạy định kỳ (APScheduler, ARCHITECTURE.md mục 5) — actor là "Hệ
thống", không phải phụ xe hay bất kỳ ai bấm nút. Mốc chốt là giờ dự kiến
tại ĐÚNG điểm đón của từng vé (không phải giờ khởi hành chung của chuyến)
trừ đi X phút.
"""

from app.repositories import ho_so_khach_hang_repository as ho_so_repo
from app.repositories import ve_repository as ve_repo
from app.services import thong_bao_khach_service as thong_bao

X_PHUT_TRUOC_GIO_DON = 5  # mục 8.2 điểm 6 — mặc định, quan_ly cấu hình được (chưa có UI cấu hình)
NGUONG_SO_LAN_VI_PHAM = 3  # mục 9 — mặc định 3 lần / 30 ngày
NGUONG_SO_NGAY_VI_PHAM = 30


def chay() -> None:
    for ve in ve_repo.tim_ve_qua_gio_len_xe(X_PHUT_TRUOC_GIO_DON):
        ve_repo.danh_dau_khong_den(ve["id"])
        if ve["khach_hang_id"]:
            so_lan = _kiem_tra_va_khoa_neu_vi_pham_qua_nguong(ve["khach_hang_id"])
            thong_bao.gui(
                ve["khach_hang_id"],
                thong_bao.nd_khong_den(ve.get("ma_ve", ""), ve.get("so_ghe", ""), so_lan, NGUONG_SO_LAN_VI_PHAM, NGUONG_SO_NGAY_VI_PHAM),
                ve_id=ve["id"],
            )


def _kiem_tra_va_khoa_neu_vi_pham_qua_nguong(khach_hang_id: str) -> int:
    """Khóa thanh toán tại quầy nếu đủ ngưỡng; trả số lần vi phạm hiện tại (để báo khách)."""
    so_lan = ve_repo.dem_vi_pham_no_show(khach_hang_id, NGUONG_SO_NGAY_VI_PHAM)
    if so_lan >= NGUONG_SO_LAN_VI_PHAM:
        ho_so_repo.khoa_thanh_toan_tai_quay(khach_hang_id)
    return so_lan
