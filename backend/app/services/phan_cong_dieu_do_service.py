"""Phân công điều độ viên phụ trách tuyến — DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md mục 3.2, NGHIEP_VU.md mục 2.

Quản lý chọn điều độ viên cho từng tuyến ở trang Tuyến (quan hệ nhiều–nhiều: 1 tuyến nhiều điều độ viên để chia ca, 1 điều độ viên
nhiều tuyến). Tuyến chưa có ai phụ trách không bị chặn gì — giao diện chỉ hiện nhãn cảnh báo, quản lý tạm xử lý thay.
"""

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import phan_cong_dieu_do_repository as repo
from app.utils.loi import GiaTriLoi, KhongTimThay


def danh_sach_dieu_do_vien() -> list[dict]:
    return repo.danh_sach_dieu_do_vien_dang_hoat_dong()


def _gom_theo_tuyen(cac_dong: list[dict]) -> dict[str, list[dict]]:
    theo_tuyen: dict[str, list[dict]] = {}
    for d in cac_dong:
        theo_tuyen.setdefault(str(d["tuyen_id"]), []).append({"id": d["nguoi_dung_id"], "ho_ten": d["ho_ten"], "email": d["email"]})
    return theo_tuyen


def danh_sach_phan_cong() -> list[dict]:
    """Mỗi tuyến ĐÃ có điều độ viên phụ trách → 1 phần tử; tuyến chưa có ai thì không xuất hiện (giao diện coi là 'chưa có')."""
    return [{"tuyen_id": tuyen_id, "dieu_do_vien": ds} for tuyen_id, ds in _gom_theo_tuyen(repo.danh_sach_phan_cong()).items()]


def dat_phan_cong(tuyen_id: str, nguoi_dung_ids: list[str]) -> dict:
    """Thay toàn bộ phân công của tuyến. Mọi id phải là điều độ viên đang hoạt động; trùng id được gộp."""
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise KhongTimThay("Không tìm thấy tuyến")
    ids = list(dict.fromkeys(str(i) for i in nguoi_dung_ids))
    if repo.dem_dieu_do_vien_hop_le(ids) != len(ids):
        raise GiaTriLoi("Chỉ phân công được tài khoản điều độ viên đang hoạt động")
    repo.dat_phan_cong_tuyen(tuyen_id, ids)
    return {"tuyen_id": tuyen_id, "dieu_do_vien": _gom_theo_tuyen(repo.danh_sach_phan_cong()).get(str(tuyen_id), [])}
