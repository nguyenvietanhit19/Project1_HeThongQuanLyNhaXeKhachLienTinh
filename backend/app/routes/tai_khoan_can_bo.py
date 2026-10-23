"""Tạo tài khoản cán bộ — UC-36 (NGHIEP_VU.md mục 8.7 điểm 2, mục 8.9). Route
chỉ mỏng: nhận request, gọi service, trả response (ARCHITECTURE.md mục 2).

Dùng chung cho quan_ly_nhan_su và quan_ly; service quyết định ai tạo được vai
trò nào. Cùng prefix /quan-ly-nhan-su với routes/nhan_su.py (UC-49) nhưng là
router riêng để không đụng file đó.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.tai_khoan_can_bo_schema import (
    TaiKhoanCanBoResponse,
    TaoTaiKhoanCanBoRequest,
    TaoTaiKhoanCanBoResponse,
    VaiTroDuocTaoResponse,
    VanPhongResponse,
)
from app.services import tai_khoan_can_bo_service as service

router = APIRouter(prefix="/quan-ly-nhan-su/tai-khoan", tags=["quan-ly-nhan-su"])

# Chỉ quan_ly_nhan_su và quan_ly gọi được; vai trò khác bị middleware chặn 403.
QuyenQuanLyNhanSu = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("quan_ly_nhan_su", "quan_ly"))]


# GET /quan-ly-nhan-su/tai-khoan?vai_tro=&tu_khoa= — danh sách tài khoản cán bộ
@router.get("", response_model=list[TaiKhoanCanBoResponse])
def danh_sach_tai_khoan(nguoi_dung: QuyenQuanLyNhanSu, vai_tro: str | None = None, tu_khoa: str | None = None):
    return service.danh_sach_tai_khoan(nguoi_dung.vai_tro, vai_tro, tu_khoa)


# GET /quan-ly-nhan-su/tai-khoan/van-phong — văn phòng cho ô chọn
@router.get("/van-phong", response_model=list[VanPhongResponse])
def danh_sach_van_phong(nguoi_dung: QuyenQuanLyNhanSu):
    return service.danh_sach_van_phong()


# GET /quan-ly-nhan-su/tai-khoan/vai-tro-duoc-tao — vai trò người đang đăng nhập được tạo (dựng ô chọn vai trò)
@router.get("/vai-tro-duoc-tao", response_model=VaiTroDuocTaoResponse)
def vai_tro_duoc_tao(nguoi_dung: QuyenQuanLyNhanSu):
    return service.vai_tro_duoc_tao(nguoi_dung.id, nguoi_dung.vai_tro)


# POST /quan-ly-nhan-su/tai-khoan — tạo tài khoản cán bộ (trả 201)
@router.post("", response_model=TaoTaiKhoanCanBoResponse, status_code=201)
def tao_tai_khoan(du_lieu: TaoTaiKhoanCanBoRequest, nguoi_dung: QuyenQuanLyNhanSu):
    return service.tao_tai_khoan(nguoi_dung.id, nguoi_dung.vai_tro, du_lieu)
