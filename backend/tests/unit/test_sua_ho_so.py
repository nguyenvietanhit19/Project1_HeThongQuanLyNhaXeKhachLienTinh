"""Unit test cho sửa hồ sơ của chính mình (họ tên + số điện thoại) — giả lập Repository."""

import pytest
from pydantic import ValidationError

from app.schemas.nguoi_dung_schema import SuaHoSoRequest
from app.services import mat_khau_service as svc
from app.utils.loi import GiaTriLoi


def _gia_lap(monkeypatch):
    da_ghi = []
    monkeypatch.setattr(svc.repo, "cap_nhat_ho_ten", lambda i, v: da_ghi.append(("ho_ten", v)))
    monkeypatch.setattr(svc.repo, "cap_nhat_so_dien_thoai", lambda i, v: da_ghi.append(("sdt", v)))
    return da_ghi


@pytest.mark.parametrize("nhap, ky_vong", [
    ("0912345678", "0912345678"),
    ("091 234 5678", "0912345678"),
    ("091.234.5678", "0912345678"),
    ("+84912345678", "0912345678"),
    ("+84 912 345 678", "0912345678"),
    ("84912345678", "0912345678"),
    ("0351234567", "0351234567"),
    ("0551234567", "0551234567"),
    ("0771234567", "0771234567"),
    ("0861234567", "0861234567"),
    ("(024) 3825-1234", "02438251234"),
])
def test_sdt_hop_le_duoc_chuan_hoa_ve_dang_0(nhap, ky_vong):
    assert svc.chuan_hoa_so_dien_thoai(nhap) == ky_vong


@pytest.mark.parametrize("nhap", [
    "abc", "12345", "912345678", "09123", "0912345678901234", "+1912345678",
    "0123456789",    # đầu 01x đã bỏ
    "0412345678",    # đầu 04 không có
    "09123456789",   # di động thừa 1 số
    "091234567",     # di động thiếu 1 số
    "0212345678",    # số bàn thiếu 1 số
    "8491234567",    # đầu 84 nhưng độ dài sai
    "0912a45678",    # lẫn chữ
])
def test_sdt_khong_hop_le_bi_chan(nhap):
    with pytest.raises(GiaTriLoi, match="không hợp lệ"):
        svc.chuan_hoa_so_dien_thoai(nhap)


@pytest.mark.parametrize("nhap", ["", "   ", None])
def test_sdt_rong_bi_chan(nhap):
    with pytest.raises(GiaTriLoi, match="nhập số điện thoại"):
        svc.chuan_hoa_so_dien_thoai(nhap)


def test_sua_chi_ho_ten(monkeypatch):
    da_ghi = _gia_lap(monkeypatch)
    svc.sua_ho_so("u1", ho_ten="  Nguyễn Văn Bình ")
    assert da_ghi == [("ho_ten", "Nguyễn Văn Bình")]


def test_sua_chi_sdt(monkeypatch):
    da_ghi = _gia_lap(monkeypatch)
    svc.sua_ho_so("u1", so_dien_thoai="091 234 5678")
    assert da_ghi == [("sdt", "0912345678")]


def test_sua_ca_hai(monkeypatch):
    da_ghi = _gia_lap(monkeypatch)
    svc.sua_ho_so("u1", ho_ten="An", so_dien_thoai="0912345678")
    assert da_ghi == [("ho_ten", "An"), ("sdt", "0912345678")]


def test_sdt_sai_thi_khong_ghi_ca_ho_ten(monkeypatch):
    da_ghi = _gia_lap(monkeypatch)
    with pytest.raises(GiaTriLoi):
        svc.sua_ho_so("u1", ho_ten="An", so_dien_thoai="abc")
    assert da_ghi == []  # kiểm tra hết trước khi ghi, không sửa dở dang


def test_ho_ten_chi_toan_khoang_trang_bi_chan(monkeypatch):
    da_ghi = _gia_lap(monkeypatch)
    with pytest.raises(GiaTriLoi, match="không được để trống"):
        svc.sua_ho_so("u1", ho_ten="   ")
    assert da_ghi == []


def test_schema_phai_co_it_nhat_1_truong():
    with pytest.raises(ValidationError):
        SuaHoSoRequest()
    assert SuaHoSoRequest(ho_ten="An").so_dien_thoai is None  # tương thích chỗ cũ chỉ gửi họ tên
    assert SuaHoSoRequest(so_dien_thoai="0912345678").ho_ten is None


# ---------------------------------------------------------
# Đăng ký: SĐT được kiểm tra + chuẩn hóa TRƯỚC khi tạo tài khoản/gửi mail
# ---------------------------------------------------------
def _gia_lap_dang_ky(monkeypatch):
    ghi = {}
    monkeypatch.setattr(svc.repo, "tim_theo_email", lambda e: None)
    monkeypatch.setattr(svc.repo, "tao_khach_hang_chua_kich_hoat", lambda *a: ghi.update(tao=a))
    monkeypatch.setattr(svc, "gui_mail", lambda *a, **k: ghi.update(mail=True) or True)
    return ghi


def test_dang_ky_luu_sdt_da_chuan_hoa(monkeypatch):
    ghi = _gia_lap_dang_ky(monkeypatch)
    svc.gui_ma_dang_ky("a@x.vn", "123456", "An", "+84 912 345 678")
    assert ghi["tao"][3] == "0912345678"  # (email, hash, ho_ten, so_dien_thoai, ...)
    assert ghi["mail"] is True


def test_dang_ky_sdt_sai_khong_tao_tai_khoan_va_khong_gui_mail(monkeypatch):
    ghi = _gia_lap_dang_ky(monkeypatch)
    with pytest.raises(GiaTriLoi, match="không hợp lệ"):
        svc.gui_ma_dang_ky("a@x.vn", "123456", "An", "12345")
    assert ghi == {}
