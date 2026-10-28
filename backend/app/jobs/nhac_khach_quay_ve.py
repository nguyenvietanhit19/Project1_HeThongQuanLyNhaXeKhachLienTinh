"""Nhắc nhân viên quầy vé liên hệ khách còn giữ chỗ trả tại quầy sắp tới giờ chạy."""

import logging
from zoneinfo import ZoneInfo

from app.repositories import quay_ve_repository as repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.services import thong_bao_khach_service as thong_bao

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def chay() -> int:
    """Gửi tối đa một nhắc cho mỗi nhân viên và lượt đặt chỗ."""
    da_nhac = 0
    try:
        nguoi_can_dong_bo = set(thong_bao_repo.xoa_nhac_quay_ve_da_xu_ly())
        nguoi_can_dong_bo.update(thong_bao_repo.gop_nhac_quay_ve_trung())
        thong_bao.dong_bo_chuong_quay_ve(list(nguoi_can_dong_bo))
        for item in repo.cac_luot_tra_tai_quay_sap_chay():
            try:
                tong_tien = f"{int(item['tong_tien']):,}".replace(",", ".")
                noi_dung = (
                    f"Khách {item['ten_khach'] or 'vãng lai'} ({item['sdt_khach'] or 'chưa có số điện thoại'}) "
                    f"chưa thanh toán lượt {item['ma_dat_cho']} — chuyến {item['ma_chuyen']} "
                    f"khởi hành lúc {item['gio_khoi_hanh'].astimezone(MUI_GIO_VN):%H:%M %d/%m/%Y}, ghế {item['cac_ghe']} "
                    f"({item['so_ve']} vé, {tong_tien}đ). Vui lòng liên hệ khách."
                )
                if thong_bao.gui_nhac_quay_ve(item["nguoi_nhan_id"], item["ma_dat_cho"], noi_dung):
                    da_nhac += 1
            except Exception:  # noqa: BLE001
                logger.exception("Không nhắc được lượt đặt chỗ %s", item.get("ma_dat_cho"))
    except Exception:  # noqa: BLE001
        logger.exception("Không quét được các lượt đặt chỗ trả tại quầy sắp chạy")
    return da_nhac
