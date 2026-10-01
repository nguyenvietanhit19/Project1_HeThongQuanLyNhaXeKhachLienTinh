"""Unit test cho chuyen_xe_service — giả lập Repository bằng monkeypatch,
không cần DB thật (ARCHITECTURE.md mục 3 'tests/unit')."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import chuyen_xe_service as svc
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _nhan_su_phu_xe(**overrides):
    data = {"id": "nhan-su-1", "ho_ten": "Phu Xe A", "chuc_danh": "phu_xe"}
    data.update(overrides)
    return data


def _chuyen(**overrides):
    data = {"id": "chuyen-1", "tuyen_id": "tuyen-1", "xe_id": "xe-1", "trang_thai": "chua_khoi_hanh", "chieu": "xuoi",
            "gio_khoi_hanh": datetime(2020, 1, 1, tzinfo=timezone.utc)}
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
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: goi.setdefault("cid", cid) and True)
    svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")
    assert goi["cid"] == "chuyen-1"


@pytest.mark.parametrize("trang_thai", ["dang_chay", "gap_su_co", "hoan_thanh", "da_huy"])
def test_xac_nhan_xuat_phat_chi_cho_phep_khi_chua_khoi_hanh(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    goi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: goi.append(cid) or True)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")
    assert goi == []


def test_xac_nhan_xuat_phat_bao_loi_khi_chuyen_vua_doi_trang_thai(monkeypatch):
    # Giữa lúc kiểm tra và lúc ghi, người khác đã xác nhận trước (UPDATE ... WHERE trang_thai = 'chua_khoi_hanh' không khớp dòng nào)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen())
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: False)
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")


def test_xac_nhan_xuat_phat_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    def tu_choi(cid, nid):
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", tu_choi)
    goi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: goi.append(cid) or True)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-khac")
    assert goi == []


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
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: True)
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, tt: [])
    assert svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1") is False


def test_xac_nhan_toi_diem_diem_cuoi_hoan_thanh(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": "d2", "thu_tu": 2}])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: True)
    goi = {}
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: goi.setdefault("cid", cid))
    assert svc.xac_nhan_toi_diem("chuyen-1", "d3", "nguoi-dung-1") is True
    assert goi["cid"] == "chuyen-1"


def test_xac_nhan_toi_diem_gui_thong_bao_eta_cho_khach_o_diem_sau(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2, "Diem B"), _diem("d3", 3)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: True)
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
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: True)
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
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: True)
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


def test_xac_nhan_toi_diem_bao_loi_khi_diem_vua_duoc_ghi_boi_nguoi_khac(monkeypatch):
    # Bấm đúp / 2 phụ xe cùng bấm: lần kiểm tra thấy chưa có, nhưng INSERT ... ON CONFLICT DO NOTHING không ghi được dòng nào
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2)])
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: False)
    hoan_thanh = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: hoan_thanh.append(cid))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")
    assert hoan_thanh == []  # không được chuyển hoan_thanh khi chính lần này không ghi được điểm


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_xac_nhan_toi_diem_chuyen_khong_con_dang_chay(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1")


def test_xac_nhan_toi_diem_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    def tu_choi(cid, nid):
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", tu_choi)
    with pytest.raises(KhongDuQuyen):
        svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-khac")


def test_xac_nhan_toi_diem_trung_gian_khong_hoan_thanh(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(
        svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tid: [_diem("d1", 1), _diem("d2", 2), _diem("d3", 3)]
    )
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [])
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: True)
    hoan_thanh = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: hoan_thanh.append(cid))
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, thu_tu: [])
    assert svc.xac_nhan_toi_diem("chuyen-1", "d2", "nguoi-dung-1") is False
    assert hoan_thanh == []


@pytest.mark.parametrize("ly_do", ["", "   "])
def test_bao_su_co_thieu_mo_ta(ly_do):
    with pytest.raises(GiaTriLoi):
        svc.bao_su_co("chuyen-1", "loi_nha_xe", ly_do, "nguoi-dung-1")


@pytest.mark.parametrize("trang_thai", ["gap_su_co", "hoan_thanh", "da_huy"])
def test_bao_su_co_khi_chuyen_khong_dang_chay(monkeypatch, trang_thai):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai=trang_thai))
    goi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: goi.append(cid) or True)
    with pytest.raises(GiaTriLoi):
        svc.bao_su_co("chuyen-1", "loi_nha_xe", "hong xe", "nguoi-dung-1")
    assert goi == []


def test_bao_su_co_khong_gui_thong_bao_khi_chuyen_vua_doi_trang_thai(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: False)
    xung_dot, da_gui = [], []
    monkeypatch.setattr(
        svc.chuyen_xe_repo, "gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai", lambda xid, cid: xung_dot.append(cid)
    )
    monkeypatch.setattr(svc, "_gui_thong_bao", lambda nid, nd: da_gui.append(nid))
    with pytest.raises(GiaTriLoi):
        svc.bao_su_co("chuyen-1", "loi_nha_xe", "hong xe", "nguoi-dung-1")
    assert xung_dot == [] and da_gui == []


def test_bao_su_co_phu_xe_khong_thuoc_xe_bi_chan(monkeypatch):
    def tu_choi(cid, nid):
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", tu_choi)
    with pytest.raises(KhongDuQuyen):
        svc.bao_su_co("chuyen-1", "loi_nha_xe", "hong xe", "nguoi-dung-khac")


def test_bao_su_co_loi_khach_quan_van_gui_thong_bao(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(trang_thai="dang_chay"))
    luu = {}
    monkeypatch.setattr(
        svc.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: luu.update(loai=loai, ly_do=ly_do) or True
    )
    monkeypatch.setattr(svc.chuyen_xe_repo, "gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai", lambda xid, cid: None)
    monkeypatch.setattr(svc.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda cid: [{"khach_hang_id": "kh-1"}])
    da_gui = []
    monkeypatch.setattr(svc, "_gui_thong_bao", lambda nid, nd: da_gui.append(nid))
    svc.bao_su_co("chuyen-1", "loi_khach_quan", "sat lo", "nguoi-dung-1")
    assert luu == {"loai": "loi_khach_quan", "ly_do": "sat lo"}
    assert da_gui == ["kh-1"]


GIO_KH = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def _chuan_bi_xuat_phat(monkeypatch, bay_gio):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(gio_khoi_hanh=GIO_KH))
    monkeypatch.setattr(svc, "_bay_gio", lambda: bay_gio)
    goi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_xac_nhan_xuat_phat", lambda cid: goi.append(cid) or True)
    return goi


@pytest.mark.parametrize("som", [timedelta(seconds=1), timedelta(minutes=10), timedelta(hours=5)])
def test_xac_nhan_xuat_phat_som_hon_gio_khoi_hanh_bi_chan(monkeypatch, som):
    goi = _chuan_bi_xuat_phat(monkeypatch, GIO_KH - som)
    with pytest.raises(GiaTriLoi) as loi:
        svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")
    assert "15:00 01/10/2026" in str(loi.value)  # hiển thị giờ Việt Nam (UTC+7)
    assert goi == []


@pytest.mark.parametrize("tre", [timedelta(0), timedelta(minutes=3), timedelta(hours=2)])
def test_xac_nhan_xuat_phat_dung_gio_hoac_muon_hon_duoc_phep(monkeypatch, tre):
    goi = _chuan_bi_xuat_phat(monkeypatch, GIO_KH + tre)
    svc.xac_nhan_xuat_phat("chuyen-1", "nguoi-dung-1")
    assert goi == ["chuyen-1"]
