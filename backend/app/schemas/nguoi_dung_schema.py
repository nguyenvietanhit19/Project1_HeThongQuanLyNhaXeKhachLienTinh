from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


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
    """Sửa hồ sơ của chính mình — gửi trường nào sửa trường đó (họ tên và/hoặc số điện thoại)."""

    ho_ten: str | None = Field(default=None, min_length=1)
    so_dien_thoai: str | None = None

    @model_validator(mode="after")
    def phai_co_it_nhat_1_truong(self):
        if self.ho_ten is None and self.so_dien_thoai is None:
            raise ValueError("Cần gửi họ tên hoặc số điện thoại để cập nhật")
        return self


class NguoiDungResponse(BaseModel):
    id: str
    email: str
    ho_ten: str
    so_dien_thoai: str
    vai_tro: str
    dang_hoat_dong: bool
    ngay_tao: datetime
