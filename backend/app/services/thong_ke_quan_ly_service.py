"""Thống kê toàn hệ thống cho quản lý (UC-39, NGHIEP_VU.md mục 8.7 điểm 4) — 7 tab, mỗi tab 1 lần gọi API.

Mỗi tab trả số của kỳ đang xem kèm số của KỲ SO SÁNH (để giao diện ghi ▲/▼ %), chuỗi theo giờ / ngày / tháng để vẽ biểu đồ, và các bảng
chia nhóm. Quy ước tính tiền, lấp đầy, đúng giờ: xem đầu file repositories/thong_ke_quan_ly_repository.py.
"""

from datetime import date, timedelta

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import thong_ke_quan_ly_repository as repo
from app.services.dieu_do_service import NGUONG_NHAC_CHUA_GAN_XE_GIO
from app.utils.loi import GiaTriLoi

SO_NGAY_TOI_DA = 366  # tối đa 1 năm
SO_NGAY_CHIA_THEO_NGAY_TOI_DA = 62  # kỳ dài hơn thì biểu đồ chia theo tháng
CAC_TAB = ("tong-quan", "doanh-thu", "chuyen", "ve", "gui-hang", "hoan-tien", "xe-nhan-su")


def _don_vi(so_ngay: int) -> str:
    if so_ngay == 1:
        return "gio"
    return "ngay" if so_ngay <= SO_NGAY_CHIA_THEO_NGAY_TOI_DA else "thang"


def xac_dinh_ky(tu_ngay: date, den_ngay: date, so_sanh_tu: date | None = None, so_sanh_den: date | None = None,
                tuyen_id: str | None = None) -> dict:
    """Kiểm tra kỳ xem + kỳ so sánh. Không truyền kỳ so sánh thì lấy đoạn cùng độ dài ngay trước kỳ xem."""
    if tu_ngay > den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    so_ngay = (den_ngay - tu_ngay).days + 1
    if so_ngay > SO_NGAY_TOI_DA:
        raise GiaTriLoi("Khoảng thống kê tối đa 1 năm")
    if (so_sanh_tu is None) != (so_sanh_den is None):
        raise GiaTriLoi("Kỳ so sánh cần đủ ngày bắt đầu và ngày kết thúc")
    if so_sanh_tu is None:
        so_sanh_den = tu_ngay - timedelta(days=1)
        so_sanh_tu = tu_ngay - timedelta(days=so_ngay)
    if so_sanh_tu > so_sanh_den:
        raise GiaTriLoi("Kỳ so sánh không hợp lệ")
    if (so_sanh_den - so_sanh_tu).days + 1 > SO_NGAY_TOI_DA:
        raise GiaTriLoi("Kỳ so sánh tối đa 1 năm")
    if tuyen_id and not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    return {
        "tu_ngay": tu_ngay, "den_ngay": den_ngay, "so_ngay": so_ngay, "don_vi": _don_vi(so_ngay),
        "so_sanh_tu": so_sanh_tu, "so_sanh_den": so_sanh_den, "tuyen_id": tuyen_id,
    }


def _p(ky: dict, truoc: bool = False) -> dict:
    if truoc:
        return {"tu": ky["so_sanh_tu"], "den": ky["so_sanh_den"], "tuyen": ky["tuyen_id"]}
    return {"tu": ky["tu_ngay"], "den": ky["den_ngay"], "tuyen": ky["tuyen_id"]}


def _hai_ky(ham, ky: dict) -> dict:
    return {"hien_tai": ham(_p(ky)), "truoc": ham(_p(ky, True))}


def gop_theo_tuyen(tien: list[dict], chuyen: list[dict]) -> list[dict]:
    """Ghép tiền theo tuyến (ngày thu) với chỉ số chuyến theo tuyến (ngày chạy) thành 1 dòng / tuyến; tuyến thiếu phía nào thì số 0."""
    khoa_tien = ("tien_ve", "tien_hang", "hoan_ve", "hoan_hang", "tien_hoan", "thuan", "so_ve")
    khoa_chuyen = ("tong_chuyen", "da_chay", "hoan_thanh", "da_huy", "co_su_co", "ghe_ban", "tong_ghe", "co_gio_xuat_phat", "dung_gio")
    gop: dict[str, dict] = {}
    for nguon, khoa in ((tien, khoa_tien), (chuyen, khoa_chuyen)):
        for r in nguon:
            dong = gop.setdefault(r["tuyen_id"], {"tuyen_id": r["tuyen_id"], "ma": r["ma"], "ten": r["ten"]})
            dong.update({k: r.get(k, 0) for k in khoa})
    ket_qua = []
    for dong in gop.values():
        for k in khoa_tien + khoa_chuyen:
            dong.setdefault(k, 0)
        ket_qua.append(dong)
    return sorted(ket_qua, key=lambda d: (-d["thuan"], d["ma"] or ""))


def tong_quan(ky: dict) -> dict:
    p = _p(ky)
    hang = _hai_ky(repo.tong_hang, ky)
    viec = repo.viec_can_xu_ly(p, NGUONG_NHAC_CHUA_GAN_XE_GIO)
    viec["xe_thieu_nhan_su"] = repo.tong_xe(p)["thieu_nhan_su"]
    return {
        "tien": _hai_ky(repo.tong_tien, ky),
        "chuyen": _hai_ky(repo.tong_chuyen, ky),
        "hang": {"hien_tai": {"don_tao": hang["hien_tai"]["don_tao"]}, "truoc": {"don_tao": hang["truoc"]["don_tao"]}},
        "chuoi_tien": repo.chuoi_tien(p, ky["don_vi"]),
        "theo_tuyen": gop_theo_tuyen(repo.tien_theo_nhom(p)["theo_tuyen"], repo.chuyen_theo_nhom(p)["theo_tuyen"]),
        "viec_can_xu_ly": viec,
    }


def doanh_thu(ky: dict) -> dict:
    p = _p(ky)
    return {"tien": _hai_ky(repo.tong_tien, ky), "chuoi_tien": repo.chuoi_tien(p, ky["don_vi"]), **repo.tien_theo_nhom(p)}


def chuyen(ky: dict) -> dict:
    p = _p(ky)
    return {
        "chuyen": _hai_ky(repo.tong_chuyen, ky),
        "chuoi_chuyen": repo.chuoi_chuyen(p, ky["don_vi"]),
        **repo.chuyen_theo_nhom(p),
        "nhiet_thu_gio": repo.nhiet_thu_gio(p),
        "bat_thuong": repo.chuyen_bat_thuong(p),
    }


def ve(ky: dict) -> dict:
    p = _p(ky)
    return {"ve": _hai_ky(repo.tong_ve, ky), "chuoi_ve": repo.chuoi_ve(p, ky["don_vi"]), "cap_diem": repo.cap_diem_dong_nhat(p)}


def gui_hang(ky: dict) -> dict:
    p = _p(ky)
    return {
        "hang": _hai_ky(repo.tong_hang, ky),
        "tien": _hai_ky(repo.tong_tien, ky),
        "chuoi_hang": repo.chuoi_hang(p, ky["don_vi"]),
        **repo.hang_theo_nhom(p),
    }


def hoan_tien(ky: dict) -> dict:
    p = _p(ky)
    return {
        "hoan": _hai_ky(repo.tong_hoan, ky),
        "theo_ly_do": repo.hoan_theo_ly_do(p),
        "chuoi_hoan": repo.chuoi_hoan(p, ky["don_vi"]),
        "dang_cho": repo.hoan_dang_cho(p),
    }


def xe_nhan_su(ky: dict) -> dict:
    p = _p(ky)
    return {"xe": repo.tong_xe(p), "hieu_suat_xe": repo.hieu_suat_xe(p), **repo.tong_nhan_su()}


_TAB = {
    "tong-quan": tong_quan, "doanh-thu": doanh_thu, "chuyen": chuyen, "ve": ve,
    "gui-hang": gui_hang, "hoan-tien": hoan_tien, "xe-nhan-su": xe_nhan_su,
}


def thong_ke(tab: str, tu_ngay: date, den_ngay: date, so_sanh_tu: date | None = None, so_sanh_den: date | None = None,
             tuyen_id: str | None = None) -> dict:
    if tab not in _TAB:
        raise GiaTriLoi("Tab thống kê không hợp lệ")
    ky = xac_dinh_ky(tu_ngay, den_ngay, so_sanh_tu, so_sanh_den, tuyen_id)
    ket_qua = _TAB[tab](ky)
    return {"ky": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in ky.items()}, **ket_qua}
