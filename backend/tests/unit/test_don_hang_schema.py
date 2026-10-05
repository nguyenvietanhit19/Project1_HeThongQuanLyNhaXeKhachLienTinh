from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.don_hang_schema import CapNhatLienHeRequest, SuaThongTinLienHeRequest, TaoDonHangRequest, GiaoHangRequest
from app.schemas.hoan_tien_schema import XacNhanChuyenKhoanRequest


def test_tao_don_hang_schema_hop_le():
    data = {
        "tuyen_id": uuid4(),
        "diem_gui_id": uuid4(),
        "diem_nhan_id": uuid4(),
        "loai_hang_id": uuid4(),
        "can_nang_kg": Decimal("10.5"),
        "gia_cuoc": 150000,
        "ten_nguoi_gui": "Nguyen Van A",
        "sdt_nguoi_gui": "0912345678",
        "ten_nguoi_nhan": "Tran Thi B",
        "sdt_nguoi_nhan": "0987654321",
        "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc",
    }
    req = TaoDonHangRequest(**data)
    assert req.can_nang_kg == Decimal("10.5")
    assert req.gia_cuoc == 150000
    assert req.phuong_thuc_thanh_toan == "nguoi_gui_tra_truoc"


def test_tao_don_hang_schema_can_nang_am_loi():
    data = {
        "tuyen_id": uuid4(),
        "diem_gui_id": uuid4(),
        "diem_nhan_id": uuid4(),
        "loai_hang_id": uuid4(),
        "can_nang_kg": Decimal("-5.0"),  # Sai: phải > 0
        "gia_cuoc": 100000,
        "ten_nguoi_gui": "A",
        "sdt_nguoi_gui": "0912345678",
        "ten_nguoi_nhan": "B",
        "sdt_nguoi_nhan": "0987654321",
        "phuong_thuc_thanh_toan": "cod_nguoi_nhan_tra",
    }
    with pytest.raises(ValidationError):
        TaoDonHangRequest(**data)


def test_xac_nhan_chuyen_khoan_schema():
    data = {
        "so_tai_khoan_nhan": "1903456789",
        "ten_ngan_hang_nhan": "Techcombank",
        "ten_chu_tai_khoan_nhan": "NGUYEN VAN A",
    }
    req = XacNhanChuyenKhoanRequest(**data)
    assert req.so_tai_khoan_nhan == "1903456789"


def _du_lieu_tao_don(**ghi_de):
    data = {
        "tuyen_id": uuid4(),
        "diem_gui_id": uuid4(),
        "diem_nhan_id": uuid4(),
        "loai_hang_id": uuid4(),
        "can_nang_kg": Decimal("2"),
        "gia_cuoc": 50000,
        "ten_nguoi_gui": "Nguyen Van A",
        "sdt_nguoi_gui": "0912345678",
        "ten_nguoi_nhan": "Tran Thi B",
        "sdt_nguoi_nhan": "0987654321",
        "phuong_thuc_thanh_toan": "cod_nguoi_nhan_tra",
    }
    data.update(ghi_de)
    return data


def test_tao_don_hang_schema_cat_khoang_trang_ten():
    req = TaoDonHangRequest(**_du_lieu_tao_don(ten_nguoi_gui="  Nguyen Van A  "))
    assert req.ten_nguoi_gui == "Nguyen Van A"


def test_tao_don_hang_schema_chan_ten_chi_co_khoang_trang():
    with pytest.raises(ValidationError):
        TaoDonHangRequest(**_du_lieu_tao_don(ten_nguoi_nhan="   "))


def test_tao_don_hang_schema_chan_vuot_kieu_cot_db():
    with pytest.raises(ValidationError):
        TaoDonHangRequest(**_du_lieu_tao_don(can_nang_kg=Decimal("1000000")))
    with pytest.raises(ValidationError):
        TaoDonHangRequest(**_du_lieu_tao_don(can_nang_kg=Decimal("1.234")))


def test_giao_hang_schema_chuan_hoa_ma_van_don():
    assert GiaoHangRequest(ma_van_don="  dh-20261001-abc123 ").ma_van_don == "DH-20261001-ABC123"


@pytest.mark.parametrize("doi_tuong,ket_qua", [
    ("nguoi_nhan", "da_lien_he"),
    ("nguoi_nhan", "khong_lien_he_duoc"),
    ("nguoi_gui", "da_lien_he"),
    ("quan_ly", "da_bao_quan_ly"),
])
def test_cap_nhat_lien_he_to_hop_hop_le(doi_tuong, ket_qua):
    req = CapNhatLienHeRequest(doi_tuong=doi_tuong, ket_qua=ket_qua, ghi_chu="  ")
    assert req.ghi_chu is None


@pytest.mark.parametrize("doi_tuong,ket_qua", [
    ("quan_ly", "da_lien_he"),
    ("nguoi_nhan", "da_bao_quan_ly"),
])
def test_cap_nhat_lien_he_chan_to_hop_vo_ly(doi_tuong, ket_qua):
    with pytest.raises(ValidationError):
        CapNhatLienHeRequest(doi_tuong=doi_tuong, ket_qua=ket_qua)



# ---------------------------------------------------------------------
# Sửa thông tin liên hệ của đơn
# ---------------------------------------------------------------------

def test_sua_lien_he_chi_nhan_truong_can_sua_va_strip():
    req = SuaThongTinLienHeRequest(sdt_nguoi_nhan=" 0987654321 ", ten_nguoi_nhan="  Trần Thị B  ")
    assert req.sdt_nguoi_nhan == "0987654321"
    assert req.ten_nguoi_nhan == "Trần Thị B"
    assert req.ten_nguoi_gui is None and req.sdt_nguoi_gui is None


def test_sua_lien_he_phai_co_it_nhat_mot_truong():
    with pytest.raises(ValidationError):
        SuaThongTinLienHeRequest()
    with pytest.raises(ValidationError):
        SuaThongTinLienHeRequest(ly_do="chỉ có lý do")


@pytest.mark.parametrize("sdt", ["123", "09876543210123", "abcdefghij", "098 765 4321"])
def test_sua_lien_he_chan_sdt_sai_dinh_dang(sdt):
    with pytest.raises(ValidationError):
        SuaThongTinLienHeRequest(sdt_nguoi_nhan=sdt)


def test_sua_lien_he_chan_ten_rong_va_ly_do_qua_dai():
    with pytest.raises(ValidationError):
        SuaThongTinLienHeRequest(ten_nguoi_gui="   ")
    with pytest.raises(ValidationError):
        SuaThongTinLienHeRequest(ten_nguoi_gui="An", ly_do="x" * 201)


def test_sua_lien_he_ly_do_rong_thanh_none():
    assert SuaThongTinLienHeRequest(ten_nguoi_gui="An", ly_do="   ").ly_do is None
