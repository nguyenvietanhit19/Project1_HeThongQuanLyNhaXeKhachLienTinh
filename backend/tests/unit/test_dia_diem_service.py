"""Unit test cho UC-30 (điểm đón/trả) — giả lập Repository bằng monkeypatch."""

import pytest

from app.services import dia_diem_service as dd
from app.utils.loi import GiaTriLoi


def _diem(khu_vuc_id="kv-1"):
    return {"id": "d-1", "khu_vuc_id": khu_vuc_id, "ten": "Bến A", "dia_chi": "x", "loai": "diem_dung"}


def test_sua_diem_doi_khu_vuc_bi_chan(monkeypatch):
    monkeypatch.setattr(dd.repo, "tim_diem_don_tra_theo_id", lambda _id: _diem("kv-1"))
    da_ghi = []
    monkeypatch.setattr(dd.repo, "sua_diem_don_tra", lambda *a: da_ghi.append(a))
    with pytest.raises(GiaTriLoi, match="đổi khu vực"):
        dd.sua_diem_don_tra("d-1", "kv-2", "Bến A", "x", "diem_dung")
    assert da_ghi == []


def test_sua_diem_giu_nguyen_khu_vuc_van_sua_duoc(monkeypatch):
    monkeypatch.setattr(dd.repo, "tim_diem_don_tra_theo_id", lambda _id: _diem("kv-1"))
    da_ghi = []
    monkeypatch.setattr(dd.repo, "sua_diem_don_tra", lambda *a: da_ghi.append(a))
    dd.sua_diem_don_tra("d-1", "kv-1", "Bến B", "y", "diem_dung")
    assert len(da_ghi) == 1


def test_sua_diem_khong_ton_tai(monkeypatch):
    monkeypatch.setattr(dd.repo, "tim_diem_don_tra_theo_id", lambda _id: None)
    with pytest.raises(GiaTriLoi, match="Không tìm thấy"):
        dd.sua_diem_don_tra("d-x", "kv-1", "B", "y", "diem_dung")
