"""Unit test phần phụ xe cho chuyến chạy NGƯỢC (THAY_DOI_TUYEN_2_CHIEU.md mục 4.2/4.4).

Tuyến d1 -> d2 -> d3 -> d4 (thu_tu 1..4 theo chiều xuôi). Chuyến `xuoi` đi
d1..d4; chuyến `nguoc` đi d4, d3, d2, d1 — điểm xuất phát là d4, điểm cuối là d1.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import chuyen_xe_service as svc
from app.services import gui_hang_service as hang
from app.utils.loi import GiaTriLoi


GIO_KH = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)


def _diem_tuyen(tid=None):
    # Cố ý trả về theo thu_tu tăng dần (đúng như dia_diem_repository)
    return [{"diem_don_tra_id": f"d{i}", "thu_tu": i, "ten": f"Diem {i}", "thoi_gian_du_kien_phut": (i - 1) * 60} for i in (1, 2, 3, 4)]


def _chuyen(chieu, trang_thai="dang_chay"):
    return {"id": "c1", "tuyen_id": "t1", "xe_id": "xe-1", "trang_thai": trang_thai, "chieu": chieu, "gio_khoi_hanh": GIO_KH}


@pytest.fixture(autouse=True)
def _tuyen(monkeypatch):
    monkeypatch.setattr(svc.dia_diem_repo, "danh_sach_diem_theo_tuyen", _diem_tuyen)


@pytest.fixture(autouse=True)
def _khong_cham_db_khi_dem_bao_cao(monkeypatch):
    monkeypatch.setattr(hang.don_hang_repo, "dem_bao_cao_theo_loai", lambda ids: {})


def _da_toi(monkeypatch, *ids):
    monkeypatch.setattr(svc.chuyen_xe_repo, "lay_diem_da_xac_nhan", lambda cid: [{"diem_don_tra_id": i, "gio_thuc_te": None} for i in ids])


def _ids(diem_list):
    return [d["diem_don_tra_id"] for d in diem_list]


# ---------------------------------------------------------- thứ tự điểm theo chiều
def test_diem_theo_chieu_xuoi_giu_nguyen_thu_tu():
    assert _ids(svc.diem_theo_chieu(_chuyen("xuoi"))) == ["d1", "d2", "d3", "d4"]


def test_diem_theo_chieu_nguoc_dao_nguoc_va_giu_thu_tu_goc():
    ds = svc.diem_theo_chieu(_chuyen("nguoc"))
    assert _ids(ds) == ["d4", "d3", "d2", "d1"]
    assert [d["thu_tu"] for d in ds] == [4, 3, 2, 1]  # thu_tu gốc không bị đổi (dùng cho SQL)


# ---------------------------------------------------------- điểm hiện tại
def test_diem_hien_tai_chuyen_nguoc_chua_toi_diem_nao_la_diem_xuat_phat(monkeypatch):
    _da_toi(monkeypatch)
    assert svc.diem_hien_tai(_chuyen("nguoc"))["diem_don_tra_id"] == "d4"


def test_diem_hien_tai_chuyen_nguoc_la_diem_xa_nhat_theo_huong_di(monkeypatch):
    # Đã tới d3 rồi d2 (thứ tự đúng chiều ngược) -> đang đứng ở d2, KHÔNG phải d3
    _da_toi(monkeypatch, "d3", "d2")
    assert svc.diem_hien_tai(_chuyen("nguoc"))["diem_don_tra_id"] == "d2"


def test_diem_hien_tai_chuyen_xuoi_van_dung(monkeypatch):
    _da_toi(monkeypatch, "d2", "d3")
    assert svc.diem_hien_tai(_chuyen("xuoi"))["diem_don_tra_id"] == "d3"


# ---------------------------------------------------------- hành trình
def test_hanh_trinh_chuyen_nguoc_hien_thi_theo_huong_di(monkeypatch):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen("nguoc"))
    _da_toi(monkeypatch, "d3")
    ht = svc.hanh_trinh("c1", "nd")
    assert _ids(ht) == ["d4", "d3", "d2", "d1"]
    assert [d["thu_tu"] for d in ht] == [1, 2, 3, 4]  # số thứ tự hiển thị theo hướng đi
    assert [d["da_toi"] for d in ht] == [False, True, False, False]


def test_hanh_trinh_gio_du_kien_theo_chieu(monkeypatch):
    # Mốc d1..d4 = 0, 60, 120, 180 phút. Xuôi: d3 tới sau 120'. Ngược: d3 tới sau 180-120 = 60'.
    _da_toi(monkeypatch)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen("xuoi"))
    xuoi = {d["diem_don_tra_id"]: d["gio_du_kien"] for d in svc.hanh_trinh("c1", "nd")}
    assert xuoi["d3"] == GIO_KH + timedelta(minutes=120)
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen("nguoc"))
    nguoc = {d["diem_don_tra_id"]: d["gio_du_kien"] for d in svc.hanh_trinh("c1", "nd")}
    assert nguoc["d4"] == GIO_KH  # điểm xuất phát chiều ngược
    assert nguoc["d3"] == GIO_KH + timedelta(minutes=60)
    assert nguoc["d1"] == GIO_KH + timedelta(minutes=180)


# ---------------------------------------------------------- xác nhận tới điểm
def _chuan_bi_toi_diem(monkeypatch, chieu, da_toi_truoc=()):
    monkeypatch.setattr(svc, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(chieu))
    _da_toi(monkeypatch, *da_toi_truoc)
    ghi, hoan_thanh, hoi_khach = [], [], []
    monkeypatch.setattr(svc.chuyen_xe_repo, "them_lich_su_diem_dung", lambda cid, did: ghi.append(did) or True)
    monkeypatch.setattr(svc.chuyen_xe_repo, "cap_nhat_hoan_thanh", lambda cid: hoan_thanh.append(cid))
    monkeypatch.setattr(svc.ve_repo, "tim_khach_cho_don_sau_diem", lambda cid, tt: hoi_khach.append(tt) or [])
    return ghi, hoan_thanh, hoi_khach


def test_toi_diem_chuyen_nguoc_diem_dau_tien_la_d3_khong_phai_d2(monkeypatch):
    ghi, _, _ = _chuan_bi_toi_diem(monkeypatch, "nguoc")
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("c1", "d2", "nd")  # nhảy cóc d3
    assert ghi == []
    assert svc.xac_nhan_toi_diem("c1", "d3", "nd") is False
    assert ghi == ["d3"]


def test_toi_diem_chuyen_nguoc_diem_xuat_phat_khong_phai_diem_den(monkeypatch):
    ghi, _, _ = _chuan_bi_toi_diem(monkeypatch, "nguoc")
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("c1", "d4", "nd")  # d4 là nơi xuất phát của chuyến ngược
    assert ghi == []


def test_toi_diem_chuyen_nguoc_diem_cuoi_la_d1_thi_hoan_thanh(monkeypatch):
    ghi, hoan_thanh, _ = _chuan_bi_toi_diem(monkeypatch, "nguoc", da_toi_truoc=("d3", "d2"))
    assert svc.xac_nhan_toi_diem("c1", "d1", "nd") is True
    assert hoan_thanh == ["c1"]


def test_toi_diem_chuyen_nguoc_toi_d2_chua_phai_diem_cuoi(monkeypatch):
    _, hoan_thanh, _ = _chuan_bi_toi_diem(monkeypatch, "nguoc", da_toi_truoc=("d3",))
    assert svc.xac_nhan_toi_diem("c1", "d2", "nd") is False
    assert hoan_thanh == []


def test_toi_diem_chuyen_xuoi_d1_la_diem_xuat_phat_va_d4_la_diem_cuoi(monkeypatch):
    _, hoan_thanh, _ = _chuan_bi_toi_diem(monkeypatch, "xuoi", da_toi_truoc=("d2", "d3"))
    with pytest.raises(GiaTriLoi):
        svc.xac_nhan_toi_diem("c1", "d1", "nd")
    assert svc.xac_nhan_toi_diem("c1", "d4", "nd") is True
    assert hoan_thanh == ["c1"]


def test_toi_diem_hoi_khach_o_cac_diem_phia_sau_bang_thu_tu_goc_cua_diem_vua_toi(monkeypatch):
    # Repository tự lật điều kiện theo chieu của chuyến; service chỉ truyền thu_tu GỐC của điểm vừa tới
    _, _, hoi_khach = _chuan_bi_toi_diem(monkeypatch, "nguoc")
    svc.xac_nhan_toi_diem("c1", "d3", "nd")
    assert hoi_khach == [3]


# ---------------------------------------------------------- UC-26: hàng cùng chiều
def _don(gui, nhan, **kw):
    d = {"id": f"{gui}-{nhan}", "tuyen_id": "t1", "chuyen_id": None, "trang_thai": "cho_van_chuyen",
         "diem_gui_id": gui, "diem_nhan_id": nhan, "ten_nguoi_nhan": "N", "can_nang_kg": 1, "ma_van_don": "M", "ngay_tao": None}
    d.update(kw)
    return d


def _chieu_van_chuyen(gui, nhan):
    """Giống don_hang_repository.kiem_tra_diem_thuoc_tuyen: so thu_tu GỐC (xuôi) của điểm gửi/nhận."""
    return {"chieu_van_chuyen": "xuoi" if gui < nhan else "nguoc"}


def _chuan_bi_chat(monkeypatch, chieu_chuyen, don):
    monkeypatch.setattr(hang, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen(chieu_chuyen))
    _da_toi(monkeypatch)  # chưa tới điểm nào -> đang ở điểm xuất phát của chuyến
    monkeypatch.setattr(hang.don_hang_repo, "tim_theo_id", lambda did: don)
    monkeypatch.setattr(
        hang.don_hang_repo, "kiem_tra_diem_thuoc_tuyen",
        lambda tid, gui, nhan: _chieu_van_chuyen(gui, nhan),
    )
    monkeypatch.setattr(hang.don_hang_repo, "tim_chuyen_xe_theo_id", lambda cid: {"chieu": chieu_chuyen})
    goi = []
    monkeypatch.setattr(
        hang.don_hang_repo, "cap_nhat_chat_hang_len_chuyen",
        lambda did, cid, nd=None: goi.append(did) or {"id": did},
    )
    return goi


def test_danh_sach_cho_chat_chuyen_nguoc_loc_theo_chieu_va_diem_dung(monkeypatch):
    monkeypatch.setattr(hang, "lay_chuyen_cua_phu_xe", lambda cid, nid: _chuyen("nguoc"))
    _da_toi(monkeypatch)  # đang ở d4 (xuất phát của chuyến ngược)
    hoi = []
    monkeypatch.setattr(
        hang.don_hang_repo, "lay_danh_sach_cho_xep_xe",
        lambda tid, cid=None: hoi.append((tid, cid)) or [_don("d4", "d2", id="a"), _don("d4", "d1", id="b"), _don("d3", "d1", id="khac-diem")],
    )
    ket_qua = hang.danh_sach_cho_chat("c1", "nd")
    assert hoi == [("t1", "c1")]  # repository lọc cùng chiều theo chuyen_id
    assert [d["id"] for d in ket_qua] == ["a", "b"]  # service chỉ giữ đơn chờ đúng tại d4


def test_xac_nhan_chat_don_nguoc_chieu_len_chuyen_xuoi_bi_chan(monkeypatch):
    # Đơn chờ ở d1 (điểm xuất phát chuyến xuôi) nhưng đi theo chiều NGƯỢC -> không được chất lên chuyến xuôi
    goi = _chuan_bi_chat(monkeypatch, "xuoi", _don("d1", "d1"))
    monkeypatch.setattr(hang.don_hang_repo, "kiem_tra_diem_thuoc_tuyen", lambda tid, gui, nhan: {"chieu_van_chuyen": "nguoc"})
    with pytest.raises(GiaTriLoi, match="chiều"):
        hang.xac_nhan_chat_hang("don", "c1", "nd")
    assert goi == []


def test_xac_nhan_chat_don_cung_chieu_chuyen_nguoc_thanh_cong(monkeypatch):
    goi = _chuan_bi_chat(monkeypatch, "nguoc", _don("d4", "d2"))
    hang.xac_nhan_chat_hang("don", "c1", "nd")
    assert goi == ["don"]


def test_xac_nhan_chat_don_xuoi_len_chuyen_nguoc_bi_chan(monkeypatch):
    # Đơn d1 -> d3 (xuôi), chuyến ngược đứng ở d4: đã bị chặn vì không chờ tại điểm xe đứng
    goi = _chuan_bi_chat(monkeypatch, "nguoc", _don("d1", "d3"))
    with pytest.raises(GiaTriLoi):
        hang.xac_nhan_chat_hang("don", "c1", "nd")
    assert goi == []
