from decimal import Decimal
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.don_hang_schema import TaoDonHangRequest, GiaoHangRequest
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

