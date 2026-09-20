"""Pydantic schemas cho Đơn hàng gửi — NGHIEP_VU.md mục 10 & DATABASE.md mục 5.2.

Định nghĩa hình dạng dữ liệu Request (nhận vào từ Frontend) và Response
(trả về sau khi xử lý xong) cho phân hệ Gửi hàng.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# 1. Schemas cho Loại hàng (Hàng thường, dễ vỡ, hàng cấm...)
# ---------------------------------------------------------
class LoaiHangResponse(BaseModel):
    id: UUID
    ten: str
    la_hang_cam: bool


# ---------------------------------------------------------
# 2. Schemas Tạo đơn hàng mới (UC-23: Nhận hàng tại quầy)
# ---------------------------------------------------------
class TaoDonHangRequest(BaseModel):
    tuyen_id: UUID = Field(..., description="Tuyến xe khách gửi hàng qua")
    diem_gui_id: UUID = Field(..., description="Văn phòng gửi (nơi tiếp nhận)")
    diem_nhan_id: UUID = Field(..., description="Văn phòng nhận hàng")
    loai_hang_id: UUID = Field(..., description="Loại hàng hóa")

    can_nang_kg: Decimal = Field(..., gt=0, description="Khối lượng hàng (kg)")
    dai_cm: Decimal | None = Field(None, gt=0, description="Chiều dài (cm, tùy chọn)")
    rong_cm: Decimal | None = Field(None, gt=0, description="Chiều rộng (cm, tùy chọn)")
    cao_cm: Decimal | None = Field(None, gt=0, description="Chiều cao (cm, tùy chọn)")

    gia_cuoc: int = Field(..., ge=0, description="Tiền cước nhân viên tự nhập tay (VNĐ)")

    ten_nguoi_gui: str = Field(..., min_length=1, description="Họ tên người gửi")
    sdt_nguoi_gui: str = Field(..., min_length=8, max_length=15, description="Số điện thoại người gửi")

    ten_nguoi_nhan: str = Field(..., min_length=1, description="Họ tên người nhận")
    sdt_nguoi_nhan: str = Field(..., min_length=8, max_length=15, description="Số điện thoại người nhận")

    phuong_thuc_thanh_toan: Literal["nguoi_gui_tra_truoc", "cod_nguoi_nhan_tra"] = Field(
        ..., description="Hình thức: người gửi trả tiền trước hoặc COD người nhận trả"
    )


# ---------------------------------------------------------
# 3. Schemas Giao hàng cho người nhận (UC-24: Giao hàng & thu COD)
# ---------------------------------------------------------
class GiaoHangRequest(BaseModel):
    ma_van_don: str = Field(..., description="Mã vận đơn khách đọc lúc nhận hàng")


# ---------------------------------------------------------
# 4. Schemas Cập nhật liên hệ hàng chờ lâu (UC-25)
# ---------------------------------------------------------
class CapNhatLienHeRequest(BaseModel):
    da_thong_bao_nguoi_nhan: bool = Field(..., description="Đã gọi được cho người nhận hay chưa")
    ghi_chu: str | None = Field(None, description="Ghi chú kết quả gọi (hẹn ngày lấy, gọi người gửi...)")


# ---------------------------------------------------------
# 5. Schema Chi tiết đơn hàng trả về (Response)
# ---------------------------------------------------------
class DonHangResponse(BaseModel):
    id: UUID
    ma_van_don: str
    tuyen_id: UUID
    chuyen_id: UUID | None = None
    diem_gui_id: UUID
    diem_nhan_id: UUID
    loai_hang_id: UUID
    ten_loai_hang: str | None = None

    can_nang_kg: Decimal
    dai_cm: Decimal | None = None
    rong_cm: Decimal | None = None
    cao_cm: Decimal | None = None

    gia_cuoc: int
    ten_nguoi_gui: str
    sdt_nguoi_gui: str
    ten_nguoi_nhan: str
    sdt_nguoi_nhan: str
    phuong_thuc_thanh_toan: str

    trang_thai: Literal["cho_van_chuyen", "da_len_xe", "cho_lay", "da_giao", "qua_han_luu_kho"]
    nhan_vien_gui_id: UUID
    nhan_vien_nhan_id: UUID | None = None

    thoi_gian_den_diem_nhan: datetime | None = None
    da_thong_bao_nguoi_nhan: bool = False
    co_canh_bao_cho_lau: bool = False

    ngay_tao: datetime
    ngay_giao: datetime | None = None


# ---------------------------------------------------------
# 6. Schemas dùng bởi phụ xe (UC-26, UC-27, UC-28) — tuanhdung, #<phu-xe>
# ---------------------------------------------------------
class DonHangChoChatResponse(BaseModel):
    """1 dòng trong danh sách đơn hàng chờ chất lên chuyến — NGHIEP_VU.md mục 10.2, UC-26."""

    id: str
    ma_van_don: str
    ten_nguoi_nhan: str
    ten_diem_nhan: str
    can_nang_kg: float
    ngay_tao: datetime


class DonHangChoDoResponse(BaseModel):
    """1 dòng trong danh sách đơn hàng cần dỡ tại điểm hiện tại — UC-27."""

    id: str
    ma_van_don: str
    ten_nguoi_nhan: str
    can_nang_kg: float


class XacNhanChatHangRequest(BaseModel):
    chuyen_id: str


class BaoThatLacRequest(BaseModel):
    mo_ta: str

