"""Unit test cho ve_service — giả lập Repository bằng monkeypatch."""

import pytest

from app.services import ve_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _ve(**overrides):
    data = {"id": "ve-1", "chuyen_id": "chuyen-1", "trang_thai": "da_thanh_toan"}
    data.update(overrides)
    return data


def test_xac_nhan_len_xe_khong_tim_thay_ve(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_ve_thuoc_chuyen_khac(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(chuyen_id="chuyen-khac"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_ve_chua_thanh_toan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="giu_cho"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve())
    goi = {}
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_len_xe", lambda vid: goi.setdefault("vid", vid))
    svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi["vid"] == "ve-1"


def test_xac_nhan_xuong_xe_chua_len_xe(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="da_thanh_toan"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_xuong_xe_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="da_len_xe", diem_tra_id="diem-b"))
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": "diem-b"}])
    goi = {}
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_xuong_xe", lambda vid: goi.setdefault("vid", vid))
    svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi["vid"] == "ve-1"


@pytest.mark.parametrize("trang_thai", ["chua_khoi_hanh", "gap_su_co", "hoan_thanh", "da_huy"])
def test_xac_nhan_len_xe_chuyen_khong_dang_chay(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": trang_thai})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve())
    goi = []
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_len_xe", lambda vid: goi.append(vid))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["da_len_xe", "da_xuong_xe", "khong_den", "het_han", "da_huy"])
def test_xac_nhan_len_xe_ve_khong_o_trang_thai_da_thanh_toan(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_len_xe_phu_xe_khac_xe_bi_chan(monkeypatch):
    def tu_choi(cid, nid):
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", tu_choi)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_len_xe("chuyen-1", "ve-1", "nguoi-dung-khac")


def _chuan_bi_xuong_xe(monkeypatch, trang_thai_chuyen="dang_chay", diem_da_toi=("diem-b",), diem_tra="diem-b"):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": trang_thai_chuyen})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(trang_thai="da_len_xe", diem_tra_id=diem_tra))
    monkeypatch.setattr(
        svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": d} for d in diem_da_toi]
    )
    goi = []
    monkeypatch.setattr(svc.ve_repo, "xac_nhan_xuong_xe", lambda vid: goi.append(vid))
    return goi


def test_xac_nhan_xuong_xe_xe_chua_toi_diem_tra(monkeypatch):
    goi = _chuan_bi_xuong_xe(monkeypatch, diem_da_toi=("diem-a",), diem_tra="diem-c")
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_xuong_xe_chua_toi_diem_nao(monkeypatch):
    goi = _chuan_bi_xuong_xe(monkeypatch, diem_da_toi=())
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_xuong_xe_cho_phep_chuyen_vua_hoan_thanh(monkeypatch):
    goi = _chuan_bi_xuong_xe(monkeypatch, trang_thai_chuyen="hoan_thanh")
    svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi == ["ve-1"]


@pytest.mark.parametrize("trang_thai", ["chua_khoi_hanh", "gap_su_co", "da_huy"])
def test_xac_nhan_xuong_xe_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    goi = _chuan_bi_xuong_xe(monkeypatch, trang_thai_chuyen=trang_thai)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_xuong_xe_ve_thuoc_chuyen_khac(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: {"id": cid, "trang_thai": "dang_chay"})
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: _ve(chuyen_id="chuyen-khac", trang_thai="da_len_xe"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-1")


def test_xac_nhan_xuong_xe_phu_xe_khac_xe_bi_chan(monkeypatch):
    def tu_choi(cid, nid):
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", tu_choi)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_xuong_xe("chuyen-1", "ve-1", "nguoi-dung-khac")
