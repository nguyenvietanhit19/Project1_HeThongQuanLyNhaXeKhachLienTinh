"""Quản lý danh mục nền tảng — UC-29 (khu vực), UC-30 (điểm đón/trả),
UC-31 (tuyến). Route chỉ mỏng: nhận request, gọi service, trả response
(ARCHITECTURE.md mục 2) — mọi route ở đây yêu cầu vai_tro = quan_ly.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import yeu_cau_vai_tro
from app.schemas.dia_diem_schema import (
    DiemDonTraRequest,
    DiemDonTraResponse,
    KhuVucRequest,
    KhuVucResponse,
    NhomTuyenResponse,
    TaoTuyenRequest,
    TuyenChiTietResponse,
    TuyenResponse,
)
from app.services import dia_diem_service as service

router = APIRouter(prefix="/quan-ly", tags=["quan-ly"], dependencies=[Depends(yeu_cau_vai_tro("quan_ly"))])


# ---------------------------------------------------------
# 1. Khu vực (UC-29)
# ---------------------------------------------------------
@router.post("/khu-vuc", response_model=KhuVucResponse, status_code=201)
def tao_khu_vuc(du_lieu: KhuVucRequest):
    return service.tao_khu_vuc(du_lieu.ten, du_lieu.tinh_thanh)


@router.put("/khu-vuc/{khu_vuc_id}")
def sua_khu_vuc(khu_vuc_id: UUID, du_lieu: KhuVucRequest):
    service.sua_khu_vuc(str(khu_vuc_id), du_lieu.ten, du_lieu.tinh_thanh)
    return {"thong_bao": "Cập nhật khu vực thành công"}


@router.get("/khu-vuc", response_model=list[KhuVucResponse])
def danh_sach_khu_vuc():
    return service.danh_sach_khu_vuc()


# ---------------------------------------------------------
# 2. Điểm đón/trả (UC-30)
# ---------------------------------------------------------
@router.post("/diem-don-tra", response_model=DiemDonTraResponse, status_code=201)
def tao_diem_don_tra(du_lieu: DiemDonTraRequest):
    return service.tao_diem_don_tra(str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai)


@router.put("/diem-don-tra/{diem_id}")
def sua_diem_don_tra(diem_id: UUID, du_lieu: DiemDonTraRequest):
    service.sua_diem_don_tra(str(diem_id), str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai)
    return {"thong_bao": "Cập nhật điểm đón/trả thành công"}


@router.get("/diem-don-tra", response_model=list[DiemDonTraResponse])
def danh_sach_diem_don_tra(khu_vuc_id: UUID | None = None):
    return service.danh_sach_diem_don_tra(str(khu_vuc_id) if khu_vuc_id else None)


# ---------------------------------------------------------
# 3. Tuyến (UC-31)
# ---------------------------------------------------------
@router.get("/nhom-tuyen", response_model=list[NhomTuyenResponse])
def danh_sach_nhom_tuyen():
    return service.danh_sach_nhom_tuyen()


@router.post("/tuyen", response_model=TuyenResponse, status_code=201)
def tao_tuyen(du_lieu: TaoTuyenRequest):
    return service.tao_tuyen(
        du_lieu.ten,
        str(du_lieu.nhom_tuyen_id) if du_lieu.nhom_tuyen_id else None,
        du_lieu.ten_nhom_tuyen_moi,
        [{"diem_don_tra_id": str(d.diem_don_tra_id), "thoi_gian_du_kien_phut": d.thoi_gian_du_kien_phut} for d in du_lieu.danh_sach_diem],
    )


@router.get("/tuyen", response_model=list[TuyenResponse])
def danh_sach_tuyen():
    return service.danh_sach_tuyen()


@router.get("/tuyen/{tuyen_id}", response_model=TuyenChiTietResponse)
def chi_tiet_tuyen(tuyen_id: UUID):
    return service.lay_chi_tiet_tuyen(str(tuyen_id))
