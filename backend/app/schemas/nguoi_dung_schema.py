from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class DangKyRequest(BaseModel):
    email: EmailStr
    mat_khau: str = Field(min_length=6)
    ho_ten: str = Field(min_length=1)
    so_dien_thoai: str = Field(min_length=1)


class XacNhanDangKyRequest(BaseModel):
    email: EmailStr
    ma_xac_nhan: str


class DangNhapRequest(BaseModel):
    email: EmailStr
    mat_khau: str


class DangNhapResponse(BaseModel):
    token: str
    ho_ten: str
    vai_tro: str


class QuenMatKhauRequest(BaseModel):
    email: EmailStr


class DatLaiMatKhauRequest(BaseModel):
    email: EmailStr
    ma_xac_nhan: str
    mat_khau_moi: str = Field(min_length=6)


class DoiMatKhauRequest(BaseModel):
    mat_khau_cu: str
    mat_khau_moi: str = Field(min_length=6)


class SuaHoSoRequest(BaseModel):
    ho_ten: str = Field(min_length=1)


class NguoiDungResponse(BaseModel):
    id: str
    email: str
    ho_ten: str
    so_dien_thoai: str
    vai_tro: str
    dang_hoat_dong: bool
    ngay_tao: datetime
