"""Pydantic schemas cho Giá vé — NGHIEP_VU.md mục 3.1, UC-33,
DATABASE.md mục 2.5.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class GiaVeRequest(BaseModel):
    tuyen_id: UUID
    diem_di_id: UUID = Field(..., description="Khu vực điểm đi")
    diem_den_id: UUID = Field(..., description="Khu vực điểm đến")
    gia_goc: int = Field(..., gt=0, description="Giá ứng với hệ số giá = 1 (chưa nhân loai_xe.he_so_gia)")
    ap_dung_tu: date | None = Field(None, description="NULL = áp dụng vô thời hạn")
    ap_dung_den: date | None = None


class SuaGiaVeRequest(BaseModel):
    gia_goc: int = Field(..., gt=0)
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None


class GiaVeResponse(BaseModel):
    id: UUID
    tuyen_id: UUID
    ten_tuyen: str | None = None
    diem_di_id: UUID
    ten_diem_di: str | None = None
    diem_den_id: UUID
    ten_diem_den: str | None = None
    gia_goc: int
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None
