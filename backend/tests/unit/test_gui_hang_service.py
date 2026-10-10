from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4
import pytest

from app.schemas.don_hang_schema import SuaThongTinLienHeRequest, TaoDonHangRequest
from app.services import gui_hang_service
from app.repositories import don_hang_repository
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongDuQuyen, KhongTimThay


@pytest.fixture
def du_lieu_tao_don_mau():
    return TaoDonHangRequest(
        tuyen_id=uuid4(),
        diem_gui_id=uuid4(),
        diem_nhan_id=uuid4(),
        loai_hang_id=uuid4(),
        can_nang_kg=Decimal("5.0"),
        dai_cm=Decimal("20"),
        rong_cm=Decimal("15"),
        cao_cm=Decimal("10"),
        gia_cuoc=120000,
        ten_nguoi_gui="Nguyen Van A",
        sdt_nguoi_gui="0912345678",
        ten_nguoi_nhan="Tran Thi B",
        sdt_nguoi_nhan="0987654321",
        phuong_thuc_thanh_toan="nguoi_gui_tra_truoc",
        xac_nhan_da_thu=True,
    )


# ---------------------------------------------------------------------
# Tạo đơn tại quầy (UC-23)
# ---------------------------------------------------------------------

def test_tao_don_hang_chan_hang_cam(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Pháo nổ", "la_hang_cam": True}
        with pytest.raises(GiaTriLoi, match="cấm vận chuyển"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))


def test_tao_don_hang_chan_diem_gui_trung_diem_nhan(du_lieu_tao_don_mau):
    cung_diem_id = du_lieu_tao_don_mau.diem_gui_id
    du_lieu_tao_don_mau.diem_nhan_id = cung_diem_id

    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.return_value = {"id": str(cung_diem_id), "ten": "VP Mỹ Đình", "loai": "van_phong"}

        with pytest.raises(GiaTriLoi, match="không được trùng"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))


def test_tao_don_hang_chan_diem_dung_doc_duong(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.return_value = {"id": str(du_lieu_tao_don_mau.diem_gui_id), "ten": "Trạm dừng nghỉ", "loai": "diem_dung"}

        with pytest.raises(GiaTriLoi, match="phải là văn phòng"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))


def test_tao_don_hang_chan_diem_khong_thuoc_tuyen(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_lh, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem, \
         patch("app.repositories.dia_diem_repository.tim_tuyen_theo_id") as mock_tuyen, \
         patch("app.repositories.don_hang_repository.kiem_tra_diem_thuoc_tuyen") as mock_chk:
        mock_lh.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.side_effect = lambda did: {"id": str(did), "ten": f"VP {did}", "loai": "van_phong"}
        mock_tuyen.return_value = {"id": str(du_lieu_tao_don_mau.tuyen_id), "ten": "Hà Nội - SaPa"}
        mock_chk.return_value = None  # Điểm không thuộc tuyến

        with pytest.raises(GiaTriLoi, match="không đi qua điểm gửi hoặc điểm nhận"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))


def test_tao_don_hang_tra_truoc_bat_buoc_xac_nhan_da_thu(du_lieu_tao_don_mau):
    du_lieu_tao_don_mau.xac_nhan_da_thu = False
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_lh, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem:
        mock_lh.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.side_effect = lambda did: {"id": str(did), "ten": f"VP {did}", "loai": "van_phong"}

        with pytest.raises(GiaTriLoi, match="xác nhận đã thu cước"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))


def test_lay_tuyen_phu_hop():
    diem_gui_id = str(uuid4())
    diem_nhan_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.tim_cac_tuyen_qua_hai_diem") as mock_repo:
        mock_repo.return_value = [
            {"id": str(uuid4()), "ten": "Hà Nội - SaPa", "chieu_van_chuyen": "xuoi"}
        ]
        res = gui_hang_service.lay_tuyen_phu_hop(diem_gui_id, diem_nhan_id)
        assert len(res) == 1
        assert res[0]["ten"] == "Hà Nội - SaPa"
        assert res[0]["chieu_van_chuyen"] == "xuoi"


# ---------------------------------------------------------------------
# Giao hàng cho người nhận (UC-24)
# ---------------------------------------------------------------------

def test_xac_nhan_giao_hang_thanh_cong():
    ma_van_don = "DH-20260920-TEST01"
    van_phong_id = str(uuid4())
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": ma_van_don,
        "diem_nhan_id": van_phong_id,
        "trang_thai": "cho_lay",
        "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc",
        "da_thu_tien": True,
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim, \
         patch("app.repositories.don_hang_repository.cap_nhat_giao_hang") as mock_cap_nhat:
        mock_tim.return_value = don_hang_mau
        mock_cap_nhat.return_value = {**don_hang_mau, "trang_thai": "da_giao"}

        ket_qua = gui_hang_service.xac_nhan_giao_hang(
            ma_van_don, nhan_vien_nhan_id=str(uuid4()), van_phong_id=van_phong_id
        )
        assert ket_qua["trang_thai"] == "da_giao"


def test_xac_nhan_giao_hang_cod_bat_buoc_xac_nhan_da_thu():
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": "DH-20260920-COD01",
        "diem_nhan_id": str(uuid4()),
        "trang_thai": "cho_lay",
        "phuong_thuc_thanh_toan": "cod_nguoi_nhan_tra",
        "da_thu_tien": False,
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim:
        mock_tim.return_value = don_hang_mau
        with pytest.raises(GiaTriLoi, match="COD"):
            gui_hang_service.xac_nhan_giao_hang(don_hang_mau["ma_van_don"], nhan_vien_nhan_id=str(uuid4()))


def test_xac_nhan_giao_hang_chan_van_phong_nhan_khac():
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": "DH-20260920-VP01",
        "diem_nhan_id": str(uuid4()),
        "trang_thai": "cho_lay",
        "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc",
        "da_thu_tien": True,
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim:
        mock_tim.return_value = don_hang_mau
        with pytest.raises(CamTruyCap):
            gui_hang_service.xac_nhan_giao_hang(
                don_hang_mau["ma_van_don"], nhan_vien_nhan_id=str(uuid4()), van_phong_id=str(uuid4())
            )


def test_xac_nhan_giao_hang_chan_khi_chua_toi_noi():
    ma_van_don = "DH-20260920-TEST02"
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": ma_van_don,
        "trang_thai": "da_len_xe",
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim:
        mock_tim.return_value = don_hang_mau
        with pytest.raises(GiaTriLoi, match="chưa tới điểm nhận"):
            gui_hang_service.xac_nhan_giao_hang(ma_van_don, nhan_vien_nhan_id=str(uuid4()))


# ---------------------------------------------------------------------
# Phụ xe chất / dỡ hàng (UC-26, UC-27, UC-28)
# lay_chuyen_cua_phu_xe & diem_hien_tai được import vào gui_hang_service
# nên patch theo đường dẫn của gui_hang_service.
# ---------------------------------------------------------------------

def _chuyen(tuyen_id, trang_thai="chua_khoi_hanh"):
    return {"id": str(uuid4()), "tuyen_id": tuyen_id, "trang_thai": trang_thai}


def _don_cho_chat(tuyen_id, diem_gui_id):
    return {
        "id": str(uuid4()),
        "tuyen_id": tuyen_id,
        "diem_gui_id": diem_gui_id,
        "diem_nhan_id": str(uuid4()),
        "trang_thai": "cho_van_chuyen",
        "chuyen_id": None,
    }


def _don_tren_xe(chuyen_id, diem_nhan_id):
    return {
        "id": str(uuid4()), "ma_van_don": "DH-TREN-XE", "trang_thai": "da_len_xe", "chuyen_id": chuyen_id,
        "diem_nhan_id": diem_nhan_id, "ten_nguoi_nhan": "Nam", "sdt_nguoi_nhan": "0987654321",
    }


def test_xac_nhan_chat_hang_thanh_cong():
    tuyen_id, diem_gui = str(uuid4()), str(uuid4())
    chuyen = _chuyen(tuyen_id)
    don = _don_cho_chat(tuyen_id, diem_gui)

    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen) as mock_quyen, \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_gui}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.kiem_tra_diem_thuoc_tuyen", return_value={"chieu_van_chuyen": "xuoi"}), \
         patch("app.repositories.don_hang_repository.tim_chuyen_xe_theo_id", return_value={**chuyen, "chieu": "xuoi"}), \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen") as mock_chat:
        mock_chat.return_value = {**don, "trang_thai": "da_len_xe", "chuyen_id": chuyen["id"]}

        ket_qua = gui_hang_service.xac_nhan_chat_hang(don["id"], chuyen["id"], "phu-xe-1")

        assert ket_qua["trang_thai"] == "da_len_xe"
        mock_quyen.assert_called_once_with(chuyen["id"], "phu-xe-1")
        mock_chat.assert_called_once_with(don["id"], chuyen["id"], "phu-xe-1")


def test_xac_nhan_chat_hang_chan_phu_xe_khong_thuoc_chuyen():
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe",
               side_effect=KhongDuQuyen("Chuyến này không thuộc về bạn")), \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen") as mock_chat:
        with pytest.raises(KhongDuQuyen):
            gui_hang_service.xac_nhan_chat_hang(str(uuid4()), str(uuid4()), "phu-xe-khac")
        mock_chat.assert_not_called()


def test_xac_nhan_chat_hang_chan_khac_tuyen():
    chuyen = _chuyen(str(uuid4()))
    don = _don_cho_chat(str(uuid4()), str(uuid4()))
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don):
        with pytest.raises(GiaTriLoi, match="không thuộc tuyến vận chuyển"):
            gui_hang_service.xac_nhan_chat_hang(don["id"], chuyen["id"], "phu-xe-1")


def test_xac_nhan_chat_hang_chan_don_khong_cho_tai_diem_dang_dung():
    tuyen_id = str(uuid4())
    chuyen = _chuyen(tuyen_id)
    don = _don_cho_chat(tuyen_id, str(uuid4()))
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": str(uuid4())}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don):
        with pytest.raises(GiaTriLoi, match="không chờ tại điểm xe đang đứng"):
            gui_hang_service.xac_nhan_chat_hang(don["id"], chuyen["id"], "phu-xe-1")


def test_xac_nhan_chat_hang_chan_khac_chieu():
    tuyen_id, diem_gui = str(uuid4()), str(uuid4())
    chuyen = _chuyen(tuyen_id)
    don = _don_cho_chat(tuyen_id, diem_gui)
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_gui}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.kiem_tra_diem_thuoc_tuyen", return_value={"chieu_van_chuyen": "nguoc"}), \
         patch("app.repositories.don_hang_repository.tim_chuyen_xe_theo_id", return_value={**chuyen, "chieu": "xuoi"}):
        with pytest.raises(GiaTriLoi, match="không thể chở đơn hàng gửi theo chiều"):
            gui_hang_service.xac_nhan_chat_hang(don["id"], chuyen["id"], "phu-xe-1")


def test_xac_nhan_chat_hang_chan_chuyen_da_huy():
    chuyen = _chuyen(str(uuid4()), trang_thai="da_huy")
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen):
        with pytest.raises(GiaTriLoi, match="'da_huy', không thể thao tác hàng"):
            gui_hang_service.xac_nhan_chat_hang(str(uuid4()), chuyen["id"], "phu-xe-1")


def test_xac_nhan_chat_hang_bao_loi_khi_don_vua_bi_nguoi_khac_chat():
    tuyen_id, diem_gui = str(uuid4()), str(uuid4())
    chuyen = _chuyen(tuyen_id)
    don = _don_cho_chat(tuyen_id, diem_gui)
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_gui}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.kiem_tra_diem_thuoc_tuyen", return_value={"chieu_van_chuyen": "xuoi"}), \
         patch("app.repositories.don_hang_repository.tim_chuyen_xe_theo_id", return_value={**chuyen, "chieu": "xuoi"}), \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen", return_value=None):
        with pytest.raises(GiaTriLoi, match="vừa được xử lý bởi người khác"):
            gui_hang_service.xac_nhan_chat_hang(don["id"], chuyen["id"], "phu-xe-1")


def test_danh_sach_cho_chat_chi_lay_don_tai_diem_dang_dung():
    tuyen_id, diem_dang_dung = str(uuid4()), str(uuid4())
    chuyen = _chuyen(tuyen_id)

    def _don(ma, diem_gui_id):
        return {
            "id": str(uuid4()), "ma_van_don": ma, "ten_nguoi_nhan": "Bich", "ten_diem_nhan": "VP Lao Cai",
            "diem_gui_id": diem_gui_id, "can_nang_kg": Decimal("3.5"), "ngay_tao": "2026-10-01",
        }

    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_dang_dung}), \
         patch("app.repositories.don_hang_repository.lay_danh_sach_cho_xep_xe") as mock_ds:
        mock_ds.return_value = [_don("DH-01", diem_dang_dung), _don("DH-KHAC-DIEM", str(uuid4()))]

        res = gui_hang_service.danh_sach_cho_chat(chuyen["id"], "phu-xe-1")

        assert [d["ma_van_don"] for d in res] == ["DH-01"]
        assert res[0]["can_nang_kg"] == 3.5
        mock_ds.assert_called_once_with(tuyen_id, chuyen["id"])


def test_danh_sach_cho_do_chi_lay_don_tai_diem_dang_dung():
    chuyen = _chuyen(str(uuid4()), trang_thai="dang_chay")
    diem_dang_dung = str(uuid4())
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_dang_dung}), \
         patch("app.repositories.don_hang_repository.tim_don_can_do_tai_diem") as mock_ds:
        mock_ds.return_value = [
            {"id": str(uuid4()), "ma_van_don": "DH-02", "ten_nguoi_nhan": "Nam", "can_nang_kg": Decimal("10.0")}
        ]
        res = gui_hang_service.danh_sach_cho_do(chuyen["id"], "phu-xe-1")

        assert res[0]["ma_van_don"] == "DH-02"
        assert res[0]["can_nang_kg"] == 10.0
        mock_ds.assert_called_once_with(chuyen["id"], diem_dang_dung)


def test_xac_nhan_do_hang_thanh_cong_tai_dung_diem_nhan():
    chuyen = _chuyen(str(uuid4()), trang_thai="dang_chay")
    diem_nhan = str(uuid4())
    don = _don_tren_xe(chuyen["id"], diem_nhan)
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen) as mock_quyen, \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": diem_nhan}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.cap_nhat_do_hang_tai_diem") as mock_do, \
         patch("app.repositories.don_hang_repository.danh_sach_nhan_vien_gui_hang_tai_diem", return_value=["nv-nhan"]), \
         patch("app.services.gui_hang_service._gui_thong_bao") as mock_thong_bao:
        mock_do.return_value = {**don, "trang_thai": "cho_lay"}

        res = gui_hang_service.xac_nhan_do_hang(don["id"], "phu-xe-1")

        assert res["trang_thai"] == "cho_lay"
        mock_quyen.assert_called_once_with(chuyen["id"], "phu-xe-1")
        mock_do.assert_called_once_with(don["id"], chuyen["id"], "phu-xe-1")
        # Mục 10.3.1 điểm 2: nhắc nhân viên điểm nhận gọi báo người nhận ngay khi hàng tới
        nguoi_nhan, noi_dung, _ = mock_thong_bao.call_args.args
        assert nguoi_nhan == "nv-nhan"
        assert "gọi báo người nhận" in noi_dung


def test_xac_nhan_do_hang_chan_khi_xe_chua_toi_diem_nhan():
    chuyen = _chuyen(str(uuid4()), trang_thai="dang_chay")
    don = _don_tren_xe(chuyen["id"], str(uuid4()))
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe", return_value=chuyen), \
         patch("app.services.gui_hang_service.diem_hien_tai", return_value={"diem_don_tra_id": str(uuid4())}), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.cap_nhat_do_hang_tai_diem") as mock_do:
        with pytest.raises(GiaTriLoi, match="chưa tới điểm nhận"):
            gui_hang_service.xac_nhan_do_hang(don["id"], "phu-xe-1")
        mock_do.assert_not_called()


def test_xac_nhan_do_hang_chan_phu_xe_khong_thuoc_chuyen():
    don = _don_tren_xe(str(uuid4()), str(uuid4()))
    with patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe",
               side_effect=KhongDuQuyen("Chuyến này không thuộc về bạn")), \
         patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.cap_nhat_do_hang_tai_diem") as mock_do:
        with pytest.raises(KhongDuQuyen):
            gui_hang_service.xac_nhan_do_hang(don["id"], "phu-xe-khac")
        mock_do.assert_not_called()


def test_bao_that_lac_phu_xe():
    don_id = str(uuid4())
    phu_xe_id = str(uuid4())
    diem_gui_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.repositories.don_hang_repository.luu_bao_cao_su_co_hang") as mock_luu, \
         patch("app.repositories.don_hang_repository.danh_sach_nhan_vien_gui_hang_tai_diem", return_value=["nv-gui"]) as mock_nv, \
         patch("app.repositories.nguoi_dung_repository.danh_sach_id_theo_vai_tro", return_value=["ql-1"]), \
         patch("app.services.chuyen_xe_service.danh_sach_chuyen_cua_toi", return_value=[{"tuyen_id": "tuyen-1"}]), \
         patch("app.services.gui_hang_service._gui_thong_bao") as mock_thong_bao:
        # Đơn còn chờ chất: phụ xe phải có chuyến cùng tuyến mới được báo (UC-28)
        mock_tim.return_value = {
            "id": don_id, "ma_van_don": "DH-03", "chuyen_id": None, "trang_thai": "cho_van_chuyen", "tuyen_id": "tuyen-1",
            "diem_gui_id": diem_gui_id, "diem_nhan_id": str(uuid4()),
        }
        mock_luu.return_value = {"id": str(uuid4()), "don_hang_id": don_id, "mo_ta": "Thùng hàng bị rách"}

        res = gui_hang_service.bao_that_lac(don_id, "Thùng hàng bị rách", phu_xe_id)

        assert res["don_hang_id"] == don_id
        assert res["mo_ta"] == "Thùng hàng bị rách"
        # UC-28 bước 2: đơn chưa lên xe → báo nhân viên điểm GỬI + quản lý
        mock_nv.assert_called_once_with(diem_gui_id)
        assert {c.args[0] for c in mock_thong_bao.call_args_list} == {"nv-gui", "ql-1"}


def test_bao_that_lac_chan_phu_xe_khong_thuoc_chuyen_cua_don():
    don_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.gui_hang_service.lay_chuyen_cua_phu_xe",
               side_effect=KhongDuQuyen("Chuyến này không thuộc về bạn")), \
         patch("app.repositories.don_hang_repository.luu_bao_cao_su_co_hang") as mock_luu:
        mock_tim.return_value = {"id": don_id, "ma_van_don": "DH-03", "chuyen_id": str(uuid4())}
        with pytest.raises(KhongDuQuyen):
            gui_hang_service.bao_that_lac(don_id, "Mất 1 kiện", "phu-xe-khac")
        mock_luu.assert_not_called()


# ---------------------------------------------------------------------
# Tra cứu & tạo đơn bền vững
# ---------------------------------------------------------------------

def test_tra_cuu_theo_ma_khong_tim_thay_tra_404():
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don", return_value=None):
        with pytest.raises(KhongTimThay):
            gui_hang_service.tra_cuu_theo_ma_van_don("DH-KHONG-CO")


def test_tra_cuu_noi_bo_chan_don_van_phong_khac():
    don = {"id": str(uuid4()), "diem_gui_id": str(uuid4()), "diem_nhan_id": str(uuid4())}
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don", return_value=don):
        with pytest.raises(CamTruyCap):
            gui_hang_service.tra_cuu_noi_bo("DH-01", str(uuid4()))


def test_tra_cuu_sdt_muc_dich_giao_chi_lay_don_cho_giao():
    van_phong_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.tim_theo_sdt", return_value=[]) as mock_tim:
        gui_hang_service.tra_cuu_theo_sdt(" 0987654321 ", van_phong_id, muc_dich="giao")
        mock_tim.assert_called_once_with("0987654321", van_phong_id, chi_cho_giao=True)


def _mock_tao_don_hop_le(du_lieu):
    return [
        patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id",
              return_value={"id": str(du_lieu.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}),
        patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id",
              side_effect=lambda did: {"id": str(did), "ten": f"VP {did}", "loai": "van_phong"}),
        patch("app.repositories.dia_diem_repository.tim_tuyen_theo_id", return_value={"id": str(du_lieu.tuyen_id)}),
        patch("app.repositories.don_hang_repository.kiem_tra_diem_thuoc_tuyen", return_value={"chieu_van_chuyen": "xuoi"}),
    ]


def test_tao_don_hang_sinh_lai_ma_khi_trung(du_lieu_tao_don_mau):
    mocks = _mock_tao_don_hop_le(du_lieu_tao_don_mau)
    for m in mocks:
        m.start()
    try:
        with patch("app.repositories.don_hang_repository.tao_don_hang") as mock_tao:
            mock_tao.side_effect = [don_hang_repository.MaVanDonDaTonTai(), {"ma_van_don": "DH-MOI"}]
            res = gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()))
            assert res["ma_van_don"] == "DH-MOI"
            assert mock_tao.call_count == 2
            ma_lan_1 = mock_tao.call_args_list[0].args[0]["ma_van_don"]
            assert ma_lan_1.startswith("DH-")
    finally:
        for m in mocks:
            m.stop()


def test_tao_don_hang_ghi_nhan_nhan_vien_thu_tien_tra_truoc(du_lieu_tao_don_mau):
    nhan_vien_id = str(uuid4())
    mocks = _mock_tao_don_hop_le(du_lieu_tao_don_mau)
    for m in mocks:
        m.start()
    try:
        with patch("app.repositories.don_hang_repository.tao_don_hang", return_value={"ok": True}) as mock_tao:
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=nhan_vien_id)
            payload = mock_tao.call_args.args[0]
            assert payload["da_thu_tien"] is True
            assert payload["nhan_vien_thu_id"] == nhan_vien_id
            assert payload["diem_gui_id"] == str(du_lieu_tao_don_mau.diem_gui_id)
    finally:
        for m in mocks:
            m.stop()


# ---------------------------------------------------------------------
# Chống tạo trùng đơn (Idempotency-Key), lịch sử trạng thái, gợi ý khách quen
# ---------------------------------------------------------------------

def test_tao_don_hang_gui_lai_cung_khoa_tra_don_cu_khong_tao_them(du_lieu_tao_don_mau):
    nhan_vien_id = str(uuid4())
    don_cu = {"id": str(uuid4()), "ma_van_don": "DH-CU"}
    with patch("app.repositories.don_hang_repository.tim_theo_khoa_chong_trung", return_value=don_cu) as mock_tim,          patch("app.repositories.don_hang_repository.tao_don_hang") as mock_tao:
        res = gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id, khoa_chong_trung="khoa-12345678")
        assert res is don_cu
        mock_tim.assert_called_once_with(nhan_vien_id, "khoa-12345678")
        mock_tao.assert_not_called()


def test_tao_don_hang_khoa_moi_van_tao_va_luu_khoa(du_lieu_tao_don_mau):
    mocks = _mock_tao_don_hop_le(du_lieu_tao_don_mau)
    for m in mocks:
        m.start()
    try:
        with patch("app.repositories.don_hang_repository.tim_theo_khoa_chong_trung", return_value=None),              patch("app.repositories.don_hang_repository.tao_don_hang", return_value={"ok": True}) as mock_tao:
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, str(uuid4()), khoa_chong_trung="khoa-12345678")
            assert mock_tao.call_args.args[0]["khoa_chong_trung"] == "khoa-12345678"
    finally:
        for m in mocks:
            m.stop()


def test_tao_don_hang_khong_khoa_khong_tra_cuu_khoa(du_lieu_tao_don_mau):
    mocks = _mock_tao_don_hop_le(du_lieu_tao_don_mau)
    for m in mocks:
        m.start()
    try:
        with patch("app.repositories.don_hang_repository.tim_theo_khoa_chong_trung") as mock_tim,              patch("app.repositories.don_hang_repository.tao_don_hang", return_value={"ok": True}) as mock_tao:
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, str(uuid4()))
            mock_tim.assert_not_called()
            assert mock_tao.call_args.args[0]["khoa_chong_trung"] is None
    finally:
        for m in mocks:
            m.stop()


def test_lich_su_trang_thai_chan_van_phong_khac():
    don = {"id": str(uuid4()), "diem_gui_id": str(uuid4()), "diem_nhan_id": str(uuid4())}
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don),          patch("app.repositories.don_hang_repository.lay_lich_su_trang_thai") as mock_ls:
        with pytest.raises(CamTruyCap):
            gui_hang_service.lay_lich_su_trang_thai(don["id"], str(uuid4()))
        mock_ls.assert_not_called()


def test_lich_su_trang_thai_xem_duoc_o_ca_hai_dau():
    gui, nhan = str(uuid4()), str(uuid4())
    don = {"id": str(uuid4()), "diem_gui_id": gui, "diem_nhan_id": nhan}
    moc = [{"den_trang_thai": "cho_van_chuyen"}]
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don),          patch("app.repositories.don_hang_repository.lay_lich_su_trang_thai", return_value=moc):
        assert gui_hang_service.lay_lich_su_trang_thai(don["id"], gui) == moc
        assert gui_hang_service.lay_lich_su_trang_thai(don["id"], nhan) == moc


def test_lich_su_trang_thai_don_khong_ton_tai():
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=None):
        with pytest.raises(KhongTimThay):
            gui_hang_service.lay_lich_su_trang_thai(str(uuid4()), str(uuid4()))


def _don_sua(trang_thai="cho_lay", gui=None, nhan=None, **them):
    return {
        "id": str(uuid4()), "ma_van_don": "DH-SUA", "trang_thai": trang_thai,
        "diem_gui_id": gui or str(uuid4()), "diem_nhan_id": nhan or str(uuid4()),
        "ten_nguoi_gui": "An", "sdt_nguoi_gui": "0911111111",
        "ten_nguoi_nhan": "Bình", "sdt_nguoi_nhan": "0922222222", **them,
    }


def test_sua_lien_he_thanh_cong_ghi_nhat_ky_va_bao_van_phong_con_lai():
    gui, nhan = str(uuid4()), str(uuid4())
    don = _don_sua(gui=gui, nhan=nhan)
    don_moi = {**don, "sdt_nguoi_nhan": "0933333333"}
    yeu_cau = SuaThongTinLienHeRequest(sdt_nguoi_nhan="0933333333", ly_do="khách đọc nhầm số")
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he", return_value=don_moi) as mock_sua, \
         patch("app.repositories.don_hang_repository.danh_sach_nhan_vien_gui_hang_tai_diem", return_value=["nv-nhan"]) as mock_ds, \
         patch("app.services.gui_hang_service._gui_thong_bao") as mock_tb:
        res = gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv-gui", gui, yeu_cau)

    assert res["sdt_nguoi_nhan"] == "0933333333"
    # Chỉ truyền đúng trường được sửa + người sửa + lý do
    mock_sua.assert_called_once_with(don["id"], {"sdt_nguoi_nhan": "0933333333"}, "nv-gui", "khách đọc nhầm số")
    mock_ds.assert_called_once_with(nhan)  # báo văn phòng NHẬN vì người sửa ở văn phòng gửi
    nguoi, noi_dung, don_id = mock_tb.call_args.args
    assert nguoi == "nv-nhan" and "SĐT người nhận" in noi_dung and don_id == don["id"]


def test_sua_lien_he_van_phong_nhan_sua_thi_bao_van_phong_gui():
    gui, nhan = str(uuid4()), str(uuid4())
    don = _don_sua(gui=gui, nhan=nhan)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he", return_value={**don, "ten_nguoi_nhan": "Bình A"}), \
         patch("app.repositories.don_hang_repository.danh_sach_nhan_vien_gui_hang_tai_diem", return_value=[]) as mock_ds:
        gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv-nhan", nhan, SuaThongTinLienHeRequest(ten_nguoi_nhan="Bình A"))
    mock_ds.assert_called_once_with(gui)


def test_sua_lien_he_khong_doi_gi_thi_khong_thong_bao():
    gui = str(uuid4())
    don = _don_sua(gui=gui)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he", return_value=dict(don)), \
         patch("app.services.gui_hang_service._gui_thong_bao") as mock_tb:
        gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv", gui, SuaThongTinLienHeRequest(ten_nguoi_gui="An"))
    mock_tb.assert_not_called()


def test_sua_lien_he_chan_don_da_giao():
    gui = str(uuid4())
    don = _don_sua(trang_thai="da_giao", gui=gui)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he") as mock_sua:
        with pytest.raises(GiaTriLoi):
            gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv", gui, SuaThongTinLienHeRequest(ten_nguoi_gui="X"))
        mock_sua.assert_not_called()


def test_sua_lien_he_chan_khi_don_vua_duoc_giao_giua_chung():
    gui = str(uuid4())
    don = _don_sua(gui=gui)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he",
               side_effect=don_hang_repository.DonDaGiao()):
        with pytest.raises(GiaTriLoi):
            gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv", gui, SuaThongTinLienHeRequest(ten_nguoi_gui="X"))


def test_sua_lien_he_chan_van_phong_khac_va_don_khong_ton_tai():
    don = _don_sua()
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.sua_thong_tin_lien_he") as mock_sua:
        with pytest.raises(CamTruyCap):
            gui_hang_service.sua_thong_tin_lien_he(don["id"], "nv", str(uuid4()), SuaThongTinLienHeRequest(ten_nguoi_gui="X"))
        mock_sua.assert_not_called()
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=None):
        with pytest.raises(KhongTimThay):
            gui_hang_service.sua_thong_tin_lien_he(str(uuid4()), "nv", str(uuid4()), SuaThongTinLienHeRequest(ten_nguoi_gui="X"))


def test_repo_sua_lien_he_tu_choi_ten_cot_la():
    with pytest.raises(ValueError):
        don_hang_repository.sua_thong_tin_lien_he(str(uuid4()), {"gia_cuoc; DROP TABLE don_hang": "1"}, "nv", None)
    with pytest.raises(ValueError):
        don_hang_repository.sua_thong_tin_lien_he(str(uuid4()), {}, "nv", None)


def test_lich_su_chinh_sua_chan_van_phong_khac():
    don = _don_sua()
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.lay_lich_su_chinh_sua") as mock_ls:
        with pytest.raises(CamTruyCap):
            gui_hang_service.lay_lich_su_chinh_sua(don["id"], str(uuid4()))
        mock_ls.assert_not_called()


def test_goi_y_khach_phan_biet_nguoi_gui_nguoi_nhan_va_gioi_han_van_phong():
    vp = str(uuid4())
    with patch("app.repositories.don_hang_repository.goi_y_khach_theo_sdt", return_value=[]) as mock_gy:
        gui_hang_service.goi_y_khach(" 0987654321 ", "gui", vp)
        mock_gy.assert_called_with("0987654321", True, vp)
        gui_hang_service.goi_y_khach("0987654321", "nhan", vp)
        mock_gy.assert_called_with("0987654321", False, vp)


# ---------------------------------------------------------------------
# Hàng đến & liên hệ người nhận / người gửi / quản lý (mục 10.3.1, UC-25)
# ---------------------------------------------------------------------

def test_lay_hang_den_theo_van_phong():
    diem_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.lay_hang_den") as mock_ds:
        mock_ds.return_value = [{"id": str(uuid4()), "ma_van_don": "DH-04", "trang_thai": "cho_lay"}]
        res = gui_hang_service.lay_hang_den(diem_id)
        assert res[0]["ma_van_don"] == "DH-04"
        mock_ds.assert_called_once_with(diem_id)


def _don_cho_lay(van_phong_id, **them):
    return {
        "id": str(uuid4()), "ma_van_don": "DH-CHO-LAY", "diem_nhan_id": van_phong_id, "ten_diem_nhan": "VP Sapa",
        "trang_thai": "cho_lay", "co_canh_bao_cho_lau": False, "da_thong_bao_nguoi_nhan": False, **them,
    }


def test_ghi_lien_he_nguoi_nhan_thanh_cong_bat_co_da_thong_bao():
    van_phong_id, nhan_vien_id = str(uuid4()), str(uuid4())
    don = _don_cho_lay(van_phong_id)
    with patch("app.repositories.don_hang_repository.tim_theo_id", side_effect=[don, {**don, "da_thong_bao_nguoi_nhan": True}]), \
         patch("app.repositories.don_hang_repository.ghi_lien_he") as mock_ghi:
        res = gui_hang_service.ghi_ket_qua_lien_he(
            don["id"], nhan_vien_id, van_phong_id, doi_tuong="nguoi_nhan", ket_qua="da_lien_he"
        )
        assert res["da_thong_bao_nguoi_nhan"] is True
        kwargs = mock_ghi.call_args.kwargs
        assert mock_ghi.call_args.args[:5] == (don["id"], nhan_vien_id, "nguoi_nhan", "da_lien_he", None)
        assert kwargs["danh_dau_da_thong_bao"] is True
        assert kwargs["thong_bao_cho"] == []


def test_ghi_lien_he_khong_lien_he_duoc_khong_dong_vao_co():
    """Cờ da_thong_bao_nguoi_nhan chỉ đi lên: 1 lần gọi lại thất bại không được xóa dấu đã báo được."""
    van_phong_id = str(uuid4())
    don = _don_cho_lay(van_phong_id, da_thong_bao_nguoi_nhan=True)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.ghi_lien_he") as mock_ghi:
        gui_hang_service.ghi_ket_qua_lien_he(
            don["id"], str(uuid4()), van_phong_id, doi_tuong="nguoi_nhan", ket_qua="khong_lien_he_duoc"
        )
        assert mock_ghi.call_args.kwargs["danh_dau_da_thong_bao"] is False


def test_ghi_lien_he_chan_bao_quan_ly_khi_don_chua_qua_7_ngay():
    van_phong_id = str(uuid4())
    don = _don_cho_lay(van_phong_id)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.ghi_lien_he") as mock_ghi:
        with pytest.raises(GiaTriLoi, match="7 ngày"):
            gui_hang_service.ghi_ket_qua_lien_he(
                don["id"], str(uuid4()), van_phong_id, doi_tuong="quan_ly", ket_qua="da_bao_quan_ly"
            )
        mock_ghi.assert_not_called()


def test_ghi_lien_he_bao_quan_ly_hang_ton_gui_quan_ly_dang_hoat_dong():
    van_phong_id = str(uuid4())
    don = _don_cho_lay(van_phong_id, trang_thai="qua_han_luu_kho", co_canh_bao_cho_lau=True)
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.nguoi_dung_repository.danh_sach_id_theo_vai_tro", return_value=["ql-1"]) as mock_ql, \
         patch("app.repositories.don_hang_repository.ghi_lien_he") as mock_ghi, \
         patch("app.services.gui_hang_service.broadcast_sync") as mock_ws:
        gui_hang_service.ghi_ket_qua_lien_he(
            don["id"], str(uuid4()), van_phong_id, doi_tuong="quan_ly", ket_qua="da_bao_quan_ly", ghi_chu="Gọi 3 lần"
        )
        mock_ql.assert_called_once_with("quan_ly", chi_dang_hoat_dong=True)
        kwargs = mock_ghi.call_args.kwargs
        assert kwargs["thong_bao_cho"] == ["ql-1"]
        assert "DH-CHO-LAY" in kwargs["noi_dung_thong_bao"] and "Gọi 3 lần" in kwargs["noi_dung_thong_bao"]
        mock_ws.assert_called_once()


def test_ghi_lien_he_chan_van_phong_khac():
    don = _don_cho_lay(str(uuid4()))
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don), \
         patch("app.repositories.don_hang_repository.ghi_lien_he") as mock_ghi:
        with pytest.raises(CamTruyCap):
            gui_hang_service.ghi_ket_qua_lien_he(
                don["id"], str(uuid4()), str(uuid4()), doi_tuong="nguoi_nhan", ket_qua="da_lien_he"
            )
        mock_ghi.assert_not_called()


def test_ghi_lien_he_chan_don_chua_toi():
    van_phong_id = str(uuid4())
    don = _don_cho_lay(van_phong_id, trang_thai="da_len_xe")
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don):
        with pytest.raises(GiaTriLoi, match="chờ lấy hoặc hàng tồn"):
            gui_hang_service.ghi_ket_qua_lien_he(
                don["id"], str(uuid4()), van_phong_id, doi_tuong="nguoi_nhan", ket_qua="da_lien_he"
            )


def test_lich_su_lien_he_chi_van_phong_nhan_xem_duoc():
    don = {"id": str(uuid4()), "diem_gui_id": str(uuid4()), "diem_nhan_id": str(uuid4())}
    with patch("app.repositories.don_hang_repository.tim_theo_id", return_value=don):
        with pytest.raises(CamTruyCap):
            gui_hang_service.lay_lich_su_lien_he(don["id"], don["diem_gui_id"])


# ---------------------------------------------------------------------
# Job UC-46
# ---------------------------------------------------------------------

def test_quet_canh_bao_va_chuyen_hang_ton():
    with patch("app.repositories.don_hang_repository.quet_canh_bao_7_ngay",
               return_value=(2, [("nv-1", "nhắc 1"), ("nv-1", "nhắc 2")])) as mock_7, \
         patch("app.repositories.don_hang_repository.quet_chuyen_hang_ton_14_ngay",
               return_value=(1, [("nv-1", "hàng tồn")])) as mock_14, \
         patch("app.services.gui_hang_service.broadcast_sync") as mock_ws:

        res = gui_hang_service.quet_canh_bao_va_chuyen_hang_ton()

        assert res == {"so_don_canh_bao_7_ngay": 2, "so_don_chuyen_ton_14_ngay": 1}
        mock_7.assert_called_once()
        mock_14.assert_called_once()
        assert mock_ws.call_count == 3


def test_noi_dung_canh_bao_7_ngay_theo_da_thong_bao():
    """Mục 10.3.1 điểm 3: đã báo được người nhận → gọi lại người nhận; chưa từng → gọi người gửi."""
    da_bao = gui_hang_service._noi_dung_canh_bao_7_ngay({"ma_van_don": "DH-A", "da_thong_bao_nguoi_nhan": True})
    chua_bao = gui_hang_service._noi_dung_canh_bao_7_ngay({"ma_van_don": "DH-B", "da_thong_bao_nguoi_nhan": False})
    assert "gọi lại người nhận" in da_bao
    assert "gọi người gửi" in chua_bao


# ---------------------------------------------------------------------
# Danh sách & thống kê (UC-39)
# ---------------------------------------------------------------------

def test_lay_danh_sach_don_tra_items_va_total():
    van_phong_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.lay_danh_sach_don") as mock_ds:
        mock_ds.return_value = ([{"ma_van_don": "DH-01"}, {"ma_van_don": "DH-02"}], 42)
        res = gui_hang_service.lay_danh_sach_don(van_phong_id, huong="nhan", limit=2, offset=10)
        assert res == {"items": [{"ma_van_don": "DH-01"}, {"ma_van_don": "DH-02"}], "total": 42}
        mock_ds.assert_called_once_with(
            van_phong_id=van_phong_id, huong="nhan", trang_thai=None, phuong_thuc_thanh_toan=None,
            tu_khoa=None, limit=2, offset=10,
        )


def test_thong_ke_hang_tai_diem_toan_he_thong():
    tu, den = date(2026, 10, 1), date(2026, 10, 3)
    with patch("app.repositories.don_hang_repository.thong_ke_hang_tai_diem") as mock_thong_ke:
        mock_thong_ke.return_value = {"tong_don_gui_di": 5, "tong_doanh_thu": 360000}
        res = gui_hang_service.thong_ke_hang_tai_diem(None, tu, den)
        assert res["tong_doanh_thu"] == 360000
        mock_thong_ke.assert_called_once_with(None, tu, den)


def test_thong_ke_chan_khoang_ngay_nguoc():
    with pytest.raises(GiaTriLoi, match="Ngày bắt đầu"):
        gui_hang_service.thong_ke_hang_tai_diem(None, date(2026, 10, 5), date(2026, 10, 1))


def test_thong_ke_hang_tai_diem_khong_ton_tai():
    with patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id", return_value=None):
        with pytest.raises(GiaTriLoi, match="không tồn tại"):
            gui_hang_service.thong_ke_hang_tai_diem(str(uuid4()), date(2026, 10, 1), date(2026, 10, 1))


def test_doi_soat_tien_cong_tong():
    with patch("app.repositories.don_hang_repository.doi_soat_tien_theo_nhan_vien") as mock_ds:
        mock_ds.return_value = [{"tong_tien": 100000}, {"tong_tien": 250000}]
        res = gui_hang_service.doi_soat_tien(str(uuid4()), date(2026, 10, 3), date(2026, 10, 3))
        assert res["tong_tien"] == 350000
        assert res["tu_ngay"] == "2026-10-03"
