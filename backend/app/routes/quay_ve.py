from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.quay_ve_schema import BanVeRequest, HuyVeRequest, TaoLinkThanhToanRequest, ThanhToanQuayRequest
from app.services import quay_ve_service as service

router = APIRouter(prefix="/quay-ve", tags=["quay-ve"])
NhanVienQuayVe = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_quay_ve"))]


@router.get("/van-phong-cua-toi")
def van_phong_cua_toi(nguoi_dung: NhanVienQuayVe):
    return service.lay_van_phong(nguoi_dung)


@router.get("/khu-vuc")
def khu_vuc(nguoi_dung: NhanVienQuayVe):
    vp = service.lay_van_phong(nguoi_dung)
    from app.repositories import quay_ve_repository as repo
    return repo.khu_vuc_co_van_phong(str(vp["id"]))


@router.get("/tim-chuyen")
def tim_chuyen(
    nguoi_dung: NhanVienQuayVe,
    diem_di_id: UUID,
    diem_den_id: UUID,
    ngay: date,
):
    return service.tim_chuyen(nguoi_dung, str(diem_di_id), str(diem_den_id), ngay)


@router.get("/chuyen/{chuyen_id}/so-do-ghe")
def so_do_ghe(chuyen_id: UUID, diem_den_id: UUID, diem_tra_id: UUID, nguoi_dung: NhanVienQuayVe):
    return service.so_do_ghe(nguoi_dung, str(chuyen_id), str(diem_den_id), str(diem_tra_id))


@router.get("/chuyen/{chuyen_id}/diem-tra")
def diem_tra(chuyen_id: UUID, diem_den_id: UUID, nguoi_dung: NhanVienQuayVe):
    return service.diem_tra(nguoi_dung, str(chuyen_id), str(diem_den_id))


@router.post("/ban-ve", status_code=201)
def ban_ve(body: BanVeRequest, nguoi_dung: NhanVienQuayVe):
    return service.ban_ve(nguoi_dung, body)


@router.get("/khach-hang")
def tim_khach_hang(nguoi_dung: NhanVienQuayVe, sdt: str = Query(..., min_length=10, max_length=16)):
    return service.tim_khach_hang(sdt)


@router.get("/tra-cuu")
def tra_cuu(
    nguoi_dung: NhanVienQuayVe,
    ma_dat_cho: str | None = Query(None, min_length=4, max_length=32),
    sdt: str | None = Query(None, min_length=10, max_length=16),
):
    return service.tra_cuu(nguoi_dung, ma_dat_cho, sdt)


@router.get("/ve-cho-thanh-toan")
def ve_cho_thanh_toan(
    nguoi_dung: NhanVienQuayVe,
    trang: int = Query(1, ge=1),
    kich_thuoc_trang: int = Query(20, ge=1, le=50),
):
    return service.ve_cho_thanh_toan(nguoi_dung, trang, kich_thuoc_trang)


@router.get("/ve-da-huy")
def ve_da_huy(
    nguoi_dung: NhanVienQuayVe,
    ngay: date,
    trang: int = Query(1, ge=1),
    kich_thuoc_trang: int = Query(20, ge=1, le=50),
):
    return service.ve_da_huy(nguoi_dung, ngay, trang, kich_thuoc_trang)


@router.post("/dat-cho/{ma_dat_cho}/thanh-toan")
def thu_tien(ma_dat_cho: str, body: ThanhToanQuayRequest, nguoi_dung: NhanVienQuayVe):
    return service.thu_tien(nguoi_dung, ma_dat_cho, body.phuong_thuc)


@router.post("/ve/{ve_id}/duong-dan-thanh-toan")
def tao_link_thanh_toan(ve_id: UUID, body: TaoLinkThanhToanRequest, nguoi_dung: NhanVienQuayVe, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")).split(",")[0].strip()
    return {"duong_dan_thanh_toan": service.tao_link_thanh_toan(nguoi_dung, str(ve_id), body.frontend_origin, ip)}


@router.post("/dat-cho/{ma_dat_cho}/duong-dan-thanh-toan")
def tao_link_thanh_toan_dat_cho(ma_dat_cho: str, body: TaoLinkThanhToanRequest,
                                nguoi_dung: NhanVienQuayVe, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")).split(",")[0].strip()
    return {"duong_dan_thanh_toan": service.tao_link_thanh_toan_dat_cho(
        nguoi_dung, ma_dat_cho, body.frontend_origin, ip)}


@router.post("/dat-cho/{ma_dat_cho}/huy")
def huy_dat_cho(ma_dat_cho: str, nguoi_dung: NhanVienQuayVe):
    return service.huy_dat_cho(nguoi_dung, ma_dat_cho)


@router.post("/ve/{ve_id}/huy-hoan-tien")
def huy_ve_hoan_tien(ve_id: UUID, body: HuyVeRequest, nguoi_dung: NhanVienQuayVe):
    return service.huy_ve_hoan_tien(nguoi_dung, str(ve_id), body.ly_do)


@router.get("/hoan-tien")
def tra_cuu_hoan_tien(
    nguoi_dung: NhanVienQuayVe,
    ma_dat_cho: str | None = Query(None, max_length=32),
    sdt: str | None = Query(None, min_length=10, max_length=16),
):
    return service.tra_cuu_hoan_tien(nguoi_dung, ma_dat_cho, sdt)


@router.get("/thong-ke")
def thong_ke(
    nguoi_dung: NhanVienQuayVe,
    tu_ngay: date,
    den_ngay: date,
    ma_ve: str | None = Query(None, max_length=32),
):
    return service.thong_ke(nguoi_dung, tu_ngay, den_ngay, ma_ve)


@router.get("/lich-su-ban-ve")
def lich_su_ban_ve(
    nguoi_dung: NhanVienQuayVe,
    tu_ngay: date,
    den_ngay: date,
    trang: int = Query(1, ge=1),
    kich_thuoc_trang: int = Query(20, ge=1, le=50),
    ma_ve: str | None = Query(None, max_length=32),
):
    return service.lich_su_ban_ve(nguoi_dung, tu_ngay, den_ngay, trang, kich_thuoc_trang, ma_ve)


@router.get("/ve-theo-trang-thai")
def ve_theo_trang_thai(
    nguoi_dung: NhanVienQuayVe,
    trang_thai: Literal["giu_cho", "da_huy"],
    tu_ngay: date,
    den_ngay: date,
    trang: int = Query(1, ge=1),
    kich_thuoc_trang: int = Query(20, ge=1, le=50),
    ma_ve: str | None = Query(None, max_length=32),
):
    return service.ve_theo_trang_thai(nguoi_dung, trang_thai, tu_ngay, den_ngay,
                                     trang, kich_thuoc_trang, ma_ve)


@router.get("/bieu-do-doanh-thu")
def bieu_do_doanh_thu(
    nguoi_dung: NhanVienQuayVe,
    tu_ngay: date,
    den_ngay: date,
    ma_ve: str | None = Query(None, max_length=32),
):
    return service.bieu_do_doanh_thu(nguoi_dung, tu_ngay, den_ngay, ma_ve)


@router.get("/ve/{ve_id}/in")
def du_lieu_in_ve(ve_id: UUID, nguoi_dung: NhanVienQuayVe):
    from app.utils.loi import GiaTriLoi, KhongTimThay
    vp = service.lay_van_phong(nguoi_dung)
    from app.repositories import quay_ve_repository as repo
    ve = repo.ve_va_chuyen(str(ve_id), str(vp["id"]))
    if not ve:
        raise KhongTimThay("Không tìm thấy vé thuộc văn phòng này")
    if ve["trang_thai"] not in ("da_thanh_toan", "da_len_xe", "da_xuong_xe", "khong_den"):
        raise GiaTriLoi("Chỉ được in vé đã thanh toán")
    return ve
