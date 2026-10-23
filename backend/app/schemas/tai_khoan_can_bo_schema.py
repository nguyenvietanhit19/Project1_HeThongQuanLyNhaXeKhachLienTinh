"""Pydantic schemas cho Tạo tài khoản cán bộ — UC-36, NGHIEP_VU.md mục 2, mục
8.7 điểm 2, mục 8.9, UC-36.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

# Vai trò cán bộ có thể được tạo qua UC-36 (khách hàng tự đăng ký, không tạo ở đây).
VaiTroCanBo = Literal[
    "phu_xe",
    "nhan_vien_quay_ve",
    "nhan_vien_gui_hang",
    "dieu_do_vien",
    "ke_toan",
    "quan_ly",
    "quan_ly_nhan_su",
]

# Chỉ 2 vai trò này phải gắn văn phòng (NGHIEP_VU.md mục 2). Điều độ viên đã
# chuyển sang phụ trách theo tuyến, không gắn văn phòng nữa.
VAI_TRO_CAN_VAN_PHONG = ("nhan_vien_quay_ve", "nhan_vien_gui_hang")


class TaoTaiKhoanCanBoRequest(BaseModel):
    """Body của POST tạo tài khoản cán bộ."""

    email: EmailStr
    ho_ten: str = Field(min_length=1)
    so_dien_thoai: str = Field(min_length=1)
    vai_tro: VaiTroCanBo
    van_phong_id: UUID | None = Field(
        default=None, description="Bắt buộc với nhan_vien_quay_ve / nhan_vien_gui_hang; các vai trò khác phải để trống"
    )

    @model_validator(mode="after")
    def kiem_tra_van_phong(self):
        # ho_ten chỉ toàn khoảng trắng thì Field(min_length=1) không bắt được
        if not self.ho_ten.strip():
            raise ValueError("Họ tên không được để trống")
        if self.vai_tro in VAI_TRO_CAN_VAN_PHONG and not self.van_phong_id:
            raise ValueError("Vai trò này bắt buộc chọn văn phòng phụ trách")
        if self.vai_tro not in VAI_TRO_CAN_VAN_PHONG and self.van_phong_id:
            raise ValueError("Vai trò này không gắn văn phòng")
        return self


class TaoTaiKhoanCanBoResponse(BaseModel):
    id: UUID
    email: str
    ho_ten: str
    vai_tro: str
    van_phong_id: UUID | None
    mat_khau_ban_dau: str = Field(
        description="Mật khẩu ban đầu (mặc định chung cho cán bộ mới, DB chỉ lưu bản băm) — người tạo báo cho cán bộ, cán bộ đổi ngay sau khi đăng nhập"
    )


class TaiKhoanCanBoResponse(BaseModel):
    """Một dòng trong danh sách tài khoản cán bộ."""

    id: UUID
    email: str
    ho_ten: str
    so_dien_thoai: str
    vai_tro: str
    dang_hoat_dong: bool
    da_dat_mat_khau: bool = Field(description="false = vừa được mời, chưa tự đặt mật khẩu lần đầu")
    van_phong_id: UUID | None
    ten_van_phong: str | None
    ngay_tao: datetime


class VanPhongResponse(BaseModel):
    """Văn phòng cho ô chọn (diem_don_tra có loai = van_phong)."""

    id: UUID
    ten: str
    dia_chi: str | None


class VaiTroDuocTaoResponse(BaseModel):
    """Các vai trò người đang đăng nhập được tạo — giao diện dùng để dựng ô chọn vai trò."""

    vai_tro: list[str]
    vai_tro_can_van_phong: list[str]
