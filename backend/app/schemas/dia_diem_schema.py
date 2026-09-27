"""Pydantic schemas cho Khu vực/Điểm đón trả/Tuyến — NGHIEP_VU.md mục 3.1,
UC-29/30/31 & DATABASE.md mục 2.1-2.4.
"""

from datetime import datetime
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
# 3. Nhóm tuyến — quản lý riêng, gắn 1 danh sách khu vực có thứ tự dọc
# hành trình vật lý. Tạo tuyến chỉ được chọn nhóm đã có sẵn (không tạo
# nhanh trong form tuyến nữa).
# ---------------------------------------------------------
class NhomTuyenRequest(BaseModel):
    ten: str = Field(..., min_length=1, description='VD "Hà Nội – Sapa" (gộp cả 2 chiều đi/về)')
    danh_sach_khu_vuc_id: list[UUID] = Field(
        ..., min_length=2, description="Theo đúng thứ tự dọc hành trình vật lý — server tự gán thu_tu theo vị trí trong mảng"
    )


class NhomTuyenResponse(BaseModel):
    id: UUID
    ten: str
    ngay_tao: datetime


class KhuVucTrongNhomTuyenResponse(BaseModel):
    khu_vuc_id: UUID
    ten: str
    tinh_thanh: str
    thu_tu: int


class NhomTuyenChiTietResponse(NhomTuyenResponse):
    danh_sach_khu_vuc: list[KhuVucTrongNhomTuyenResponse]


# ---------------------------------------------------------
# 4. Tuyến (UC-31)
# ---------------------------------------------------------
class DiemTrongTuyenRequest(BaseModel):
    diem_don_tra_id: UUID
    thoi_gian_du_kien_phut: int = Field(..., description="Số phút lệch so với giờ khởi hành")


class TaoTuyenRequest(BaseModel):
    ten: str = Field(..., min_length=1, description='VD "Yên Nghĩa → Sapa"')
    nhom_tuyen_id: UUID = Field(..., description="Bắt buộc chọn 1 nhóm tuyến đã có sẵn — quản lý ở mục Nhóm tuyến")
    danh_sach_diem: list[DiemTrongTuyenRequest] = Field(
        ...,
        min_length=2,
        description=(
            "Đúng theo thứ tự xe đi qua — server tự gán thu_tu theo vị trí trong mảng. "
            "Mỗi điểm phải thuộc 1 khu vực có trong nhóm tuyến đã chọn, và thứ tự khu vực "
            "phải đơn điệu tăng hoặc giảm theo đúng thứ tự đã cấu hình ở nhóm tuyến."
        ),
    )


class DiemTrongTuyenResponse(BaseModel):
    diem_don_tra_id: UUID
    ten: str
    khu_vuc_id: UUID
    ten_khu_vuc: str
    loai: Literal["van_phong", "diem_dung"]
    thu_tu: int
    thoi_gian_du_kien_phut: int


class TuyenResponse(BaseModel):
    id: UUID
    nhom_tuyen_id: UUID
    ten: str
    ngay_tao: datetime


class TuyenChiTietResponse(TuyenResponse):
    danh_sach_diem: list[DiemTrongTuyenResponse]
