"""Schema Pydantic cho chuyến xe và điều độ viên.

Request/Response được dùng bởi routes/dieu_do.py.
Tên field khớp đúng với tên cột trong DATABASE.md mục 3.3.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ============================================================
# Response — hiển thị chuyến xe
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


# ============================================================
# Response — xe đủ điều kiện gán
# ============================================================

class XeDuDieuKienResponse(BaseModel):
    id: UUID
    bien_so: str
    loai_xe_id: UUID
    ten_loai_xe: str
    tuyen_id: UUID | None       # None = xe dự phòng
    diem_goc_id: UUID
    ten_diem_goc: str


# ============================================================
# Request — UC-44 Gán xe
# ============================================================

class GanXeRequest(BaseModel):
    xe_id: UUID


# ============================================================
# Request — UC-19 / UC-20 Điều xe thay thế
# ============================================================

class DieuXeThayTheRequest(BaseModel):
    xe_thay_the_id: UUID


class HoanChuyenRequest(BaseModel):
    gio_khoi_hanh_moi: datetime
