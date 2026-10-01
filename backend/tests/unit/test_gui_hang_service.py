from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4
import pytest

from app.schemas.don_hang_schema import TaoDonHangRequest
from app.services import gui_hang_service
from app.utils.loi import GiaTriLoi


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
        xac_nhan_da_thu_truoc=True,
    )


def test_tao_don_hang_chan_hang_cam(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Pháo nổ", "la_hang_cam": True}
        with pytest.raises(GiaTriLoi, match="cấm vận chuyển"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()), vai_tro="quan_ly")


def test_tao_don_hang_chan_diem_gui_trung_diem_nhan(du_lieu_tao_don_mau):
    cung_diem_id = du_lieu_tao_don_mau.diem_gui_id
    du_lieu_tao_don_mau.diem_nhan_id = cung_diem_id

    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.return_value = {"id": str(cung_diem_id), "ten": "VP Mỹ Đình", "loai": "van_phong"}

        with pytest.raises(GiaTriLoi, match="không được trùng"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()), vai_tro="quan_ly")


def test_tao_don_hang_chan_diem_dung_doc_duong(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.return_value = {"id": str(du_lieu_tao_don_mau.diem_gui_id), "ten": "Trạm dừng nghỉ", "loai": "diem_dung"}

        with pytest.raises(GiaTriLoi, match="phải là văn phòng"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()), vai_tro="quan_ly")


def test_xac_nhan_giao_hang_thanh_cong():
    ma_van_don = "DH-20260920-TEST01"
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": ma_van_don,
        "trang_thai": "cho_lay",
        "diem_nhan_id": str(uuid4()),
        "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc",
        "da_thu_tien": True,
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim, \
         patch("app.repositories.don_hang_repository.cap_nhat_giao_hang") as mock_cap_nhat:
        mock_tim.return_value = don_hang_mau
        mock_cap_nhat.return_value = {**don_hang_mau, "trang_thai": "da_giao"}

        ket_qua = gui_hang_service.xac_nhan_giao_hang(ma_van_don, nhan_vien_nhan_id=str(uuid4()), vai_tro="quan_ly")
        assert ket_qua["trang_thai"] == "da_giao"


def test_xac_nhan_giao_hang_chan_khi_don_chua_o_trang_thai_cho_lay():
    ma_van_don = "DH-20260920-TEST02"
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": ma_van_don,
        "trang_thai": "da_len_xe",
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim:
        mock_tim.return_value = don_hang_mau
        with pytest.raises(GiaTriLoi):
            gui_hang_service.xac_nhan_giao_hang(ma_van_don, nhan_vien_nhan_id=str(uuid4()), vai_tro="quan_ly")


def test_xac_nhan_chat_hang_va_do_hang():
    don_id = str(uuid4())
    chuyen_id = str(uuid4())
    tuyen_id = str(uuid4())
    diem_gui_id = str(uuid4())
    diem_nhan_id = str(uuid4())

    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_chuyen, \
         patch("app.services.chuyen_xe_service.diem_hien_tai") as mock_diem_hien_tai, \
         patch("app.repositories.dia_diem_repository.danh_sach_diem_theo_tuyen") as mock_diem_tuyen, \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen") as mock_chat, \
         patch("app.repositories.don_hang_repository.cap_nhat_do_hang_tai_diem") as mock_do:
        mock_tim.return_value = {
            "id": don_id,
            "tuyen_id": tuyen_id,
            "diem_gui_id": diem_gui_id,
            "diem_nhan_id": diem_nhan_id,
            "trang_thai": "cho_van_chuyen",
        }
        mock_chuyen.return_value = {
            "id": chuyen_id,
            "tuyen_id": tuyen_id,
            "chieu": "xuoi",
            "trang_thai": "dang_chay",
        }
        mock_diem_hien_tai.side_effect = [
            {"diem_don_tra_id": diem_gui_id},
            {"diem_don_tra_id": diem_nhan_id},
        ]
        mock_diem_tuyen.return_value = [
            {"diem_don_tra_id": diem_gui_id, "thu_tu": 1},
            {"diem_don_tra_id": diem_nhan_id, "thu_tu": 2},
        ]
        mock_chat.return_value = {"id": don_id, "trang_thai": "da_len_xe", "chuyen_id": chuyen_id}

        phu_xe_id = str(uuid4())
        ket_qua = gui_hang_service.xac_nhan_chat_hang(don_id, chuyen_id, phu_xe_id)
        assert ket_qua["trang_thai"] == "da_len_xe"

        mock_tim.return_value = {
            "id": don_id,
            "tuyen_id": tuyen_id,
            "diem_nhan_id": diem_nhan_id,
            "chuyen_id": chuyen_id,
            "trang_thai": "da_len_xe",
        }
        mock_do.return_value = {"id": don_id, "trang_thai": "cho_lay"}
        ket_qua_do = gui_hang_service.xac_nhan_do_hang(don_id, phu_xe_id)
        assert ket_qua_do["trang_thai"] == "cho_lay"


def test_tao_don_hang_chan_diem_ngoai_tuyen(du_lieu_tao_don_mau):
    with patch("app.repositories.don_hang_repository.tim_loai_hang_theo_id") as mock_loai_hang, \
         patch("app.repositories.dia_diem_repository.tim_diem_don_tra_theo_id") as mock_diem, \
         patch("app.repositories.dia_diem_repository.tim_tuyen_theo_id") as mock_tuyen, \
         patch("app.repositories.dia_diem_repository.danh_sach_diem_theo_tuyen") as mock_diem_tuyen:
        mock_loai_hang.return_value = {"id": str(du_lieu_tao_don_mau.loai_hang_id), "ten": "Quần áo", "la_hang_cam": False}
        mock_diem.side_effect = [
            {"id": str(du_lieu_tao_don_mau.diem_gui_id), "ten": "VP Hà Nội", "loai": "van_phong"},
            {"id": str(du_lieu_tao_don_mau.diem_nhan_id), "ten": "VP Sapa", "loai": "van_phong"},
        ]
        mock_tuyen.return_value = {"id": str(du_lieu_tao_don_mau.tuyen_id), "ten": "Hà Nội - Sapa"}
        # Điểm nhận không nằm trong tuyến
        mock_diem_tuyen.return_value = [
            {"diem_don_tra_id": str(du_lieu_tao_don_mau.diem_gui_id), "thu_tu": 1},
            {"diem_don_tra_id": "diem-khac", "thu_tu": 2},
        ]

        with pytest.raises(GiaTriLoi, match="không thuộc lộ trình tuyến"):
            gui_hang_service.tao_don_hang(du_lieu_tao_don_mau, nhan_vien_id=str(uuid4()), vai_tro="quan_ly")


def test_xac_nhan_chat_hang_chan_sai_tuyen():
    don_id = str(uuid4())
    chuyen_id = str(uuid4())
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_chuyen:
        mock_tim.return_value = {"id": don_id, "tuyen_id": "tuyen-1", "trang_thai": "cho_van_chuyen"}
        mock_chuyen.return_value = {"id": chuyen_id, "tuyen_id": "tuyen-2", "chieu": "xuoi", "trang_thai": "dang_chay"}
        with pytest.raises(GiaTriLoi, match="không thuộc tuyến vận chuyển"):
            gui_hang_service.xac_nhan_chat_hang(don_id, chuyen_id, str(uuid4()))


def test_xac_nhan_chat_hang_chan_nguoc_chieu_chuyen_xuoi():
    don_id = str(uuid4())
    chuyen_id = str(uuid4())
    tuyen_id = "tuyen-1"
    diem_gui_id = "diem-2"
    diem_nhan_id = "diem-1"
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_chuyen, \
         patch("app.repositories.dia_diem_repository.danh_sach_diem_theo_tuyen") as mock_diem_tuyen:
        mock_tim.return_value = {
            "id": don_id, "tuyen_id": tuyen_id, "diem_gui_id": diem_gui_id, "diem_nhan_id": diem_nhan_id, "trang_thai": "cho_van_chuyen"
        }
        mock_chuyen.return_value = {"id": chuyen_id, "tuyen_id": tuyen_id, "chieu": "xuoi", "trang_thai": "dang_chay"}
        mock_diem_tuyen.return_value = [
            {"diem_don_tra_id": "diem-1", "thu_tu": 1},
            {"diem_don_tra_id": "diem-2", "thu_tu": 2},
        ]
        with pytest.raises(GiaTriLoi, match="không cùng chiều"):
            gui_hang_service.xac_nhan_chat_hang(don_id, chuyen_id, str(uuid4()))


def test_xac_nhan_chat_hang_thanh_cong_chuyen_nguoc():
    don_id = str(uuid4())
    chuyen_id = str(uuid4())
    tuyen_id = "tuyen-1"
    diem_gui_id = "diem-2"
    diem_nhan_id = "diem-1"
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_chuyen, \
         patch("app.services.chuyen_xe_service.diem_hien_tai") as mock_diem_hien_tai, \
         patch("app.repositories.dia_diem_repository.danh_sach_diem_theo_tuyen") as mock_diem_tuyen, \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen") as mock_chat:
        mock_tim.return_value = {
            "id": don_id, "tuyen_id": tuyen_id, "diem_gui_id": diem_gui_id, "diem_nhan_id": diem_nhan_id, "trang_thai": "cho_van_chuyen"
        }
        # Chuyến ngược: xe chạy từ thu_tu lớn về nhỏ (diem-2 -> diem-1)
        mock_chuyen.return_value = {"id": chuyen_id, "tuyen_id": tuyen_id, "chieu": "nguoc", "trang_thai": "dang_chay"}
        mock_diem_hien_tai.return_value = {"diem_don_tra_id": diem_gui_id}
        mock_diem_tuyen.return_value = [
            {"diem_don_tra_id": "diem-1", "thu_tu": 1},
            {"diem_don_tra_id": "diem-2", "thu_tu": 2},
        ]
        mock_chat.return_value = {"id": don_id, "trang_thai": "da_len_xe", "chuyen_id": chuyen_id}

        res = gui_hang_service.xac_nhan_chat_hang(don_id, chuyen_id, str(uuid4()))
        assert res["trang_thai"] == "da_len_xe"


def test_phu_xe_danh_sach_cho_chat():
    chuyen_id = "chuyen-1"
    phu_xe_id = "user-1"
    with patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_lay_chuyen, \
         patch("app.services.chuyen_xe_service.diem_hien_tai") as mock_diem_ht, \
         patch("app.repositories.don_hang_repository.lay_danh_sach_cho_xep_xe") as mock_cho_xep:
        mock_lay_chuyen.return_value = {"id": chuyen_id, "tuyen_id": "tuyen-1", "trang_thai": "chua_khoi_hanh"}
        mock_diem_ht.return_value = {"diem_don_tra_id": "diem-1"}
        mock_cho_xep.return_value = [{"id": "dh-1", "ma_van_don": "DH01"}]

        res = gui_hang_service.danh_sach_cho_chat(chuyen_id, phu_xe_id)
        assert len(res) == 1
        assert res[0]["ma_van_don"] == "DH01"
        mock_cho_xep.assert_called_once_with(tuyen_id="tuyen-1", chuyen_id=chuyen_id, diem_gui_id="diem-1")


def test_phu_xe_danh_sach_cho_do():
    chuyen_id = "chuyen-1"
    phu_xe_id = "user-1"
    with patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_lay_chuyen, \
         patch("app.services.chuyen_xe_service.diem_hien_tai") as mock_diem_ht, \
         patch("app.repositories.don_hang_repository.tim_don_can_do_tai_diem") as mock_do:
        mock_lay_chuyen.return_value = {"id": chuyen_id, "tuyen_id": "tuyen-1", "trang_thai": "dang_chay"}
        mock_diem_ht.return_value = {"diem_don_tra_id": "diem-2"}
        mock_do.return_value = [{"id": "dh-2", "ma_van_don": "DH02"}]

        res = gui_hang_service.danh_sach_cho_do(chuyen_id, phu_xe_id)
        assert len(res) == 1
        assert res[0]["ma_van_don"] == "DH02"
        mock_do.assert_called_once_with(chuyen_id, "diem-2")


def test_phu_xe_bao_that_lac():
    don_id = "dh-1"
    phu_xe_id = "user-1"
    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.services.chuyen_xe_service.lay_chuyen_cua_phu_xe") as mock_lay_chuyen, \
         patch("app.repositories.bao_cao_su_co_hang_repository.tao") as mock_tao_bao_cao:
        mock_tim.return_value = {"id": don_id, "trang_thai": "da_len_xe", "chuyen_id": "chuyen-1"}
        mock_lay_chuyen.return_value = {"id": "chuyen-1", "tuyen_id": "tuyen-1"}
        gui_hang_service.bao_that_lac(don_id, "Bể vỡ kiện hàng lúc bốc xếp", phu_xe_id)
        mock_tao_bao_cao.assert_called_once_with(don_id, phu_xe_id, "Bể vỡ kiện hàng lúc bốc xếp")


def test_thong_ke_hang_tai_diem_toan_he_thong():
    with patch("app.repositories.don_hang_repository.thong_ke_hang_tai_diem") as mock_thong_ke:
        mock_thong_ke.return_value = {
            "tong_don_gui_di": 5,
            "tong_so_don": 5,
            "tong_doanh_thu": 360000,
            "cho_lay": 1,
            "da_giao": 2,
            "hang_ton_qua_han": 0,
        }
        res = gui_hang_service.thong_ke_hang_tai_diem(None, nguoi_dung_id=str(uuid4()), vai_tro="quan_ly")
        assert res["tong_so_don"] == 5
        assert res["tong_doanh_thu"] == 360000


def test_lay_danh_sach_don_gan_day():
    with patch("app.repositories.don_hang_repository.lay_danh_sach_don_gan_day") as mock_repo:
        mock_repo.return_value = [{"ma_van_don": "DH-01"}, {"ma_van_don": "DH-02"}]
        res = gui_hang_service.lay_danh_sach_don_gan_day(limit=10)
        assert len(res) == 2
        assert res[0]["ma_van_don"] == "DH-01"


