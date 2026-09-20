"""Giao diện di động của phụ xe — UC-12,13,15,16,17,26,27,28 (NGHIEP_VU.md
mục 8.2). Route chỉ mỏng: nhận request, gọi service, trả response — không
tự viết logic (CONTRIBUTING.md mục 2 phần "người 3": chỉ gọi hàm có sẵn từ
chuyen_xe_service/ve_service/gui_hang_service).
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.chuyen_xe_schema import (
    BaoSuCoRequest,
    ChuyenPhuXeResponse,
    DiemHienTaiResponse,
    HanhTrinhDiemResponse,
    ThongKePhuXeResponse,
    XacNhanToiDiemRequest,
    XacNhanToiDiemResponse,
)
from app.schemas.don_hang_schema import (
    BaoThatLacRequest,
    DonHangChoChatResponse,
    DonHangChoDoResponse,
    XacNhanChatHangRequest,
)
from app.services import chuyen_xe_service, gui_hang_service, ve_service

router = APIRouter(prefix="/phu-xe", tags=["phu_xe"])

_phu_xe = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("phu_xe"))]


@router.get("/chuyen-cua-toi", response_model=list[ChuyenPhuXeResponse])
def chuyen_cua_toi(nguoi_dung: _phu_xe):
    return chuyen_xe_service.danh_sach_chuyen_cua_toi(nguoi_dung.id)


@router.get("/thong-ke", response_model=ThongKePhuXeResponse)
def thong_ke(nguoi_dung: _phu_xe, tu_ngay: date, den_ngay: date):
    # den_ngay người dùng chọn là bao gồm cả ngày đó — cộng thêm 1 ngày để
    # thành mốc loại trừ (exclusive) khi so sánh với gio_khoi_hanh (TIMESTAMPTZ).
    return chuyen_xe_service.thong_ke_cua_toi(nguoi_dung.id, tu_ngay, den_ngay + timedelta(days=1))


@router.get("/chuyen/{chuyen_id}", response_model=ChuyenPhuXeResponse)
def chi_tiet_chuyen(chuyen_id: str, nguoi_dung: _phu_xe):
    """Không lọc theo trạng thái (khác /chuyen-cua-toi) — cần để giao diện
    vẫn tải được header ngay sau khi chuyến vừa chuyển hoan_thanh."""
    return chuyen_xe_service.chi_tiet_cho_phu_xe(chuyen_id, nguoi_dung.id)


@router.get("/chuyen/{chuyen_id}/hanh-trinh", response_model=list[HanhTrinhDiemResponse])
def hanh_trinh(chuyen_id: str, nguoi_dung: _phu_xe):
    return chuyen_xe_service.hanh_trinh(chuyen_id, nguoi_dung.id)


@router.get("/chuyen/{chuyen_id}/diem-hien-tai", response_model=DiemHienTaiResponse)
def diem_hien_tai(chuyen_id: str, nguoi_dung: _phu_xe):
    return chuyen_xe_service.khach_tai_diem_hien_tai(chuyen_id, nguoi_dung.id)


@router.post("/chuyen/{chuyen_id}/xuat-phat")
def xac_nhan_xuat_phat(chuyen_id: str, nguoi_dung: _phu_xe):
    chuyen_xe_service.xac_nhan_xuat_phat(chuyen_id, nguoi_dung.id)
    return {"thong_bao": "Đã xác nhận xuất phát"}


@router.post("/chuyen/{chuyen_id}/toi-diem", response_model=XacNhanToiDiemResponse)
def xac_nhan_toi_diem(chuyen_id: str, du_lieu: XacNhanToiDiemRequest, nguoi_dung: _phu_xe):
    da_hoan_thanh = chuyen_xe_service.xac_nhan_toi_diem(chuyen_id, du_lieu.diem_don_tra_id, nguoi_dung.id)
    return XacNhanToiDiemResponse(da_hoan_thanh=da_hoan_thanh)


@router.post("/chuyen/{chuyen_id}/bao-su-co")
def bao_su_co(chuyen_id: str, du_lieu: BaoSuCoRequest, nguoi_dung: _phu_xe):
    chuyen_xe_service.bao_su_co(chuyen_id, du_lieu.loai_su_co, du_lieu.ly_do, nguoi_dung.id)
    return {"thong_bao": "Đã ghi nhận sự cố, điều độ viên sẽ xử lý"}


@router.post("/chuyen/{chuyen_id}/ve/{ve_id}/len-xe")
def xac_nhan_len_xe(chuyen_id: str, ve_id: str, nguoi_dung: _phu_xe):
    ve_service.xac_nhan_len_xe(chuyen_id, ve_id, nguoi_dung.id)
    return {"thong_bao": "Đã xác nhận khách lên xe"}


@router.post("/chuyen/{chuyen_id}/ve/{ve_id}/xuong-xe")
def xac_nhan_xuong_xe(chuyen_id: str, ve_id: str, nguoi_dung: _phu_xe):
    ve_service.xac_nhan_xuong_xe(chuyen_id, ve_id, nguoi_dung.id)
    return {"thong_bao": "Đã xác nhận khách xuống xe"}


@router.get("/chuyen/{chuyen_id}/hang-cho-chat", response_model=list[DonHangChoChatResponse])
def hang_cho_chat(chuyen_id: str, nguoi_dung: _phu_xe):
    return gui_hang_service.danh_sach_cho_chat(chuyen_id, nguoi_dung.id)


@router.get("/chuyen/{chuyen_id}/hang-cho-do", response_model=list[DonHangChoDoResponse])
def hang_cho_do(chuyen_id: str, nguoi_dung: _phu_xe):
    return gui_hang_service.danh_sach_cho_do(chuyen_id, nguoi_dung.id)


@router.post("/don-hang/{don_hang_id}/chat-len-xe")
def xac_nhan_chat_hang(don_hang_id: str, du_lieu: XacNhanChatHangRequest, nguoi_dung: _phu_xe):
    gui_hang_service.xac_nhan_chat_hang(don_hang_id, du_lieu.chuyen_id, nguoi_dung.id)
    return {"thong_bao": "Đã xác nhận chất hàng lên xe"}


@router.post("/don-hang/{don_hang_id}/do-hang")
def xac_nhan_do_hang(don_hang_id: str, nguoi_dung: _phu_xe):
    gui_hang_service.xac_nhan_do_hang(don_hang_id, nguoi_dung.id)
    return {"thong_bao": "Đã xác nhận dỡ hàng khỏi xe"}


@router.post("/don-hang/{don_hang_id}/bao-that-lac")
def bao_that_lac(don_hang_id: str, du_lieu: BaoThatLacRequest, nguoi_dung: _phu_xe):
    gui_hang_service.bao_that_lac(don_hang_id, du_lieu.mo_ta, nguoi_dung.id)
    return {"thong_bao": "Đã ghi nhận báo cáo"}
