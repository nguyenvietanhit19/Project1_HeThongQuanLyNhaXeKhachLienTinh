"""Unit test hàm dựng mã tự sinh (utils/ma_tu_sinh.py) — hàm thuần, không cần DB."""

import datetime
from zoneinfo import ZoneInfo

import pytest

from app.utils import ma_tu_sinh as ma

UTC = datetime.timezone.utc
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.mark.parametrize(
    "ham, so, mong_doi",
    [
        (ma.ma_khu_vuc, 1, "KV001"),
        (ma.ma_khu_vuc, 42, "KV042"),
        (ma.ma_tuyen, 7, "T007"),
        (ma.ma_loai_xe, 12, "LX012"),
        (ma.ma_ve, 1, "VE000001"),
        (ma.ma_ve, 54, "VE000054"),
    ],
)
def test_dinh_dang_co_dem_so_0(ham, so, mong_doi):
    assert ham(so) == mong_doi


@pytest.mark.parametrize(
    "ham, so, mong_doi",
    [
        (ma.ma_khu_vuc, 999, "KV999"),
        (ma.ma_khu_vuc, 1000, "KV1000"),  # lpad của Postgres cắt thành "KV100" → trùng; ở đây không cắt
        (ma.ma_tuyen, 12345, "T12345"),
        (ma.ma_loai_xe, 1000, "LX1000"),
        (ma.ma_ve, 999999, "VE999999"),
        (ma.ma_ve, 1000000, "VE1000000"),
        (ma.ma_ve, 1234567, "VE1234567"),
    ],
)
def test_so_dai_hon_do_rong_khong_bi_cat(ham, so, mong_doi):
    assert ham(so) == mong_doi


def test_ma_khong_trung_khi_so_lien_tiep_qua_moc():
    cac_ma = {ma.ma_ve(n) for n in range(999990, 1000011)}
    assert len(cac_ma) == 21


def test_ma_diem_don_tra_dem_rieng_tung_khu_vuc():
    assert ma.ma_diem_don_tra("KV001", 1) == "KV001-DT001"
    assert ma.ma_diem_don_tra("KV002", 1) == "KV002-DT001"
    assert ma.ma_diem_don_tra("KV001", 1000) == "KV001-DT1000"


def test_ma_chuyen_theo_gio_viet_nam():
    gio = datetime.datetime(2026, 10, 8, 1, 0, tzinfo=UTC)  # 08:00 giờ Việt Nam
    assert ma.ma_chuyen("T001", "LX001", gio, "xuoi") == "T001-LX001-261008-0800-DI"


def test_ma_chuyen_qua_nua_dem_tinh_theo_ngay_viet_nam():
    gio = datetime.datetime(2026, 10, 8, 17, 30, tzinfo=UTC)  # 00:30 ngày 09/10 giờ Việt Nam
    assert ma.ma_chuyen("T001", "LX002", gio, "nguoc") == "T001-LX002-261009-0030-VE"


def test_ma_chuyen_gio_da_o_mui_gio_viet_nam_van_dung():
    gio = datetime.datetime(2026, 10, 8, 23, 30, tzinfo=VN)
    assert ma.ma_chuyen("T003", "LX001", gio, "xuoi") == "T003-LX001-261008-2330-DI"


def test_ma_chuyen_chieu_nguoc_la_ve():
    gio = datetime.datetime(2026, 1, 2, 3, 4, tzinfo=VN)
    assert ma.ma_chuyen("T001", "LX001", gio, "nguoc").endswith("-VE")
    assert ma.ma_chuyen("T001", "LX001", gio, "xuoi").endswith("-DI")


def test_ma_chuyen_thieu_mui_gio_bi_tu_choi():
    with pytest.raises(ValueError):
        ma.ma_chuyen("T001", "LX001", datetime.datetime(2026, 10, 8, 8, 0), "xuoi")
