"""Pydantic schemas cho Loại xe — NGHIEP_VU.md mục 3.1, UC-32,
DATABASE.md mục 3.1.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class GheXe(BaseModel):
    ma_ghe: str = Field(..., min_length=1, description='VD "A1", hoặc "2-A1" nếu xe 2 tầng')
    tang: int = Field(..., ge=1, le=2)
    hang: int = Field(..., ge=1, description="Số thứ tự hàng — dùng để vẽ lưới ghế")
    cot: int = Field(..., ge=1, description="Số thứ tự cột trong hàng — dùng để vẽ lưới ghế")


class LoaiXeRequest(BaseModel):
    ten: str = Field(..., min_length=1)
    he_so_gia: Decimal = Field(..., gt=0, description="Hệ số nhân với gia_ve.gia_goc để ra giá bán thực tế")
    so_do_ghe: list[GheXe] = Field(..., min_length=1, description="Sơ đồ ghế thật — dùng chung cho mọi xe cùng loại này")


class LoaiXeResponse(BaseModel):
    id: UUID
    ten: str
    he_so_gia: Decimal
    so_do_ghe: list[GheXe]
