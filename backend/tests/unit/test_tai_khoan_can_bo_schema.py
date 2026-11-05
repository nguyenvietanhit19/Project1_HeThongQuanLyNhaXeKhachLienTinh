"""Unit test cho schema khóa / mở khóa tài khoản (UC-37, bước 1) — thuần Pydantic, không cần DB."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tai_khoan_can_bo_schema import (
    DoiTrangThaiTaiKhoanRequest,
    DoiTrangThaiTaiKhoanResponse,
    XeThieuPhuXe,
)


def test_ly_do_hop_le_duoc_giu_nguyen():
    assert DoiTrangThaiTaiKhoanRequest(ly_do="Nghỉ việc").ly_do == "Nghỉ việc"


def test_ly_do_duoc_cat_khoang_trang_hai_dau():
    assert DoiTrangThaiTaiKhoanRequest(ly_do="   Nghỉ việc  \n").ly_do == "Nghỉ việc"


@pytest.mark.parametrize("ly_do", ["", " ", "   ", "\n\t "])
def test_ly_do_rong_hoac_toan_khoang_trang_bi_chan(ly_do):
    with pytest.raises(ValidationError, match="Vui lòng nhập lý do"):
        DoiTrangThaiTaiKhoanRequest(ly_do=ly_do)


def test_thieu_ly_do_bi_chan():
    with pytest.raises(ValidationError):
        DoiTrangThaiTaiKhoanRequest()


def test_ly_do_none_bi_chan():
    with pytest.raises(ValidationError):
        DoiTrangThaiTaiKhoanRequest(ly_do=None)


def test_ly_do_dung_500_ky_tu_la_hop_le():
    assert len(DoiTrangThaiTaiKhoanRequest(ly_do="a" * 500).ly_do) == 500


def test_ly_do_501_ky_tu_bi_chan():
    with pytest.raises(ValidationError):
        DoiTrangThaiTaiKhoanRequest(ly_do="a" * 501)


def test_khoang_trang_hai_dau_khong_tinh_vao_do_dai():
    # 500 ký tự thật + khoảng trắng thừa vẫn hợp lệ vì được cắt trước khi kiểm độ dài
    assert len(DoiTrangThaiTaiKhoanRequest(ly_do="  " + "a" * 500 + "  ").ly_do) == 500


def test_response_mac_dinh_khong_co_canh_bao():
    kq = DoiTrangThaiTaiKhoanResponse(id=uuid4(), dang_hoat_dong=False)
    assert kq.canh_bao_xe_thieu_phu_xe == []


def test_response_co_canh_bao_xe_thieu_phu_xe():
    kq = DoiTrangThaiTaiKhoanResponse(
        id=uuid4(), dang_hoat_dong=False,
        canh_bao_xe_thieu_phu_xe=[XeThieuPhuXe(xe_id=uuid4(), bien_so="29B-12345")],
    )
    assert kq.canh_bao_xe_thieu_phu_xe[0].bien_so == "29B-12345"


def test_hai_response_khong_dung_chung_danh_sach_canh_bao():
    # default_factory: mỗi response có danh sách riêng, không bị dùng chung giữa các request
    a = DoiTrangThaiTaiKhoanResponse(id=uuid4(), dang_hoat_dong=True)
    b = DoiTrangThaiTaiKhoanResponse(id=uuid4(), dang_hoat_dong=True)
    a.canh_bao_xe_thieu_phu_xe.append(XeThieuPhuXe(xe_id=uuid4(), bien_so="30F-99999"))
    assert b.canh_bao_xe_thieu_phu_xe == []
