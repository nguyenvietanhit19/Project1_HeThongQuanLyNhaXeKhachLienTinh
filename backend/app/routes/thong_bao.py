"""Thông báo của chính người đang đăng nhập — DATABASE.md mục 6.1.

Route dùng chung cho mọi vai trò (nhân viên gửi hàng đọc nhắc UC-46/UC-28,
quản lý đọc yêu cầu thanh lý hàng tồn UC-25, khách hàng/phụ xe... cũng dùng
được). Mọi truy vấn đều lọc theo id lấy từ token, không nhận id người dùng
từ client.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_dang_nhap
from app.repositories import thong_bao_repository as thong_bao_repo
from app.utils.loi import KhongTimThay

router = APIRouter(prefix="/thong-bao", tags=["thong-bao"])


@router.get("/cua-toi")
def thong_bao_cua_toi(
    nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_dang_nhap),
    chi_chua_doc: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
):
    return {
        "items": thong_bao_repo.danh_sach_cua_toi(nguoi_dung.id, chi_chua_doc, limit),
        "so_chua_doc": thong_bao_repo.dem_chua_doc(nguoi_dung.id),
    }


@router.put("/da-doc-tat-ca")
def danh_dau_tat_ca_da_doc(nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_dang_nhap)):
    return {"so_da_danh_dau": thong_bao_repo.danh_dau_tat_ca_da_doc(nguoi_dung.id)}


@router.put("/{thong_bao_id}/da-doc")
def danh_dau_da_doc(thong_bao_id: UUID, nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_dang_nhap)):
    if not thong_bao_repo.danh_dau_da_doc(str(thong_bao_id), nguoi_dung.id):
        raise KhongTimThay("Không tìm thấy thông báo")
    return {"thong_bao": "Đã đánh dấu đã đọc"}
