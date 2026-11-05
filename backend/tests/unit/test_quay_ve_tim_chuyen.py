"""Thẻ chuyến của quầy vé dùng đúng điểm đón và đoạn ghế tại văn phòng."""

from types import SimpleNamespace

from app.services import quay_ve_service as service


def test_tim_chuyen_dung_gio_va_so_ghe_tai_van_phong(monkeypatch):
    user = SimpleNamespace(van_phong_id="office-1")
    monkeypatch.setattr(service, "lay_van_phong", lambda _: {
        "id": "office-1", "ten": "VP Hà Nội", "khu_vuc_id": "area-1",
    })
    monkeypatch.setattr(service.tim_kiem_chuyen_service, "tim_chuyen", lambda *_: [
        {"id": "trip-1", "tong_ghe": 2, "so_ghe_trong": 0,
         "ten_diem_don": "VP trước", "gio_don_du_kien": "giờ trước"},
        {"id": "trip-khong-qua-quay", "tong_ghe": 2, "so_ghe_trong": 2},
    ])
    monkeypatch.setattr(service.repo, "thong_tin_chuyen_tai_van_phong", lambda *_: {
        "trip-1": {
            "hl_don": 2, "hl_tra": 4, "gio_don_du_kien": "giờ tại quầy",
            "diem_tra_id": "drop-1", "ten_diem_tra": "VP điểm cuối", "gio_den_du_kien": "giờ đến",
        },
    })
    monkeypatch.setattr(service.chuyen_repo, "tim_doan_ve_dang_giu", lambda *_: [
        {"chuyen_id": "trip-1", "so_ghe": "A1", "hl_don": 1, "hl_tra": 2},
        {"chuyen_id": "trip-1", "so_ghe": "A2", "hl_don": 2, "hl_tra": 4},
    ])

    trips = service.tim_chuyen(user, "area-1", "area-2", None)

    assert len(trips) == 1
    assert trips[0]["ten_diem_don"] == "VP Hà Nội"
    assert trips[0]["gio_don_du_kien"] == "giờ tại quầy"
    assert trips[0]["ten_diem_tra"] == "VP điểm cuối"
    assert trips[0]["so_ghe_trong"] == 1  # Ghế A1 đã trống lại sau khi qua văn phòng.
