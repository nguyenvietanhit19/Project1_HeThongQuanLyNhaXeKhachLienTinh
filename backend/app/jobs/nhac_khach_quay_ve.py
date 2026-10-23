"""Nhắc nhân viên quầy vé liên hệ khách còn giữ chỗ trả tại quầy sắp tới giờ chạy."""

import logging
from zoneinfo import ZoneInfo

from app.repositories import quay_ve_repository as repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.services import thong_bao_khach_service as thong_bao

logger = logging.getLogger(__name__)
DUONG_DAN_TRA_CUU = "/nhan-vien/quay-ve/tra-cuu-ve.html"
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def chay() -> int:
    """Gửi tối đa một nhắc cho mỗi nhân viên và lượt đặt chỗ."""
    da_nhac = 0
    try:
        for item in repo.cac_luot_tra_tai_quay_sap_chay():
            try:
                tong_tien = f"{int(item['tong_tien']):,}".replace(",", ".")
                noi_dung = (
                    f"Khách {item['ten_khach'] or 'vãng lai'} ({item['sdt_khach'] or 'chưa có số điện thoại'}) "
                    f"chưa thanh toán lượt {item['ma_dat_cho']} — chuyến {item['ma_chuyen']} "
                    f"khởi hành lúc {item['gio_khoi_hanh'].astimezone(MUI_GIO_VN):%H:%M %d/%m/%Y}, ghế {item['cac_ghe']} "
                    f"({item['so_ve']} vé, {tong_tien}đ). Vui lòng liên hệ khách."
                )
                if thong_bao_repo.da_co_thong_bao_giong(item["nguoi_nhan_id"], noi_dung):
                    continue
                thong_bao.gui(
                    item["nguoi_nhan_id"], noi_dung,
                    duong_dan=f"{DUONG_DAN_TRA_CUU}?ma_dat_cho={item['ma_dat_cho']}",
                )
                da_nhac += 1
            except Exception:  # noqa: BLE001
                logger.exception("Không nhắc được lượt đặt chỗ %s", item.get("ma_dat_cho"))
    except Exception:  # noqa: BLE001
        logger.exception("Không quét được các lượt đặt chỗ trả tại quầy sắp chạy")
    return da_nhac
