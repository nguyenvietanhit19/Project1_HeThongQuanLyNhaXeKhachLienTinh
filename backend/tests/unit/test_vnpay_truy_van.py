"""Unit test truy vấn giao dịch VNPay (querydr) — chữ ký yêu cầu/phản hồi và xác nhận vé; Repository + HTTP giả lập."""

import hashlib
import hmac

import pytest

from app.services import thanh_toan_service as tt
from app.services import vnpay_service as vp

KHOA = "khoa-bi-mat-thu-nghiem"
MA_GD = "DCAB12-20261010150000"


@pytest.fixture(autouse=True)
def cau_hinh(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_HASH_SECRET", KHOA)
    monkeypatch.setattr(vp, "VNPAY_TMN_CODE", "TMN12345")
    monkeypatch.setattr(tt, "VNPAY_CHE_DO", "sandbox")


def _ky(chuoi):
    return hmac.new(KHOA.encode(), chuoi.encode(), hashlib.sha512).hexdigest()


def _phan_hoi(ma="00", tinh_trang="00", so_tien=40000000, ma_gd=MA_GD):
    p = {
        "vnp_ResponseId": "r1", "vnp_Command": "querydr", "vnp_ResponseCode": ma, "vnp_Message": "OK", "vnp_TmnCode": "TMN12345",
        "vnp_TxnRef": ma_gd, "vnp_Amount": str(so_tien), "vnp_BankCode": "NCB", "vnp_PayDate": "20261010150500",
        "vnp_TransactionNo": "999", "vnp_TransactionType": "01", "vnp_TransactionStatus": tinh_trang,
        "vnp_OrderInfo": "x", "vnp_PromotionCode": "", "vnp_PromotionAmount": "",
    }
    p["vnp_SecureHash"] = _ky(
        "|".join(str(p.get(f"vnp_{t}", "")) for t in vp._TRUONG_PHAN_HOI_TRUY_VAN)
    )
    return p


def test_yeu_cau_truy_van_ky_dung_thu_tu_truong():
    y = vp.tao_yeu_cau_truy_van(MA_GD)
    chuoi = "|".join(y[f"vnp_{t}"] for t in ("RequestId", "Version", "Command", "TmnCode", "TxnRef", "TransactionDate", "CreateDate", "IpAddr", "OrderInfo"))
    assert y["vnp_SecureHash"] == _ky(chuoi)
    assert y["vnp_Command"] == "querydr" and y["vnp_TransactionDate"] == "20261010150000"


def test_phan_hoi_dung_chu_ky_thi_hop_le_sua_so_tien_thi_khong():
    p = _phan_hoi()
    assert vp.phan_hoi_truy_van_hop_le(p)
    p["vnp_Amount"] = "1"
    assert not vp.phan_hoi_truy_van_hop_le(p)


@pytest.fixture
def kho(monkeypatch):
    ghi = {"da_tra": [], "huy": [], "ve": [{"so_ghe": "1", "gia": 400000, "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_ngay"}]}
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ngay", lambda ma, gd: ghi["da_tra"].append((ma, gd)) or 1)
    monkeypatch.setattr(tt.repo, "huy_thanh_toan_ngay", lambda ma: ghi["huy"].append(ma) or 1)
    monkeypatch.setattr(tt.repo, "lay_ve_cua_dat_cho", lambda ma: ghi["ve"])
    return ghi


def test_khong_o_che_do_sandbox_thi_bo_qua(kho, monkeypatch):
    monkeypatch.setattr(tt, "VNPAY_CHE_DO", "gia_lap")
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: pytest.fail("không được gọi VNPay"))
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "bo_qua"


def test_thanh_cong_ghi_nhan_ma_giao_dich(kho, monkeypatch):
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: _phan_hoi())
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "thanh_cong"
    assert kho["da_tra"] == [("DCAB12", "999")]


def test_that_bai_huy_ca_lo(kho, monkeypatch):
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: _phan_hoi(tinh_trang="02"))
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "that_bai"
    assert kho["huy"] == ["DCAB12"] and not kho["da_tra"]


def test_vnpay_chua_co_giao_dich_hoac_dang_xu_ly_thi_khong_doi_gi(kho, monkeypatch):
    for kq in (_phan_hoi(ma="91"), _phan_hoi(tinh_trang="01")):
        monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m, kq=kq: kq)
        assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "chua_thanh_toan"
    assert not kho["da_tra"] and not kho["huy"]


def test_khong_hoi_duoc_vnpay_thi_chua_ro(kho, monkeypatch):
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: None)
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "chua_ro"


def test_phan_hoi_cua_giao_dich_khac_bi_bo_qua(kho, monkeypatch):
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: _phan_hoi(ma_gd="KHAC-20261010150000"))
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "chua_thanh_toan"
    assert not kho["da_tra"]


def test_sai_so_tien_khong_ghi_nhan(kho, monkeypatch):
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: _phan_hoi(so_tien=100))
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "khong_hop_le"
    assert not kho["da_tra"]


def test_ve_da_thanh_toan_roi_thi_khong_hoi_lai(kho, monkeypatch):
    kho["ve"][0]["trang_thai"] = "da_thanh_toan"
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: pytest.fail("không được gọi VNPay"))
    assert tt.xac_nhan_qua_truy_van(MA_GD)["trang_thai"] == "da_xac_nhan"


def test_quet_chi_hoi_cac_luot_dang_cho(kho, monkeypatch):
    import datetime
    cu = "DCAB12-" + vp.dinh_dang_gio_vn(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5))
    monkeypatch.setattr(tt.repo, "lay_ma_giao_dich_dang_cho", lambda: [cu])
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: _phan_hoi(ma_gd=cu))
    assert tt.quet_giao_dich_dang_cho() == 1


def test_quet_bo_qua_giao_dich_con_moi(kho, monkeypatch):
    import datetime
    moi = vp.dinh_dang_gio_vn(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=30))
    monkeypatch.setattr(tt.repo, "lay_ma_giao_dich_dang_cho", lambda: [f"DCAB12-{moi}"])
    monkeypatch.setattr(vp, "truy_van_giao_dich", lambda m: pytest.fail("giao dịch còn mới, chưa được hỏi"))
    assert tt.quet_giao_dich_dang_cho() == 0
