"""Pydantic schemas cho tìm kiếm chuyến xe — UC-04, UC-05.

Route chỉ khai báo hình dạng request/response, Service chứa logic
nghiệp vụ (ARCHITECTURE.md mục 2).
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


# ─── Request ──────────────────────────────────────────────────────────────────

class TimKiemChuyenRequest(BaseModel):
    """UC-04: Tìm kiếm chuyến công khai theo điểm đi/đến + ngày."""
    diem_di_id: str    # UUID của khu_vuc điểm đi (DATABASE.md mục 2.1)
    diem_den_id: str   # UUID của khu_vuc điểm đến
    ngay_di: date      # Ngày khách muốn đi


# ─── Response ─────────────────────────────────────────────────────────────────

class DiemDonTraResponse(BaseModel):
    """Thông tin 1 điểm đón/trả trong tuyến — dùng cho sơ đồ chọn điểm."""
    id: str
    ten: str
    dia_chi: str
    loai: str       # 'van_phong' | 'diem_dung'
    thu_tu: int     # Thứ tự trong tuyến — dùng để tính overlap chặng (mục 6)
    thoi_gian_du_kien_phut: int


class ChuyenXeResponse(BaseModel):
    """1 kết quả trong danh sách tìm kiếm chuyến (UC-04 bước 2–3)."""
    id: str
    tuyen_id: str
    ten_tuyen: str
    loai_xe_ten: str        # Tên loại xe — hiển thị khi chưa gán xe_id cụ thể
    bien_so: str | None     # None nếu chưa gán xe cụ thể (mục 3.5 NGHIEP_VU.md)
    gio_khoi_hanh: datetime
    so_ghe_trong: int       # Tính theo đoạn rộng nhất của cặp khu_vuc đang tìm
    gia_tu: int             # gia_ve.gia_goc × loai_xe.he_so_gia (mục 3.1)
    dang_hoan: bool         # Đang hoãn trước giờ chạy (mục 3.3)
    trang_thai: str


class SoDoGheResponse(BaseModel):
    """Sơ đồ ghế của 1 chuyến để khách chọn (UC-04 bước 4, UC-05 bước 1)."""
    chuyen_id: str
    loai_xe_ten: str
    so_do_ghe: list[Any]    # JSONB từ loai_xe.so_do_ghe (DATABASE.md mục 3.1)
    ghe_da_chon: list[str]  # Danh sách so_ghe đang bị giữ trong đoạn tìm kiếm
    diem_don_hop_le: list[DiemDonTraResponse]   # Chỉ van_phong thuộc khu_vuc đi
    diem_tra_hop_le: list[DiemDonTraResponse]   # van_phong + diem_dung thuộc khu_vuc đến
