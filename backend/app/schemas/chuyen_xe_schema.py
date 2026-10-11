from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class HanhTrinhDiemResponse(BaseModel):
    """1 điểm trong toàn bộ lộ trình của chuyến — mục 8.2 điểm 5."""

    diem_don_tra_id: str
    ten_diem: str
    thu_tu: int
    da_toi: bool
    gio_thuc_te: datetime | None = None


class ChuyenPhuXeResponse(BaseModel):
    """1 dòng trong danh sách 'chuyến của tôi' — NGHIEP_VU.md mục 8.2 điểm 1."""

    id: str
    tuyen_ten: str
    bien_so: str
    gio_khoi_hanh: datetime
    trang_thai: str
    dang_hoan: bool


class KhachTaiDiemResponse(BaseModel):
    ve_id: str
    so_ghe: str
    ho_ten: str
    so_dien_thoai: str
    ma_dat_cho: str


class DiemHienTaiResponse(BaseModel):
    """Danh sách khách cần lên/xuống tại điểm phụ xe đang đứng — mục 8.2 điểm 1."""

    diem_don_tra_id: str
    ten_diem: str
    khach_can_len: list[KhachTaiDiemResponse]
    khach_can_xuong: list[KhachTaiDiemResponse]


class XacNhanToiDiemRequest(BaseModel):
    diem_don_tra_id: str


class XacNhanToiDiemResponse(BaseModel):
    da_hoan_thanh: bool


class BaoSuCoRequest(BaseModel):
    loai_su_co: str
    ly_do: str


class ThongKePhuXeResponse(BaseModel):
    """UC-39 — chỉ tính các chuyến thuộc xe của phụ xe đang xem."""

    so_chuyen: int
    doanh_thu: float
    ty_le_lap_day_trung_binh: float
    so_chuyen_su_co: int
    so_chuyen_huy: int


# ============================================================
# Schemas cho Điều độ viên (UC-44, UC-45, UC-19, UC-20, UC-40, UC-39)
# ============================================================

class ChuyenXeResponse(BaseModel):
    id: UUID
    tuyen_id: UUID
    ten_tuyen: str
    chieu: str                  # 'xuoi' | 'nguoc'
    xe_id: UUID | None
    bien_so_xe: str | None
    loai_xe_id: UUID
    ten_loai_xe: str
    lich_chay_dinh_ky_id: UUID | None
    xe_thuc_te_id: UUID | None
    gio_khoi_hanh: datetime
    trang_thai: str
    dang_hoan: bool
    co_canh_bao_xung_dot_vi_tri: bool
    loai_su_co: str | None


class DanhSachChuyenResponse(BaseModel):
    chuyen: list[ChuyenXeResponse]


class XeDuDieuKienResponse(BaseModel):
    id: UUID
    bien_so: str
    loai_xe_id: UUID
    ten_loai_xe: str
    tuyen_id: UUID | None       # None = xe dự phòng
    diem_goc_id: UUID
    ten_diem_goc: str


class GanXeRequest(BaseModel):
    xe_id: UUID


class DieuXeThayTheRequest(BaseModel):
    xe_thay_the_id: UUID


class HoanChuyenRequest(BaseModel):
    gio_khoi_hanh_moi: datetime

