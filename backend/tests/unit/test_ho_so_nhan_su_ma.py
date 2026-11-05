"""Unit test mã nhân viên ở hồ sơ nhân sự (UC-49) — KE_HOACH_MA_NHAN_VIEN.md mục 3.2.

Tài xế: hồ sơ có mã riêng TX... (cấp trong cùng transaction khi tạo). Phụ xe: hồ sơ KHÔNG có mã riêng, lấy mã của
tài khoản liên kết. Repository dùng kết nối giả, không cần DB."""

from datetime import date
from uuid import uuid4

import pytest

from app.repositories import nhan_su_van_hanh_repository as repo
from app.schemas.nhan_su_schema import HoSoNhanSuResponse, HoSoTomTatResponse, TaiKhoanPhuXeResponse
from app.services import ho_so_nhan_su_service as svc


# ---------------------------------------------------------
# Kết nối giả cho repository
# ---------------------------------------------------------
class CursorGia:
    def __init__(self, nhat_ky, so_tra_ve):
        self.nhat_ky = nhat_ky
        self.so_tra_ve = so_tra_ve
        self._cuoi = ""

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        return False

    def execute(self, sql, tham_so=None):
        self._cuoi = sql
        self.nhat_ky.append((sql, tham_so))

    def fetchone(self):
        return (self.so_tra_ve,) if "nextval" in self._cuoi else ("id-ho-so",)


class KetNoiGia:
    def __init__(self, so_tra_ve=3):
        self.nhat_ky = []
        self.so_tra_ve = so_tra_ve
        self.da_commit = False

    def cursor(self):
        return CursorGia(self.nhat_ky, self.so_tra_ve)

    def commit(self):
        self.da_commit = True

    def rollback(self):
        pass


@pytest.fixture
def ket_noi(monkeypatch):
    kn = KetNoiGia()
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    return kn


def _tao(chuc_danh, nguoi_dung_id=None):
    return repo.tao_ho_so("A", "0912345678", chuc_danh, nguoi_dung_id, None, None, None)


# ---------------------------------------------------------
# Repository: cấp mã khi tạo hồ sơ
# ---------------------------------------------------------
def test_tai_xe_duoc_cap_ma_tx_trong_cung_transaction(ket_noi):
    assert _tao("tai_xe") == "id-ho-so"
    cau_lenh = [sql for sql, _ in ket_noi.nhat_ky]
    assert "nextval('seq_ma_tai_xe')" in cau_lenh[0]  # lấy số trước, rồi mới INSERT
    assert cau_lenh[1].lstrip().startswith("INSERT INTO nhan_su_van_hanh")
    tham_so = ket_noi.nhat_ky[1][1]
    assert tham_so[-1] == "TX0003"  # mã là tham số cuối của INSERT
    assert ket_noi.da_commit  # một lần commit duy nhất cho cả lấy số và INSERT


def test_phu_xe_khong_co_ma_rieng_va_khong_lay_so(ket_noi):
    _tao("phu_xe", str(uuid4()))
    cau_lenh = [sql for sql, _ in ket_noi.nhat_ky]
    assert len(cau_lenh) == 1 and "nextval" not in cau_lenh[0]
    assert ket_noi.nhat_ky[0][1][-1] is None


def test_ma_tx_theo_so_cua_sequence(monkeypatch):
    kn = KetNoiGia(so_tra_ve=12)
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    _tao("tai_xe")
    assert kn.nhat_ky[1][1][-1] == "TX0012"


def test_loi_khi_insert_thi_rollback_khong_commit(monkeypatch):
    kn = KetNoiGia()

    class CursorLoi(CursorGia):
        def execute(self, sql, tham_so=None):
            super().execute(sql, tham_so)
            if sql.lstrip().startswith("INSERT"):
                raise RuntimeError("loi insert")

    kn.cursor = lambda: CursorLoi(kn.nhat_ky, kn.so_tra_ve)
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    with pytest.raises(RuntimeError):
        _tao("tai_xe")
    assert not kn.da_commit


# ---------------------------------------------------------
# Câu SQL đọc: lấy mã từ hồ sơ hoặc từ tài khoản
# ---------------------------------------------------------
def _sql_da_chay(monkeypatch, ham, *args):
    kn = KetNoiGia()

    class CursorDoc(CursorGia):
        description = [("id",)]

        def fetchone(self):
            return None

        def fetchall(self):
            return []

    kn.cursor = lambda: CursorDoc(kn.nhat_ky, 0)
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    ham(*args)
    return " ".join(kn.nhat_ky[0][0].split())


def test_chi_tiet_va_danh_sach_lay_ma_tu_ho_so_hoac_tai_khoan_lien_ket(monkeypatch):
    for sql in (
        _sql_da_chay(monkeypatch, repo.tim_ho_so_day_du, str(uuid4())),
        _sql_da_chay(monkeypatch, repo.danh_sach_ho_so),
    ):
        assert "COALESCE(n.ma, nd.ma) AS ma" in sql
        assert "LEFT JOIN nguoi_dung nd ON nd.id = n.nguoi_dung_id" in sql


def test_danh_sach_chi_dang_lam_van_loc_dung_va_khong_loi_alias(monkeypatch):
    sql = _sql_da_chay(monkeypatch, repo.danh_sach_ho_so, True)
    assert "WHERE n.trang_thai = 'dang_lam'" in sql and "ORDER BY n.chuc_danh, n.ho_ten" in sql


def test_o_chon_tai_khoan_phu_xe_tra_ma(monkeypatch):
    sql = _sql_da_chay(monkeypatch, repo.danh_sach_tai_khoan_phu_xe_chua_gan)
    assert sql.startswith("SELECT nd.id, nd.ma,")


# ---------------------------------------------------------
# Service + schema: mã đi hết đường ra API
# ---------------------------------------------------------
def test_service_danh_sach_giu_nguyen_ma(monkeypatch):
    ds = [{"id": uuid4(), "ma": "PX0001", "ho_ten": "A", "so_dien_thoai": "0912345678", "chuc_danh": "phu_xe", "nguoi_dung_id": uuid4(), "trang_thai": "dang_lam"},
          {"id": uuid4(), "ma": "TX0001", "ho_ten": "B", "so_dien_thoai": "0912345678", "chuc_danh": "tai_xe", "nguoi_dung_id": None, "trang_thai": "dang_lam"}]
    monkeypatch.setattr(svc.nhan_su_repo, "danh_sach_ho_so", lambda chi_dang_lam=False: ds)
    ket_qua = [HoSoTomTatResponse(**h) for h in svc.danh_sach_ho_so()]
    assert [(h.chuc_danh, h.ma, h.co_tai_khoan) for h in ket_qua] == [("phu_xe", "PX0001", True), ("tai_xe", "TX0001", False)]


def test_schema_cho_phep_ho_so_chua_co_ma():
    h = HoSoTomTatResponse(id=uuid4(), ho_ten="A", so_dien_thoai="0912345678", chuc_danh="phu_xe", trang_thai="dang_lam", co_tai_khoan=False)
    assert h.ma is None
    chi_tiet = HoSoNhanSuResponse(
        id=uuid4(), ho_ten="A", so_dien_thoai="0912345678", chuc_danh="tai_xe", nguoi_dung_id=None, so_cccd=None,
        ngay_sinh=None, ngay_vao_lam=date.today(), trang_thai="dang_lam", ngay_nghi_viec=None, ly_do_nghi_viec=None,
    )
    assert chi_tiet.ma is None


def test_schema_chi_tiet_va_tai_khoan_phu_xe_nhan_ma():
    chi_tiet = HoSoNhanSuResponse(
        id=uuid4(), ma="PX0007", ho_ten="A", so_dien_thoai="0912345678", chuc_danh="phu_xe", nguoi_dung_id=uuid4(), so_cccd=None,
        ngay_sinh=None, ngay_vao_lam=date.today(), trang_thai="dang_lam", ngay_nghi_viec=None, ly_do_nghi_viec=None,
    )
    assert chi_tiet.ma == "PX0007"
    assert TaiKhoanPhuXeResponse(id=uuid4(), ma="PX0007", ho_ten="A", email="a@t.vn").ma == "PX0007"
    assert TaiKhoanPhuXeResponse(id=uuid4(), ho_ten="A", email="a@t.vn").ma is None


# ---- Phụ xe: tài khoản đã khóa; nhật ký của quan_ly ----
def test_tai_khoan_phu_xe_da_khoa_bi_tu_choi(monkeypatch):
    from app.services import ho_so_nhan_su_service as svc
    from app.utils.loi import GiaTriLoi

    monkeypatch.setattr(svc.nguoi_dung_repo, "tim_theo_id", lambda _id: {"vai_tro": "phu_xe", "dang_hoat_dong": False})
    with pytest.raises(GiaTriLoi, match="khóa"):
        svc._kiem_tra_tai_khoan_phu_xe("x")


def test_nhat_ky_ho_so_theo_vai_tro_khong_ghi_cheo(monkeypatch):
    from app.services import ho_so_nhan_su_service as svc

    qlns, admin = [], []
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: qlns.append(a))
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: admin.append(a))
    svc._ghi_nhat_ky("a", "quan_ly", "tao_ho_so_nhan_su", "n")
    assert len(admin) == 1 and qlns == []
    svc._ghi_nhat_ky("b", "quan_ly_nhan_su", "tao_ho_so_nhan_su", "n")
    assert len(admin) == 1 and len(qlns) == 1
