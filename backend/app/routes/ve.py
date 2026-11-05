"""Đặt vé online của khách hàng (UC-05, UC-08) — NGHIEP_VU.md mục 3.4, 6. Cần đăng nhập, chỉ vai trò khách hàng.

Route mỏng, chỉ gọi service. Khách chỉ thấy/sửa được lượt đặt chỗ của chính mình.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.ve_schema import (
    BoGheRequest,
    DatChoResponse,
    DuongDanThanhToanRequest,
    DuongDanThanhToanResponse,
    GiuChoRequest,
    HuyDatChoResponse,
    HuyVeResponse,
    LichSuDatChoResponse,
    ThanhToanRequest,
)
from app.services import dat_ve_service as service

router = APIRouter(prefix="/ve", tags=["ve"])

KhachHang = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("khach_hang"))]


@router.post("/giu-cho", response_model=DatChoResponse)
def giu_cho(body: GiuChoRequest, nguoi_dung: KhachHang):
    return service.giu_cho(
        nguoi_dung.id, str(body.chuyen_id), str(body.diem_di_id), str(body.diem_den_id), body.danh_sach_ghe,
        str(body.diem_don_id), str(body.diem_tra_id),
    )


@router.get("/gio-hang", response_model=list[DatChoResponse])
def gio_hang(nguoi_dung: KhachHang):
    return service.gio_hang(nguoi_dung.id)


@router.get("/lich-su", response_model=list[LichSuDatChoResponse])
def lich_su(nguoi_dung: KhachHang):
    return service.lich_su(nguoi_dung.id)


@router.get("/dat-cho/{ma_dat_cho}", response_model=DatChoResponse)
def xem_dat_cho(ma_dat_cho: str, nguoi_dung: KhachHang):
    return service.xem_dat_cho(nguoi_dung.id, ma_dat_cho)


@router.post("/dat-cho/{ma_dat_cho}/bo-ghe", response_model=DatChoResponse)
def bo_ghe(ma_dat_cho: str, body: BoGheRequest, nguoi_dung: KhachHang):
    return service.bo_ghe(nguoi_dung.id, ma_dat_cho, body.so_ghe)


@router.post("/dat-cho/{ma_dat_cho}/thanh-toan", response_model=DatChoResponse)
def thanh_toan(ma_dat_cho: str, body: ThanhToanRequest, nguoi_dung: KhachHang):
    return service.thanh_toan(nguoi_dung.id, ma_dat_cho, body.danh_sach_ghe, body.loai_hinh)


@router.post("/dat-cho/{ma_dat_cho}/duong-dan-thanh-toan", response_model=DuongDanThanhToanResponse)
def duong_dan_thanh_toan(ma_dat_cho: str, body: DuongDanThanhToanRequest, nguoi_dung: KhachHang, request: Request):
    # Sau proxy (Render) IP thật của khách nằm ở X-Forwarded-For; cổng thanh toán yêu cầu gửi kèm IP khách
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")).split(",")[0].strip()
    return {"duong_dan_thanh_toan": service.tao_duong_dan_thanh_toan(nguoi_dung.id, ma_dat_cho, body.frontend_origin, ip)}


@router.post("/{ve_id}/huy", response_model=HuyVeResponse)
def huy_ve(ve_id: UUID, nguoi_dung: KhachHang):
    return service.huy_ve(nguoi_dung.id, str(ve_id))


@router.post("/{ve_id}/duong-dan-thanh-toan", response_model=DuongDanThanhToanResponse)
def duong_dan_thanh_toan_ve(ve_id: UUID, body: DuongDanThanhToanRequest, nguoi_dung: KhachHang, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")).split(",")[0].strip()
    return {"duong_dan_thanh_toan": service.tao_duong_dan_thanh_toan_ve(nguoi_dung.id, str(ve_id), body.frontend_origin, ip)}


@router.post("/dat-cho/{ma_dat_cho}/huy", response_model=HuyDatChoResponse)
def huy_dat_cho(ma_dat_cho: str, nguoi_dung: KhachHang):
    return service.huy_dat_cho(nguoi_dung.id, ma_dat_cho)
