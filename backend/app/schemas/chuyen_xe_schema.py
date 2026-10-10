from datetime import datetime

from pydantic import BaseModel


class HanhTrinhDiemResponse(BaseModel):
    """1 điểm trong toàn bộ lộ trình của chuyến — mục 8.2 điểm 5."""

    diem_don_tra_id: str
    ten_diem: str
    thu_tu: int
    da_toi: bool
    gio_thuc_te: datetime | None = None
    gio_du_kien: datetime | None = None


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


# ---------------------------------------------------------------- Tổng quan chuyến (phụ xe xem lại)
class HanhKhachResponse(BaseModel):
    """1 hành khách (1 vé) trên chuyến — kèm trạng thái lên/xuống xe."""

    ve_id: str
    so_ghe: str
    ho_ten: str
    so_dien_thoai: str
    ma_dat_cho: str
    trang_thai: str
    diem_don_id: str
    diem_tra_id: str
    ten_diem_don: str
    ten_diem_tra: str
    gia: float
    loai_hinh_thanh_toan: str
    gio_len_xe: datetime | None = None
    gio_xuong_xe: datetime | None = None
    da_hoan_tac: bool = False  # phụ xe đã tự tay sửa vé này → job no-show bỏ qua


class HangHoaResponse(BaseModel):
    """1 đơn hàng đã xếp lên chuyến."""

    id: str
    ma_van_don: str
    trang_thai: str
    can_nang_kg: float
    ten_nguoi_gui: str
    sdt_nguoi_gui: str
    ten_nguoi_nhan: str
    sdt_nguoi_nhan: str
    ten_diem_gui: str
    ten_diem_nhan: str
    ten_loai_hang: str | None = None
    so_bao_cao_su_co: int = 0
    so_bao_hu_hong: int = 0
    so_bao_that_lac: int = 0


class ThongTinChuyenResponse(BaseModel):
    id: str
    ma: str | None = None
    tuyen_ten: str
    chieu: str
    bien_so: str | None = None
    gio_khoi_hanh: datetime
    gio_xac_nhan_xuat_phat: datetime | None = None
    gio_hoan_thanh: datetime | None = None
    trang_thai: str
    dang_hoan: bool
    loai_su_co: str | None = None
    ly_do_su_co: str | None = None


class TongQuanChuyenResponse(BaseModel):
    chuyen: ThongTinChuyenResponse
    hanh_trinh: list[HanhTrinhDiemResponse]
    hanh_khach: list[HanhKhachResponse]
    hang_hoa: list[HangHoaResponse]


class ChuyenDaChayResponse(BaseModel):
    """1 dòng trong danh sách chuyến đã chạy (trang thống kê)."""

    id: str
    ma: str | None = None
    tuyen_ten: str
    chieu: str
    gio_khoi_hanh: datetime
    trang_thai: str
    tong_ghe: int | None = None
    so_ve_ban: int
    doanh_thu: float
    so_don_hang: int


class LichSuTrangThaiDonResponse(BaseModel):
    tu_trang_thai: str | None = None
    den_trang_thai: str
    thoi_gian: datetime
    ten_nguoi_thuc_hien: str | None = None  # None = hệ thống tự chuyển


class BaoCaoSuCoHangResponse(BaseModel):
    id: str
    mo_ta: str
    ngay_tao: datetime
    ten_nguoi_bao_cao: str | None = None
    loai: str = "hu_hong"


class ChiTietDonHangResponse(BaseModel):
    """Thông tin đầy đủ 1 đơn hàng + các mốc đổi trạng thái + báo cáo thất lạc/hư hỏng."""

    id: str
    ma_van_don: str
    trang_thai: str
    can_nang_kg: float
    ten_loai_hang: str | None = None
    ten_tuyen: str | None = None
    ten_nguoi_gui: str
    sdt_nguoi_gui: str
    ten_nguoi_nhan: str
    sdt_nguoi_nhan: str
    ten_diem_gui: str | None = None
    ten_diem_nhan: str | None = None
    gia_cuoc: float
    phuong_thuc_thanh_toan: str
    ma_chuyen: str | None = None
    bien_so_xe: str | None = None
    thoi_gian_den_diem_nhan: datetime | None = None
    lich_su_trang_thai: list[LichSuTrangThaiDonResponse]
    bao_cao_su_co: list[BaoCaoSuCoHangResponse]
