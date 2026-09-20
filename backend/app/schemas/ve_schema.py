from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums định nghĩa theo DATABASE.md mục 4 và NGHIEP_VU.md mục 5, 6
# ---------------------------------------------------------------------------
class TrangThaiVe(str, Enum):
    GIU_CHO = "giu_cho"
    HET_HAN = "het_han"
    DA_THANH_TOAN = "da_thanh_toan"
    DA_LEN_XE = "da_len_xe"
    DA_XUONG_XE = "da_xuong_xe"
    KHONG_DEN = "khong_den"
    DA_HUY = "da_huy"


class LoaiHinhThanhToan(str, Enum):
    THANH_TOAN_NGAY = "thanh_toan_ngay"        # Thanh toán qua VNPay trong 5 phút
    THANH_TOAN_TAI_QUAY = "thanh_toan_tai_quay"  # Trả sau tại quầy (online trả sau, UC-09, UC-10)


class PhuongThucThanhToan(str, Enum):
    TIEN_MAT = "tien_mat"
    CHUYEN_KHOAN = "chuyen_khoan"


# ---------------------------------------------------------------------------
# Base & Response Schemas
# ---------------------------------------------------------------------------
class VeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chuyen_id: UUID
    so_ghe: str
    diem_don_id: UUID
    diem_tra_id: UUID
    khach_hang_id: Optional[UUID] = None
    ten_khach_vang_lai: Optional[str] = None
    sdt_khach_vang_lai: Optional[str] = None
    gia: Decimal
    ma_dat_cho: str
    la_ve_dat_coc: bool = False
    loai_hinh_thanh_toan: LoaiHinhThanhToan
    phuong_thuc_thanh_toan: Optional[PhuongThucThanhToan] = None
    ma_giao_dich_cong_thanh_toan: Optional[str] = None
    trang_thai: TrangThaiVe
    gio_bat_dau_dem_han: Optional[datetime] = None
    han_giu_cho_den: Optional[datetime] = None
    gio_thanh_toan: Optional[datetime] = None
    gio_len_xe: Optional[datetime] = None
    gio_xuong_xe: Optional[datetime] = None
    gio_huy: Optional[datetime] = None
    ngay_tao: datetime


class ThongTinDatChoResponse(BaseModel):
    """Thông tin 1 lần đặt chỗ (nhóm theo ma_dat_cho)."""
    ma_dat_cho: str
    chuyen_id: UUID
    loai_hinh_thanh_toan: LoaiHinhThanhToan
    tong_tien: Decimal
    so_tien_can_thanh_toan_ngay: Decimal = Decimal(0)
    co_ve_dat_coc: bool = False
    han_giu_cho_den: Optional[datetime] = None
    trang_thai_chung: str
    danh_sach_ve: List[VeResponse]
    url_thanh_toan: Optional[str] = None


# ---------------------------------------------------------------------------
# Request Schemas theo từng Use Case
# ---------------------------------------------------------------------------

# UC-05: Khách đặt vé online
class DatVeRequest(BaseModel):
    chuyen_id: UUID
    danh_sach_so_ghe: List[str] = Field(..., min_length=1)
    diem_don_id: UUID
    diem_tra_id: UUID
    loai_hinh_thanh_toan: LoaiHinhThanhToan
    # Bắt buộc với khách vãng lai (không đăng nhập)
    ten_khach_vang_lai: Optional[str] = None
    sdt_khach_vang_lai: Optional[str] = None


# UC-08: Hủy giữ chỗ trước khi thanh toán
class HuyGiuChoRequest(BaseModel):
    ma_dat_cho: Optional[str] = None
    ve_id: Optional[UUID] = None


# UC-09: Bán vé trực tiếp tại quầy
class BanVeTaiQuayRequest(BaseModel):
    chuyen_id: UUID
    danh_sach_so_ghe: List[str] = Field(..., min_length=1)
    diem_don_id: UUID
    diem_tra_id: UUID
    ten_khach: str = Field(..., min_length=1)
    sdt_khach: str = Field(..., min_length=10)
    khach_hang_id: Optional[UUID] = None
    phuong_thuc_thanh_toan: PhuongThucThanhToan


# UC-10: Bán vé qua hotline
class BanVeHotlineRequest(BaseModel):
    chuyen_id: UUID
    danh_sach_so_ghe: List[str] = Field(..., min_length=1)
    diem_don_id: UUID
    diem_tra_id: UUID
    ten_khach: str = Field(..., min_length=1)
    sdt_khach: str = Field(..., min_length=10)
    khach_hang_id: Optional[UUID] = None
    tra_ngay_qua_link: bool = False  # True nếu khách đồng ý trả ngay qua link/QR gửi qua điện thoại


# UC-11: Thu tiền vé đặt trước tại quầy
class ThuTienTaiQuayRequest(BaseModel):
    ma_dat_cho: str
    phuong_thuc_thanh_toan: PhuongThucThanhToan


# UC-41 & UC-42: Hủy vé nhận hoàn tiền khi hoãn chuyến hoặc sự cố lỗi nhà xe
class HuyVeNhanHoanRequest(BaseModel):
    ve_id: UUID
    ly_do: str
    so_tai_khoan_nhan: Optional[str] = None
    ten_ngan_hang_nhan: Optional[str] = None
    ten_chu_tai_khoan_nhan: Optional[str] = None


# Dành cho phụ xe (Người 3) gọi cập nhật trạng thái
class CapNhatTrangThaiVeRequest(BaseModel):
    ve_id: UUID
    trang_thai: TrangThaiVe
