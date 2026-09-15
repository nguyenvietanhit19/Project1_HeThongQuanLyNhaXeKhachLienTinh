from fastapi import FastAPI

app = FastAPI(title="Hệ thống Quản lý Nhà xe Khách")


@app.get("/")
def health_check():
    return {"status": "OK"}
