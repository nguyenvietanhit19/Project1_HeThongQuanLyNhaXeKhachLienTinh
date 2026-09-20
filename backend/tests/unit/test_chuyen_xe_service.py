"""Unit test cho chuyen_xe_service — giả lập Repository bằng monkeypatch,
không cần DB thật (ARCHITECTURE.md mục 3 'tests/unit')."""

import pytest

from app.services import chuyen_xe_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _nhan_su_phu_xe(**overrides):
    data = {"id": "nhan-su-1", "ho_ten": "Phu Xe A", "chuc_danh": "phu_xe"}
    data.update(overrides)
    return data


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "xe_id": "xe-1", "trang_thai": "chua_khoi_hanh"}
    data.update(overrides)
    return data


def _diem(id_, thu_tu, ten="Diem"):
    return {"diem_don_tra_id": id_, "thu_tu": thu_tu, "ten": ten}


def test_lay_chuyen_cua_phu_xe_khong_tim_thay_chuyen(monkeypatch):
    monkeypatch.setattr(svc.chuyen_xe_repo, "tim_theo_id", lambda cid: None)
    with pytest.raises(GiaTriLoi):
        svc.lay_chuyen_cua_phu_xe("chuyen-1", "nguoi-dung-1")


def test_lay_chuyen_cua_phu_xe_khong_phai_phu_xe(monkeypatch):
    monkeypatch.setattr(svc.chuyen_xe_repo, "tim_theo_id", lambda cid: _chuyen())
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: None)
    with pytest.raises(KhongDuQuyen):
        svc.lay_chuyen_cua_phu_xe("chuyen-1", "nguoi-dung-1")


def test_lay_chuyen_cua_phu_xe_khong_thuoc_ve_minh(monkeypatch):
    monkeypatch.setattr(svc.chuyen_xe_repo, "tim_theo_id", lambda cid: _chuyen(xe_id="xe-khac"))
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: _nhan_su_phu_xe())
    monkeypatch.setattr(svc.nhan_su_repo, "tim_xe_dang_gan", lambda nsid: "xe-1")
    with pytest.raises(KhongDuQuyen):
        svc.lay_chuyen_cua_phu_xe("chuyen-1", "nguoi-dung-1")


def test_lay_chuyen_cua_phu_xe_hop_le(monkeypatch):
    chuyen = _chuyen()
    monkeypatch.setattr(svc.chuyen_xe_repo, "tim_theo_id", lambda cid: chuyen)
    monkeypatch.setattr(svc.nhan_su_repo, "tim_theo_nguoi_dung_id", lambda nid: _nhan_su_phu_xe())
    monkeypatch.setattr(svc.nhan_su_repo, "tim_xe_dang_gan", lambda nsid: "xe-1")
    assert svc.lay_chuyen_cua_phu_xe("chuyen-1", "nguoi-dung-1") == chuyen


def test_xac_nhan_xuat_phat_sai_trang_thai(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")


def test_xac_nhan_xuat_phat_thanh_cong(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    goi = {}
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: goi.setdefault("cid", cid))
    svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")
    assert goi["cid"] == "chuyen-1"


def test_xac_nhan_toi_diem_chuyen_chua_xuat_phat(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="chua_khoi_hanh"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")


def test_xac_nhan_toi_diem_diem_khong_thuoc_tuyen(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2)])
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "diem-la", "nguoi-dung-1")


def test_xac_nhan_toi_diem_nhay_coc_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "d3", "nguoi-dung-1")  # nhảy cóc qua d2


def test_xac_nhan_toi_diem_da_xac_nhan_truoc_do(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": "d2", "thu_tu": 2}])
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")


def test_xac_nhan_toi_diem_dung_thu_tu_chua_hoan_thanh(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: None)
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, tt: [])
    assert svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1") is False


def test_xac_nhan_toi_diem_diem_cuoi_hoan_thanh(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": "d2", "thu_tu": 2}])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: None)
    goi = {}
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: goi.setdefault("cid", cid))
    assert svc.xac_nhan_toi_diem("chuyen-1", "d3", "nguoi-dung-1") is True
    assert goi["cid"] == "chuyen-1"


def test_xac_nhan_toi_diem_gui_thong_bao_eta_cho_khach_o_diem_sau(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2, "Diem B"), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: None)
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, tt: [{"khach_hang_id": "kh-1"}])
    da_gui = []
    monkeypatch.setattr(svc, "_gui_thong_bao", lambda nid, nd: da_gui.append((nid, nd)))
    svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")
    assert da_gui == [("kh-1", "Xe vừa đến Diem B — cập nhật giờ dự kiến đón bạn")]


def test_xac_nhan_toi_diem_khong_gui_thong_bao_khi_hoan_thanh(monkeypatch):
    """Điểm cuối tuyến không có ai chờ 'phía sau' — không gọi _gui_thong_bao."""
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: None)
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: None)
    da_goi = []
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, tt: da_goi.append(1))
    svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")
    assert da_goi == []  # không được gọi vì da_hoan_thanh = True


def test_bao_su_co_nguyen_nhan_khong_hop_le():
    with pytest.raises(GiaTriLoi):
        svc.bao_su_co("chuyen-1", "linh_tinh", "ly do", "nguoi-dung-1")


def test_bao_su_co_sai_trang_thai(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="chua_khoi_hanh"))
    with pytest.raises(GiaTriLoi):
        svc.bao_su_co("chuyen-1", "loi_nha_xe", "hong xe", "nguoi-dung-1")


def test_bao_su_co_thanh_cong_va_gui_thong_bao_khach(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: None)
    goi_co = {}
    monkeypatch.setattr(
        svc.chuyen_xe_repo,
        "gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai",
        lambda xe_id, cid: goi_co.update(xe_id=xe_id, cid=cid),
    )
    monkeypatch.setattr(
        svc.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda cid: [{"khach_hang_id": "kh-1"}, {"khach_hang_id": "kh-2"}]
    )
    da_gui = []
    monkeypatch.setattr(svc, "_gui_thong_bao", lambda nid, nd: da_gui.append(nid))

    svc.bao_su_co("chuyen-1", "loi_nha_xe", "thung lop", "nguoi-dung-1")

    assert goi_co == {"xe_id": "xe-1", "cid": "chuyen-1"}
    assert da_gui == ["kh-1", "kh-2"]
