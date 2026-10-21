"""Chốt ca tiền mặt của nhân viên gửi hàng — KE_HOACH_SUA_GUI_HANG.md mục 7, NGHIEP_VU_GUI_HANG.md mục 6.

Kỳ của 1 ca = từ lần chốt trước của CHÍNH nhân viên đó tới mốc `den_luc`. Mốc `den_luc` do màn xem trước sinh ra
và gửi lại khi xác nhận: số trên màn hình nhân viên thấy luôn khớp số được lưu, tiền phát sinh sau mốc tự sang ca sau.
Nhân viên chỉ chốt / xem ca của mình; quản lý xem mọi ca (chỉ xem, không chốt hộ).
"""

from datetime import date, datetime, timedelta, timezone

from app.repositories import chot_ca_repository as chot_ca_repo
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

SO_GIO_XEM_TRUOC_TOI_DA = 2          # màn xem trước mở quá 2 tiếng thì bắt tải lại (số tiền có thể đã khác nhiều)
DO_LECH_DONG_HO_CHO_PHEP = timedelta(seconds=5)
SO_NGAY_LOC_TOI_DA = 366


def _phai_co(tong: dict) -> int:
    return tong["tien_tra_truoc"] + tong["tien_cod"] - tong["tien_hoan"]


def xem_truoc(nhan_vien_id: str) -> dict:
    """Số tiền trong két LẼ RA phải có tính tới bây giờ, kèm từng khoản để nhân viên đối chiếu trước khi đếm."""
    den_luc = datetime.now(timezone.utc)
    tu_luc = chot_ca_repo.lay_moc_chot_cuoi(nhan_vien_id)
    tong = chot_ca_repo.tinh_tong(nhan_vien_id, tu_luc, den_luc)
    return {
        "tu_luc": tu_luc,
        "den_luc": den_luc,
        **tong,
        "tien_phai_co": _phai_co(tong),
        "khoan": chot_ca_repo.lay_khoan(nhan_vien_id, tu_luc, den_luc),
    }


def chot_ca(
    nhan_vien_id: str, van_phong_id: str | None, den_luc: datetime, tien_thuc_dem: int, ghi_chu: str | None
) -> dict:
    """Xác nhận chốt ca với đúng mốc `den_luc` của màn xem trước. Lệch tiền thì bắt buộc ghi chú."""
    if den_luc.tzinfo is None:
        raise GiaTriLoi("Mốc chốt ca phải kèm múi giờ")
    bay_gio = datetime.now(timezone.utc)
    if den_luc > bay_gio + DO_LECH_DONG_HO_CHO_PHEP:
        raise GiaTriLoi("Mốc chốt ca không được ở tương lai")
    if bay_gio - den_luc > timedelta(hours=SO_GIO_XEM_TRUOC_TOI_DA):
        raise GiaTriLoi("Màn chốt ca đã mở quá lâu, vui lòng tải lại để xem số tiền mới nhất")

    tu_luc = chot_ca_repo.lay_moc_chot_cuoi(nhan_vien_id)
    if tu_luc is not None and den_luc <= tu_luc:
        raise GiaTriLoi("Ca này đã được chốt rồi, vui lòng tải lại")
    if tien_thuc_dem - _phai_co(chot_ca_repo.tinh_tong(nhan_vien_id, tu_luc, den_luc)) != 0 and not ghi_chu:
        raise GiaTriLoi("Số tiền đếm được lệch với số phải có — bắt buộc ghi chú lý do")

    try:
        return chot_ca_repo.tao_chot_ca(nhan_vien_id, van_phong_id, den_luc, tien_thuc_dem, ghi_chu)
    except chot_ca_repo.DaChotSauMocNay:
        raise GiaTriLoi("Ca này vừa được chốt (bấm 2 lần hoặc mở 2 cửa sổ), vui lòng tải lại") from None


def _pham_vi_xem(nguoi_xem_id: str, la_quan_ly: bool) -> str | None:
    """Nhân viên chỉ xem ca của mình; quản lý xem mọi ca (None = không lọc theo nhân viên)."""
    return None if la_quan_ly else nguoi_xem_id


def lay_lich_su(
    nguoi_xem_id: str,
    la_quan_ly: bool,
    van_phong_id: str | None,
    tu_ngay: date | None,
    den_ngay: date | None,
    chi_lech: bool,
    limit: int,
    offset: int,
) -> dict:
    if tu_ngay and den_ngay:
        if tu_ngay > den_ngay:
            raise GiaTriLoi("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
        if (den_ngay - tu_ngay).days >= SO_NGAY_LOC_TOI_DA:
            raise GiaTriLoi("Khoảng lọc tối đa 1 năm")
    items, total = chot_ca_repo.lay_lich_su(
        _pham_vi_xem(nguoi_xem_id, la_quan_ly), van_phong_id, tu_ngay, den_ngay, chi_lech, limit, offset
    )
    return {"items": items, "total": total}


def lay_chi_tiet(chot_ca_id: str, nguoi_xem_id: str, la_quan_ly: bool) -> dict:
    """Chi tiết 1 lần chốt + từng khoản trong ca (để in lại phiếu)."""
    ca = chot_ca_repo.tim_theo_id(chot_ca_id)
    if not ca:
        raise KhongTimThay("Không tìm thấy lần chốt ca")
    if not la_quan_ly and str(ca["nhan_vien_id"]) != str(nguoi_xem_id):
        raise CamTruyCap("Chỉ xem được ca của chính mình")
    return {**ca, "khoan": chot_ca_repo.lay_khoan(str(ca["nhan_vien_id"]), ca["tu_luc"], ca["den_luc"])}
