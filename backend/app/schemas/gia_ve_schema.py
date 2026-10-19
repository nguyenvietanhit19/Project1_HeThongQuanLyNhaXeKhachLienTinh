"""Pydantic schemas cho bộ giá vé — NGHIEP_VU.md mục 3.1, UC-33, DATABASE.md mục 2.5."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GiaChangRequest(BaseModel):
    diem_di_id: UUID = Field(..., description="Khu vực điểm đi")
    diem_den_id: UUID = Field(..., description="Khu vực điểm đến")
    gia_goc: int = Field(..., gt=0, description="Giá ứng với hệ số giá = 1 (chưa nhân hệ số giá của chuyến, lấy từ lịch chạy)")


class BoGiaRequest(BaseModel):
    """Tạo bộ giá mới: giá cho ĐỦ mọi chặng của tuyến."""

    tuyen_id: UUID
    ap_dung_tu: date | None = Field(
        None, description="Ngày bắt đầu: bộ đầu tiên của tuyến — bỏ trống = ngày mai; bộ sau luôn là ngày liền sau bộ trước (bỏ trống để tự lấy)"
    )
    ap_dung_den: date = Field(..., description="Ngày kết thúc (bắt buộc)")
    danh_sach_gia: list[GiaChangRequest] = Field(..., min_length=1)
    xac_nhan_canh_bao: bool = Field(False, description="Đã xem và xác nhận các cảnh báo giá bất thường")


class SuaBoGiaRequest(BaseModel):
    ap_dung_tu: date | None = Field(None, description="Bỏ trống = giữ nguyên")
    ap_dung_den: date
    danh_sach_gia: list[GiaChangRequest] = Field(..., min_length=1)
    xac_nhan_canh_bao: bool = False


class XemTruocSuaBoGiaRequest(BaseModel):
    ap_dung_tu: date | None = None
    ap_dung_den: date
    danh_sach_gia: list[GiaChangRequest] = Field(..., min_length=1)


class GiaChangResponse(BaseModel):
    id: UUID
    diem_di_id: UUID
    ten_diem_di: str
    diem_den_id: UUID
    ten_diem_den: str
    gia_goc: int


class BoGiaResponse(BaseModel):
    id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    ap_dung_tu: date
    ap_dung_den: date
    trang_thai: str = Field(..., description="sap_ap_dung | dang_ap_dung | da_ket_thuc")
    so_chuyen_da_sinh: int = Field(0, description="Số chuyến của tuyến đã sinh trong khoảng ngày áp dụng của bộ")
    khoa: bool = Field(False, description="True = đã được dùng để sinh chuyến: không sửa giá/ngày bắt đầu, không xóa")
    la_bo_cuoi: bool = Field(False, description="Bộ cuối cùng của tuyến: chỉ bộ này đổi được ngày kết thúc / xóa được")
    ngay_chuyen_cuoi: date | None = Field(None, description="Ngày khởi hành xa nhất của chuyến đã sinh trong bộ (chỉ có khi bộ bị khóa)")
    ngay_tao: datetime
    danh_sach_gia: list[GiaChangResponse]


class BoTruocResponse(BaseModel):
    ap_dung_tu: date
    ap_dung_den: date


class ThayDoiChangResponse(BaseModel):
    ten_chang: str
    gia_cu: int | None = Field(None, description="Giá chặng này ở bộ liền trước; None nếu chưa có bộ trước")
    gia_moi: int


class XemTruocBoGiaResponse(BaseModel):
    ap_dung_tu: date
    ap_dung_den: date
    bo_truoc: BoTruocResponse | None = None
    thay_doi: list[ThayDoiChangResponse]
    canh_bao: list[str] = Field(default_factory=list)
