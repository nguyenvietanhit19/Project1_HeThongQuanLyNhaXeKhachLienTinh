"""Unit test cho trang "Chuyến" (UC-18) — sửa giờ chuyến, giả lập Repository."""

import datetime

import pytest

from app.services import chuyen_service as cs
from app.utils.loi import GiaTriLoi

VN = cs.MUI_GIO_VN


def _chuyen(ngay, **ghi_de):
    du_lieu = {
        "id": "c-1",
        "loai_xe_id": "lx-1",
        "xe_id": None,
        "trang_thai": "chua_khoi_hanh",
        "so_ve_dang_hoat_dong": 0,
        "gio_khoi_hanh": datetime.datetime.combine(ngay, datetime.time(6, 30), tzinfo=VN),
    }
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap(monkeypatch, chuyen, trung=False):
    da_ghi = []
    monkeypatch.setattr(cs.repo, "tim_chuyen_theo_id_ql", lambda _id: chuyen)
    monkeypatch.setattr(cs.repo, "tim_trung_loai_xe_va_gio", lambda *a: trung)
    monkeypatch.setattr(cs.repo, "sua_gio_chuyen", lambda cid, gio: da_ghi.append(gio))
    monkeypatch.setattr(cs, "chi_tiet_chuyen", lambda cid: {"id": cid})  # sửa xong trả chi tiết đầy đủ (kiểm riêng ở test chi tiết)
    return da_ghi


def _ngay_tuong_lai():
    return datetime.datetime.now(VN).date() + datetime.timedelta(days=10)


def test_sua_gio_giu_nguyen_ngay(monkeypatch):
    ngay = _ngay_tuong_lai()
    da_ghi = _gia_lap(monkeypatch, _chuyen(ngay))
    cs.sua_gio_chuyen("c-1", datetime.time(7, 15))
    assert da_ghi == [datetime.datetime.combine(ngay, datetime.time(7, 15), tzinfo=VN)]


def test_sua_gio_ngay_lay_theo_gio_vn_khong_theo_utc(monkeypatch):
    # 00:30 giờ VN = 17:30 UTC hôm trước — ngày phải vẫn là ngày VN.
    ngay = _ngay_tuong_lai()
    chuyen = _chuyen(ngay, gio_khoi_hanh=datetime.datetime.combine(ngay, datetime.time(0, 30), tzinfo=VN).astimezone(datetime.timezone.utc))
    da_ghi = _gia_lap(monkeypatch, chuyen)
    cs.sua_gio_chuyen("c-1", datetime.time(1, 0))
    assert da_ghi[0].astimezone(VN).date() == ngay


def test_sua_gio_trong_qua_khu_bi_chan(monkeypatch):
    hom_nay = datetime.datetime.now(VN).date()
    da_ghi = _gia_lap(monkeypatch, _chuyen(hom_nay - datetime.timedelta(days=1)))
    with pytest.raises(GiaTriLoi, match="đã qua"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []


def test_sua_gio_chuyen_da_co_ve_bi_chan(monkeypatch):
    da_ghi = _gia_lap(monkeypatch, _chuyen(_ngay_tuong_lai(), so_ve_dang_hoat_dong=2))
    with pytest.raises(GiaTriLoi, match="vé"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []


def test_sua_gio_trung_loai_xe_va_gio_bi_chan(monkeypatch):
    da_ghi = _gia_lap(monkeypatch, _chuyen(_ngay_tuong_lai()), trung=True)
    with pytest.raises(GiaTriLoi, match="cùng loại xe"):
        cs.sua_gio_chuyen("c-1", datetime.time(8, 0))
    assert da_ghi == []


# ---------------------------------------------------------
# Chi tiết chuyến: sơ đồ ghế có hệ số + vé đang chiếm ghế + giá từng ghế theo chặng
# ---------------------------------------------------------
def test_chi_tiet_chuyen_co_so_do_ghe_he_so_ve_va_gia_tung_ghe(monkeypatch):
    chuyen = _chuyen(_ngay_tuong_lai(), loai_xe_id="lx1", tuyen_id="t1", chieu="xuoi", he_so_gia=1, he_so_ghe={"A1": 1.2})
    so_do = [{"ma_ghe": "A1", "tang": 1, "x": 0, "y": 0}, {"ma_ghe": "B1", "tang": 2, "x": 0, "y": 0}]
    ve = {"ma_ve": "VE1", "so_ghe": "A1", "trang_thai": "da_thanh_toan", "gia": __import__("decimal").Decimal("360000"),
          "ten_diem_don": "VP A", "ten_diem_tra": "VP B"}
    monkeypatch.setattr(cs.repo, "tim_chuyen_theo_id_ql", lambda _id: chuyen)
    monkeypatch.setattr(cs.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"so_do_ghe": so_do})
    monkeypatch.setattr(cs.repo, "danh_sach_ve_dang_chiem_ghe", lambda _id: [ve])
    da_goi = {}
    monkeypatch.setattr(cs.gia_ve_service, "bang_gia_cua_chuyen", lambda *a: da_goi.update(args=a) or {"cac_chang": []})
    kq = cs.chi_tiet_chuyen("c-1")
    assert kq["so_tang"] == 2
    assert [(g["ma_ghe"], g["he_so"]) for g in kq["so_do_ghe"]] == [("A1", 1.2), ("B1", 1)]
    assert kq["cac_ve_tren_ghe"][0]["gia"] == 360000 and isinstance(kq["cac_ve_tren_ghe"][0]["gia"], int)
    assert da_goi["args"][4] == ["A1", "B1"] and da_goi["args"][5] == {"A1": 1.2}  # đúng danh sách ghế + hệ số đã chốt vào chuyến
