"""Pydantic schemas cho phân công điều độ viên phụ trách tuyến — DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md mục 3.2."""

from uuid import UUID

from pydantic import BaseModel, Field


class DieuDoVienTomTat(BaseModel):
    id: UUID
    ho_ten: str
    email: str


class DieuDoVienChonResponse(DieuDoVienTomTat):
    so_tuyen: int  # số tuyến đang phụ trách — giúp quản lý cân bằng việc khi phân công


class PhanCongTuyenResponse(BaseModel):
    tuyen_id: UUID
    dieu_do_vien: list[DieuDoVienTomTat]  # chỉ điều độ viên đang hoạt động


class DatPhanCongRequest(BaseModel):
    nguoi_dung_ids: list[UUID] = Field(
        default_factory=list, description="Toàn bộ điều độ viên phụ trách tuyến sau khi lưu; rỗng = bỏ hết phân công"
    )
