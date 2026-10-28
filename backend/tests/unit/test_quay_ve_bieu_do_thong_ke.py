"""Thống kê chi tiết và biểu đồ dùng cùng phạm vi văn phòng, ngày lập vé, mã vé."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.repositories import quay_ve_repository as repo
from app.services import quay_ve_service as service
from app.utils.loi import GiaTriLoi


def test_bieu_do_dien_ngay_khong_co_doanh_thu_va_loc_van_phong(monkeypatch):
    user = SimpleNamespace(van_phong_id="vp-a")
    monkeypatch.setattr(service, "lay_van_phong", lambda current: {"id": current.van_phong_id})
    called = []
    monkeypatch.setattr(service.repo, "bieu_do_doanh_thu", lambda *args: called.append(args) or [
        {"moc": date(2026, 10, 2), "so_ve": 2, "doanh_thu": 500000}
    ])

    result = service.bieu_do_doanh_thu(user, date(2026, 10, 1), date(2026, 10, 3), " VE001 ")
    assert result == {"nhom": "ngay", "diem": [
        {"moc": "2026-10-01", "so_ve": 0, "doanh_thu": 0},
        {"moc": "2026-10-02", "so_ve": 2, "doanh_thu": 500000},
        {"moc": "2026-10-03", "so_ve": 0, "doanh_thu": 0},
    ]}
    assert called == [("vp-a", date(2026, 10, 1), date(2026, 10, 3), "VE001", "day")]


def test_bieu_do_nhom_thang_cho_khoang_dai(monkeypatch):
    monkeypatch.setattr(service, "lay_van_phong", lambda _: {"id": "vp-a"})
    monkeypatch.setattr(service.repo, "bieu_do_doanh_thu", lambda *args: [
        {"moc": date(2026, 9, 1), "so_ve": 1, "doanh_thu": 200000}
    ])
    result = service.bieu_do_doanh_thu(object(), date(2026, 8, 20), date(2026, 10, 27))
    assert result["nhom"] == "thang"
    assert [point["moc"] for point in result["diem"]] == ["2026-08-01", "2026-09-01", "2026-10-01"]
    assert [point["doanh_thu"] for point in result["diem"]] == [0, 200000, 0]


def test_trang_thai_chi_tiet_gioi_han_va_loc_ma_ve(monkeypatch):
    monkeypatch.setattr(service, "lay_van_phong", lambda _: {"id": "vp-a"})
    called = []
    monkeypatch.setattr(service.repo, "ve_theo_trang_thai", lambda *args: called.append(args) or {"ve": []})
    result = service.ve_theo_trang_thai(object(), "giu_cho", date(2026, 10, 1), date(2026, 10, 27), 2, 10, " VE001 ")
    assert result == {"ve": []}
    assert called == [("vp-a", "giu_cho", date(2026, 10, 1), date(2026, 10, 27), 2, 10, "VE001")]
    with pytest.raises(GiaTriLoi):
        service.ve_theo_trang_thai(object(), "da_thanh_toan", date(2026, 10, 1), date(2026, 10, 27))
    with pytest.raises(GiaTriLoi):
        service.bieu_do_doanh_thu(object(), date(2026, 10, 27), date(2026, 10, 1))


def test_sql_bieu_do_va_danh_sach_trang_thai_cung_bo_loc(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (1,)
    cur.description = [("moc",), ("so_ve",), ("doanh_thu",)]
    cur.fetchall.return_value = [(date(2026, 10, 2), 1, 200000)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(repo, "get_connection", lambda: conn)
    monkeypatch.setattr(repo, "release_connection", lambda _: None)

    repo.bieu_do_doanh_thu("vp-a", date(2026, 10, 1), date(2026, 10, 27), "VE001", "day")
    sql, params = cur.execute.call_args.args
    assert "v.diem_don_id = %s" in sql and "v.ngay_tao" in sql
    assert "v.ma_ve ILIKE %s::text" in sql and "v.trang_thai IN" in sql
    assert params == ("vp-a", date(2026, 10, 1), date(2026, 10, 27), "VE001", "%VE001%")

    repo.ve_theo_trang_thai("vp-a", "da_huy", date(2026, 10, 1), date(2026, 10, 27), 2, 10, "VE001")
    count_sql, count_params = cur.execute.call_args_list[1].args
    list_sql, list_params = cur.execute.call_args_list[2].args
    assert "v.diem_don_id = %s AND v.trang_thai = %s" in count_sql
    assert "v.ngay_tao" in count_sql and "v.ma_ve ILIKE %s::text" in count_sql
    assert count_params == ("vp-a", "da_huy", date(2026, 10, 1), date(2026, 10, 27), "VE001", "%VE001%")
    assert "LIMIT %s OFFSET %s" in list_sql and list_params[-2:] == (10, 10)


def test_kenh_ban_chi_dem_ve_da_thanh_toan_nhu_doanh_thu(monkeypatch):
    cur = MagicMock()
    cur.description = [("so_ve_da_ban",)]
    cur.fetchall.return_value = [(0,)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(repo, "get_connection", lambda: conn)
    monkeypatch.setattr(repo, "release_connection", lambda _: None)
    repo.thong_ke("vp-a", date(2026, 10, 1), date(2026, 10, 27))
    sql = cur.execute.call_args.args[0]
    for channel in ("tai_quay", "hotline", "IS NULL"):
        assert "v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den') AND v.kenh_ban " + ("= '" + channel + "'" if channel != "IS NULL" else channel) in sql
