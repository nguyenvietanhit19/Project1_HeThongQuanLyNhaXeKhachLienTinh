"""Unit test cho UC-45: Tự động chuyển "đang hoãn" khi tới giờ chạy mà chưa gán xe (Job định kỳ).

Căn cứ:
- NGHIEP_VU.md mục 3.3, mục 7, UC-45
- ARCHITECTURE.md mục 5
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import chuyen_xe_service


@pytest.mark.anyio
async def test_xu_ly_tu_dong_chuyen_dang_hoan_thanh_cong():
    """Chuyến chưa khởi hành, quá giờ, xe_id IS NULL -> chuyển sang dang_hoan=true, dời giờ +60p."""
    gio_cu = datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc)
    chuyen_mock = [
        {
            "id": "chuyen-uuid-1",
            "tuyen_id": "tuyen-uuid-1",
            "ten_tuyen": "Hà Nội - Hải Phòng",
            "gio_khoi_hanh": gio_cu,
            "dang_hoan": False,
        }
    ]

    with (
        patch("app.repositories.chuyen_xe_repository.lay_danh_sach_chuyen_can_hoan", return_value=chuyen_mock),
        patch("app.repositories.chuyen_xe_repository.bat_co_dang_hoan") as mock_bat_co,
        patch("app.repositories.ve_repository.tim_ve_da_thanh_toan_theo_chuyen", return_value=[{"khach_hang_id": "khach-1"}]),
        patch("app.services.websocket_manager.manager.broadcast", new_callable=AsyncMock) as mock_broadcast,
    ):
        ket_qua = await chuyen_xe_service.xu_ly_tu_dong_chuyen_dang_hoan()

        assert len(ket_qua) == 1
        assert ket_qua[0]["id"] == "chuyen-uuid-1"

        # Kiểm tra repository được gọi với giờ mới (+60 phút)
        gio_moi_du_kien = gio_cu + timedelta(minutes=60)
        mock_bat_co.assert_called_once_with("chuyen-uuid-1", gio_moi_du_kien)

        # Kiểm tra thông báo WebSocket được gửi cho khách hàng
        mock_broadcast.assert_called_once()
        args, _ = mock_broadcast.call_args
        assert args[0] == "khach-1"
        assert "hoãn" in args[1].lower()


@pytest.mark.anyio
async def test_khong_hoan_khi_khong_co_chuyen_thoa_man():
    """Nếu không có chuyến nào quá giờ mà thiếu xe -> không thực hiện thao tác nào."""
    with (
        patch("app.repositories.chuyen_xe_repository.lay_danh_sach_chuyen_can_hoan", return_value=[]),
        patch("app.repositories.chuyen_xe_repository.bat_co_dang_hoan") as mock_bat_co,
    ):
        ket_qua = await chuyen_xe_service.xu_ly_tu_dong_chuyen_dang_hoan()

        assert ket_qua == []
        mock_bat_co.assert_not_called()
