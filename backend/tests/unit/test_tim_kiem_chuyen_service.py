"""Unit test cho tra cứu chuyến công khai (UC-04) — hàm thuần + service với Repository giả lập."""

import datetime
from decimal import Decimal

import pytest

from app.services import tim_kiem_chuyen_service as svc
from app.utils.loi import GiaTriLoi

VN = svc.MUI_GIO_VN
A, B, C = "kv-a", "kv-b", "kv-c"


def _gia(di, den, gia_goc, tu=None, den_ngay=None, tuyen="t1"):
    return {"tuyen_id": tuyen, "diem_di_id": di, "diem_den_id": den, "gia_goc": gia_goc, "ap_dung_tu": tu, "ap_dung_den": den_ngay}


# ---------------------------------------------------------
# chon_gia
# ---------------------------------------------------------
def test_gia_chuyen_xuoi_dung_cap_di_den_va_nhan_he_so():
    gia = svc.chon_gia([_gia(A, C, 200000)], "xuoi", A, C, datetime.date(2026, 10, 5), Decimal("1.50"))
    assert gia == 300000


def test_gia_chuyen_nguoc_phai_dao_cap():
    # gia_ve lưu theo chiều xuôi (A→C); khách đi ngược C→A vẫn tra ra đúng dòng này
    gia = svc.chon_gia([_gia(A, C, 200000)], "nguoc", C, A, datetime.date(2026, 10, 5), Decimal("1"))
    assert gia == 200000


def test_gia_chuyen_nguoc_khong_nham_voi_cap_xuoi_cung_chieu_khach_tim():
    # Chỉ có dòng giá (C→A) = không phải thứ tự xuôi → chuyến ngược tìm C→A tra cặp (A,C) => không thấy
    assert svc.chon_gia([_gia(C, A, 200000)], "nguoc", C, A, datetime.date(2026, 10, 5), Decimal("1")) is None


def test_gia_mua_dang_ap_dung_uu_tien_hon_gia_thuong():
    dong = [_gia(A, C, 200000), _gia(A, C, 260000, tu=datetime.date(2026, 12, 20), den_ngay=datetime.date(2027, 1, 5))]
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2026, 12, 25), Decimal("1")) == 260000
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2026, 10, 5), Decimal("1")) == 200000  # ngoài mùa


def test_gia_mua_ngay_dau_va_cuoi_deu_tinh():
    dong = [_gia(A, C, 100, tu=datetime.date(2026, 12, 20), den_ngay=datetime.date(2027, 1, 5)), _gia(A, C, 50)]
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2026, 12, 20), Decimal("1")) == 100
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2027, 1, 5), Decimal("1")) == 100
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2027, 1, 6), Decimal("1")) == 50


def test_gia_chi_co_gia_mua_ngoai_mua_thi_khong_co_gia():
    dong = [_gia(A, C, 100, tu=datetime.date(2026, 12, 20), den_ngay=datetime.date(2027, 1, 5))]
    assert svc.chon_gia(dong, "xuoi", A, C, datetime.date(2026, 10, 5), Decimal("1")) is None


def test_gia_lam_tron_len_dong():
    assert svc.chon_gia([_gia(A, C, 100001)], "xuoi", A, C, datetime.date(2026, 10, 5), Decimal("1.25")) == 125001


# ---------------------------------------------------------
# tinh_ghe_dang_giu — đoạn nửa mở [don, tra)
# ---------------------------------------------------------
def _ve(so_ghe, hl_don, hl_tra):
    return {"so_ghe": so_ghe, "hl_don": hl_don, "hl_tra": hl_tra}


def test_ghe_giu_doan_ke_nhau_khong_giao():
    # ghế 1 giữ A→B [0,1); khách tìm B→C [1,3) => không giao => ghế vẫn trống
    assert svc.tinh_ghe_dang_giu([_ve("1", 0, 1)], 1, 3) == set()


def test_ghe_giu_doan_giao_nhau():
    assert svc.tinh_ghe_dang_giu([_ve("1", 0, 2)], 1, 3) == {"1"}
    assert svc.tinh_ghe_dang_giu([_ve("1", 1, 2)], 0, 3) == {"1"}


def test_ghe_giu_chuyen_nguoc_hl_am():
    # hl âm của chuyến ngược: ve [-3,-2), khách [-2,0) => kề nhau, không giao
    assert svc.tinh_ghe_dang_giu([_ve("1", -3, -2)], -2, 0) == set()
    assert svc.tinh_ghe_dang_giu([_ve("1", -3, -1)], -2, 0) == {"1"}


# ---------------------------------------------------------
# tim_chuyen / so_do_ghe_chuyen — Repository giả lập
# ---------------------------------------------------------
def _ngay_mai():
    return datetime.datetime.now(VN).date() + datetime.timedelta(days=1)


def _hang(ngay, **ghi_de):
    gio = datetime.datetime.combine(ngay, datetime.time(7, 0), tzinfo=VN)
    du_lieu = {
        "id": "c1", "ma": "T001-LX001-x", "tuyen_id": "t1", "chieu": "xuoi", "gio_khoi_hanh": gio, "dang_hoan": False,
        "ma_loai_xe": "LX001", "ten_loai_xe": "Giường", "he_so_gia": Decimal("1.00"), "tong_ghe": 3,
        "so_do_ghe": [
            {"ma_ghe": "A1", "tang": 1, "x": 0, "y": 0},
            {"ma_ghe": "A2", "tang": 1, "x": 50, "y": 0},
            {"ma_ghe": "B1", "tang": 2, "x": 0, "y": 0},
        ],
        "diem_don_id": "d1", "ten_diem_don": "VP A", "hl_don": 0, "phut_don": 0,
        "diem_tra_id": "d3", "ten_diem_tra": "VP C", "hl_tra": 3, "phut_tra": 150,
        "bien_so": None,
    }
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap(monkeypatch, hang, dong_gia, ve=()):
    monkeypatch.setattr(svc.repo, "tim_khu_vuc_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(svc.repo, "tim_chuyen", lambda *a, **k: hang)
    monkeypatch.setattr(svc.repo, "danh_sach_gia_ve", lambda *a: dong_gia)
    monkeypatch.setattr(svc.repo, "tim_doan_ve_dang_giu", lambda ids: list(ve))


def test_tim_chuyen_diem_di_trung_diem_den_bi_chan():
    with pytest.raises(GiaTriLoi, match="khác nhau"):
        svc.tim_chuyen(A, A, _ngay_mai())


def test_tim_chuyen_ngay_qua_khu_bi_chan(monkeypatch):
    monkeypatch.setattr(svc.repo, "tim_khu_vuc_theo_id", lambda _id: {"id": _id})
    with pytest.raises(GiaTriLoi, match="đã qua"):
        svc.tim_chuyen(A, C, datetime.date(2020, 1, 1))


def test_tim_chuyen_khu_vuc_khong_ton_tai(monkeypatch):
    monkeypatch.setattr(svc.repo, "tim_khu_vuc_theo_id", lambda _id: None)
    with pytest.raises(GiaTriLoi, match="không tồn tại"):
        svc.tim_chuyen(A, C, _ngay_mai())


def test_tim_chuyen_tinh_gia_ghe_trong_va_gio(monkeypatch):
    ngay = _ngay_mai()
    _gia_lap(monkeypatch, [_hang(ngay)], [_gia(A, C, 200000)], ve=[{"chuyen_id": "c1", "so_ghe": "A1", "hl_don": 0, "hl_tra": 1}])
    the = svc.tim_chuyen(A, C, ngay)
    assert len(the) == 1
    assert the[0]["gia"] == 200000
    assert the[0]["so_ghe_trong"] == 2  # 3 ghế, A1 bị giữ
    assert the[0]["gio_den_du_kien"] - the[0]["gio_don_du_kien"] == datetime.timedelta(minutes=150)


def test_tim_chuyen_bo_chuyen_chua_co_gia(monkeypatch):
    ngay = _ngay_mai()
    _gia_lap(monkeypatch, [_hang(ngay)], [])
    assert svc.tim_chuyen(A, C, ngay) == []


def test_so_do_ghe_khong_lo_thong_tin_khach_va_danh_dau_ghe(monkeypatch):
    ngay = _ngay_mai()
    _gia_lap(monkeypatch, [_hang(ngay)], [_gia(A, C, 200000)], ve=[{"chuyen_id": "c1", "so_ghe": "A2", "hl_don": 0, "hl_tra": 3}])
    monkeypatch.setattr(
        svc.repo,
        "danh_sach_diem_cua_chuyen",
        lambda cid, kv: [{"diem_id": "d1", "ten": "VP A", "loai": "van_phong", "hl": 0, "phut": 0}]
        if kv == A
        else [{"diem_id": "d3", "ten": "VP C", "loai": "van_phong", "hl": 3, "phut": 150}],
    )
    ct = svc.so_do_ghe_chuyen("c1", A, C)
    trang_thai = {g["ma_ghe"]: g["trang_thai"] for g in ct["so_do_ghe"]}
    assert trang_thai == {"A1": "trong", "A2": "da_co_nguoi", "B1": "trong"}
    assert ct["so_tang"] == 2
    assert ct["so_ghe_trong"] == 2
    assert [d["ten"] for d in ct["diem_don_co_the_chon"]] == ["VP A"]
    assert [d["ten"] for d in ct["diem_tra_co_the_chon"]] == ["VP C"]
    assert "khach_hang_id" not in str(ct)


def test_so_do_ghe_chuyen_khong_con_mo_ban(monkeypatch):
    _gia_lap(monkeypatch, [], [])
    with pytest.raises(GiaTriLoi, match="không còn mở bán"):
        svc.so_do_ghe_chuyen("c1", A, C)
