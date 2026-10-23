"""Phân công điều độ viên phụ trách tuyến (trang Tuyến của quản lý) — DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md mục 3.2. Route chỉ mỏng:
nhận request, gọi service, trả response (ARCHITECTURE.md mục 2). Chỉ `quan_ly` gọi được — tuyến là danh mục của quản lý."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import yeu_cau_vai_tro
from app.schemas.phan_cong_dieu_do_schema import DatPhanCongRequest, DieuDoVienChonResponse, PhanCongTuyenResponse
from app.services import phan_cong_dieu_do_service as service

router = APIRouter(prefix="/quan-ly", tags=["phan-cong-dieu-do"], dependencies=[Depends(yeu_cau_vai_tro("quan_ly"))])


@router.get("/dieu-do-vien", response_model=list[DieuDoVienChonResponse])
def danh_sach_dieu_do_vien():
    return service.danh_sach_dieu_do_vien()


@router.get("/phan-cong-dieu-do", response_model=list[PhanCongTuyenResponse])
def danh_sach_phan_cong():
    return service.danh_sach_phan_cong()


@router.put("/phan-cong-dieu-do/{tuyen_id}", response_model=PhanCongTuyenResponse)
def dat_phan_cong(tuyen_id: UUID, du_lieu: DatPhanCongRequest):
    return service.dat_phan_cong(str(tuyen_id), [str(i) for i in du_lieu.nguoi_dung_ids])
