"""Unit test cho điều độ viên gán xe theo chu trình (UC-44) — phạm vi theo TUYẾN được phân công; giả lập Repository bằng monkeypatch,
không cần DB thật."""

import datetime
from zoneinfo import ZoneInfo

import pytest

from app.middleware.auth_middleware import NguoiDungHienTai
from app.services import dieu_do_service as dd
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

VN = ZoneInfo("Asia/Ho_Chi_Minh")
A, B = "diem-A", "diem-B"
TEN = {A: "Hà Nội", B: "Sapa"}


def gio(ngay: int, gio_: int, phut: int = 0) -> datetime.datetime:
    return datetime.datetime(2030, 1, ngay, gio_, phut, tzinfo=VN)


def chuyen(id_, chieu="xuoi", bat_dau=None, tong_phut=360, xe_id=None, **ghi_de):
    bat_dau = bat_dau or gio(10, 8)
    di, den = (A, B) if chieu == "xuoi" else (B, A)
    du_lieu = {
        "id": id_, "ma": f"MA-{id_}", "chu_trinh_id": "ct-1", "tuyen_id": "tuyen-1", "ma_tuyen": "T001", "ten_tuyen": "Hà Nội – Sapa",
        "chieu": chieu, "gio_khoi_hanh": bat_dau, "gio_ket_thuc": bat_dau + datetime.timedelta(minutes=tong_phut),
        "loai_xe_id": "loai-1", "ten_loai_xe": "Giường nằm", "trang_thai": "chua_khoi_hanh", "dang_hoan": False,
        "xe_id": xe_id, "bien_so_xe": "29B-1" if xe_id else None, "trang_thai_xe": "hoat_dong" if xe_id else None, "xe_thuc_te_id": None,
        "bien_so_xe_thuc_te": None, "trang_thai_xe_thuc_te": None, "co_canh_bao_xung_dot_vi_tri": False, "loai_su_co": None, "ly_do_su_co": None,
        "tong_phut": tong_phut,
        "diem_di_id": di, "ten_diem_di": TEN[di], "diem_den_id": den, "ten_diem_den": TEN[den],
    }
    du_lieu.update(ghi_de)
    return du_lieu


def chu_trinh_mau():
    """Đi 08:00–14:00, về 15:00–21:00 cùng ngày."""
    return [chuyen("di", "xuoi", gio(10, 8)), chuyen("ve", "nguoc", gio(10, 15))]


def xe(**ghi_de):
    du_lieu = {"id": "xe-1", "bien_so": "29B-1", "loai_xe_id": "loai-1", "trang_thai": "hoat_dong", "tuyen_id": None,
               "diem_goc_id": A, "ten_diem_goc": TEN[A], "ma_loai_xe": "LX001", "ten_loai_xe": "Giường nằm", "so_ghe": 34, "so_tang": 2,
               "ma_tuyen_co_dinh": None, "ten_tuyen_co_dinh": None}
    du_lieu.update(ghi_de)
    return du_lieu


def lich(trong_khoang=(), truoc=None, sau=None):
    return {"trong_khoang": list(trong_khoang), "truoc": truoc, "sau": sau}


TUYEN_1 = {"id": "tuyen-1", "ma": "T001", "ten": "Hà Nội – Sapa"}
TUYEN_KHAC = {"id": "tuyen-khac", "ma": "T009", "ten": "Hà Nội – Vinh"}


@pytest.fixture(autouse=True)
def phan_cong(monkeypatch):
    """Điều độ viên 'nd-1' mặc định được phân công tuyến 'tuyen-1' (tuyến của chu trình mẫu); test đổi bằng phan_cong['nd-1'] = [...]."""
    bang = {"nd-1": [TUYEN_1]}
    monkeypatch.setattr(dd.phan_cong_repo, "danh_sach_tuyen_cua_dieu_do_vien", lambda nguoi_dung_id: bang.get(nguoi_dung_id, []))
    return bang


def ddv():
    return NguoiDungHienTai(id="nd-1", vai_tro="dieu_do_vien")


def quan_ly():
    return NguoiDungHienTai(id="nd-2", vai_tro="quan_ly")


# ---------------------------------------------------------------- danh_gia_xe (quy tắc gán)
def test_xe_dung_loai_dung_vi_tri_khong_vuong_lich_gan_duoc():
    assert dd.danh_gia_xe(chu_trinh_mau(), xe(), lich()) == []


def test_xe_khac_loai_bi_chan():
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(loai_xe_id="loai-2"), lich())
    assert len(ly_do) == 1 and "Khác loại xe" in ly_do[0] and "Giường nằm" in ly_do[0]


def test_xe_bao_tri_bi_chan():
    assert any("hoạt động" in l for l in dd.danh_gia_xe(chu_trinh_mau(), xe(trang_thai="bao_tri"), lich()))


def test_xe_co_dinh_tuyen_khac_bi_chan_con_xe_co_dinh_dung_tuyen_hoac_linh_hoat_thi_duoc():
    assert any("cố định một tuyến khác" in l for l in dd.danh_gia_xe(chu_trinh_mau(), xe(tuyen_id="tuyen-khac"), lich()))
    assert dd.danh_gia_xe(chu_trinh_mau(), xe(tuyen_id="tuyen-1"), lich()) == []


def test_xe_dang_o_diem_khac_theo_chuyen_truoc_bi_chan_va_noi_ro_xe_se_o_dau():
    truoc = chuyen("truoc", "xuoi", gio(10, 0), tong_phut=240)  # đi A→B, kết thúc 04:00 → xe nằm ở B
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(), lich(truoc=truoc))
    assert len(ly_do) == 1
    assert "Sapa" in ly_do[0] and "sau chuyến MA-truoc" in ly_do[0] and "Hà Nội" in ly_do[0]


def test_xe_vua_ve_toi_diem_xuat_phat_theo_chuyen_truoc_gan_duoc():
    truoc = chuyen("truoc", "nguoc", gio(10, 0), tong_phut=240)  # về B→A, kết thúc 04:00 → xe nằm ở A
    assert dd.danh_gia_xe(chu_trinh_mau(), xe(), lich(truoc=truoc)) == []


def test_chua_co_chuyen_truoc_thi_lay_diem_goc_cua_xe():
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(diem_goc_id=B, ten_diem_goc="Sapa"), lich())
    assert len(ly_do) == 1 and "điểm gốc của xe" in ly_do[0]


def test_trung_lich_bao_ro_chuyen_va_khoang_nghi():
    khac = chuyen("khac", "xuoi", gio(10, 13), xe_id="xe-1")  # 13:00–19:00 chồng với chu trình
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(), lich(trong_khoang=[khac]))
    assert len(ly_do) == 1 and "Trùng lịch với chuyến MA-khac" in ly_do[0] and "30 phút" in ly_do[0]


def test_chu_trinh_lam_hong_chuyen_ke_tiep_cua_xe_bi_chan():
    sau = chuyen("sau", "nguoc", gio(11, 8), xe_id="xe-1")  # chuyến kế tiếp xuất phát từ B, nhưng sau chu trình xe ở A
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(), lich(sau=sau))
    assert len(ly_do) == 1 and "Sau chu trình này xe sẽ ở Hà Nội" in ly_do[0] and "MA-sau" in ly_do[0]


def test_chuyen_ke_tiep_xuat_phat_dung_cho_thi_khong_loi():
    sau = chuyen("sau", "xuoi", gio(11, 8), xe_id="xe-1")  # xuất phát từ A, khớp
    assert dd.danh_gia_xe(chu_trinh_mau(), xe(), lich(sau=sau)) == []


def test_nhieu_loi_cung_luc_duoc_liet_ke_het():
    truoc = chuyen("truoc", "xuoi", gio(10, 0), tong_phut=240)
    ly_do = dd.danh_gia_xe(chu_trinh_mau(), xe(trang_thai="bao_tri", loai_xe_id="loai-2"), lich(truoc=truoc))
    assert len(ly_do) == 3


def test_khung_chu_trinh_tu_chuyen_dau_den_chuyen_cuoi_ca_khoang_nghi():
    tu, den, moc = dd._khung_chu_trinh(chu_trinh_mau())
    assert tu == gio(10, 7, 30) and den == gio(10, 21, 30) and moc == gio(10, 8)


# ---------------------------------------------------------------- phạm vi quyền
def _gia_lap_chu_trinh(monkeypatch, chuyen_list=None):
    monkeypatch.setattr(dd.repo, "lay_chu_trinh", lambda _id: chu_trinh_mau() if chuyen_list is None else chuyen_list)


def test_danh_sach_xe_tuyen_khong_duoc_phan_cong_bi_chan(monkeypatch, phan_cong):
    _gia_lap_chu_trinh(monkeypatch)
    phan_cong["nd-1"] = [TUYEN_KHAC]
    with pytest.raises(CamTruyCap, match="chưa được phân công phụ trách tuyến này"):
        dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1")


def test_dieu_do_vien_chua_duoc_phan_cong_tuyen_nao_thi_khong_thay_chu_trinh_nao(monkeypatch, phan_cong):
    phan_cong["nd-1"] = []
    da_hoi = []
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, tuyen_ids: da_hoi.append(tuyen_ids) or [])
    assert dd.danh_sach_chu_trinh(ddv()) == []
    assert da_hoi == [[]]  # truy vấn nhận danh sách tuyến rỗng, không phải "mọi tuyến"


def test_pham_vi_dieu_do_vien_la_cac_tuyen_duoc_phan_cong_con_quan_ly_la_moi_tuyen(monkeypatch, phan_cong):
    phan_cong["nd-1"] = [TUYEN_1, TUYEN_KHAC]
    da_hoi = []
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, tuyen_ids: da_hoi.append(tuyen_ids) or [])
    dd.danh_sach_chu_trinh(quan_ly())
    dd.danh_sach_chu_trinh(ddv())
    assert da_hoi == [None, ["tuyen-1", "tuyen-khac"]]


def test_danh_sach_tuyen_phu_trach_dieu_do_vien_theo_phan_cong_quan_ly_la_moi_tuyen(monkeypatch, phan_cong):
    phan_cong["nd-1"] = [TUYEN_1, TUYEN_KHAC]
    assert [t["ma"] for t in dd.danh_sach_tuyen_phu_trach(ddv())] == ["T001", "T009"]
    monkeypatch.setattr(dd.dia_diem_repo, "danh_sach_tuyen", lambda: [{**TUYEN_1, "ngay_tao": 1}, {**TUYEN_KHAC, "ngay_tao": 2}, {"id": "t3", "ma": "T003", "ten": "X", "ngay_tao": 3}])
    ket_qua = dd.danh_sach_tuyen_phu_trach(quan_ly())
    assert [t["ma"] for t in ket_qua] == ["T001", "T009", "T003"] and all(set(t) == {"id", "ma", "ten"} for t in ket_qua)


def test_cua_so_ngoai_khoang_1_den_7_ngay_bi_chan():
    for so_ngay in (0, 8, -1):
        with pytest.raises(GiaTriLoi, match="1 đến 7 ngày"):
            dd.danh_sach_chu_trinh(quan_ly(), so_ngay)


def test_cua_so_mac_dinh_3_ngay_tinh_tu_bay_gio(monkeypatch):
    bay_gio = datetime.datetime(2030, 1, 10, 3, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dd, "_bay_gio", lambda: bay_gio)
    da_hoi = []
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, vp: da_hoi.append((tu, den)) or [])
    dd.danh_sach_chu_trinh(quan_ly())
    assert da_hoi == [(bay_gio, bay_gio + datetime.timedelta(days=3))]


def test_danh_sach_chu_trinh_gom_hai_chuyen_thanh_mot_dong_va_tinh_trang_thai_gan(monkeypatch):
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-1"),
                   chuyen("di2", "xuoi", gio(11, 8), chu_trinh_id="ct-2"), chuyen("ve2", "nguoc", gio(11, 15), chu_trinh_id="ct-2"),
                   chuyen("di3", "xuoi", gio(12, 8), chu_trinh_id="ct-3", xe_id="xe-2"), chuyen("ve3", "nguoc", gio(12, 15), chu_trinh_id="ct-3")]
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, vp: chuyen_list)
    ket_qua = dd.danh_sach_chu_trinh(quan_ly())
    assert [c["chu_trinh_id"] for c in ket_qua] == ["ct-1", "ct-2", "ct-3"]
    assert [c["trang_thai_gan"] for c in ket_qua] == ["da_gan", "chua_gan", "mot_phan"]
    assert [len(c["cac_chuyen"]) for c in ket_qua] == [2, 2, 2]
    assert ket_qua[0]["ten_tuyen"] == "Hà Nội – Sapa" and "ten_van_phong" not in ket_qua[0]


# ---------------------------------------------------------------- danh_sach_xe_cho_chu_trinh
def test_danh_sach_xe_xe_hop_le_xep_truoc_va_ghi_ly_do_xe_khong_hop_le(monkeypatch):
    _gia_lap_chu_trinh(monkeypatch)
    ds = [xe(id="xe-a", bien_so="29B-9"), xe(id="xe-b", bien_so="29B-1", diem_goc_id=B, ten_diem_goc="Sapa"), xe(id="xe-c", bien_so="29B-5")]
    monkeypatch.setattr(dd.repo, "danh_sach_xe_de_chon", lambda: ds)
    monkeypatch.setattr(dd.repo, "lich_cac_xe", lambda ids, *a: {i: lich() for i in ids})
    ket_qua = dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1")
    assert [(x["bien_so"], x["hop_le"]) for x in ket_qua] == [("29B-5", True), ("29B-9", True), ("29B-1", False)]
    assert ket_qua[2]["ly_do"] and ket_qua[0]["ly_do"] == []
    assert ket_qua[2]["ma_ly_do"] == ["sai_vi_tri"] and ket_qua[2]["vi_tri"]["ten_diem"] == "Sapa"
    assert ket_qua[0]["loai_xe"]["so_ghe"] == 34 and ket_qua[0]["dung_loai"] is True and ket_qua[0]["vi_tri"]["nguon"] == "diem_goc"


def test_danh_sach_xe_hien_ca_xe_khong_phu_hop_kem_ma_ly_do_va_vi_tri(monkeypatch):
    _gia_lap_chu_trinh(monkeypatch)
    ds = [
        xe(id="xe-ok", bien_so="29B-1"),
        xe(id="xe-bt", bien_so="29B-2", trang_thai="bao_tri"),
        xe(id="xe-lk", bien_so="29B-3", loai_xe_id="loai-2", ma_loai_xe="LX002", ten_loai_xe="Limousine"),
    ]
    truoc = {"ma": "MA-x", "gio_ket_thuc": gio(10, 5), "diem_den_id": B, "ten_diem_den": "Sapa"}
    monkeypatch.setattr(dd.repo, "danh_sach_xe_de_chon", lambda: ds)
    monkeypatch.setattr(dd.repo, "lich_cac_xe", lambda ids, *a: {i: (lich(truoc=truoc) if i == "xe-lk" else lich()) for i in ids})
    ket_qua = {x["xe_id"]: x for x in dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1")}
    assert set(ket_qua) == {"xe-ok", "xe-bt", "xe-lk"}
    assert ket_qua["xe-bt"]["ma_ly_do"] == ["khong_hoat_dong"]
    assert ket_qua["xe-lk"]["ma_ly_do"] == ["khac_loai", "sai_vi_tri"] and ket_qua["xe-lk"]["dung_loai"] is False
    assert ket_qua["xe-lk"]["vi_tri"] == {"diem_id": B, "ten_diem": "Sapa", "nguon": "sau_chuyen", "chuyen_ma": "MA-x", "tu_luc": gio(10, 5), "dung_diem_xuat_phat": False}


# ---------------------------------------------------------------- lộ trình + loại xe
def test_lo_trinh_chuyen_ve_di_nguoc_cac_diem_va_giu_thoi_gian_giua_2_diem(monkeypatch):
    _gia_lap_chu_trinh(monkeypatch)
    diem = [
        {"diem_don_tra_id": "d1", "ten": "Mỹ Đình", "ten_khu_vuc": "Hà Nội", "loai": "van_phong", "thu_tu": 1, "thoi_gian_du_kien_phut": 0},
        {"diem_don_tra_id": "d2", "ten": "Việt Trì", "ten_khu_vuc": "Phú Thọ", "loai": "diem_dung", "thu_tu": 2, "thoi_gian_du_kien_phut": 100},
        {"diem_don_tra_id": "d3", "ten": "Sapa", "ten_khu_vuc": "Lào Cai", "loai": "van_phong", "thu_tu": 3, "thoi_gian_du_kien_phut": 360},
    ]
    monkeypatch.setattr(dd.dia_diem_repo, "danh_sach_diem_theo_tuyen", lambda tuyen_id: diem)
    monkeypatch.setattr(dd.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": "loai-1", "ma": "LX001", "ten": "Giường nằm", "so_do_ghe": [{"ma_ghe": "A1", "tang": 1, "x": 0, "y": 0}, {"ma_ghe": "B1", "tang": 2, "x": 0, "y": 0}]})
    kq = dd.chi_tiet_chu_trinh(ddv(), "ct-1")
    di, ve = kq["cac_chuyen"]
    assert [d["ten"] for d in di["diem"]] == ["Mỹ Đình", "Việt Trì", "Sapa"]
    assert [d["gio_den"] for d in di["diem"]] == [gio(10, 8), gio(10, 9, 40), gio(10, 14)]
    assert [d["ten"] for d in ve["diem"]] == ["Sapa", "Việt Trì", "Mỹ Đình"]
    assert [d["gio_den"] for d in ve["diem"]] == [gio(10, 15), gio(10, 19, 20), gio(10, 21)]
    assert kq["loai_xe_cam_ket"]["so_ghe"] == 2 and kq["loai_xe_cam_ket"]["so_tang"] == 2


def test_lo_trinh_ngoai_pham_vi_bi_chan(monkeypatch, phan_cong):
    _gia_lap_chu_trinh(monkeypatch)
    phan_cong["nd-1"] = [TUYEN_KHAC]
    with pytest.raises(CamTruyCap):
        dd.chi_tiet_chu_trinh(ddv(), "ct-1")


def test_chi_tiet_loai_xe(monkeypatch):
    monkeypatch.setattr(dd.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": "l", "ma": "LX1", "ten": "T", "so_do_ghe": [{"ma_ghe": "A1", "tang": 1, "x": 0, "y": 0}]})
    assert dd.chi_tiet_loai_xe("l")["so_do_ghe"][0]["ma_ghe"] == "A1"
    monkeypatch.setattr(dd.xe_repo, "tim_loai_xe_theo_id", lambda _id: None)
    with pytest.raises(KhongTimThay):
        dd.chi_tiet_loai_xe("l")


def test_danh_sach_xe_chu_trinh_khong_ton_tai(monkeypatch):
    monkeypatch.setattr(dd.repo, "lay_chu_trinh", lambda _id: [])
    with pytest.raises(KhongTimThay):
        dd.danh_sach_xe_cho_chu_trinh(quan_ly(), "ct-x")


def test_danh_sach_xe_chu_trinh_da_khoi_hanh_het_bi_chan(monkeypatch):
    _gia_lap_chu_trinh(monkeypatch, [chuyen("di", trang_thai="dang_chay"), chuyen("ve", "nguoc", trang_thai="da_huy")])
    with pytest.raises(GiaTriLoi, match="đã khởi hành"):
        dd.danh_sach_xe_cho_chu_trinh(quan_ly(), "ct-1")


# ---------------------------------------------------------------- gan_xe
def _gia_lap_gan(monkeypatch, chuyen_list=None, xe_dang_gan=None, lich_cua_xe=None, bay_gio=None):
    """Thay repo.gan_xe_cho_chu_trinh: gọi đúng callback kiem_tra như repo thật, rồi coi như đã ghi."""
    monkeypatch.setattr(dd, "_bay_gio", lambda: bay_gio or datetime.datetime(2030, 1, 9, tzinfo=datetime.timezone.utc))
    da_goi = {}

    def gan(chu_trinh_id, xe_id, kiem_tra):
        chuyen_list_ = chu_trinh_mau() if chuyen_list is None else chuyen_list
        kiem_tra(chuyen_list_, xe_dang_gan, lambda *a: lich_cua_xe or lich())
        da_goi["gan"] = (chu_trinh_id, xe_id)
        return [{**c, "xe_id": xe_id, "bien_so_xe": "29B-1"} for c in chuyen_list_]

    monkeypatch.setattr(dd.repo, "gan_xe_cho_chu_trinh", gan)
    return da_goi


def test_gan_xe_thanh_cong_ca_hai_chuyen_cung_xe(monkeypatch):
    da_goi = _gia_lap_gan(monkeypatch, xe_dang_gan=xe())
    ket_qua = dd.gan_xe(ddv(), "ct-1", "xe-1")
    assert da_goi["gan"] == ("ct-1", "xe-1")
    assert ket_qua["trang_thai_gan"] == "da_gan" and {c["xe_id"] for c in ket_qua["cac_chuyen"]} == {"xe-1"}


def test_gan_xe_vi_pham_quy_tac_bao_moi_ly_do_va_khong_ghi(monkeypatch):
    da_goi = _gia_lap_gan(monkeypatch, xe_dang_gan=xe(loai_xe_id="loai-2", trang_thai="bao_tri"))
    with pytest.raises(GiaTriLoi, match=r"Không gán được xe 29B-1: .*hoạt động.*loại xe"):
        dd.gan_xe(ddv(), "ct-1", "xe-1")
    assert "gan" not in da_goi


def test_gan_xe_chu_trinh_tuyen_khong_duoc_phan_cong_bi_chan(monkeypatch, phan_cong):
    da_goi = _gia_lap_gan(monkeypatch, xe_dang_gan=xe())
    phan_cong["nd-1"] = [TUYEN_KHAC]
    with pytest.raises(CamTruyCap, match="chưa được phân công"):
        dd.gan_xe(ddv(), "ct-1", "xe-1")
    assert "gan" not in da_goi


def test_gan_xe_chua_duoc_phan_cong_tuyen_nao_bi_chan(monkeypatch, phan_cong):
    da_goi = _gia_lap_gan(monkeypatch, xe_dang_gan=xe())
    phan_cong["nd-1"] = []
    with pytest.raises(CamTruyCap):
        dd.gan_xe(ddv(), "ct-1", "xe-1")
    assert "gan" not in da_goi


def test_gan_xe_quan_ly_gan_duoc_cho_moi_tuyen(monkeypatch):
    _gia_lap_gan(monkeypatch, xe_dang_gan=xe())
    assert dd.gan_xe(quan_ly(), "ct-1", "xe-1")["trang_thai_gan"] == "da_gan"


def test_gan_xe_khong_ton_tai_hoac_chu_trinh_khong_ton_tai(monkeypatch):
    _gia_lap_gan(monkeypatch, xe_dang_gan=None)
    with pytest.raises(KhongTimThay, match="xe"):
        dd.gan_xe(quan_ly(), "ct-1", "xe-x")
    _gia_lap_gan(monkeypatch, chuyen_list=[], xe_dang_gan=xe())
    with pytest.raises(KhongTimThay, match="chu trình"):
        dd.gan_xe(quan_ly(), "ct-x", "xe-1")


def test_gan_xe_chuyen_da_qua_gio_bi_chan(monkeypatch):
    _gia_lap_gan(monkeypatch, xe_dang_gan=xe(), bay_gio=datetime.datetime(2030, 1, 10, 2, 0, tzinfo=datetime.timezone.utc))  # 09:00 VN, sau 08:00
    with pytest.raises(GiaTriLoi, match="đã quá giờ khởi hành"):
        dd.gan_xe(quan_ly(), "ct-1", "xe-1")


def test_gan_xe_chuyen_dang_co_xe_chay_thay_khong_doi_xe_goc(monkeypatch):
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-9", xe_thuc_te_id="xe-8"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-9")]
    _gia_lap_gan(monkeypatch, chuyen_list=chuyen_list, xe_dang_gan=xe())
    with pytest.raises(GiaTriLoi, match="xe chạy thay"):
        dd.gan_xe(quan_ly(), "ct-1", "xe-1")


def test_gan_xe_chi_xet_chuyen_chua_khoi_hanh_cua_chu_trinh(monkeypatch):
    # chuyến đi đã chạy (xe gốc đang đi), chuyến về còn chưa khởi hành → chỉ chuyến về được gán và được kiểm tra
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), trang_thai="dang_chay", xe_id="xe-1"), chuyen("ve", "nguoc", gio(10, 15))]
    truoc = chuyen("truoc", "xuoi", gio(10, 8), xe_id="xe-1")  # đi A→B kết thúc 14:00 → xe ở B, khớp điểm xuất phát chuyến về
    _gia_lap_gan(monkeypatch, chuyen_list=chuyen_list, xe_dang_gan=xe(), lich_cua_xe=lich(truoc=truoc))
    assert dd.gan_xe(quan_ly(), "ct-1", "xe-1")["trang_thai_gan"] == "da_gan"


def test_gan_xe_chuyen_dang_hoan_qua_gio_van_gan_duoc_va_tra_ve_chu_trinh(monkeypatch):
    # chuyến đang hoãn: quá giờ khởi hành mà chưa có xe → vẫn gán được (repo tắt cờ đang hoãn khi ghi)
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), dang_hoan=True), chuyen("ve", "nguoc", gio(10, 15), dang_hoan=True)]
    _gia_lap_gan(monkeypatch, chuyen_list=chuyen_list, xe_dang_gan=xe(), bay_gio=datetime.datetime(2030, 1, 10, 3, 0, tzinfo=datetime.timezone.utc))
    assert dd.gan_xe(quan_ly(), "ct-1", "xe-1")["trang_thai_gan"] == "da_gan"


# ---------------------------------------------------------------- Cần chú ý (can_chu_y_chu_trinh)
BAY_GIO = datetime.datetime(2030, 1, 9, 17, 0, tzinfo=datetime.timezone.utc)  # 00:00 ngày 10 giờ VN → chuyến đi 08:00 còn 8 giờ


def _ma(ds):
    return [v["ma"] for v in ds]


def test_can_chu_y_chu_trinh_da_gan_xe_binh_thuong_khong_co_gi():
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-1")]
    assert dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO) == []


def test_can_chu_y_chua_gan_xe_con_xa_hon_48_gio_khong_nhac():
    xa = BAY_GIO + datetime.timedelta(hours=50)
    assert dd.can_chu_y_chu_trinh([chuyen("di", "xuoi", xa)], BAY_GIO) == []


def test_can_chu_y_chua_gan_xe_trong_48_gio_canh_bao_va_duoi_6_gio_khan():
    canh_bao = dd.can_chu_y_chu_trinh([chuyen("di", "xuoi", BAY_GIO + datetime.timedelta(hours=20))], BAY_GIO)
    assert [(v["ma"], v["muc_do"]) for v in canh_bao] == [("chua_gan_sap_toi", "canh_bao")]
    assert canh_bao[0]["gio_khoi_hanh"] == BAY_GIO + datetime.timedelta(hours=20) and canh_bao[0]["ma_chuyen"] == "MA-di"  # giao diện tính "còn 20 giờ" từ đây
    khan = dd.can_chu_y_chu_trinh([chuyen("di", "xuoi", BAY_GIO + datetime.timedelta(hours=5, minutes=30))], BAY_GIO)
    assert [(v["ma"], v["muc_do"]) for v in khan] == [("chua_gan_sap_toi", "khan")]
    assert khan[0]["gio_khoi_hanh"] == BAY_GIO + datetime.timedelta(hours=5, minutes=30)


def test_con_lai_dang_chu_tu_1_ngay_tro_len_tinh_theo_ngay():
    h = lambda gio, phut=0: datetime.timedelta(hours=gio, minutes=phut)  # noqa: E731
    assert dd.con_lai_dang_chu(h(37, 51)) == "1 ngày 13 giờ"
    assert dd.con_lai_dang_chu(h(48)) == "2 ngày"
    assert dd.con_lai_dang_chu(h(24, 20)) == "1 ngày"  # phút lẻ bỏ qua khi đã tính theo ngày
    assert dd.con_lai_dang_chu(h(17, 21)) == "17 giờ 21 phút"
    assert dd.con_lai_dang_chu(h(6)) == "6 giờ"
    assert dd.con_lai_dang_chu(h(0, 45)) == "45 phút"
    assert dd.con_lai_dang_chu(h(-1)) == "0 phút"


def test_duong_dan_chu_trinh():
    assert dd.duong_dan_chu_trinh("abc") == "/nhan-vien/dieu-do/gan-xe.html?chu_trinh=abc"
    assert dd.duong_dan_chu_trinh(None) == "/nhan-vien/dieu-do/gan-xe.html"


def test_can_chu_y_chua_gan_xe_ca_hai_chuyen_chi_nhac_mot_lan_cho_chu_trinh():
    chuyen_list = [chuyen("di", "xuoi", BAY_GIO + datetime.timedelta(hours=3)), chuyen("ve", "nguoc", BAY_GIO + datetime.timedelta(hours=9))]
    ds = dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO)
    assert _ma(ds) == ["chua_gan_sap_toi"] and "MA-di" in ds[0]["noi_dung"]  # nêu chuyến sớm nhất


def test_can_chu_y_chuyen_dang_hoan_la_muc_khan():
    chuyen_list = [chuyen("di", "xuoi", BAY_GIO - datetime.timedelta(hours=1), dang_hoan=True)]
    ds = dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO)
    assert [(v["ma"], v["muc_do"]) for v in ds] == [("dang_hoan", "khan")]
    assert ds[0]["gio_khoi_hanh"] == BAY_GIO - datetime.timedelta(hours=1)  # đã quá giờ: giao diện ghi "đã quá 1 giờ"


def test_can_chu_y_xe_gan_dang_bao_tri_can_thay_xe():
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", trang_thai_xe="bao_tri")]
    ds = dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO)
    assert [(v["ma"], v["muc_do"]) for v in ds] == [("xe_hong", "khan")] and "29B-1" in ds[0]["noi_dung"]


def test_can_chu_y_xe_chay_thay_van_hoat_dong_thi_xe_goc_hong_khong_bao_nua():
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", trang_thai_xe="bao_tri", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2", trang_thai_xe_thuc_te="hoat_dong")]
    assert dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO) == []


def test_can_chu_y_xe_chay_thay_cung_hong_bao_khan_con_xe_goc_song_lai_bao_thong_tin():
    hong = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", trang_thai_xe="bao_tri", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2", trang_thai_xe_thuc_te="bao_tri")]
    assert [(v["ma"], v["muc_do"]) for v in dd.can_chu_y_chu_trinh(hong, BAY_GIO)] == [("xe_hong", "khan")]
    song_lai = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2", trang_thai_xe_thuc_te="hoat_dong")]
    assert [(v["ma"], v["muc_do"]) for v in dd.can_chu_y_chu_trinh(song_lai, BAY_GIO)] == [("xe_goc_san_sang", "thong_tin")]


def test_can_chu_y_canh_bao_vi_tri_va_sap_nang_truoc():
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", co_canh_bao_xung_dot_vi_tri=True, trang_thai_xe="bao_tri")]
    assert _ma(dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO)) == ["xe_hong", "canh_bao_vi_tri"]  # khẩn trước cảnh báo


def test_can_chu_y_bo_qua_chuyen_da_khoi_hanh():
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), trang_thai="dang_chay", xe_id="xe-1", trang_thai_xe="bao_tri"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-1")]
    assert dd.can_chu_y_chu_trinh(chuyen_list, BAY_GIO) == []


def test_danh_sach_chu_trinh_kem_can_chu_y(monkeypatch):
    monkeypatch.setattr(dd, "_bay_gio", lambda: BAY_GIO)
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, tuyen_ids: chu_trinh_mau())
    kq = dd.danh_sach_chu_trinh(ddv())
    assert _ma(kq[0]["can_chu_y"]) == ["chua_gan_sap_toi"]


# ---------------------------------------------------------------- danh sách xe chế độ "thay"
def test_danh_sach_xe_che_do_thay_bo_xe_goc_va_danh_dau_xe_dang_chay_thay(monkeypatch):
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", xe_thuc_te_id="xe-2"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-1", xe_thuc_te_id="xe-2")]
    _gia_lap_chu_trinh(monkeypatch, chuyen_list)
    monkeypatch.setattr(dd.repo, "danh_sach_xe_de_chon", lambda: [xe(id="xe-1", bien_so="29B-1"), xe(id="xe-2", bien_so="29B-2"), xe(id="xe-3", bien_so="29B-3")])
    monkeypatch.setattr(dd.repo, "lich_cac_xe", lambda ids, *a: {i: lich() for i in ids})
    kq = dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1", "thay")
    assert sorted(x["bien_so"] for x in kq) == ["29B-2", "29B-3"]  # xe gốc xe-1 không nằm trong danh sách chọn xe thay
    assert {x["bien_so"]: x["dang_gan"] for x in kq} == {"29B-2": True, "29B-3": False}


def test_danh_sach_xe_che_do_thay_chu_trinh_chua_co_xe_goc_bao_loi(monkeypatch):
    _gia_lap_chu_trinh(monkeypatch)
    with pytest.raises(GiaTriLoi, match="chưa có xe gốc"):
        dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1", "thay")


def test_danh_sach_xe_che_do_khong_hop_le(monkeypatch):
    with pytest.raises(GiaTriLoi, match="Chế độ"):
        dd.danh_sach_xe_cho_chu_trinh(ddv(), "ct-1", "abc")


# ---------------------------------------------------------------- thay_xe / tra_xe_goc (UC-20)
def _chu_trinh_co_xe_goc():
    return [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-9"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-9")]


def _gia_lap_thay(monkeypatch, chuyen_list=None, xe_thay=None, lich_cua_xe=None, bay_gio=None):
    monkeypatch.setattr(dd, "_bay_gio", lambda: bay_gio or datetime.datetime(2030, 1, 9, tzinfo=datetime.timezone.utc))
    da_goi = {"bao": []}
    monkeypatch.setattr(dd.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda chuyen_id: [{"khach_hang_id": f"kh-{chuyen_id}"}])
    monkeypatch.setattr(dd.thong_bao, "gui", lambda nguoi_id, noi_dung, **kw: da_goi["bao"].append((nguoi_id, noi_dung)))

    def thay_repo(chu_trinh_id, xe_id, kiem_tra):
        ds = _chu_trinh_co_xe_goc() if chuyen_list is None else chuyen_list
        kiem_tra(ds, xe_thay, lambda *a: lich_cua_xe or lich())
        da_goi["thay"] = (chu_trinh_id, xe_id)
        return [{**c, "xe_thuc_te_id": xe_id, "bien_so_xe_thuc_te": "29B-1"} for c in ds]

    monkeypatch.setattr(dd.repo, "thay_xe_cho_chu_trinh", thay_repo)
    return da_goi


def test_thay_xe_thanh_cong_bao_khach_va_ghi_xe_chay_thay(monkeypatch):
    da_goi = _gia_lap_thay(monkeypatch, xe_thay=xe(id="xe-1"))
    kq = dd.thay_xe(ddv(), "ct-1", "xe-1", " xe gốc hỏng máy ")
    assert da_goi["thay"] == ("ct-1", "xe-1")
    assert {c["xe_thuc_te_id"] for c in kq["cac_chuyen"]} == {"xe-1"}
    assert sorted(n[0] for n in da_goi["bao"]) == ["kh-di", "kh-ve"]
    assert all("29B-1" in n[1] and "Lý do: xe gốc hỏng máy" in n[1] for n in da_goi["bao"])


def test_thay_xe_chinh_xe_goc_bi_chan(monkeypatch):
    da_goi = _gia_lap_thay(monkeypatch, xe_thay=xe(id="xe-9"))
    with pytest.raises(GiaTriLoi, match="xe gốc"):
        dd.thay_xe(ddv(), "ct-1", "xe-9")
    assert da_goi["bao"] == []


def test_thay_xe_chu_trinh_chua_co_xe_goc_bi_chan(monkeypatch):
    _gia_lap_thay(monkeypatch, chuyen_list=chu_trinh_mau(), xe_thay=xe(id="xe-1"))
    with pytest.raises(GiaTriLoi, match="chưa có xe gốc"):
        dd.thay_xe(ddv(), "ct-1", "xe-1")


def test_thay_xe_vi_pham_quy_tac_khong_ghi_khong_bao_khach(monkeypatch):
    da_goi = _gia_lap_thay(monkeypatch, xe_thay=xe(id="xe-1", loai_xe_id="loai-2", trang_thai="bao_tri"))
    with pytest.raises(GiaTriLoi, match=r"Không cho xe 29B-1 chạy thay được: .*hoạt động.*loại xe"):
        dd.thay_xe(ddv(), "ct-1", "xe-1")
    assert "thay" not in da_goi and da_goi["bao"] == []


def test_thay_xe_ngoai_pham_vi_bi_chan(monkeypatch, phan_cong):
    da_goi = _gia_lap_thay(monkeypatch, xe_thay=xe(id="xe-1"))
    phan_cong["nd-1"] = [TUYEN_KHAC]
    with pytest.raises(CamTruyCap):
        dd.thay_xe(ddv(), "ct-1", "xe-1")
    assert "thay" not in da_goi


def test_thay_xe_chuyen_da_qua_gio_bi_chan(monkeypatch):
    _gia_lap_thay(monkeypatch, xe_thay=xe(id="xe-1"), bay_gio=datetime.datetime(2030, 1, 10, 2, 0, tzinfo=datetime.timezone.utc))
    with pytest.raises(GiaTriLoi, match="đã quá giờ khởi hành"):
        dd.thay_xe(quan_ly(), "ct-1", "xe-1")


def test_thay_xe_chi_xet_chuyen_con_chua_khoi_hanh(monkeypatch):
    # chuyến đi đã chạy bằng xe gốc, chỉ chuyến về còn lại → xe thay phải đang ở B (đã tới B sau chuyến trước) mới khớp
    chuyen_list = [chuyen("di", "xuoi", gio(10, 8), trang_thai="dang_chay", xe_id="xe-9"), chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-9")]
    truoc = chuyen("truoc", "xuoi", gio(10, 8), xe_id="xe-1")
    da_goi = _gia_lap_thay(monkeypatch, chuyen_list=chuyen_list, xe_thay=xe(id="xe-1"), lich_cua_xe=lich(truoc=truoc))
    dd.thay_xe(ddv(), "ct-1", "xe-1")
    assert da_goi["thay"] == ("ct-1", "xe-1") and [n[0] for n in da_goi["bao"]] == ["kh-ve"]  # chỉ khách chuyến về được báo


def _gia_lap_tra(monkeypatch, chuyen_list, xe_goc, lich_cua_xe=None):
    monkeypatch.setattr(dd, "_bay_gio", lambda: datetime.datetime(2030, 1, 9, tzinfo=datetime.timezone.utc))
    monkeypatch.setattr(dd.repo, "lay_chu_trinh", lambda _id: chuyen_list)
    monkeypatch.setattr(dd.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda chuyen_id: [{"khach_hang_id": f"kh-{chuyen_id}"}])
    bao = []
    monkeypatch.setattr(dd.thong_bao, "gui", lambda nguoi_id, noi_dung, **kw: bao.append((nguoi_id, noi_dung)))

    def tra_repo(chu_trinh_id, kiem_tra):
        kiem_tra(chuyen_list, xe_goc, lambda *a: lich_cua_xe or lich())
        return [{**c, "xe_thuc_te_id": None, "bien_so_xe_thuc_te": None} for c in chuyen_list]

    monkeypatch.setattr(dd.repo, "tra_xe_goc_cho_chu_trinh", tra_repo)
    return bao


def _chu_trinh_dang_chay_thay():
    return [chuyen("di", "xuoi", gio(10, 8), xe_id="xe-9", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2"),
            chuyen("ve", "nguoc", gio(10, 15), xe_id="xe-9", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2")]


def test_tra_xe_goc_thanh_cong_bao_khach(monkeypatch):
    bao = _gia_lap_tra(monkeypatch, _chu_trinh_dang_chay_thay(), xe(id="xe-9", bien_so="29B-1"))
    kq = dd.tra_xe_goc(ddv(), "ct-1")
    assert {c["xe_thuc_te_id"] for c in kq["cac_chuyen"]} == {None}
    assert sorted(n[0] for n in bao) == ["kh-di", "kh-ve"] and all("29B-1" in n[1] for n in bao)


def test_tra_xe_goc_chu_trinh_khong_co_xe_chay_thay_bi_chan(monkeypatch):
    _gia_lap_tra(monkeypatch, _chu_trinh_co_xe_goc(), xe(id="xe-9"))
    with pytest.raises(GiaTriLoi, match="không có xe nào đang chạy thay"):
        dd.tra_xe_goc(ddv(), "ct-1")


def test_tra_xe_goc_khi_xe_goc_chua_hoat_dong_lai_bi_chan(monkeypatch):
    bao = _gia_lap_tra(monkeypatch, _chu_trinh_dang_chay_thay(), xe(id="xe-9", bien_so="29B-1", trang_thai="bao_tri"))
    with pytest.raises(GiaTriLoi, match=r"Chưa trả về xe gốc 29B-1 được: .*hoạt động"):
        dd.tra_xe_goc(ddv(), "ct-1")
    assert bao == []


# ---------------------------------------------------------------- sự cố + người nhận
def test_danh_sach_su_co_theo_pham_vi_tuyen(monkeypatch):
    da_hoi = []
    sc = chuyen("di", "xuoi", gio(10, 8), xe_id="xe-1", trang_thai="gap_su_co", loai_su_co="loi_nha_xe", ly_do_su_co="nổ lốp")

    def gia_lap(tuyen_ids):
        da_hoi.append(tuyen_ids)
        return [sc]

    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_gap_su_co", gia_lap)
    kq = dd.danh_sach_su_co(ddv())
    assert da_hoi == [["tuyen-1"]] and kq[0]["ly_do_su_co"] == "nổ lốp" and kq[0]["bien_so_xe"] == "29B-1"
    dd.danh_sach_su_co(quan_ly())
    assert da_hoi[1] is None  # quản lý thấy mọi tuyến


def test_nguoi_nhan_thong_bao_cua_tuyen_roi_xuong_dan(monkeypatch):
    monkeypatch.setattr(dd.phan_cong_repo, "danh_sach_id_dieu_do_vien_cua_tuyen", lambda t: ["a"])
    assert dd.nguoi_nhan_thong_bao_cua_tuyen("t") == ["a"]
    monkeypatch.setattr(dd.phan_cong_repo, "danh_sach_id_dieu_do_vien_cua_tuyen", lambda t: [])
    monkeypatch.setattr(dd.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vai_tro, chi_dang_hoat_dong=False: ["ddv"] if vai_tro == "dieu_do_vien" else ["ql"])
    assert dd.nguoi_nhan_thong_bao_cua_tuyen("t") == ["ddv"]
    monkeypatch.setattr(dd.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vai_tro, chi_dang_hoat_dong=False: [] if vai_tro == "dieu_do_vien" else ["ql"])
    assert dd.nguoi_nhan_thong_bao_cua_tuyen("t") == ["ql"]


# ---------------------------------------------------------------- thống kê tổng quan
def _gia_lap_thong_ke(monkeypatch, cac_nhom_chuyen, tuyen=None):
    monkeypatch.setattr(dd, "_bay_gio", lambda: BAY_GIO)
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_trong_cua_so", lambda tu, den, tuyen_ids: [c for nhom in cac_nhom_chuyen for c in nhom])
    monkeypatch.setattr(dd.repo, "danh_sach_chuyen_gap_su_co", lambda tuyen_ids: [chuyen("sc", "xuoi", gio(10, 8), trang_thai="gap_su_co")])
    da_hoi = {}
    monkeypatch.setattr(dd.repo, "thong_ke_doi_xe", lambda tu, den: {"hoat_dong": 10, "bao_tri": 2, "du_phong": 3, "co_dinh_tuyen": 7, "ranh": 4})
    monkeypatch.setattr(dd.repo, "dem_chuyen_theo_trang_thai", lambda tu, den, tuyen_ids: da_hoi.update(khoang=(tu, den), tuyen_ids=tuyen_ids) or {"hoan_thanh": 30, "da_huy": 1})
    monkeypatch.setattr(dd.phan_cong_repo, "danh_sach_tuyen_cua_dieu_do_vien", lambda nd: tuyen if tuyen is not None else [TUYEN_1, TUYEN_KHAC])
    monkeypatch.setattr(dd.dia_diem_repo, "danh_sach_tuyen", lambda: [TUYEN_1, TUYEN_KHAC])  # quản lý thấy mọi tuyến
    return da_hoi


def _nhom(chu_trinh_id, gio_di, **ghi_de):
    return [chuyen(f"{chu_trinh_id}-d", "xuoi", gio_di, chu_trinh_id=chu_trinh_id, **ghi_de), chuyen(f"{chu_trinh_id}-v", "nguoc", gio_di + datetime.timedelta(hours=7), chu_trinh_id=chu_trinh_id, **ghi_de)]


def test_thong_ke_tong_quan_dem_chu_trinh_theo_tinh_trang_va_theo_tuyen_theo_ngay(monkeypatch):
    sap = BAY_GIO + datetime.timedelta(hours=10)  # 10:00 VN ngày 10
    nhom = [
        _nhom("c-gan", sap, xe_id="xe-1"),
        _nhom("c-chua", sap + datetime.timedelta(days=1)),
        _nhom("c-hoan", BAY_GIO - datetime.timedelta(hours=1), dang_hoan=True),
        _nhom("c-thay", sap + datetime.timedelta(days=1), xe_id="xe-1", xe_thuc_te_id="xe-2", bien_so_xe_thuc_te="29B-2", trang_thai_xe_thuc_te="hoat_dong"),
    ]
    da_hoi = _gia_lap_thong_ke(monkeypatch, nhom)
    kq = dd.thong_ke_tong_quan(quan_ly(), 3)
    t = kq["tong"]
    assert (t["so_chu_trinh"], t["so_chuyen"], t["da_gan"], t["chua_gan"], t["dang_hoan"]) == (4, 8, 2, 1, 1)
    assert t["dang_chay_thay"] == 1 and t["su_co_dang_xay_ra"] == 1
    assert t["viec_khan"] == 1 and t["viec_can_chu_y"] >= 1  # chỉ chu trình đang hoãn có việc khẩn (chu trình chưa gán còn >6 giờ thì chỉ cảnh báo)
    # mỗi chu trình chỉ vào MỘT nhóm: tổng 3 nhóm = tổng chu trình
    assert t["da_gan"] + t["chua_gan"] + t["dang_hoan"] == t["so_chu_trinh"]
    # theo tuyến: cả tuyến chưa có chu trình nào cũng có mặt (số 0), tuyến nhiều việc chưa xong lên trước
    assert [x["ma_tuyen"] for x in kq["theo_tuyen"]] == ["T001", "T009"] and kq["theo_tuyen"][1]["so_chu_trinh"] == 0
    # theo ngày sắp tăng dần, đếm đúng
    assert [(x["ngay"].day, x["so_chu_trinh"]) for x in kq["theo_ngay"]][-1][1] >= 1 and kq["theo_ngay"] == sorted(kq["theo_ngay"], key=lambda x: x["ngay"])
    assert kq["doi_xe"] == {"hoat_dong": 10, "bao_tri": 2, "du_phong": 3, "co_dinh_tuyen": 7, "ranh": 4, "dang_chay_thay": 1}
    assert kq["chuyen_gan_day"] == {"so_ngay": 7, "hoan_thanh": 30, "dang_chay": 0, "gap_su_co": 0, "da_huy": 1}
    assert da_hoi["khoang"] == (BAY_GIO - datetime.timedelta(days=7), BAY_GIO)  # 7 ngày vừa qua, đến bây giờ


def test_thong_ke_tong_quan_dieu_do_vien_chi_tinh_tuyen_duoc_phan_cong(monkeypatch):
    da_hoi = _gia_lap_thong_ke(monkeypatch, [_nhom("c-1", BAY_GIO + datetime.timedelta(hours=10), xe_id="xe-1")], tuyen=[TUYEN_1])
    kq = dd.thong_ke_tong_quan(ddv(), 3)
    assert [x["ma_tuyen"] for x in kq["theo_tuyen"]] == ["T001"] and da_hoi["tuyen_ids"] == ["tuyen-1"]


def test_thong_ke_tong_quan_khong_co_chu_trinh_nao_tra_so_0(monkeypatch):
    _gia_lap_thong_ke(monkeypatch, [])
    kq = dd.thong_ke_tong_quan(quan_ly(), 3)
    assert kq["tong"]["so_chu_trinh"] == 0 and kq["theo_ngay"] == [] and kq["tong"]["viec_khan"] == 0
