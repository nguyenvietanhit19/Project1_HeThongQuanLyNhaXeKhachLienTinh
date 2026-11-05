"""Unit test cho phân công điều độ viên phụ trách tuyến — giả lập Repository bằng monkeypatch, không cần DB thật."""

import pytest

from app.services import phan_cong_dieu_do_service as svc
from app.utils.loi import GiaTriLoi, KhongTimThay

TUYEN_1, TUYEN_2 = "tuyen-1", "tuyen-2"


def dd(id_, ho_ten="Điều độ viên"):
    return {"id": id_, "ho_ten": ho_ten, "email": f"{id_}@x.vn"}


def dong(tuyen_id, id_, ho_ten="Điều độ viên"):
    return {"tuyen_id": tuyen_id, "nguoi_dung_id": id_, "ho_ten": ho_ten, "email": f"{id_}@x.vn"}


@pytest.fixture
def csdl(monkeypatch):
    """Giả lập: tuyến 'tuyen-1' tồn tại, id hợp lệ do test đặt, ghi lại lần ghi phân công."""
    trang_thai = {"tuyen_ton_tai": {TUYEN_1, TUYEN_2}, "hop_le": {"dd-1", "dd-2", "dd-3"}, "da_ghi": [], "cac_dong": []}
    monkeypatch.setattr(svc.dia_diem_repo, "tim_tuyen_theo_id", lambda tid: {"id": tid} if tid in trang_thai["tuyen_ton_tai"] else None)
    monkeypatch.setattr(svc.repo, "dem_dieu_do_vien_hop_le", lambda ids: len([i for i in ids if i in trang_thai["hop_le"]]))
    monkeypatch.setattr(svc.repo, "dat_phan_cong_tuyen", lambda tid, ids: trang_thai["da_ghi"].append((tid, ids)))
    monkeypatch.setattr(svc.repo, "danh_sach_phan_cong", lambda: trang_thai["cac_dong"])
    return trang_thai


def test_danh_sach_phan_cong_gom_theo_tuyen_va_tuyen_chua_co_ai_thi_khong_xuat_hien(csdl):
    csdl["cac_dong"] = [dong(TUYEN_1, "dd-1", "An"), dong(TUYEN_1, "dd-2", "Bình"), dong(TUYEN_2, "dd-1", "An")]
    ket_qua = {p["tuyen_id"]: [x["id"] for x in p["dieu_do_vien"]] for p in svc.danh_sach_phan_cong()}
    assert ket_qua == {TUYEN_1: ["dd-1", "dd-2"], TUYEN_2: ["dd-1"]}  # 1 điều độ viên phụ trách nhiều tuyến, 1 tuyến nhiều điều độ viên


def test_danh_sach_phan_cong_rong_khi_chua_phan_cong_ai(csdl):
    assert svc.danh_sach_phan_cong() == []


def test_dat_phan_cong_thanh_cong_ghi_dung_danh_sach_va_tra_ve_phan_cong_cua_tuyen(csdl):
    csdl["cac_dong"] = [dong(TUYEN_1, "dd-1", "An"), dong(TUYEN_2, "dd-3", "Chi")]
    ket_qua = svc.dat_phan_cong(TUYEN_1, ["dd-1"])
    assert csdl["da_ghi"] == [(TUYEN_1, ["dd-1"])]
    assert ket_qua["tuyen_id"] == TUYEN_1 and [x["id"] for x in ket_qua["dieu_do_vien"]] == ["dd-1"]  # không lẫn phân công của tuyến khác


def test_dat_phan_cong_gop_id_trung_va_giu_thu_tu(csdl):
    svc.dat_phan_cong(TUYEN_1, ["dd-2", "dd-1", "dd-2"])
    assert csdl["da_ghi"] == [(TUYEN_1, ["dd-2", "dd-1"])]


def test_dat_phan_cong_danh_sach_rong_la_bo_het_phan_cong(csdl):
    ket_qua = svc.dat_phan_cong(TUYEN_1, [])
    assert csdl["da_ghi"] == [(TUYEN_1, [])] and ket_qua["dieu_do_vien"] == []


def test_dat_phan_cong_tuyen_khong_ton_tai_bi_chan(csdl):
    with pytest.raises(KhongTimThay, match="tuyến"):
        svc.dat_phan_cong("tuyen-la", ["dd-1"])
    assert csdl["da_ghi"] == []


def test_dat_phan_cong_id_khong_phai_dieu_do_vien_dang_hoat_dong_bi_chan_va_khong_ghi_gi(csdl):
    with pytest.raises(GiaTriLoi, match="điều độ viên đang hoạt động"):
        svc.dat_phan_cong(TUYEN_1, ["dd-1", "tai-khoan-la"])  # 1 id lạ làm hỏng cả lần lưu
    assert csdl["da_ghi"] == []


def test_danh_sach_dieu_do_vien_tra_ve_nguyen_du_lieu_tu_repo(monkeypatch):
    monkeypatch.setattr(svc.repo, "danh_sach_dieu_do_vien_dang_hoat_dong", lambda: [dd("dd-1")])
    assert svc.danh_sach_dieu_do_vien() == [dd("dd-1")]
