"""Quy tắc kỳ thống kê và ghép số theo tuyến của trang Thống kê quản lý (UC-39)."""

from datetime import date

import pytest

from app.services import thong_ke_quan_ly_service as s
from app.utils.loi import GiaTriLoi


@pytest.fixture(autouse=True)
def _tuyen_ton_tai(monkeypatch):
    monkeypatch.setattr(s.dia_diem_repo, "tim_tuyen_theo_id", lambda tuyen_id: {"id": tuyen_id} if tuyen_id != "khong-co" else None)


def test_don_vi_theo_do_dai_ky():
    assert s.xac_dinh_ky(date(2026, 11, 5), date(2026, 11, 5))["don_vi"] == "gio"
    assert s.xac_dinh_ky(date(2026, 11, 1), date(2026, 11, 30))["don_vi"] == "ngay"
    assert s.xac_dinh_ky(date(2026, 1, 1), date(2026, 3, 3))["don_vi"] == "ngay"  # 62 ngày
    assert s.xac_dinh_ky(date(2026, 1, 1), date(2026, 3, 4))["don_vi"] == "thang"  # 63 ngày
    assert s.xac_dinh_ky(date(2026, 1, 1), date(2026, 12, 31))["don_vi"] == "thang"


def test_ky_so_sanh_mac_dinh_la_doan_cung_do_dai_ngay_truoc():
    ky = s.xac_dinh_ky(date(2026, 11, 1), date(2026, 11, 30))
    assert (ky["so_sanh_tu"], ky["so_sanh_den"]) == (date(2026, 10, 2), date(2026, 10, 31))
    ky = s.xac_dinh_ky(date(2026, 11, 25), date(2026, 11, 25))
    assert (ky["so_sanh_tu"], ky["so_sanh_den"]) == (date(2026, 11, 24), date(2026, 11, 24))


def test_ky_so_sanh_tuy_chon():
    ky = s.xac_dinh_ky(date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 1), date(2026, 10, 25))
    assert (ky["so_sanh_tu"], ky["so_sanh_den"]) == (date(2026, 10, 1), date(2026, 10, 25))


@pytest.mark.parametrize(
    "tham_so, thong_bao",
    [
        ((date(2026, 11, 30), date(2026, 11, 1)), "trước hoặc bằng"),
        ((date(2025, 1, 1), date(2026, 1, 5)), "tối đa 1 năm"),
        ((date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 1), None), "đủ ngày"),
        ((date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 31), date(2026, 10, 1)), "không hợp lệ"),
        ((date(2026, 11, 1), date(2026, 11, 30), date(2024, 1, 1), date(2025, 6, 1)), "tối đa 1 năm"),
        ((date(2026, 11, 1), date(2026, 11, 30), None, None, "khong-co"), "Tuyến không tồn tại"),
    ],
)
def test_ky_khong_hop_le(tham_so, thong_bao):
    with pytest.raises(GiaTriLoi, match=thong_bao):
        s.xac_dinh_ky(*tham_so)


def test_tab_sai():
    with pytest.raises(GiaTriLoi):
        s.thong_ke("khong-co", date(2026, 11, 1), date(2026, 11, 30))


def test_gop_theo_tuyen_dien_so_0_cho_phia_thieu_va_xep_theo_doanh_thu():
    tien = [{"tuyen_id": "a", "ma": "T001", "ten": "A", "tien_ve": 100, "tien_hang": 20, "hoan_ve": 10, "hoan_hang": 0,
             "tien_hoan": 10, "thuan": 110, "so_ve": 2}]
    chuyen = [
        {"tuyen_id": "a", "ma": "T001", "ten": "A", "tong_chuyen": 4, "da_chay": 3, "hoan_thanh": 3, "da_huy": 1, "co_su_co": 0,
         "ghe_ban": 30, "tong_ghe": 60, "co_gio_xuat_phat": 3, "dung_gio": 2},
        {"tuyen_id": "b", "ma": "T002", "ten": "B", "tong_chuyen": 2, "da_chay": 0, "hoan_thanh": 0, "da_huy": 0, "co_su_co": 0,
         "ghe_ban": 0, "tong_ghe": 0, "co_gio_xuat_phat": 0, "dung_gio": 0},
    ]
    kq = s.gop_theo_tuyen(tien, chuyen)
    assert [r["ma"] for r in kq] == ["T001", "T002"]
    assert kq[0]["thuan"] == 110 and kq[0]["da_chay"] == 3
    assert kq[1]["thuan"] == 0 and kq[1]["tien_ve"] == 0 and kq[1]["tong_chuyen"] == 2
