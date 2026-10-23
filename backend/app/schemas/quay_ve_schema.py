from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BanVeRequest(BaseModel):
    kenh_ban: Literal["tai_quay", "hotline"]
    chuyen_id: UUID
    diem_di_id: UUID
    diem_den_id: UUID
    diem_don_id: UUID
    diem_tra_id: UUID
    danh_sach_ghe: list[str] = Field(min_length=1, max_length=8)
    ten_khach: str | None = Field(default=None, max_length=120)
    sdt_khach: str = Field(min_length=10, max_length=10, pattern=r"^0[35789][0-9]{8}$")
    khach_hang_id: UUID | None = None
    phuong_thuc: Literal["tien_mat", "chuyen_khoan", "thanh_toan_tai_quay"]


class ThanhToanQuayRequest(BaseModel):
    phuong_thuc: Literal["tien_mat", "chuyen_khoan"]


class HuyVeRequest(BaseModel):
    ly_do: str | None = Field(default=None, max_length=300)


class ThongKeQuery(BaseModel):
    tu_ngay: date
    den_ngay: date


class TaoLinkThanhToanRequest(BaseModel):
    frontend_origin: str


class VeQuayResponse(BaseModel):
    id: UUID
    ma_ve: str
    ma_dat_cho: str
    so_ghe: str
    gia: int
    trang_thai: str
    phuong_thuc_thanh_toan: str | None = None
    ten_khach: str
    sdt_khach: str
    ma_chuyen: str
    ten_tuyen: str
    gio_khoi_hanh: datetime
    ten_diem_don: str
    ten_diem_tra: str
    gio_don_du_kien: datetime
    gio_den_du_kien: datetime
    ten_loai_xe: str
    bien_so: str | None = None
    trang_thai_chuyen: str
    dang_hoan: bool
    loai_su_co: str | None = None
    co_the_in: bool
    co_the_thanh_toan: bool
    co_the_huy_giu_cho: bool
    co_the_huy_hoan_tien: bool


class HoanTienQuayResponse(BaseModel):
    id: UUID
    ve_id: UUID
    ma_ve: str
    ma_dat_cho: str
    so_tien: int
    ly_do: str
    trang_thai: str
    thoi_gian_xac_dinh: datetime
    thoi_gian_hoan_xong: datetime | None = None
