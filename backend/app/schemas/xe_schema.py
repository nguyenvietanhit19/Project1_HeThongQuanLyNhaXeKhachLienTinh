"""Pydantic schemas cho Loại xe (UC-32, DATABASE.md mục 3.1), Xe (UC-34, mục 3.2)
và Biên chế xe (UC-35, mục 1.5) — NGHIEP_VU.md mục 3.1/3.2.
"""

from decimal import Decimal
from typing import Literal
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
    ma: str
    ten: str
    he_so_gia: Decimal
    so_do_ghe: list[GheXe]


# ---------------------------------------------------------
# Xe (UC-34)
# ---------------------------------------------------------
class XeRequest(BaseModel):
    bien_so: str = Field(..., min_length=1, max_length=20)
    loai_xe_id: UUID
    diem_goc_id: UUID = Field(..., description="Phải là điểm loai = van_phong (kiểm tra ở Service)")
    tuyen_id: UUID | None = Field(None, description="Có giá trị = xe cố định đúng tuyến này (cả 2 chiều); None = xe dự phòng")
    trang_thai: Literal["hoat_dong", "bao_tri", "ngung_su_dung"] = "hoat_dong"


class XeResponse(BaseModel):
    id: UUID
    bien_so: str
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    trang_thai: str
    diem_goc_id: UUID
    ma_diem_goc: str
    ten_diem_goc: str
    tuyen_id: UUID | None = None
    ma_tuyen: str | None = None
    ten_tuyen: str | None = None
    so_tai_xe_co_dinh: int
    so_phu_xe_co_dinh: int


# ---------------------------------------------------------
# Biên chế xe (UC-35)
# ---------------------------------------------------------
class BienCheItem(BaseModel):
    id: UUID = Field(..., description="id dòng xe_nhan_su")
    nhan_su_van_hanh_id: UUID
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    loai: str
    trang_thai: str


class NhanSuKhaDung(BaseModel):
    id: UUID
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    co_tai_khoan: bool
    bien_so_xe_co_dinh: str | None = None


class ThemBienCheRequest(BaseModel):
    nhan_su_van_hanh_id: UUID
