"""Xem nhật ký thao tác — UC-52 (NGHIEP_VU.md UC-52). Route chỉ mỏng: nhận request, gọi service, trả response
(ARCHITECTURE.md mục 2).

Dùng chung cho quan_ly_nhan_su (chỉ thấy dòng của mình) và quan_ly (thấy toàn bộ) — service ép phạm vi theo vai
trò. Cùng prefix /quan-ly-nhan-su với routes/nhan_su.py nhưng là router riêng để không đụng file đó.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.nhat_ky_schema import NhatKyTrangResponse, TuyChonLocResponse
from app.services import nhat_ky_service as service

router = APIRouter(prefix="/quan-ly-nhan-su/nhat-ky", tags=["quan-ly-nhan-su"])

QuyenQuanLyNhanSu = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("quan_ly_nhan_su", "quan_ly"))]


# GET /quan-ly-nhan-su/nhat-ky?tu_ngay=&den_ngay=&hanh_dong=&doi_tuong_loai=&nguoi_id=&trang=&so_dong=
@router.get("", response_model=NhatKyTrangResponse)
def xem_nhat_ky(
    nguoi_dung: QuyenQuanLyNhanSu,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    hanh_dong: Annotated[str | None, Query(max_length=64)] = None,
    doi_tuong_loai: Annotated[str | None, Query(max_length=64)] = None,
    nguoi_id: UUID | None = None,  # chỉ quan_ly có tác dụng; quan_ly_nhan_su gửi gì cũng bị bỏ qua
    trang: Annotated[int, Query(ge=1)] = 1,
    so_dong: Annotated[int, Query(ge=1, le=service.SO_DONG_TOI_DA)] = service.SO_DONG_MAC_DINH,
):
    return service.xem_nhat_ky(
        nguoi_dung.id, nguoi_dung.vai_tro, tu_ngay, den_ngay, hanh_dong, doi_tuong_loai,
        str(nguoi_id) if nguoi_id else None, trang, so_dong,
    )


# GET /quan-ly-nhan-su/nhat-ky/tuy-chon-loc — dữ liệu đổ các ô lọc
@router.get("/tuy-chon-loc", response_model=TuyChonLocResponse)
def tuy_chon_loc(nguoi_dung: QuyenQuanLyNhanSu):
    return service.tuy_chon_loc(nguoi_dung.id, nguoi_dung.vai_tro)
