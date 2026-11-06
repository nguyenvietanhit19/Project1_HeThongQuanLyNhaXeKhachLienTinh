"""Unit test báo lỗi trùng CCCD / số điện thoại khi tạo và sửa hồ sơ nhân sự (UC-49).

Trước đây trùng CCCD làm database ném lỗi, người dùng chỉ thấy "Đã có lỗi hệ thống". Giờ phải báo rõ trùng cái gì và trùng
với ai. Service dùng Repository giả (monkeypatch), không cần DB."""

from datetime import date
from types import SimpleNamespace

import psycopg2.errors
import pytest

from app.repositories import nhan_su_van_hanh_repository as repo
from app.services import ho_so_nhan_su_service as svc
from app.utils.loi import GiaTriLoi


def _du_lieu_tai_xe(**ghi_de):
    gia_tri = dict(
        ho_ten="Nguyễn Văn A", so_dien_thoai="0912345678", chuc_danh="tai_xe", nguoi_dung_id=None,
        so_cccd="012345678901", ngay_sinh=None, ngay_vao_lam=None,
        giay_to=[SimpleNamespace(loai="bang_lai", so_giay_to="1", hang="B2", ngay_cap=None, ngay_het_han=date(2035, 1, 1))],
    )
    gia_tri.update(ghi_de)
    return SimpleNamespace(**gia_tri)


def _gia_lap(monkeypatch, trung=None):
    """trung: {cot: dòng hồ sơ trùng}. Trả (danh sách lệnh đã gọi tao_ho_so)."""
    trung = trung or {}
    da_tao = []
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_trung", lambda cot, gia_tri, bo_qua_id=None: trung.get(cot))
    monkeypatch.setattr(svc.nhan_su_repo, "tao_ho_so", lambda *a: da_tao.append(a) or "id-moi")
    monkeypatch.setattr(svc, "_luu_giay_to", lambda *a: None)
    monkeypatch.setattr(svc, "_ghi_nhat_ky", lambda *a, **k: None)
    monkeypatch.setattr(svc, "xem_chi_tiet", lambda i: {"id": i})
    return da_tao


def test_tao_trung_cccd_bao_ro_trung_voi_ai(monkeypatch):
    da_tao = _gia_lap(monkeypatch, {"so_cccd": {"id": "x", "ma": "TX0001", "ho_ten": "Hoàng Văn Nghĩa", "chuc_danh": "tai_xe", "trang_thai": "dang_lam"}})
    with pytest.raises(GiaTriLoi) as e:
        svc.tao_ho_so("a1", "quan_ly_nhan_su", _du_lieu_tai_xe())
    assert "Số CCCD 012345678901 đã có trong hồ sơ của Hoàng Văn Nghĩa (TX0001)" in str(e.value)
    assert da_tao == []  # chặn trước khi ghi -> không cấp mã tài xế, không "đốt" số


def test_tao_trung_so_dien_thoai(monkeypatch):
    _gia_lap(monkeypatch, {"so_dien_thoai": {"id": "x", "ma": None, "ho_ten": "Trần B", "chuc_danh": "phu_xe", "trang_thai": "dang_lam"}})
    with pytest.raises(GiaTriLoi, match="Số điện thoại 0912345678 đã có trong hồ sơ của Trần B"):
        svc.tao_ho_so("a1", "quan_ly_nhan_su", _du_lieu_tai_xe())


def test_trung_voi_ho_so_da_nghi_viec_noi_ro(monkeypatch):
    _gia_lap(monkeypatch, {"so_cccd": {"id": "x", "ma": "TX0004", "ho_ten": "Lê C", "chuc_danh": "tai_xe", "trang_thai": "da_nghi_viec"}})
    with pytest.raises(GiaTriLoi, match="hồ sơ đã nghỉ việc"):
        svc.tao_ho_so("a1", "quan_ly_nhan_su", _du_lieu_tai_xe())


def test_khong_trung_thi_tao_binh_thuong(monkeypatch):
    da_tao = _gia_lap(monkeypatch)
    svc.tao_ho_so("a1", "quan_ly_nhan_su", _du_lieu_tai_xe())
    assert len(da_tao) == 1


def test_cccd_trong_khong_bi_kiem_tra_trung(monkeypatch):
    da_tao = _gia_lap(monkeypatch, {"so_cccd": {"id": "x", "ma": None, "ho_ten": "?", "chuc_danh": "tai_xe", "trang_thai": "dang_lam"}})
    svc.tao_ho_so("a1", "quan_ly_nhan_su", _du_lieu_tai_xe(so_cccd=None))
    assert len(da_tao) == 1


def _gia_lap_sua(monkeypatch, ho_so_cu, trung):
    da_hoi = []
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda i: ho_so_cu)
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_trung", lambda cot, gia_tri, bo_qua_id=None: da_hoi.append((cot, gia_tri, bo_qua_id)) or trung.get(cot))
    monkeypatch.setattr(svc.nhan_su_repo, "cap_nhat_ho_so", lambda *a: None)
    monkeypatch.setattr(svc, "_luu_giay_to", lambda *a: None)
    monkeypatch.setattr(svc, "_ghi_nhat_ky", lambda *a, **k: None)
    monkeypatch.setattr(svc, "xem_chi_tiet", lambda i: {"id": i})
    return da_hoi


HO_SO_CU = {"ho_ten": "A", "so_dien_thoai": "0911111111", "so_cccd": "111111111111", "ngay_sinh": None, "ngay_vao_lam": date(2026, 1, 1)}
DONG_TRUNG = {"id": "khac", "ma": "TX0002", "ho_ten": "Từ Anh Rừng", "chuc_danh": "tai_xe", "trang_thai": "dang_lam"}


def test_sua_doi_cccd_sang_so_da_co_bi_chan(monkeypatch):
    da_hoi = _gia_lap_sua(monkeypatch, HO_SO_CU, {"so_cccd": DONG_TRUNG})
    du_lieu = SimpleNamespace(ho_ten=None, so_dien_thoai=None, so_cccd="222222222222", ngay_sinh=None, ngay_vao_lam=None, giay_to=[])
    with pytest.raises(GiaTriLoi, match="Số CCCD 222222222222 đã có trong hồ sơ của Từ Anh Rừng"):
        svc.sua_ho_so("a1", "quan_ly_nhan_su", "id-dang-sua", du_lieu)
    assert da_hoi == [("so_cccd", "222222222222", "id-dang-sua")]  # bỏ qua chính hồ sơ đang sửa


def test_sua_giu_nguyen_cccd_khong_bi_chan_du_trung_du_lieu_cu(monkeypatch):
    da_hoi = _gia_lap_sua(monkeypatch, HO_SO_CU, {"so_cccd": DONG_TRUNG, "so_dien_thoai": DONG_TRUNG})
    du_lieu = SimpleNamespace(ho_ten="B", so_dien_thoai="0911111111", so_cccd="111111111111", ngay_sinh=None, ngay_vao_lam=None, giay_to=[])
    svc.sua_ho_so("a1", "quan_ly_nhan_su", "id-dang-sua", du_lieu)  # không raise
    assert da_hoi == []  # CCCD / SĐT không đổi -> không kiểm tra lại


def test_sua_doi_so_dien_thoai_trung_bi_chan(monkeypatch):
    _gia_lap_sua(monkeypatch, HO_SO_CU, {"so_dien_thoai": DONG_TRUNG})
    du_lieu = SimpleNamespace(ho_ten=None, so_dien_thoai="0987654321", so_cccd=None, ngay_sinh=None, ngay_vao_lam=None, giay_to=[])
    with pytest.raises(GiaTriLoi, match="Số điện thoại 0987654321"):
        svc.sua_ho_so("a1", "quan_ly_nhan_su", "id-dang-sua", du_lieu)


# ---------------------------------------------------------
# Lưới an toàn ở repository: 2 người lưu cùng lúc lọt qua bước kiểm tra -> database báo trùng -> vẫn phải ra câu rõ ràng
# ---------------------------------------------------------
def test_doi_loi_trung_cccd_o_repository():
    loi = psycopg2.errors.UniqueViolation()
    loi_diag = SimpleNamespace(constraint_name="nhan_su_van_hanh_so_cccd_duy_nhat")
    loi_gia = SimpleNamespace(diag=loi_diag)
    assert "Số CCCD này đã có" in str(repo._doi_loi_trung(loi_gia))
    assert isinstance(loi, psycopg2.errors.UniqueViolation)


def test_doi_loi_trung_khong_biet_ten_van_ra_cau_chung_khong_phai_loi_he_thong():
    loi_gia = SimpleNamespace(diag=SimpleNamespace(constraint_name="ten_la"))
    assert "trùng" in str(repo._doi_loi_trung(loi_gia))


def test_tim_ho_so_trung_chi_nhan_cot_co_dinh():
    with pytest.raises(ValueError):
        repo.tim_ho_so_trung("ho_ten; DROP TABLE nhan_su_van_hanh", "x")
