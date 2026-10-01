"""API Router cho phân hệ Gửi hàng — NGHIEP_VU.md mục 10 & mục 8.5.

Route chỉ nhận request, kiểm tra quyền qua dependency yeu_cau_vai_tro,
gọi gui_hang_service và trả response.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.repositories import dia_diem_repository as dia_diem_repo
from app.schemas.don_hang_schema import (
    CapNhatLienHeRequest,
    DonHangResponse,
    GiaoHangRequest,
    LoaiHangResponse,
    TaoDonHangRequest,
    TheoDoiDonHangResponse,
    XacNhanThuCODRequest,
)
from app.services import gui_hang_service

router = APIRouter(prefix="/gui-hang", tags=["gui-hang"])

QuyenNhanVienGuiHang = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_gui_hang", "quan_ly"))
]
QuyenPhuXe = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("phu_xe"))
]


# ====================================================================
# 1. Danh mục Loại hàng & Tạo đơn (UC-23)
# ====================================================================

@router.get("/loai-hang", response_model=list[LoaiHangResponse])
def lay_danh_sach_loai_hang():
    """Lấy danh mục các loại hàng hóa (dùng hiển thị dropdown trên giao diện tạo đơn)."""
    return gui_hang_service.lay_danh_sach_loai_hang()


@router.get("/tuyen")
def lay_danh_sach_tuyen():
    """Lấy danh sách các tuyến vận chuyển từ database."""
    return dia_diem_repo.danh_sach_tuyen()


@router.get("/van-phong")
def lay_danh_sach_van_phong():
    """Lấy danh sách các điểm/văn phòng nhận gửi hàng từ database."""
    tat_ca = dia_diem_repo.danh_sach_diem_don_tra()
    return [d for d in tat_ca if d.get("loai") == "van_phong"]


@router.get("/pham-vi")
def lay_pham_vi(nguoi_dung: QuyenNhanVienGuiHang):
    return gui_hang_service.lay_pham_vi(nguoi_dung.id, nguoi_dung.vai_tro)



@router.post("/tao-don", response_model=DonHangResponse, status_code=status.HTTP_201_CREATED)
def tao_don_hang(du_lieu: TaoDonHangRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-23: Nhân viên quầy tạo đơn gửi hàng theo tuyến, tính cước và in biên nhận."""
    return gui_hang_service.tao_don_hang(du_lieu, nhan_vien_id=nguoi_dung.id, vai_tro=nguoi_dung.vai_tro)


# ====================================================================
# 2. Giao hàng cho người nhận (UC-24)
# ====================================================================

@router.post("/giao-hang", response_model=DonHangResponse)
def giao_hang(du_lieu: GiaoHangRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-24: Bàn giao tại quầy sau khi khoản cước cần thu đã được ghi nhận."""
    return gui_hang_service.xac_nhan_giao_hang(
        du_lieu.ma_van_don, nhan_vien_nhan_id=nguoi_dung.id, vai_tro=nguoi_dung.vai_tro
    )


@router.post("/xac-nhan-thu-cod", response_model=DonHangResponse)
def xac_nhan_thu_cod(du_lieu: XacNhanThuCODRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """Ghi nhận tiền COD ở quầy nhận trước khi xác nhận bàn giao."""
    return gui_hang_service.xac_nhan_thu_cod(
        du_lieu.ma_van_don,
        nhan_vien_thu_id=nguoi_dung.id,
        vai_tro=nguoi_dung.vai_tro,
        xac_nhan_da_thu=du_lieu.xac_nhan_da_thu,
    )


# ====================================================================
# 3. Tra cứu Đơn hàng & Đơn gần đây (Public / Khách hàng / Nhân viên)
# ====================================================================

@router.get("/theo-doi/{ma_van_don}", response_model=TheoDoiDonHangResponse)
def theo_doi_cong_khai(
    ma_van_don: str,
    sdt: str = Query(..., min_length=8, max_length=15, description="SĐT người gửi hoặc người nhận để xác minh"),
):
    """Tra cứu mã vận đơn kèm SĐT xác minh; không trả thông tin cá nhân hay thanh toán."""
    return gui_hang_service.tra_cuu_cong_khai(ma_van_don, sdt)


@router.get("/tra-cuu/{ma_van_don}", response_model=DonHangResponse)
@router.get("/don-hang/{ma_van_don}", response_model=DonHangResponse)
def tra_cuu_theo_ma(ma_van_don: str, nguoi_dung: QuyenNhanVienGuiHang):
    """Nhân viên tra cứu chi tiết đơn thuộc văn phòng mình; quản lý xem toàn hệ thống."""
    return gui_hang_service.tra_cuu_theo_ma_van_don(ma_van_don, nguoi_dung.id, nguoi_dung.vai_tro)


@router.get("/tra-cuu-sdt", response_model=list[DonHangResponse])
def tra_cuu_theo_sdt(
    nguoi_dung: QuyenNhanVienGuiHang,
    sdt: str = Query(..., min_length=8, description="Số điện thoại người gửi hoặc người nhận"),
    ten: str = Query(..., min_length=1, description="Tên người gửi hoặc người nhận để xác minh"),
):
    """Tra cứu tại quầy theo SĐT và tên, giới hạn theo văn phòng tài khoản."""
    return gui_hang_service.tra_cuu_theo_sdt(sdt, ten, nguoi_dung.id, nguoi_dung.vai_tro)


@router.get("/don-gan-day", response_model=list[DonHangResponse])
def lay_don_gan_day(
    nguoi_dung: QuyenNhanVienGuiHang,
    limit: int = Query(20, ge=1, le=100),
    diem_gui_id: UUID | None = Query(None),
    trang_thai: str | None = Query(None, description="Lọc theo trạng thái đơn hàng"),
    tu_khoa: str | None = Query(None, description="Tìm kiếm mã vận đơn, người gửi/nhận, SĐT"),
):
    """Lấy danh sách các đơn hàng vừa tạo gần đây tại quầy phục vụ hiển thị tức thì."""
    return gui_hang_service.lay_danh_sach_don_gan_day(
        limit=limit,
        diem_gui_id=str(diem_gui_id) if diem_gui_id else None,
        trang_thai=trang_thai,
        tu_khoa=tu_khoa,
        nguoi_dung_id=nguoi_dung.id,
        vai_tro=nguoi_dung.vai_tro,
    )


# ====================================================================
# 4. Quản lý Hàng tại Văn phòng & Xử lý Hàng chờ lâu (UC-25)
# ====================================================================

@router.get("/diem-nhan/{diem_nhan_id}/cho-lay", response_model=list[DonHangResponse])
def lay_danh_sach_hang_cho_tai_diem(diem_nhan_id: UUID, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-25: Xem danh sách hàng đang chờ lấy / có cờ cảnh báo / quá hạn lưu kho tại văn phòng."""
    return gui_hang_service.lay_danh_sach_hang_cho_tai_diem(
        str(diem_nhan_id), nguoi_dung.id, nguoi_dung.vai_tro
    )


@router.get("/hang-cho-lau", response_model=list[DonHangResponse])
def lay_hang_cho_lau_chung(
    nguoi_dung: QuyenNhanVienGuiHang,
    diem_nhan_id: UUID | None = Query(None),
):
    """UC-25: Xem danh sách hàng chờ lấy / quá hạn tại văn phòng (hoặc toàn bộ nếu không chọn)."""
    target_id = str(diem_nhan_id) if diem_nhan_id else None
    return gui_hang_service.lay_danh_sach_hang_cho_tai_diem(target_id, nguoi_dung.id, nguoi_dung.vai_tro)


@router.put("/{don_hang_id}/lien-he", response_model=DonHangResponse)
@router.post("/hang-cho-lau/{don_hang_id}/lien-he-lai", response_model=DonHangResponse)
def cap_nhat_lien_he(
    nguoi_dung: QuyenNhanVienGuiHang,
    don_hang_id: UUID,
    du_lieu: CapNhatLienHeRequest | None = None,
):
    """UC-25: Ghi nhận đã gọi điện thông báo cho người nhận (đã liên hệ hay chưa)."""
    da_thong_bao = du_lieu.da_thong_bao_nguoi_nhan if du_lieu else True
    return gui_hang_service.cap_nhat_thong_bao_nguoi_nhan(
        str(don_hang_id), da_thong_bao, nguoi_dung.id, nguoi_dung.vai_tro
    )


# ====================================================================
# 5. Hỗ trợ Phụ xe Chất / Dỡ hàng (UC-26, UC-27)
# ====================================================================

@router.get("/tuyen/{tuyen_id}/cho-xep-xe", response_model=list[DonHangResponse])
def lay_danh_sach_cho_xep_xe(tuyen_id: UUID, nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_vai_tro("quan_ly"))):
    """Quản lý có thể xem danh sách chờ theo tuyến trên toàn hệ thống."""
    return gui_hang_service.lay_danh_sach_cho_xep_xe(str(tuyen_id))


@router.post("/{don_hang_id}/chat-hang", response_model=DonHangResponse)
def chat_hang_len_chuyen(don_hang_id: UUID, chuyen_id: UUID, nguoi_dung: QuyenPhuXe):
    """UC-26: Phụ xe xác nhận chất hàng lên chuyến xe."""
    return gui_hang_service.xac_nhan_chat_hang(str(don_hang_id), str(chuyen_id), nguoi_dung.id)


@router.post("/{don_hang_id}/do-hang", response_model=DonHangResponse)
def do_hang_xuong_diem(don_hang_id: UUID, nguoi_dung: QuyenPhuXe):
    """UC-27: Phụ xe xác nhận dỡ hàng xuống điểm nhận."""
    return gui_hang_service.xac_nhan_do_hang(str(don_hang_id), nguoi_dung.id)


# ====================================================================
# 6. Thống kê Hoạt động Gửi hàng (UC-39)
# ====================================================================

@router.get("/thong-ke")
def thong_ke_hang(
    nguoi_dung: QuyenNhanVienGuiHang,
    diem_id: UUID | None = Query(None, description="ID văn phòng cần xem thống kê (nếu để trống sẽ thống kê toàn hệ thống)"),
    so_ngay: int = Query(7, ge=7, le=30, description="Khoảng thời gian biểu đồ: 7, 14 hoặc 30 ngày"),
):
    """UC-39: Nhân viên gửi hàng xem thống kê số lượng đơn và cước phí tại điểm phụ trách."""
    return gui_hang_service.thong_ke_hang_tai_diem(
        str(diem_id) if diem_id else None, nguoi_dung.id, nguoi_dung.vai_tro, so_ngay
    )

