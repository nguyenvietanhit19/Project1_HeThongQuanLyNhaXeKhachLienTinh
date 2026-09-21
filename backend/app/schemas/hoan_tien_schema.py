"""Pydantic schemas cho Kế toán & Hoàn tiền — NGHIEP_VU.md mục 7 & DATABASE.md mục 4.1.

Định nghĩa hình dạng dữ liệu Request và Response cho phân hệ Kế toán xử lý
hoàn tiền (thủ công & tự động).
hoàn tiền (thủ công & tự động) và báo cáo tài chính doanh thu (UC-39).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# 1. Request Kế toán xác nhận đã chuyển khoản hoàn tiền (UC-22)
# 1. Request Tạo bản ghi hoàn tiền
# ---------------------------------------------------------
class TaoHoanTienRequest(BaseModel):
    ve_id: UUID = Field(..., description="ID của vé cần hoàn tiền")
    ly_do: Literal[
        "bat_kha_khang_khong_hoan_thanh",
        "loi_nha_xe_giua_duong",
        "hoan_truoc_gio_chay",
        "tu_dong_hoan_qua_3_tieng",
    ] = Field(..., description="Lý do hoàn tiền theo quy định tại NGHIEP_VU.md")
    so_tien: int | None = Field(None, gt=0, description="Số tiền hoàn (mặc định lấy 100% giá vé nếu bỏ trống)")


# ---------------------------------------------------------
# 2. Request Kế toán xác nhận đã chuyển khoản hoàn tiền (UC-22)
# ---------------------------------------------------------
class XacNhanChuyenKhoanRequest(BaseModel):
    so_tai_khoan_nhan: str = Field(..., min_length=4, max_length=30, description="Số tài khoản ngân hàng của khách")
    ten_ngan_hang_nhan: str = Field(..., min_length=2, description="Tên ngân hàng (Vietcombank, MB, Techcombank...)")
    ten_chu_tai_khoan_nhan: str = Field(..., min_length=2, description="Tên chủ tài khoản nhận tiền")


# ---------------------------------------------------------
# 2. Response Chi tiết bản ghi hoàn tiền
# 3. Response Dòng chờ xử lý hoàn tiền cho Kế toán
# ---------------------------------------------------------
class HoanTienChoXuLyItemResponse(BaseModel):
    id: UUID
    ve_id: UUID
    so_ghe: str | None = None
    ma_dat_cho: str | None = None
    gia_ve: int | None = None
    so_tien: int
    ly_do: str
    trang_thai: str
    ten_khach_hang: str | None = None
    sdt_khach_hang: str | None = None
    thoi_gian_xac_dinh: datetime


# ---------------------------------------------------------
# 4. Response Chi tiết bản ghi hoàn tiền
# ---------------------------------------------------------
class LichSuHoanTienResponse(BaseModel):
    id: UUID
    ve_id: UUID
    ly_do: Literal[
        "bat_kha_khang_khong_hoan_thanh",
        "loi_nha_xe_giua_duong",
        "hoan_truoc_gio_chay",
        "tu_dong_hoan_qua_3_tieng",
    ]
    so_tien: int
    trang_thai: Literal["cho_xu_ly", "da_hoan_tu_dong", "da_hoan_chuyen_khoan_thu_cong"]

    ma_giao_dich_hoan_tien: str | None = None
    nhan_vien_xu_ly_id: UUID | None = None

    # Dữ liệu nhạy cảm (chỉ trả về cho Kế toán/Quản lý)
    # Dữ liệu đối soát tài khoản
    so_tai_khoan_nhan: str | None = None
    ten_ngan_hang_nhan: str | None = None
    ten_chu_tai_khoan_nhan: str | None = None

    thoi_gian_xac_dinh: datetime
    thoi_gian_hoan_xong: datetime | None = None

    # Thông tin bổ trợ nếu join vé
    so_ghe: str | None = None
    ma_dat_cho: str | None = None
    ten_khach_hang: str | None = None
    sdt_khach_hang: str | None = None


# ---------------------------------------------------------
# 5. Response Thống kê tài chính dành cho Kế toán (UC-39)
# ---------------------------------------------------------
class ThongKeKeToanResponse(BaseModel):
    tong_doanh_thu_ve: int = Field(0, description="Tổng tiền thu từ vé (da_thanh_toan, da_len_xe, da_xuong_xe)")
    tong_doanh_thu_gui_hang: int = Field(0, description="Tổng tiền thu từ cước gửi hàng")
    tong_tien_hoan_ve: int = Field(0, description="Tổng tiền đã hoàn trả cho khách")
    doanh_thu_thuan: int = Field(0, description="Doanh thu thực tế = (Vé + Hàng) - Hoàn tiền")
    so_luong_ve_da_ban: int = 0
    so_luong_don_hang: int = 0
    so_luot_hoan_tien: int = 0
    so_luot_cho_xu_ly: int = 0
