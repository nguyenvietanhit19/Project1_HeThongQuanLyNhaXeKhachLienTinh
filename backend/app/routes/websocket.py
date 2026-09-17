import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.middleware.auth_middleware import giai_ma_token
from app.services.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str) -> None:
    """Điểm kết nối real-time — chỉ lo xác thực + giữ kết nối, không chứa
    nghiệp vụ (ARCHITECTURE.md mục 6). Token truyền qua query string vì
    WebSocket API gốc của trình duyệt không cho set header Authorization
    lúc bắt tay kết nối.
    """
    try:
        nguoi_dung_id = giai_ma_token(token)
    except jwt.InvalidTokenError:
        await websocket.close(code=1008)  # 1008 = policy violation (token sai/hết hạn)
        return

    await manager.connect(nguoi_dung_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # chỉ để giữ kết nối sống, không xử lý nội dung nhận vào
    except WebSocketDisconnect:
        manager.disconnect(nguoi_dung_id)
