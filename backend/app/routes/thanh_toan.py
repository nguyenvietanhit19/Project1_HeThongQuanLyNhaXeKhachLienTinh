"""Kết quả thanh toán VNPay (UC-05 nhánh "thanh toán ngay") — NGHIEP_VU.md mục 6.

Các route ở đây KHÔNG cần đăng nhập vì người gọi là cổng thanh toán hoặc trang kết quả; thay vào đó mọi tham số đều phải
có chữ ký hợp lệ (HMAC-SHA512, vnpay_service). Route mỏng, chỉ gọi service.

- GET /thanh-toan/vnpay/ipn      : VNPay gọi về (nguồn sự thật để đổi trạng thái vé)
- GET /thanh-toan/vnpay/ket-qua  : trang kết quả hỏi lại để HIỂN THỊ (không đổi trạng thái)
- POST /thanh-toan/vnpay/xac-nhan: backend hỏi VNPay (querydr) kết quả thật rồi đổi trạng thái vé — thay IPN khi IPN không tới
- /cong-thanh-toan-gia/*         : cổng giả lập cho demo (chỉ chạy khi VNPAY_CHE_DO = gia_lap)
"""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services import cong_thanh_toan_gia_service as cong_gia
from app.services import thanh_toan_service

router = APIRouter(tags=["thanh-toan"])


def _tham_so_vnp(request: Request) -> dict:
    return {k: v for k, v in request.query_params.items() if k.startswith("vnp_")}


@router.get("/thanh-toan/vnpay/ipn")
def ipn_vnpay(request: Request):
    return thanh_toan_service.xu_ly_ipn(_tham_so_vnp(request))


@router.get("/thanh-toan/vnpay/ket-qua")
def ket_qua_vnpay(request: Request):
    return thanh_toan_service.doc_ket_qua_tra_ve(_tham_so_vnp(request))


class XacNhanRequest(BaseModel):
    ma_giao_dich: str  # vnp_TxnRef trên đường dẫn trả về; backend tự hỏi VNPay kết quả thật nên không cần tin dữ liệu này


@router.post("/thanh-toan/vnpay/xac-nhan")
def xac_nhan_vnpay(body: XacNhanRequest):
    return thanh_toan_service.xac_nhan_qua_truy_van(body.ma_giao_dich)


class XuLyGiaLapRequest(BaseModel):
    tham_so: dict[str, str]  # nguyên các tham số vnp_* trên đường dẫn thanh toán
    ket_qua: Literal["thanh_cong", "huy"]


@router.get("/cong-thanh-toan-gia/thong-tin")
def thong_tin_giao_dich_gia(request: Request):
    return cong_gia.thong_tin_giao_dich(_tham_so_vnp(request))


@router.post("/cong-thanh-toan-gia/xu-ly")
def xu_ly_giao_dich_gia(body: XuLyGiaLapRequest):
    return cong_gia.xu_ly(body.tham_so, body.ket_qua)
