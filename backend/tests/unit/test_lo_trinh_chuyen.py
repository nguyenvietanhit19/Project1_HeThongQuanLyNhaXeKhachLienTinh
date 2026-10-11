"""Unit test lộ trình chuyến (tim_kiem_chuyen_service.lo_trinh_chuyen) — Repository giả lập."""

import datetime

import pytest

from app.services import tim_kiem_chuyen_service as svc
from app.utils.loi import KhongTimThay

GIO = datetime.datetime(2026, 10, 9, 1, 0, tzinfo=datetime.timezone.utc)  # 08:00 giờ Việt Nam


def _diem(ten, phut, loai="van_phong", khu_vuc="Hà Nội"):
    return {
        "diem_id": f"id-{ten}", "ten": ten, "loai": loai, "khu_vuc_id": f"kv-{khu_vuc}", "ten_khu_vuc": khu_vuc,
        "dia_chi": f"Địa chỉ {ten}", "hl": phut, "phut": phut, "gio_khoi_hanh": GIO, "ten_tuyen": "Hà Nội - Vinh",
    }


@pytest.fixture
def tuyen(monkeypatch):
    ds = [_diem("Mỹ Đình", 0), _diem("Buýt Bầu", 20, "diem_dung"), _diem("Nội Bài", 40), _diem("Km122", 340, "diem_dung", "Vinh"), _diem("VP Vinh", 370, khu_vuc="Vinh")]
    monkeypatch.setattr(svc.repo, "lo_trinh_cua_chuyen", lambda chuyen_id: ds)
    return ds


def test_lo_trinh_giu_thu_tu_chay_va_tinh_gio_tung_diem(tuyen):
    lt = svc.lo_trinh_chuyen("c1")
    assert [d["ten"] for d in lt["diem"]] == ["Mỹ Đình", "Buýt Bầu", "Nội Bài", "Km122", "VP Vinh"]
    assert [d["gio_du_kien"] for d in lt["diem"]] == [GIO + datetime.timedelta(minutes=m) for m in (0, 20, 40, 340, 370)]


def test_lo_trinh_tong_thoi_gian_va_thong_tin_chung(tuyen):
    lt = svc.lo_trinh_chuyen("c1")
    assert lt["tong_thoi_gian_phut"] == 370
    assert lt["ten_tuyen"] == "Hà Nội - Vinh" and lt["gio_khoi_hanh"] == GIO and lt["chuyen_id"] == "c1"


def test_lo_trinh_giu_loai_diem_va_khu_vuc(tuyen):
    lt = svc.lo_trinh_chuyen("c1")
    assert [d["loai"] for d in lt["diem"]] == ["van_phong", "diem_dung", "van_phong", "diem_dung", "van_phong"]
    assert lt["diem"][3]["ten_khu_vuc"] == "Vinh" and lt["diem"][0]["dia_chi"] == "Địa chỉ Mỹ Đình"


def test_chuyen_khong_ton_tai_bao_khong_tim_thay(monkeypatch):
    monkeypatch.setattr(svc.repo, "lo_trinh_cua_chuyen", lambda chuyen_id: [])
    with pytest.raises(KhongTimThay):
        svc.lo_trinh_chuyen("khong-co")


def test_chieu_nguoc_phut_tinh_theo_chieu_chay_thi_giu_nguyen_thu_tu_repo(monkeypatch):
    # repository đã đảo hl/phút theo chiều; service chỉ tin thứ tự và số phút nhận được
    ngược = [_diem("VP Vinh", 0, khu_vuc="Vinh"), _diem("Km122", 30, "diem_dung", "Vinh"), _diem("Nội Bài", 330), _diem("Mỹ Đình", 370)]
    monkeypatch.setattr(svc.repo, "lo_trinh_cua_chuyen", lambda chuyen_id: ngược)
    lt = svc.lo_trinh_chuyen("c2")
    assert lt["diem"][0]["ten"] == "VP Vinh" and lt["tong_thoi_gian_phut"] == 370
    assert lt["diem"][-1]["gio_du_kien"] == GIO + datetime.timedelta(minutes=370)
