"""Unit test thanh toán VNPay: chữ ký, đường dẫn, IPN, cổng giả lập — Repository giả lập, không cần DB."""

import datetime
import hashlib
import hmac
from urllib.parse import parse_qsl, quote_plus, urlparse

import pytest

from app.services import cong_thanh_toan_gia_service as gia_lap
from app.services import thanh_toan_service as tt
from app.services import vnpay_service as vp
from app.utils.loi import GiaTriLoi

KHOA = "khoa-bi-mat-thu-nghiem"
BAY_GIO = datetime.datetime(2026, 10, 10, 8, 0, tzinfo=datetime.timezone.utc)  # 15:00 giờ Việt Nam


@pytest.fixture(autouse=True)
def khoa_va_origin(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_HASH_SECRET", KHOA)
    monkeypatch.setattr(vp, "CORS_ORIGINS", ["http://localhost:5500"])


def _ky_doc_lap(chuoi: str) -> str:
    return hmac.new(KHOA.encode(), chuoi.encode(), hashlib.sha512).hexdigest()


# ---------------------------------------------------------
# Chữ ký
# ---------------------------------------------------------
def test_chuoi_can_ky_sap_a_z_bo_hash_bo_rong_bo_tham_so_la():
    p = {"vnp_B": "2", "vnp_A": "x y&z", "vnp_SecureHash": "bo", "vnp_SecureHashType": "bo", "khac": "bo", "vnp_Rong": ""}
    assert vp.chuoi_can_ky(p) == "vnp_A=x+y%26z&vnp_B=2"


def test_chu_ky_khop_cach_tinh_doc_lap_hmac_sha512():
    p = {"vnp_Amount": "10000000", "vnp_TxnRef": "DCAB12", "vnp_OrderInfo": "Thanh toan ve"}
    mong_doi = _ky_doc_lap(f"vnp_Amount=10000000&vnp_OrderInfo={quote_plus('Thanh toan ve')}&vnp_TxnRef=DCAB12")
    assert vp.ky(p) == mong_doi
    assert len(mong_doi) == 128  # SHA-512 dạng hex


def test_chu_ky_hop_le_va_bi_phat_hien_khi_sua_du_lieu():
    p = {"vnp_Amount": "10000000", "vnp_TxnRef": "DCAB12"}
    p["vnp_SecureHash"] = vp.ky(p)
    assert vp.chu_ky_hop_le(p) is True
    assert vp.chu_ky_hop_le({**p, "vnp_Amount": "100"}) is False  # sửa số tiền
    assert vp.chu_ky_hop_le({k: v for k, v in p.items() if k != "vnp_SecureHash"}) is False  # thiếu chữ ký
    assert vp.chu_ky_hop_le({**p, "vnp_SecureHash": "abc"}) is False


# ---------------------------------------------------------
# Đường dẫn thanh toán
# ---------------------------------------------------------
def _tham_so_tu_url(url: str) -> dict:
    return dict(parse_qsl(urlparse(url).query))


def test_tao_url_thanh_toan_dung_tham_so_va_chu_ky(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_CHE_DO", "gia_lap")
    url = vp.tao_url_thanh_toan("DCAB12", 400000, BAY_GIO + datetime.timedelta(minutes=5), "http://localhost:5500", "1.2.3.4", BAY_GIO)
    assert url.startswith("http://localhost:5500/khach-hang/cong-thanh-toan-gia.html?")
    p = _tham_so_tu_url(url)
    assert p["vnp_Amount"] == "40000000" and p["vnp_Command"] == "pay" and p["vnp_Version"] == "2.1.0"
    assert p["vnp_CreateDate"] == "20261010150000" and p["vnp_ExpireDate"] == "20261010150500"  # giờ VN, +5 phút
    assert p["vnp_TxnRef"] == "DCAB12-20261010150000" and p["vnp_IpAddr"] == "1.2.3.4"
    assert p["vnp_ReturnUrl"] == "http://localhost:5500/khach-hang/ket-qua-thanh-toan.html"
    assert vp.chu_ky_hop_le(p)


def test_tao_url_thanh_toan_che_do_that_tro_ve_cong_vnpay(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_CHE_DO", "sandbox")
    url = vp.tao_url_thanh_toan("DCAB12", 1000, BAY_GIO + datetime.timedelta(minutes=5), "http://localhost:5500", "1.2.3.4", BAY_GIO)
    assert url.startswith("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?")


@pytest.mark.parametrize("origin", [None, "", "https://trang-la.example", "http://localhost:9999"])
def test_origin_ngoai_cors_bi_chan(origin):
    with pytest.raises(GiaTriLoi):
        vp.kiem_tra_origin_frontend(origin)


def test_ma_giao_dich_tach_dung_ma_dat_cho():
    ma_gd = vp.tao_ma_giao_dich("DCAB12CD34", BAY_GIO)
    assert vp.ma_dat_cho_tu_ma_giao_dich(ma_gd) == "DCAB12CD34"


def test_moi_lan_thanh_toan_co_ma_giao_dich_khac_nhau():
    sau = BAY_GIO + datetime.timedelta(seconds=1)
    assert vp.tao_ma_giao_dich("DCAB12", BAY_GIO) != vp.tao_ma_giao_dich("DCAB12", sau)


# ---------------------------------------------------------
# IPN
# ---------------------------------------------------------
def _ve(so_ghe, gia, trang_thai="giu_cho", loai="thanh_toan_ngay"):
    return {"id": f"v{so_ghe}", "so_ghe": so_ghe, "gia": gia, "trang_thai": trang_thai, "loai_hinh_thanh_toan": loai, "han_giu_cho_den": None}


def _ipn(so_tien=400000, ma_phan_hoi="00", trang_thai="00", ma_gd="DCAB12-20261010150000", **them):
    p = {
        "vnp_TmnCode": "DEMO", "vnp_Amount": str(so_tien * 100), "vnp_ResponseCode": ma_phan_hoi,
        "vnp_TransactionStatus": trang_thai, "vnp_TxnRef": ma_gd, "vnp_TransactionNo": "12345678", **them,
    }
    p["vnp_SecureHash"] = vp.ky(p)
    return p


@pytest.fixture
def kho(monkeypatch):
    ghi = {"da_tra": [], "huy": []}
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ngay", lambda ma, gd: ghi["da_tra"].append((ma, gd)) or 2)
    monkeypatch.setattr(tt.repo, "huy_thanh_toan_ngay", lambda ma: ghi["huy"].append(ma) or 2)
    monkeypatch.setattr(tt.repo, "lay_ve_cua_dat_cho", lambda ma: ghi.get("ve", []))
    return ghi


def test_ipn_sai_chu_ky(kho):
    p = _ipn()
    p["vnp_Amount"] = "1"
    assert tt.xu_ly_ipn(p)["RspCode"] == "97"
    assert not kho["da_tra"] and not kho["huy"]


def test_ipn_khong_thay_don(kho):
    kho["ve"] = []
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "01"


def test_ipn_don_chi_co_ve_tai_quay_thi_khong_thay_don_online(kho):
    kho["ve"] = [_ve("1", 400000, loai="thanh_toan_tai_quay")]
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "01"


def test_ipn_sai_so_tien(kho):
    kho["ve"] = [_ve("1", 200000), _ve("2", 200000)]
    assert tt.xu_ly_ipn(_ipn(so_tien=399999))["RspCode"] == "04"
    assert not kho["da_tra"]


def test_ipn_chi_tinh_tien_cac_ve_tra_online_khong_tinh_phan_tra_tai_quay(kho):
    kho["ve"] = [_ve("1", 200000), _ve("2", 200000), _ve("3", 200000, loai="thanh_toan_tai_quay"), _ve("4", 200000, loai="thanh_toan_tai_quay")]
    assert tt.xu_ly_ipn(_ipn(so_tien=400000))["RspCode"] == "00"
    assert kho["da_tra"] == [("DCAB12", "12345678")]


def test_ipn_thanh_cong_ghi_nhan_ma_giao_dich_cua_cong(kho):
    kho["ve"] = [_ve("1", 200000), _ve("2", 200000)]
    kq = tt.xu_ly_ipn(_ipn())
    assert kq == {"RspCode": "00", "Message": "Confirm Success"}
    assert kho["da_tra"] == [("DCAB12", "12345678")] and not kho["huy"]


def test_ipn_thanh_cong_nhung_ve_da_qua_han_khong_ghi_nhan(kho, monkeypatch):
    kho["ve"] = [_ve("1", 200000), _ve("2", 200000)]
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ngay", lambda ma, gd: 0)
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "02"  # dừng cổng gọi lại; cần hoàn tiền thủ công


def test_ipn_goi_lai_khong_xu_ly_lan_hai(kho):
    kho["ve"] = [_ve("1", 200000, trang_thai="da_thanh_toan"), _ve("2", 200000, trang_thai="da_thanh_toan")]
    assert tt.xu_ly_ipn(_ipn())["RspCode"] == "02"
    assert not kho["da_tra"] and not kho["huy"]


@pytest.mark.parametrize("ma,trang_thai", [("24", "02"), ("11", "02"), ("51", "02"), ("00", "02")])
def test_ipn_that_bai_huy_ca_lo(kho, ma, trang_thai):
    kho["ve"] = [_ve("1", 400000)]
    assert tt.xu_ly_ipn(_ipn(ma_phan_hoi=ma, trang_thai=trang_thai))["RspCode"] == "00"
    assert kho["huy"] == ["DCAB12"] and not kho["da_tra"]


def test_ket_qua_tra_ve_hop_le_va_khong_doi_trang_thai(kho):
    ok = tt.doc_ket_qua_tra_ve(_ipn())
    assert ok == {"hop_le": True, "thanh_cong": True, "ma_dat_cho": "DCAB12", "ma_phan_hoi": "00"}
    huy = tt.doc_ket_qua_tra_ve(_ipn(ma_phan_hoi="24", trang_thai="02"))
    assert huy["hop_le"] and not huy["thanh_cong"]
    gia = _ipn()
    gia["vnp_ResponseCode"] = "00"
    gia["vnp_Amount"] = "1"
    assert tt.doc_ket_qua_tra_ve(gia)["hop_le"] is False
    assert not kho["da_tra"] and not kho["huy"]


# ---------------------------------------------------------
# Cổng giả lập
# ---------------------------------------------------------
@pytest.fixture
def cong(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_CHE_DO", "gia_lap")
    monkeypatch.setattr(gia_lap, "VNPAY_CHE_DO", "gia_lap")
    url = vp.tao_url_thanh_toan("DCAB12", 400000, BAY_GIO + datetime.timedelta(minutes=5), "http://localhost:5500", "1.2.3.4", BAY_GIO)
    nhan = {}
    monkeypatch.setattr(gia_lap.thanh_toan_service, "xu_ly_ipn", lambda p: nhan.update(ipn=p) or {"RspCode": "00", "Message": "Confirm Success"})
    return _tham_so_tu_url(url), nhan


def test_cong_gia_thong_tin_giao_dich(cong):
    tham_so, _ = cong
    info = gia_lap.thong_tin_giao_dich(tham_so)
    assert info["so_tien"] == 400000 and info["ma_giao_dich"] == "DCAB12-20261010150000"
    assert info["han_thanh_toan"] == vp.doc_gio_vn("20261010150500")


def test_cong_gia_thanh_cong_goi_ipn_co_chu_ky_va_tra_url_ve(cong):
    tham_so, nhan = cong
    kq = gia_lap.xu_ly(tham_so, "thanh_cong", BAY_GIO + datetime.timedelta(minutes=2))
    ipn = nhan["ipn"]
    assert vp.chu_ky_hop_le(ipn) and ipn["vnp_ResponseCode"] == "00" and ipn["vnp_TransactionStatus"] == "00"
    assert ipn["vnp_Amount"] == "40000000" and ipn["vnp_TxnRef"] == tham_so["vnp_TxnRef"]
    assert kq["ipn"]["RspCode"] == "00"
    base, query = kq["return_url"].split("?", 1)
    assert base == "http://localhost:5500/khach-hang/ket-qua-thanh-toan.html"
    assert vp.chu_ky_hop_le(dict(parse_qsl(query)))


def test_cong_gia_khach_huy(cong):
    tham_so, nhan = cong
    gia_lap.xu_ly(tham_so, "huy", BAY_GIO + datetime.timedelta(minutes=1))
    assert nhan["ipn"]["vnp_ResponseCode"] == "24" and nhan["ipn"]["vnp_TransactionStatus"] == "02"


def test_cong_gia_qua_han_thanh_toan_luon_that_bai_du_bam_thanh_cong(cong):
    tham_so, nhan = cong
    gia_lap.xu_ly(tham_so, "thanh_cong", BAY_GIO + datetime.timedelta(minutes=5, seconds=1))
    assert nhan["ipn"]["vnp_ResponseCode"] == "11"


def test_cong_gia_tu_choi_duong_dan_bi_sua(cong):
    tham_so, nhan = cong
    tham_so["vnp_Amount"] = "100"
    with pytest.raises(GiaTriLoi, match="sai chữ ký"):
        gia_lap.xu_ly(tham_so, "thanh_cong", BAY_GIO)
    with pytest.raises(GiaTriLoi, match="sai chữ ký"):
        gia_lap.thong_tin_giao_dich(tham_so)
    assert "ipn" not in nhan


def test_cong_gia_khong_chay_khi_dung_vnpay_that(cong, monkeypatch):
    tham_so, _ = cong
    monkeypatch.setattr(gia_lap, "VNPAY_CHE_DO", "sandbox")
    with pytest.raises(GiaTriLoi, match="gia_lap"):
        gia_lap.xu_ly(tham_so, "thanh_cong", BAY_GIO)
