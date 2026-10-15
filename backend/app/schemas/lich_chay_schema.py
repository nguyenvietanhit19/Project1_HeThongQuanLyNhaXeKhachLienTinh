"""Pydantic schemas cho Lịch chạy định kỳ theo cặp — UC-18, NGHIEP_VU.md mục 3.5,
DATABASE.md mục 3.5.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


class TaoCapLichChayRequest(BaseModel):
    """Một cặp luôn cùng 1 tuyến và 1 loại xe; mỗi chiều có giờ khởi hành riêng."""

    tuyen_id: UUID
    loai_xe_id: UUID
    gio_xuoi: time
    gio_nguoc: time


class SuaLichChayRequest(BaseModel):
    """Sửa giờ 1 chiều của cặp; loại xe đổi thì đổi cho cả cặp. Không đổi tuyến/chiều."""

    gio_khoi_hanh: time
    loai_xe_id: UUID


class DoiApDungRequest(BaseModel):
    dang_ap_dung: bool


class XemTruocCapResponse(BaseModel):
    tong_phut: int
    gio_den: time
    ngay_den_lech: int
    ngay_lech: int


class SinhChuyenRequest(BaseModel):
    cap_ids: list[UUID] = Field(..., min_length=1)
    tu_ngay: date
    den_ngay: date


class SinhChuyenResponse(BaseModel):
    so_chuyen_di_moi_sinh: int
    so_chuyen_ve_moi_sinh: int
    so_chuyen_di_da_co_san: int
    so_chuyen_ve_da_co_san: int
    so_chu_ky_bo_qua_do_qua_gio: int


class LichChayResponse(BaseModel):
    id: UUID
    chieu: str
    gio_khoi_hanh: time
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    dang_ap_dung: bool
    so_chuyen_da_sinh: int
    ngay_tao: datetime


class CapLichChayResponse(BaseModel):
    cap_id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    tong_phut: int | None
    ngay_lech: int
    gio_den_chieu_di: time
    ngay_den_lech: int
    dang_ap_dung: bool
    so_chuyen_da_sinh: int
    cac_cap_thieu_gia: list[str] = []
    xuoi: LichChayResponse
    nguoc: LichChayResponse
