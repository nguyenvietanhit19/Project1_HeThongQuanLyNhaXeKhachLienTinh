"""Pydantic schemas cho trang "Chuyến" (xem/sửa/xóa từ góc nhìn quản lý) —
UC-18, NGHIEP_VU.md mục 3.5, DATABASE.md mục 3.3.
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class SuaGioChuyenRequest(BaseModel):
    """Chỉ đổi GIỜ — ngày của chuyến giữ nguyên (server tự lấy ngày hiện có)."""

    gio: time


class ChangGiaChuyen(BaseModel):
    ten_chang: str
    gia_goc: int
    gia_ban: int  # giá ghế thường (hệ số ghế = 1)
    gia_thap_nhat: int  # giá rẻ nhất trong các ghế của xe (khi tính hệ số từng ghế)
    gia_cao_nhat: int  # giá đắt nhất — bằng gia_ban khi mọi ghế cùng giá
    gia_theo_ghe: dict[str, int] = {}  # {mã ghế: giá bán ở chặng này}


class NhomGheKhacGia(BaseModel):
    he_so: Decimal
    cac_ghe: list[str]


class BangGiaChuyen(BaseModel):
    ap_dung_tu: date
    he_so_gia: Decimal
    cac_chang: list[ChangGiaChuyen]
    cac_nhom_ghe: list[NhomGheKhacGia] = []  # các ghế có hệ số khác 1, gom theo hệ số


class GheTrenChuyen(BaseModel):
    ma_ghe: str
    tang: int
    x: float
    y: float
    he_so: Decimal  # hệ số ghế đã chốt vào chuyến (1 = giá thường)


class VeTrenGhe(BaseModel):
    ma_ve: str
    so_ghe: str
    trang_thai: str  # giu_cho (còn hạn) | da_thanh_toan | da_len_xe | da_xuong_xe
    gia: int  # giá đã chốt lúc giữ ghế
    ten_diem_don: str
    ten_diem_tra: str


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
    he_so_gia: Decimal
    trang_thai: str
    xe_id: UUID | None = None
    bien_so_xe: str | None = None
    lich_chay_dinh_ky_id: UUID | None = None
    so_ve_dang_hoat_dong: int
    so_tang: int = 1  # chỉ có ở màn chi tiết
    so_do_ghe: list[GheTrenChuyen] = []  # chỉ có ở màn chi tiết 1 chuyến
    cac_ve_tren_ghe: list[VeTrenGhe] = []  # vé đang chiếm ghế (giữ còn hạn/đã thanh toán/đã lên-xuống xe) — chỉ ở màn chi tiết
    bang_gia: BangGiaChuyen | None = None  # chỉ có ở màn chi tiết 1 chuyến; None = ngày đó chưa có giá (khách không thấy chuyến)
