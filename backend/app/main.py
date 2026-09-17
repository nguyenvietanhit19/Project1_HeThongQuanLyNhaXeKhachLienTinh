from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes.auth import router as auth_router
from app.routes.websocket import router as websocket_router
from app.utils.loi import GiaTriLoi, KhongDuQuyen, LoiHeThong

app = FastAPI(title="Hệ thống Quản lý Nhà xe Khách")


@app.get("/")
def health_check():
    return {"status": "OK"}


@app.exception_handler(GiaTriLoi)
def xu_ly_gia_tri_loi(request: Request, exc: GiaTriLoi):
    return JSONResponse(status_code=400, content={"loi": str(exc)})


@app.exception_handler(KhongDuQuyen)
def xu_ly_khong_du_quyen(request: Request, exc: KhongDuQuyen):
    return JSONResponse(status_code=401, content={"loi": str(exc)})


@app.exception_handler(LoiHeThong)
def xu_ly_loi_he_thong(request: Request, exc: LoiHeThong):
    return JSONResponse(status_code=500, content={"loi": str(exc)})


app.include_router(websocket_router)
app.include_router(auth_router)
