"""Quản lý danh mục nền tảng — UC-29 (khu vực), UC-30 (điểm đón/trả),
UC-31 (tuyến), UC-32 (loại xe), UC-33 (giá vé). Route chỉ mỏng: nhận
request, gọi service, trả response (ARCHITECTURE.md mục 2) — mọi route ở
đây yêu cầu vai_tro = quan_ly.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import yeu_cau_vai_tro
from app.schemas.dia_diem_schema import (
    DiemDonTraRequest,
    DiemDonTraResponse,
    KhuVucRequest,
    KhuVucResponse,
    TaoTuyenRequest,
    TuyenChiTietResponse,
    TuyenResponse,
)
from app.schemas.gia_ve_schema import GiaVeRequest, GiaVeResponse, SuaGiaVeRequest
from app.schemas.ho_so_can_bo_diem_schema import GanVanPhongRequest, NhanVienGuiHangPhanCongResponse
from app.schemas.xe_schema import LoaiXeRequest, LoaiXeResponse
from app.services import ho_so_can_bo_diem_service
from app.services import dia_diem_service as service
from app.services import gia_ve_service
from app.services import xe_service

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


@router.delete("/khu-vuc/{khu_vuc_id}")
def xoa_khu_vuc(khu_vuc_id: UUID):
    service.xoa_khu_vuc(str(khu_vuc_id))
    return {"thong_bao": "Xóa khu vực thành công"}


# ---------------------------------------------------------
# 2. Điểm đón/trả (UC-30)
# ---------------------------------------------------------
@router.post("/diem-don-tra", response_model=DiemDonTraResponse, status_code=201)
def tao_diem_don_tra(du_lieu: DiemDonTraRequest):
    return service.tao_diem_don_tra(
        str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai, du_lieu.sdt_lien_he
    )


@router.put("/diem-don-tra/{diem_id}")
def sua_diem_don_tra(diem_id: UUID, du_lieu: DiemDonTraRequest):
    service.sua_diem_don_tra(
        str(diem_id), str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai, du_lieu.sdt_lien_he
    )
    return {"thong_bao": "Cập nhật điểm đón/trả thành công"}


@router.get("/diem-don-tra", response_model=list[DiemDonTraResponse])
def danh_sach_diem_don_tra(khu_vuc_id: UUID | None = None):
    return service.danh_sach_diem_don_tra(str(khu_vuc_id) if khu_vuc_id else None)


@router.get("/nhan-vien-gui-hang", response_model=list[NhanVienGuiHangPhanCongResponse])
def danh_sach_phan_cong_nhan_vien_gui_hang():
    return ho_so_can_bo_diem_service.danh_sach_nhan_vien_gui_hang()


@router.put("/nhan-vien-gui-hang/{nguoi_dung_id}/van-phong", response_model=NhanVienGuiHangPhanCongResponse)
def gan_van_phong_nhan_vien_gui_hang(nguoi_dung_id: UUID, du_lieu: GanVanPhongRequest):
    return ho_so_can_bo_diem_service.gan_van_phong(str(nguoi_dung_id), str(du_lieu.van_phong_id))


@router.delete("/diem-don-tra/{diem_id}")
def xoa_diem_don_tra(diem_id: UUID):
    service.xoa_diem_don_tra(str(diem_id))
    return {"thong_bao": "Xóa điểm đón/trả thành công"}


# ---------------------------------------------------------
# 3. Tuyến (UC-31) — không còn "nhóm tuyến", 1 tuyến chạy được cả 2 chiều
# ---------------------------------------------------------
@router.post("/tuyen", response_model=TuyenResponse, status_code=201)
def tao_tuyen(du_lieu: TaoTuyenRequest):
    return service.tao_tuyen(
        du_lieu.ten,
        [{"diem_don_tra_id": str(d.diem_don_tra_id), "thoi_gian_du_kien_phut": d.thoi_gian_du_kien_phut} for d in du_lieu.danh_sach_diem],
    )


@router.put("/tuyen/{tuyen_id}")
def sua_tuyen(tuyen_id: UUID, du_lieu: TaoTuyenRequest):
    service.sua_tuyen(
        str(tuyen_id),
        du_lieu.ten,
        [{"diem_don_tra_id": str(d.diem_don_tra_id), "thoi_gian_du_kien_phut": d.thoi_gian_du_kien_phut} for d in du_lieu.danh_sach_diem],
    )
    return {"thong_bao": "Cập nhật tuyến thành công"}


@router.get("/tuyen", response_model=list[TuyenResponse])
def danh_sach_tuyen():
    return service.danh_sach_tuyen()


@router.delete("/tuyen/{tuyen_id}")
def xoa_tuyen(tuyen_id: UUID):
    service.xoa_tuyen(str(tuyen_id))
    return {"thong_bao": "Xóa tuyến thành công"}


@router.get("/tuyen/{tuyen_id}", response_model=TuyenChiTietResponse)
def chi_tiet_tuyen(tuyen_id: UUID):
    return service.lay_chi_tiet_tuyen(str(tuyen_id))


# ---------------------------------------------------------
# 4. Loại xe (UC-32)
# ---------------------------------------------------------
@router.post("/loai-xe", response_model=LoaiXeResponse, status_code=201)
def tao_loai_xe(du_lieu: LoaiXeRequest):
    return xe_service.tao_loai_xe(du_lieu.ten, du_lieu.he_so_gia, [g.model_dump() for g in du_lieu.so_do_ghe])


@router.put("/loai-xe/{loai_xe_id}")
def sua_loai_xe(loai_xe_id: UUID, du_lieu: LoaiXeRequest):
    xe_service.sua_loai_xe(str(loai_xe_id), du_lieu.ten, du_lieu.he_so_gia, [g.model_dump() for g in du_lieu.so_do_ghe])
    return {"thong_bao": "Cập nhật loại xe thành công"}


@router.get("/loai-xe", response_model=list[LoaiXeResponse])
def danh_sach_loai_xe():
    return xe_service.danh_sach_loai_xe()


@router.delete("/loai-xe/{loai_xe_id}")
def xoa_loai_xe(loai_xe_id: UUID):
    xe_service.xoa_loai_xe(str(loai_xe_id))
    return {"thong_bao": "Xóa loại xe thành công"}


# ---------------------------------------------------------
# 5. Giá vé (UC-33)
# ---------------------------------------------------------
@router.post("/gia-ve", response_model=GiaVeResponse, status_code=201)
def tao_gia_ve(du_lieu: GiaVeRequest):
    return gia_ve_service.tao_gia_ve(
        str(du_lieu.tuyen_id),
        str(du_lieu.diem_di_id),
        str(du_lieu.diem_den_id),
        du_lieu.gia_goc,
        du_lieu.ap_dung_tu,
        du_lieu.ap_dung_den,
    )


@router.put("/gia-ve/{gia_ve_id}")
def sua_gia_ve(gia_ve_id: UUID, du_lieu: SuaGiaVeRequest):
    gia_ve_service.sua_gia_ve(str(gia_ve_id), du_lieu.gia_goc, du_lieu.ap_dung_tu, du_lieu.ap_dung_den)
    return {"thong_bao": "Cập nhật giá vé thành công"}


@router.get("/gia-ve", response_model=list[GiaVeResponse])
def danh_sach_gia_ve(tuyen_id: UUID | None = None):
    return gia_ve_service.danh_sach_gia_ve(str(tuyen_id) if tuyen_id else None)


@router.delete("/gia-ve/{gia_ve_id}")
def xoa_gia_ve(gia_ve_id: UUID):
    gia_ve_service.xoa_gia_ve(str(gia_ve_id))
    return {"thong_bao": "Xóa giá vé thành công"}
