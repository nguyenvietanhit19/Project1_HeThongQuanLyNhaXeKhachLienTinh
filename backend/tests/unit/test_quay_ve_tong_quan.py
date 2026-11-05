"""Chi tiết bốn ô tổng quan phải đúng phạm vi văn phòng và ngày hiển thị."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.repositories import quay_ve_repository as repo
from app.services import quay_ve_service as service


def test_danh_sach_ve_da_huy_chi_dung_van_phong_nhan_vien(monkeypatch):
    user = SimpleNamespace(van_phong_id="vp-1")
    monkeypatch.setattr(service, "lay_van_phong", lambda current: {"id": current.van_phong_id})
    called = []
    monkeypatch.setattr(service.repo, "ve_da_huy", lambda *args: called.append(args) or {"ve": []})

    assert service.ve_da_huy(user, date(2026, 10, 27), 2, 10) == {"ve": []}
    assert called == [("vp-1", date(2026, 10, 27), 2, 10)]


def test_sql_ve_da_huy_loc_dung_ngay_lap_va_phan_trang(monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = (3,)
    cur.description = [("ma_ve",)]
    cur.fetchall.return_value = [("VE1",)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(repo, "get_connection", lambda: conn)
    monkeypatch.setattr(repo, "release_connection", lambda _: None)

    result = repo.ve_da_huy("vp-1", date(2026, 10, 27), 2, 2)
    assert result == {"tong_so": 3, "trang": 2, "kich_thuoc_trang": 2, "ve": [{"ma_ve": "VE1"}]}
    count_sql, count_params = cur.execute.call_args_list[0].args
    list_sql, list_params = cur.execute.call_args_list[1].args
    assert "v.diem_don_id = %s" in count_sql and "v.trang_thai = 'da_huy'" in count_sql
    assert "v.ngay_tao" in count_sql and "Asia/Ho_Chi_Minh" in count_sql
    assert "v.gio_huy" in list_sql and "LIMIT %s OFFSET %s" in list_sql
    assert count_params == ("vp-1", date(2026, 10, 27), date(2026, 10, 27))
    assert list_params[-2:] == (2, 2)


def test_sql_thong_ke_co_chi_tiet_doanh_thu_theo_phuong_thuc(monkeypatch):
    cur = MagicMock()
    cur.description = [("doanh_thu",)]
    cur.fetchall.return_value = [(300000,)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(repo, "get_connection", lambda: conn)
    monkeypatch.setattr(repo, "release_connection", lambda _: None)

    repo.thong_ke("vp-1", date(2026, 10, 27), date(2026, 10, 27))
    sql = cur.execute.call_args.args[0]
    assert "AS doanh_thu_tien_mat" in sql
    assert "AS doanh_thu_chuyen_khoan" in sql
    assert "v.diem_don_id = %s" in sql
