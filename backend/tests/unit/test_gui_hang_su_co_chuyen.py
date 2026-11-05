"""Hàng gửi khi chuyến chở nó gặp sự cố / chạy lại / bị hủy giữa đường — phần A
(HANG_KHI_CHUYEN_HUY_GIUA_DUONG.md mục 2.1, KE_HOACH_SUA_GUI_HANG.md mục 9).
Giả lập repository bằng monkeypatch, không cần DB thật."""

import pytest

from app.services import chuyen_xe_service
from app.services import gui_hang_service as svc
from app.utils.loi import GiaTriLoi


def _don(id_, ma, diem_gui="vp-gui", diem_nhan="vp-nhan", **them):
    d = {"id": id_, "ma_van_don": ma, "diem_gui_id": diem_gui, "diem_nhan_id": diem_nhan, "ma_chuyen": "CX-01"}
    d.update(them)
    return d


@pytest.fixture
def da_gui(monkeypatch):
    """Ghi lại mọi thông báo (người nhận, nội dung, đơn) thay vì ghi DB / đẩy WebSocket."""
    ds: list[tuple] = []
    monkeypatch.setattr(svc, "_gui_thong_bao", lambda nid, nd, did=None: ds.append((nid, nd, did)))
    nhan_vien = {"vp-gui": ["nv-gui-1", "nv-gui-2"], "vp-nhan": ["nv-nhan-1"], "vp-nhan-2": ["nv-nhan-2"]}
    monkeypatch.setattr(svc.don_hang_repo, "danh_sach_nhan_vien_gui_hang_tai_diem", lambda vp: nhan_vien.get(vp, []))
    monkeypatch.setattr(svc.nguoi_dung_repo, "danh_sach_id_theo_vai_tro",
                        lambda vai_tro, chi_dang_hoat_dong=False: ["ql-1"] if vai_tro == "quan_ly" else [])
    return ds


def _dat_don_tren_chuyen(monkeypatch, ds):
    monkeypatch.setattr(svc.don_hang_repo, "tim_don_dang_tren_chuyen", lambda cid: ds)


def _gui_toi(da_gui, nguoi):
    return [nd for nid, nd, _ in da_gui if nid == nguoi]


# ---------------------------------------------------------------------
# Báo văn phòng gửi + văn phòng nhận khi chuyến chở hàng gặp sự cố
# ---------------------------------------------------------------------

def test_gap_su_co_bao_van_phong_nhan_hang_se_toi_tre(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "thủng lốp")

    tin = _gui_toi(da_gui, "nv-nhan-1")
    assert len(tin) == 1
    assert "DH-1" in tin[0] and "trễ" in tin[0] and "thủng lốp" in tin[0]


def test_gap_su_co_bao_ca_nhan_vien_van_phong_gui(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "thủng lốp")

    assert len(_gui_toi(da_gui, "nv-gui-1")) == 1
    assert len(_gui_toi(da_gui, "nv-gui-2")) == 1
    assert "người gửi" in _gui_toi(da_gui, "nv-gui-1")[0]


def test_moi_van_phong_chi_nhan_1_tin_gom_cac_don_cua_minh(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [
        _don("d1", "DH-1", diem_nhan="vp-nhan"),
        _don("d2", "DH-2", diem_nhan="vp-nhan-2"),
        _don("d3", "DH-3", diem_nhan="vp-nhan"),
    ])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "hỏng máy")

    tin_nhan_1 = _gui_toi(da_gui, "nv-nhan-1")
    assert len(tin_nhan_1) == 1 and "DH-1" in tin_nhan_1[0] and "DH-3" in tin_nhan_1[0] and "DH-2" not in tin_nhan_1[0]
    tin_nhan_2 = _gui_toi(da_gui, "nv-nhan-2")
    assert len(tin_nhan_2) == 1 and "DH-2" in tin_nhan_2[0] and "DH-1" not in tin_nhan_2[0]
    tin_gui = _gui_toi(da_gui, "nv-gui-1")
    assert len(tin_gui) == 1 and all(ma in tin_gui[0] for ma in ("DH-1", "DH-2", "DH-3"))


def test_tin_1_don_gan_don_hang_id_de_bam_mo_chi_tiet(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "x")

    assert {did for _, _, did in da_gui} == {"d1"}


def test_tin_nhieu_don_khong_gan_don_hang_id(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1"), _don("d2", "DH-2")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "x")

    assert {did for _, _, did in da_gui} == {None}


def test_qua_5_don_chi_liet_ke_5_ma_va_dem_phan_con_lai(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don(f"d{i}", f"DH-{i}") for i in range(1, 8)])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "x")

    tin = _gui_toi(da_gui, "nv-nhan-1")[0]
    assert "DH-5" in tin and "DH-6" not in tin and "và 2 đơn khác" in tin and "7 đơn" in tin


def test_chuyen_khong_cho_hang_thi_khong_bao_ai(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "x")

    assert da_gui == []


def test_chay_lai_bao_hang_tiep_tuc_duoc_cho(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "chay_lai")

    tin = _gui_toi(da_gui, "nv-nhan-1")
    assert len(tin) == 1 and "chạy tiếp" in tin[0] and "DH-1" in tin[0]
    assert _gui_toi(da_gui, "ql-1") == []


def test_da_huy_bao_ca_quan_ly_de_xu_ly_hang_ket(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1"), _don("d2", "DH-2", diem_nhan="vp-nhan-2")])

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "da_huy", "sạt lở")

    assert "hủy" in _gui_toi(da_gui, "nv-nhan-1")[0]
    tin_ql = _gui_toi(da_gui, "ql-1")
    assert len(tin_ql) == 1 and "DH-1" in tin_ql[0] and "DH-2" in tin_ql[0]


def test_su_kien_khong_hop_le_bi_tu_choi(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])
    with pytest.raises(ValueError):
        svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "linh_tinh")


def test_loi_gui_1_thong_bao_khong_chan_cac_van_phong_khac(monkeypatch, da_gui):
    _dat_don_tren_chuyen(monkeypatch, [_don("d1", "DH-1")])
    con_lai: list[str] = []

    def gui(nid, nd, did=None):
        if nid == "nv-nhan-1":
            raise RuntimeError("mất kết nối")
        con_lai.append(nid)

    monkeypatch.setattr(svc, "_gui_thong_bao", gui)

    svc.bao_van_phong_khi_chuyen_co_bien_dong("chuyen-1", "gap_su_co", "x")

    assert con_lai == ["nv-gui-1", "nv-gui-2"]


# ---------------------------------------------------------------------
# Phụ xe báo sự cố (UC-17) → gọi sang gửi hàng
# ---------------------------------------------------------------------

@pytest.fixture
def bao_su_co_san_sang(monkeypatch):
    monkeypatch.setattr(chuyen_xe_service, "lay_chuyen_cua_phu_xe",
                        lambda cid, nid: {"id": cid, "xe_id": "xe-1", "trang_thai": "dang_chay", "tuyen_id": "t-1", "chieu": "xuoi"})
    monkeypatch.setattr(chuyen_xe_service.chuyen_xe_repo, "cap_nhat_gap_su_co", lambda cid, loai, ly_do: True)
    monkeypatch.setattr(chuyen_xe_service.chuyen_xe_repo, "gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai", lambda xe, cid: None)
    monkeypatch.setattr(chuyen_xe_service.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda cid: [])
    monkeypatch.setattr(chuyen_xe_service, "_bao_dieu_do_vien_su_co", lambda chuyen, loai, ly_do: None)


def test_bao_su_co_bao_van_phong_gui_hang(monkeypatch, bao_su_co_san_sang):
    goi: list[tuple] = []
    monkeypatch.setattr(svc, "bao_van_phong_khi_chuyen_co_bien_dong", lambda *a: goi.append(a))

    chuyen_xe_service.bao_su_co("chuyen-1", "loi_nha_xe", "  thủng lốp ", "phu-xe-1")

    assert goi == [("chuyen-1", "gap_su_co", "thủng lốp")]


def test_bao_su_co_van_thanh_cong_khi_bao_van_phong_gui_hang_loi(monkeypatch, bao_su_co_san_sang):
    def loi(*a):
        raise RuntimeError("DB lỗi")

    monkeypatch.setattr(svc, "bao_van_phong_khi_chuyen_co_bien_dong", loi)

    chuyen_xe_service.bao_su_co("chuyen-1", "loi_nha_xe", "thủng lốp", "phu-xe-1")  # không ném lỗi


# ---------------------------------------------------------------------
# Văn phòng nhận ghi cuộc gọi báo trễ cho đơn còn trên xe
# ---------------------------------------------------------------------

@pytest.fixture
def ghi(monkeypatch):
    lan_ghi: list[dict] = []

    def ghi_lien_he(don_hang_id, nhan_vien_id, doi_tuong, ket_qua, ghi_chu, danh_dau_da_thong_bao,
                    thong_bao_cho, noi_dung_thong_bao, cho_phep_dang_tren_xe=False):
        lan_ghi.append({"doi_tuong": doi_tuong, "ket_qua": ket_qua, "ghi_chu": ghi_chu,
                        "danh_dau": danh_dau_da_thong_bao, "tren_xe": cho_phep_dang_tren_xe})

    monkeypatch.setattr(svc.don_hang_repo, "ghi_lien_he", ghi_lien_he)
    return lan_ghi


def _don_tren_xe(monkeypatch, **chuyen):
    don = {"id": "d1", "ma_van_don": "DH-1", "diem_gui_id": "vp-gui", "diem_nhan_id": "vp-nhan", "trang_thai": "da_len_xe",
           "trang_thai_chuyen": "dang_chay", "chuyen_dang_hoan": False}
    don.update(chuyen)
    monkeypatch.setattr(svc.don_hang_repo, "tim_theo_id", lambda did: don)
    return don


def test_ghi_bao_tre_cho_don_tren_chuyen_gap_su_co(monkeypatch, ghi):
    _don_tren_xe(monkeypatch, trang_thai_chuyen="gap_su_co")

    svc.ghi_ket_qua_lien_he("d1", "nv-1", "vp-nhan", "nguoi_nhan", "da_lien_he", "hẹn mai lấy")

    assert len(ghi) == 1
    assert ghi[0]["tren_xe"] is True
    assert ghi[0]["danh_dau"] is False  # hàng chưa tới: chưa phải "đã báo được người nhận"
    assert ghi[0]["ghi_chu"].startswith("Báo hàng tới trễ") and "hẹn mai lấy" in ghi[0]["ghi_chu"]


@pytest.mark.parametrize("chuyen", [{"trang_thai_chuyen": "da_huy"}, {"chuyen_dang_hoan": True}])
def test_ghi_bao_tre_cho_chuyen_da_huy_hoac_dang_hoan(monkeypatch, ghi, chuyen):
    _don_tren_xe(monkeypatch, **chuyen)

    svc.ghi_ket_qua_lien_he("d1", "nv-1", "vp-nhan", "nguoi_gui", "khong_lien_he_duoc")

    assert len(ghi) == 1 and ghi[0]["ghi_chu"].startswith("Báo hàng tới trễ")


def test_khong_ghi_lien_he_don_tren_chuyen_binh_thuong(monkeypatch, ghi):
    _don_tren_xe(monkeypatch)

    with pytest.raises(GiaTriLoi):
        svc.ghi_ket_qua_lien_he("d1", "nv-1", "vp-nhan", "nguoi_nhan", "da_lien_he")
    assert ghi == []


def test_khong_bao_quan_ly_cho_don_con_tren_xe(monkeypatch, ghi):
    _don_tren_xe(monkeypatch, trang_thai_chuyen="gap_su_co")

    with pytest.raises(GiaTriLoi):
        svc.ghi_ket_qua_lien_he("d1", "nv-1", "vp-nhan", "quan_ly", "da_bao_quan_ly")


def test_ghi_lien_he_don_cho_lay_khong_doi(monkeypatch, ghi):
    don = _don_tren_xe(monkeypatch)
    don["trang_thai"] = "cho_lay"

    svc.ghi_ket_qua_lien_he("d1", "nv-1", "vp-nhan", "nguoi_nhan", "da_lien_he", "ok")

    assert ghi == [{"doi_tuong": "nguoi_nhan", "ket_qua": "da_lien_he", "ghi_chu": "ok", "danh_dau": True, "tren_xe": False}]


# ---------------------------------------------------------------------
# Văn phòng gửi lọc đơn đang trên chuyến có vấn đề
# ---------------------------------------------------------------------

def test_danh_sach_don_loc_chuyen_co_van_de(monkeypatch):
    nhan: dict = {}
    monkeypatch.setattr(svc.don_hang_repo, "lay_danh_sach_don", lambda **kw: (nhan.update(kw), ([], 0))[1])

    svc.lay_danh_sach_don("vp-gui", huong="gui", van_de_chuyen=True)

    assert nhan["van_de_chuyen"] is True
