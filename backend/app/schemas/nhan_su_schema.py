"""Pydantic schemas cho Hồ sơ nhân sự vận hành — UC-49, NGHIEP_VU.md mục 8.9,
DATABASE.md mục 1.4/1.6.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Chỉ chấp nhận 2 loại giấy tờ này; giá trị khác Pydantic tự báo lỗi 422.
LoaiGiayTo = Literal["bang_lai", "giay_kham_suc_khoe"]


class GiayToInput(BaseModel):
    """Dữ liệu giấy tờ client GỬI LÊN (trong tạo/sửa hồ sơ)."""

    loai: LoaiGiayTo
    so_giay_to: str | None = None
    hang: str | None = Field(default=None, description="Chỉ dùng cho bang_lai, VD D, E")
    ngay_cap: date | None = None
    ngay_het_han: date


class GiayToResponse(BaseModel):
    """Dữ liệu giấy tờ API TRẢ VỀ cho client."""

    id: UUID
    loai: LoaiGiayTo
    so_giay_to: str | None
    hang: str | None
    ngay_cap: date | None
    ngay_het_han: date
    anh_url: str | None = Field(default=None, description="URL có chữ ký, sinh lúc trả response — không lưu cố định")
    # 2 cờ do job cảnh báo đặt (true = đã nhắc rồi, không nhắc lại); gia hạn thì tự về false
    da_canh_bao_sap_het_han: bool
    da_canh_bao_het_han: bool


class TaoHoSoRequest(BaseModel):
    """Body của POST tạo hồ sơ."""

    ho_ten: str = Field(min_length=1)
    so_dien_thoai: str = Field(min_length=1)
    chuc_danh: Literal["tai_xe", "phu_xe"]
    nguoi_dung_id: UUID | None = Field(
        default=None, description="Bắt buộc nếu chuc_danh = phu_xe (tài khoản phu_xe đã tạo qua UC-36); phải để trống nếu tai_xe"
    )
    so_cccd: str | None = None
    ngay_sinh: date | None = None
    ngay_vao_lam: date | None = Field(default=None, description="Để trống thì lấy ngày hiện tại")
    giay_to: list[GiayToInput] = Field(default_factory=list)

    # Chạy sau khi các field đã hợp lệ: kiểm tra quy tắc liên quan nhiều field.
    # Phụ xe <-> bắt buộc có tài khoản; tài xế <-> không được có tài khoản.
    @model_validator(mode="after")
    def kiem_tra_chuc_danh_va_tai_khoan(self):
        if self.chuc_danh == "phu_xe" and not self.nguoi_dung_id:
            raise ValueError("Hồ sơ phụ xe bắt buộc chọn tài khoản phu_xe đã tạo")
        if self.chuc_danh == "tai_xe" and self.nguoi_dung_id:
            raise ValueError("Tài xế không có tài khoản đăng nhập, không được chọn tài khoản")
        return self


class SuaHoSoRequest(BaseModel):
    """Sửa hồ sơ có sẵn — không sửa được chuc_danh/nguoi_dung_id (không đổi
    chức danh sau khi tạo, UC-49). Giấy tờ gửi lên sẽ tạo mới nếu chưa có
    dòng cùng `loai`, hoặc cập nhật (gia hạn) nếu đã có."""

    ho_ten: str | None = Field(default=None, min_length=1)
    so_dien_thoai: str | None = None
    so_cccd: str | None = None
    ngay_sinh: date | None = None
    ngay_vao_lam: date | None = None
    giay_to: list[GiayToInput] = Field(default_factory=list)

    # Chặn request rỗng (không có gì để cập nhật).
    @model_validator(mode="after")
    def phai_co_it_nhat_1_truong(self):
        if all(
            v is None
            for v in (self.ho_ten, self.so_dien_thoai, self.so_cccd, self.ngay_sinh, self.ngay_vao_lam)
        ) and not self.giay_to:
            raise ValueError("Cần gửi ít nhất 1 trường hoặc giấy tờ để cập nhật")
        return self


class HoSoTomTatResponse(BaseModel):
    """Dùng cho danh sách — không trả CCCD/ngày sinh để nhẹ, xem chi tiết
    dùng HoSoNhanSuResponse."""

    id: UUID
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    trang_thai: str
    co_tai_khoan: bool


class HoSoNhanSuResponse(BaseModel):
    """Hồ sơ đầy đủ (có CCCD, ngày sinh, ảnh, danh sách giấy tờ)."""

    id: UUID
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    nguoi_dung_id: UUID | None
    so_cccd: str | None
    ngay_sinh: date | None
    anh_url: str | None = Field(default=None, description="URL ảnh chân dung có chữ ký, sinh lúc trả response")
    ngay_vao_lam: date
    trang_thai: str
    ngay_nghi_viec: date | None
    ly_do_nghi_viec: str | None
    giay_to: list[GiayToResponse] = Field(default_factory=list)


class AnhResponse(BaseModel):
    """Kết quả upload ảnh: URL có chữ ký để hiển thị ngay."""

    url: str


class TaiKhoanPhuXeResponse(BaseModel):
    """1 tài khoản phu_xe chưa gắn hồ sơ (phục vụ ô chọn khi tạo hồ sơ phụ xe)."""

    id: UUID
    ho_ten: str
    email: str
    so_dien_thoai: str | None = None
