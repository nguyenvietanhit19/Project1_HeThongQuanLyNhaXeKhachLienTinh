"""Làm tròn giá bán tới bội số của 10.000đ — NGHIEP_VU.md mục 3.1."""

from decimal import Decimal

from app.utils.gia import gia_theo_ghe, tinh_gia_ban


def test_khong_doi_khi_da_la_boi_so():
    assert tinh_gia_ban(300_000, Decimal("1.50")) == 450_000


def test_nua_lam_tron_len():
    assert tinh_gia_ban(250_000, Decimal("1.5")) == 380_000  # 375.000
    assert tinh_gia_ban(130_000, Decimal("1.15")) == 150_000  # 149.500
    assert tinh_gia_ban(130_000, Decimal("1.1")) == 140_000  # 143.000


def test_lam_tron_xuong_khi_duoi_nua():
    assert tinh_gia_ban(100_000, Decimal("1.04")) == 100_000  # 104.000


def test_khong_bao_gio_ve_0():
    assert tinh_gia_ban(3_000, Decimal("1")) == 10_000


def test_he_so_ghe_nhan_cung_he_so_chuyen_roi_lam_tron_mot_lan():
    # 130.000 × 1,5 × 1,1 = 214.500 → 210.000 (nếu tròn từng bước: 195.000 → 200.000 × 1,1 = 220.000 — khác)
    assert tinh_gia_ban(130_000, Decimal("1.5"), Decimal("1.1")) == 210_000


def test_gia_theo_ghe_ghe_vang_mat_trong_he_so_la_1():
    gia = gia_theo_ghe(100_000, Decimal("1.5"), ["A1", "A2", "A3"], {"A1": 1.2, "A3": 0.8})
    assert gia == {"A1": 180_000, "A2": 150_000, "A3": 120_000}


def test_gia_theo_ghe_chap_nhan_he_so_ghe_none():
    assert gia_theo_ghe(100_000, 1, ["A1"], None) == {"A1": 100_000}
