"""Vé chưa thanh toán tự hủy khi chuyến đã qua giờ khởi hành."""

from unittest.mock import MagicMock

from app.jobs import quet_ve_qua_gio_chay
from app.repositories import ve_lock_repository, ve_thanh_toan_repository, ve_repository


def _mock_connection(monkeypatch, module, rows=(), columns=()):
    cur = MagicMock()
    cur.description = [(column,) for column in columns]
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(module, "get_connection", lambda: conn)
    monkeypatch.setattr(module, "release_connection", lambda value: None)
    return conn, cur


def test_job_huy_ve_qua_gio_va_chi_bao_mot_lan_moi_luot(monkeypatch, da_gui_thong_bao):
    tickets = [
        {"id": "v1", "ma_dat_cho": "DC1", "so_ghe": "A1", "khach_hang_id": "kh1"},
        {"id": "v2", "ma_dat_cho": "DC1", "so_ghe": "A2", "khach_hang_id": "kh1"},
        {"id": "v3", "ma_dat_cho": "DC2", "so_ghe": "B1", "khach_hang_id": None},
    ]
    monkeypatch.setattr(quet_ve_qua_gio_chay.lock_repo, "huy_ve_chua_thanh_toan_qua_gio_chay", lambda: tickets)

    assert quet_ve_qua_gio_chay.chay() == 3
    assert len(da_gui_thong_bao) == 1
    assert da_gui_thong_bao[0][0] == "kh1"
    assert "DC1" in da_gui_thong_bao[0][1]
    assert "quá giờ khởi hành" in da_gui_thong_bao[0][1]


def test_sql_chi_huy_ve_giu_cho_qua_gio_khoi_hanh(monkeypatch):
    conn, cur = _mock_connection(
        monkeypatch, ve_lock_repository,
        rows=[("v1", "DC1", "A1", None)],
        columns=("id", "ma_dat_cho", "so_ghe", "khach_hang_id"),
    )

    assert len(ve_lock_repository.huy_ve_chua_thanh_toan_qua_gio_chay()) == 1
    query = cur.execute.call_args.args[0]
    assert "v.trang_thai = 'giu_cho'" in query
    assert "c.gio_khoi_hanh <= now()" in query
    assert "gio_huy = now()" in query
    conn.commit.assert_called_once()


def test_job_het_han_khong_nhan_mat_ve_da_qua_gio_chay(monkeypatch):
    _, cur = _mock_connection(monkeypatch, ve_lock_repository)

    ve_lock_repository.danh_dau_het_han_qua_han()
    assert "c.gio_khoi_hanh > now()" in cur.execute.call_args.args[0]


def test_thanh_toan_vnpay_va_tien_mat_chan_ve_qua_gio(monkeypatch):
    _, cur = _mock_connection(monkeypatch, ve_thanh_toan_repository)
    cur.rowcount = 0
    assert ve_thanh_toan_repository.ghi_nhan_thanh_toan_ve_le("VE1", "REF", "GD") == 0
    assert "c.gio_khoi_hanh > now()" in cur.execute.call_args.args[0]

    _, cur = _mock_connection(monkeypatch, ve_lock_repository)
    cur.rowcount = 0
    assert ve_lock_repository.thanh_toan_ve_quay("DC1", "VP1", "NV1", "tien_mat", 1) == 0
    assert "c.gio_khoi_hanh > now()" in cur.execute.call_args.args[0]


def test_no_show_chi_ap_dung_ve_da_thanh_toan(monkeypatch):
    _, cur = _mock_connection(monkeypatch, ve_repository)
    ve_repository.danh_dau_khong_den("v1")
    assert "trang_thai = 'da_thanh_toan'" in cur.execute.call_args.args[0]
