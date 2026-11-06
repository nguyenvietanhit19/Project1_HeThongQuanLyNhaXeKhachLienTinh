"""Pydantic schemas cho Hồ sơ nhân sự vận hành — UC-49, NGHIEP_VU.md mục 8.9,
DATABASE.md mục 1.4/1.6.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

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
    # Không còn nguoi_dung_id: hồ sơ tạo TRƯỚC, tài khoản phụ xe (nếu cần) tạo SAU ở UC-36 và tự lấy họ tên / số điện thoại từ hồ sơ.
    so_cccd: str | None = None
    ngay_sinh: date | None = None
    ngay_vao_lam: date | None = Field(default=None, description="Để trống thì lấy ngày hiện tại")
    giay_to: list[GiayToInput] = Field(default_factory=list)


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
    ma: str | None = Field(default=None, description="Mã nhân viên: tài xế TX..., phụ xe lấy mã của tài khoản (PX...); null nếu chưa được cấp")
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    trang_thai: str
    co_tai_khoan: bool


class HoSoNhanSuResponse(BaseModel):
    """Hồ sơ đầy đủ (có CCCD, ngày sinh, ảnh, danh sách giấy tờ)."""

    id: UUID
    ma: str | None = Field(default=None, description="Mã nhân viên: tài xế TX..., phụ xe lấy mã của tài khoản (PX...); null nếu chưa được cấp")
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


class HoSoPhuXeChuaCoTaiKhoanResponse(BaseModel):
    """1 hồ sơ phụ xe đang làm mà chưa có tài khoản (phục vụ ô chọn khi tạo tài khoản phụ xe, UC-36)."""

    id: UUID
    ho_ten: str
    so_dien_thoai: str


# ---------------------------------------------------------
# UC-51: cho nghỉ việc (NGHIEP_VU.md UC-51; KE_HOACH_UC51_CHO_NGHI_VIEC.md)
# ---------------------------------------------------------
class ChoNghiViecRequest(BaseModel):
    """Body của POST cho nghỉ việc. Ngày nghỉ bỏ trống = hôm nay (giờ VN); lý do bắt buộc, 1-500 ký tự sau khi cắt khoảng trắng."""

    ngay_nghi: date | None = None
    ly_do: str = Field(min_length=1, max_length=500)

    @field_validator("ly_do", mode="before")
    @classmethod
    def cat_khoang_trang(cls, gia_tri):
        if isinstance(gia_tri, str):
            gia_tri = gia_tri.strip()
            if not gia_tri:
                raise ValueError("Vui lòng nhập lý do")
        return gia_tri


class BienCheNghiViecResponse(BaseModel):
    xe_id: UUID
    bien_so: str
    loai: str
    trang_thai: str


class XeThieuNguoiResponse(BaseModel):
    xe_id: UUID
    bien_so: str
    thieu_tai_xe: bool
    thieu_phu_xe: bool
    so_tai_xe_con_lai: int
    so_phu_xe_con_lai: int


class XeDangChayResponse(BaseModel):
    xe_id: UUID
    bien_so: str


class XemTruocNghiViecResponse(BaseModel):
    """Kết quả xem trước (không ghi gì). co_the_nghi = false khi xe của người này đang có chuyến chạy / gặp sự cố."""

    id: UUID
    ma: str | None = None
    ho_ten: str
    chuc_danh: str
    se_khoa_tai_khoan: bool
    bien_che: list[BienCheNghiViecResponse]
    xe_thieu_nguoi: list[XeThieuNguoiResponse]
    xe_dang_chay: list[XeDangChayResponse]
    co_the_nghi: bool


class ChoNghiViecResponse(BaseModel):
    id: UUID
    trang_thai: str
    ngay_nghi_viec: date
    da_khoa_tai_khoan: bool
    xe_thieu_nguoi: list[XeThieuNguoiResponse] = Field(
        default_factory=list,
        description="Xe sẽ thiếu người sau khi nghỉ; hệ thống KHÔNG tự gỡ biên chế, đã báo quan_ly + điều độ viên",
    )
