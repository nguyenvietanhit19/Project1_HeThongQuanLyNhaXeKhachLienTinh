"""Nghiệp vụ phân công nhân viên gửi hàng vào văn phòng cố định."""

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import ho_so_can_bo_diem_repository as ho_so_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.utils.loi import GiaTriLoi


def lay_van_phong_cua_nhan_vien(nguoi_dung_id: str) -> dict:
    ho_so = ho_so_repo.lay_theo_nguoi_dung_id(nguoi_dung_id)
    if not ho_so:
        raise GiaTriLoi("Tài khoản nhân viên gửi hàng chưa được phân công văn phòng")
    return ho_so


def danh_sach_nhan_vien_gui_hang() -> list[dict]:
    return ho_so_repo.danh_sach_nhan_vien_gui_hang()


def gan_van_phong(nguoi_dung_id: str, van_phong_id: str) -> dict:
    nguoi_dung = nguoi_dung_repo.tim_theo_id(nguoi_dung_id)
    if not nguoi_dung or nguoi_dung["vai_tro"] != "nhan_vien_gui_hang":
        raise GiaTriLoi("Tài khoản cần phân công không phải nhân viên gửi hàng")

    van_phong = dia_diem_repo.tim_diem_don_tra_theo_id(van_phong_id)
    if not van_phong or van_phong["loai"] != "van_phong":
        raise GiaTriLoi("Điểm được phân công phải là văn phòng")

    ho_so_repo.gan_van_phong(nguoi_dung_id, van_phong_id)
    return ho_so_repo.lay_theo_nguoi_dung_id(nguoi_dung_id)
