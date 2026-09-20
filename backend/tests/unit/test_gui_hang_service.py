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
    )


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


def test_xac_nhan_giao_hang_thanh_cong():
    ma_van_don = "DH-20260920-TEST01"
    don_hang_mau = {
        "id": str(uuid4()),
        "ma_van_don": ma_van_don,
        "trang_thai": "cho_lay",
        "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc",
    }
    with patch("app.repositories.don_hang_repository.tim_theo_ma_van_don") as mock_tim, \
         patch("app.repositories.don_hang_repository.cap_nhat_giao_hang") as mock_cap_nhat:
        mock_tim.return_value = don_hang_mau
        mock_cap_nhat.return_value = {**don_hang_mau, "trang_thai": "da_giao"}

        ket_qua = gui_hang_service.xac_nhan_giao_hang(ma_van_don, nhan_vien_nhan_id=str(uuid4()))
        assert ket_qua["trang_thai"] == "da_giao"


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


def test_xac_nhan_chat_hang_va_do_hang():
    don_id = str(uuid4())
    chuyen_id = str(uuid4())

    with patch("app.repositories.don_hang_repository.tim_theo_id") as mock_tim, \
         patch("app.repositories.don_hang_repository.cap_nhat_chat_hang_len_chuyen") as mock_chat:
        mock_tim.return_value = {"id": don_id, "trang_thai": "cho_van_chuyen"}
        mock_chat.return_value = {"id": don_id, "trang_thai": "da_len_xe", "chuyen_id": chuyen_id}

        ket_qua = gui_hang_service.xac_nhan_chat_hang(don_id, chuyen_id)
        assert ket_qua["trang_thai"] == "da_len_xe"

