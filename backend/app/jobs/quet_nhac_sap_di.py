"""Nhắc khách "sắp đến giờ đi" (⏱) — NGHIEP_VU.md mục 8.1 điểm 4.

Chạy định kỳ: vé đã chắc chắn đi mà giờ đón (tại đúng điểm đón của vé) còn chưa tới `NHAC_TRUOC_GIO_DON_PHUT` phút thì gửi
đúng 1 thông báo cho mỗi lượt đặt (gộp các ghế cùng lượt) rồi đánh dấu vé đã nhắc, để không nhắc lại. Không phải use case riêng —
là cơ chế nền của luồng đặt vé (UC-05), cùng nhóm với quet_ve_het_han và quet_no_show.
"""

import datetime

from app.config import NHAC_TRUOC_GIO_DON_PHUT
from app.repositories import ve_nhac_repository as nhac_repo
from app.services import thong_bao_khach_service as thong_bao


def chay(phut_truoc_gio_don: int = NHAC_TRUOC_GIO_DON_PHUT, bay_gio: datetime.datetime | None = None) -> int:
    """Trả số lượt đặt đã nhắc."""
    bay_gio = bay_gio or datetime.datetime.now(datetime.timezone.utc)
    theo_luot: dict[tuple[str, str], list[dict]] = {}
    for ve in nhac_repo.tim_ve_can_nhac(phut_truoc_gio_don):
        theo_luot.setdefault((str(ve["khach_hang_id"]), ve["ma_dat_cho"]), []).append(ve)
    for (khach_hang_id, ma_dat_cho), cac_ve in theo_luot.items():
        dau = cac_ve[0]
        con_phut = int((dau["gio_don_du_kien"] - bay_gio).total_seconds() // 60)
        thong_bao.gui(
            khach_hang_id,
            thong_bao.nd_sap_di(
                ma_dat_cho, sorted(v["so_ghe"] for v in cac_ve), dau["ten_diem_don"], dau["ten_diem_tra"], dau["gio_don_du_kien"], con_phut
            ),
            ve_id=dau["id"],
        )
        nhac_repo.danh_dau_da_nhac([v["id"] for v in cac_ve])
    return len(theo_luot)
