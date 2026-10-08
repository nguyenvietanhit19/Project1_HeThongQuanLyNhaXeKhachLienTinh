"""Unit test thông báo cho khách hàng: nội dung, hàm gửi (không bao giờ ném lỗi), các sự kiện gắn ở service/job — Repository giả lập."""

import datetime

import pytest

from app.jobs import quet_nhac_sap_di, quet_no_show, quet_ve_het_han
from app.services import dat_ve_service as dv
from app.services import thanh_toan_service as tt
from app.services import thong_bao_khach_service as tbk
from app.services import vnpay_service as vp
from tests.unit.test_dat_ve_service import BAY_GIO, _ve

gui_that = tbk.gui  # bản gốc, lấy TRƯỚC khi fixture tự động (conftest) thay bằng hàm ghi lại
UTC = datetime.timezone.utc


# ---------------------------------------------------------
# Nội dung
# ---------------------------------------------------------
GIO_DON = datetime.datetime(2026, 10, 10, 1, 0, tzinfo=UTC)  # 08:00 giờ Việt Nam


def test_noi_dung_dat_ve_tai_quay():
    nd = tbk.nd_dat_ve_tai_quay("DCAB12", ["A1", "A2"], "Bến xe Mỹ Đình", GIO_DON, 600000)
    assert nd == "Đặt vé thành công — mã đặt chỗ DCAB12, ghế A1, A2. Vui lòng ra Bến xe Mỹ Đình trước 08:00 ngày 10/10/2026 để nhận vé và thanh toán 600.000đ."


def test_noi_dung_thanh_toan():
    assert tbk.nd_thanh_toan_thanh_cong("DCAB12", ["B1"], 300000) == "Thanh toán thành công 300.000đ — mã đặt chỗ DCAB12, ghế B1."
    assert tbk.nd_thanh_toan_ve_thanh_cong("VE000007", "B1", 1250000) == "Thanh toán thành công 1.250.000đ cho vé VE000007 (ghế B1)."


def test_noi_dung_that_bai_va_het_han_neu_ma_va_ghe():
    assert "DCAB12" in tbk.nd_thanh_toan_that_bai("DCAB12", ["A1", "A2"]) and "A1, A2" in tbk.nd_thanh_toan_that_bai("DCAB12", ["A1", "A2"])
    assert "hết hạn giữ chỗ" in tbk.nd_het_han("DCAB12", ["A1"])


def test_noi_dung_khong_den_canh_bao_truoc_nguong_va_khoa_khi_du_nguong():
    chua_du = tbk.nd_khong_den("VE000001", "A1", 2, 3, 30)
    assert "2/3" in chua_du and "chỉ được thanh toán ngay" not in chua_du
    du = tbk.nd_khong_den("VE000001", "A1", 3, 3, 30)
    assert "chỉ được thanh toán ngay" in du and "3 lần trong 30 ngày" in du


@pytest.mark.parametrize("con_phut, mong_doi", [(125, "2 giờ 05 phút"), (60, "1 giờ 00 phút"), (45, "45 phút"), (0, "1 phút")])
def test_noi_dung_sap_di_cach_noi_thoi_gian_con_lai(con_phut, mong_doi):
    nd = tbk.nd_sap_di("DCAB12", ["A1"], "Bến xe Mỹ Đình", "Vinh", GIO_DON, con_phut)
    assert f"còn khoảng {mong_doi}" in nd and "Bến xe Mỹ Đình → Vinh" in nd and "08:00 ngày 10/10/2026" in nd


# ---------------------------------------------------------
# Hàm gửi: lưu rồi đẩy, không bao giờ ném lỗi
# ---------------------------------------------------------
def test_gui_luu_roi_day_real_time(monkeypatch):
    nhat_ky = []
    monkeypatch.setattr(tbk.thong_bao_repo, "tao", lambda nguoi, nd, ve_id=None: nhat_ky.append(("luu", nguoi, nd, ve_id)))
    monkeypatch.setattr(tbk, "broadcast_sync", lambda nguoi, nd: nhat_ky.append(("day", nguoi, nd)))
    gui_that("kh1", "xin chào", ve_id="ve-1")
    assert nhat_ky == [("luu", "kh1", "xin chào", "ve-1"), ("day", "kh1", "xin chào")]  # đúng thứ tự: lưu TRƯỚC


def test_gui_khong_co_nguoi_nhan_thi_bo_qua(monkeypatch):
    monkeypatch.setattr(tbk.thong_bao_repo, "tao", lambda *a, **k: pytest.fail("không được ghi"))
    gui_that(None, "x")


@pytest.mark.parametrize("hong", ["repo", "day"])
def test_gui_loi_khong_lam_hong_nghiep_vu(monkeypatch, hong):
    def no(*a, **k):
        raise RuntimeError("hỏng")

    monkeypatch.setattr(tbk.thong_bao_repo, "tao", no if hong == "repo" else lambda *a, **k: None)
    monkeypatch.setattr(tbk, "broadcast_sync", no if hong == "day" else lambda *a, **k: None)
    gui_that("kh1", "x")  # không ném


# ---------------------------------------------------------
# Thanh toán xong / không thành công (IPN)
# ---------------------------------------------------------
KHOA = "khoa-bi-mat-thu-nghiem"


@pytest.fixture
def cong(monkeypatch):
    monkeypatch.setattr(vp, "VNPAY_HASH_SECRET", KHOA)
    ghi = {"ve": [], "da_tra": 2, "huy": 2}
    monkeypatch.setattr(tt.repo, "lay_ve_cua_dat_cho", lambda ma: ghi["ve"])
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ngay", lambda ma, gd: ghi["da_tra"])
    monkeypatch.setattr(tt.repo, "huy_thanh_toan_ngay", lambda ma: ghi["huy"])
    return ghi


def _ipn(so_tien, ma_phan_hoi="00", trang_thai="00", ma_gd="DCAB12-20261010150000"):
    p = {"vnp_TmnCode": "D", "vnp_Amount": str(so_tien * 100), "vnp_ResponseCode": ma_phan_hoi, "vnp_TransactionStatus": trang_thai,
         "vnp_TxnRef": ma_gd, "vnp_TransactionNo": "9"}
    p["vnp_SecureHash"] = vp.ky(p)
    return p


def test_ipn_thanh_cong_bao_khach_dung_ghe_va_tien(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000, khach_hang_id="kh1"), _ve("A2", gia=200000, khach_hang_id="kh1")]
    assert tt.xu_ly_ipn(_ipn(500000))["RspCode"] == "00"
    assert len(da_gui_thong_bao) == 1
    nguoi, noi_dung, ve_id = da_gui_thong_bao[0]
    assert nguoi == "kh1" and ve_id == "ve-A1"
    assert noi_dung == tbk.nd_thanh_toan_thanh_cong("DCAB12", ["A1", "A2"], 500000)


def test_ipn_thanh_cong_chi_tinh_ve_vua_tra_khong_tinh_ve_da_tra_truoc(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000, trang_thai="da_thanh_toan", khach_hang_id="kh1"), _ve("A2", gia=200000, khach_hang_id="kh1")]
    tt.xu_ly_ipn(_ipn(500000))
    assert da_gui_thong_bao[0][1] == tbk.nd_thanh_toan_thanh_cong("DCAB12", ["A2"], 200000)


def test_ipn_goi_lai_khi_da_xu_ly_khong_bao_lan_hai(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000, trang_thai="da_thanh_toan", khach_hang_id="kh1")]
    assert tt.xu_ly_ipn(_ipn(300000))["RspCode"] == "02"
    assert not da_gui_thong_bao


def test_ipn_het_han_khong_ghi_nhan_thi_khong_bao_thanh_cong(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000, khach_hang_id="kh1")]
    cong["da_tra"] = 0
    assert tt.xu_ly_ipn(_ipn(300000))["RspCode"] == "02"
    assert not da_gui_thong_bao


def test_ipn_that_bai_bao_khach_da_huy_giu_cho(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000, khach_hang_id="kh1"), _ve("A2", gia=300000, khach_hang_id="kh1")]
    assert tt.xu_ly_ipn(_ipn(600000, ma_phan_hoi="24", trang_thai="02"))["RspCode"] == "00"
    assert da_gui_thong_bao == [("kh1", tbk.nd_thanh_toan_that_bai("DCAB12", ["A1", "A2"]), "ve-A1")]


def test_ipn_khong_co_khach_hang_id_thi_khong_loi(cong, da_gui_thong_bao):
    cong["ve"] = [_ve("A1", gia=300000)]  # không có khach_hang_id
    assert tt.xu_ly_ipn(_ipn(300000))["RspCode"] == "00"


def test_ipn_ve_le_thanh_cong_bao_khach(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(vp, "VNPAY_HASH_SECRET", KHOA)
    ve = {"id": "ve-9", "ma_ve": "VE000009", "so_ghe": "C3", "ma_dat_cho": "DC1", "gia": 300000, "trang_thai": "giu_cho",
          "loai_hinh_thanh_toan": "thanh_toan_tai_quay", "han_giu_cho_den": None, "khach_hang_id": "kh1"}
    monkeypatch.setattr(tt.repo, "lay_ve_theo_ma_ve", lambda ma: ve)
    monkeypatch.setattr(tt.repo, "ghi_nhan_thanh_toan_ve_le", lambda ma, gd: 1)
    assert tt.xu_ly_ipn(_ipn(300000, ma_gd="VE000009-20261010150000"))["RspCode"] == "00"
    assert da_gui_thong_bao == [("kh1", tbk.nd_thanh_toan_ve_thanh_cong("VE000009", "C3", 300000), "ve-9")]


# ---------------------------------------------------------
# Chốt trả tại quầy (đặt vé thành công)
# ---------------------------------------------------------
def test_chot_tai_quay_bao_dat_ve_thanh_cong(monkeypatch, da_gui_thong_bao):
    ve = [_ve("1", gia=200000, han=BAY_GIO + datetime.timedelta(minutes=9)), _ve("2", gia=250000, han=BAY_GIO + datetime.timedelta(minutes=9))]
    monkeypatch.setattr(dv, "_bay_gio", lambda: BAY_GIO)
    monkeypatch.setattr(dv, "_lay_dat_cho_con_giu", lambda kh, ma: ve)
    monkeypatch.setattr(dv.ho_so_repo, "lay_theo_id", lambda kh: {"khoa_thanh_toan_tai_quay": False})
    monkeypatch.setattr(dv.lock_repo, "chot_thanh_toan_tai_quay", lambda *a: True)
    dat_cho = {"ma_dat_cho": "DCAB12", "chuyen": {"ten_diem_don": "VP A", "gio_don_du_kien": GIO_DON}, "ve": [{"id": "ve-1", "so_ghe": "1"}, {"id": "ve-2", "so_ghe": "2"}]}
    monkeypatch.setattr(dv, "xem_dat_cho", lambda kh, ma: dat_cho)
    assert dv.thanh_toan("kh1", "DCAB12", ["1", "2"], "thanh_toan_tai_quay") is dat_cho
    assert da_gui_thong_bao == [("kh1", tbk.nd_dat_ve_tai_quay("DCAB12", ["1", "2"], "VP A", GIO_DON, 450000), "ve-1")]


# ---------------------------------------------------------
# Job: hết hạn / không đến / sắp đến giờ
# ---------------------------------------------------------
def test_job_het_han_bao_moi_luot_mot_lan_va_bo_qua_khach_vang_lai(monkeypatch, da_gui_thong_bao):
    ve_het_han = [
        {"id": "a1", "ma_dat_cho": "DC1", "so_ghe": "A2", "khach_hang_id": "kh1"},
        {"id": "a2", "ma_dat_cho": "DC1", "so_ghe": "A1", "khach_hang_id": "kh1"},
        {"id": "b1", "ma_dat_cho": "DC2", "so_ghe": "B1", "khach_hang_id": "kh2"},
        {"id": "c1", "ma_dat_cho": "DC3", "so_ghe": "C1", "khach_hang_id": None},
    ]
    monkeypatch.setattr(quet_ve_het_han.lock_repo, "danh_dau_het_han_qua_han", lambda: ve_het_han)
    assert quet_ve_het_han.chay() == 4
    assert da_gui_thong_bao == [
        ("kh1", tbk.nd_het_han("DC1", ["A1", "A2"]), "a1"),
        ("kh2", tbk.nd_het_han("DC2", ["B1"]), "b1"),
    ]


def test_job_het_han_khong_co_gi_thi_khong_bao(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(quet_ve_het_han.lock_repo, "danh_dau_het_han_qua_han", lambda: [])
    assert quet_ve_het_han.chay() == 0 and not da_gui_thong_bao


def test_job_khong_den_bao_khach_kem_so_lan(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(quet_no_show.ve_repo, "tim_ve_qua_gio_len_xe", lambda x: [{"id": "v1", "khach_hang_id": "kh1", "ma_ve": "VE000001", "so_ghe": "A1"}])
    monkeypatch.setattr(quet_no_show.ve_repo, "danh_dau_khong_den", lambda i: None)
    monkeypatch.setattr(quet_no_show.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: 2)
    khoa = []
    monkeypatch.setattr(quet_no_show.ho_so_repo, "khoa_thanh_toan_tai_quay", lambda kh: khoa.append(kh))
    quet_no_show.chay()
    assert da_gui_thong_bao == [("kh1", tbk.nd_khong_den("VE000001", "A1", 2, quet_no_show.NGUONG_SO_LAN_VI_PHAM, quet_no_show.NGUONG_SO_NGAY_VI_PHAM), "v1")]
    assert not khoa  # mới 2 lần, chưa tới ngưỡng


def test_job_khong_den_du_nguong_khoa_va_bao_khoa(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(quet_no_show.ve_repo, "tim_ve_qua_gio_len_xe", lambda x: [{"id": "v1", "khach_hang_id": "kh1", "ma_ve": "VE000001", "so_ghe": "A1"}])
    monkeypatch.setattr(quet_no_show.ve_repo, "danh_dau_khong_den", lambda i: None)
    monkeypatch.setattr(quet_no_show.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: 3)
    khoa = []
    monkeypatch.setattr(quet_no_show.ho_so_repo, "khoa_thanh_toan_tai_quay", lambda kh: khoa.append(kh))
    quet_no_show.chay()
    assert khoa == ["kh1"] and "chỉ được thanh toán ngay" in da_gui_thong_bao[0][1]


def test_job_khong_den_khach_vang_lai_khong_bao(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(quet_no_show.ve_repo, "tim_ve_qua_gio_len_xe", lambda x: [{"id": "v1", "khach_hang_id": None, "ma_ve": "VE000001", "so_ghe": "A1"}])
    monkeypatch.setattr(quet_no_show.ve_repo, "danh_dau_khong_den", lambda i: None)
    quet_no_show.chay()
    assert not da_gui_thong_bao


def test_job_nhac_sap_di_gop_theo_luot_va_danh_dau_da_nhac(monkeypatch, da_gui_thong_bao):
    gio = BAY_GIO + datetime.timedelta(minutes=90)
    ve = [
        {"id": "a1", "ma_dat_cho": "DC1", "so_ghe": "A2", "khach_hang_id": "kh1", "ten_diem_don": "VP A", "ten_diem_tra": "VP C", "gio_don_du_kien": gio},
        {"id": "a2", "ma_dat_cho": "DC1", "so_ghe": "A1", "khach_hang_id": "kh1", "ten_diem_don": "VP A", "ten_diem_tra": "VP C", "gio_don_du_kien": gio},
        {"id": "b1", "ma_dat_cho": "DC2", "so_ghe": "B1", "khach_hang_id": "kh2", "ten_diem_don": "VP A", "ten_diem_tra": "VP C", "gio_don_du_kien": gio},
    ]
    da_nhac = []
    monkeypatch.setattr(quet_nhac_sap_di.nhac_repo, "tim_ve_can_nhac", lambda phut: ve)
    monkeypatch.setattr(quet_nhac_sap_di.nhac_repo, "danh_dau_da_nhac", lambda ids: da_nhac.append(list(ids)))
    assert quet_nhac_sap_di.chay(bay_gio=BAY_GIO) == 2
    assert da_gui_thong_bao == [
        ("kh1", tbk.nd_sap_di("DC1", ["A1", "A2"], "VP A", "VP C", gio, 90), "a1"),
        ("kh2", tbk.nd_sap_di("DC2", ["B1"], "VP A", "VP C", gio, 90), "b1"),
    ]
    assert da_nhac == [["a1", "a2"], ["b1"]]


def test_job_nhac_sap_di_khong_co_ve_thi_khong_lam_gi(monkeypatch, da_gui_thong_bao):
    monkeypatch.setattr(quet_nhac_sap_di.nhac_repo, "tim_ve_can_nhac", lambda phut: [])
    monkeypatch.setattr(quet_nhac_sap_di.nhac_repo, "danh_dau_da_nhac", lambda ids: pytest.fail("không có vé để đánh dấu"))
    assert quet_nhac_sap_di.chay() == 0 and not da_gui_thong_bao
