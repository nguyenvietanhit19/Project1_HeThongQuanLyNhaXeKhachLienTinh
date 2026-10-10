"""Pydantic schemas cho tra cứu chuyến công khai (UC-04) — NGHIEP_VU.md mục 3.4, 8.1.

Mọi response ở đây công khai (không cần đăng nhập) nên tuyệt đối không có thông tin cá nhân của
khách đang giữ ghế — chỉ có trạng thái ghế "trống"/"có người" (ARCHITECTURE.md mục 9).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class KhuVucCongKhai(BaseModel):
    id: UUID
    ma: str
    ten: str
    tinh_thanh: str
    co_van_phong: bool


class ChuyenTimThay(BaseModel):
    id: UUID
    ma: str
    chieu: Literal["xuoi", "nguoc"]
    gio_khoi_hanh: datetime
    gio_don_du_kien: datetime
    gio_den_du_kien: datetime
    diem_don_id: UUID
    ten_diem_don: str
    diem_tra_id: UUID
    ten_diem_tra: str
    ma_loai_xe: str
    ten_loai_xe: str
    gia: int
    so_ghe_trong: int
    tong_ghe: int
    bien_so: str | None = None
    dang_hoan: bool


class GheTrongSoDo(BaseModel):
    ma_ghe: str
    tang: int
    x: float
    y: float
    trang_thai: Literal["trong", "da_co_nguoi"]


class DiemTrenChuyen(BaseModel):
    diem_id: UUID
    ten: str
    loai: Literal["van_phong", "diem_dung"]
    gio_du_kien: datetime


class ChuyenChiTiet(ChuyenTimThay):
    so_tang: int
    so_do_ghe: list[GheTrongSoDo]
    diem_don_co_the_chon: list[DiemTrenChuyen]
    diem_tra_co_the_chon: list[DiemTrenChuyen]
