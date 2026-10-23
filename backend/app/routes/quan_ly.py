"""Quản lý danh mục nền tảng — UC-29 (khu vực), UC-30 (điểm đón/trả),
UC-31 (tuyến), UC-32 (loại xe), UC-33 (giá vé), UC-34 (xe), UC-35 (biên chế
xe), UC-18 (lịch chạy định kỳ). Route chỉ mỏng: nhận request, gọi service,
trả response (ARCHITECTURE.md mục 2) — mọi route ở đây yêu cầu vai_tro = quan_ly.
"""

from datetime import date, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import yeu_cau_vai_tro
from app.schemas.chuyen_quan_ly_schema import ChuyenQuanLyResponse, SuaGioChuyenRequest
from app.schemas.don_hang_schema import GanVanPhongCanBoRequest
from app.schemas.dia_diem_schema import (
    DiemDonTraRequest,
    DiemDonTraResponse,
    KhuVucRequest,
    KhuVucResponse,
    TaoTuyenRequest,
    TuyenChiTietResponse,
    TuyenResponse,
)
from app.schemas.gia_ve_schema import (
    BoGiaRequest,
    BoGiaResponse,
    SuaBoGiaRequest,
    XemTruocBoGiaResponse,
    XemTruocSuaBoGiaRequest,
)
from app.schemas.lich_chay_schema import (
    CapLichChayResponse,
    DoiApDungRequest,
    DoiHeSoGiaRequest,
    SinhChuyenRequest,
    SinhChuyenResponse,
    SuaLichChayRequest,
    TaoCapLichChayRequest,
    XemTruocCapResponse,
)
from app.schemas.xe_schema import (
    BienCheItem,
    LoaiXeRequest,
    LoaiXeResponse,
    NhanSuKhaDung,
    ThemBienCheRequest,
    XeRequest,
    XeResponse,
)
from app.services import bien_che_service
from app.services import chuyen_service
from app.services import dia_diem_service as service
from app.services import gia_ve_service
from app.services import gui_hang_service
from app.services import lich_chay_service
from app.services import xe_service

router = APIRouter(prefix="/quan-ly", tags=["quan-ly"], dependencies=[Depends(yeu_cau_vai_tro("quan_ly"))])


@router.put("/ho-so-can-bo-diem/{nguoi_dung_id}")
def gan_van_phong_can_bo(nguoi_dung_id: UUID, du_lieu: GanVanPhongCanBoRequest):
    """Gán/cập nhật văn phòng cho nhân viên quầy vé hoặc gửi hàng (điều độ viên không gắn văn phòng)."""
    gui_hang_service.gan_van_phong_can_bo(str(nguoi_dung_id), str(du_lieu.van_phong_id))
    return {"thong_bao": "Đã gán văn phòng phụ trách"}


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
    return service.tao_diem_don_tra(str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai)


@router.put("/diem-don-tra/{diem_id}")
def sua_diem_don_tra(diem_id: UUID, du_lieu: DiemDonTraRequest):
    service.sua_diem_don_tra(str(diem_id), str(du_lieu.khu_vuc_id), du_lieu.ten, du_lieu.dia_chi, du_lieu.loai)
    return {"thong_bao": "Cập nhật điểm đón/trả thành công"}


@router.get("/diem-don-tra", response_model=list[DiemDonTraResponse])
def danh_sach_diem_don_tra(khu_vuc_id: UUID | None = None):
    return service.danh_sach_diem_don_tra(str(khu_vuc_id) if khu_vuc_id else None)


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
    return xe_service.tao_loai_xe(du_lieu.ten, [g.model_dump() for g in du_lieu.so_do_ghe], du_lieu.he_so_ghe)


@router.put("/loai-xe/{loai_xe_id}")
def sua_loai_xe(loai_xe_id: UUID, du_lieu: LoaiXeRequest):
    xe_service.sua_loai_xe(
        str(loai_xe_id), du_lieu.ten, [g.model_dump() for g in du_lieu.so_do_ghe], du_lieu.he_so_ghe, du_lieu.phien_ban
    )
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
@router.get("/bo-gia", response_model=list[BoGiaResponse])
def danh_sach_bo_gia(tuyen_id: UUID | None = None):
    return gia_ve_service.danh_sach_bo(str(tuyen_id) if tuyen_id else None)


@router.post("/bo-gia", response_model=BoGiaResponse, status_code=201)
def tao_bo_gia(du_lieu: BoGiaRequest):
    return gia_ve_service.tao_bo(
        str(du_lieu.tuyen_id), du_lieu.ap_dung_tu, du_lieu.ap_dung_den, [g.model_dump() for g in du_lieu.danh_sach_gia], du_lieu.xac_nhan_canh_bao
    )


@router.post("/bo-gia/xem-truoc", response_model=XemTruocBoGiaResponse)
def xem_truoc_tao_bo_gia(du_lieu: BoGiaRequest):
    return gia_ve_service.xem_truoc_tao_bo(
        str(du_lieu.tuyen_id), du_lieu.ap_dung_tu, du_lieu.ap_dung_den, [g.model_dump() for g in du_lieu.danh_sach_gia]
    )


@router.put("/bo-gia/{bo_gia_id}", response_model=BoGiaResponse)
def sua_bo_gia(bo_gia_id: UUID, du_lieu: SuaBoGiaRequest):
    return gia_ve_service.sua_bo(
        str(bo_gia_id), du_lieu.ap_dung_tu, du_lieu.ap_dung_den, [g.model_dump() for g in du_lieu.danh_sach_gia], du_lieu.xac_nhan_canh_bao
    )


@router.post("/bo-gia/{bo_gia_id}/xem-truoc", response_model=XemTruocBoGiaResponse)
def xem_truoc_sua_bo_gia(bo_gia_id: UUID, du_lieu: XemTruocSuaBoGiaRequest):
    return gia_ve_service.xem_truoc_sua_bo(
        str(bo_gia_id), du_lieu.ap_dung_tu, du_lieu.ap_dung_den, [g.model_dump() for g in du_lieu.danh_sach_gia]
    )


@router.delete("/bo-gia/{bo_gia_id}")
def xoa_bo_gia(bo_gia_id: UUID):
    gia_ve_service.xoa_bo(str(bo_gia_id))
    return {"thong_bao": "Xóa bộ giá vé thành công"}


# ---------------------------------------------------------
# 6. Xe (UC-34)
# ---------------------------------------------------------
@router.post("/xe", response_model=XeResponse, status_code=201)
def tao_xe(du_lieu: XeRequest):
    return xe_service.tao_xe(
        du_lieu.bien_so,
        str(du_lieu.loai_xe_id),
        str(du_lieu.diem_goc_id),
        str(du_lieu.tuyen_id) if du_lieu.tuyen_id else None,
        du_lieu.trang_thai,
    )


@router.put("/xe/{xe_id}", response_model=XeResponse)
def sua_xe(xe_id: UUID, du_lieu: XeRequest):
    return xe_service.sua_xe(
        str(xe_id),
        du_lieu.bien_so,
        str(du_lieu.loai_xe_id),
        str(du_lieu.diem_goc_id),
        str(du_lieu.tuyen_id) if du_lieu.tuyen_id else None,
        du_lieu.trang_thai,
    )


@router.get("/xe", response_model=list[XeResponse])
def danh_sach_xe():
    return xe_service.danh_sach_xe()


@router.delete("/xe/{xe_id}")
def xoa_xe(xe_id: UUID):
    xe_service.xoa_xe(str(xe_id))
    return {"thong_bao": "Xóa xe thành công"}


# ---------------------------------------------------------
# 7. Biên chế cố định của xe (UC-35)
# ---------------------------------------------------------
@router.get("/nhan-su-dang-lam", response_model=list[NhanSuKhaDung])
def danh_sach_nhan_su_dang_lam():
    return bien_che_service.danh_sach_nhan_su_dang_lam()


@router.get("/xe/{xe_id}/bien-che", response_model=list[BienCheItem])
def lay_bien_che_xe(xe_id: UUID):
    return bien_che_service.lay_bien_che(str(xe_id))


@router.post("/xe/{xe_id}/bien-che", response_model=list[BienCheItem], status_code=201)
def them_bien_che_xe(xe_id: UUID, du_lieu: ThemBienCheRequest):
    return bien_che_service.them_bien_che_co_dinh(str(xe_id), str(du_lieu.nhan_su_van_hanh_id))


@router.delete("/bien-che/{xe_nhan_su_id}", response_model=list[BienCheItem])
def go_bien_che(xe_nhan_su_id: UUID):
    return bien_che_service.go_bien_che_co_dinh(str(xe_nhan_su_id))


# ---------------------------------------------------------
# 8. Lịch chạy định kỳ (UC-18)
# ---------------------------------------------------------
@router.post("/lich-chay", response_model=CapLichChayResponse, status_code=201)
def tao_cap_lich_chay(du_lieu: TaoCapLichChayRequest):
    return lich_chay_service.tao_cap_lich_chay(
        str(du_lieu.tuyen_id),
        {"gio_khoi_hanh": du_lieu.gio_xuoi, "loai_xe_id": str(du_lieu.loai_xe_id)},
        {"gio_khoi_hanh": du_lieu.gio_nguoc, "loai_xe_id": str(du_lieu.loai_xe_id)},
        du_lieu.he_so_gia,
    )


@router.get("/lich-chay/xem-truoc", response_model=XemTruocCapResponse)
def xem_truoc_cap_lich_chay(tuyen_id: UUID, gio_xuoi: time, gio_nguoc: time):
    return lich_chay_service.xem_truoc_cap(str(tuyen_id), gio_xuoi, gio_nguoc)


@router.put("/lich-chay/{lich_id}", response_model=CapLichChayResponse)
def sua_lich_chay(lich_id: UUID, du_lieu: SuaLichChayRequest):
    return lich_chay_service.sua_lich_chay(str(lich_id), du_lieu.gio_khoi_hanh, str(du_lieu.loai_xe_id))


@router.patch("/lich-chay/cap/{cap_id}/he-so-gia", response_model=CapLichChayResponse)
def doi_he_so_gia_cap_lich_chay(cap_id: UUID, du_lieu: DoiHeSoGiaRequest):
    return lich_chay_service.doi_he_so_gia_cap(str(cap_id), du_lieu.he_so_gia)


@router.patch("/lich-chay/cap/{cap_id}/ap-dung", response_model=CapLichChayResponse)
def doi_ap_dung_cap_lich_chay(cap_id: UUID, du_lieu: DoiApDungRequest):
    return lich_chay_service.doi_ap_dung_cap(str(cap_id), du_lieu.dang_ap_dung)


@router.get("/lich-chay", response_model=list[CapLichChayResponse])
def danh_sach_cap_lich_chay(tuyen_id: UUID | None = None):
    return lich_chay_service.danh_sach_cap(str(tuyen_id) if tuyen_id else None)


@router.delete("/lich-chay/cap/{cap_id}")
def xoa_cap_lich_chay(cap_id: UUID):
    lich_chay_service.xoa_cap(str(cap_id))
    return {"thong_bao": "Xóa cặp lịch chạy thành công"}


@router.post("/lich-chay/sinh-chuyen", response_model=SinhChuyenResponse)
def sinh_chuyen(du_lieu: SinhChuyenRequest):
    return lich_chay_service.sinh_chuyen_cho_cac_cap([str(c) for c in du_lieu.cap_ids], du_lieu.tu_ngay, du_lieu.den_ngay)


# ---------------------------------------------------------
# 10. Chuyến (UC-18) — xem/lọc/sửa/xóa chuyến đã sinh, từ góc nhìn quản lý
# ---------------------------------------------------------
@router.get("/chuyen", response_model=list[ChuyenQuanLyResponse])
def danh_sach_chuyen(
    tuyen_id: UUID | None = None,
    chieu: Literal["xuoi", "nguoc"] | None = None,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    trang_thai: Literal["chua_khoi_hanh", "dang_chay", "gap_su_co", "hoan_thanh", "da_huy"] | None = None,
    da_gan_xe: bool | None = None,
    lich_chay_id: UUID | None = None,
):
    return chuyen_service.danh_sach_chuyen(
        str(tuyen_id) if tuyen_id else None, chieu, tu_ngay, den_ngay, trang_thai, da_gan_xe,
        str(lich_chay_id) if lich_chay_id else None,
    )


@router.get("/chuyen/{chuyen_id}", response_model=ChuyenQuanLyResponse)
def chi_tiet_chuyen(chuyen_id: UUID):
    return chuyen_service.chi_tiet_chuyen(str(chuyen_id))


@router.put("/chuyen/{chuyen_id}", response_model=ChuyenQuanLyResponse)
def sua_gio_chuyen(chuyen_id: UUID, du_lieu: SuaGioChuyenRequest):
    return chuyen_service.sua_gio_chuyen(str(chuyen_id), du_lieu.gio)


@router.delete("/chuyen/{chuyen_id}")
def xoa_chuyen(chuyen_id: UUID):
    chuyen_service.xoa_chuyen(str(chuyen_id))
    return {"thong_bao": "Xóa chuyến thành công"}
