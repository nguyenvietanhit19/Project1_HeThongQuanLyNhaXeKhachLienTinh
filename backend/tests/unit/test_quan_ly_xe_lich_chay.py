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
# UC-18 Lịch chạy định kỳ
# ---------------------------------------------------------
GIO = datetime.time(6, 30)


def _gia_lap_lich_chay(monkeypatch, co_gia_ve=True, trung=None):
    monkeypatch.setattr(lc.dia_diem_repo, "tim_tuyen_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.gia_ve_repo, "danh_sach_gia_ve", lambda _id: [{"id": "gv"}] if co_gia_ve else [])
    monkeypatch.setattr(lc.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.repo, "tim_trung", lambda *a, **k: trung)
    monkeypatch.setattr(lc.repo, "tao", lambda *a: "lich-1")
    monkeypatch.setattr(lc.repo, "tim_theo_id", lambda _id: {"id": _id})


def test_tao_lich_chay_tuyen_chua_co_gia_ve_bi_chan(monkeypatch):
    _gia_lap_lich_chay(monkeypatch, co_gia_ve=False)
    with pytest.raises(GiaTriLoi, match="giá vé"):
        lc.tao_lich_chay("tuyen-1", "xuoi", GIO, "loai-1")


def test_tao_lich_chay_trung_bi_chan(monkeypatch):
    _gia_lap_lich_chay(monkeypatch, trung={"id": "lich-cu"})
    with pytest.raises(GiaTriLoi, match="Đã có lịch chạy"):
        lc.tao_lich_chay("tuyen-1", "xuoi", GIO, "loai-1")


def test_tao_lich_chay_hop_le(monkeypatch):
    _gia_lap_lich_chay(monkeypatch)
    assert lc.tao_lich_chay("tuyen-1", "nguoc", GIO, "loai-1") == {"id": "lich-1"}


def test_doi_ap_dung_khong_dung_den_chuyen(monkeypatch):
    monkeypatch.setattr(lc.repo, "tim_theo_id", lambda _id: {"id": _id})
    da_goi = []
    monkeypatch.setattr(lc.repo, "doi_ap_dung", lambda lich_id, gia_tri: da_goi.append((lich_id, gia_tri)))
    lc.doi_ap_dung("lich-1", False)
    assert da_goi == [("lich-1", False)]


# ---------------------------------------------------------
# UC-18 Sinh chuyến theo khoảng ngày (thủ công, không job nền)
# ---------------------------------------------------------
HOM_NAY = lc.datetime.datetime.now(lc.MUI_GIO_VN).date()


def _lich(**ghi_de):
    du_lieu = {"id": "lich-1", "tuyen_id": "tuyen-1", "chieu": "xuoi", "gio_khoi_hanh": GIO, "loai_xe_id": "loai-1", "dang_ap_dung": True}
    du_lieu.update(ghi_de)
    return du_lieu


def _gia_lap_sinh_chuyen(monkeypatch, dang_ap_dung=True, da_co_theo_ngay=None):
    monkeypatch.setattr(
        lc.repo,
        "tim_theo_id",
        lambda _id: _lich(dang_ap_dung=dang_ap_dung, id=_id) if _id else None,
    )
    monkeypatch.setattr(lc.chuyen_xe_repo, "da_co_chuyen_theo_ngay", da_co_theo_ngay or (lambda *_: False))
    da_tao = []
    monkeypatch.setattr(lc.chuyen_xe_repo, "tao_chuyen_tu_lich_dinh_ky", lambda *a: da_tao.append(a) or "moi")
    return da_tao


def test_sinh_chuyen_lich_khong_ton_tai_bi_chan(monkeypatch):
    monkeypatch.setattr(lc.repo, "tim_theo_id", lambda _id: None)
    with pytest.raises(GiaTriLoi, match="Không tìm thấy lịch"):
        lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY)


def test_sinh_chuyen_lich_da_ngung_ap_dung_bi_chan(monkeypatch):
    _gia_lap_sinh_chuyen(monkeypatch, dang_ap_dung=False)
    with pytest.raises(GiaTriLoi, match="ngừng áp dụng"):
        lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY)


def test_sinh_chuyen_ngay_bat_dau_sau_ngay_ket_thuc_bi_chan(monkeypatch):
    _gia_lap_sinh_chuyen(monkeypatch)
    with pytest.raises(GiaTriLoi, match="trước hoặc bằng"):
        lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY + datetime.timedelta(days=2), HOM_NAY)


def test_sinh_chuyen_ngay_qua_khu_bi_chan(monkeypatch):
    _gia_lap_sinh_chuyen(monkeypatch)
    hom_qua = HOM_NAY - datetime.timedelta(days=1)
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        lc.sinh_chuyen_theo_khoang_ngay("lich-1", hom_qua, HOM_NAY)


def test_sinh_chuyen_khoang_qua_dai_bi_chan(monkeypatch):
    _gia_lap_sinh_chuyen(monkeypatch)
    with pytest.raises(GiaTriLoi, match="tối đa 180 ngày"):
        lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY + datetime.timedelta(days=200))


def test_sinh_chuyen_du_so_ngay_khi_chua_co_chuyen_nao(monkeypatch):
    da_tao = _gia_lap_sinh_chuyen(monkeypatch)
    ket_qua = lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY + datetime.timedelta(days=4))
    assert ket_qua == {"so_chuyen_moi_sinh": 5, "so_ngay_da_co_san": 0}
    assert len(da_tao) == 5
    for _, _, _, _, gio_khoi_hanh in da_tao:
        assert gio_khoi_hanh.tzinfo is not None
        assert str(gio_khoi_hanh.tzinfo) == "Asia/Ho_Chi_Minh"


def test_sinh_chuyen_bo_qua_ngay_da_co_san(monkeypatch):
    da_co_san = {HOM_NAY, HOM_NAY + datetime.timedelta(days=1)}
    da_tao = _gia_lap_sinh_chuyen(monkeypatch, da_co_theo_ngay=lambda lich_id, ngay: ngay in da_co_san)

    ket_qua = lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY + datetime.timedelta(days=3))

    assert ket_qua == {"so_chuyen_moi_sinh": 2, "so_ngay_da_co_san": 2}
    assert len(da_tao) == 2


def test_sinh_chuyen_dung_tuyen_chieu_loai_xe_theo_dung_lich(monkeypatch):
    monkeypatch.setattr(
        lc.repo,
        "tim_theo_id",
        lambda _id: _lich(chieu="nguoc", tuyen_id="tuyen-9", loai_xe_id="loai-9"),
    )
    monkeypatch.setattr(lc.chuyen_xe_repo, "da_co_chuyen_theo_ngay", lambda *_: False)
    da_tao = []
    monkeypatch.setattr(lc.chuyen_xe_repo, "tao_chuyen_tu_lich_dinh_ky", lambda *a: da_tao.append(a) or "x")

    lc.sinh_chuyen_theo_khoang_ngay("lich-1", HOM_NAY, HOM_NAY)

    tuyen_id, chieu, loai_xe_id, lich_id, _ = da_tao[0]
    assert (tuyen_id, chieu, loai_xe_id, lich_id) == ("tuyen-9", "nguoc", "loai-9", "lich-1")


# ---------------------------------------------------------
# UC-18 — sửa lịch đã sinh chuyến bị khóa
# ---------------------------------------------------------
def _gia_lap_sua_lich(monkeypatch, so_chuyen_da_sinh):
    lich = {"id": "lich-1", "tuyen_id": "tuyen-1", "so_chuyen_da_sinh": so_chuyen_da_sinh}
    da_ghi = []
    monkeypatch.setattr(lc.repo, "tim_theo_id", lambda _id: lich)
    monkeypatch.setattr(lc.xe_repo, "tim_loai_xe_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(lc.repo, "tim_trung", lambda *a, **k: False)
    monkeypatch.setattr(lc.repo, "sua", lambda *a: da_ghi.append(a))
    return da_ghi


def test_sua_lich_da_sinh_chuyen_bi_chan(monkeypatch):
    da_ghi = _gia_lap_sua_lich(monkeypatch, so_chuyen_da_sinh=7)
    with pytest.raises(GiaTriLoi, match="đã sinh 7 chuyến"):
        lc.sua_lich_chay("lich-1", "nguoc", GIO, "loai-1")
    assert da_ghi == []


def test_sua_lich_chua_sinh_chuyen_van_sua_duoc(monkeypatch):
    da_ghi = _gia_lap_sua_lich(monkeypatch, so_chuyen_da_sinh=0)
    lc.sua_lich_chay("lich-1", "nguoc", GIO, "loai-1")
    assert len(da_ghi) == 1
