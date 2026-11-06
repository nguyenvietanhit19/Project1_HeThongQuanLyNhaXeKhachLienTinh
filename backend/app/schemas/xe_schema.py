"""Pydantic schemas cho Loại xe (UC-32, DATABASE.md mục 3.1), Xe (UC-34, mục 3.2)
và Biên chế xe (UC-35, mục 1.5) — NGHIEP_VU.md mục 3.1/3.2.
"""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from datetime import date

from pydantic import BaseModel, Field, computed_field

from app.utils import bien_che as quy_tac_bien_che


class GheXe(BaseModel):
    ma_ghe: str = Field(..., min_length=1, description='VD "A1-1" (dãy A, ghế 1, tầng 1)')
    tang: int = Field(..., ge=1, le=2)
    x: float = Field(..., ge=0, description="Vị trí ngang trên sơ đồ (px) — đặt tự do, không theo lưới cố định")
    y: float = Field(..., ge=0, description="Vị trí dọc trên sơ đồ (px), 0 = đầu xe")


class LoaiXeRequest(BaseModel):
    ten: str = Field(..., min_length=1)
    he_so_ghe: dict[str, Decimal] = Field(
        default_factory=dict,
        description='Hệ số giá từng ghế {"A1-1": 1.1}; ghế vắng mặt = 1. Luôn sửa được (kể cả khi sơ đồ đã khóa), chỉ áp dụng cho chuyến sinh sau',
    )
    phien_ban: int | None = Field(None, description="Phiên bản đang xem (bắt buộc khi sửa) — lệch nghĩa là đã có người khác sửa")
    so_do_ghe: list[GheXe] = Field(..., min_length=1, description="Sơ đồ ghế thật — dùng chung cho mọi xe cùng loại này")


class LoaiXeResponse(BaseModel):
    id: UUID
    ma: str
    ten: str
    so_do_ghe: list[GheXe]
    he_so_ghe: dict[str, Decimal] = Field(default_factory=dict)
    phien_ban: int = 1
    khoa_so_do_ghe: bool = Field(False, description="True khi đã có xe/chuyến dùng loại này — không sửa sơ đồ ghế được nữa")


# ---------------------------------------------------------
# Xe (UC-34)
# ---------------------------------------------------------
class XeRequest(BaseModel):
    bien_so: str = Field(..., min_length=1, max_length=20)
    loai_xe_id: UUID
    diem_goc_id: UUID = Field(..., description="Phải là điểm loai = van_phong (kiểm tra ở Service)")
    tuyen_id: UUID | None = Field(None, description="Có giá trị = xe cố định đúng tuyến này (cả 2 chiều); None = xe dự phòng")
    trang_thai: Literal["hoat_dong", "bao_tri", "ngung_su_dung"] = "hoat_dong"


class XeResponse(BaseModel):
    id: UUID
    bien_so: str
    loai_xe_id: UUID
    ma_loai_xe: str
    ten_loai_xe: str
    trang_thai: str
    diem_goc_id: UUID
    ma_diem_goc: str
    ten_diem_goc: str
    tuyen_id: UUID | None = None
    ma_tuyen: str | None = None
    ten_tuyen: str | None = None
    so_tai_xe_co_dinh: int
    so_phu_xe_co_dinh: int
    so_tai_xe_hieu_luc: int = Field(..., description="Tài xế ĐANG HOẠT ĐỘNG (cố định hoặc tạm thời, hồ sơ còn đang làm) — NGHIEP_VU.md mục 3.2")
    so_phu_xe_hieu_luc: int

    @computed_field
    @property
    def du_nhan_su(self) -> bool:
        """Đủ 2 tài xế + ít nhất 1 phụ xe đang hoạt động — chưa đủ thì KHÔNG gán được chuyến (UC-44)."""
        return quy_tac_bien_che.du_nhan_su(self.so_tai_xe_hieu_luc, self.so_phu_xe_hieu_luc)

    @computed_field
    @property
    def thieu_nhan_su(self) -> str:
        return quy_tac_bien_che.mo_ta_thieu(self.so_tai_xe_hieu_luc, self.so_phu_xe_hieu_luc)

    @computed_field
    @property
    def can_canh_bao_nhan_su(self) -> bool:
        """Hiện cảnh báo trên trang Xe: xe đang hoạt động, cố định tuyến, chưa đủ nhân sự (xe dự phòng không cảnh báo)."""
        return quy_tac_bien_che.can_canh_bao_thieu_nhan_su(self.trang_thai, self.tuyen_id, self.so_tai_xe_hieu_luc, self.so_phu_xe_hieu_luc)


# ---------------------------------------------------------
# Biên chế xe (UC-35)
# ---------------------------------------------------------
class BienCheItem(BaseModel):
    id: UUID = Field(..., description="id dòng xe_nhan_su")
    nhan_su_van_hanh_id: UUID
    ma: str | None = None
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    loai: str
    trang_thai: str
    trang_thai_nhan_su: str | None = None  # dang_lam | da_nghi_viec — người đã nghỉ việc không được tính vào nhân sự của xe


class NhanSuKhaDung(BaseModel):
    id: UUID
    ma: str | None = None  # mã nhân viên: tài xế TX…, phụ xe PX… (của tài khoản)
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    co_tai_khoan: bool
    email: str | None = None  # chỉ phụ xe
    ngay_vao_lam: date | None = None
    xe_id_co_dinh: UUID | None = None
    bien_so_xe_co_dinh: str | None = None
    giay_to_tinh_trang: Literal["het_han", "sap_het_han"] | None = None  # giấy tờ có vấn đề (hết hạn / sắp hết hạn), None = ổn hoặc chưa có


class GiayToChiTiet(BaseModel):
    loai: Literal["bang_lai", "giay_kham_suc_khoe"]
    so_giay_to: str | None = None
    hang: str | None = None
    ngay_cap: date | None = None
    ngay_het_han: date
    tinh_trang: Literal["con_han", "sap_het_han", "het_han"]
    anh_url: str | None = Field(default=None, description="URL ảnh giấy tờ có chữ ký (Cloudinary), None nếu chưa có ảnh hoặc không sinh được URL")


class BienCheHienTai(BaseModel):
    xe_id: UUID
    bien_so: str
    loai: str
    trang_thai: str


class NhanSuChiTietBienChe(BaseModel):
    """TOÀN BỘ hồ sơ nhân sự (chỉ xem) cho quản lý khi cân nhắc đưa vào biên chế: thông tin cá nhân, ảnh, giấy tờ, tài khoản, biên chế hiện tại.
    Sửa hồ sơ vẫn là việc của quan_ly_nhan_su (UC-49)."""

    id: UUID
    ma: str | None = None
    ho_ten: str
    so_dien_thoai: str
    chuc_danh: str
    trang_thai: str
    so_cccd: str | None = None
    ngay_sinh: date | None = None
    anh_url: str | None = Field(default=None, description="URL ảnh chân dung có chữ ký, None nếu chưa có ảnh")
    ngay_vao_lam: date | None = None
    ngay_nghi_viec: date | None = None
    ly_do_nghi_viec: str | None = None
    co_tai_khoan: bool
    email: str | None = None
    tai_khoan_hoat_dong: bool | None = None
    giay_to: list[GiayToChiTiet]
    bien_che: list[BienCheHienTai]


class ThemBienCheRequest(BaseModel):
    nhan_su_van_hanh_id: UUID
