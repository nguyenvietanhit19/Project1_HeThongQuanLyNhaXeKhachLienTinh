"""Loại xe — UC-32, NGHIEP_VU.md mục 3.1. Đúng theo ARCHITECTURE.md mục 2:
Service quyết định quy tắc nghiệp vụ, Repository chỉ đọc/ghi SQL thuần.
"""

import psycopg2.errors

from app.repositories import xe_repository as repo
from app.utils.loi import GiaTriLoi


def _kiem_tra_so_do_ghe(so_do_ghe: list[dict]) -> None:
    ma_ghe_list = [ghe["ma_ghe"] for ghe in so_do_ghe]
    if len(set(ma_ghe_list)) != len(ma_ghe_list):
        raise GiaTriLoi("Sơ đồ ghế có mã ghế bị trùng lặp")


def tao_loai_xe(ten: str, he_so_gia, so_do_ghe: list[dict]) -> dict:
    _kiem_tra_so_do_ghe(so_do_ghe)
    try:
        return repo.tao_loai_xe(ten, he_so_gia, so_do_ghe)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại loại xe tên "{ten}"')


def sua_loai_xe(loai_xe_id: str, ten: str, he_so_gia, so_do_ghe: list[dict]) -> None:
    if not repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Không tìm thấy loại xe")
    _kiem_tra_so_do_ghe(so_do_ghe)
    try:
        repo.sua_loai_xe(loai_xe_id, ten, he_so_gia, so_do_ghe)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại loại xe tên "{ten}"')


def danh_sach_loai_xe() -> list[dict]:
    return repo.danh_sach_loai_xe()


def xoa_loai_xe(loai_xe_id: str) -> None:
    if not repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Không tìm thấy loại xe")
    try:
        repo.xoa_loai_xe(loai_xe_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: loại xe này đang được gán cho ít nhất 1 xe")
