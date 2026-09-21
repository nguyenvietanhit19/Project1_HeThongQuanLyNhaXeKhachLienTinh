"""Unit tests kiểm tra phân quyền và validation API cho routes/ke_toan.py (không cần httpx).

Kiểm tra:
- Không gửi token hoặc token rỗng -> HTTPException 401 Unauthorized
- Token của vai trò không được phép (khach_hang, phu_xe) -> HTTPException 403 Forbidden
- Token hợp lệ của vai trò 'ke_toan' hoặc 'quan_ly' -> Cho phép truy cập
- Route handler gọi đúng Service tương ứng
"""

from unittest.mock import patch, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_dang_nhap, yeu_cau_vai_tro
from app.routes import ke_toan as route
from app.schemas.hoan_tien_schema import TaoHoanTienRequest, XacNhanChuyenKhoanRequest


# ====================================================================
# 1. Kiểm tra Ngoại lệ Thiếu Token & Token sai vai trò (401 & 403)
# ====================================================================

def test_auth_middleware_thieu_token():
    """Không truyền Header Authorization -> HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        yeu_cau_dang_nhap(None)
    assert exc_info.value.status_code == 401
    assert "Thiếu token" in exc_info.value.detail


def test_auth_middleware_sai_dinh_dang_bearer():
    """Header Authorization không bắt đầu bằng Bearer -> HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        yeu_cau_dang_nhap("Basic 123456")
    assert exc_info.value.status_code == 401
    assert "Thiếu token" in exc_info.value.detail


def test_auth_middleware_vai_tro_bi_chan():
    """Khách hàng hoặc Phụ xe cố truy cập route chỉ dành cho Kế toán/Quản lý -> HTTPException 403."""
    kiem_tra_ke_toan = yeu_cau_vai_tro("ke_toan", "quan_ly")
    nguoi_dung_khach = NguoiDungHienTai(id=str(uuid4()), vai_tro="khach_hang")
    nguoi_dung_phu_xe = NguoiDungHienTai(id=str(uuid4()), vai_tro="phu_xe")

    with pytest.raises(HTTPException) as exc1:
        kiem_tra_ke_toan(nguoi_dung_khach)
    assert exc1.value.status_code == 403
    assert "Không có quyền" in exc1.value.detail

    with pytest.raises(HTTPException) as exc2:
        kiem_tra_ke_toan(nguoi_dung_phu_xe)
    assert exc2.value.status_code == 403
    assert "Không có quyền" in exc2.value.detail


def test_auth_middleware_vai_tro_duoc_phep():
    """Kế toán hoặc Quản lý được phép truy cập."""
    kiem_tra_ke_toan = yeu_cau_vai_tro("ke_toan", "quan_ly")
    nguoi_dung_kt = NguoiDungHienTai(id=str(uuid4()), vai_tro="ke_toan")
    nguoi_dung_ql = NguoiDungHienTai(id=str(uuid4()), vai_tro="quan_ly")

    assert kiem_tra_ke_toan(nguoi_dung_kt) == nguoi_dung_kt
    assert kiem_tra_ke_toan(nguoi_dung_ql) == nguoi_dung_ql


# ====================================================================
# 2. Kiểm tra Route Handlers
# ====================================================================

@patch("app.services.hoan_tien_service.lay_danh_sach_cho_xu_ly")
def test_route_xem_danh_sach_cho_xu_ly(mock_service):
    """Route xem danh sách chờ xử lý chuyển lời gọi tới service."""
    mock_service.return_value = [{"id": str(uuid4()), "so_tien": 200000}]
    nguoi_dung = NguoiDungHienTai(id=str(uuid4()), vai_tro="ke_toan")

    res = route.xem_danh_sach_cho_xu_ly(nguoi_dung)
    assert len(res) == 1
    mock_service.assert_called_once()


@patch("app.services.hoan_tien_service.duyet_hoan_tien_thu_cong")
def test_route_duyet_hoan_tien_thu_cong(mock_service):
    """Route duyệt hoàn tiền thủ công truyền đúng thông tin sang service."""
    hoan_id = uuid4()
    nguoi_dung = NguoiDungHienTai(id=str(uuid4()), vai_tro="ke_toan")
    body = XacNhanChuyenKhoanRequest(
        so_tai_khoan_nhan="0987654321",
        ten_ngan_hang_nhan="Techcombank",
        ten_chu_tai_khoan_nhan="TRAN THI C",
    )
    mock_service.return_value = {"id": str(hoan_id), "trang_thai": "da_hoan_chuyen_khoan_thu_cong"}

    res = route.duyet_hoan_tien_thu_cong(hoan_id, body, nguoi_dung)
    assert res["trang_thai"] == "da_hoan_chuyen_khoan_thu_cong"
    mock_service.assert_called_once_with(
        hoan_tien_id=str(hoan_id),
        nhan_vien_xu_ly_id=nguoi_dung.id,
        thong_tin_ngan_hang=body.model_dump(),
    )


@patch("app.services.hoan_tien_service.thong_ke_doanh_thu_ke_toan")
def test_route_thong_ke_tai_chinh(mock_service):
    """Route thống kê tài chính truyền đúng query param."""
    nguoi_dung = NguoiDungHienTai(id=str(uuid4()), vai_tro="ke_toan")
    mock_service.return_value = {"doanh_thu_thuan": 10000000}

    res = route.xem_thong_ke_tai_chinh(nguoi_dung, tu_ngay="2026-09-01", den_ngay="2026-09-21")
    assert res["doanh_thu_thuan"] == 10000000
    mock_service.assert_called_once_with(tu_ngay="2026-09-01", den_ngay="2026-09-21")

