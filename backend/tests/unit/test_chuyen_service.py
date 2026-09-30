"""Unit test cho trang "Chuyến" (UC-18) — sửa giờ chuyến, giả lập Repository."""

import datetime

import pytest

from app.services import chuyen_service as cs
from app.utils.loi import GiaTriLoi

VN = cs.MUI_GIO_VN


def _chuyen(ngay, **ghi_de):
    du_lieu = {
        "id": "c-1",
        "loai_xe_id": "lx-1",
        "xe_id": None,
        "trang_thai": "chua_khoi_hanh",
        "so_ve_dang_hoat_dong": 0,
        "gio_khoi_hanh": datetime.datetime.combine(ngay, datetime.time(6, 30), tzinfo=VN),
    }
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap(monkeypatch, chuyen, trung=False):
    da_ghi = []
    monkeypatch.setattr(cs.repo, "tim_chuyen_theo_id_ql", lambda _id: chuyen)
    monkeypatch.setattr(cs.repo, "tim_trung_loai_xe_va_gio", lambda *a: trung)
    monkeypatch.setattr(cs.repo, "sua_gio_chuyen", lambda cid, gio: da_ghi.append(gio))
    return da_ghi


def _ngay_tuong_lai():
    return datetime.datetime.now(VN).date() + datetime.timedelta(days=10)


def test_sua_gio_giu_nguyen_ngay(monkeypatch):
    ngay = _ngay_tuong_lai()
    da_ghi = _gia_lap(monkeypatch, _chuyen(ngay))
    cs.sua_gio_chuyen("c-1", datetime.time(7, 15))
    assert da_ghi == [datetime.datetime.combine(ngay, datetime.time(7, 15), tzinfo=VN)]


def test_sua_gio_ngay_lay_theo_gio_vn_khong_theo_utc(monkeypatch):
    # 00:30 giờ VN = 17:30 UTC hôm trước — ngày phải vẫn là ngày VN.
    ngay = _ngay_tuong_lai()
    chuyen = _chuyen(ngay, gio_khoi_hanh=datetime.datetime.combine(ngay, datetime.time(0, 30), tzinfo=VN).astimezone(datetime.timezone.utc))
    da_ghi = _gia_lap(monkeypatch, chuyen)
    cs.sua_gio_chuyen("c-1", datetime.time(1, 0))
    assert da_ghi[0].astimezone(VN).date() == ngay


def test_sua_gio_trong_qua_khu_bi_chan(monkeypatch):
    hom_nay = datetime.datetime.now(VN).date()
    da_ghi = _gia_lap(monkeypatch, _chuyen(hom_nay - datetime.timedelta(days=1)))
    with pytest.raises(GiaTriLoi, match="đã qua"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []


def test_sua_gio_chuyen_da_co_ve_bi_chan(monkeypatch):
    da_ghi = _gia_lap(monkeypatch, _chuyen(_ngay_tuong_lai(), so_ve_dang_hoat_dong=2))
    with pytest.raises(GiaTriLoi, match="vé"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []


def test_sua_gio_trung_loai_xe_va_gio_bi_chan(monkeypatch):
    da_ghi = _gia_lap(monkeypatch, _chuyen(_ngay_tuong_lai()), trung=True)
    with pytest.raises(GiaTriLoi, match="cùng loại xe"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []
