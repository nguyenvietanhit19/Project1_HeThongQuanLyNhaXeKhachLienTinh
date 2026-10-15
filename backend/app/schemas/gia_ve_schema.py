"""Pydantic schemas cho Giá vé — NGHIEP_VU.md mục 3.1, UC-33,
DATABASE.md mục 2.5.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class GiaVeRequest(BaseModel):
    tuyen_id: UUID
    diem_di_id: UUID = Field(..., description="Khu vực điểm đi")
    diem_den_id: UUID = Field(..., description="Khu vực điểm đến")
    gia_goc: int = Field(..., gt=0, description="Giá ứng với hệ số giá = 1 (chưa nhân loai_xe.he_so_gia)")
    ap_dung_tu: date | None = Field(None, description="Ngày bắt đầu áp dụng; bỏ trống = ngày mai. Không được ở quá khứ")
    ap_dung_den: date | None = Field(None, description="Ngày kết thúc; bỏ trống = vô thời hạn")
    xac_nhan_canh_bao: bool = Field(False, description="Đã xem và xác nhận các cảnh báo giá bất thường")


class SuaGiaVeRequest(BaseModel):
    gia_goc: int = Field(..., gt=0)
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None
    xac_nhan_canh_bao: bool = False


class XemTruocSuaGiaVeRequest(BaseModel):
    gia_goc: int = Field(..., gt=0)
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None


class GiaCuResponse(BaseModel):
    gia_goc: int
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None
    se_ket_thuc_vao: date | None = Field(None, description="Ngày giá cũ sẽ bị đóng khi lưu giá mới (None = giữ nguyên)")


class XemTruocGiaVeResponse(BaseModel):
    gia_goc: int
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None
    gia_cu: GiaCuResponse | None = None
    canh_bao: list[str] = []


class GiaVeResponse(BaseModel):
    id: UUID
    tuyen_id: UUID
    ma_tuyen: str | None = None
    ten_tuyen: str | None = None
    diem_di_id: UUID
    ma_diem_di: str | None = None
    ten_diem_di: str | None = None
    diem_den_id: UUID
    ma_diem_den: str | None = None
    ten_diem_den: str | None = None
    gia_goc: int
    ap_dung_tu: date | None = None
    ap_dung_den: date | None = None
    trang_thai: str | None = Field(None, description="sap_ap_dung | dang_ap_dung | da_ket_thuc")
    so_chuyen_da_sinh: int = Field(0, description="Số chuyến của tuyến đã sinh trong khoảng ngày áp dụng của dòng giá này")
    khoa_so_tien: bool = Field(False, description="True = giá đã được dùng để sinh chuyến: không sửa số tiền/xóa, chỉ đóng")
