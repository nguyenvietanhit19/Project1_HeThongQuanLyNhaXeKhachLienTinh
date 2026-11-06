"""Pydantic schemas cho điều độ viên gán xe theo chu trình — UC-44, DIEU_DO_VIEN_THIET_KE_MOI.md mục 8."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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
    xe_thuc_te_id: UUID | None = None  # xe đang chạy thay xe gốc (UC-20); None = chạy bằng xe gốc
    bien_so_xe_thuc_te: str | None = None
    dang_hoan: bool = False  # đã quá giờ khởi hành mà chưa có xe (UC-44 ⏱)


class CanChuY(BaseModel):
    """Một việc điều độ viên cần xử lý ở chu trình."""

    ma: Literal["dang_hoan", "chua_gan_sap_toi", "xe_hong", "xe_thieu_nhan_su", "xe_goc_san_sang", "canh_bao_vi_tri"]
    muc_do: Literal["khan", "canh_bao", "thong_tin"]
    noi_dung: str
    ma_chuyen: str | None = None  # chuyến liên quan
    gio_khoi_hanh: datetime | None = None  # giờ khởi hành của chuyến đó — giao diện tự tính thời gian còn lại / đã quá


class ChuTrinhResponse(BaseModel):
    chu_trinh_id: UUID
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str
    loai_xe_id: UUID
    ten_loai_xe: str
    trang_thai_gan: Literal["chua_gan", "mot_phan", "da_gan"]
    can_chu_y: list[CanChuY] = []
    cac_chuyen: list[ChuyenTrongChuTrinh]


class SuCoDangXayRa(BaseModel):
    chuyen_id: UUID
    chu_trinh_id: UUID | None = None
    ma: str
    ma_tuyen: str
    ten_tuyen: str
    gio_khoi_hanh: datetime
    bien_so_xe: str | None = None
    loai_su_co: str | None = None  # loi_nha_xe | loi_khach_quan
    ly_do_su_co: str | None = None


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


class NhanSuXe(BaseModel):
    """Nhân sự đang hoạt động của xe: cần 2 tài xế + ≥1 phụ xe mới gán chuyến được."""

    tai_xe: int
    phu_xe: int
    du: bool


class XeChoChuTrinhResponse(BaseModel):
    xe_id: UUID
    bien_so: str
    hop_le: bool
    ly_do: list[str]  # mọi lý do không gán được (rỗng khi hop_le)
    ma_ly_do: list[str]  # song song ly_do: khong_hoat_dong | thieu_nhan_su | khac_loai | tuyen_co_dinh | trung_lich | sai_vi_tri | hong_chuyen_ke_tiep
    dang_gan: bool  # xe đang được gán cho chu trình này
    trang_thai_xe: str  # hoat_dong | bao_tri
    nhan_su: NhanSuXe
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


class NhomGanXe(BaseModel):
    """Đếm chu trình theo tình trạng gán xe; mỗi chu trình thuộc đúng một nhóm (đang hoãn > đã gán > chưa gán, gồm gán một phần)."""

    so_chu_trinh: int
    da_gan: int
    chua_gan: int
    dang_hoan: int


class TongQuanTong(NhomGanXe):
    so_chuyen: int
    dang_chay_thay: int  # chu trình đang có xe chạy thay
    viec_khan: int  # chu trình có ít nhất 1 việc mức khẩn
    viec_can_chu_y: int  # tổng số việc cần chú ý
    su_co_dang_xay_ra: int


class TongQuanTheoTuyen(NhomGanXe):
    tuyen_id: UUID
    ma_tuyen: str
    ten_tuyen: str


class TongQuanTheoNgay(NhomGanXe):
    ngay: date  # ngày khởi hành của chuyến đầu, giờ Việt Nam


class TongQuanDoiXe(BaseModel):
    hoat_dong: int
    bao_tri: int
    du_phong: int  # xe hoạt động không cố định tuyến
    co_dinh_tuyen: int
    ranh: int  # xe hoạt động chưa có chuyến nào trong khoảng đang xem
    dang_chay_thay: int  # số xe đang chạy thay trong các chu trình đang xem


class TongQuanChuyenGanDay(BaseModel):
    so_ngay: int
    hoan_thanh: int
    dang_chay: int
    gap_su_co: int
    da_huy: int


class TongQuanResponse(BaseModel):
    so_ngay: int
    tong: TongQuanTong
    theo_tuyen: list[TongQuanTheoTuyen]
    theo_ngay: list[TongQuanTheoNgay]
    doi_xe: TongQuanDoiXe
    chuyen_gan_day: TongQuanChuyenGanDay


class GanXeRequest(BaseModel):
    xe_id: UUID


class ThayXeRequest(BaseModel):
    xe_id: UUID
    ly_do: str | None = Field(default=None, max_length=200)  # kèm vào thông báo cho khách
