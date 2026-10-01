"""Unit test phần hàng gửi của phụ xe (UC-26, UC-27, UC-28) — giả lập
Repository bằng monkeypatch, không cần DB thật. File riêng, không đụng
test_gui_hang_service.py (phần nhân viên gửi hàng)."""

import pytest

from app.services import gui_hang_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "xe_id": "xe-1", "trang_thai": "dang_chay", "chieu": "xuoi"}
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
def _tuyen_3_diem(monkeypatch):
    """Tuyến d1 -> d2 -> d3 (thu_tu 1,2,3 theo chiều xuôi)."""
    monkeypatch.setattr(
        svc.chuyen_xe_service.dia_diem_repo,
        "danh_sach_diem_theo_tuyen",
        lambda tid: [{"diem_don_tra_id": f"d{i}", "thu_tu": i, "ten": f"Diem {i}"} for i in (1, 2, 3)],
    )


def test_danh_sach_cho_chat_chi_lay_don_tai_diem_hien_tai(monkeypatch):
    _tuyen_3_diem(monkeypatch)
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
    _tuyen_3_diem(monkeypatch)
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


# ---------------------------------------------------------------- UC-27
def test_danh_sach_cho_do_lay_don_tai_diem_hien_tai(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc, "diem_hien_tai", lambda chuyen: {"diem_don_tra_id": "d3"})
    hoi = {}
    monkeypatch.setattr(
        svc.don_hang_repo, "tim_don_can_do_tai_diem", lambda cid, did: hoi.update(cid=cid, did=did) or [{"id": "don-1"}]
    )
    assert svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1") == [{"id": "don-1"}]
    assert hoi == {"cid": "chuyen-1", "did": "d3"}


@pytest.mark.parametrize("trang_thai", ["dang_chay", "hoan_thanh"])
def test_danh_sach_cho_do_cho_phep_chuyen_dang_chay_va_vua_hoan_thanh(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    monkeypatch.setattr(svc, "diem_hien_tai", lambda chuyen: {"diem_don_tra_id": "d3"})
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_can_do_tai_diem", lambda cid, did: [])
    assert svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1") == []


@pytest.mark.parametrize("trang_thai", ["chua_khoi_hanh", "gap_su_co", "da_huy"])
def test_danh_sach_cho_do_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.danh_sach_cho_do("chuyen-1", "nguoi-dung-1")


def _chuan_bi_do(monkeypatch, chuyen=None, don=None, diem_da_toi=("d1", "d3"), do_duoc=True):
    don_mac_dinh = _don(chuyen_id="chuyen-1", trang_thai="da_len_xe") if don is None else don
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don_mac_dinh)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen or _chuyen())
    monkeypatch.setattr(
        svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": d} for d in diem_da_toi]
    )
    goi = []
    monkeypatch.setattr(svc.don_hang_repo, "do_hang_neu_dang_tren_xe", lambda did: goi.append(did) or do_duoc)
    return goi


def test_xac_nhan_do_hang_thanh_cong(monkeypatch):
    goi = _chuan_bi_do(monkeypatch)
    svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == ["don-1"]


def test_xac_nhan_do_hang_cho_phep_chuyen_vua_hoan_thanh(monkeypatch):
    goi = _chuan_bi_do(monkeypatch, chuyen=_chuyen(trang_thai="hoan_thanh"))
    svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == ["don-1"]


def test_xac_nhan_do_hang_xe_chua_toi_diem_nhan(monkeypatch):
    goi = _chuan_bi_do(monkeypatch, diem_da_toi=("d2",))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_hang_khong_tim_thay_don(monkeypatch):
    goi = _chuan_bi_do(monkeypatch)
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: None)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_hang_don_chua_tung_len_chuyen(monkeypatch):
    goi = _chuan_bi_do(monkeypatch, don=_don(chuyen_id=None))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["cho_van_chuyen", "cho_lay", "da_giao", "qua_han_luu_kho"])
def test_xac_nhan_do_hang_don_khong_o_trang_thai_da_len_xe(monkeypatch, trang_thai):
    goi = _chuan_bi_do(monkeypatch, don=_don(chuyen_id="chuyen-1", trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == []


@pytest.mark.parametrize("trang_thai", ["chua_khoi_hanh", "gap_su_co", "da_huy"])
def test_xac_nhan_do_hang_chuyen_sai_trang_thai(monkeypatch, trang_thai):
    goi = _chuan_bi_do(monkeypatch, chuyen=_chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_do_hang_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    goi = _chuan_bi_do(monkeypatch)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-khac")
    assert goi == []


def test_xac_nhan_do_hang_bam_dup_khong_do_lai(monkeypatch):
    # UPDATE ... WHERE trang_thai = 'da_len_xe' không khớp dòng nào (đã dỡ ở lần bấm trước)
    _chuan_bi_do(monkeypatch, do_duoc=False)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_do_hang_cua_phu_xe("don-1", "nguoi-dung-1")


# ---------------------------------------------------------------- UC-28
def _chuan_bi_bao_cao(monkeypatch, don=None, chuyen_cua_toi=None):
    don_mac_dinh = _don(chuyen_id="chuyen-1", trang_thai="da_len_xe", ma_van_don="VD01", nhan_vien_gui_id="nv-gui-1") if don is None else don
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don_mac_dinh)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(
        svc.chuyen_xe_service, "danh_sach_chuyen_cua_toi", lambda nid: [{"tuyen_id": "tuyen-1"}] if chuyen_cua_toi is None else chuyen_cua_toi
    )
    ghi = []
    monkeypatch.setattr(svc.bao_cao_repo, "tao", lambda did, nid, mo_ta: ghi.append((did, nid, mo_ta)))
    thong_bao = []
    monkeypatch.setattr(svc.thong_bao_repo, "tao", lambda nid, nd: thong_bao.append((nid, nd)))
    monkeypatch.setattr(svc, "broadcast_sync", lambda nid, nd: None)
    return ghi, thong_bao


def test_bao_that_lac_don_tren_xe_ghi_bao_cao_va_bao_nhan_vien_gui_hang(monkeypatch):
    ghi, thong_bao = _chuan_bi_bao_cao(monkeypatch)
    svc.bao_that_lac("don-1", "  vo thung  ", "nguoi-dung-1")
    assert ghi == [("don-1", "nguoi-dung-1", "vo thung")]  # mô tả đã được cắt khoảng trắng
    assert len(thong_bao) == 1 and thong_bao[0][0] == "nv-gui-1" and "VD01" in thong_bao[0][1]


@pytest.mark.parametrize("mo_ta", ["", "   "])
def test_bao_that_lac_thieu_mo_ta(monkeypatch, mo_ta):
    ghi, _ = _chuan_bi_bao_cao(monkeypatch)
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", mo_ta, "nguoi-dung-1")
    assert ghi == []


def test_bao_that_lac_khong_tim_thay_don(monkeypatch):
    ghi, _ = _chuan_bi_bao_cao(monkeypatch)
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: None)
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "hu hong", "nguoi-dung-1")
    assert ghi == []


def test_bao_that_lac_don_cua_chuyen_khac_xe_bi_chan(monkeypatch):
    ghi, _ = _chuan_bi_bao_cao(monkeypatch)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", _khong_thuoc_xe)
    with pytest.raises(KhongDuQuyen):
        svc.bao_that_lac("don-1", "hu hong", "nguoi-dung-khac")
    assert ghi == []


def test_bao_that_lac_don_dang_cho_chat_cung_tuyen_duoc_phep(monkeypatch):
    # Hư hỏng phát hiện ngay lúc cầm kiện hàng lên xe (UC-26) — đơn chưa có chuyến
    ghi, _ = _chuan_bi_bao_cao(
        monkeypatch,
        don=_don(chuyen_id=None, trang_thai="cho_van_chuyen", ma_van_don="VD02", nhan_vien_gui_id="nv-gui-1"),
    )
    svc.bao_that_lac("don-1", "rach bao bi", "nguoi-dung-1")
    assert len(ghi) == 1


def test_bao_that_lac_don_dang_cho_chat_khac_tuyen_bi_chan(monkeypatch):
    ghi, _ = _chuan_bi_bao_cao(
        monkeypatch,
        don=_don(chuyen_id=None, trang_thai="cho_van_chuyen", tuyen_id="tuyen-khac", nhan_vien_gui_id="nv-gui-1"),
    )
    with pytest.raises(KhongDuQuyen):
        svc.bao_that_lac("don-1", "rach bao bi", "nguoi-dung-1")
    assert ghi == []


def test_bao_that_lac_phu_xe_chua_co_chuyen_nao_bi_chan(monkeypatch):
    ghi, _ = _chuan_bi_bao_cao(
        monkeypatch,
        don=_don(chuyen_id=None, trang_thai="cho_van_chuyen", nhan_vien_gui_id="nv-gui-1"),
        chuyen_cua_toi=[],
    )
    with pytest.raises(KhongDuQuyen):
        svc.bao_that_lac("don-1", "rach bao bi", "nguoi-dung-1")
    assert ghi == []


@pytest.mark.parametrize("trang_thai", ["cho_lay", "da_giao", "qua_han_luu_kho"])
def test_bao_that_lac_don_ngoai_giai_doan_chat_do_khong_co_chuyen(monkeypatch, trang_thai):
    # Đơn không gắn chuyến mà cũng không còn chờ chất: không thuộc UC-26/27 nên phụ xe không báo qua màn hình này
    ghi, _ = _chuan_bi_bao_cao(
        monkeypatch, don=_don(chuyen_id=None, trang_thai=trang_thai, nhan_vien_gui_id="nv-gui-1")
    )
    with pytest.raises(GiaTriLoi):
        svc.bao_that_lac("don-1", "hu hong", "nguoi-dung-1")
    assert ghi == []


def test_bao_that_lac_khong_doi_trang_thai_don(monkeypatch):
    # Báo cáo không chặn UC-26/27: không gọi bất kỳ hàm đổi trạng thái đơn nào
    _chuan_bi_bao_cao(monkeypatch)
    doi_trang_thai = []
    for ten in ("cap_nhat_chat_hang_len_chuyen", "chat_len_chuyen_neu_dang_cho", "do_hang_neu_dang_tren_xe", "cap_nhat_do_hang_tai_diem"):
        monkeypatch.setattr(svc.don_hang_repo, ten, lambda *a, _ten=ten: doi_trang_thai.append(_ten))
    svc.bao_that_lac("don-1", "hu hong", "nguoi-dung-1")
    assert doi_trang_thai == []
