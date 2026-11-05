"""Unit test cho di_chuyen_service — phụ xe bấm "Bắt đầu di chuyển" rời điểm dừng."""

import pytest

from app.services import di_chuyen_service as svc
from app.utils.loi import GiaTriLoi

DIEM = [{"diem_don_tra_id": d, "ten": f"Diem {d}", "thu_tu": i} for i, d in enumerate(["a", "b", "c"], start=1)]


def _chuan_bi(monkeypatch, *, dang_o="a", trang_thai="dang_chay", dang_di_chuyen=False, xuong=(), do=(), len_=(), chat=()):
    chuyen = {"id": "c1", "trang_thai": trang_thai, "dang_di_chuyen": dang_di_chuyen}
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen)
    monkeypatch.setattr(svc, "diem_theo_chieu", lambda c: DIEM)
    monkeypatch.setattr(svc, "diem_xe_vua_roi_hoac_dung", lambda c: next(d for d in DIEM if d["diem_don_tra_id"] == dang_o))
    monkeypatch.setattr(svc.ve_repo, "tim_ve_can_xuong_xe_tai_diem", lambda cid, did: list(xuong))
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_can_do_tai_diem", lambda cid, did: list(do))
    monkeypatch.setattr(svc.ve_repo, "tim_ve_chua_len_tai_diem", lambda cid, did: list(len_))
    monkeypatch.setattr(svc.gui_hang_service, "danh_sach_cho_chat", lambda cid, nid: list(chat))
    ghi = []
    monkeypatch.setattr(svc.chuyen_xe_repo, "dat_dang_di_chuyen", lambda cid, v: ghi.append(v) or True)
    return ghi


def test_bat_dau_di_chuyen_khi_khong_con_viec(monkeypatch):
    ghi = _chuan_bi(monkeypatch)
    kq = svc.bat_dau_di_chuyen("c1", False, "nd")
    assert ghi == [True] and kq["diem_ke_tiep"] == "Diem b"


def test_bi_chan_khi_con_khach_chua_xuong(monkeypatch):
    ghi = _chuan_bi(monkeypatch, dang_o="b", xuong=[{"ve_id": "v1"}])
    with pytest.raises(GiaTriLoi, match="chưa xuống xe"):
        svc.bat_dau_di_chuyen("c1", True, "nd")  # bỏ qua cảnh báo cũng không vượt được chặn
    assert ghi == []


def test_bi_chan_khi_con_hang_chua_do(monkeypatch):
    ghi = _chuan_bi(monkeypatch, dang_o="b", do=[{"id": "h1"}])
    with pytest.raises(GiaTriLoi, match="chưa dỡ"):
        svc.bat_dau_di_chuyen("c1", True, "nd")
    assert ghi == []


def test_canh_bao_khi_con_khach_chua_len_hoac_hang_chua_chat(monkeypatch):
    ghi = _chuan_bi(monkeypatch, len_=[{"ve_id": "v1"}], chat=[{"id": "h1"}])
    with pytest.raises(GiaTriLoi, match="chưa lên xe.*chưa chất"):
        svc.bat_dau_di_chuyen("c1", False, "nd")
    assert ghi == []
    svc.bat_dau_di_chuyen("c1", True, "nd")  # đã xem cảnh báo → đi được
    assert ghi == [True]


def test_khong_o_diem_cuoi(monkeypatch):
    _chuan_bi(monkeypatch, dang_o="c")
    with pytest.raises(GiaTriLoi, match="điểm cuối"):
        svc.bat_dau_di_chuyen("c1", False, "nd")


@pytest.mark.parametrize("kwargs, thong_diep", [
    ({"trang_thai": "gap_su_co"}, "đang chạy"),
    ({"dang_di_chuyen": True}, "đã bắt đầu di chuyển"),
])
def test_bat_dau_di_chuyen_sai_trang_thai(monkeypatch, kwargs, thong_diep):
    ghi = _chuan_bi(monkeypatch, **kwargs)
    with pytest.raises(GiaTriLoi, match=thong_diep):
        svc.bat_dau_di_chuyen("c1", False, "nd")
    assert ghi == []



def test_xuat_phat_tai_diem_dau_khi_chuyen_chua_khoi_hanh(monkeypatch):
    ghi = _chuan_bi(monkeypatch, trang_thai="chua_khoi_hanh")
    monkeypatch.setattr(svc, "kiem_tra_co_the_xuat_phat", lambda chuyen: None)
    xuat_phat = []
    monkeypatch.setattr(svc, "xac_nhan_xuat_phat", lambda cid, nid: xuat_phat.append(cid))
    svc.bat_dau_di_chuyen("c1", False, "nd")
    assert xuat_phat == ["c1"] and ghi == []  # xuất phát đã kèm pha di chuyển, không ghi lần 2


def test_chua_den_gio_chay_thi_khong_xuat_phat_duoc(monkeypatch):
    ghi = _chuan_bi(monkeypatch, trang_thai="chua_khoi_hanh")

    def som(chuyen):
        raise GiaTriLoi("Chưa đến giờ khởi hành")

    monkeypatch.setattr(svc, "kiem_tra_co_the_xuat_phat", som)
    with pytest.raises(GiaTriLoi, match="giờ khởi hành"):
        svc.bat_dau_di_chuyen("c1", True, "nd")
    assert ghi == []
