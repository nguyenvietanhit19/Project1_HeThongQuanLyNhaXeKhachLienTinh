"""API Router cho phân hệ Gửi hàng — NGHIEP_VU.md mục 10 & mục 8.5.

Route chỉ nhận request, kiểm tra quyền qua dependency yeu_cau_vai_tro,
gọi gui_hang_service và trả response.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.don_hang_schema import (
    CapNhatLienHeRequest,
    DonHangResponse,
    GiaoHangRequest,
    LoaiHangResponse,
    TaoDonHangRequest,
)
from app.services import gui_hang_service

router = APIRouter(prefix="/gui-hang", tags=["gui-hang"])

QuyenNhanVienGuiHang = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_gui_hang", "quan_ly"))
]
QuyenPhuXe = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("phu_xe", "quan_ly"))
]


# ====================================================================
# 1. Danh mục Loại hàng & Tạo đơn (UC-23)
# ====================================================================

@router.get("/loai-hang", response_model=list[LoaiHangResponse])
def lay_danh_sach_loai_hang():
    """Lấy danh mục các loại hàng hóa (dùng hiển thị dropdown trên giao diện tạo đơn)."""
    return gui_hang_service.lay_danh_sach_loai_hang()


@router.post("/tao-don", response_model=DonHangResponse, status_code=status.HTTP_201_CREATED)
def tao_don_hang(du_lieu: TaoDonHangRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-23: Nhân viên quầy tạo đơn gửi hàng theo tuyến, tính cước và in biên nhận."""
    return gui_hang_service.tao_don_hang(du_lieu, nhan_vien_id=nguoi_dung.id)


# ====================================================================
# 2. Giao hàng cho người nhận (UC-24)
# ====================================================================

@router.post("/giao-hang", response_model=DonHangResponse)
def giao_hang(du_lieu: GiaoHangRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-24: Bàn giao hàng cho người nhận tại quầy (thu COD nếu có)."""
    return gui_hang_service.xac_nhan_giao_hang(du_lieu.ma_van_don, nhan_vien_nhan_id=nguoi_dung.id)


# ====================================================================
# 3. Tra cứu Đơn hàng (Public / Khách hàng / Nhân viên)
# ====================================================================

@router.get("/tra-cuu/{ma_van_don}", response_model=DonHangResponse)
def tra_cuu_theo_ma(ma_van_don: str):
    """Tra cứu chi tiết đơn hàng theo mã vận đơn."""
    return gui_hang_service.tra_cuu_theo_ma_van_don(ma_van_don)


@router.get("/tra-cuu-sdt", response_model=list[DonHangResponse])
def tra_cuu_theo_sdt(sdt: str = Query(..., min_length=8, description="Số điện thoại người gửi hoặc người nhận")):
    """Tra cứu các đơn hàng liên quan đến số điện thoại."""
    return gui_hang_service.tra_cuu_theo_sdt(sdt)


# ====================================================================
# 4. Quản lý Hàng tại Văn phòng & Xử lý Hàng chờ lâu (UC-25)
# ====================================================================

@router.get("/diem-nhan/{diem_nhan_id}/cho-lay", response_model=list[DonHangResponse])
def lay_danh_sach_hang_cho_tai_diem(diem_nhan_id: UUID, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-25: Xem danh sách hàng đang chờ lấy / có cờ cảnh báo / quá hạn lưu kho tại văn phòng."""
    return gui_hang_service.lay_danh_sach_hang_cho_tai_diem(str(diem_nhan_id))


@router.put("/{don_hang_id}/lien-he", response_model=DonHangResponse)
def cap_nhat_lien_he(don_hang_id: UUID, du_lieu: CapNhatLienHeRequest, nguoi_dung: QuyenNhanVienGuiHang):
    """UC-25: Ghi nhận đã gọi điện thông báo cho người nhận (đã liên hệ hay chưa)."""
    return gui_hang_service.cap_nhat_thong_bao_nguoi_nhan(str(don_hang_id), du_lieu.da_thong_bao_nguoi_nhan)


# ====================================================================
# 5. Hỗ trợ Phụ xe Chất / Dỡ hàng (UC-26, UC-27)
# ====================================================================

@router.get("/tuyen/{tuyen_id}/cho-xep-xe", response_model=list[DonHangResponse])
def lay_danh_sach_cho_xep_xe(tuyen_id: UUID, nguoi_dung: QuyenPhuXe):
    """UC-26: Phụ xe xem các đơn hàng đang chờ chất lên xe tại tuyến này."""
    return gui_hang_service.lay_danh_sach_cho_xep_xe(str(tuyen_id))


@router.post("/{don_hang_id}/chat-hang", response_model=DonHangResponse)
def chat_hang_len_chuyen(don_hang_id: UUID, chuyen_id: UUID, nguoi_dung: QuyenPhuXe):
    """UC-26: Phụ xe xác nhận chất hàng lên chuyến xe."""
    return gui_hang_service.xac_nhan_chat_hang(str(don_hang_id), str(chuyen_id))


@router.post("/{don_hang_id}/do-hang", response_model=DonHangResponse)
def do_hang_xuong_diem(don_hang_id: UUID, nguoi_dung: QuyenPhuXe):
    """UC-27: Phụ xe xác nhận dỡ hàng xuống điểm nhận."""
    return gui_hang_service.xac_nhan_do_hang(str(don_hang_id))


# ====================================================================
# 6. Thống kê Hoạt động Gửi hàng (UC-39)
# ====================================================================

@router.get("/thong-ke")
def thong_ke_hang(diem_id: UUID = Query(..., description="ID văn phòng cần xem thống kê"), nguoi_dung: QuyenNhanVienGuiHang = None):
    """UC-39: Nhân viên gửi hàng xem thống kê số lượng đơn và cước phí tại điểm phụ trách."""
    return gui_hang_service.thong_ke_hang_tai_diem(str(diem_id))

