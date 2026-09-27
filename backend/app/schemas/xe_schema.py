"""Pydantic schemas cho Loại xe — NGHIEP_VU.md mục 3.1, UC-32,
DATABASE.md mục 3.1.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class GheXe(BaseModel):
    ma_ghe: str = Field(..., min_length=1, description='VD "A1-1" (dãy A, ghế 1, tầng 1)')
    tang: int = Field(..., ge=1, le=2)
    x: float = Field(..., ge=0, description="Vị trí ngang trên sơ đồ (px) — đặt tự do, không theo lưới cố định")
    y: float = Field(..., ge=0, description="Vị trí dọc trên sơ đồ (px), 0 = đầu xe")


class LoaiXeRequest(BaseModel):
    ten: str = Field(..., min_length=1)
    he_so_gia: Decimal = Field(..., gt=0, description="Hệ số nhân với gia_ve.gia_goc để ra giá bán thực tế")
    so_do_ghe: list[GheXe] = Field(..., min_length=1, description="Sơ đồ ghế thật — dùng chung cho mọi xe cùng loại này")


class LoaiXeResponse(BaseModel):
    id: UUID
    ten: str
    he_so_gia: Decimal
    so_do_ghe: list[GheXe]
