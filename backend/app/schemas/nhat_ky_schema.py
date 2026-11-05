"""Pydantic schemas cho UC-52 — xem nhật ký thao tác (NGHIEP_VU.md UC-52)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NhatKyItemResponse(BaseModel):
    id: UUID
    nguon: str = Field(description="Bảng nguồn: quan_ly_nhan_su (nhat_ky_quan_ly_nhan_su) hoặc admin (nhat_ky_admin)")
    nguoi_id: UUID
    ten_nguoi: str
    ma_nguoi: str | None = None
    vai_tro_nguoi: str
    hanh_dong: str
    nhan_hanh_dong: str = Field(description="Nhãn tiếng Việt; hành động lạ (nhóm khác ghi) hiện nguyên giá trị thô")
    doi_tuong_loai: str
    doi_tuong_id: UUID
    doi_tuong_hien_thi: str = Field(description="'Họ tên (mã)' nếu tra được; không thì 'loại + 8 ký tự đầu của id'")
    ghi_chu: str | None = None
    thoi_gian: datetime


class NhatKyTrangResponse(BaseModel):
    items: list[NhatKyItemResponse]
    tong: int
    trang: int
    so_dong: int
    so_trang: int


class LuaChonLoc(BaseModel):
    gia_tri: str
    nhan: str


class NguoiThucHienResponse(BaseModel):
    id: UUID
    ho_ten: str
    ma: str | None = None
    vai_tro: str


class TuyChonLocResponse(BaseModel):
    hanh_dong: list[LuaChonLoc]
    doi_tuong_loai: list[LuaChonLoc]
    nguoi_thuc_hien: list[NguoiThucHienResponse] = Field(
        default_factory=list, description="Chỉ quan_ly được lọc theo người; quan_ly_nhan_su nhận danh sách rỗng"
    )
