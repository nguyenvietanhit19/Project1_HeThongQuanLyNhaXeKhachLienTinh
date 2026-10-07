"""Unit test đặt vé online (UC-05, UC-08) — hàm thuần + service với Repository giả lập.

Khóa ghế thật (SELECT ... FOR UPDATE, giao đoạn) kiểm bằng SQL trên DB tạm, không phải ở đây.
"""

import datetime

import pytest

from app.services import dat_ve_service as svc
from app.utils.loi import GiaTriLoi

UTC = datetime.timezone.utc
BAY_GIO = datetime.datetime(2026, 10, 10, 8, 0, tzinfo=UTC)


def _ve(so_ghe="1", gia=100000, trang_thai="giu_cho", han=None, loai="thanh_toan_ngay", gio_don=None, **kw):
    v = {
        "id": f"ve-{so_ghe}", "so_ghe": so_ghe, "gia": gia, "trang_thai": trang_thai, "loai_hinh_thanh_toan": loai,
        "la_ve_dat_coc": False, "han_giu_cho_den": han, "ma_dat_cho": "DCAB12", "chuyen_id": "c1", "diem_don_id": "d1",
        "diem_tra_id": "d2", "ma_chuyen": "T001-LX001-261011-0600-DI", "gio_khoi_hanh": BAY_GIO + datetime.timedelta(hours=24),
        "tuyen_id": "t1", "chieu": "xuoi", "trang_thai_chuyen": "chua_khoi_hanh", "ten_diem_don": "VP A", "ten_diem_tra": "VP C",
        "khu_vuc_di_id": "kvA", "khu_vuc_den_id": "kvC", "ten_loai_xe": "Xe thường", "gio_bat_dau_dem_han": None,
        "gio_don_du_kien": gio_don or BAY_GIO + datetime.timedelta(hours=24),
        "gio_den_du_kien": BAY_GIO + datetime.timedelta(hours=30),
    }
    v.update(kw)
    return v


# ---------------------------------------------------------
# Hàm thuần
# ---------------------------------------------------------
def test_chuan_hoa_ghe_bo_khoang_trang_va_dung_thu_tu():
    assert svc.chuan_hoa_danh_sach_ghe([" A1", "A2 "]) == ["A1", "A2"]


@pytest.mark.parametrize("ghe", [[], ["", "  "], ["A1", "A1"], [str(i) for i in range(11)]])
def test_chuan_hoa_ghe_chan_du_lieu_xau(ghe):
    with pytest.raises(GiaTriLoi):
        svc.chuan_hoa_danh_sach_ghe(ghe)


@pytest.mark.parametrize(
    "so_ve,tong,ket_qua",
    [(1, 5_000_000, False), (2, 600_000, False), (2, 600_001, True), (3, 450_000, False), (4, 1_000_000, True)],
)
def test_can_dat_coc(so_ve, tong, ket_qua):
    assert svc.can_dat_coc(so_ve, tong) is ket_qua


def test_ma_dat_cho_khong_trung_nhau():
    assert len({svc.sinh_ma_dat_cho() for _ in range(200)}) == 200


def test_trang_thai_dang_giu_tam():
    han = BAY_GIO + datetime.timedelta(minutes=5)
    assert svc.trang_thai_dat_cho([_ve(han=han)], BAY_GIO) == "dang_giu"


def test_trang_thai_het_han_khi_qua_han_du_job_chua_quet():
    han = BAY_GIO - datetime.timedelta(seconds=1)
    assert svc.trang_thai_dat_cho([_ve(han=han)], BAY_GIO) == "het_han"


def test_trang_thai_tai_quay_khong_han_la_dat_thanh_cong():
    assert svc.trang_thai_dat_cho([_ve(han=None, loai="thanh_toan_tai_quay")], BAY_GIO) == "dat_thanh_cong_tai_quay"


def test_trang_thai_da_thanh_toan_va_da_huy():
    assert svc.trang_thai_dat_cho([_ve(trang_thai="da_thanh_toan")], BAY_GIO) == "da_thanh_toan"
    assert svc.trang_thai_dat_cho([_ve(trang_thai="da_huy")], BAY_GIO) == "da_huy"
    assert svc.trang_thai_dat_cho([_ve(trang_thai="het_han")], BAY_GIO) == "het_han"


def test_moc_chot_truoc_x_phut_tai_diem_don():
    gio_don = BAY_GIO + datetime.timedelta(minutes=svc.X_PHUT_CHOT_LEN_XE)
    assert svc.con_truoc_moc_chot(gio_don, BAY_GIO) is False  # đúng mốc chốt = hết quyền hủy
    assert svc.con_truoc_moc_chot(gio_don + datetime.timedelta(minutes=1), BAY_GIO) is True


# ---------------------------------------------------------
# Service với repository giả
# ---------------------------------------------------------
class _Gia:  # chuyến giả dạng dòng của tim_chuyen
    r = {
        "diem_don_id": "d1", "diem_tra_id": "d9",
        "so_do_ghe": [{"ma_ghe": g, "tang": 1, "x": 0, "y": 0} for g in ("1", "2", "3")],
    }


@pytest.fixture
def gia_lap(monkeypatch):
    ho_so = {"khoa_thanh_toan_tai_quay": False, "bi_khoa": False, "ly_do_khoa": None}
    monkeypatch.setattr(svc.ho_so_repo, "lay_theo_id", lambda nid: ho_so)
    monkeypatch.setattr(svc, "_bay_gio", lambda: BAY_GIO)
    return ho_so


def test_giu_cho_thanh_cong_dung_doan_rong_nhat_va_gia(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 150000}, {"3"}))
    goi = {}
    monkeypatch.setattr(svc.lock_repo, "giu_ghe", lambda **kw: goi.update(kw))
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: [_ve("1", 150000, han=BAY_GIO + datetime.timedelta(minutes=9), ma_dat_cho=ma), _ve("2", 150000, han=BAY_GIO + datetime.timedelta(minutes=9), ma_dat_cho=ma)])
    kq = svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1", "2"])
    assert goi["diem_don_id"] == "d1" and goi["diem_tra_id"] == "d9" and goi["gia"] == 150000
    assert goi["danh_sach_ghe"] == ["1", "2"] and goi["khach_hang_id"] == "kh1"
    assert kq["tong_tien"] == 300000 and kq["so_ve"] == 2 and kq["trang_thai"] == "dang_giu"
    assert kq["can_dat_coc"] is False and kq["cho_phep_huy"] is True


def test_giu_cho_chan_tai_khoan_bi_khoa(monkeypatch, gia_lap):
    gia_lap["bi_khoa"] = True
    with pytest.raises(GiaTriLoi, match="hạn chế"):
        svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1"])


def test_giu_cho_ghe_khong_ton_tai(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 1}, set()))
    with pytest.raises(GiaTriLoi, match="không tồn tại"):
        svc.giu_cho("kh1", "c1", "kvA", "kvC", ["99"])


def _diem(diem_id, loai, kv, hl):
    return {"diem_id": diem_id, "ten": diem_id, "loai": loai, "khu_vuc_id": kv, "hl": hl}


DIEM = [
    _diem("d1", "van_phong", "kvA", 1), _diem("d2", "van_phong", "kvA", 2), _diem("dd", "diem_dung", "kvA", 3),
    _diem("d3", "diem_dung", "kvC", 4), _diem("d9", "van_phong", "kvC", 5),
]


def _chuan_bi_dat_cho(monkeypatch, ve_list=None):
    ve_list = ve_list or [_ve("1", han=BAY_GIO + datetime.timedelta(minutes=9))]
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: ve_list)
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: DIEM)
    return ve_list


@pytest.mark.parametrize(
    "don,tra,loi",
    [
        ("dd", "d9", "văn phòng"),  # điểm đón là điểm dừng
        ("d9", "d9", "khu vực điểm đi"),  # điểm đón sai khu vực
        ("d1", "d2", "khu vực điểm đến"),  # điểm trả sai khu vực
        ("d1", "khong-co", "không thuộc tuyến"),
    ],
)
def test_giu_cho_chan_cap_diem_sai_va_khong_khoa_ghe(monkeypatch, gia_lap, don, tra, loi):
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 150000}, set()))
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: DIEM)
    monkeypatch.setattr(svc.lock_repo, "giu_ghe", lambda **kw: pytest.fail("không được khóa ghế khi điểm sai"))
    with pytest.raises(GiaTriLoi, match=loi):
        svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1"], don, tra)


def test_giu_cho_diem_tra_dung_truoc_diem_don(monkeypatch, gia_lap):
    diem = [_diem("d1", "van_phong", "kvA", 5), _diem("d9", "van_phong", "kvC", 2)]  # điểm trả có thứ tự nhỏ hơn
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 1}, set()))
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: diem)
    with pytest.raises(GiaTriLoi, match="đứng sau"):
        svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1"], "d1", "d9")


def test_giu_cho_khoa_ghe_tren_dung_doan_khach_chon_khong_phai_doan_rong_nhat(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 150000}, set()))
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: DIEM)
    goi = {}
    monkeypatch.setattr(svc.lock_repo, "giu_ghe", lambda **kw: goi.update(kw))
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: [_ve("1", 150000, han=BAY_GIO + datetime.timedelta(minutes=9), ma_dat_cho=ma)])
    svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1"], "d2", "d3")
    assert goi["diem_don_id"] == "d2" and goi["diem_tra_id"] == "d3" and goi["han_giu_tam_phut"] == 10


def test_giu_cho_ghe_thay_la_co_nguoi_tren_doan_rong_van_giu_duoc_neu_doan_hep_trong(monkeypatch, gia_lap):
    # sơ đồ (đoạn rộng nhất) báo ghế 3 có người, nhưng khách chọn đoạn hẹp — việc phán quyết nằm ở giu_ghe, không chặn sớm
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 1}, {"3"}))
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: DIEM)
    goi = {}
    monkeypatch.setattr(svc.lock_repo, "giu_ghe", lambda **kw: goi.update(kw))
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: [_ve("3", 1, han=BAY_GIO + datetime.timedelta(minutes=9), ma_dat_cho=ma)])
    svc.giu_cho("kh1", "c1", "kvA", "kvC", ["3"], "d2", "d3")
    assert goi["danh_sach_ghe"] == ["3"]


def test_giu_cho_nguoi_den_sau_nhan_loi_tu_giu_ghe(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.tim_kiem, "lay_chuyen_mo_ban", lambda c, a, b: (_Gia.r, {"gia": 1}, set()))
    monkeypatch.setattr(svc.lock_repo, "tim_diem_cua_chuyen", lambda cid: DIEM)

    def da_co_nguoi(**kw):
        raise GiaTriLoi("Ghế 1 đã có người chọn — vui lòng chọn ghế khác")

    monkeypatch.setattr(svc.lock_repo, "giu_ghe", da_co_nguoi)
    with pytest.raises(GiaTriLoi, match="đã có người"):
        svc.giu_cho("kh1", "c1", "kvA", "kvC", ["1"], "d1", "d9")


def test_lay_dat_cho_cua_nguoi_khac_la_khong_tim_thay(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: [])
    with pytest.raises(GiaTriLoi, match="Không tìm thấy"):
        svc.xem_dat_cho("kh-khac", "DCAB12")


def _live(*ghe_gia, han_phut=9):
    han = BAY_GIO + datetime.timedelta(minutes=han_phut)
    return [_ve(g, gia, han=han) for g, gia in ghe_gia]


def test_bo_ghe_thanh_cong_chi_huy_dung_ghe_do(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000), ("2", 100000)))
    goi = {}
    monkeypatch.setattr(svc.lock_repo, "bo_ghe", lambda ma, nid, g: goi.setdefault("ghe", g) and True)
    svc.bo_ghe("kh1", "DCAB12", "2")
    assert goi["ghe"] == "2"


def test_bo_ghe_khong_co_trong_luot_dat(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    with pytest.raises(GiaTriLoi, match="không còn trong lượt"):
        svc.bo_ghe("kh1", "DCAB12", "9")


def test_bo_ghe_qua_moc_chot(monkeypatch, gia_lap):
    gio_don = BAY_GIO + datetime.timedelta(minutes=2)
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", han=BAY_GIO + datetime.timedelta(minutes=9), gio_don=gio_don)])
    monkeypatch.setattr(svc.lock_repo, "bo_ghe", lambda *a: pytest.fail("không được bỏ ghế"))
    with pytest.raises(GiaTriLoi, match="mốc chốt"):
        svc.bo_ghe("kh1", "DCAB12", "1")


@pytest.mark.parametrize(
    "so_ve,tong,so_coc",
    [(1, 9_000_000, 0), (2, 600_000, 0), (2, 700_000, 1), (3, 900_000, 1), (4, 900_000, 2), (5, 1_500_000, 2)],
)
def test_so_ve_phai_dat_coc_la_mot_nua_lam_tron_xuong(so_ve, tong, so_coc):
    assert svc.so_ve_phai_dat_coc(so_ve, tong) == so_coc


def test_thanh_toan_tai_quay_chi_ap_dung_cho_ghe_duoc_tich(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000), ("2", 100000), ("3", 100000)))
    goi = {}
    monkeypatch.setattr(svc.lock_repo, "chot_thanh_toan_tai_quay", lambda ma, nid, chon, con_giu: goi.update(chon=chon, con_giu=con_giu) or True)
    svc.thanh_toan("kh1", "DCAB12", ["1", "3"], "thanh_toan_tai_quay")
    assert goi == {"chon": ["1", "3"], "con_giu": 3}  # 3 vé đang giữ, chỉ 2 vé được chốt, vé còn lại bị nhả


def test_thanh_toan_ghe_khong_thuoc_luot_dat(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    with pytest.raises(GiaTriLoi, match="không còn trong lượt"):
        svc.thanh_toan("kh1", "DCAB12", ["1", "7"], "thanh_toan_tai_quay")


def test_thanh_toan_tai_quay_chon_2_ghe_tren_600k_van_phai_coc(monkeypatch, gia_lap):
    # đặt 5 ghế nhưng chỉ tích 2 ghế, tổng 700.000đ > 600.000đ → vẫn phải cọc 1 vé
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 350000), ("2", 350000), ("3", 350000), ("4", 350000), ("5", 350000)))
    monkeypatch.setattr(svc.lock_repo, "chot_thanh_toan_tai_quay", lambda *a: pytest.fail("không được chốt khi cần cọc"))
    with pytest.raises(GiaTriLoi, match="cần đặt cọc.*1 vé"):
        svc.thanh_toan("kh1", "DCAB12", ["1", "2"], "thanh_toan_tai_quay")


def test_thanh_toan_tich_it_ghe_duoi_nguong_khong_can_coc(monkeypatch, gia_lap):
    # 5 ghế tổng 1.750.000đ nhưng chỉ tích 1 ghế 350.000đ → không cọc
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 350000), ("2", 350000), ("3", 350000), ("4", 350000), ("5", 350000)))
    monkeypatch.setattr(svc.lock_repo, "chot_thanh_toan_tai_quay", lambda *a: True)
    svc.thanh_toan("kh1", "DCAB12", ["1"], "thanh_toan_tai_quay")


def _vnpay_gia_lap(monkeypatch):
    goi = {}
    monkeypatch.setattr(svc.thanh_toan_repo, "bat_dau_thanh_toan_ngay", lambda *a: goi.update(args=a) or True)
    return goi


def test_thanh_toan_vnpay_lo_khong_coc_moi_ghe_duoc_tich_deu_tra_vnpay(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 200000), ("2", 200000), ("3", 200000)))
    goi = _vnpay_gia_lap(monkeypatch)
    svc.thanh_toan("kh1", "DCAB12", ["1", "2"], "vnpay_qr")
    ma, nid, online, quay, con_giu, han, la_coc = goi["args"]
    assert online == ["1", "2"] and quay == [] and con_giu == 3 and la_coc is False
    assert han == 5 + 2  # hạn cổng 5 phút + 2 phút đệm cho IPN


def test_thanh_toan_vnpay_lo_coc_chi_n_ghe_dau_tra_vnpay_con_lai_tai_quay(monkeypatch, gia_lap):
    # 4 ghế × 200.000đ = 800.000đ > 600.000đ → cọc 2 vé: 2 ghế đầu VNPay, 2 ghế sau tại quầy
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 200000), ("2", 200000), ("3", 200000), ("4", 200000)))
    goi = _vnpay_gia_lap(monkeypatch)
    svc.thanh_toan("kh1", "DCAB12", ["4", "2", "1", "3"], "vnpay_qr")
    ma, nid, online, quay, con_giu, han, la_coc = goi["args"]
    assert online == ["1", "2"] and quay == ["3", "4"] and la_coc is True


def test_thanh_toan_vnpay_chi_tinh_tren_ghe_duoc_tich(monkeypatch, gia_lap):
    # đặt 5 ghế, tích 2 ghế tổng 700.000đ > 600.000đ → cọc 1 vé (ghế đầu của 2 ghế được tích), ghế kia tại quầy
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 350000), ("2", 350000), ("3", 350000), ("4", 350000), ("5", 350000)))
    goi = _vnpay_gia_lap(monkeypatch)
    svc.thanh_toan("kh1", "DCAB12", ["3", "5"], "vnpay_qr")
    ma, nid, online, quay, con_giu, han, la_coc = goi["args"]
    assert online == ["3"] and quay == ["5"] and con_giu == 5 and la_coc is True


def test_thanh_toan_vnpay_lo_het_han_giua_chung(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    monkeypatch.setattr(svc.thanh_toan_repo, "bat_dau_thanh_toan_ngay", lambda *a: False)
    with pytest.raises(GiaTriLoi, match="hết hạn"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "vnpay_qr")


def test_da_bam_vnpay_roi_khong_thanh_toan_lai_duoc_nua(monkeypatch, gia_lap):
    # lượt đã chờ thanh toán thì phải dùng đường dẫn thanh toán (không chọn lại loại hình)
    han = BAY_GIO + datetime.timedelta(minutes=6)
    cho = [_ve("1", 100000, han=han, gio_bat_dau_dem_han=BAY_GIO)]
    _chuan_bi_dat_cho(monkeypatch, cho)
    with pytest.raises(GiaTriLoi, match="đã hết hạn hoặc đã được xử lý"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "thanh_toan_tai_quay")


# ---------- trạng thái chờ thanh toán, đường dẫn, giỏ hàng ----------
def test_trang_thai_cho_thanh_toan_sau_khi_bam_vnpay():
    han = BAY_GIO + datetime.timedelta(minutes=6)
    assert svc.trang_thai_dat_cho([_ve("1", han=han, gio_bat_dau_dem_han=BAY_GIO)], BAY_GIO) == "cho_thanh_toan"
    assert svc.trang_thai_dat_cho([_ve("1", han=han)], BAY_GIO) == "dang_giu"  # chưa bấm Thanh toán


def test_han_thanh_toan_tru_phan_dem_cua_ipn(gia_lap):
    han_giu = BAY_GIO + datetime.timedelta(minutes=7)
    r = svc._dung_dat_cho([_ve("1", han=han_giu, gio_bat_dau_dem_han=BAY_GIO)], gia_lap)
    assert r["trang_thai"] == "cho_thanh_toan" and r["han_giu_cho_den"] == han_giu
    assert r["han_thanh_toan"] == BAY_GIO + datetime.timedelta(minutes=5)
    assert r["chuyen"]["ten_loai_xe"] == "Xe thường"
    assert svc._dung_dat_cho([_ve("1", han=han_giu)], gia_lap)["han_thanh_toan"] is None


def _cho_thanh_toan(monkeypatch, ve_list):
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: ve_list)
    monkeypatch.setattr(svc.vnpay_service, "CORS_ORIGINS", ["http://localhost:5500"])


def test_tao_duong_dan_thanh_toan_dung_so_tien_va_han(monkeypatch, gia_lap):
    han = BAY_GIO + datetime.timedelta(minutes=7)
    ve = [_ve("1", 200000, han=han, gio_bat_dau_dem_han=BAY_GIO), _ve("2", 200000, han=han, gio_bat_dau_dem_han=BAY_GIO),
          _ve("3", 200000, han=han, loai="thanh_toan_tai_quay", gio_bat_dau_dem_han=None)]  # phần trả tại quầy: không tính
    _cho_thanh_toan(monkeypatch, ve)
    url = svc.tao_duong_dan_thanh_toan("kh1", "DCAB12", "http://localhost:5500", "1.2.3.4")
    assert "vnp_Amount=40000000" in url
    assert "vnp_ExpireDate=20261010150500" in url  # 08:00 UTC + 5 phút = 15:05 giờ Việt Nam


def test_tao_duong_dan_chi_khi_dang_cho_thanh_toan(monkeypatch, gia_lap):
    _cho_thanh_toan(monkeypatch, [_ve("1", han=BAY_GIO + datetime.timedelta(minutes=9))])  # mới giữ ghế, chưa bấm Thanh toán
    with pytest.raises(GiaTriLoi, match="chờ thanh toán"):
        svc.tao_duong_dan_thanh_toan("kh1", "DCAB12", "http://localhost:5500")


def test_tao_duong_dan_het_thoi_gian_thanh_toan_du_con_phan_dem(monkeypatch, gia_lap):
    han = BAY_GIO + datetime.timedelta(minutes=1)  # còn 1 phút giữ vé nhưng hạn cổng (trừ 2 phút đệm) đã qua
    _cho_thanh_toan(monkeypatch, [_ve("1", han=han, gio_bat_dau_dem_han=BAY_GIO)])
    with pytest.raises(GiaTriLoi, match="hết thời gian thanh toán"):
        svc.tao_duong_dan_thanh_toan("kh1", "DCAB12", "http://localhost:5500")


@pytest.mark.parametrize("origin", [None, "", "https://trang-la.example"])
def test_tao_duong_dan_origin_la_bi_chan(monkeypatch, gia_lap, origin):
    han = BAY_GIO + datetime.timedelta(minutes=7)
    _cho_thanh_toan(monkeypatch, [_ve("1", han=han, gio_bat_dau_dem_han=BAY_GIO)])
    with pytest.raises(GiaTriLoi, match="không hợp lệ"):
        svc.tao_duong_dan_thanh_toan("kh1", "DCAB12", origin)


def test_gio_hang_gom_luot_dang_giu_va_cho_thanh_toan_bo_luot_da_xong(monkeypatch, gia_lap):
    han = BAY_GIO + datetime.timedelta(minutes=8)
    lo = {
        "DC1": [_ve("1", han=han, ma_dat_cho="DC1")],  # đang giữ 10 phút
        "DC2": [_ve("2", han=han, ma_dat_cho="DC2", gio_bat_dau_dem_han=BAY_GIO)],  # chờ thanh toán VNPay
        "DC3": [_ve("3", han=None, ma_dat_cho="DC3", loai="thanh_toan_tai_quay")],  # đã đặt thành công tại quầy
    }
    monkeypatch.setattr(svc.lock_repo, "tim_ma_dat_cho_con_giu", lambda nid: ["DC1", "DC2", "DC3"])
    monkeypatch.setattr(svc.lock_repo, "lay_dat_cho", lambda ma, nid: lo[ma])
    kq = svc.gio_hang("kh1")
    assert [(d["ma_dat_cho"], d["trang_thai"]) for d in kq] == [("DC1", "dang_giu"), ("DC2", "cho_thanh_toan")]


def test_gio_hang_rong(monkeypatch, gia_lap):
    monkeypatch.setattr(svc.lock_repo, "tim_ma_dat_cho_con_giu", lambda nid: [])
    assert svc.gio_hang("kh1") == []


def test_huy_duoc_ca_khi_dang_cho_thanh_toan(monkeypatch, gia_lap):
    han = BAY_GIO + datetime.timedelta(minutes=6)
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", han=han, gio_bat_dau_dem_han=BAY_GIO)])
    monkeypatch.setattr(svc.lock_repo, "huy_dat_cho", lambda ma, nid: 1)
    assert svc.huy_dat_cho("kh1", "DCAB12")["so_ve_da_huy"] == 1


def test_thanh_toan_loai_hinh_la(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    with pytest.raises(GiaTriLoi, match="không hợp lệ"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "chuyen_khoan_la")


def test_thanh_toan_tai_quay_bi_chan_khi_khach_bi_han_che(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    gia_lap["khoa_thanh_toan_tai_quay"] = True
    with pytest.raises(GiaTriLoi, match="chỉ được thanh toán ngay"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "thanh_toan_tai_quay")


def test_thanh_toan_lo_het_han(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", han=BAY_GIO - datetime.timedelta(minutes=1))])
    with pytest.raises(GiaTriLoi, match="hết hạn"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "thanh_toan_tai_quay")


def test_thanh_toan_chot_that_bai_giua_chung(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, _live(("1", 100000)))
    monkeypatch.setattr(svc.lock_repo, "chot_thanh_toan_tai_quay", lambda *a: False)
    with pytest.raises(GiaTriLoi, match="hết hạn"):
        svc.thanh_toan("kh1", "DCAB12", ["1"], "thanh_toan_tai_quay")


def test_hien_thi_bo_ghe_da_huy_khoi_lo_dat(gia_lap):
    han = BAY_GIO + datetime.timedelta(minutes=9)
    r = svc._dung_dat_cho([_ve("1", 100000, han=han), _ve("2", 100000, trang_thai="da_huy")], gia_lap)
    assert r["so_ve"] == 1 and r["tong_tien"] == 100000 and [v["so_ghe"] for v in r["ve"]] == ["1"]
    assert r["nguong_dat_coc"] == 600000 and r["ty_le_dat_coc"] == 0.5


def test_huy_giu_cho_thanh_cong(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch)
    monkeypatch.setattr(svc.lock_repo, "huy_dat_cho", lambda ma, nid: 1)
    assert svc.huy_dat_cho("kh1", "DCAB12") == {"ma_dat_cho": "DCAB12", "so_ve_da_huy": 1}


def test_huy_giu_cho_qua_moc_chot(monkeypatch, gia_lap):
    gio_don = BAY_GIO + datetime.timedelta(minutes=3)
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", han=None, loai="thanh_toan_tai_quay", gio_don=gio_don)])
    monkeypatch.setattr(svc.lock_repo, "huy_dat_cho", lambda ma, nid: pytest.fail("không được hủy"))
    with pytest.raises(GiaTriLoi, match="mốc chốt"):
        svc.huy_dat_cho("kh1", "DCAB12")


def test_huy_ve_da_thanh_toan_bi_chan(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", trang_thai="da_thanh_toan")])
    with pytest.raises(GiaTriLoi, match="đã thanh toán"):
        svc.huy_dat_cho("kh1", "DCAB12")


def test_huy_lo_da_het_han_bi_chan(monkeypatch, gia_lap):
    _chuan_bi_dat_cho(monkeypatch, [_ve("1", trang_thai="het_han")])
    with pytest.raises(GiaTriLoi, match="không còn"):
        svc.huy_dat_cho("kh1", "DCAB12")
