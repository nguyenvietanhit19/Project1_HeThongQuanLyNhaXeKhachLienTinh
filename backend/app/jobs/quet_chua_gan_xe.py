"""Job định kỳ: Tự động chuyển "đang hoãn" khi tới giờ chạy mà chưa gán xe (UC-45 ⏱).

Căn cứ thiết kế:
- NGHIEP_VU.md mục 3.3, mục 7, UC-45
- ARCHITECTURE.md mục 5 (Chiến lược xử lý hết hạn — bảng đối chiếu dòng UC-45)
- CONTRIBUTING.md mục 5.2 (Mỗi người sở hữu 1 file job riêng)

Người 4 (Son — Điều độ viên) sở hữu file này.
Chạy định kỳ 1 phút/lần bằng APScheduler (AsyncIOScheduler) trong tiến trình FastAPI.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import chuyen_xe_service

logger = logging.getLogger("jobs.quet_chua_gan_xe")


async def quet_chuyen_chua_gan_xe():
    """Tác vụ định kỳ quét các chuyến chưa khởi hành đã quá giờ mà chưa có xe_id.
    Chạy mỗi 1 phút một lần.
    """
    try:
        chuyen_da_hoan = await chuyen_xe_service.xu_ly_tu_dong_chuyen_dang_hoan()
        if chuyen_da_hoan:
            logger.warning(
                f"[UC-45] Đã tự động chuyển {len(chuyen_da_hoan)} chuyến sang 'đang hoãn': "
                f"{[c['id'] for c in chuyen_da_hoan]}"
            )
    except Exception as e:
        logger.error(f"[UC-45] Lỗi trong job quét chưa gán xe: {e}", exc_info=True)


def dang_ky_job(scheduler: AsyncIOScheduler) -> None:
    """Đăng ký job UC-45 vào scheduler chung của ứng dụng."""
    scheduler.add_job(
        quet_chuyen_chua_gan_xe,
        "interval",
        minutes=1,
        id="uc45_quet_chua_gan_xe",
        replace_existing=True,
    )
    logger.info("[UC-45] Đã đăng ký job 'quet_chua_gan_xe' chu kỳ 1 phút.")
