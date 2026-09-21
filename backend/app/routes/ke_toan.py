"""Router API cho phân hệ Kế toán & Hoàn tiền — NGHIEP_VU.md mục 7, 8.8.

Cung cấp các API:
- UC-22: Kế toán xem và duyệt chuyển khoản hoàn tiền thủ công
- UC-21: Kích hoạt hoàn tiền tự động khi hủy chuyến vì sự cố khách quan
- UC-39: Báo cáo tài chính doanh thu, số liệu hoàn tiền cho Kế toán
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.hoan_tien_schema import (
    HoanTienChoXuLyItemResponse,
    LichSuHoanTienResponse,
    TaoHoanTienRequest,
    ThongKeKeToanResponse,
    XacNhanChuyenKhoanRequest,
)
from app.services import hoan_tien_service

router = APIRouter(prefix="/ke-toan", tags=["Kế toán & Hoàn tiền"])

KiemTraKeToan = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("ke_toan", "quan_ly"))]
KiemTraDieuDoHoacKeToan = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("ke_toan", "quan_ly", "dieu_do_vien"))
]


# ====================================================================
# 1. UC-22: Danh sách Chờ xử lý & Duyệt Chuyển khoản Thủ công
# ====================================================================

@router.get(
    "/hoan-tien/cho-xu-ly",
    response_model=list[HoanTienChoXuLyItemResponse],
    summary="Danh sách các khoản chờ Kế toán gọi điện và chuyển khoản hoàn tiền (UC-22)",
)
def xem_danh_sach_cho_xu_ly(nguoi_dung: KiemTraKeToan):
    """Kế toán xem toàn bộ các khoản cần chuyển khoản thủ công trên toàn hệ thống."""
    return hoan_tien_service.lay_danh_sach_cho_xu_ly()


@router.post(
    "/hoan-tien/{hoan_tien_id}/duyet",
    response_model=LichSuHoanTienResponse,
    summary="Kế toán xác nhận đã chuyển khoản thành công và lưu vết ngân hàng nhận (UC-22)",
)
def duyet_hoan_tien_thu_cong(
    hoan_tien_id: UUID,
    body: XacNhanChuyenKhoanRequest,
    nguoi_dung: KiemTraKeToan,
):
    """Kế toán nhập thông tin tài khoản ngân hàng của khách và hoàn tất lệnh hoàn tiền."""
    return hoan_tien_service.duyet_hoan_tien_thu_cong(
        hoan_tien_id=str(hoan_tien_id),
        nhan_vien_xu_ly_id=nguoi_dung.id,
        thong_tin_ngan_hang=body.model_dump(),
    )


# ====================================================================
# 2. Tra cứu Lịch sử Hoàn tiền & Tạo Lệnh Hoàn tiền
# ====================================================================

@router.get(
    "/hoan-tien/lich-su",
    response_model=list[LichSuHoanTienResponse],
    summary="Lịch sử hoàn tiền toàn hệ thống có phân trang và bộ lọc",
)
def tra_cuu_lich_su_hoan_tien(
    nguoi_dung: KiemTraKeToan,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    trang_thai: str | None = Query(None, description="Lọc theo cho_xu_ly, da_hoan_tu_dong, da_hoan_chuyen_khoan_thu_cong"),
    tu_ngay: str | None = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    den_ngay: str | None = Query(None, description="Đến ngày (YYYY-MM-DD)"),
):
    """Xem lịch sử các lệnh hoàn tiền đã và đang xử lý."""
    return hoan_tien_service.lay_danh_sach_lich_su(
        limit=limit,
        offset=offset,
        trang_thai=trang_thai,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
    )


@router.post(
    "/hoan-tien/tao-yeu-cau",
    response_model=LichSuHoanTienResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo yêu cầu hoàn tiền cho 1 vé (hỗ trợ hoàn tự động hoặc chờ duyệt)",
)
def tao_yeu_cau_hoan_tien(
    body: TaoHoanTienRequest,
    nguoi_dung: KiemTraKeToan,
):
    """Tạo bản ghi hoàn tiền mới cho một vé cụ thể."""
    return hoan_tien_service.tao_hoan_tien(
        ve_id=str(body.ve_id),
        ly_do=body.ly_do,
        so_tien=body.so_tien,
    )


@router.post(
    "/hoan-tien/su-co-chuyen/{chuyen_id}",
    response_model=list[LichSuHoanTienResponse],
    summary="Kích hoạt hoàn tiền tự động 100% cho các vé khi hủy chuyến vì sự cố khách quan (UC-21)",
)
def hoan_tien_chuyen_bi_huy(
    chuyen_id: UUID,
    nguoi_dung: KiemTraDieuDoHoacKeToan,
):
    """Chuyển toàn bộ vé đã thanh toán sang đã hủy và tạo lệnh hoàn tiền 100% theo UC-21."""
    return hoan_tien_service.xu_ly_hoan_tien_chuyen_bi_huy(str(chuyen_id))


# ====================================================================
# 3. UC-39: Báo cáo Thống kê Doanh thu & Tài chính cho Kế toán
# ====================================================================

@router.get(
    "/thong-ke",
    response_model=ThongKeKeToanResponse,
    summary="Thống kê doanh thu vé, cước gửi hàng, tiền hoàn và doanh thu thuần (UC-39)",
)
def xem_thong_ke_tai_chinh(
    nguoi_dung: KiemTraKeToan,
    tu_ngay: str | None = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    den_ngay: str | None = Query(None, description="Đến ngày (YYYY-MM-DD)"),
):
    """Báo cáo doanh thu thực tế dành cho Kế toán và Quản lý."""
    return hoan_tien_service.thong_ke_doanh_thu_ke_toan(tu_ngay=tu_ngay, den_ngay=den_ngay)

