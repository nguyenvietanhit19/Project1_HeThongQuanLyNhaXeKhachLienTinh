"""Pydantic schemas cho Tạo tài khoản cán bộ — UC-36, NGHIEP_VU.md mục 2, mục
8.7 điểm 2, mục 8.9, UC-36.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

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
    ma: str = Field(description="Mã nhân viên tự sinh theo vai trò, VD PX0001 — không đổi sau khi tạo")
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
    ma: str | None = Field(description="Mã nhân viên; null với tài khoản tạo trực tiếp vào DB (VD script demo) chưa được cấp mã")
    email: str
    ho_ten: str
    so_dien_thoai: str
    vai_tro: str
    dang_hoat_dong: bool
    da_dat_mat_khau: bool = Field(description="true = tài khoản đã có mật khẩu (tạo mới luôn có mật khẩu ban đầu); false chỉ gặp ở dữ liệu cũ chưa có mật khẩu")
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


# ---------------------------------------------------------
# UC-37: khóa / mở khóa tài khoản (NGHIEP_VU.md UC-37; KE_HOACH_UC37 bước 1)
# ---------------------------------------------------------
class DoiTrangThaiTaiKhoanRequest(BaseModel):
    """Body của POST khóa / mở khóa. Lý do BẮT BUỘC (cả khóa lẫn mở khóa), chỉ là chữ tự do — không chọn từ danh sách."""

    ly_do: str = Field(min_length=1, max_length=500, description="Lý do khóa / mở khóa, 1–500 ký tự sau khi cắt khoảng trắng hai đầu")

    # mode="before": cắt khoảng trắng TRƯỚC khi Field kiểm độ dài, để "   " bị coi là rỗng
    # và "  abc  " tính 3 ký tự chứ không phải 7.
    @field_validator("ly_do", mode="before")
    @classmethod
    def cat_khoang_trang(cls, gia_tri):
        if isinstance(gia_tri, str):
            gia_tri = gia_tri.strip()
            if not gia_tri:
                raise ValueError("Vui lòng nhập lý do")
        return gia_tri


class XeThieuPhuXe(BaseModel):
    xe_id: UUID
    bien_so: str


class DoiTrangThaiTaiKhoanResponse(BaseModel):
    id: UUID
    dang_hoat_dong: bool
    canh_bao_xe_thieu_phu_xe: list[XeThieuPhuXe] = Field(
        default_factory=list,
        description="Chỉ có khi khóa tài khoản phụ xe làm xe nào đó thiếu phụ xe cố định; hệ thống KHÔNG tự đổi biên chế",
    )


# ---------------------------------------------------------
# Đổi văn phòng của cán bộ — nhánh kèm UC-36 (NGHIEP_VU.md; KE_HOACH_DOI_VAN_PHONG.md)
# ---------------------------------------------------------
SO_TU_TOI_DA_LY_DO_DOI_VAN_PHONG = 200
SO_KY_TU_TOI_DA_LY_DO_DOI_VAN_PHONG = 2000  # chặn kỹ thuật: tránh 1 "từ" dài vô hạn


def kiem_tra_ly_do_doi_van_phong(gia_tri):
    """Cắt khoảng trắng hai đầu, bắt buộc có chữ, tối đa 200 từ (tách theo khoảng trắng) và 2000 ký tự."""
    if isinstance(gia_tri, str):
        gia_tri = gia_tri.strip()
        if not gia_tri:
            raise ValueError("Vui lòng nhập lý do")
        if len(gia_tri.split()) > SO_TU_TOI_DA_LY_DO_DOI_VAN_PHONG:
            raise ValueError(f"Lý do tối đa {SO_TU_TOI_DA_LY_DO_DOI_VAN_PHONG} từ")
        if len(gia_tri) > SO_KY_TU_TOI_DA_LY_DO_DOI_VAN_PHONG:
            raise ValueError(f"Lý do tối đa {SO_KY_TU_TOI_DA_LY_DO_DOI_VAN_PHONG} ký tự")
    return gia_tri


class DoiVanPhongRequest(BaseModel):
    """Body của PUT đổi văn phòng. Lý do BẮT BUỘC, văn bản tự do, tối đa 200 từ."""

    van_phong_id: UUID
    ly_do: str = Field(min_length=1)

    @field_validator("ly_do", mode="before")
    @classmethod
    def kiem_tra_ly_do(cls, gia_tri):
        return kiem_tra_ly_do_doi_van_phong(gia_tri)


class DoiVanPhongResponse(BaseModel):
    id: UUID
    van_phong_cu_id: UUID | None = Field(default=None, description="null = chưa có văn phòng (gán lần đầu)")
    ten_van_phong_cu: str | None = None
    van_phong_moi_id: UUID
    ten_van_phong_moi: str
