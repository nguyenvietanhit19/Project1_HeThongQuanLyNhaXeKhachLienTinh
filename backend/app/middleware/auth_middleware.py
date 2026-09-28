import datetime
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from app.repositories import nguoi_dung_repository as repo


def giai_ma_token(token: str) -> str:
    """Giải mã JWT, trả về nguoi_dung_id (claim 'sub').

    Dùng chung cho mọi nơi cần đọc token trong hệ thống (route HTTP thường
    lẫn WebSocket, routes/websocket.py) — không tự viết lại logic
    jwt.decode ở nơi khác. Ném lỗi jwt.InvalidTokenError (hoặc lớp con,
    VD ExpiredSignatureError) nếu token sai/hết hạn.
    """
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload["sub"]


def tao_token(nguoi_dung_id: str, vai_tro: str) -> str:
    """Sinh JWT lúc đăng nhập thành công — claim 'sub' luôn là nguoi_dung_id
    (đúng chuẩn JWT), kèm 'vai_tro' chỉ để tham khảo hiển thị phía client;
    mọi kiểm tra quyền THẬT SỰ đều tra lại DB (yeu_cau_dang_nhap dưới đây),
    không tin tưởng tuyệt đối 'vai_tro' trong token cũ (đã đổi vai trò/khóa
    tài khoản thì token cũ phải mất quyền ngay, không đợi hết hạn)."""
    payload = {
        "sub": nguoi_dung_id,
        "vai_tro": vai_tro,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@dataclass
class NguoiDungHienTai:
    id: str
    vai_tro: str


def yeu_cau_dang_nhap(authorization: Annotated[str | None, Header()] = None) -> NguoiDungHienTai:
    """Dependency FastAPI dùng cho mọi route cần đăng nhập:

        @router.get("/toi")
        def xem_thong_tin(nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_dang_nhap)):
            ...

    Tương đương @can_access() của bản v1 (Flask) nhưng viết theo đúng kiểu
    dependency injection của FastAPI thay vì decorator — route khác chỉ cần
    khai báo tham số, không tự viết lại logic kiểm tra JWT.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        nguoi_dung_id = giai_ma_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")

    nguoi_dung = repo.tim_theo_id(nguoi_dung_id)
    if not nguoi_dung:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại")
    if not nguoi_dung["dang_hoat_dong"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    return NguoiDungHienTai(id=nguoi_dung["id"], vai_tro=nguoi_dung["vai_tro"])


def yeu_cau_vai_tro(*vai_tro_cho_phep: str):
    """Factory tạo dependency giới hạn theo vai trò:

        @router.post("/quan-ly/tuyen")
        def tao_tuyen(nguoi_dung: NguoiDungHienTai = Depends(yeu_cau_vai_tro("quan_ly"))):
            ...
    """

    def kiem_tra(nguoi_dung: Annotated[NguoiDungHienTai, Depends(yeu_cau_dang_nhap)]) -> NguoiDungHienTai:
        if nguoi_dung.vai_tro not in vai_tro_cho_phep:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền")
        return nguoi_dung

    return kiem_tra
