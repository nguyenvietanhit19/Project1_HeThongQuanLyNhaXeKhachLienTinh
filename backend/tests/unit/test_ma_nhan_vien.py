"""Unit test mã nhân viên (KE_HOACH_MA_NHAN_VIEN.md): hàm dựng mã (utils/ma_tu_sinh.py) và hàm cấp mã
(repositories/ma_repository.py) — không cần DB, cursor giả."""

import re
from pathlib import Path

import pytest

from app.repositories import ma_repository
from app.utils import ma_tu_sinh as ma

TAT_CA_VAI_TRO = [
    "tai_xe", "phu_xe", "nhan_vien_quay_ve", "nhan_vien_gui_hang",
    "dieu_do_vien", "ke_toan", "quan_ly_nhan_su", "quan_ly",
]
THU_MUC_MIGRATION = Path(__file__).resolve().parents[2] / "migrations"


# ---------------------------------------------------------
# Hàm dựng mã
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "vai_tro, so, mong_doi",
    [
        ("tai_xe", 1, "TX0001"),
        ("phu_xe", 1, "PX0001"),
        ("nhan_vien_quay_ve", 7, "QV0007"),
        ("nhan_vien_gui_hang", 25, "GH0025"),
        ("dieu_do_vien", 12, "DDV0012"),
        ("ke_toan", 300, "KT0300"),
        ("quan_ly_nhan_su", 1, "NS0001"),
        ("quan_ly", 1, "QL0001"),
    ],
)
def test_dinh_dang_tien_to_va_4_chu_so(vai_tro, so, mong_doi):
    assert ma.ma_nhan_vien(vai_tro, so) == mong_doi


def test_moi_vai_tro_co_dung_mot_tien_to_va_tien_to_khong_trung():
    assert set(ma.TIEN_TO_NHAN_VIEN) == set(TAT_CA_VAI_TRO)
    tien_to = list(ma.TIEN_TO_NHAN_VIEN.values())
    assert len(set(tien_to)) == len(tien_to)


@pytest.mark.parametrize(
    "so, mong_doi",
    [(9999, "PX9999"), (10000, "PX10000"), (123456, "PX123456")],
)
def test_so_qua_9999_dai_ra_khong_bi_cat(so, mong_doi):
    # lpad() của Postgres cắt "10000" thành "1000" → trùng mã; ở đây không cắt
    assert ma.ma_nhan_vien("phu_xe", so) == mong_doi


def test_ma_lien_tiep_qua_moc_khong_trung():
    assert ma.ma_nhan_vien("phu_xe", 9999) != ma.ma_nhan_vien("phu_xe", 10000)


def test_khach_hang_va_vai_tro_la_khong_co_ma():
    for vai_tro in ("khach_hang", "", "admin", "PHU_XE"):
        with pytest.raises(ValueError, match="không có mã nhân viên"):
            ma.ma_nhan_vien(vai_tro, 1)


@pytest.mark.parametrize("so", [0, -1])
def test_so_thu_tu_phai_tu_1_vi_0_danh_cho_tai_khoan_goc(so):
    with pytest.raises(ValueError, match="bắt đầu từ 1"):
        ma.ma_nhan_vien("quan_ly", so)


def test_ma_quan_ly_goc_khong_bao_gio_do_sinh_tu_dong_sinh_ra():
    assert ma.MA_QUAN_LY_GOC == "QL0000"
    for so in range(1, 50):
        assert ma.ma_nhan_vien("quan_ly", so) != ma.MA_QUAN_LY_GOC


@pytest.mark.parametrize("vai_tro", TAT_CA_VAI_TRO)
def test_ma_sinh_ra_khop_dinh_dang_check_cua_migration(vai_tro):
    # Cùng biểu thức chính quy với CHECK trong migration: ^<TIỀN TỐ>[0-9]{4,}$
    for so in (1, 9999, 10000):
        assert re.fullmatch(rf"{ma.TIEN_TO_NHAN_VIEN[vai_tro]}[0-9]{{4,}}", ma.ma_nhan_vien(vai_tro, so))


# ---------------------------------------------------------
# Hàm cấp mã (cursor giả)
# ---------------------------------------------------------
class CursorGia:
    def __init__(self, so_tra_ve=1):
        self.cau_lenh = []
        self._so = so_tra_ve

    def execute(self, sql, *_):
        self.cau_lenh.append(sql)

    def fetchone(self):
        return (self._so,)


@pytest.mark.parametrize(
    "vai_tro, ten_sequence, so, mong_doi",
    [
        ("tai_xe", "seq_ma_tai_xe", 3, "TX0003"),
        ("phu_xe", "seq_ma_phu_xe", 7, "PX0007"),
        ("nhan_vien_quay_ve", "seq_ma_quay_ve", 1, "QV0001"),
        ("nhan_vien_gui_hang", "seq_ma_gui_hang", 12, "GH0012"),
        ("dieu_do_vien", "seq_ma_dieu_do_vien", 5, "DDV0005"),
        ("ke_toan", "seq_ma_ke_toan", 2, "KT0002"),
        ("quan_ly_nhan_su", "seq_ma_quan_ly_nhan_su", 2, "NS0002"),
        ("quan_ly", "seq_ma_quan_ly", 1, "QL0001"),
    ],
)
def test_cap_ma_lay_dung_sequence_cua_vai_tro(vai_tro, ten_sequence, so, mong_doi):
    cur = CursorGia(so_tra_ve=so)
    assert ma_repository.cap_ma_nhan_vien(cur, vai_tro) == mong_doi
    assert cur.cau_lenh == [f"SELECT nextval('{ten_sequence}')"]


@pytest.mark.parametrize("vai_tro", ["khach_hang", "", "khong_biet"])
def test_vai_tro_khong_co_ma_bi_tu_choi_truoc_khi_lay_so(vai_tro):
    cur = CursorGia()
    with pytest.raises(ValueError):
        ma_repository.cap_ma_nhan_vien(cur, vai_tro)
    assert cur.cau_lenh == []  # không gọi nextval nên không làm mất số


def test_khong_lam_hong_cac_sequence_cu():
    for loai, ten in {"khu_vuc": "seq_ma_khu_vuc", "tuyen": "seq_ma_tuyen", "loai_xe": "seq_ma_loai_xe", "ve": "ve_ma_seq"}.items():
        cur = CursorGia(so_tra_ve=5)
        assert ma_repository.so_tiep_theo(cur, loai) == 5
        assert cur.cau_lenh == [f"SELECT nextval('{ten}')"]


def test_ten_sequence_trong_code_khop_voi_migration():
    """Đổi tên sequence ở một bên mà quên bên kia sẽ làm tạo tài khoản lỗi 500 — bắt ngay ở đây."""
    sql = (THU_MUC_MIGRATION / "20261105_0900_ma_nhan_vien.sql").read_text(encoding="utf-8")
    trong_migration = set(re.findall(r"CREATE SEQUENCE (seq_ma_\w+);", sql))
    trong_code = {ma_repository._SEQUENCE[vt] for vt in TAT_CA_VAI_TRO}
    assert trong_migration == trong_code
    assert len(trong_code) == len(TAT_CA_VAI_TRO)  # mỗi vai trò một sequence riêng


def test_tien_to_trong_code_khop_voi_migration():
    sql = (THU_MUC_MIGRATION / "20261105_0900_ma_nhan_vien.sql").read_text(encoding="utf-8")
    for vai_tro, tien_to in ma.TIEN_TO_NHAN_VIEN.items():
        if vai_tro == "tai_xe":
            assert f"^{tien_to}[0-9]{{4,}}$" in sql and "'TX' ||" in sql
        else:
            assert f"'{vai_tro}'" in sql and (f"'{tien_to}'" in sql or f"^{tien_to}[0-9]" in sql)
