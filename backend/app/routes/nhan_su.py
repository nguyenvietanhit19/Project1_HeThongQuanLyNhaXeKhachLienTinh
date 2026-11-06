"""Hồ sơ nhân sự vận hành — UC-49 (NGHIEP_VU.md mục 8.9, mục 12). Route chỉ
mỏng: nhận request, gọi service, trả response (ARCHITECTURE.md mục 2).

CHỈ quan_ly_nhan_su (UC-49, UC-51): từ 6/11/2026 quan_ly không còn làm hồ sơ tài xế / phụ xe và cho nghỉ việc
(NGHIEP_VU.md mục 8.9; KE_HOACH_PHAN_QUYEN_QUAN_LY.md) — khác quan_ly.py (router đó khóa cứng vai_tro = quan_ly).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.nhan_su_schema import (
    AnhResponse,
    ChoNghiViecRequest,
    ChoNghiViecResponse,
    HoSoNhanSuResponse,
    HoSoTomTatResponse,
    LoaiGiayTo,
    SuaHoSoRequest,
    HoSoPhuXeChuaCoTaiKhoanResponse,
    TaoHoSoRequest,
    XemTruocNghiViecResponse,
)
from app.services import ho_so_nhan_su_service as service
from app.utils.kiem_tra_anh import KICH_THUOC_TOI_DA_BYTE

router = APIRouter(prefix="/quan-ly-nhan-su", tags=["quan-ly-nhan-su"])

# Dùng làm tham số của route: chỉ cho quan_ly_nhan_su gọi API.
# Vai trò khác (kể cả quan_ly, khách, tài xế...) bị middleware chặn 403 trước khi vào hàm.
QuyenQuanLyNhanSu = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("quan_ly_nhan_su"))]


# GET /quan-ly-nhan-su/ho-so?chi_dang_lam=true — danh sách hồ sơ (bản tóm tắt)
@router.get("/ho-so", response_model=list[HoSoTomTatResponse])
def danh_sach_ho_so(nguoi_dung: QuyenQuanLyNhanSu, chi_dang_lam: bool = False):
    return service.danh_sach_ho_so(chi_dang_lam)


# GET /quan-ly-nhan-su/ho-so-phu-xe-chua-co-tai-khoan — hồ sơ phụ xe đang làm chưa có tài khoản (cho ô chọn khi tạo tài khoản phụ xe)
@router.get("/ho-so-phu-xe-chua-co-tai-khoan", response_model=list[HoSoPhuXeChuaCoTaiKhoanResponse])
def ho_so_phu_xe_chua_co_tai_khoan(nguoi_dung: QuyenQuanLyNhanSu):
    return service.danh_sach_ho_so_phu_xe_chua_co_tai_khoan()


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
    # Chỉ đọc tối đa 5MB + 1 byte: file lớn hơn vẫn bị service báo "quá lớn" mà không nạp cả file khổng lồ vào bộ nhớ.
    du_lieu = await file.read(KICH_THUOC_TOI_DA_BYTE + 1)
    url = service.cap_nhat_anh_ho_so(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), du_lieu)
    return {"url": url}


# POST /quan-ly-nhan-su/ho-so/{id}/giay-to/{loai}/anh — upload ảnh giấy tờ
# {loai} = bang_lai hoặc giay_kham_suc_khoe
@router.post("/ho-so/{nhan_su_id}/giay-to/{loai}/anh", response_model=AnhResponse)
async def tai_anh_giay_to_len(nhan_su_id: UUID, loai: LoaiGiayTo, nguoi_dung: QuyenQuanLyNhanSu, file: UploadFile = File(...)):
    du_lieu = await file.read(KICH_THUOC_TOI_DA_BYTE + 1)
    url = service.cap_nhat_anh_giay_to(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), loai, du_lieu)
    return {"url": url}


# GET /quan-ly-nhan-su/ho-so/{id}/xem-truoc-nghi-viec — UC-51 bước 2: chỉ xem, không ghi gì
@router.get("/ho-so/{nhan_su_id}/xem-truoc-nghi-viec", response_model=XemTruocNghiViecResponse)
def xem_truoc_nghi_viec(nhan_su_id: UUID, nguoi_dung: QuyenQuanLyNhanSu):
    return service.xem_truoc_nghi_viec(str(nhan_su_id))


# POST /quan-ly-nhan-su/ho-so/{id}/nghi-viec — UC-51: cho nghỉ việc (ngày nghỉ bỏ trống = hôm nay)
@router.post("/ho-so/{nhan_su_id}/nghi-viec", response_model=ChoNghiViecResponse)
def cho_nghi_viec(nhan_su_id: UUID, du_lieu: ChoNghiViecRequest, nguoi_dung: QuyenQuanLyNhanSu):
    return service.cho_nghi_viec(nguoi_dung.id, nguoi_dung.vai_tro, str(nhan_su_id), du_lieu)
