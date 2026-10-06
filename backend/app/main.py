from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.jobs.quet_chua_gan_xe import dang_ky_job as dang_ky_job_uc45
from app.routes.auth import router as auth_router
from app.routes.quan_ly import router as quan_ly_router
from app.routes.websocket import router as websocket_router
from app.utils.loi import GiaTriLoi, KhongDuQuyen, LoiHeThong

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động các background jobs theo ARCHITECTURE.md mục 5 & CONTRIBUTING.md mục 5.2
    dang_ky_job_uc45(scheduler)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


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


from app.routes import dieu_do as dieu_do_router

app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(quan_ly_router)
app.include_router(dieu_do_router.router)
