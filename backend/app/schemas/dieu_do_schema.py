"""Pydantic schemas cho điều độ viên gán xe theo chu trình — UC-44, DIEU_DO_VIEN_THIET_KE_MOI.md mục 8."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ChuyenTrongChuTrinh(BaseModel):
    id: UUID
    ma: str
    chieu: str  # xuoi (chuyến đi) | nguoc (chuyến về)
    gio_khoi_hanh: datetime
    gio_ket_thuc: datetime  # dự kiến = giờ khởi hành + thời gian chạy cả tuyến
    ten_diem_di: str
    ten_diem_den: str
    trang_thai: str
    xe_id: UUID | None = None
    bien_so_xe: str | None = None


class ChuTrinhResponse(BaseModel):
    chu_trinh_id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    loai_xe_id: UUID
    ten_loai_xe: str
    trang_thai_gan: Literal["chua_gan", "mot_phan", "da_gan"]
    cac_chuyen: list[ChuyenTrongChuTrinh]


class TuyenPhuTrachResponse(BaseModel):
    id: UUID
    ma: str
    ten: str


class LoaiXeTomTat(BaseModel):
    id: UUID
    ma: str
    ten: str
    so_ghe: int
    so_tang: int


class GheTrenSoDo(BaseModel):
    ma_ghe: str
    tang: int
    x: float
    y: float


class LoaiXeChiTietResponse(LoaiXeTomTat):
    so_do_ghe: list[GheTrenSoDo]


class ViTriXe(BaseModel):
    """Vị trí DỰ KIẾN của xe lúc chuyến đầu khởi hành (suy ra từ lịch, không phải GPS)."""

    diem_id: UUID
    ten_diem: str
    nguon: Literal["diem_goc", "sau_chuyen"]
    chuyen_ma: str | None = None  # chuyến gần nhất đưa xe tới đây (nguon = sau_chuyen)
    tu_luc: datetime | None = None  # giờ xe tới đây
    dung_diem_xuat_phat: bool


class ChuyenKeTiepCuaXe(BaseModel):
    ma: str
    gio_khoi_hanh: datetime
    ten_diem_di: str
    ten_diem_den: str


class ChuyenChiemLichXe(BaseModel):
    ma: str
    gio_khoi_hanh: datetime
    gio_ket_thuc: datetime


class TuyenCoDinhCuaXe(BaseModel):
    ma: str
    ten: str


class XeChoChuTrinhResponse(BaseModel):
    xe_id: UUID
    bien_so: str
    hop_le: bool
    ly_do: list[str]  # mọi lý do không gán được (rỗng khi hop_le)
    ma_ly_do: list[str]  # song song ly_do: khong_hoat_dong | khac_loai | tuyen_co_dinh | trung_lich | sai_vi_tri | hong_chuyen_ke_tiep
    dang_gan: bool  # xe đang được gán cho chu trình này
    trang_thai_xe: str  # hoat_dong | bao_tri
    loai_xe: LoaiXeTomTat
    dung_loai: bool  # đúng loại xe cam kết của chu trình
    tuyen_co_dinh: TuyenCoDinhCuaXe | None = None
    vi_tri: ViTriXe
    chuyen_ke_tiep: ChuyenKeTiepCuaXe | None = None  # chuyến sớm nhất của xe sau chu trình
    chuyen_trung: list[ChuyenChiemLichXe] = []  # chuyến đang chiếm lịch xe, chồng với chu trình


class DiemLoTrinh(BaseModel):
    diem_don_tra_id: UUID
    ten: str
    ten_khu_vuc: str
    loai: Literal["van_phong", "diem_dung"]
    gio_den: datetime  # dự kiến


class ChuyenLoTrinh(BaseModel):
    id: UUID
    ma: str
    chieu: str
    trang_thai: str
    gio_khoi_hanh: datetime
    gio_ket_thuc: datetime
    diem: list[DiemLoTrinh]  # theo đúng thứ tự xe đi qua của chiều này


class LoTrinhChuTrinhResponse(BaseModel):
    chu_trinh_id: UUID
    tuyen: TuyenPhuTrachResponse
    loai_xe_cam_ket: LoaiXeTomTat
    cac_chuyen: list[ChuyenLoTrinh]


class GanXeRequest(BaseModel):
    xe_id: UUID
