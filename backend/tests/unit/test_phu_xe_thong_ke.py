"""Unit test UC-39 phía phụ xe (thống kê chỉ các chuyến của xe mình) — giả lập
Repository bằng monkeypatch, không cần DB thật."""

from datetime import date

import pytest

from app.services import chuyen_xe_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen

TU, DEN = date(2026, 10, 1), date(2026, 10, 8)


def _chuyen(trang_thai="hoan_thanh", so_ve_ban=5, tong_ghe=10, doanh_thu=500000):
    return {"id": "c", "trang_thai": trang_thai, "so_ve_ban": so_ve_ban, "tong_ghe": tong_ghe, "doanh_thu": doanh_thu}


def _phu_xe(monkeypatch, xe_id="xe-1", chuyen_list=()):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: {"id": "ns-1", "chuc_danh": "phu_xe"})
    monkeypatch.setattr(svc.nhan_su_repo, "tim_xe_dang_gan", lambda nsid: xe_id)
    hoi = {}
    monkeypatch.setattr(
        svc.chuyen_xe_repo, "thong_ke_theo_xe", lambda xid, tu, den: hoi.update(xe_id=xid, tu=tu, den=den) or list(chuyen_list)
    )
    return hoi


def test_thong_ke_khoang_ngay_dao_nguoc_bi_chan():
    with pytest.raises(GiaTriLoi):
        svc.thong_ke_cua_toi("nguoi-dung-1", DEN, TU)


def test_thong_ke_cung_ngay_bi_chan():
    # den_ngay là mốc loại trừ — tu_ngay == den_ngay là khoảng rỗng
    with pytest.raises(GiaTriLoi):
        svc.thong_ke_cua_toi("nguoi-dung-1", TU, TU)


def test_thong_ke_khong_phai_phu_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: {"id": "ns-1", "chuc_danh": "tai_xe"})
    with pytest.raises(KhongDuQuyen):
        svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)


def test_thong_ke_chua_co_tai_khoan_nhan_su_bi_chan(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: None)
    with pytest.raises(KhongDuQuyen):
        svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)


def test_thong_ke_phu_xe_chua_duoc_bien_che_vao_xe_nao(monkeypatch):
    hoi = _phu_xe(monkeypatch, xe_id=None)
    kq = svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)
    assert kq == {"so_chuyen": 0, "doanh_thu": 0, "ty_le_lap_day_trung_binh": 0, "so_chuyen_su_co": 0, "so_chuyen_huy": 0}
    assert hoi == {}  # không truy vấn gì khi chưa có xe


def test_thong_ke_khong_co_chuyen_nao_trong_khoang(monkeypatch):
    _phu_xe(monkeypatch, chuyen_list=[])
    assert svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)["so_chuyen"] == 0


def test_thong_ke_chi_truy_van_dung_xe_cua_phu_xe_va_dung_khoang(monkeypatch):
    hoi = _phu_xe(monkeypatch, xe_id="xe-cua-toi", chuyen_list=[_chuyen()])
    svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)
    assert hoi == {"xe_id": "xe-cua-toi", "tu": TU, "den": DEN}


def test_thong_ke_tinh_dung_cac_chi_so(monkeypatch):
    _phu_xe(
        monkeypatch,
        chuyen_list=[
            _chuyen("hoan_thanh", so_ve_ban=10, tong_ghe=10, doanh_thu=1000000),  # lấp đầy 100%
            _chuyen("hoan_thanh", so_ve_ban=5, tong_ghe=10, doanh_thu=500000),  # 50%
            _chuyen("gap_su_co", so_ve_ban=0, tong_ghe=10, doanh_thu=0),  # 0%
            _chuyen("da_huy", so_ve_ban=0, tong_ghe=10, doanh_thu=0),  # không tính vào tỷ lệ lấp đầy
        ],
    )
    kq = svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)
    assert kq["so_chuyen"] == 4
    assert kq["doanh_thu"] == 1500000
    assert kq["so_chuyen_su_co"] == 1
    assert kq["so_chuyen_huy"] == 1
    assert kq["ty_le_lap_day_trung_binh"] == pytest.approx((1.0 + 0.5 + 0.0) / 3)


def test_thong_ke_chuyen_khong_biet_tong_ghe_khong_chia_cho_khong(monkeypatch):
    _phu_xe(monkeypatch, chuyen_list=[_chuyen(tong_ghe=None), _chuyen(tong_ghe=0), _chuyen(so_ve_ban=5, tong_ghe=10)])
    kq = svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)
    assert kq["so_chuyen"] == 3
    assert kq["ty_le_lap_day_trung_binh"] == pytest.approx(0.5)  # chỉ tính chuyến có tổng ghế hợp lệ


def test_thong_ke_toan_chuyen_huy_khong_co_ty_le_lap_day(monkeypatch):
    _phu_xe(monkeypatch, chuyen_list=[_chuyen("da_huy", so_ve_ban=0)])
    assert svc.thong_ke_cua_toi("nguoi-dung-1", TU, DEN)["ty_le_lap_day_trung_binh"] == 0
