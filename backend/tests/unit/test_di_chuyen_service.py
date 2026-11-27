"""Unit test cho di_chuyen_service — phụ xe bấm "Bắt đầu di chuyển" rời điểm dừng."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import di_chuyen_service as svc
from app.utils.loi import GiaTriLoi

DIEM = [{"diem_don_tra_id": d, "ten": f"Diem {d}", "thu_tu": i, "thoi_gian_du_kien_phut": (i - 1) * 30}
        for i, d in enumerate(["a", "b", "c"], start=1)]
DA_DANH_DAU = []


def _khach(ve_id="v1", trang_thai="da_thanh_toan", han=None):
    return {"ve_id": ve_id, "id": ve_id, "trang_thai": trang_thai, "han_giu_cho_den": han, "khach_hang_id": None}


def _chuan_bi(monkeypatch, *, dang_o="a", trang_thai="dang_chay", dang_di_chuyen=False, xuong=(), do=(), len_=(), chat=()):
    chuyen = {"id": "c1", "trang_thai": trang_thai, "dang_di_chuyen": dang_di_chuyen, "chieu": "xuoi",
              "gio_khoi_hanh": datetime.now(timezone.utc) - timedelta(hours=3)}  # mọi giờ đón dự kiến đã qua
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: chuyen)
    monkeypatch.setattr(svc, "diem_theo_chieu", lambda c: DIEM)
    monkeypatch.setattr(svc, "diem_xe_vua_roi_hoac_dung", lambda c: next(d for d in DIEM if d["diem_don_tra_id"] == dang_o))
    monkeypatch.setattr(svc.ve_repo, "tim_ve_can_xuong_xe_tai_diem", lambda cid, did: list(xuong))
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_can_do_tai_diem", lambda cid, did: list(do))
    monkeypatch.setattr(svc.ve_repo, "tim_ve_chua_len_tai_diem", lambda cid, did: list(len_))
    monkeypatch.setattr(svc.gui_hang_service, "danh_sach_cho_chat", lambda cid, nid: list(chat))
    monkeypatch.setattr(svc.khong_den_service, "danh_dau_khong_den", lambda ve: DA_DANH_DAU.append(ve["ve_id"]) or True)
    DA_DANH_DAU.clear()
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
    ghi = _chuan_bi(monkeypatch, len_=[_khach()], chat=[{"id": "h1"}])
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


def test_chi_danh_dau_khong_den_sau_khi_xac_nhan(monkeypatch):
    _chuan_bi(monkeypatch, len_=[_khach("v1"), _khach("v2", "giu_cho"), _khach("v3", "giu_cho", han=datetime.now(timezone.utc))])
    with pytest.raises(GiaTriLoi, match="chưa lên xe"):
        svc.bat_dau_di_chuyen("c1", False, "nd")
    assert DA_DANH_DAU == []  # chưa xác nhận thì không ai bị tính
    kq = svc.bat_dau_di_chuyen("c1", True, "nd")
    assert DA_DANH_DAU == ["v1", "v2"]  # vé đã trả + vé trả tại quầy chưa trả; vé giữ tạm có hạn thì không
    assert kq["so_khach_khong_den"] == 2


def test_khong_duoc_roi_diem_doc_duong_truoc_gio_don_du_kien(monkeypatch):
    ghi = _chuan_bi(monkeypatch, dang_o="b", len_=[_khach()])
    chuyen = svc.lay_chuyen_cua_phu_xe("c1", "nd")
    chuyen["gio_khoi_hanh"] = datetime.now(timezone.utc) - timedelta(minutes=20)  # điểm b = +30 phút → còn 10 phút
    with pytest.raises(GiaTriLoi, match="Chưa tới giờ đón dự kiến"):
        svc.bat_dau_di_chuyen("c1", True, "nd")  # xác nhận cảnh báo cũng không vượt được
    assert ghi == [] and DA_DANH_DAU == []
    chuyen["gio_khoi_hanh"] = datetime.now(timezone.utc) - timedelta(minutes=40)  # đã qua giờ đón
    svc.bat_dau_di_chuyen("c1", True, "nd")
    assert ghi == [True] and DA_DANH_DAU == ["v1"]


def test_du_khach_thi_duoc_di_som(monkeypatch):
    ghi = _chuan_bi(monkeypatch, dang_o="b")
    svc.lay_chuyen_cua_phu_xe("c1", "nd")["gio_khoi_hanh"] = datetime.now(timezone.utc)
    svc.bat_dau_di_chuyen("c1", False, "nd")
    assert ghi == [True]


def _chuan_bi_hoan_tac(monkeypatch, *, dang_di_chuyen=True, dang_o="a", ve_trang_thai="khong_den", da_tra=True, trang_thai="dang_chay"):
    _chuan_bi(monkeypatch, dang_o=dang_o, dang_di_chuyen=dang_di_chuyen, trang_thai=trang_thai)
    ve = {"id": "v1", "chuyen_id": "c1", "diem_don_id": "a", "trang_thai": ve_trang_thai, "khach_hang_id": "kh1",
          "gio_thanh_toan": datetime.now(timezone.utc) if da_tra else None, "ma_ve": "VE1", "so_ghe": "A1"}
    monkeypatch.setattr(svc.ve_repo, "tim_theo_id", lambda vid: ve)
    goi = []
    monkeypatch.setattr(svc.khong_den_service, "hoan_tac_khong_den", lambda v: goi.append(v["id"]) or True)
    return goi


def test_hoan_tac_khong_den_khi_xe_chua_toi_diem_ke_tiep(monkeypatch):
    goi = _chuan_bi_hoan_tac(monkeypatch)
    svc.hoan_tac_khong_den("c1", "v1", "nd")
    assert goi == ["v1"]


@pytest.mark.parametrize("kwargs, thong_diep", [
    ({"dang_di_chuyen": False, "dang_o": "b"}, "đã tới điểm kế tiếp"),
    ({"dang_o": "b"}, "đã tới điểm kế tiếp"),          # đã qua điểm sau, xe lại đang chạy
    ({"ve_trang_thai": "da_len_xe"}, "không có gì để hoàn tác"),
    ({"da_tra": False}, "chưa trả tiền"),
    ({"trang_thai": "hoan_thanh"}, "đang chạy"),
])
def test_hoan_tac_khong_den_bi_tu_choi(monkeypatch, kwargs, thong_diep):
    goi = _chuan_bi_hoan_tac(monkeypatch, **kwargs)
    with pytest.raises(GiaTriLoi, match="(?i)" + thong_diep):
        svc.hoan_tac_khong_den("c1", "v1", "nd")
    assert goi == []


@pytest.mark.parametrize("truoc, sau, mo_khoa", [(3, 2, True), (2, 1, False), (4, 3, False)])
def test_hoan_tac_chi_go_khoa_khi_chinh_lan_nay_lam_du_nguong(monkeypatch, truoc, sau, mo_khoa):
    kds = svc.khong_den_service
    dem = iter([truoc, sau])
    monkeypatch.setattr(kds.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: next(dem))
    monkeypatch.setattr(kds.ve_repo, "hoan_tac_khong_den", lambda vid: True)
    monkeypatch.setattr(kds.thong_bao, "gui", lambda *a, **k: None)
    da_mo = []
    monkeypatch.setattr(kds.ho_so_repo, "mo_khoa_thanh_toan_tai_quay", lambda kh: da_mo.append(kh))
    assert kds.hoan_tac_khong_den({"id": "v1", "khach_hang_id": "kh1", "ma_ve": "VE1", "so_ghe": "A1"})
    assert bool(da_mo) is mo_khoa
