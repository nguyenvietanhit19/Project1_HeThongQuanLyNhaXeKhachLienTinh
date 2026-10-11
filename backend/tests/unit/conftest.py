"""Fixture dùng chung cho unit test.

`da_gui_thong_bao`: thay thế hàm gửi thông báo cho khách bằng 1 danh sách ghi lại các lần gọi (người nhận, nội dung, ve_id) —
tự áp dụng cho MỌI test (autouse) để không test nào vô tình ghi vào DB thật hoặc đẩy WebSocket. Test cần kiểm tra thông báo thì
nhận fixture này làm tham số và đọc danh sách.
"""

import pytest

from app.services import thong_bao_khach_service


@pytest.fixture(autouse=True)
def da_gui_thong_bao(monkeypatch):
    da_gui: list[tuple] = []
    monkeypatch.setattr(thong_bao_khach_service, "gui", lambda nguoi_nhan_id, noi_dung, ve_id=None: da_gui.append((nguoi_nhan_id, noi_dung, ve_id)))
    return da_gui
