"""Unit test phần hàng gửi của phụ xe (UC-26, UC-27, UC-28) — giả lập
Repository bằng monkeypatch, không cần DB thật. Chiều chạy ngược được test
riêng ở test_phu_xe_chieu_nguoc.py; test_gui_hang_service.py là phần nhân
viên gửi hàng."""

import pytest

from app.services import gui_hang_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongDuQuyen


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "xe_id": "xe-1", "trang_thai": "dang_chay", "chieu": "xuoi"}
    data.update(overrides)
    return data


def _don(**overrides):
    data = {
        "id": "don-1", "ma_van_don": "VD001", "tuyen_id": "tuyen-1", "chuyen_id": None, "trang_thai": "cho_van_chuyen",
        "diem_gui_id": "d1", "diem_nhan_id": "d3", "ten_nguoi_nhan": "Chị Mai", "sdt_nguoi_nhan": "0944000000",
        "can_nang_kg": 2, "ngay_tao": None, "ten_diem_nhan": "Diem 3",
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def _khong_cham_db_khi_dem_bao_cao(monkeypatch):
    monkeypatch.setattr(svc.don_hang_repo, "dem_bao_cao_theo_loai", lambda ids: {})


def _khong_thuoc_xe(cid, nid):
    raise KhongDuQuyen("Chuyến này không thuộc về bạn")


def _dang_o_diem(monkeypatch, diem_id):
    monkeypatch.setattr(svc, "diem_hien_tai", lambda chuyen: {"diem_don_tra_id": diem_id})


def _chuyen_cua_phu_xe(monkeypatch, **overrides):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(**overrides))


# ---------------------------------------------------------------- UC-26: danh sách chờ chất
def test_danh_sach_cho_chat_chi_lay_don_tai_diem_hien_tai(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch)
    _dang_o_diem(monkeypatch, "d1")
    monkeypatch.setattr(
        svc.don_hang_repo, "lay_danh_sach_cho_xep_xe",
        lambda tid, cid=None: [_don(id="a", diem_gui_id="d1"), _don(id="b", diem_gui_id="d2"), _don(id="c", diem_gui_id="d1")],
    )
    ket_qua = svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-1")
    assert [d["id"] for d in ket_qua] == ["a", "c"]  # giữ nguyên thứ tự đơn cũ trước


def test_danh_sach_cho_chat_truyen_chuyen_id_de_loc_cung_chieu(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch)
    _dang_o_diem(monkeypatch, "d1")
    hoi = []
    monkeypatch.setattr(svc.don_hang_repo, "lay_danh_sach_cho_xep_xe", lambda tid, cid=None: hoi.append((tid, cid)) or [])
    svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-1")
    assert hoi == [("tuyen-1", "chuyen-1")]


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_danh_sach_cho_chat_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    _chuyen_cua_phu_xe(monkeypatch, trang_thai=trang_thai)
    with pytest.raises(GiaTriLoi):
        svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-1")


def test_danh_sach_cho_chat_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.danh_sach_cho_chat("chuyen-1", "nguoi-dung-khac")


# ---------------------------------------------------------------- UC-26: xác nhận chất
def _chuan_bi_chat(monkeypatch, chuyen=None, don="mac_dinh", chat_duoc=True, chieu_van_chuyen="xuoi", diem="d1"):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen or _chuyen())
    _dang_o_diem(monkeypatch, diem)
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: _don() if don == "mac_dinh" else don)
    monkeypatch.setattr(
        svc.don_hang_repo, "kiem_tra_diem_thuoc_tuyen",
        lambda tid, gui, nhan: {"chieu_van_chuyen": chieu_van_chuyen} if chieu_van_chuyen else None,
    )
    monkeypatch.setattr(svc.don_hang_repo, "tim_chuyen_xe_theo_id", lambda cid: {"chieu": (chuyen or _chuyen())["chieu"]})
    goi = []
    monkeypatch.setattr(
        svc.don_hang_repo, "cap_nhat_chat_hang_len_chuyen",
        lambda did, cid, nd=None: goi.append((did, cid, nd)) or ({"id": did} if chat_duoc else None),
    )
    return goi


def test_xac_nhan_chat_thanh_cong_gan_chuyen_cho_don(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch)
    svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == [("don-1", "chuyen-1", "nguoi-dung-1")]


def test_xac_nhan_chat_don_khong_ton_tai(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["da_len_xe", "cho_lay", "da_giao", "qua_han_luu_kho"])
def test_xac_nhan_chat_don_khong_o_trang_thai_cho_van_chuyen(monkeypatch, trang_thai):
    goi = _chuan_bi_chat(monkeypatch, don=_don(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_don_da_gan_chuyen_khac_bi_chan(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=_don(chuyen_id="chuyen-khac"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_khac_tuyen_bi_chan(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, don=_don(tuyen_id="tuyen-khac"))
    with pytest.raises(GiaTriLoi, match="tuyến"):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_don_cho_o_diem_khac_diem_xe_dang_dung_bi_chan(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, diem="d2")
    with pytest.raises(GiaTriLoi, match="điểm"):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_diem_khong_thuoc_tuyen_bi_chan(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, chieu_van_chuyen=None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_xac_nhan_chat_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    goi = _chuan_bi_chat(monkeypatch, chuyen=_chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_chat_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-khac")


def test_xac_nhan_chat_bam_dup_chi_mot_lan_thanh_cong(monkeypatch):
    _chuan_bi_chat(monkeypatch, chat_duoc=False)  # UPDATE có điều kiện không khớp dòng nào
    with pytest.raises(GiaTriLoi, match="tải lại"):
        svc.xac_nhan_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")


# ---------------------------------------------------------------- UC-27: dỡ hàng
def _chuan_bi_do(monkeypatch, don="mac_dinh", chuyen=None, diem="d3", do_duoc=True, nhan_vien=("nv-1",)):
    mac_dinh = _don(trang_thai="da_len_xe", chuyen_id="chuyen-1")
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: mac_dinh if don == "mac_dinh" else don)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen or _chuyen())
    _dang_o_diem(monkeypatch, diem)
    goi = []
    monkeypatch.setattr(
        svc.don_hang_repo, "cap_nhat_do_hang_tai_diem",
        lambda did, cid, nd=None: goi.append((did, cid, nd)) or ({"id": did} if do_duoc else None),
    )
    monkeypatch.setattr(svc.don_hang_repo, "danh_sach_nhan_vien_gui_hang_tai_diem", lambda diem_id: list(nhan_vien))
    da_bao = []
    monkeypatch.setattr(svc, "_gui_thong_bao_an_toan", lambda ids, nd, did: da_bao.append((list(ids), nd)))
    return goi, da_bao


def test_danh_sach_cho_do_chi_lay_don_den_diem_hien_tai(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch)
    _dang_o_diem(monkeypatch, "d3")
    hoi = []
    monkeypatch.setattr(
        svc.don_hang_repo, "tim_don_can_do_tai_diem",
        lambda cid, diem_id: hoi.append((cid, diem_id)) or [{"id": "x", "ma_van_don": "VD9", "ten_nguoi_nhan": "A", "can_nang_kg": 3}],
    )
    ket_qua = svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1")
    assert hoi == [("chuyen-1", "d3")]
    assert ket_qua[0]["ma_van_don"] == "VD9"


def test_danh_sach_cho_do_cho_phep_chuyen_vua_hoan_thanh(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch, trang_thai="hoan_thanh")
    _dang_o_diem(monkeypatch, "d3")
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_can_do_tai_diem", lambda cid, diem_id: [])
    assert svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1") == []


def test_xac_nhan_do_thanh_cong_va_bao_nhan_vien_diem_nhan(monkeypatch):
    goi, da_bao = _chuan_bi_do(monkeypatch)
    svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == [("don-1", "chuyen-1", "nguoi-dung-1")]
    assert da_bao[0][0] == ["nv-1"]
    assert "Chị Mai" in da_bao[0][1] and "0944000000" in da_bao[0][1]


def test_xac_nhan_do_khong_tim_thay_don(monkeypatch):
    goi, _ = _chuan_bi_do(monkeypatch, don=None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_don_chua_tung_len_chuyen(monkeypatch):
    goi, _ = _chuan_bi_do(monkeypatch, don=_don(trang_thai="cho_van_chuyen", chuyen_id=None))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["cho_van_chuyen", "cho_lay", "da_giao", "qua_han_luu_kho"])
def test_xac_nhan_do_don_khong_o_trang_thai_da_len_xe(monkeypatch, trang_thai):
    goi, _ = _chuan_bi_do(monkeypatch, don=_don(trang_thai=trang_thai, chuyen_id="chuyen-1"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_xe_chua_toi_diem_nhan_bi_chan(monkeypatch):
    goi, da_bao = _chuan_bi_do(monkeypatch, diem="d2")  # đơn nhận ở d3, xe mới tới d2
    with pytest.raises(GiaTriLoi, match="chưa tới"):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == [] and da_bao == []


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "da_huy"])
def test_xac_nhan_do_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    goi, _ = _chuan_bi_do(monkeypatch, chuyen=_chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    _chuan_bi_do(monkeypatch)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-khac")


def test_xac_nhan_do_bam_dup_khong_bao_lai(monkeypatch):
    _, da_bao = _chuan_bi_do(monkeypatch, do_duoc=False)
    with pytest.raises(GiaTriLoi, match="tải lại"):
        svc.xac_nhan_do_hang("don-1", "nguoi-dung-1")
    assert da_bao == []


# ---------------------------------------------------------------- UC-28: báo thất lạc/hư hỏng
def _chuan_bi_bao_cao(monkeypatch, don, chuyen_cua_toi=()):
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.chuyen_xe_service, "danh_sach_chuyen_cua_toi", lambda nid: list(chuyen_cua_toi))
    luu = []
    monkeypatch.setattr(
        svc.don_hang_repo, "luu_bao_cao_su_co_hang",
        lambda did, nid, mo_ta, loai="hu_hong": luu.append((did, nid, mo_ta)) or {"id": "bc-1"},
    )
    hoi_diem = []
    monkeypatch.setattr(
        svc.don_hang_repo, "danh_sach_nhan_vien_gui_hang_tai_diem", lambda diem_id: hoi_diem.append(diem_id) or ["nv-1"]
    )
    monkeypatch.setattr(svc.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vt, chi_dang_hoat_dong=False: ["ql-1"])
    da_bao = []
    monkeypatch.setattr(svc, "_gui_thong_bao_an_toan", lambda ids, nd, did: da_bao.append(list(ids)))
    return luu, hoi_diem, da_bao


def test_bao_that_lac_don_tren_xe_bao_nhan_vien_diem_nhan_va_quan_ly(monkeypatch):
    luu, hoi_diem, da_bao = _chuan_bi_bao_cao(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-1"))
    svc.bao_that_lac("don-1", "  vỡ kiện  ", "nguoi-dung-1")
    assert luu == [("don-1", "nguoi-dung-1", "vỡ kiện")]  # đã cắt khoảng trắng
    assert hoi_diem == ["d3"]  # đã lên xe -> báo điểm NHẬN
    assert da_bao == [["nv-1", "ql-1"]]


def test_bao_that_lac_don_dang_cho_chat_bao_nhan_vien_diem_gui(monkeypatch):
    luu, hoi_diem, _ = _chuan_bi_bao_cao(monkeypatch, _don(), chuyen_cua_toi=[{"tuyen_id": "tuyen-1"}])
    svc.bao_that_lac("don-1", "rách bao bì", "nguoi-dung-1")
    assert len(luu) == 1
    assert hoi_diem == ["d1"]  # chưa lên xe -> báo điểm GỬI


@pytest.mark.parametrize("mo_ta", ["", "   "])
def test_bao_that_lac_thieu_mo_ta(monkeypatch, mo_ta):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-1"))
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", mo_ta, "nguoi-dung-1")
    assert luu == []


def test_bao_that_lac_khong_tim_thay_don(monkeypatch):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, None)
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "mất", "nguoi-dung-1")
    assert luu == []


def test_bao_that_lac_don_cua_chuyen_khac_xe_bi_chan(monkeypatch):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-khac"))
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.bao_that_lac("don-1", "mất", "nguoi-dung-khac")
    assert luu == []


def test_bao_that_lac_don_cho_chat_khac_tuyen_bi_chan(monkeypatch):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, _don(), chuyen_cua_toi=[{"tuyen_id": "tuyen-khac"}])
    with pytest.raises(CamTruyCap):
        svc.bao_that_lac("don-1", "mất", "nguoi-dung-1")
    assert luu == []


def test_bao_that_lac_phu_xe_chua_co_chuyen_nao_bi_chan(monkeypatch):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, _don(), chuyen_cua_toi=[])
    with pytest.raises(CamTruyCap):
        svc.bao_that_lac("don-1", "mất", "nguoi-dung-1")
    assert luu == []


@pytest.mark.parametrize("trang_thai", ["cho_lay", "da_giao", "qua_han_luu_kho"])
def test_bao_that_lac_don_ngoai_giai_doan_chat_do_khong_co_chuyen(monkeypatch, trang_thai):
    luu, _, _ = _chuan_bi_bao_cao(monkeypatch, _don(trang_thai=trang_thai, chuyen_id=None), chuyen_cua_toi=[{"tuyen_id": "tuyen-1"}])
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "mất", "nguoi-dung-1")
    assert luu == []


# ---------------------------------------------------------------- hoàn tác chất / dỡ
def _chuan_bi_hoan_tac(monkeypatch, don, diem="d1"):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    _dang_o_diem(monkeypatch, diem)
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don)
    goi = {"chat": [], "do": [], "tb": []}
    monkeypatch.setattr(svc.don_hang_repo, "hoan_tac_chat_hang", lambda did, cid, nd=None: goi["chat"].append(did) or True)
    monkeypatch.setattr(svc.don_hang_repo, "hoan_tac_do_hang", lambda did, cid, nd=None: goi["do"].append(did) or True)
    monkeypatch.setattr(svc.don_hang_repo, "danh_sach_nhan_vien_gui_hang_tai_diem", lambda diem_id: ["nv-1"])
    monkeypatch.setattr(svc, "_gui_thong_bao_an_toan", lambda ids, nd, did: goi["tb"].append((ids, did)))
    return goi


def test_hoan_tac_chat_thanh_cong_khi_xe_con_o_diem_gui(monkeypatch):
    goi = _chuan_bi_hoan_tac(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-1"))
    svc.hoan_tac_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi["chat"] == ["don-1"]


def test_hoan_tac_chat_bi_chan_khi_xe_da_roi_diem_gui(monkeypatch):
    goi = _chuan_bi_hoan_tac(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-1"), diem="d2")
    with pytest.raises(GiaTriLoi):
        svc.hoan_tac_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi["chat"] == []


def test_hoan_tac_chat_don_chua_chat(monkeypatch):
    _chuan_bi_hoan_tac(monkeypatch, _don(trang_thai="cho_van_chuyen"))
    with pytest.raises(GiaTriLoi):
        svc.hoan_tac_chat_hang("don-1", "chuyen-1", "nguoi-dung-1")


def test_hoan_tac_do_thanh_cong_va_bao_lai_van_phong(monkeypatch):
    goi = _chuan_bi_hoan_tac(monkeypatch, _don(trang_thai="cho_lay", chuyen_id="chuyen-1", diem_nhan_id="d3"), diem="d3")
    svc.hoan_tac_do_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi["do"] == ["don-1"]
    assert goi["tb"] == [(["nv-1"], "don-1")]


def test_hoan_tac_do_bi_chan_khi_van_phong_da_bao_nguoi_nhan(monkeypatch):
    goi = _chuan_bi_hoan_tac(
        monkeypatch, _don(trang_thai="cho_lay", chuyen_id="chuyen-1", diem_nhan_id="d3", da_thong_bao_nguoi_nhan=True), diem="d3"
    )
    with pytest.raises(GiaTriLoi):
        svc.hoan_tac_do_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi["do"] == []


def test_hoan_tac_do_bi_chan_khi_xe_da_roi_diem_nhan(monkeypatch):
    goi = _chuan_bi_hoan_tac(monkeypatch, _don(trang_thai="cho_lay", chuyen_id="chuyen-1", diem_nhan_id="d3"), diem="d4")
    with pytest.raises(GiaTriLoi):
        svc.hoan_tac_do_hang("don-1", "chuyen-1", "nguoi-dung-1")
    assert goi["do"] == []


def test_danh_sach_hoan_tac_chi_hoi_tai_diem_xe_dang_dung(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch)
    _dang_o_diem(monkeypatch, "d3")
    hoi = []
    monkeypatch.setattr(
        svc.don_hang_repo, "tim_don_co_the_hoan_tac",
        lambda cid, did: hoi.append((cid, did)) or [{"id": "a", "ma_van_don": "VD1", "ten_nguoi_nhan": "X", "can_nang_kg": 2, "loai": "chat"}],
    )
    ket_qua = svc.danh_sach_hoan_tac("chuyen-1", "nguoi-dung-1")
    assert hoi == [("chuyen-1", "d3")]
    assert ket_qua[0]["loai"] == "chat"


# ---------------------------------------------------------------- chất / dỡ hàng loạt
def test_chat_tat_ca_dem_don_thanh_cong_va_liet_ke_don_loi(monkeypatch):
    monkeypatch.setattr(svc, "danh_sach_cho_chat", lambda cid, nid: [{"id": "a", "ma_van_don": "VA"}, {"id": "b", "ma_van_don": "VB"}])

    def chat(did, cid, nid):
        if did == "b":
            raise GiaTriLoi("sai chiều")

    monkeypatch.setattr(svc, "xac_nhan_chat_hang", chat)
    kq = svc.chat_tat_ca("chuyen-1", "nd")
    assert kq["so_luong"] == 1
    assert kq["loi"] == ["VB: sai chiều"]


def test_do_tat_ca_dem_don_da_do(monkeypatch):
    monkeypatch.setattr(svc, "danh_sach_cho_do", lambda cid, nid: [{"id": "a", "ma_van_don": "VA"}, {"id": "b", "ma_van_don": "VB"}])
    monkeypatch.setattr(svc, "xac_nhan_do_hang", lambda did, nid: None)
    assert svc.do_tat_ca("chuyen-1", "nd") == {"so_luong": 2, "loi": []}


def test_danh_sach_cho_do_gan_nhan_bao_cao_hu_hong_va_that_lac(monkeypatch):
    _chuyen_cua_phu_xe(monkeypatch)
    _dang_o_diem(monkeypatch, "d3")
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_can_do_tai_diem",
                        lambda cid, did: [{"id": "a", "ma_van_don": "VA", "ten_nguoi_nhan": "X", "can_nang_kg": 1},
                                          {"id": "b", "ma_van_don": "VB", "ten_nguoi_nhan": "Y", "can_nang_kg": 2}])
    monkeypatch.setattr(svc.don_hang_repo, "dem_bao_cao_theo_loai", lambda ids: {"a": {"hu_hong": 1, "that_lac": 0}, "b": {"hu_hong": 0, "that_lac": 2}})
    ds = svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1")
    assert (ds[0]["so_bao_hu_hong"], ds[0]["so_bao_that_lac"]) == (1, 0)
    assert (ds[1]["so_bao_hu_hong"], ds[1]["so_bao_that_lac"]) == (0, 2)


def test_do_tat_ca_bo_qua_don_da_bao_that_lac(monkeypatch):
    monkeypatch.setattr(svc, "danh_sach_cho_do", lambda cid, nid: [
        {"id": "a", "ma_van_don": "VA", "so_bao_that_lac": 0}, {"id": "b", "ma_van_don": "VB", "so_bao_that_lac": 1}])
    da_do = []
    monkeypatch.setattr(svc, "xac_nhan_do_hang", lambda did, nid: da_do.append(did))
    kq = svc.do_tat_ca("chuyen-1", "nd")
    assert da_do == ["a"] and kq["so_luong"] == 1 and "VB" in kq["loi"][0]


def test_bao_that_lac_loai_khong_hop_le(monkeypatch):
    _chuan_bi_bao_cao(monkeypatch, _don(trang_thai="da_len_xe", chuyen_id="chuyen-1"))
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "mô tả", "nguoi-dung-1", "khac")
