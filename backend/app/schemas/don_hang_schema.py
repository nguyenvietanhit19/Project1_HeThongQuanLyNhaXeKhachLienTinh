"""Pydantic schemas cho Đơn hàng gửi — NGHIEP_VU.md mục 10 & DATABASE.md mục 5.2.

Định nghĩa hình dạng dữ liệu Request (nhận vào từ Frontend) và Response
(trả về sau khi xử lý xong) cho phân hệ Gửi hàng.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

TrangThaiDonHang = Literal["cho_van_chuyen", "da_len_xe", "cho_lay", "da_giao", "qua_han_luu_kho"]
PhuongThucThanhToan = Literal["nguoi_gui_tra_truoc", "cod_nguoi_nhan_tra"]

# Tên người gửi/nhận: bỏ khoảng trắng 2 đầu, không được rỗng, giới hạn độ dài
# (người vãng lai không có tài khoản — mục 10.1, chỉ lưu tên + SĐT).
HoTen = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
SoDienThoai = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{10,11}$")]

# Cận trên khớp kiểu cột DB (NUMERIC(8,2) / NUMERIC(12,0)) — trả 422 thay vì để DB ném lỗi thành 500.
KICH_THUOC_TOI_DA = Decimal("999999.99")
CUOC_TOI_DA = 999_999_999_999


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

    can_nang_kg: Decimal = Field(..., gt=0, le=KICH_THUOC_TOI_DA, decimal_places=2, description="Khối lượng hàng (kg)")
    dai_cm: Decimal | None = Field(None, gt=0, le=KICH_THUOC_TOI_DA, decimal_places=2, description="Chiều dài (cm, tùy chọn)")
    rong_cm: Decimal | None = Field(None, gt=0, le=KICH_THUOC_TOI_DA, decimal_places=2, description="Chiều rộng (cm, tùy chọn)")
    cao_cm: Decimal | None = Field(None, gt=0, le=KICH_THUOC_TOI_DA, decimal_places=2, description="Chiều cao (cm, tùy chọn)")

    gia_cuoc: int = Field(..., ge=1000, le=CUOC_TOI_DA, description="Tiền cước nhân viên tự nhập tay (VNĐ), tối thiểu 1.000")

    ten_nguoi_gui: HoTen = Field(..., description="Họ tên người gửi")
    sdt_nguoi_gui: SoDienThoai = Field(..., description="Số điện thoại người gửi")

    ten_nguoi_nhan: HoTen = Field(..., description="Họ tên người nhận")
    sdt_nguoi_nhan: SoDienThoai = Field(..., description="Số điện thoại người nhận")

    phuong_thuc_thanh_toan: PhuongThucThanhToan = Field(
        ..., description="Hình thức: người gửi trả tiền trước hoặc COD người nhận trả"
    )
    xac_nhan_da_thu: bool = Field(False, description="Nhân viên xác nhận đã thu tiền nếu người gửi trả trước")


# ---------------------------------------------------------
# 3. Schemas Giao hàng cho người nhận (UC-24: Giao hàng & thu COD)
# ---------------------------------------------------------
class GiaoHangRequest(BaseModel):
    ma_van_don: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=40)] = Field(
        ..., description="Mã vận đơn khách đọc lúc nhận hàng"
    )
    xac_nhan_da_thu: bool = Field(False, description="Nhân viên xác nhận đã thu đủ cước COD tại quầy")


# ---------------------------------------------------------
# 3b. Schemas Sửa thông tin liên hệ của đơn (tên / SĐT người gửi, người nhận)
# ---------------------------------------------------------
TRUONG_LIEN_HE = ("ten_nguoi_gui", "sdt_nguoi_gui", "ten_nguoi_nhan", "sdt_nguoi_nhan")


class SuaThongTinLienHeRequest(BaseModel):
    """Chỉ gửi những trường cần sửa. Không có tuyến/điểm nhận/loại hàng/cước — đổi các thứ đó
    ảnh hưởng chuyến xe và đối soát tiền nên phải hủy đơn rồi tạo lại."""

    ten_nguoi_gui: HoTen | None = None
    sdt_nguoi_gui: SoDienThoai | None = None
    ten_nguoi_nhan: HoTen | None = None
    sdt_nguoi_nhan: SoDienThoai | None = None
    ly_do: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = Field(
        None, description="Lý do sửa (tùy chọn, hiện trong nhật ký chỉnh sửa)"
    )

    @model_validator(mode="after")
    def _phai_co_it_nhat_mot_truong(self):
        if not any(getattr(self, t) is not None for t in TRUONG_LIEN_HE):
            raise ValueError("Cần ít nhất một thông tin để sửa")
        if not self.ly_do:
            self.ly_do = None
        return self


class LichSuChinhSuaResponse(BaseModel):
    truong: str
    gia_tri_cu: str | None = None
    gia_tri_moi: str
    ten_nguoi_thuc_hien: str | None = None
    ly_do: str | None = None
    thoi_gian: datetime


# ---------------------------------------------------------
# 4. Schemas Cập nhật liên hệ hàng chờ lâu (UC-25)
# ---------------------------------------------------------
TO_HOP_LIEN_HE_HOP_LE = {
    ("nguoi_nhan", "da_lien_he"),
    ("nguoi_nhan", "khong_lien_he_duoc"),
    ("nguoi_gui", "da_lien_he"),
    ("nguoi_gui", "khong_lien_he_duoc"),
    ("quan_ly", "da_bao_quan_ly"),
}


class CapNhatLienHeRequest(BaseModel):
    doi_tuong: Literal["nguoi_nhan", "nguoi_gui", "quan_ly"] = "nguoi_nhan"
    ket_qua: Literal["da_lien_he", "khong_lien_he_duoc", "da_bao_quan_ly"]
    ghi_chu: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = Field(
        None, description="Ghi chú kết quả liên hệ / hướng xử lý đã thỏa thuận"
    )

    @model_validator(mode="after")
    def kiem_tra_to_hop(self):
        if (self.doi_tuong, self.ket_qua) not in TO_HOP_LIEN_HE_HOP_LE:
            raise ValueError("Kết quả liên hệ không phù hợp với đối tượng liên hệ")
        if self.ghi_chu == "":
            self.ghi_chu = None
        return self


class LichSuLienHeResponse(BaseModel):
    id: UUID
    doi_tuong: str
    ket_qua: str
    ghi_chu: str | None = None
    ten_nhan_vien: str | None = None
    ngay_tao: datetime


class LichSuTrangThaiResponse(BaseModel):
    tu_trang_thai: str | None = None
    den_trang_thai: str
    ten_nguoi_thuc_hien: str | None = Field(None, description="Rỗng = hệ thống tự chuyển")
    thoi_gian: datetime


class GoiYKhachResponse(BaseModel):
    ten: str
    so_don: int
    lan_cuoi: datetime


class BaoCaoSuCoHangResponse(BaseModel):
    id: UUID
    mo_ta: str
    ten_nguoi_bao_cao: str | None = None
    ngay_tao: datetime


class GanVanPhongCanBoRequest(BaseModel):
    van_phong_id: UUID


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
    ten_tuyen: str | None = None
    ten_diem_gui: str | None = None
    ten_diem_nhan: str | None = None
    dia_chi_diem_gui: str | None = None
    dia_chi_diem_nhan: str | None = None
    sdt_diem_nhan: str | None = None

    can_nang_kg: float
    dai_cm: float | None = None
    rong_cm: float | None = None
    cao_cm: float | None = None

    gia_cuoc: int
    ten_nguoi_gui: str
    sdt_nguoi_gui: str
    ten_nguoi_nhan: str
    sdt_nguoi_nhan: str
    phuong_thuc_thanh_toan: str
    da_thu_tien: bool = False
    thoi_gian_thu: datetime | None = None
    nhan_vien_thu_id: UUID | None = None

    trang_thai: TrangThaiDonHang
    nhan_vien_gui_id: UUID
    nhan_vien_nhan_id: UUID | None = None

    thoi_gian_den_diem_nhan: datetime | None = None
    da_thong_bao_nguoi_nhan: bool = False
    co_canh_bao_cho_lau: bool = False
    so_bao_cao_su_co: int = 0
    so_lan_chinh_sua: int = 0

    # Thông tin chuyến đang chở (chỉ có khi đơn đã lên xe) — màn "Hàng sắp đến"
    ma_chuyen: str | None = None
    bien_so_xe: str | None = None
    gio_khoi_hanh: datetime | None = None

    ngay_tao: datetime
    ngay_giao: datetime | None = None


class DanhSachDonHangResponse(BaseModel):
    items: list[DonHangResponse]
    total: int


class DonHangTraCuuCongKhaiResponse(BaseModel):
    """Thông tin tối thiểu được phép hiển thị khi tra cứu công khai."""
    ma_van_don: str
    ten_tuyen: str | None = None
    ten_diem_gui: str | None = None
    ten_diem_nhan: str | None = None
    dia_chi_diem_nhan: str | None = None
    trang_thai: TrangThaiDonHang
    thoi_gian_den_diem_nhan: datetime | None = None
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
