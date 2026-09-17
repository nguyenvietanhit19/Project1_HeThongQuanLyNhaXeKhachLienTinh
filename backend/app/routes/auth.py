"""Đăng ký/đăng nhập/quên mật khẩu (khách hàng) — UC-01, UC-02, UC-03.

Route chỉ mỏng: nhận request, gọi service, trả response — không viết SQL,
không tự quyết định quy tắc nghiệp vụ (ARCHITECTURE.md mục 2). Không có
try/except ở đây — lỗi nghiệp vụ (GiaTriLoi/KhongDuQuyen/LoiHeThong) được
main.py bắt chung qua exception_handler, đổi thành đúng mã HTTP.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_dang_nhap
from app.schemas.nguoi_dung_schema import (
    DangKyRequest,
    DangNhapRequest,
    DangNhapResponse,
    DatLaiMatKhauRequest,
    DoiMatKhauRequest,
    NguoiDungResponse,
    QuenMatKhauRequest,
    SuaHoSoRequest,
    XacNhanDangKyRequest,
)
from app.services import mat_khau_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/gui-ma-dang-ky")
def gui_ma_dang_ky(du_lieu: DangKyRequest):
    mat_khau_service.gui_ma_dang_ky(du_lieu.email, du_lieu.mat_khau, du_lieu.ho_ten, du_lieu.so_dien_thoai)
    return {"thong_bao": "Mã xác nhận đã gửi về email, có hiệu lực 1 phút"}


@router.post("/dang-ky", status_code=201)
def dang_ky(du_lieu: XacNhanDangKyRequest):
    mat_khau_service.xac_nhan_dang_ky(du_lieu.email, du_lieu.ma_xac_nhan)
    return {"thong_bao": "Đăng ký thành công, vui lòng đăng nhập"}


@router.post("/dang-nhap", response_model=DangNhapResponse)
def dang_nhap(du_lieu: DangNhapRequest):
    return mat_khau_service.dang_nhap(du_lieu.email, du_lieu.mat_khau)


@router.post("/quen-mat-khau")
def quen_mat_khau(du_lieu: QuenMatKhauRequest):
    mat_khau_service.quen_mat_khau(du_lieu.email)
    return {"thong_bao": "Nếu email tồn tại, mã xác nhận sẽ được gửi"}


@router.post("/dat-lai-mat-khau")
def dat_lai_mat_khau(du_lieu: DatLaiMatKhauRequest):
    mat_khau_service.dat_lai_mat_khau(du_lieu.email, du_lieu.ma_xac_nhan, du_lieu.mat_khau_moi)
    return {"thong_bao": "Đổi mật khẩu thành công, vui lòng đăng nhập lại"}


@router.get("/toi", response_model=NguoiDungResponse)
def xem_thong_tin(nguoi_dung: Annotated[NguoiDungHienTai, Depends(yeu_cau_dang_nhap)]):
    return mat_khau_service.lay_thong_tin(nguoi_dung.id)


@router.put("/toi")
def sua_ho_so(du_lieu: SuaHoSoRequest, nguoi_dung: Annotated[NguoiDungHienTai, Depends(yeu_cau_dang_nhap)]):
    mat_khau_service.sua_ho_ten(nguoi_dung.id, du_lieu.ho_ten)
    return {"thong_bao": "Cập nhật thành công"}


@router.put("/doi-mat-khau")
def doi_mat_khau(du_lieu: DoiMatKhauRequest, nguoi_dung: Annotated[NguoiDungHienTai, Depends(yeu_cau_dang_nhap)]):
    mat_khau_service.doi_mat_khau(nguoi_dung.id, du_lieu.mat_khau_cu, du_lieu.mat_khau_moi)
    return {"thong_bao": "Đổi mật khẩu thành công"}
