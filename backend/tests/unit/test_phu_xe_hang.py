"""Unit test phần hàng gửi của phụ xe (UC-26, UC-27, UC-28) — giả lập
Repository bằng monkeypatch, không cần DB thật. File riêng, không đụng
test_gui_hang_service.py (phần nhân viên gửi hàng)."""

import pytest

from app.services import gui_hang_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "xe_id": "xe-1", "trang_thai": "dang_chay"}
    data.update(overrides)
    return data


def _don(**overrides):
    data = {
        "id": "don-1", "tuyen_id": "tuyen-1", "chuyen_id": None, "trang_thai": "cho_van_chuyen",
        "diem_gui_id": "d1", "diem_nhan_id": "d3",
    }
    data.update(overrides)
    return data


def _khong_thuoc_xe(cid, nid):
    raise KhongDuQuyen("Chuyến này không thuộc về bạn")


# ---------------------------------------------------------------- UC-26
def test_danh_sach_cho_chat_chi_lay_don_tai_diem_hien_tai(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc, "diem_hien_tai", lambda chuyen: {"diem_don_tra_id": "d1"})
    monkeypatch.setattr(
        svc.don_hang_repo,
        "lay_danh_sach_cho_xep_xe",
        lambda tid: [_don(id="a", diem_gui_id="d1"), _don(id="b", diem_gui_id="d2"), _don(id="c", diem_gui_id="d1")],
    )
    ket_qua = svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-1")
    assert [d["id"] for d in ket_qua] == ["a", "c"]  # giữ nguyên thứ tự đơn cũ trước


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_danh_sach_cho_chat_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-1")


def test_danh_sach_cho_chat_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-khac")


def _chuan_bi_chat(monkeypatch, chuyen=None, don=None, chat_duoc=True):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen or _chuyen())
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don)
    goi = []
    monkeypatch.setattr(
        svc.don_hang_repo, "chat_len_chuyen_neu_dang_cho", lambda did, cid: goi.append((did, cid)) or chat_duoc
    )
    return goi


def test_xac_nhan_chat_hang_thanh_cong_gan_dung_chuyen(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=_don())
    svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == [("don-1", "chuyen-1")]


@pytest.mark.parametrize("trang_thai", ["chua_khoi_hanh", "dang_chay"])
def test_xac_nhan_chat_hang_cho_phep_chuyen_chua_chay_va_dang_chay(monkeypatch, trang_thai):
    goi = _chuan_bi_chat(monkeypatch, chuyen=_chuyen(trang_thai=trang_thai), don=_don())
    svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert len(goi) == 1


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_xac_nhan_chat_hang_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    goi = _chuan_bi_chat(monkeypatch, chuyen=_chuyen(trang_thai=trang_thai), don=_don())
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_hang_khong_tim_thay_don(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["da_len_xe", "cho_lay", "da_giao", "qua_han_luu_kho"])
def test_xac_nhan_chat_hang_don_khong_con_cho_van_chuyen(monkeypatch, trang_thai):
    goi = _chuan_bi_chat(monkeypatch, don=_don(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_hang_don_da_gan_chuyen_khac(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=_don(chuyen_id="chuyen-khac"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_hang_don_khac_tuyen(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=_don(tuyen_id="tuyen-khac"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_hang_bi_nguoi_khac_chat_truoc(monkeypatch):
    # 2 phụ xe (2 chuyến cùng tuyến) cùng bấm: UPDATE có điều kiện không khớp dòng nào
    _chuan_bi_chat(monkeypatch, don=_don(), chat_duoc=False)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-1")


def test_xac_nhan_chat_hang_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_chat_hang_cua_phu_xe("don-1", "chuyen-1", "nguoi-dung-khac")
