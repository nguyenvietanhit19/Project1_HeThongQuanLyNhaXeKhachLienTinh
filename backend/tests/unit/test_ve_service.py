"""Unit test cho ve_service — giả lập Repository bằng monkeypatch."""

import pytest

from app.services import ve_service as svc
from app.utils.loi import GiaTriLoi


def _ve(**overrides):
    data = {"id": "ve-1", "chuyen_id": "chuyen-1", "trang_thai": "da_thanh_toan"}
    data.update(overrides)
    return data


def test_xac_nhan_len_xe_khong_tim_thay_ve(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_ve_thuoc_chuyen_khac(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(chuyen_id="chuyen-khac"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_ve_chua_thanh_toan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="giu_cho"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve())
    goi = {}
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_len_xe", lambda vid: goi.setdefault("vid", vid))
    svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi["vid"] == "ve-1"


def test_xac_nhan_xuong_xe_chua_len_xe(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="da_thanh_toan"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_xuong_xe_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="da_len_xe"))
    goi = {}
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_xuong_xe", lambda vid: goi.setdefault("vid", vid))
    svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi["vid"] == "ve-1"
