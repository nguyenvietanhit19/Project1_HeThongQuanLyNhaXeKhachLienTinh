"""Lịch sử vé đã bán phải dùng đúng phạm vi văn phòng và khoảng ngày thống kê."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import quay_ve_service as service
from app.utils.loi import GiaTriLoi


def test_thong_ke_loc_ma_ve_cung_khoang_ngay(monkeypatch):
    user = SimpleNamespace(van_phong_id="van-phong-a")
    monkeypatch.setattr(service, "lay_van_phong", lambda current: {"id": current.van_phong_id})
    called = []
    expected = {"so_ve_da_ban": 1, "doanh_thu": 500000}
    monkeypatch.setattr(service.repo, "thong_ke", lambda *args: called.append(args) or expected)

    start, end = date(2026, 10, 1), date(2026, 10, 31)
    assert service.thong_ke(user, start, end, "  VE000015  ") == expected
    assert called == [("van-phong-a", start, end, "VE000015")]


@pytest.mark.parametrize(
    ("ma_ve", "expected_pattern"),
    [("VE000015", "%VE000015%"), (None, None)],
)
def test_truy_van_thong_ke_loc_ma_ve_trong_van_phong(monkeypatch, ma_ve, expected_pattern):
    cur = MagicMock()
    cur.description = [("so_ve_da_ban",), ("doanh_thu",)]
    cur.fetchall.return_value = [(1, 500000)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(service.repo, "get_connection", lambda: conn)
    release = MagicMock()
    monkeypatch.setattr(service.repo, "release_connection", release)

    start, end = date(2026, 10, 1), date(2026, 10, 31)
    assert service.repo.thong_ke("van-phong-a", start, end, ma_ve)["so_ve_da_ban"] == 1
    query, params = cur.execute.call_args.args
    assert "v.diem_don_id = %s" in query
    assert "v.ma_ve ILIKE %s::text" in query
    assert params == ("van-phong-a", start, end, ma_ve, expected_pattern)
    release.assert_called_once_with(conn)


def test_lich_su_ban_ve_chi_lay_van_phong_cua_nhan_vien(monkeypatch):
    user = SimpleNamespace(van_phong_id="van-phong-a")
    monkeypatch.setattr(service, "lay_van_phong", lambda current: {"id": current.van_phong_id})
    called = []
    expected = {"tong_so": 1, "trang": 2, "kich_thuoc_trang": 10, "ve": []}
    monkeypatch.setattr(
        service.repo,
        "lich_su_ban_ve",
        lambda *args: called.append(args) or expected,
    )

    start, end = date(2026, 10, 1), date(2026, 10, 31)
    assert service.lich_su_ban_ve(user, start, end, 2, 10) == expected
    assert called == [("van-phong-a", start, end, 2, 10, None)]


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 10, 2), date(2026, 10, 1)),
        (date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=367)),
    ],
)
def test_lich_su_ban_ve_chan_khoang_ngay_khong_hop_le(start, end, monkeypatch):
    monkeypatch.setattr(service.repo, "lich_su_ban_ve", lambda *_: pytest.fail("Không được truy vấn DB"))
    with pytest.raises(GiaTriLoi):
        service.lich_su_ban_ve(SimpleNamespace(van_phong_id="van-phong-a"), start, end)
