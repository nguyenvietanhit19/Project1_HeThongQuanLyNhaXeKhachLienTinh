"""Thông báo gửi cho KHÁCH HÀNG về vé của họ — NGHIEP_VU.md mục 8.1 điểm 4 (vé được xác nhận, sắp đến giờ khởi hành...).

Gồm: (1) `gui()` — ghi vào bảng thong_bao TRƯỚC (khách offline vẫn đọc lại được, DATABASE.md mục 6.1) rồi đẩy real-time qua
WebSocket; (2) các hàm dựng nội dung (hàm thuần, unit test được). Thông báo chỉ là phụ trợ: `gui()` KHÔNG BAO GIỜ ném lỗi
ra ngoài, vì lỗi thông báo không được làm hỏng nghiệp vụ chính (VD phản hồi IPN cho cổng thanh toán, job quét vé).

Các sự kiện do service/job tương ứng gọi: chốt trả tại quầy (dat_ve_service), thanh toán thành công/không thành công
(thanh_toan_service), hết hạn giữ chỗ (jobs/quet_ve_het_han), không đến (jobs/quet_no_show), sắp đến giờ đón
(jobs/quet_nhac_sap_di). Thông báo về xe/sự cố do phụ xe và điều độ viên gửi ở chuyen_xe_service.
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from app.repositories import thong_bao_repository as thong_bao_repo
from app.services.websocket_manager import broadcast_sync

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def gui(nguoi_nhan_id: str | None, noi_dung: str, ve_id: str | None = None) -> None:
    """Lưu rồi đẩy real-time cho 1 khách. Bỏ qua nếu không có người nhận (vé bán cho khách vãng lai). Nuốt mọi lỗi."""
    if not nguoi_nhan_id:
        return
    try:
        thong_bao_repo.tao(str(nguoi_nhan_id), noi_dung, ve_id=str(ve_id) if ve_id else None)
        broadcast_sync(str(nguoi_nhan_id), noi_dung)
    except Exception:  # noqa: BLE001 — xem docstring đầu file
        logger.exception("Không gửi được thông báo cho khách %s", nguoi_nhan_id)


# ---------------------------------------------------------
# Dựng nội dung
# ---------------------------------------------------------
def _ghe(danh_sach_ghe: list[str]) -> str:
    return ", ".join(danh_sach_ghe)


def _tien(so_tien: int) -> str:
    return f"{int(so_tien):,}".replace(",", ".") + "đ"


def _gio(thoi_diem: datetime.datetime) -> str:
    return thoi_diem.astimezone(MUI_GIO_VN).strftime("%H:%M ngày %d/%m/%Y")


def nd_dat_ve_tai_quay(ma_dat_cho: str, danh_sach_ghe: list[str], ten_diem_don: str, gio_don: datetime.datetime, tong_tien: int) -> str:
    return (
        f"Đặt vé thành công — mã đặt chỗ {ma_dat_cho}, ghế {_ghe(danh_sach_ghe)}. Vui lòng ra {ten_diem_don} trước "
        f"{_gio(gio_don)} để nhận vé và thanh toán {_tien(tong_tien)}."
    )


def nd_thanh_toan_thanh_cong(ma_dat_cho: str, danh_sach_ghe: list[str], so_tien: int) -> str:
    return f"Thanh toán thành công {_tien(so_tien)} — mã đặt chỗ {ma_dat_cho}, ghế {_ghe(danh_sach_ghe)}."


def nd_thanh_toan_ve_thanh_cong(ma_ve: str, so_ghe: str, so_tien: int) -> str:
    return f"Thanh toán thành công {_tien(so_tien)} cho vé {ma_ve} (ghế {so_ghe})."


def nd_thanh_toan_that_bai(ma_dat_cho: str, danh_sach_ghe: list[str]) -> str:
    return (
        f"Thanh toán không thành công — mã đặt chỗ {ma_dat_cho} (ghế {_ghe(danh_sach_ghe)}) đã bị hủy giữ chỗ, "
        "ghế được nhả cho người khác. Bạn có thể đặt lại."
    )


def nd_het_han(ma_dat_cho: str, danh_sach_ghe: list[str]) -> str:
    return f"Mã đặt chỗ {ma_dat_cho} (ghế {_ghe(danh_sach_ghe)}) đã hết hạn giữ chỗ, ghế được nhả cho người khác. Bạn có thể đặt lại."


def nd_khong_den(ma_ve: str, so_ghe: str, so_lan: int, nguong: int, so_ngay: int) -> str:
    canh_bao = (
        f"Bạn đã không đến {so_lan} lần trong {so_ngay} ngày nên từ nay chỉ được thanh toán ngay khi đặt vé."
        if so_lan >= nguong
        else f"Không đến {nguong} lần trong {so_ngay} ngày sẽ bị hạn chế thanh toán tại quầy (hiện {so_lan}/{nguong})."
    )
    return f"Vé {ma_ve} (ghế {so_ghe}) bị ghi nhận là không đến. {canh_bao}"


def nd_sap_di(
    ma_dat_cho: str, danh_sach_ghe: list[str], ten_diem_don: str, ten_diem_tra: str, gio_don: datetime.datetime, con_phut: int
) -> str:
    con = f"{con_phut // 60} giờ {con_phut % 60:02d} phút" if con_phut >= 60 else f"{max(con_phut, 1)} phút"
    return (
        f"Sắp đến giờ đi: {ten_diem_don} → {ten_diem_tra} lúc {_gio(gio_don)} (còn khoảng {con}). "
        f"Mã đặt chỗ {ma_dat_cho}, ghế {_ghe(danh_sach_ghe)}."
    )

