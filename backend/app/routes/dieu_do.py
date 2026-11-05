"""Điều độ viên gán xe theo chu trình (UC-44) — DIEU_DO_VIEN_THIET_KE_MOI.md. Route chỉ mỏng: nhận request, gọi service,
trả response (ARCHITECTURE.md mục 2). Điều độ viên bị giới hạn ở các tuyến được phân công; quản lý thay được mọi tuyến."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.dieu_do_schema import (
    ChuTrinhResponse,
    GanXeRequest,
    LoaiXeChiTietResponse,
    LoTrinhChuTrinhResponse,
    TuyenPhuTrachResponse,
    XeChoChuTrinhResponse,
)
from app.services import dieu_do_service

router = APIRouter(prefix="/dieu-do", tags=["dieu-do"])

NguoiGan = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("dieu_do_vien", "quan_ly"))]


@router.get("/tuyen", response_model=list[TuyenPhuTrachResponse])
def danh_sach_tuyen_phu_trach(nguoi_dung: NguoiGan):
    return dieu_do_service.danh_sach_tuyen_phu_trach(nguoi_dung)


@router.get("/chu-trinh", response_model=list[ChuTrinhResponse])
def danh_sach_chu_trinh(nguoi_dung: NguoiGan, so_ngay: int = dieu_do_service.CUA_SO_MAC_DINH_NGAY):
    return dieu_do_service.danh_sach_chu_trinh(nguoi_dung, so_ngay)


@router.get("/chu-trinh/{chu_trinh_id}/lo-trinh", response_model=LoTrinhChuTrinhResponse)
def lo_trinh_chu_trinh(chu_trinh_id: UUID, nguoi_dung: NguoiGan):
    return dieu_do_service.chi_tiet_chu_trinh(nguoi_dung, str(chu_trinh_id))


@router.get("/loai-xe/{loai_xe_id}", response_model=LoaiXeChiTietResponse)
def chi_tiet_loai_xe(loai_xe_id: UUID, nguoi_dung: NguoiGan):
    return dieu_do_service.chi_tiet_loai_xe(str(loai_xe_id))


@router.get("/chu-trinh/{chu_trinh_id}/xe", response_model=list[XeChoChuTrinhResponse])
def danh_sach_xe_cho_chu_trinh(chu_trinh_id: UUID, nguoi_dung: NguoiGan):
    return dieu_do_service.danh_sach_xe_cho_chu_trinh(nguoi_dung, str(chu_trinh_id))


@router.put("/chu-trinh/{chu_trinh_id}/xe", response_model=ChuTrinhResponse)
def gan_xe(chu_trinh_id: UUID, du_lieu: GanXeRequest, nguoi_dung: NguoiGan):
    return dieu_do_service.gan_xe(nguoi_dung, str(chu_trinh_id), str(du_lieu.xe_id))
