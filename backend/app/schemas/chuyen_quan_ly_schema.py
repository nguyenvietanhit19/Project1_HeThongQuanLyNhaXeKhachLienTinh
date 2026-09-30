"""Pydantic schemas cho trang "Chuyến" (xem/sửa/xóa từ góc nhìn quản lý) —
UC-18, NGHIEP_VU.md mục 3.5, DATABASE.md mục 3.3.
"""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel


class SuaGioChuyenRequest(BaseModel):
    """Chỉ đổi GIỜ — ngày của chuyến giữ nguyên (server tự lấy ngày hiện có)."""

    gio: time


class ChuyenQuanLyResponse(BaseModel):
    id: UUID
    ma: str
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    chieu: str
    gio_khoi_hanh: datetime
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    trang_thai: str
    xe_id: UUID | None = None
    bien_so_xe: str | None = None
    lich_chay_dinh_ky_id: UUID | None = None
    so_ve_dang_hoat_dong: int
