"""Pydantic schemas cho Lịch chạy định kỳ theo cặp — UC-18, NGHIEP_VU.md mục 3.5,
DATABASE.md mục 3.5.
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TaoCapLichChayRequest(BaseModel):
    """Một cặp luôn cùng 1 tuyến và 1 loại xe; mỗi chiều có giờ khởi hành riêng."""

    tuyen_id: UUID
    loai_xe_id: UUID
    gio_xuoi: time
    gio_nguoc: time
    he_so_gia: Decimal = Field(Decimal("1.0"), gt=0, le=Decimal("99.99"), decimal_places=2, description="Nhân với giá gốc của bộ giá; chốt vào từng chuyến lúc sinh chuyến")


class SuaLichChayRequest(BaseModel):
    """Sửa giờ 1 chiều của cặp; loại xe đổi thì đổi cho cả cặp. Không đổi tuyến/chiều."""

    gio_khoi_hanh: time
    loai_xe_id: UUID


class DoiHeSoGiaRequest(BaseModel):
    he_so_gia: Decimal = Field(..., gt=0, le=Decimal("99.99"), decimal_places=2)


class DoiApDungRequest(BaseModel):
    dang_ap_dung: bool


class XemTruocCapResponse(BaseModel):
    tong_phut: int
    gio_den: time
    ngay_den_lech: int
    ngay_lech: int


class SinhChuyenRequest(BaseModel):
    cap_ids: list[UUID] = Field(..., min_length=1)
    tu_ngay: date
    den_ngay: date


class SinhChuyenResponse(BaseModel):
    so_chuyen_di_moi_sinh: int
    so_chuyen_ve_moi_sinh: int
    so_chuyen_di_da_co_san: int
    so_chuyen_ve_da_co_san: int
    so_chu_ky_bo_qua_do_qua_gio: int


class LichChayResponse(BaseModel):
    id: UUID
    chieu: str
    gio_khoi_hanh: time
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    he_so_gia: Decimal
    dang_ap_dung: bool
    so_chuyen_da_sinh: int
    ngay_tao: datetime


class CapLichChayResponse(BaseModel):
    cap_id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    tong_phut: int | None
    ngay_lech: int
    he_so_gia: Decimal
    gio_den_chieu_di: time
    ngay_den_lech: int
    dang_ap_dung: bool
    so_chuyen_da_sinh: int
    sinh_chuyen_tu_ngay: date | None = None  # ngày sớm nhất sinh được chuyến đi (bộ giá đầu tiên của tuyến bắt đầu); None = tuyến chưa có bộ giá
    sinh_chuyen_den_ngay: date | None = None  # ngày muộn nhất sinh được chuyến đi = ngày cuối bộ giá mới nhất trừ độ lệch chuyến về
    xuoi: LichChayResponse
    nguoc: LichChayResponse
