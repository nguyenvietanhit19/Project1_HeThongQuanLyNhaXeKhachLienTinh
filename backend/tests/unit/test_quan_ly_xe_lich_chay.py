"""Unit test cho UC-34 (xe), UC-35 (biên chế cố định), UC-18 (lịch chạy) —
giả lập Repository bằng monkeypatch, không cần DB thật."""

import datetime

import pytest

from app.services import bien_che_service as bc
from app.services import lich_chay_service as lc
from app.services import xe_service as xs
from app.utils.loi import GiaTriLoi


# ---------------------------------------------------------
# UC-34 Xe
# ---------------------------------------------------------
def _xe(**ghi_de):
    du_lieu = {"id": "xe-1", "bien_so": "29B-1", "loai_xe_id": "loai-1", "trang_thai": "hoat_dong"}
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap_tham_chieu_hop_le(monkeypatch, loai_diem="van_phong"):
    monkeypatch.setattr(xs.repo, "tim_loai_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(xs.dia_diem_repo, "tim_diem_don_tra_theo_id", lambda _id: {"id": _id, "loai": loai_diem})
    monkeypatch.setattr(xs.dia_diem_repo, "tim_tuyen_theo_id", lambda _id: {"id": _id})


def test_tao_xe_diem_goc_khong_phai_van_phong_bi_chan(monkeypatch):
    _gia_lap_tham_chieu_hop_le(monkeypatch, loai_diem="diem_dung")
    with pytest.raises(GiaTriLoi, match="văn phòng"):
        xs.tao_xe("29B-1", "loai-1", "diem-1", None, "hoat_dong")


def test_tao_xe_chuan_hoa_bien_so(monkeypatch):
    _gia_lap_tham_chieu_hop_le(monkeypatch)
    da_luu = {}
    monkeypatch.setattr(xs.repo, "tao_xe", lambda bien_so, *_: da_luu.setdefault("bien_so", bien_so) and "xe-1")
    monkeypatch.setattr(xs.repo, "tim_xe_theo_id", lambda _id: _xe())
    xs.tao_xe("  29b-1 ", "loai-1", "diem-1", None, "hoat_dong")
    assert da_luu["bien_so"] == "29B-1"


def test_sua_xe_doi_loai_khi_dang_gan_chuyen_chua_xong_bi_chan(monkeypatch):
    _gia_lap_tham_chieu_hop_le(monkeypatch)
    monkeypatch.setattr(xs.repo, "tim_xe_theo_id", lambda _id: _xe(loai_xe_id="loai-1"))
    monkeypatch.setattr(xs.repo, "dem_chuyen_chua_xong_cua_xe", lambda _id: 2)
    with pytest.raises(GiaTriLoi, match="đổi loại xe"):
        xs.sua_xe("xe-1", "29B-1", "loai-2", "diem-1", None, "hoat_dong")


def test_sua_xe_bao_tri_ve_hoat_dong_co_chuyen_chay_thay_thi_bao_dieu_do_vien(monkeypatch):
    _gia_lap_tham_chieu_hop_le(monkeypatch)
    monkeypatch.setattr(xs.repo, "tim_xe_theo_id", lambda _id: _xe(trang_thai="bao_tri"))
    monkeypatch.setattr(xs.repo, "sua_xe", lambda *a: None)
    monkeypatch.setattr(xs.repo, "dem_chuyen_dang_chay_thay", lambda _id: 3)
    monkeypatch.setattr(xs.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vt: ["ddv-1", "ddv-2"])
    da_bao = []
    monkeypatch.setattr(xs.thong_bao_repo, "tao", lambda nguoi_id, nd: da_bao.append(nguoi_id))
    monkeypatch.setattr(xs, "broadcast_sync", lambda *_: None)

    xs.sua_xe("xe-1", "29B-1", "loai-1", "diem-1", None, "hoat_dong")
    assert da_bao == ["ddv-1", "ddv-2"]


def test_sua_xe_khong_bao_neu_khong_co_chuyen_chay_thay(monkeypatch):
    _gia_lap_tham_chieu_hop_le(monkeypatch)
    monkeypatch.setattr(xs.repo, "tim_xe_theo_id", lambda _id: _xe(trang_thai="bao_tri"))
    monkeypatch.setattr(xs.repo, "sua_xe", lambda *a: None)
    monkeypatch.setattr(xs.repo, "dem_chuyen_dang_chay_thay", lambda _id: 0)
    da_bao = []
    monkeypatch.setattr(xs.thong_bao_repo, "tao", lambda *a: da_bao.append(a))
    xs.sua_xe("xe-1", "29B-1", "loai-1", "diem-1", None, "hoat_dong")
    assert da_bao == []


# ---------------------------------------------------------
# UC-35 Biên chế cố định
# ---------------------------------------------------------
def _nhan_su(**ghi_de):
    du_lieu = {"id": "ns-1", "chuc_danh": "tai_xe", "nguoi_dung_id": None, "trang_thai": "dang_lam"}
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap_bien_che(monkeypatch, nhan_su, da_co=None, so_tai_xe=0):
    monkeypatch.setattr(bc.xe_repo, "tim_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(bc.nhan_su_repo, "tim_theo_id", lambda _id: nhan_su)
    monkeypatch.setattr(bc.nhan_su_repo, "tim_bien_che_co_dinh_cua_nhan_su", lambda _id: da_co)
    monkeypatch.setattr(bc.nhan_su_repo, "dem_co_dinh_theo_chuc_danh", lambda *_: so_tai_xe)
    monkeypatch.setattr(bc.nhan_su_repo, "them_bien_che_co_dinh", lambda *_: "moi")
    monkeypatch.setattr(bc.nhan_su_repo, "danh_sach_bien_che_theo_xe", lambda _id: [])


def test_them_bien_che_tai_xe_thu_3_bi_chan(monkeypatch):
    _gia_lap_bien_che(monkeypatch, _nhan_su(), so_tai_xe=2)
    with pytest.raises(GiaTriLoi, match="đủ 2 tài xế"):
        bc.them_bien_che_co_dinh("xe-1", "ns-1")


def test_them_bien_che_tai_xe_thu_2_duoc(monkeypatch):
    _gia_lap_bien_che(monkeypatch, _nhan_su(), so_tai_xe=1)
    assert bc.them_bien_che_co_dinh("xe-1", "ns-1") == []


def test_them_bien_che_phu_xe_khong_co_tai_khoan_bi_chan(monkeypatch):
    _gia_lap_bien_che(monkeypatch, _nhan_su(chuc_danh="phu_xe", nguoi_dung_id=None))
    with pytest.raises(GiaTriLoi, match="tài khoản"):
        bc.them_bien_che_co_dinh("xe-1", "ns-1")


def test_them_bien_che_nhan_su_da_nghi_viec_bi_chan(monkeypatch):
    _gia_lap_bien_che(monkeypatch, _nhan_su(trang_thai="da_nghi_viec"))
    with pytest.raises(GiaTriLoi, match="nghỉ việc"):
        bc.them_bien_che_co_dinh("xe-1", "ns-1")


def test_them_bien_che_nhan_su_dang_thuoc_xe_khac_bi_chan(monkeypatch):
    _gia_lap_bien_che(monkeypatch, _nhan_su(), da_co={"id": "dong-1", "xe_id": "xe-khac", "bien_so": "30A-9"})
    with pytest.raises(GiaTriLoi, match="30A-9"):
        bc.them_bien_che_co_dinh("xe-1", "ns-1")


def test_go_bien_che_tam_thoi_bi_chan(monkeypatch):
    monkeypatch.setattr(bc.nhan_su_repo, "tim_bien_che_theo_id", lambda _id: {"id": _id, "xe_id": "xe-1", "loai": "tam_thoi"})
    with pytest.raises(GiaTriLoi, match="điều độ viên"):
        bc.go_bien_che_co_dinh("dong-1")
# ---------------------------------------------------------
# UC-18 Lịch chạy định kỳ theo cặp (chiều đi + chiều về)
# ---------------------------------------------------------
def gio(h, m=0):
    return datetime.time(h, m)


TONG_PHUT = 360  # tuyến chạy 6 giờ


def test_tinh_ngay_lech_cung_ngay_khi_ve_sau_khi_toi_noi_du_30_phut():
    # đi 06:00, tới 12:00, về 13:00 → cùng ngày
    assert lc.tinh_ngay_lech(gio(6), gio(13), TONG_PHUT) == 0


def test_tinh_ngay_lech_dung_30_phut_nghi_van_hop_le():
    # đi 06:00, tới 12:00, về đúng 12:30
    assert lc.tinh_ngay_lech(gio(6), gio(12, 30), TONG_PHUT) == 0


def test_tinh_ngay_lech_thieu_30_phut_day_sang_ngay_sau():
    # đi 06:00, tới 12:00, về 12:29 chưa đủ nghỉ → chiều về chạy ngày hôm sau
    assert lc.tinh_ngay_lech(gio(6), gio(12, 29), TONG_PHUT) == 1


def test_tinh_ngay_lech_xe_toi_sang_hom_sau_ve_sang_som():
    # đi 23:00, tới 05:00 hôm sau, về 07:00 → lệch 1 ngày
    assert lc.tinh_ngay_lech(gio(23), gio(7), TONG_PHUT) == 1


def test_tinh_ngay_lech_hanh_trinh_dai_hon_mot_ngay():
    # tuyến 30 giờ: đi 08:00 tới 14:00 hôm sau, về 20:00 → lệch 1 ngày; về 13:00 → lệch 2 ngày
    assert lc.tinh_ngay_lech(gio(8), gio(20), 30 * 60) == 1
    assert lc.tinh_ngay_lech(gio(8), gio(13), 30 * 60) == 2


def _gia_lap_cap(monkeypatch, co_gia_ve=True, trung_chieu=None, tong_phut=TONG_PHUT):
    monkeypatch.setattr(lc.dia_diem_repo, "tim_tuyen_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.gia_ve_repo, "danh_sach_gia_ve", lambda _id: [{"id": "gv"}] if co_gia_ve else [])
    monkeypatch.setattr(lc.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.repo, "tim_trung", lambda t, chieu, *a, **k: {"id": "cu"} if chieu == trung_chieu else None)
    monkeypatch.setattr(lc.repo, "tong_phut_tuyen", lambda _id: tong_phut)
    da_tao = []

    def tao_cap(tuyen_id, xuoi, nguoc, ngay_lech):
        da_tao.append((tuyen_id, xuoi, nguoc, ngay_lech))
        return "cap-1"

    monkeypatch.setattr(lc.repo, "tao_cap", tao_cap)
    monkeypatch.setattr(lc.repo, "lich_cua_cap", lambda _id: _lich_cua_cap())
    return da_tao


def _lich_cua_cap(so_chuyen_xuoi=0, so_chuyen_nguoc=0, dang_ap_dung=True, ngay_lech=1):
    chung = {"cap_id": "cap-1", "tuyen_id": "tuyen-1", "ma_tuyen": "T001", "ten_tuyen": "Tuyến 1", "tong_phut": TONG_PHUT,
             "dang_ap_dung": dang_ap_dung, "loai_xe_id": "loai-1"}
    return [
        {**chung, "id": "lich-di", "chieu": "xuoi", "gio_khoi_hanh": gio(23), "ngay_lech": 0, "so_chuyen_da_sinh": so_chuyen_xuoi},
        {**chung, "id": "lich-ve", "chieu": "nguoc", "gio_khoi_hanh": gio(7), "ngay_lech": ngay_lech, "so_chuyen_da_sinh": so_chuyen_nguoc},
    ]


CHIEU_DI = {"gio_khoi_hanh": gio(23), "loai_xe_id": "loai-1"}
CHIEU_VE = {"gio_khoi_hanh": gio(7), "loai_xe_id": "loai-1"}


def test_tao_cap_tuyen_chua_co_gia_ve_bi_chan(monkeypatch):
    _gia_lap_cap(monkeypatch, co_gia_ve=False)
    with pytest.raises(GiaTriLoi, match="giá vé"):
        lc.tao_cap_lich_chay("tuyen-1", CHIEU_DI, CHIEU_VE)


def test_tao_cap_chieu_ve_trung_bi_chan(monkeypatch):
    da_tao = _gia_lap_cap(monkeypatch, trung_chieu="nguoc")
    with pytest.raises(GiaTriLoi, match="chiều về"):
        lc.tao_cap_lich_chay("tuyen-1", CHIEU_DI, CHIEU_VE)
    assert da_tao == []


def test_tao_cap_khac_loai_xe_bi_chan(monkeypatch):
    da_tao = _gia_lap_cap(monkeypatch)
    with pytest.raises(GiaTriLoi, match="cùng loại xe"):
        lc.tao_cap_lich_chay("tuyen-1", CHIEU_DI, {**CHIEU_VE, "loai_xe_id": "loai-2"})
    assert da_tao == []


def test_tao_cap_tuyen_chua_co_thoi_gian_chay_bi_chan(monkeypatch):
    _gia_lap_cap(monkeypatch, tong_phut=None)
    with pytest.raises(GiaTriLoi, match="thời gian chạy"):
        lc.tao_cap_lich_chay("tuyen-1", CHIEU_DI, CHIEU_VE)


def test_tao_cap_hop_le_luu_dung_ngay_lech_va_loai_xe_tung_chieu(monkeypatch):
    da_tao = _gia_lap_cap(monkeypatch)
    cap = lc.tao_cap_lich_chay("tuyen-1", CHIEU_DI, CHIEU_VE)
    assert da_tao == [("tuyen-1", CHIEU_DI, CHIEU_VE, 1)]  # đi 23:00 tới 05:00 → về 07:00 hôm sau
    assert cap["xuoi"]["id"] == "lich-di" and cap["nguoc"]["id"] == "lich-ve"
    assert cap["gio_den_chieu_di"] == gio(5) and cap["ngay_den_lech"] == 1


def test_doi_ap_dung_ca_cap(monkeypatch):
    monkeypatch.setattr(lc.repo, "lich_cua_cap", lambda _id: _lich_cua_cap())
    da_goi = []
    monkeypatch.setattr(lc.repo, "doi_ap_dung_cap", lambda cap_id, gia_tri: da_goi.append((cap_id, gia_tri)))
    lc.doi_ap_dung_cap("cap-1", False)
    assert da_goi == [("cap-1", False)]


def test_doi_ap_dung_cap_khong_ton_tai(monkeypatch):
    monkeypatch.setattr(lc.repo, "lich_cua_cap", lambda _id: [])
    with pytest.raises(GiaTriLoi, match="Không tìm thấy"):
        lc.doi_ap_dung_cap("cap-x", False)


# ---------------------------------------------------------
# UC-18 Sinh chuyến cho các cặp (thủ công, không job nền)
# ---------------------------------------------------------
def _gia_lap_sinh(monkeypatch, lich=None, da_co=lambda lich_id, ngay: False):
    monkeypatch.setattr(lc.repo, "lich_cua_cap", lambda _id: lich if lich is not None else _lich_cua_cap())
    da_sinh = []

    def sinh(ke_hoach):
        for muc in ke_hoach:
            muc["da_sinh"] = not da_co(muc["lich"]["id"], muc["ngay"])
            if muc["da_sinh"]:
                da_sinh.append(muc)
        return ke_hoach

    monkeypatch.setattr(lc.chuyen_xe_repo, "sinh_nhieu_chuyen_tu_lich", sinh)
    return da_sinh


def _hom_nay():
    return datetime.datetime.now(lc.MUI_GIO_VN).date()


def _ngay_mai():
    return _hom_nay() + datetime.timedelta(days=1)


def _gia_lap_gio_hien_tai(monkeypatch, bay_gio):
    """Đóng băng đồng hồ của service (bay_gio là datetime có múi giờ VN)."""
    import types

    class DongHo(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return bay_gio

    monkeypatch.setattr(lc, "datetime", types.SimpleNamespace(
        datetime=DongHo, date=datetime.date, time=datetime.time, timedelta=datetime.timedelta))


def test_sinh_chuyen_chuyen_di_hom_nay_da_qua_gio_thi_bo_ca_chu_ky_khong_thua_chuyen_ve(monkeypatch):
    # Lịch: đi 23:00, về 07:00 (lệch 1 ngày). Bây giờ 12/10 lúc 23:30 → chuyến đi 12/10 đã quá giờ
    bay_gio = datetime.datetime(2026, 10, 12, 23, 30, tzinfo=lc.MUI_GIO_VN)
    _gia_lap_gio_hien_tai(monkeypatch, bay_gio)
    da_sinh = _gia_lap_sinh(monkeypatch)
    hom_nay = datetime.date(2026, 10, 12)
    kq = lc.sinh_chuyen_cho_cac_cap(["cap-1"], hom_nay, hom_nay + datetime.timedelta(days=2))
    assert kq["so_chu_ky_bo_qua_do_qua_gio"] == 1
    assert kq["so_chuyen_di_moi_sinh"] == 2 and kq["so_chuyen_ve_moi_sinh"] == 2
    ngay_di = sorted(m["ngay"] for m in da_sinh if m["lich"]["chieu"] == "xuoi")
    ngay_ve = sorted(m["ngay"] for m in da_sinh if m["lich"]["chieu"] == "nguoc")
    assert ngay_di == [datetime.date(2026, 10, 13), datetime.date(2026, 10, 14)]
    # chuyến về 13/10 (của chu kỳ đi 12/10 đã bỏ) không được sinh
    assert ngay_ve == [datetime.date(2026, 10, 14), datetime.date(2026, 10, 15)]


def test_sinh_chuyen_chuyen_di_hom_nay_con_gio_thi_van_sinh_ca_hai_chieu(monkeypatch):
    bay_gio = datetime.datetime(2026, 10, 12, 10, 0, tzinfo=lc.MUI_GIO_VN)
    _gia_lap_gio_hien_tai(monkeypatch, bay_gio)
    da_sinh = _gia_lap_sinh(monkeypatch)
    hom_nay = datetime.date(2026, 10, 12)
    kq = lc.sinh_chuyen_cho_cac_cap(["cap-1"], hom_nay, hom_nay)
    assert kq["so_chu_ky_bo_qua_do_qua_gio"] == 0
    assert (kq["so_chuyen_di_moi_sinh"], kq["so_chuyen_ve_moi_sinh"]) == (1, 1)


def test_sinh_chuyen_khong_chon_cap_nao_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch)
    with pytest.raises(GiaTriLoi, match="ít nhất 1 cặp"):
        lc.sinh_chuyen_cho_cac_cap([], _hom_nay(), _hom_nay())


def test_sinh_chuyen_cap_khong_ton_tai_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch, lich=[])
    with pytest.raises(GiaTriLoi, match="Không tìm thấy"):
        lc.sinh_chuyen_cho_cac_cap(["cap-x"], _hom_nay(), _hom_nay())


def test_sinh_chuyen_cap_da_ngung_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch, lich=_lich_cua_cap(dang_ap_dung=False))
    with pytest.raises(GiaTriLoi, match="ngừng áp dụng"):
        lc.sinh_chuyen_cho_cac_cap(["cap-1"], _hom_nay(), _hom_nay())


def test_sinh_chuyen_ngay_bat_dau_sau_ngay_ket_thuc_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch)
    with pytest.raises(GiaTriLoi, match="trước hoặc bằng"):
        lc.sinh_chuyen_cho_cac_cap(["cap-1"], _hom_nay() + datetime.timedelta(days=3), _hom_nay())


def test_sinh_chuyen_ngay_qua_khu_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch)
    qua_khu = _hom_nay() - datetime.timedelta(days=1)
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        lc.sinh_chuyen_cho_cac_cap(["cap-1"], qua_khu, _hom_nay())


def test_sinh_chuyen_khoang_qua_dai_bi_chan(monkeypatch):
    _gia_lap_sinh(monkeypatch)
    hom_nay = _hom_nay()
    with pytest.raises(GiaTriLoi, match="tối đa"):
        lc.sinh_chuyen_cho_cac_cap(["cap-1"], hom_nay, hom_nay + datetime.timedelta(days=lc.SO_NGAY_TOI_DA_MOI_LAN))


def test_sinh_chuyen_chieu_ve_lech_dung_so_ngay_cua_cap(monkeypatch):
    da_sinh = _gia_lap_sinh(monkeypatch)  # ngay_lech = 1
    hom_nay = _ngay_mai()
    kq = lc.sinh_chuyen_cho_cac_cap(["cap-1"], hom_nay, hom_nay + datetime.timedelta(days=2))
    assert kq == {"so_chuyen_di_moi_sinh": 3, "so_chuyen_ve_moi_sinh": 3, "so_chuyen_di_da_co_san": 0, "so_chuyen_ve_da_co_san": 0, "so_chu_ky_bo_qua_do_qua_gio": 0}
    ngay_di = sorted(m["ngay"] for m in da_sinh if m["lich"]["chieu"] == "xuoi")
    ngay_ve = sorted(m["ngay"] for m in da_sinh if m["lich"]["chieu"] == "nguoc")
    assert ngay_di == [hom_nay + datetime.timedelta(days=i) for i in range(3)]
    assert ngay_ve == [hom_nay + datetime.timedelta(days=i) for i in range(1, 4)]  # chuyến về cuối rơi sau ngày kết thúc


def test_sinh_chuyen_gan_mui_gio_viet_nam_cho_gio_khoi_hanh(monkeypatch):
    da_sinh = _gia_lap_sinh(monkeypatch)
    lc.sinh_chuyen_cho_cac_cap(["cap-1"], _ngay_mai(), _ngay_mai())
    assert all(m["gio_khoi_hanh"].tzinfo is not None for m in da_sinh)
    assert da_sinh[0]["gio_khoi_hanh"].utcoffset() == datetime.timedelta(hours=7)


def test_sinh_chuyen_dem_rieng_chuyen_da_co_san_tung_chieu(monkeypatch):
    # chiều đi đã có sẵn ở mọi ngày, chiều về chưa có
    _gia_lap_sinh(monkeypatch, da_co=lambda lich_id, ngay: lich_id == "lich-di")
    hom_nay = _ngay_mai()
    kq = lc.sinh_chuyen_cho_cac_cap(["cap-1"], hom_nay, hom_nay + datetime.timedelta(days=1))
    assert kq == {"so_chuyen_di_moi_sinh": 0, "so_chuyen_ve_moi_sinh": 2, "so_chuyen_di_da_co_san": 2, "so_chuyen_ve_da_co_san": 0, "so_chu_ky_bo_qua_do_qua_gio": 0}


def test_sinh_chuyen_cap_chon_trung_lap_chi_tinh_mot_lan(monkeypatch):
    _gia_lap_sinh(monkeypatch)
    kq = lc.sinh_chuyen_cho_cac_cap(["cap-1", "cap-1"], _ngay_mai(), _ngay_mai())
    assert kq["so_chuyen_di_moi_sinh"] == 1


# ---------------------------------------------------------
# UC-18 — sửa lịch của cặp đã sinh chuyến bị khóa
# ---------------------------------------------------------
def _gia_lap_sua_lich(monkeypatch, so_chuyen_xuoi=0, so_chuyen_nguoc=0):
    cap = _lich_cua_cap(so_chuyen_xuoi, so_chuyen_nguoc)
    da_ghi = []
    monkeypatch.setattr(lc.repo, "tim_theo_id", lambda _id: next(l for l in cap if l["id"] == _id))
    monkeypatch.setattr(lc.repo, "lich_cua_cap", lambda _id: cap)
    monkeypatch.setattr(lc.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.repo, "tim_trung", lambda *a, **k: None)
    monkeypatch.setattr(lc.repo, "tong_phut_tuyen", lambda _id: TONG_PHUT)
    monkeypatch.setattr(lc.repo, "sua", lambda *a: da_ghi.append(a))
    return da_ghi


def test_sua_lich_cua_cap_da_sinh_chuyen_bi_chan_ke_ca_khi_chi_chieu_kia_co_chuyen(monkeypatch):
    da_ghi = _gia_lap_sua_lich(monkeypatch, so_chuyen_xuoi=0, so_chuyen_nguoc=7)
    with pytest.raises(GiaTriLoi, match="đã sinh 7 chuyến"):
        lc.sua_lich_chay("lich-di", gio(22), "loai-1")
    assert da_ghi == []


def test_sua_lich_chua_sinh_chuyen_tinh_lai_ngay_lech_theo_gio_moi(monkeypatch):
    da_ghi = _gia_lap_sua_lich(monkeypatch)
    lc.sua_lich_chay("lich-ve", gio(13), "loai-1")  # đi 23:00 tới 05:00, về 13:00 → vẫn lệch 1 ngày
    lc.sua_lich_chay("lich-di", gio(0), "loai-1")  # đi 00:00 tới 06:00, về 07:00 → cùng ngày
    assert [a[4] for a in da_ghi] == [1, 0]


def test_sua_gio_lam_chieu_ve_truoc_gio_ket_thuc_chieu_di_bi_chan(monkeypatch):
    da_ghi = _gia_lap_sua_lich(monkeypatch)
    with pytest.raises(GiaTriLoi, match="cùng ngày"):
        lc.sua_lich_chay("lich-di", gio(6), "loai-1")  # đi 06:00 tới 12:00 mà về 07:00
    assert da_ghi == []


def test_kiem_tra_gio_cap_chieu_di_ket_thuc_trong_ngay_thi_chieu_ve_cung_ngay():
    with pytest.raises(GiaTriLoi, match="từ 12:30"):
        lc.kiem_tra_gio_cap(gio(6), gio(10), TONG_PHUT)  # đúng ca người dùng gặp: đi 06-12, về 10
    with pytest.raises(GiaTriLoi):
        lc.kiem_tra_gio_cap(gio(6), gio(12, 29), TONG_PHUT)
    lc.kiem_tra_gio_cap(gio(6), gio(12, 30), TONG_PHUT)  # đúng 30 phút: hợp lệ
    lc.kiem_tra_gio_cap(gio(6), gio(18), TONG_PHUT)


def test_kiem_tra_gio_cap_chieu_di_qua_nua_dem_khong_rang_buoc_gio_ve():
    lc.kiem_tra_gio_cap(gio(23), gio(7), TONG_PHUT)  # tới 05:00 hôm sau, về 07:00 sau 1 ngày


def test_tao_cap_chieu_ve_truoc_gio_ket_thuc_chieu_di_bi_chan(monkeypatch):
    da_tao = _gia_lap_cap(monkeypatch)
    with pytest.raises(GiaTriLoi, match="cùng ngày"):
        lc.tao_cap_lich_chay("tuyen-1", {**CHIEU_DI, "gio_khoi_hanh": gio(6)}, {**CHIEU_VE, "gio_khoi_hanh": gio(10)})
    assert da_tao == []
