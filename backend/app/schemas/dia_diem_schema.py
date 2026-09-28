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
# 3. Tuyến (UC-31) — không còn khái niệm "nhóm tuyến": 1 tuyến tự thân đại
# diện cả 1 hành trình vật lý, chạy được CẢ 2 CHIỀU. Danh sách điểm dừng
# nhập theo đúng "chiều xuôi" — chiều ngược suy ra bằng cách đọc lại danh
# sách này theo thu_tu giảm dần, không nhập riêng (NGHIEP_VU.md mục 3.1).
# ---------------------------------------------------------
class DiemTrongTuyenRequest(BaseModel):
    diem_don_tra_id: UUID
    thoi_gian_du_kien_phut: int = Field(..., description="Số phút lệch so với giờ khởi hành, tính theo chiều xuôi")


class TaoTuyenRequest(BaseModel):
    ten: str = Field(..., min_length=1, description='VD "Hà Nội – Sapa" (đặt theo hành trình, không theo 1 chiều cụ thể)')
    danh_sach_diem: list[DiemTrongTuyenRequest] = Field(
        ...,
        min_length=2,
        description=(
            "Đúng theo thứ tự xe đi qua ở CHIỀU XUÔI — server tự gán thu_tu theo vị trí trong mảng. "
            "Điểm đầu và điểm cuối bắt buộc là văn phòng."
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
    ten: str
    ngay_tao: datetime


class TuyenChiTietResponse(TuyenResponse):
    danh_sach_diem: list[DiemTrongTuyenResponse]
