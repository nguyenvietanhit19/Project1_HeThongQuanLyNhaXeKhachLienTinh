from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.repositories import chot_ca_repository
from app.schemas.don_hang_schema import ChotCaRequest
from app.services import chot_ca_service
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

REPO = "app.repositories.chot_ca_repository"
TONG = {"so_don_tra_truoc": 1, "tien_tra_truoc": 50000, "so_don_cod": 1, "tien_cod": 120000,
        "so_don_hoan": 1, "tien_hoan": 30000}
BAY_GIO = lambda: datetime.now(timezone.utc)  # noqa: E731


def test_xem_truoc_tinh_phai_co_tu_lan_chot_truoc():
    moc = BAY_GIO() - timedelta(hours=5)
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=moc), \
         patch(f"{REPO}.tinh_tong", return_value=TONG) as mock_tong, \
         patch(f"{REPO}.lay_khoan", return_value=[{"loai": "hoan"}]):
        res = chot_ca_service.xem_truoc("nv")
    assert res["tien_phai_co"] == 140000 and res["tu_luc"] == moc and res["khoan"] == [{"loai": "hoan"}]
    nv, tu, den = mock_tong.call_args.args
    assert nv == "nv" and tu == moc and den == res["den_luc"]


def test_xem_truoc_lan_dau_khong_co_moc():
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=None), \
         patch(f"{REPO}.tinh_tong", return_value={**TONG, "tien_tra_truoc": 0, "tien_cod": 0, "tien_hoan": 0}), \
         patch(f"{REPO}.lay_khoan", return_value=[]):
        res = chot_ca_service.xem_truoc("nv")
    assert res["tu_luc"] is None and res["tien_phai_co"] == 0


def test_chot_ca_khop_tien_khong_can_ghi_chu():
    den = BAY_GIO() - timedelta(minutes=1)
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=None), \
         patch(f"{REPO}.tinh_tong", return_value=TONG), \
         patch(f"{REPO}.tao_chot_ca", return_value={"id": "x"}) as mock_tao:
        chot_ca_service.chot_ca("nv", "vp", den, 140000, None)
    mock_tao.assert_called_once_with("nv", "vp", den, 140000, None)


def test_chot_ca_lech_tien_bat_buoc_ghi_chu():
    den = BAY_GIO() - timedelta(minutes=1)
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=None), \
         patch(f"{REPO}.tinh_tong", return_value=TONG), \
         patch(f"{REPO}.tao_chot_ca") as mock_tao:
        with pytest.raises(GiaTriLoi, match="ghi chú"):
            chot_ca_service.chot_ca("nv", "vp", den, 130000, None)
        mock_tao.assert_not_called()
        chot_ca_service.chot_ca("nv", "vp", den, 130000, "trả nhầm tiền thừa")
        mock_tao.assert_called_once()


@pytest.mark.parametrize("lech", [timedelta(minutes=5), -timedelta(hours=3)])
def test_chot_ca_chan_moc_tuong_lai_va_moc_qua_cu(lech):
    with patch(f"{REPO}.tao_chot_ca") as mock_tao:
        with pytest.raises(GiaTriLoi):
            chot_ca_service.chot_ca("nv", "vp", BAY_GIO() + lech, 0, None)
        mock_tao.assert_not_called()


def test_chot_ca_chan_moc_khong_mui_gio():
    with pytest.raises(GiaTriLoi, match="múi giờ"):
        chot_ca_service.chot_ca("nv", "vp", datetime.now(), 0, None)


def test_chot_ca_chan_khi_da_chot_toi_moc_nay():
    den = BAY_GIO() - timedelta(minutes=10)
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=den), patch(f"{REPO}.tao_chot_ca") as mock_tao:
        with pytest.raises(GiaTriLoi, match="đã được chốt"):
            chot_ca_service.chot_ca("nv", "vp", den, 0, None)
        mock_tao.assert_not_called()


def test_chot_ca_bam_2_lan_cung_luc():
    den = BAY_GIO() - timedelta(minutes=1)
    with patch(f"{REPO}.lay_moc_chot_cuoi", return_value=None), \
         patch(f"{REPO}.tinh_tong", return_value=TONG), \
         patch(f"{REPO}.tao_chot_ca", side_effect=chot_ca_repository.DaChotSauMocNay()):
        with pytest.raises(GiaTriLoi, match="vừa được chốt"):
            chot_ca_service.chot_ca("nv", "vp", den, 140000, None)


def test_lich_su_nhan_vien_chi_thay_ca_cua_minh_quan_ly_thay_het():
    with patch(f"{REPO}.lay_lich_su", return_value=([], 0)) as mock_ls:
        chot_ca_service.lay_lich_su("nv", False, None, None, None, False, 20, 0)
        chot_ca_service.lay_lich_su("ql", True, "vp", None, None, True, 20, 0)
    assert mock_ls.call_args_list[0].args[0] == "nv"
    assert mock_ls.call_args_list[1].args[:2] == (None, "vp") and mock_ls.call_args_list[1].args[4] is True


def test_lich_su_chan_khoang_ngay_sai():
    with pytest.raises(GiaTriLoi):
        chot_ca_service.lay_lich_su("nv", False, None, date(2026, 10, 9), date(2026, 10, 1), False, 20, 0)


def test_chi_tiet_nhan_vien_khac_bi_chan_quan_ly_xem_duoc():
    ca = {"id": str(uuid4()), "nhan_vien_id": "nv-a", "tu_luc": None, "den_luc": BAY_GIO()}
    with patch(f"{REPO}.tim_theo_id", return_value=ca), patch(f"{REPO}.lay_khoan", return_value=[]):
        with pytest.raises(CamTruyCap):
            chot_ca_service.lay_chi_tiet(ca["id"], "nv-b", False)
        assert chot_ca_service.lay_chi_tiet(ca["id"], "nv-a", False)["khoan"] == []
        assert chot_ca_service.lay_chi_tiet(ca["id"], "ql", True)["id"] == ca["id"]
    with patch(f"{REPO}.tim_theo_id", return_value=None):
        with pytest.raises(KhongTimThay):
            chot_ca_service.lay_chi_tiet(str(uuid4()), "nv", False)


def test_schema_chot_ca():
    den = BAY_GIO().isoformat()
    assert ChotCaRequest(den_luc=den, tien_thuc_dem=0, ghi_chu="  ").ghi_chu is None
    for sai in [{"tien_thuc_dem": -1}, {"ghi_chu": "x" * 501}, {"tien_thuc_dem": "abc"}]:
        with pytest.raises(ValidationError):
            ChotCaRequest(**{"den_luc": den, "tien_thuc_dem": 0, **sai})
