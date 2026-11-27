"""Vé giữ chỗ khi chuyến trễ giờ (không còn job hủy vé theo giờ khởi hành, NGHIEP_VU.md mục 8.2 điểm 6)."""

from unittest.mock import MagicMock

from app.repositories import ve_lock_repository, ve_repository, ve_thanh_toan_repository


def _mock_connection(monkeypatch, module):
    cur = MagicMock()
    cur.fetchall.return_value = []
    cur.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(module, "get_connection", lambda: conn)
    monkeypatch.setattr(module, "release_connection", lambda value: None)
    return cur


def test_thu_tien_mat_tai_quay_khong_chan_theo_gio_khoi_hanh(monkeypatch):
    cur = _mock_connection(monkeypatch, ve_lock_repository)
    ve_lock_repository.thanh_toan_ve_quay("DC1", "VP1", "NV1", "tien_mat", 1)
    sql = cur.execute.call_args.args[0]
    assert "gio_khoi_hanh" not in sql
    assert "c.trang_thai NOT IN ('hoan_thanh', 'da_huy')" in sql and "v.trang_thai = 'giu_cho'" in sql


def test_ve_giu_tam_het_han_duoc_don_ca_khi_chuyen_da_qua_gio(monkeypatch):
    cur = _mock_connection(monkeypatch, ve_lock_repository)
    ve_lock_repository.danh_dau_het_han_qua_han()
    sql = cur.execute.call_args.args[0]
    assert "gio_khoi_hanh" not in sql and "han_giu_cho_den <= now()" in sql


def test_thanh_toan_vnpay_ve_le_van_chan_ve_qua_gio(monkeypatch):
    cur = _mock_connection(monkeypatch, ve_thanh_toan_repository)
    assert ve_thanh_toan_repository.ghi_nhan_thanh_toan_ve_le("VE1", "REF", "GD") == 0
    assert "c.gio_khoi_hanh > now()" in cur.execute.call_args.args[0]


def test_khong_den_ap_dung_ve_da_tra_va_ve_tra_tai_quay_chua_tra(monkeypatch):
    cur = _mock_connection(monkeypatch, ve_repository)
    assert ve_repository.danh_dau_khong_den("v1") is False
    sql = cur.execute.call_args.args[0]
    assert "trang_thai = 'da_thanh_toan'" in sql and "han_giu_cho_den IS NULL" in sql
