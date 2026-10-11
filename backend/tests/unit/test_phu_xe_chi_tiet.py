"""Unit test phần "xem lại" của phụ xe: tổng quan chuyến, chi tiết đơn hàng, chuyến đã chạy —
giả lập Repository bằng monkeypatch, không cần DB thật."""

from datetime import date, datetime, timezone

import pytest

from app.services import phu_xe_chi_tiet_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongDuQuyen, KhongTimThay

GIO = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)


def _chuyen(**overrides):
    data = {
        "id": "c1", "ma": "T001-LX001-261006-0800-DI", "tuyen_id": "t1", "chieu": "xuoi", "xe_id": "xe-1",
        "xe_thuc_te_id": None, "gio_khoi_hanh": GIO, "gio_xac_nhan_xuat_phat": GIO, "gio_hoan_thanh": None,
        "trang_thai": "hoan_thanh", "dang_hoan": False, "loai_su_co": None, "ly_do_su_co": None,
    }
    data.update(overrides)
    return data


def _khong_thuoc_xe(cid, nid):
    raise KhongDuQuyen("Chuyến này không thuộc về bạn")


# ---------------------------------------------------------------- tổng quan chuyến
def test_tong_quan_chuyen_gom_khach_hang_hoa_va_hanh_trinh(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_ten_tuyen_va_bien_so", lambda tid, xid: {"tuyen_ten": "Ha Noi - Sapa", "bien_so": "29B-1"})
    monkeypatch.setattr(svc.chuyen_xe_service, "hanh_trinh", lambda cid, nid: [{"diem_don_tra_id": "a"}])
    monkeypatch.setattr(svc.ve_repo, "tim_hanh_khach_cua_chuyen", lambda cid: [{"ve_id": "v1"}])
    monkeypatch.setattr(svc.don_hang_repo, "tim_hang_hoa_cua_chuyen", lambda cid: [{"id": "d1"}])
    kq = svc.tong_quan_chuyen("c1", "nd")
    assert kq["chuyen"]["tuyen_ten"] == "Ha Noi - Sapa"
    assert kq["chuyen"]["bien_so"] == "29B-1"
    assert kq["chuyen"]["trang_thai"] == "hoan_thanh"  # xem được cả chuyến đã hoàn thành
    assert kq["hanh_khach"] == [{"ve_id": "v1"}] and kq["hang_hoa"] == [{"id": "d1"}]
    assert kq["hanh_trinh"] == [{"diem_don_tra_id": "a"}]


def test_tong_quan_chuyen_hien_bien_so_xe_chay_thay(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(xe_thuc_te_id="xe-thay"))
    hoi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_ten_tuyen_va_bien_so", lambda tid, xid: hoi.append(xid) or {"tuyen_ten": "T", "bien_so": "B"})
    monkeypatch.setattr(svc.chuyen_xe_service, "hanh_trinh", lambda cid, nid: [])
    monkeypatch.setattr(svc.ve_repo, "tim_hanh_khach_cua_chuyen", lambda cid: [])
    monkeypatch.setattr(svc.don_hang_repo, "tim_hang_hoa_cua_chuyen", lambda cid: [])
    svc.tong_quan_chuyen("c1", "nd")
    assert hoi == ["xe-thay"]


def test_tong_quan_chuyen_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.tong_quan_chuyen("c1", "nguoi-khac")


# ---------------------------------------------------------------- chi tiết đơn hàng
def _don(**overrides):
    data = {"id": "d1", "ma_van_don": "VD1", "tuyen_id": "t1", "chuyen_id": None, "trang_thai": "cho_van_chuyen"}
    data.update(overrides)
    return data


def _chuan_bi_don(monkeypatch, don):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don)
    monkeypatch.setattr(svc.don_hang_repo, "lay_lich_su_trang_thai", lambda did: [{"den_trang_thai": "da_len_xe"}])
    monkeypatch.setattr(svc.don_hang_repo, "lay_bao_cao_su_co", lambda did: [{"mo_ta": "vo"}])


def test_chi_tiet_don_tren_xe_kem_lich_su_va_bao_cao(monkeypatch):
    _chuan_bi_don(monkeypatch, _don(chuyen_id="c1", trang_thai="da_len_xe"))
    kiem = []
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: kiem.append(cid) or _chuyen())
    kq = svc.chi_tiet_don_hang("d1", "nd")
    assert kiem == ["c1"]  # phải là chuyến của chính phụ xe
    assert kq["lich_su_trang_thai"] == [{"den_trang_thai": "da_len_xe"}]
    assert kq["bao_cao_su_co"] == [{"mo_ta": "vo"}]
    assert kq["ma_van_don"] == "VD1"


def test_chi_tiet_don_cua_chuyen_khac_xe_bi_chan(monkeypatch):
    _chuan_bi_don(monkeypatch, _don(chuyen_id="c9", trang_thai="da_len_xe"))
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.chi_tiet_don_hang("d1", "nguoi-khac")


def test_chi_tiet_don_cho_chat_cung_tuyen_duoc_xem(monkeypatch):
    _chuan_bi_don(monkeypatch, _don())
    monkeypatch.setattr(svc.chuyen_xe_service, "danh_sach_chuyen_cua_toi", lambda nid: [{"tuyen_id": "t1"}])
    assert svc.chi_tiet_don_hang("d1", "nd")["id"] == "d1"


def test_chi_tiet_don_cho_chat_khac_tuyen_bi_chan(monkeypatch):
    _chuan_bi_don(monkeypatch, _don())
    monkeypatch.setattr(svc.chuyen_xe_service, "danh_sach_chuyen_cua_toi", lambda nid: [{"tuyen_id": "t-khac"}])
    with pytest.raises(CamTruyCap):
        svc.chi_tiet_don_hang("d1", "nd")


@pytest.mark.parametrize("trang_thai", ["cho_lay", "da_giao", "qua_han_luu_kho"])
def test_chi_tiet_don_khong_gan_chuyen_ngoai_giai_doan_cho_chat_bi_chan(monkeypatch, trang_thai):
    _chuan_bi_don(monkeypatch, _don(trang_thai=trang_thai))
    with pytest.raises(CamTruyCap):
        svc.chi_tiet_don_hang("d1", "nd")


def test_chi_tiet_don_khong_ton_tai(monkeypatch):
    _chuan_bi_don(monkeypatch, None)
    with pytest.raises(KhongTimThay):
        svc.chi_tiet_don_hang("d1", "nd")


# ---------------------------------------------------------------- chuyến đã chạy
def test_chuyen_da_chay_ngay_bat_dau_phai_truoc_ngay_ket_thuc():
    with pytest.raises(GiaTriLoi):
        svc.chuyen_da_chay("nd", date(2026, 10, 6), date(2026, 10, 6))


def test_chuyen_da_chay_khong_phai_phu_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: {"id": "ns", "chuc_danh": "tai_xe"})
    with pytest.raises(KhongDuQuyen):
        svc.chuyen_da_chay("nd", date(2026, 10, 1), date(2026, 10, 7))


def test_chuyen_da_chay_chua_bien_che_tra_rong(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: {"id": "ns", "chuc_danh": "phu_xe"})
    monkeypatch.setattr(svc.nhan_su_repo, "tim_xe_dang_gan", lambda nsid: None)
    assert svc.chuyen_da_chay("nd", date(2026, 10, 1), date(2026, 10, 7)) == []


def test_chuyen_da_chay_lay_theo_xe_cua_minh(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: {"id": "ns", "chuc_danh": "phu_xe"})
    monkeypatch.setattr(svc.nhan_su_repo, "tim_xe_dang_gan", lambda nsid: "xe-1")
    hoi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "danh_sach_chuyen_da_chay", lambda xid, tu, den: hoi.append((xid, tu, den)) or [{"id": "c1"}])
    assert svc.chuyen_da_chay("nd", date(2026, 10, 1), date(2026, 10, 8)) == [{"id": "c1"}]
    assert hoi == [("xe-1", date(2026, 10, 1), date(2026, 10, 8))]
