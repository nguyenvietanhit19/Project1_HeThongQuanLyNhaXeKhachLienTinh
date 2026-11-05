"""Nhắc quầy: một lượt một thông báo, đọc không gỡ, chỉ gỡ sau thanh toán/giờ chạy."""

import datetime
from unittest.mock import MagicMock

from app.jobs import nhac_khach_quay_ve
from app.repositories import quay_ve_repository, thong_bao_repository
from app.services import quay_ve_service, thanh_toan_service, thong_bao_khach_service


def _mock_connection(monkeypatch, module):
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(module, "get_connection", lambda: conn)
    monkeypatch.setattr(module, "release_connection", lambda _: None)
    return conn, cur


def test_job_gop_nhieu_ve_cung_luot_va_khong_nhac_lai_khi_da_doc(monkeypatch):
    item = {
        "nguoi_nhan_id": "nv-1", "ma_dat_cho": "DC1", "ma_chuyen": "T1",
        "gio_khoi_hanh": datetime.datetime(2026, 10, 27, 16, 30, tzinfo=datetime.timezone.utc),
        "ten_khach": "Khách A", "sdt_khach": "0912345678", "cac_ghe": "A1, A2",
        "so_ve": 2, "tong_tien": 400000,
    }
    calls = []
    monkeypatch.setattr(nhac_khach_quay_ve.thong_bao_repo, "xoa_nhac_quay_ve_da_xu_ly", lambda: [])
    monkeypatch.setattr(nhac_khach_quay_ve.thong_bao_repo, "gop_nhac_quay_ve_trung", lambda: [])
    monkeypatch.setattr(nhac_khach_quay_ve.thong_bao, "dong_bo_chuong_quay_ve", lambda _: None)
    monkeypatch.setattr(nhac_khach_quay_ve.repo, "cac_luot_tra_tai_quay_sap_chay", lambda: [item])
    def gui(nguoi_nhan_id, ma_dat_cho, noi_dung):
        calls.append((nguoi_nhan_id, ma_dat_cho, noi_dung))
        return len(calls) == 1
    monkeypatch.setattr(nhac_khach_quay_ve.thong_bao, "gui_nhac_quay_ve", gui)

    assert nhac_khach_quay_ve.chay() == 1
    assert nhac_khach_quay_ve.chay() == 0
    assert all(call[:2] == ("nv-1", "DC1") for call in calls)
    assert "A1, A2" in calls[0][2] and "2 vé" in calls[0][2]


def test_sql_nguon_chi_online_va_hotline_trong_hai_gio(monkeypatch):
    _, cur = _mock_connection(monkeypatch, quay_ve_repository)
    cur.description = [("nguoi_nhan_id",)]
    cur.fetchall.return_value = []
    quay_ve_repository.cac_luot_tra_tai_quay_sap_chay()
    sql = cur.execute.call_args.args[0]
    assert "v.kenh_ban IS NULL OR v.kenh_ban = 'hotline'" in sql
    assert "v.loai_hinh_thanh_toan = 'thanh_toan_tai_quay'" in sql
    assert "c.gio_khoi_hanh <= now() + interval '2 hours'" in sql
    assert "GROUP BY nd.id, v.ma_dat_cho" in sql


def test_sql_tao_nhac_chong_trung_theo_ma_dat_cho_khong_theo_noi_dung(monkeypatch):
    conn, cur = _mock_connection(monkeypatch, thong_bao_repository)
    cur.fetchone.return_value = ("tb-1",)
    assert thong_bao_repository.tao_nhac_quay_ve("nv-1", "DC1", "nội dung") is True
    sql = cur.execute.call_args_list[2].args[0]
    params = cur.execute.call_args_list[2].args[1]
    assert "pg_advisory_xact_lock" in cur.execute.call_args_list[0].args[0]
    assert "SET noi_dung = %s" in cur.execute.call_args_list[1].args[0]
    assert "da_doc" not in cur.execute.call_args_list[1].args[0]
    assert "nguoi_nhan_id = %s AND duong_dan = %s" in sql
    assert "c.gio_khoi_hanh > now()" in sql
    assert params[2] == "/nhan-vien/quay-ve/tra-cuu-ve.html?ma_dat_cho=DC1"
    conn.commit.assert_called_once()


def test_da_doc_chi_cap_nhat_trang_thai_va_giu_ban_ghi(monkeypatch):
    conn, cur = _mock_connection(monkeypatch, thong_bao_repository)
    cur.fetchone.return_value = ("tb-1",)
    assert thong_bao_repository.danh_dau_da_doc("tb-1", "nv-1") == "updated"
    sql = cur.execute.call_args.args[0]
    assert "SET da_doc = true" in sql
    assert "DELETE" not in sql and "gio_khoi_hanh" not in sql
    conn.commit.assert_called_once()


def test_doc_het_khong_go_canh_bao_va_so_tren_chuong_chi_dem_chua_doc(monkeypatch):
    _, cur = _mock_connection(monkeypatch, thong_bao_repository)
    cur.rowcount = 2
    assert thong_bao_repository.danh_dau_tat_ca_da_doc("nv-1") == 2
    assert "tb.da_doc = false" in cur.execute.call_args.args[0]
    assert "DELETE" not in cur.execute.call_args.args[0]
    cur.fetchone.return_value = (0,)
    assert thong_bao_repository.dem_chua_doc("nv-1") == 0
    assert "da_doc = false" in cur.execute.call_args.args[0]


def test_xoa_nhac_chi_sau_khi_du_tien_hoac_den_gio(monkeypatch):
    _, cur = _mock_connection(monkeypatch, thong_bao_repository)
    cur.fetchall.return_value = [("nv-1",)]
    assert thong_bao_repository.xoa_nhac_quay_ve_neu_da_xu_ly("DC1") == ["nv-1"]
    sql = cur.execute.call_args.args[0]
    assert "c.gio_khoi_hanh <= now()" in sql
    assert "NOT EXISTS" in sql and "v.trang_thai = 'giu_cho'" in sql
    assert "da_doc" not in sql


def test_quet_gio_cung_don_canh_bao_da_thanh_toan_va_gop_nhac_trung(monkeypatch):
    _, cur = _mock_connection(monkeypatch, thong_bao_repository)
    cur.fetchall.return_value = [("nv-1",), ("nv-1",)]
    assert thong_bao_repository.xoa_nhac_quay_ve_da_xu_ly() == ["nv-1"]
    sql = cur.execute.call_args.args[0]
    assert "c.gio_khoi_hanh <= now()" in sql
    assert "NOT EXISTS" in sql and "thanh_toan_tai_quay" in sql
    assert thong_bao_repository.gop_nhac_quay_ve_trung() == ["nv-1"]
    assert "PARTITION BY nguoi_nhan_id, duong_dan" in cur.execute.call_args.args[0]
    assert "ORDER BY da_doc DESC" in cur.execute.call_args.args[0]


def test_gui_nhac_chi_day_realtime_khi_vua_tao(monkeypatch):
    sent = []
    monkeypatch.setattr(thong_bao_khach_service.thong_bao_repo, "tao_nhac_quay_ve", lambda *_: False)
    monkeypatch.setattr(thong_bao_khach_service, "broadcast_sync", lambda *args: sent.append(args))
    assert thong_bao_khach_service.gui_nhac_quay_ve("nv-1", "DC1", "nhắc") is False
    assert sent == []


def test_thu_tien_mat_go_canh_bao_sau_khi_ghi_nhan_thanh_cong(monkeypatch):
    now = datetime.datetime.now(datetime.timezone.utc)
    events = []
    monkeypatch.setattr(quay_ve_service, "lay_van_phong", lambda _: {"id": "vp-1"})
    monkeypatch.setattr(quay_ve_service.repo, "tra_cuu", lambda *_args, **_kwargs: [{
        "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_tai_quay",
        "han_giu_cho_den": None, "gio_khoi_hanh": now + datetime.timedelta(hours=1),
        "gio_don_du_kien": now + datetime.timedelta(hours=1),
    }])
    monkeypatch.setattr(quay_ve_service.dat_ve_service, "con_truoc_moc_chot", lambda *_: True)
    monkeypatch.setattr(quay_ve_service.lock_repo, "thanh_toan_ve_quay", lambda *_: events.append("paid") or 1)
    monkeypatch.setattr(quay_ve_service.thong_bao, "don_nhac_quay_ve", lambda code: events.append(code))

    user = type("User", (), {"id": "nv-1"})()
    assert quay_ve_service.thu_tien(user, "DC1", "tien_mat")["so_ve_da_thanh_toan"] == 1
    assert events == ["paid", "DC1"]


def test_thanh_toan_vnpay_ve_online_tra_tai_quay_go_canh_bao(monkeypatch):
    ticket = {
        "id": "ve-1", "ma_ve": "VE1", "ma_dat_cho": "DC1", "so_ghe": "A1",
        "gia": 200000, "trang_thai": "giu_cho", "loai_hinh_thanh_toan": "thanh_toan_tai_quay",
        "ma_tham_chieu_vnpay": "ref-1", "khach_hang_id": "kh-1",
    }
    events = []
    monkeypatch.setattr(thanh_toan_service.repo, "lay_ve_theo_ma_ve", lambda _: ticket)
    monkeypatch.setattr(thanh_toan_service.repo, "ghi_nhan_thanh_toan_ve_le", lambda *_: events.append("paid") or True)
    monkeypatch.setattr(thanh_toan_service.thong_bao, "don_nhac_quay_ve", lambda code: events.append(code))
    monkeypatch.setattr(thanh_toan_service.thong_bao, "gui", lambda *_args, **_kwargs: None)

    result = thanh_toan_service._ap_dung_ket_qua_ve("VE1", "20000000", True, "gd-1", "ref-1")
    assert result["RspCode"] == "00"
    assert events == ["paid", "DC1"]
