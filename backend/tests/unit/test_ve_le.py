"""Unit test từng vé riêng lẻ (trang Booking): tiền đã trả/còn lại, hủy 1 vé, thanh toán riêng 1 vé tại quầy — Repository giả lập."""

import datetime
from urllib.parse import parse_qs, urlparse

import pytest

from app.services import dat_ve_service as svc
from app.services import thanh_toan_service as tt
from app.services import vnpay_service as vp
from app.utils.loi import GiaTriLoi
from tests.unit.test_dat_ve_service import BAY_GIO, _ve

SAU = BAY_GIO + datetime.timedelta(minutes=5)
KHOA = "khoa-bi-mat-thu-nghiem"


@pytest.fixture(autouse=True)
def cau_hinh(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_HASH_SECRET", KHOA)
    monkeypatch.setattr(vp, "CORS_ORIGINS", ["http://localhost:5500"])
    monkeypatch.setattr(svc, "_bay_gio", lambda: BAY_GIO)


# ---------------------------------------------------------
# Tiền đã trả / còn lại, hủy được / thanh toán được
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "ve, mong_doi",
    [
        (_ve("1", gia=300000, trang_thai="da_thanh_toan", han=None), (300000, 0)),
        (_ve("1", gia=300000, trang_thai="da_xuong_xe", han=None), (300000, 0)),
        (_ve("1", gia=300000, han=SAU), (0, 300000)),
        (_ve("1", gia=300000, loai="thanh_toan_tai_quay", han=None), (0, 300000)),
        (_ve("1", gia=300000, han=BAY_GIO - datetime.timedelta(minutes=1)), (0, 0)),  # hết hạn
        (_ve("1", gia=300000, trang_thai="da_huy", han=None), (0, 0)),
        (_ve("1", gia=300000, trang_thai="khong_den", han=None), (0, 0)),
    ],
)
def test_tien_da_tra_con_lai(ve, mong_doi):
    assert svc.tien_da_tra_con_lai(ve, BAY_GIO) == mong_doi


def test_ve_tai_quay_chua_tra_huy_duoc_va_thanh_toan_duoc():
    ve = _ve("1", loai="thanh_toan_tai_quay", han=None)
    assert svc.ve_huy_duoc(ve, "dat_thanh_cong_tai_quay", BAY_GIO)
    assert svc.ve_thanh_toan_duoc(ve, BAY_GIO)


def test_ve_da_tra_khong_huy_khong_thanh_toan_lai():
    ve = _ve("1", trang_thai="da_thanh_toan", han=None)
    assert not svc.ve_huy_duoc(ve, "da_thanh_toan", BAY_GIO)
    assert not svc.ve_thanh_toan_duoc(ve, BAY_GIO)


def test_ve_dang_giu_tam_huy_duoc_nhung_chua_thanh_toan_rieng_duoc():
    ve = _ve("1", han=SAU)
    assert svc.ve_huy_duoc(ve, "dang_giu", BAY_GIO)
    assert not svc.ve_thanh_toan_duoc(ve, BAY_GIO)


def test_ve_tra_vnpay_cua_luot_dang_cho_thanh_toan_khong_huy_le():
    ve = _ve("1", han=SAU, gio_bat_dau_dem_han=BAY_GIO)
    assert not svc.ve_huy_duoc(ve, "cho_thanh_toan", BAY_GIO)


def test_ve_tai_quay_trong_luot_cho_vnpay_van_huy_duoc():
    ve = _ve("2", loai="thanh_toan_tai_quay", han=SAU)
    assert svc.ve_huy_duoc(ve, "cho_thanh_toan", BAY_GIO)


def test_qua_moc_chot_khong_huy_khong_thanh_toan():
    gan = BAY_GIO + datetime.timedelta(minutes=svc.X_PHUT_CHOT_LEN_XE - 1)
    ve = _ve("1", loai="thanh_toan_tai_quay", han=None, gio_don=gan)
    assert not svc.ve_huy_duoc(ve, "dat_thanh_cong_tai_quay", BAY_GIO)
    assert not svc.ve_thanh_toan_duoc(ve, BAY_GIO)


def test_chuyen_da_chay_khong_huy_khong_thanh_toan():
    ve = _ve("1", loai="thanh_toan_tai_quay", han=None, trang_thai_chuyen="dang_chay")
    assert not svc.ve_huy_duoc(ve, "dat_thanh_cong_tai_quay", BAY_GIO)
    assert not svc.ve_thanh_toan_duoc(ve, BAY_GIO)


def test_lich_su_tinh_da_tra_con_lai_cua_luot(monkeypatch):
    hang = [
        {**_ve("1", trang_thai="da_thanh_toan", han=None, gia=300000), "ma_dat_cho": "DC0001", "ngay_tao": BAY_GIO},
        {**_ve("2", loai="thanh_toan_tai_quay", han=None, gia=200000), "ma_dat_cho": "DC0001", "ngay_tao": BAY_GIO},
    ]
    monkeypatch.setattr(svc.lich_su_repo, "lay_ve_cua_khach", lambda kh: hang)
    (luot,) = svc.lich_su("kh1")
    assert (luot["tong_tien"], luot["da_thanh_toan"], luot["con_lai"], luot["so_ve"]) == (500000, 300000, 200000, 2)
    ve1, ve2 = luot["ve"]
    assert (ve1["ma_ve"], ve1["da_thanh_toan"], ve1["con_lai"], ve1["co_the_huy"], ve1["co_the_thanh_toan"]) == ("VE00001", 300000, 0, False, False)
    assert (ve2["con_lai"], ve2["co_the_huy"], ve2["co_the_thanh_toan"]) == (200000, True, True)
    assert luot["chuyen"]["ten_tuyen"] == "Hà Nội - Vinh" and luot["chuyen"]["bien_so"] == "29B-123.45"


# ---------------------------------------------------------
# Hủy 1 vé
# ---------------------------------------------------------
@pytest.fixture
def kho(monkeypatch):
    ghi = {"huy": [], "luu_ma": [], "ve": None, "dat_cho": []}
    monkeypatch.setattr(svc.lich_su_repo, "lay_ve_theo_id", lambda ve_id, kh: ghi["ve"])
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, kh: ghi["dat_cho"])
    monkeypatch.setattr(svc.thanh_toan_repo, "huy_ve_dang_giu", lambda ve_id, kh: ghi["huy"].append(ve_id) or True)
    monkeypatch.setattr(svc.thanh_toan_repo, "luu_ma_tham_chieu_vnpay_ve", lambda ve_id, gd: ghi["luu_ma"].append((ve_id, gd)))
    return ghi


def test_huy_ve_tai_quay_thanh_cong(kho):
    kho["ve"] = _ve("1", loai="thanh_toan_tai_quay", han=None)
    assert svc.huy_ve("kh1", "ve-1") == {"ma_ve": "VE00001", "trang_thai": "da_huy"}
    assert kho["huy"] == ["ve-1"]


def test_huy_ve_khong_thay(kho):
    kho["ve"] = None
    with pytest.raises(GiaTriLoi, match="Không tìm thấy vé"):
        svc.huy_ve("kh1", "ve-x")


def test_huy_ve_da_thanh_toan_bi_chan(kho):
    kho["ve"] = _ve("1", trang_thai="da_thanh_toan", han=None)
    with pytest.raises(GiaTriLoi, match="không tự hủy được"):
        svc.huy_ve("kh1", "ve-1")
    assert not kho["huy"]


def test_huy_ve_qua_moc_chot_bi_chan(kho):
    kho["ve"] = _ve("1", loai="thanh_toan_tai_quay", han=None, gio_don=BAY_GIO + datetime.timedelta(minutes=2))
    with pytest.raises(GiaTriLoi, match="mốc chốt"):
        svc.huy_ve("kh1", "ve-1")


def test_huy_ve_het_han_bi_chan(kho):
    kho["ve"] = _ve("1", han=BAY_GIO - datetime.timedelta(minutes=1))
    with pytest.raises(GiaTriLoi, match="không còn ở trạng thái giữ chỗ"):
        svc.huy_ve("kh1", "ve-1")


def test_huy_ve_tra_vnpay_cua_luot_cho_thanh_toan_bi_chan(kho):
    ve = _ve("1", han=SAU, gio_bat_dau_dem_han=BAY_GIO)
    kho["ve"] = ve
    kho["dat_cho"] = [ve]
    with pytest.raises(GiaTriLoi, match="chờ thanh toán VNPay"):
        svc.huy_ve("kh1", "ve-1")


# ---------------------------------------------------------
# Thanh toán riêng 1 vé tại quầy
# ---------------------------------------------------------
def test_duong_dan_thanh_toan_ve(kho):
    kho["ve"] = _ve("1", gia=300000, loai="thanh_toan_tai_quay", han=None)
    url = svc.tao_duong_dan_thanh_toan_ve("kh1", "ve-1", "http://localhost:5500", "1.2.3.4")
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["vnp_Amount"] == "30000000"
    assert q["vnp_TxnRef"] == "VE00001-20261010150000"  # tiền tố là mã vé
    assert q["vnp_ExpireDate"] == "20261010150500"  # 5 phút
    assert "VE00001" in q["vnp_OrderInfo"]
    assert vp.chu_ky_hop_le(q)
    assert kho["luu_ma"] == [("ve-1", "VE00001-20261010150000")]


def test_duong_dan_thanh_toan_ve_da_tra_bi_chan(kho):
    kho["ve"] = _ve("1", trang_thai="da_thanh_toan", han=None)
    with pytest.raises(GiaTriLoi, match="đã được thanh toán"):
        svc.tao_duong_dan_thanh_toan_ve("kh1", "ve-1", "http://localhost:5500")


def test_duong_dan_thanh_toan_ve_khong_phai_tai_quay_bi_chan(kho):
    kho["ve"] = _ve("1", han=SAU)
    with pytest.raises(GiaTriLoi, match="không thanh toán online được"):
        svc.tao_duong_dan_thanh_toan_ve("kh1", "ve-1", "http://localhost:5500")


# ---------------------------------------------------------
# IPN / querydr cho giao dịch của 1 vé
# ---------------------------------------------------------
MA_GD = "VE00001-20261010150000"


def _ipn(so_tien=300000, ma_phan_hoi="00", trang_thai="00", ma_gd=MA_GD):
    p = {
        "vnp_TmnCode": "DEMO", "vnp_Amount": str(so_tien * 100), "vnp_ResponseCode": ma_phan_hoi,
        "vnp_TransactionStatus": trang_thai, "vnp_TxnRef": ma_gd, "vnp_TransactionNo": "555",
    }
    p["vnp_SecureHash"] = vp.ky(p)
    return p


@pytest.fixture
def ipn_kho(monkeypatch):
    ghi = {"ghi": [], "ve": {"id": "ve-1", "ma_ve": "VE00001", "ma_dat_cho": "DC0001", "gia": 300000,
                              "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_tai_quay", "han_giu_cho_den": None},
           "ghi_ket_qua": 1}
    monkeypatch.setattr(tt.repo, "lay_ve_theo_ma_ve", lambda ma: ghi["ve"])
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ve_le", lambda ma, gd: ghi["ghi"].append((ma, gd)) or ghi["ghi_ket_qua"])
    monkeypatch.setattr(tt.repo, "lay_ve_cua_dat_cho", lambda ma: pytest.fail("không được xử lý như giao dịch của cả lượt"))
    return ghi


def test_ipn_ve_thanh_cong(ipn_kho):
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "00"
    assert ipn_kho["ghi"] == [("VE00001", "555")]


def test_ipn_ve_that_bai_khong_doi_gi(ipn_kho):
    assert tt.xu_ly_ipn(_ipn(ma_phan_hoi="24", trang_thai="02"))["RspCode"] == "00"
    assert not ipn_kho["ghi"]


def test_ipn_ve_sai_so_tien(ipn_kho):
    assert tt.xu_ly_ipn(_ipn(so_tien=100000))["RspCode"] == "04"
    assert not ipn_kho["ghi"]


def test_ipn_ve_da_thanh_toan_roi(ipn_kho):
    ipn_kho["ve"]["trang_thai"] = "da_thanh_toan"
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "02"
    assert not ipn_kho["ghi"]


def test_ipn_ve_khong_thay_ve(ipn_kho):
    ipn_kho["ve"] = None
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "01"


def test_ipn_ve_da_bi_huy_trong_luc_thanh_toan_can_hoan_tien_tay(ipn_kho):
    ipn_kho["ghi_ket_qua"] = 0
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "02"


def test_trang_ket_qua_cua_ve_tra_ve_ma_dat_cho_cua_luot(ipn_kho):
    kq = tt.doc_ket_qua_tra_ve(_ipn())
    assert kq["hop_le"] and kq["thanh_cong"] and kq["ma_dat_cho"] == "DC0001"


def test_truy_van_ve_thanh_cong(ipn_kho, monkeypatch):
    monkeypatch.setattr(tt, "VNPAY_CHE_DO", "sandbox")
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: {
        "vnp_ResponseCode": "00", "vnp_TxnRef": MA_GD, "vnp_TransactionStatus": "00", "vnp_Amount": "30000000", "vnp_TransactionNo": "777"})
    assert tt.xac_nhan_qua_truy_van(MA_GD) == {"trang_thai": "thanh_cong"}
    assert ipn_kho["ghi"] == [("VE00001", "777")]


def test_truy_van_ve_that_bai_khong_doi_trang_thai_ve(ipn_kho, monkeypatch):
    monkeypatch.setattr(tt, "VNPAY_CHE_DO", "sandbox")
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: {
        "vnp_ResponseCode": "00", "vnp_TxnRef": MA_GD, "vnp_TransactionStatus": "02", "vnp_Amount": "30000000", "vnp_TransactionNo": "777"})
    assert tt.xac_nhan_qua_truy_van(MA_GD) == {"trang_thai": "that_bai"}
    assert not ipn_kho["ghi"]


def test_truy_van_ve_da_tra_roi_khong_hoi_lai(ipn_kho, monkeypatch):
    monkeypatch.setattr(tt, "VNPAY_CHE_DO", "sandbox")
    ipn_kho["ve"]["trang_thai"] = "da_thanh_toan"
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: pytest.fail("không được gọi VNPay"))
    assert tt.xac_nhan_qua_truy_van(MA_GD) == {"trang_thai": "da_xac_nhan"}
