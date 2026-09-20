import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.chuyen_schema import (
    ChuyenXePublicResponse,
    GheItemResponse,
    SoDoGheResponse,
    TraCuuChuyenParams,
)
from app.schemas.ve_schema import (
    BanVeHotlineRequest,
    BanVeTaiQuayRequest,
    CapNhatTrangThaiVeRequest,
    DatVeRequest,
    HuyGiuChoRequest,
    HuyVeNhanHoanRequest,
    LoaiHinhThanhToan,
    PhuongThucThanhToan,
    ThuTienTaiQuayRequest,
    TrangThaiVe,
    VeResponse,
)


def test_dat_ve_request_valid():
    req = DatVeRequest(
        chuyen_id=uuid.uuid4(),
        danh_sach_so_ghe=["A01", "A02"],
        diem_don_id=uuid.uuid4(),
        diem_tra_id=uuid.uuid4(),
        loai_hinh_thanh_toan=LoaiHinhThanhToan.THANH_TOAN_NGAY,
        ten_khach_vang_lai="Nguyen Van A",
        sdt_khach_vang_lai="0901234567",
    )
    assert len(req.danh_sach_so_ghe) == 2
    assert req.loai_hinh_thanh_toan == LoaiHinhThanhToan.THANH_TOAN_NGAY


def test_dat_ve_request_empty_seats_fails():
    with pytest.raises(ValidationError):
        DatVeRequest(
            chuyen_id=uuid.uuid4(),
            danh_sach_so_ghe=[],  # min_length=1
            diem_don_id=uuid.uuid4(),
            diem_tra_id=uuid.uuid4(),
            loai_hinh_thanh_toan=LoaiHinhThanhToan.THANH_TOAN_TAI_QUAY,
        )


def test_ve_response_valid():
    ve_id = uuid.uuid4()
    chuyen_id = uuid.uuid4()
    don_id = uuid.uuid4()
    tra_id = uuid.uuid4()
    now = datetime.now()

    ve = VeResponse(
        id=ve_id,
        chuyen_id=chuyen_id,
        so_ghe="B03",
        diem_don_id=don_id,
        diem_tra_id=tra_id,
        gia=Decimal("250000"),
        ma_dat_cho="DC123456",
        loai_hinh_thanh_toan=LoaiHinhThanhToan.THANH_TOAN_TAI_QUAY,
        trang_thai=TrangThaiVe.GIU_CHO,
        ngay_tao=now,
    )
    assert ve.so_ghe == "B03"
    assert ve.trang_thai == TrangThaiVe.GIU_CHO
    assert ve.la_ve_dat_coc is False


def test_ban_ve_tai_quay_request():
    req = BanVeTaiQuayRequest(
        chuyen_id=uuid.uuid4(),
        danh_sach_so_ghe=["A05"],
        diem_don_id=uuid.uuid4(),
        diem_tra_id=uuid.uuid4(),
        ten_khach="Tran Thi B",
        sdt_khach="0912345678",
        phuong_thuc_thanh_toan=PhuongThucThanhToan.TIEN_MAT,
    )
    assert req.phuong_thuc_thanh_toan == PhuongThucThanhToan.TIEN_MAT


def test_huy_ve_nhan_hoan_request():
    req = HuyVeNhanHoanRequest(
        ve_id=uuid.uuid4(),
        ly_do="Chuyến bị hoãn quá lâu (UC-41)",
        so_tai_khoan_nhan="1903456789",
        ten_ngan_hang_nhan="Techcombank",
        ten_chu_tai_khoan_nhan="NGUYEN VAN A",
    )
    assert req.so_tai_khoan_nhan == "1903456789"


def test_chuyen_schemas():
    c_id = uuid.uuid4()
    t_id = uuid.uuid4()
    now = datetime.now()

    chuyen = ChuyenXePublicResponse(
        chuyen_id=c_id,
        tuyen_id=t_id,
        ten_tuyen="Sài Gòn - Đà Lạt",
        gio_khoi_hanh=now,
        gio_den_du_kien=now,
        ten_loai_xe="Giường nằm 34 chỗ",
        so_cho=34,
        so_ghe_trong=20,
        gia_ve_tu=Decimal("280000"),
        dang_hoan=False,
        trang_thai="chua_khoi_hanh",
    )
    assert chuyen.so_ghe_trong == 20
    assert chuyen.dang_hoan is False
