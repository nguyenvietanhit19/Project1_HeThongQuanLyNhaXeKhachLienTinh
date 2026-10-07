"""Pydantic schemas cho đặt vé online (UC-05, UC-08) — NGHIEP_VU.md mục 3.4, 6.

Chỉ trả vé của chính khách đang đăng nhập; không có thông tin của khách khác.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GiuChoRequest(BaseModel):
    """Mốc khóa ghế — khách bấm "Tiếp tục" sau khi chọn điểm đón/trả. `diem_di_id`/`diem_den_id` là khu vực khách đã
    tìm ở UC-04; `diem_don_id`/`diem_tra_id` là điểm đón (văn phòng) và điểm trả cụ thể khách chọn."""

    chuyen_id: UUID
    diem_di_id: UUID
    diem_den_id: UUID
    diem_don_id: UUID
    diem_tra_id: UUID
    danh_sach_ghe: list[str] = Field(min_length=1)


class BoGheRequest(BaseModel):
    so_ghe: str


class ThanhToanRequest(BaseModel):
    """Chỉ các ghế trong `danh_sach_ghe` được thanh toán; ghế còn lại của lượt đặt bị nhả."""

    danh_sach_ghe: list[str] = Field(min_length=1)
    # thanh_toan_tai_quay · vnpay_qr (= "thanh toán ngay": đặt vé thành công, chờ khách trả VNPay trong 5 phút)
    loai_hinh: Literal["thanh_toan_tai_quay", "vnpay_qr"]


class DuongDanThanhToanRequest(BaseModel):
    # Địa chỉ trang web đang mở (location.origin) — nơi cổng thanh toán đưa khách về; phải nằm trong CORS_ORIGINS
    frontend_origin: str


class DuongDanThanhToanResponse(BaseModel):
    duong_dan_thanh_toan: str


class VeTrongDatCho(BaseModel):
    id: UUID
    so_ghe: str
    gia: int
    trang_thai: str
    loai_hinh_thanh_toan: str  # thanh_toan_ngay · thanh_toan_tai_quay


class ChuyenTrongDatCho(BaseModel):
    id: UUID
    ma: str
    gio_khoi_hanh: datetime
    gio_don_du_kien: datetime
    gio_den_du_kien: datetime
    ten_loai_xe: str
    ten_diem_don: str
    ten_diem_tra: str


class DatChoResponse(BaseModel):
    ma_dat_cho: str
    # dang_giu: ghế đang giữ (10 phút), chưa chọn cách thanh toán · cho_thanh_toan: đã chọn VNPay, chờ khách trả trong 5 phút
    # dat_thanh_cong_tai_quay: đã chốt "thanh toán tại quầy" · het_han / da_huy / da_thanh_toan: kết thúc theo vòng đời vé (mục 5)
    trang_thai: Literal["dang_giu", "cho_thanh_toan", "dat_thanh_cong_tai_quay", "het_han", "da_huy", "da_thanh_toan"]
    chuyen: ChuyenTrongDatCho
    ve: list[VeTrongDatCho]
    so_ve: int
    tong_tien: int
    han_giu_cho_den: datetime | None = None
    han_thanh_toan: datetime | None = None  # chỉ khi cho_thanh_toan: hạn khách phải trả VNPay (đã trừ phần đệm cho IPN)
    duoc_chon_thanh_toan_tai_quay: bool  # false khi khách đã vi phạm no-show đủ ngưỡng (mục 9)
    can_dat_coc: bool  # cả lượt đặt: ≥2 vé có tổng giá trị > ngưỡng (mục 3.4); giao diện tự tính lại theo ghế được tích
    nguong_dat_coc: int
    ty_le_dat_coc: float
    cho_phep_huy: bool  # còn trước mốc chốt lên xe tại điểm đón (mục 7)


class HuyDatChoResponse(BaseModel):
    ma_dat_cho: str
    so_ve_da_huy: int
