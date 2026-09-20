from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TraCuuChuyenParams(BaseModel):
    diem_di_khu_vuc_id: UUID
    diem_den_khu_vuc_id: UUID
    ngay_di: date
    so_luong_ve: int = Field(default=1, ge=1, le=10)


class ChuyenXePublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chuyen_id: UUID
    tuyen_id: UUID
    ten_tuyen: str
    gio_khoi_hanh: datetime
    gio_den_du_kien: datetime
    ten_loai_xe: str
    bien_so_xe: Optional[str] = None
    so_cho: int
    so_ghe_trong: int
    gia_ve_tu: Decimal
    dang_hoan: bool = False
    trang_thai: str


class GheItemResponse(BaseModel):
    so_ghe: str
    tang: int
    hang: int
    cot: int
    trang_thai: str  # 'trong', 'giu_cho', 'da_ban'
    gia: Decimal


class SoDoGheResponse(BaseModel):
    chuyen_id: UUID
    diem_don_id: Optional[UUID] = None
    diem_tra_id: Optional[UUID] = None
    so_tang: int
    so_hang: int
    so_cot: int
    danh_sach_ghe: List[GheItemResponse]
