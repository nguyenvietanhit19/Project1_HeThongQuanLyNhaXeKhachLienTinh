"""Pydantic schemas cho Lịch chạy định kỳ — UC-18, NGHIEP_VU.md mục 3.5,
DATABASE.md mục 3.5.
"""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LichChayRequest(BaseModel):
    tuyen_id: UUID
    chieu: Literal["xuoi", "nguoc"] = Field(..., description="Tuyến chạy được cả 2 chiều nên phải chọn rõ chiều của lịch này")
    gio_khoi_hanh: time
    loai_xe_id: UUID


class SuaLichChayRequest(BaseModel):
    """Không cho đổi tuyến của 1 lịch đã có — muốn đổi tuyến thì tạo lịch mới."""

    chieu: Literal["xuoi", "nguoc"]
    gio_khoi_hanh: time
    loai_xe_id: UUID


class DoiApDungRequest(BaseModel):
    dang_ap_dung: bool


class SinhChuyenRequest(BaseModel):
    tu_ngay: date
    den_ngay: date


class SinhChuyenResponse(BaseModel):
    so_chuyen_moi_sinh: int
    so_ngay_da_co_san: int


class LichChayResponse(BaseModel):
    id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    chieu: str
    gio_khoi_hanh: time
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    dang_ap_dung: bool
    so_chuyen_da_sinh: int
    ngay_tao: datetime
