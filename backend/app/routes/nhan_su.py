"""Hồ sơ nhân sự vận hành — UC-49 (NGHIEP_VU.md mục 8.9, mục 12). Route chỉ
mỏng: nhận request, gọi service, trả response (ARCHITECTURE.md mục 2).

Dùng chung cho cả quan_ly_nhan_su lẫn quan_ly (NGHIEP_VU.md mục 11: cả 2 vai
trò đều làm được UC-49) — khác quan_ly.py (router đó khóa cứng
vai_tro = quan_ly, không mở cho quan_ly_nhan_su).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.nhan_su_schema import (
    AnhResponse,
    HoSoNhanSuResponse,
    HoSoTomTatResponse,
    SuaHoSoRequest,
    TaiKhoanPhuXeResponse,
    TaoHoSoRequest,
)
from app.services import ho_so_nhan_su_service as service

router = APIRouter(prefix="/quan-ly-nhan-su", tags=["quan-ly-nhan-su"])

# Dùng làm tham số của route: chỉ cho quan_ly_nhan_su và quan_ly gọi API.
# Vai trò khác (khách, tài xế...) bị middleware chặn 403 trước khi vào hàm.
QuyenQuanLyNhanSu = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("quan_ly_nhan_su", "quan_ly"))]


# GET /quan-ly-nhan-su/ho-so?chi_dang_lam=true — danh sách hồ sơ (bản tóm tắt)
@router.get("/ho-so", response_model=list[HoSoTomTatResponse])
def danh_sach_ho_so(nguoi_dung: QuyenQuanLyNhanSu, chi_dang_lam: bool = False):
    return service.danh_sach_ho_so(chi_dang_lam)


# GET /quan-ly-nhan-su/tai-khoan-phu-xe-chua-gan — tài khoản phu_xe chưa có hồ sơ (cho ô chọn)
@router.get("/tai-khoan-phu-xe-chua-gan", response_model=list[TaiKhoanPhuXeResponse])
def tai_khoan_phu_xe_chua_gan(nguoi_dung: QuyenQuanLyNhanSu):
    return service.danh_sach_tai_khoan_phu_xe_chua_gan()


# GET /quan-ly-nhan-su/ho-so/{id} — xem chi tiết 1 hồ sơ kèm giấy tờ
@router.get("/ho-so/{nhan_su_id}", response_model=HoSoNhanSuResponse)
def xem_ho_so(nhan_su_id: UUID, nguoi_dung: QuyenQuanLyNhanSu):
    return service.xem_chi_tiet(str(nhan_su_id))


# POST /quan-ly-nhan-su/ho-so — tạo hồ sơ mới (trả 201)
@router.post("/ho-so", response_model=HoSoNhanSuResponse, status_code=201)
def tao_ho_so(du_lieu: TaoHoSoRequest, nguoi_dung: QuyenQuanLyNhanSu):
    return service.tao_ho_so(nguoi_dung.id, nguoi_dung.vai_tro, du_lieu)


# PUT /quan-ly-nhan-su/ho-so/{id} — sửa hồ sơ / thêm hoặc gia hạn giấy tờ
@router.put("/ho-so/{nhan_su_id}", response_model=HoSoNhanSuResponse)
def sua_ho_so(nhan_su_id: UUID, du_lieu: SuaHoSoRequest, nguoi_dung: QuyenQuanLyNhanSu):
    return service.sua_ho_so(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), du_lieu)


# POST /quan-ly-nhan-su/ho-so/{id}/anh — upload ảnh chân dung (form-data, field "file")
# async vì UploadFile.read() là hàm bất đồng bộ; service bên dưới vẫn là hàm thường.
@router.post("/ho-so/{nhan_su_id}/anh", response_model=AnhResponse)
async def tai_anh_ho_so_len(nhan_su_id: UUID, nguoi_dung: QuyenQuanLyNhanSu, file: UploadFile = File(...)):
    du_lieu = await file.read()
    url = service.cap_nhat_anh_ho_so(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), du_lieu)
    return {"url": url}


# POST /quan-ly-nhan-su/ho-so/{id}/giay-to/{loai}/anh — upload ảnh giấy tờ
# {loai} = bang_lai hoặc giay_kham_suc_khoe
@router.post("/ho-so/{nhan_su_id}/giay-to/{loai}/anh", response_model=AnhResponse)
async def tai_anh_giay_to_len(nhan_su_id: UUID, loai: str, nguoi_dung: QuyenQuanLyNhanSu, file: UploadFile = File(...)):
    du_lieu = await file.read()
    url = service.cap_nhat_anh_giay_to(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), loai, du_lieu)
    return {"url": url}
