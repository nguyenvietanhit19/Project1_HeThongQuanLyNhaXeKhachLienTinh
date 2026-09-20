from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.jobs import quet_no_show
from app.routes.auth import router as auth_router
from app.routes.phu_xe import router as phu_xe_router
from app.routes.quan_ly import router as quan_ly_router
from app.routes.websocket import router as websocket_router
from app.utils.loi import GiaTriLoi, KhongDuQuyen, LoiHeThong

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # UC-14 (⏱, mục 8.2 điểm 6/mục 9) — chu kỳ 1 phút đủ chính xác cho mốc
    # X phút (mặc định 5), theo đúng ARCHITECTURE.md mục 5.
    scheduler.add_job(quet_no_show.chay, "interval", minutes=1, id="quet_no_show")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Hệ thống Quản lý Nhà xe Khách", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.exception_handler(Exception)
def xu_ly_loi_khong_luong_truoc(request: Request, exc: Exception):
    """Lưới an toàn cuối cùng cho lỗi không lường trước (VD ID sai định
    dạng UUID khiến driver DB ném lỗi thẳng, DB mất kết nối...).

    Không có handler này, Starlette tự trả 500 "trần" (kèm traceback nếu
    debug bật) từ ServerErrorMiddleware. Đăng ký handler ở đây còn để tự
    gắn header CORS thủ công bên dưới — đã kiểm chứng thực tế
    (`app.add_middleware(CORSMiddleware, ...)`) KHÔNG tự thêm header CORS
    cho response sinh ra từ exception handler, kể cả khi handler này nằm
    trong `ExceptionMiddleware` (về lý thuyết nằm trong CORSMiddleware).
    Thiếu bước này, trình duyệt hiển thị nhầm mọi lỗi 500 thành lỗi CORS
    ("Failed to fetch"), che mất lỗi thật, cực khó debug từ phía frontend.
    """
    response = JSONResponse(status_code=500, content={"loi": "Đã có lỗi hệ thống, vui lòng thử lại sau"})
    origin = request.headers.get("origin")
    if origin in CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(quan_ly_router)
app.include_router(phu_xe_router)
