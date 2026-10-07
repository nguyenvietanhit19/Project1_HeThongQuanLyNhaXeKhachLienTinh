"""Unit test trang Booking (lịch sử vé của khách): phân nhóm + nhãn trạng thái, dựng danh sách — Repository giả lập."""

import datetime

import pytest

from app.services import dat_ve_service as svc
from tests.unit.test_dat_ve_service import BAY_GIO, _ve

TRUOC = BAY_GIO - datetime.timedelta(minutes=1)
SAU = BAY_GIO + datetime.timedelta(minutes=5)


def _loai(*ve, **kw):
    return svc.phan_loai_lich_su(list(ve), BAY_GIO)


# ---------------------------------------------------------
# Sắp đi
# ---------------------------------------------------------
def test_dang_giu_chua_chon_cach_thanh_toan_la_sap_di():
    assert _loai(_ve("1", han=SAU)) == ("sap_di", "dang_giu")


def test_cho_thanh_toan_vnpay():
    assert _loai(_ve("1", han=SAU, gio_bat_dau_dem_han=BAY_GIO)) == ("sap_di", "cho_thanh_toan")


def test_da_chot_thanh_toan_tai_quay():
    assert _loai(_ve("1", loai="thanh_toan_tai_quay", han=None)) == ("sap_di", "dat_thanh_cong_tai_quay")


def test_da_thanh_toan_chuyen_chua_chay_la_sap_di():
    assert _loai(_ve("1", trang_thai="da_thanh_toan", han=None)) == ("sap_di", "da_thanh_toan")


def test_da_len_xe_chuyen_dang_chay_van_la_sap_di():
    ve = _ve("1", trang_thai="da_len_xe", han=None, trang_thai_chuyen="dang_chay")
    assert _loai(ve) == ("sap_di", "da_len_xe")


def test_lo_cung_co_ve_tra_online_va_ve_giu_tai_quay_la_da_thanh_toan():
    assert _loai(_ve("1", trang_thai="da_thanh_toan", han=None), _ve("2", loai="thanh_toan_tai_quay", han=None)) == ("sap_di", "da_thanh_toan")


# ---------------------------------------------------------
# Đã đi
# ---------------------------------------------------------
def test_da_xuong_xe_la_da_di():
    assert _loai(_ve("1", trang_thai="da_xuong_xe", han=None, trang_thai_chuyen="hoan_thanh")) == ("da_di", "da_di")


def test_khong_den_la_da_di_nhan_khong_den():
    assert _loai(_ve("1", trang_thai="khong_den", han=None, trang_thai_chuyen="hoan_thanh")) == ("da_di", "khong_den")


def test_lo_vua_di_vua_bo_khong_tinh_la_khong_den():
    ve = [_ve("1", trang_thai="da_xuong_xe", han=None, trang_thai_chuyen="hoan_thanh"),
          _ve("2", trang_thai="khong_den", han=None, trang_thai_chuyen="hoan_thanh")]
    assert svc.phan_loai_lich_su(ve, BAY_GIO) == ("da_di", "da_di")


def test_chuyen_da_hoan_thanh_ma_ve_van_da_thanh_toan_la_da_di():
    assert _loai(_ve("1", trang_thai="da_thanh_toan", han=None, trang_thai_chuyen="hoan_thanh")) == ("da_di", "da_di")


# ---------------------------------------------------------
# Đã hủy
# ---------------------------------------------------------
def test_khach_huy_giu_cho():
    assert _loai(_ve("1", trang_thai="da_huy", han=None)) == ("da_huy", "da_huy")


def test_het_han_do_job_da_quet():
    assert _loai(_ve("1", trang_thai="het_han", han=TRUOC)) == ("da_huy", "het_han")


def test_het_han_du_job_chua_quet():
    assert _loai(_ve("1", trang_thai="giu_cho", han=TRUOC)) == ("da_huy", "het_han")


def test_chuyen_bi_huy():
    assert _loai(_ve("1", trang_thai="da_thanh_toan", han=None, trang_thai_chuyen="da_huy")) == ("da_huy", "chuyen_bi_huy")


def test_ghe_da_bo_khong_anh_huong_nhom_cua_luot():
    ve = [_ve("1", trang_thai="da_huy", han=None), _ve("2", trang_thai="da_thanh_toan", han=None)]
    assert svc.phan_loai_lich_su(ve, BAY_GIO) == ("sap_di", "da_thanh_toan")


# ---------------------------------------------------------
# Dựng danh sách
# ---------------------------------------------------------
def _v(ma, so_ghe, **kw):
    return _ve(so_ghe, ma_dat_cho=ma, ngay_tao=BAY_GIO - datetime.timedelta(hours=1), **kw)


def test_lich_su_gom_theo_luot_giu_thu_tu_va_bo_ghe_da_huy(monkeypatch):
    rows = [
        _v("DC0001", "1", trang_thai="da_thanh_toan", han=None, gia=300000),
        _v("DC0001", "2", trang_thai="da_huy", han=None, gia=300000),
        _v("DC0001", "3", trang_thai="da_thanh_toan", han=None, gia=200000),
        _v("DC0002", "9", han=SAU, gio_bat_dau_dem_han=BAY_GIO, gia=150000),
    ]
    monkeypatch.setattr(svc.lich_su_repo, "lay_ve_cua_khach", lambda kh: rows)
    monkeypatch.setattr(svc, "_bay_gio", lambda: BAY_GIO)
    ds = svc.lich_su("kh1")
    assert [d["ma_dat_cho"] for d in ds] == ["DC0001", "DC0002"]
    a, b = ds
    assert (a["nhom"], a["trang_thai"], a["so_ve"], a["tong_tien"], a["co_the_tiep_tuc"]) == ("sap_di", "da_thanh_toan", 2, 500000, False)
    assert [v["so_ghe"] for v in a["ve"]] == ["1", "3"]
    assert (b["trang_thai"], b["co_the_tiep_tuc"]) == ("cho_thanh_toan", True)
    assert b["han_thanh_toan"] == SAU - datetime.timedelta(minutes=svc.HAN_DE_DUNG_TRE_IPN_PHUT)


def test_lich_su_khach_chua_dat_gi_la_danh_sach_rong(monkeypatch):
    monkeypatch.setattr(svc.lich_su_repo, "lay_ve_cua_khach", lambda kh: [])
    assert svc.lich_su("kh1") == []


def test_lich_su_luot_da_huy_het_van_hien_tong_tien_cac_ve_da_huy(monkeypatch):
    rows = [_v("DC0003", "1", trang_thai="da_huy", han=None, gia=100000), _v("DC0003", "2", trang_thai="da_huy", han=None, gia=100000)]
    monkeypatch.setattr(svc.lich_su_repo, "lay_ve_cua_khach", lambda kh: rows)
    monkeypatch.setattr(svc, "_bay_gio", lambda: BAY_GIO)
    (d,) = svc.lich_su("kh1")
    assert (d["nhom"], d["trang_thai"], d["so_ve"], d["tong_tien"]) == ("da_huy", "da_huy", 2, 200000)
