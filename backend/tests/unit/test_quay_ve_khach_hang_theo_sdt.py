"""Tên người mua tại quầy được cố định theo số điện thoại đã lưu."""

from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.schemas.quay_ve_schema import BanVeRequest
from app.services import quay_ve_service as service
from app.utils.loi import GiaTriLoi


PHONE = "0912345678"


def test_tra_cuu_uu_tien_tai_khoan(monkeypatch):
    account = {"id": "account-1", "ho_ten": "Nguyễn An", "so_dien_thoai": PHONE}
    monkeypatch.setattr(service.repo, "khach_hang_theo_sdt", lambda phone: account)
    monkeypatch.setattr(service.repo, "khach_vang_lai_theo_sdt", lambda phone: pytest.fail("Không tra vé cũ"))

    assert service.tim_khach_hang(PHONE) == {**account, "nguon": "tai_khoan"}


def test_tra_cuu_lay_khach_tu_ve_cu(monkeypatch):
    monkeypatch.setattr(service.repo, "khach_hang_theo_sdt", lambda phone: None)
    monkeypatch.setattr(service.repo, "khach_vang_lai_theo_sdt", lambda phone: {"ho_ten": "Trần Bình"})

    assert service.tim_khach_hang(PHONE) == {"id": None, "ho_ten": "Trần Bình", "nguon": "lich_su"}


@pytest.mark.parametrize(
    ("account", "guest", "entered", "expected_name", "expected_id"),
    [
        ({"id": "account-1", "ho_ten": "Nguyễn An"}, None, "Tên khác", "Nguyễn An", "account-1"),
        (None, {"ho_ten": "Trần Bình"}, "Tên khác", "Trần Bình", None),
        (None, None, "  Lê   Cường  ", "Lê Cường", None),
    ],
)
def test_ban_ve_luon_dung_ten_da_luu(monkeypatch, account, guest, entered, expected_name, expected_id):
    user = SimpleNamespace(id="staff-1", van_phong_id="office-1")
    data = SimpleNamespace(
        diem_di_id="area-1", diem_den_id="area-2", diem_tra_id="drop-1", chuyen_id="trip-1",
        danh_sach_ghe=["A1"], sdt_khach=PHONE, ten_khach=entered, khach_hang_id=None,
        kenh_ban="tai_quay", phuong_thuc="tien_mat",
    )
    monkeypatch.setattr(service, "lay_van_phong", lambda _: {"id": "office-1", "khu_vuc_id": "area-1"})
    monkeypatch.setattr(service.repo, "diem_tra_thuoc_khu_vuc", lambda *_: True)
    monkeypatch.setattr(service.repo, "diem_hop_le", lambda *_: True)
    monkeypatch.setattr(service.repo, "khach_hang_theo_sdt", lambda _: account)
    monkeypatch.setattr(service.repo, "khach_vang_lai_theo_sdt", lambda _: guest)
    monkeypatch.setattr(service.tim_kiem_chuyen_service, "so_do_ghe_chuyen", lambda *_: {"so_do_ghe": [{"ma_ghe": "A1", "gia": 100000}]})
    calls = []

    def create(*args):
        calls.append(args)
        return [{"gia": 100000, "trang_thai": "da_thanh_toan", "ten_khach_vang_lai": args[8]}]

    monkeypatch.setattr(service.lock_repo, "tao_ve_quay", create)
    result = service.ban_ve(user, data)

    assert calls[0][7:10] == (expected_id, expected_name, PHONE)
    assert result["ten_khach"] == expected_name


def test_khach_moi_phai_nhap_ten(monkeypatch):
    user = SimpleNamespace(id="staff-1", van_phong_id="office-1")
    data = SimpleNamespace(
        diem_di_id="area-1", diem_den_id="area-2", diem_tra_id="drop-1", chuyen_id="trip-1",
        danh_sach_ghe=["A1"], sdt_khach=PHONE, ten_khach=None, khach_hang_id=None,
        kenh_ban="tai_quay", phuong_thuc="tien_mat",
    )
    monkeypatch.setattr(service, "lay_van_phong", lambda _: {"id": "office-1", "khu_vuc_id": "area-1"})
    monkeypatch.setattr(service.repo, "diem_tra_thuoc_khu_vuc", lambda *_: True)
    monkeypatch.setattr(service.repo, "diem_hop_le", lambda *_: True)
    monkeypatch.setattr(service.repo, "khach_hang_theo_sdt", lambda _: None)
    monkeypatch.setattr(service.repo, "khach_vang_lai_theo_sdt", lambda _: None)

    with pytest.raises(GiaTriLoi, match="Khách mới cần nhập họ tên"):
        service.ban_ve(user, data)


def test_request_cho_phep_bo_ten_khi_da_co_sdt():
    from uuid import uuid4

    payload = {
        "kenh_ban": "tai_quay", "chuyen_id": uuid4(), "diem_di_id": uuid4(),
        "diem_den_id": uuid4(), "diem_don_id": uuid4(), "diem_tra_id": uuid4(),
        "danh_sach_ghe": ["A1"], "sdt_khach": PHONE, "phuong_thuc": "tien_mat",
    }
    assert BanVeRequest(**payload).ten_khach is None


def test_truy_van_lich_su_uu_tien_ve_da_thanh_toan(monkeypatch):
    cur = MagicMock()
    cur.description = [("ho_ten",)]
    cur.fetchall.return_value = [("Trần Bình",)]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(service.repo, "get_connection", lambda: conn)
    monkeypatch.setattr(service.repo, "release_connection", lambda _: None)

    assert service.repo.khach_vang_lai_theo_sdt(PHONE) == {"ho_ten": "Trần Bình"}
    query, params = cur.execute.call_args.args
    assert "v.sdt_khach_vang_lai = %s" in query
    assert "v.gio_thanh_toan IS NOT NULL THEN 0 ELSE 1" in query
    assert params == (PHONE,)


def test_tao_ve_khoa_sdt_va_lay_lai_ten_trong_transaction(monkeypatch):
    lock = service.lock_repo
    cur = MagicMock()
    cur.description = [(key,) for key in (
        "id", "ma_ve", "ma_dat_cho", "so_ghe", "gia", "trang_thai", "ten_khach_vang_lai",
    )]
    cur.fetchone.side_effect = [
        ("trip-1",),
        ("chua_khoi_hanh", datetime(2099, 1, 1, tzinfo=timezone.utc)),
        ("Tên đã lưu",),
        ("ticket-1", "VE000001", "DC000001", "A1", 100000, "da_thanh_toan", "Tên đã lưu"),
    ]
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(lock, "get_connection", lambda: conn)
    monkeypatch.setattr(lock, "release_connection", lambda _: None)
    monkeypatch.setattr(lock, "_hl_cua_diem", lambda *_: {"office-1": 1, "drop-1": 2})
    monkeypatch.setattr(lock.ma_repository, "so_tiep_theo", lambda *_: 1)

    result = lock.tao_ve_quay(
        "trip-1", ["A1"], "office-1", "drop-1", {"A1": 100000},
        "DC000001", "staff-1", None, "Tên mới", PHONE, "tai_quay", "tien_mat",
    )

    queries = [call.args[0] for call in cur.execute.call_args_list]
    assert any("pg_advisory_xact_lock" in query for query in queries)
    insert_call = next(call for call in cur.execute.call_args_list if "INSERT INTO ve" in call.args[0])
    assert insert_call.args[1][10:12] == ("Tên đã lưu", PHONE)
    assert result[0]["ten_khach_vang_lai"] == "Tên đã lưu"
    conn.commit.assert_called_once()
