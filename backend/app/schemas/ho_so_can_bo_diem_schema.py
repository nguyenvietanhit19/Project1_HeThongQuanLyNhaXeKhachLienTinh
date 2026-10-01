from uuid import UUID

from pydantic import BaseModel


class GanVanPhongRequest(BaseModel):
    van_phong_id: UUID


class NhanVienGuiHangPhanCongResponse(BaseModel):
    nguoi_dung_id: UUID
    email: str
    ho_ten: str
    van_phong_id: UUID | None = None
    ten_van_phong: str | None = None
