"""Tự hủy vé chưa thanh toán khi chuyến đã qua giờ khởi hành."""

from app.repositories import ve_lock_repository as lock_repo
from app.services import thong_bao_khach_service as thong_bao


def chay() -> int:
    ve_da_huy = lock_repo.huy_ve_chua_thanh_toan_qua_gio_chay()
    theo_luot: dict[tuple[str, str], list[dict]] = {}
    for ve in ve_da_huy:
        if ve["khach_hang_id"]:
            theo_luot.setdefault((str(ve["khach_hang_id"]), ve["ma_dat_cho"]), []).append(ve)
    for (khach_hang_id, ma_dat_cho), cac_ve in theo_luot.items():
        thong_bao.gui(
            khach_hang_id,
            thong_bao.nd_huy_ve_qua_gio_chay(ma_dat_cho, sorted(v["so_ghe"] for v in cac_ve)),
            ve_id=cac_ve[0]["id"],
        )
    return len(ve_da_huy)
