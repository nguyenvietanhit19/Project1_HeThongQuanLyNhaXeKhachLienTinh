"""Pydantic schemas cho Kế toán & Hoàn tiền — NGHIEP_VU.md mục 7 & DATABASE.md mục 4.1.

Định nghĩa hình dạng dữ liệu Request và Response cho phân hệ Kế toán xử lý
hoàn tiền (thủ công & tự động).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# 1. Request Kế toán xác nhận đã chuyển khoản hoàn tiền (UC-22)
# ---------------------------------------------------------
class XacNhanChuyenKhoanRequest(BaseModel):
    so_tai_khoan_nhan: str = Field(..., min_length=4, max_length=30, description="Số tài khoản ngân hàng của khách")
    ten_ngan_hang_nhan: str = Field(..., min_length=2, description="Tên ngân hàng (Vietcombank, MB, Techcombank...)")
    ten_chu_tai_khoan_nhan: str = Field(..., min_length=2, description="Tên chủ tài khoản nhận tiền")


# ---------------------------------------------------------
# 2. Response Chi tiết bản ghi hoàn tiền
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
    so_tai_khoan_nhan: str | None = None
    ten_ngan_hang_nhan: str | None = None
    ten_chu_tai_khoan_nhan: str | None = None

    thoi_gian_xac_dinh: datetime
    thoi_gian_hoan_xong: datetime | None = None

