"""Unit test cho gui_hang_service — giả lập Repository bằng monkeypatch."""

import pytest

from app.services import gui_hang_service as svc
from app.utils.loi import GiaTriLoi


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "trang_thai": "dang_chay"}
    data.update(overrides)
    return data


def _don_hang(**overrides):
    data = {"id": "don-1", "tuyen_id": "tuyen-1", "chuyen_id": None, "trang_thai": "cho_van_chuyen"}
    data.update(overrides)
    return data


def test_xac_nhan_chat_hang_khong_tim_thay_don(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")


def test_xac_nhan_chat_hang_khac_tuyen(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(tuyen_id="tuyen-khac"))
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang())
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")


def test_xac_nhan_chat_hang_da_len_xe_roi(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang(trang_thai="da_len_xe"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")


def test_xac_nhan_chat_hang_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang())
    goi = {}
    monkeypatch.setattr(svc.don_hang_repo, "cap_nhat_chat_hang_len_chuyen", lambda did, cid: goi.update(don=did, chuyen=cid))
    svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == {"don": "don-1", "chuyen": "chuyen-1"}


def test_xac_nhan_do_hang_chua_tung_len_xe(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang(chuyen_id=None))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")


def test_xac_nhan_do_hang_sai_trang_thai(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang(chuyen_id="chuyen-1", trang_thai="cho_lay"))
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")


def test_xac_nhan_do_hang_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang(chuyen_id="chuyen-1", trang_thai="da_len_xe"))
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    goi = {}
    monkeypatch.setattr(svc.don_hang_repo, "cap_nhat_do_hang_tai_diem", lambda did: goi.setdefault("did", did))
    svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi["did"] == "don-1"


def test_bao_that_lac_khong_tim_thay_don(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: None)
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "mo ta", "nguoi-dung-1")


def test_bao_that_lac_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don_hang())
    goi = {}
    monkeypatch.setattr(svc.bao_cao_repo, "tao", lambda did, uid, mota: goi.update(don=did, nguoi=uid, mota=mota))
    svc.bao_that_lac("don-1", "mo ta hu hong", "nguoi-dung-1")
    assert goi == {"don": "don-1", "nguoi": "nguoi-dung-1", "mota": "mo ta hu hong"}
