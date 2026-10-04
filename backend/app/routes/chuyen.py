"""Tra cứu chuyến công khai (UC-04) — KHÔNG cần đăng nhập, NGHIEP_VU.md mục 3.4/8.1.

Route mỏng, chỉ gọi service. Không có thông tin cá nhân của khách trong bất kỳ response nào.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter

from app.schemas.tim_kiem_chuyen_schema import ChuyenChiTiet, ChuyenTimThay, KhuVucCongKhai
from app.services import tim_kiem_chuyen_service as service

router = APIRouter(prefix="/chuyen", tags=["chuyen"])


@router.get("/khu-vuc", response_model=list[KhuVucCongKhai])
def danh_sach_khu_vuc():
    return service.danh_sach_khu_vuc()


@router.get("/tim-kiem", response_model=list[ChuyenTimThay])
def tim_chuyen(diem_di_id: UUID, diem_den_id: UUID, ngay: date):
    return service.tim_chuyen(str(diem_di_id), str(diem_den_id), ngay)


@router.get("/{chuyen_id}/so-do-ghe", response_model=ChuyenChiTiet)
def so_do_ghe(chuyen_id: UUID, diem_di_id: UUID, diem_den_id: UUID):
    return service.so_do_ghe_chuyen(str(chuyen_id), str(diem_di_id), str(diem_den_id))
