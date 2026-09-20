import asyncio

from fastapi import WebSocket


class WebSocketManager:
    """Hạ tầng real-time dùng chung — ARCHITECTURE.md mục 6.

    Chỉ 1 hàm duy nhất các domain khác cần biết: broadcast(). Không ai
    ngoài người 1 được sửa file này — cần gửi thêm kiểu thông báo nào thì
    gọi broadcast(), không tự viết lại cơ chế quản lý kết nối.

    Đơn giản hóa cho quy mô BTL: mỗi nguoi_dung_id chỉ giữ 1 kết nối gần
    nhất (mở thêm tab thứ 2 sẽ ghi đè kết nối cũ) — đủ dùng, không cần
    theo dõi nhiều kết nối song song cho 1 người.
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, nguoi_dung_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[nguoi_dung_id] = websocket

    def disconnect(self, nguoi_dung_id: str) -> None:
        self.active_connections.pop(nguoi_dung_id, None)

    async def broadcast(self, nguoi_dung_id: str, noi_dung: str) -> None:
        """Gửi thông báo real-time nếu người dùng đang online.

        Lưu ý: hàm này KHÔNG lưu vào bảng thong_bao — nơi gọi (VD
        chuyen_xe_service khi đổi xe) phải tự ghi thong_bao_repository.tao(...)
        TRƯỚC khi gọi broadcast(), để khách offline vẫn đọc lại được sau
        (DATABASE.md mục 6.1). broadcast() chỉ lo phần "đẩy ngay lúc đang
        online", không phải nơi lưu trữ.
        """
        websocket = self.active_connections.get(nguoi_dung_id)
        if websocket is not None:
            await websocket.send_json({"noi_dung": noi_dung})


manager = WebSocketManager()


def broadcast_sync(nguoi_dung_id: str, noi_dung: str) -> None:
    """Wrapper đồng bộ cho broadcast() — các Service sync (chuyen_xe_service,
    ve_service, gui_hang_service...) chạy trong threadpool của FastAPI
    (không có event loop nào đang chạy sẵn trong thread đó), nên gọi
    asyncio.run() ở đây an toàn, không xung đột với event loop chính của
    app. Dùng hàm này thay vì gọi thẳng broadcast() từ code sync."""
    try:
        asyncio.run(manager.broadcast(nguoi_dung_id, noi_dung))
    except RuntimeError:
        pass  # hiếm khi xảy ra (đã có event loop khác chạy sẵn trong thread) — bỏ qua, không phải lỗi nghiệp vụ
