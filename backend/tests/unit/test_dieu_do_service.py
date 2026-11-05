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
        "xe_id": xe_id, "bien_so_xe": "29B-1" if xe_id else None, "xe_thuc_te_id": None, "tong_phut": tong_phut,
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
