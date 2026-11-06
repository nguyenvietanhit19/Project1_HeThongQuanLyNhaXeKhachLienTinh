"""Phụ xe KHÔNG được tự sửa họ tên / số điện thoại (hai thông tin này nằm cả ở hồ sơ nhân sự, chỉ Quản lý nhân sự sửa)
và khi QLNS sửa hồ sơ phụ xe thì tài khoản đổi theo cùng một transaction. Repository dùng kết nối giả, không cần DB."""

import pytest

from app.repositories import nhan_su_van_hanh_repository as repo
from app.services import mat_khau_service as svc
from app.utils.loi import CamTruyCap


def _gia_lap(monkeypatch):
    da_ghi = []
    monkeypatch.setattr(svc.repo, "cap_nhat_ho_ten", lambda i, v: da_ghi.append(("ho_ten", v)))
    monkeypatch.setattr(svc.repo, "cap_nhat_so_dien_thoai", lambda i, v: da_ghi.append(("sdt", v)))
    return da_ghi


@pytest.mark.parametrize("truong", [{"ho_ten": "Tên mới"}, {"so_dien_thoai": "0912345678"}, {"ho_ten": "A", "so_dien_thoai": "0912345678"}])
def test_phu_xe_khong_tu_sua_duoc(monkeypatch, truong):
    da_ghi = _gia_lap(monkeypatch)
    with pytest.raises(CamTruyCap, match="Quản lý nhân sự"):
        svc.sua_ho_so("u1", vai_tro="phu_xe", **truong)
    assert da_ghi == []


@pytest.mark.parametrize("vai_tro", ["khach_hang", "quan_ly", "quan_ly_nhan_su", "nhan_vien_quay_ve", "dieu_do_vien", None])
def test_vai_tro_khac_van_tu_sua_duoc(monkeypatch, vai_tro):
    da_ghi = _gia_lap(monkeypatch)
    svc.sua_ho_so("u1", ho_ten="Tên mới", vai_tro=vai_tro)
    assert da_ghi == [("ho_ten", "Tên mới")]


class CursorGia:
    def __init__(self, nhat_ky):
        self.nhat_ky = nhat_ky

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        return False

    def execute(self, sql, tham_so=None):
        self.nhat_ky.append((" ".join(sql.split()), tham_so))


class KetNoiGia:
    def __init__(self):
        self.nhat_ky, self.da_commit = [], False

    def cursor(self):
        return CursorGia(self.nhat_ky)

    def commit(self):
        self.da_commit = True

    def rollback(self):
        pass


def test_sua_ho_so_dong_bo_ho_ten_sdt_sang_tai_khoan_cung_transaction(monkeypatch):
    kn = KetNoiGia()
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    repo.cap_nhat_ho_so("hs1", "Tên mới", "0912345678", None, None, None)
    cau_lenh = [sql for sql, _ in kn.nhat_ky]
    assert cau_lenh[0].startswith("UPDATE nhan_su_van_hanh")
    assert cau_lenh[1].startswith("UPDATE nguoi_dung SET ho_ten = %s, so_dien_thoai = %s")
    assert "SELECT nguoi_dung_id FROM nhan_su_van_hanh WHERE id = %s" in cau_lenh[1]  # tài xế (không tài khoản) -> không dòng nào đổi
    assert kn.da_commit and len(cau_lenh) == 2  # một lần commit cho cả hai bảng
