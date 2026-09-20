"""Pydantic schemas cho Khu vực/Điểm đón trả/Tuyến — NGHIEP_VU.md mục 3.1,
UC-29/30/31 & DATABASE.md mục 2.1-2.4.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.tinh_thanh import DANH_SACH_TINH_THANH


# ---------------------------------------------------------
# 1. Khu vực (UC-29)
# ---------------------------------------------------------
class KhuVucRequest(BaseModel):
    ten: str = Field(..., min_length=1)
    tinh_thanh: Literal[tuple(DANH_SACH_TINH_THANH)] = Field(
        ..., description="Bắt buộc đúng 1 trong 34 tỉnh/thành sau sáp nhập — không nhận giá trị tự do"
    )


class KhuVucResponse(BaseModel):
    id: UUID
    ten: str
    tinh_thanh: str


# ---------------------------------------------------------
# 2. Điểm đón/trả (UC-30)
# ---------------------------------------------------------
class DiemDonTraRequest(BaseModel):
    khu_vuc_id: UUID
    ten: str = Field(..., min_length=1)
    dia_chi: str = Field(..., min_length=1)
    loai: Literal["van_phong", "diem_dung"]


class DiemDonTraResponse(BaseModel):
    id: UUID
    khu_vuc_id: UUID
    ten: str
    dia_chi: str
    loai: Literal["van_phong", "diem_dung"]


# ---------------------------------------------------------
# 3. Tuyến (UC-31)
# ---------------------------------------------------------
class NhomTuyenResponse(BaseModel):
    id: UUID
    ten: str


class DiemTrongTuyenRequest(BaseModel):
    diem_don_tra_id: UUID
    thoi_gian_du_kien_phut: int = Field(..., description="Số phút lệch so với giờ khởi hành")


class TaoTuyenRequest(BaseModel):
    ten: str = Field(..., min_length=1, description='VD "Yên Nghĩa → Sapa"')
    nhom_tuyen_id: UUID | None = Field(None, description="Chọn nhóm tuyến có sẵn")
    ten_nhom_tuyen_moi: str | None = Field(None, description="Tạo nhóm tuyến mới nếu chưa chọn nhom_tuyen_id")
    danh_sach_diem: list[DiemTrongTuyenRequest] = Field(
        ..., min_length=2, description="Đúng theo thứ tự xe đi qua — server tự gán thu_tu theo vị trí trong mảng"
    )


class DiemTrongTuyenResponse(BaseModel):
    diem_don_tra_id: UUID
    ten: str
    khu_vuc_id: UUID
    loai: Literal["van_phong", "diem_dung"]
    thu_tu: int
    thoi_gian_du_kien_phut: int


class TuyenResponse(BaseModel):
    id: UUID
    nhom_tuyen_id: UUID
    ten: str


class TuyenChiTietResponse(TuyenResponse):
    danh_sach_diem: list[DiemTrongTuyenResponse]
