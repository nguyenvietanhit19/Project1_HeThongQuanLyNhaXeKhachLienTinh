"""Xác nhận cọc từ Return URL đã ký trong môi trường VNPay sandbox tại quầy."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services import quay_ve_service as quay_ve
from app.utils.loi import GiaTriLoi


@pytest.fixture
def giao_dich_coc(monkeypatch):
    ma_dat_cho = "DC12345678"
    ma_giao_dich = f"{ma_dat_cho}-20261105173500"
    monkeypatch.setattr(quay_ve, "VNPAY_CHE_DO", "sandbox")
    monkeypatch.setattr(quay_ve, "VNPAY_TMN_CODE", "TESTTMN")
    monkeypatch.setattr(quay_ve.vnpay_service, "VNPAY_HASH_SECRET", "test-secret")
    monkeypatch.setattr(quay_ve, "lay_van_phong", lambda _: {"id": "office-1"})

    ve = [
        {"ma_dat_cho": ma_dat_cho, "id": "deposit-1", "so_ghe": "A1", "gia": 500000,
         "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_ngay",
         "la_ve_dat_coc": True, "kenh_ban": "hotline", "ma_tham_chieu_vnpay": ma_giao_dich},
        {"ma_dat_cho": ma_dat_cho, "id": "cash-1", "so_ghe": "A2", "gia": 500000,
         "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_tai_quay",
         "la_ve_dat_coc": False, "kenh_ban": "hotline", "ma_tham_chieu_vnpay": None},
    ]
    monkeypatch.setattr(quay_ve.repo, "tra_cuu", lambda office_id, ma_dat_cho=None: ve if office_id == "office-1" else [])
    monkeypatch.setattr(quay_ve.thanh_toan_service.repo, "lay_ve_cua_dat_cho", lambda _: ve)
    monkeypatch.setattr(quay_ve.thanh_toan_service.thong_bao, "don_nhac_quay_ve", lambda _: None)
    monkeypatch.setattr(quay_ve.thanh_toan_service.thong_bao, "gui", lambda *args, **kwargs: None)

    def ghi_nhan(ma, giao_dich, tham_chieu, so_ve):
        assert (ma, tham_chieu, so_ve) == (ma_dat_cho, ma_giao_dich, 1)
        ve[0]["trang_thai"] = "da_thanh_toan"
        return 1

    monkeypatch.setattr(quay_ve.thanh_toan_service.repo, "ghi_nhan_thanh_toan_ngay", ghi_nhan)
    tham_so = {"vnp_TmnCode": "TESTTMN", "vnp_TxnRef": ma_giao_dich,
               "vnp_Amount": "50000000", "vnp_ResponseCode": "00",
               "vnp_TransactionStatus": "00", "vnp_TransactionNo": "123456"}
    tham_so["vnp_SecureHash"] = quay_ve.vnpay_service.ky(tham_so)
    return SimpleNamespace(user=SimpleNamespace(id="staff-1", van_phong_id="office-1"), ve=ve, tham_so=tham_so)


def test_return_url_co_chu_ky_chi_ghi_nhan_ve_coc(giao_dich_coc):
    result = quay_ve.xac_nhan_vnpay_sandbox(giao_dich_coc.user, giao_dich_coc.tham_so)
    assert result["la_dat_coc"] is True
    assert result["so_ve_da_thanh_toan"] == 1
    assert [v["trang_thai"] for v in giao_dich_coc.ve] == ["da_thanh_toan", "giu_cho"]


def test_return_url_bi_sua_so_tien_bi_tu_choi(giao_dich_coc):
    giao_dich_coc.tham_so["vnp_Amount"] = "100000000"
    with pytest.raises(GiaTriLoi, match="chữ ký"):
        quay_ve.xac_nhan_vnpay_sandbox(giao_dich_coc.user, giao_dich_coc.tham_so)
    assert giao_dich_coc.ve[0]["trang_thai"] == "giu_cho"


def test_ve_da_het_han_khong_duoc_danh_dau_da_coc(giao_dich_coc, monkeypatch):
    # Repository trả 0 khi hạn giữ chỗ đã qua, dù job chưa kịp đổi trạng thái vé.
    monkeypatch.setattr(quay_ve.thanh_toan_service.repo, "ghi_nhan_thanh_toan_ngay", lambda *args: 0)
    with pytest.raises(GiaTriLoi, match="cần đối soát"):
        quay_ve.xac_nhan_vnpay_sandbox(giao_dich_coc.user, giao_dich_coc.tham_so)
    assert giao_dich_coc.ve[0]["trang_thai"] == "giu_cho"


def test_chi_thu_phan_tien_mat_sau_khi_coc_da_duoc_xac_nhan(giao_dich_coc, monkeypatch):
    ve_coc, ve_con_lai = giao_dich_coc.ve
    with pytest.raises(GiaTriLoi, match="đặt cọc"):
        quay_ve.thu_tien(giao_dich_coc.user, ve_coc["ma_dat_cho"], "tien_mat")
    ve_coc["trang_thai"] = "het_han"
    with pytest.raises(GiaTriLoi, match="đặt cọc"):
        quay_ve.thu_tien(giao_dich_coc.user, ve_coc["ma_dat_cho"], "tien_mat")

    ve_coc["trang_thai"] = "da_thanh_toan"
    ve_con_lai["gio_khoi_hanh"] = datetime(2099, 1, 1, tzinfo=timezone.utc)
    ve_con_lai["gio_don_du_kien"] = datetime(2099, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(quay_ve.dat_ve_service, "con_truoc_moc_chot", lambda *args: True)
    monkeypatch.setattr(quay_ve.lock_repo, "thanh_toan_ve_quay", lambda *args: 1)
    monkeypatch.setattr(quay_ve.thong_bao, "don_nhac_quay_ve", lambda *args: None)
    assert quay_ve.thu_tien(giao_dich_coc.user, ve_coc["ma_dat_cho"], "tien_mat")["so_ve_da_thanh_toan"] == 1
