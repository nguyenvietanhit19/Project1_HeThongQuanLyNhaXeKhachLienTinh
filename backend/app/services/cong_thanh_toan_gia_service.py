"""Cổng thanh toán GIẢ LẬP dùng để demo (VNPAY_CHE_DO = "gia_lap") — đóng vai trò của VNPay.

Làm đúng những việc VNPay làm: kiểm tra chữ ký của đường dẫn thanh toán, từ chối giao dịch quá hạn, rồi
(1) gọi IPN về hệ thống với tham số có chữ ký, (2) trả đường dẫn đưa trình duyệt khách về trang kết quả, cũng có chữ ký.
Không có tiền thật nào chuyển đi. Khi chuyển sang VNPay sandbox thật, cả file này (và trang
frontend/khach-hang/cong-thanh-toan-gia.html) không còn được dùng — phần còn lại của luồng giữ nguyên.
"""

import datetime
import random

from app.config import VNPAY_CHE_DO
from app.services import thanh_toan_service, vnpay_service
from app.utils.loi import GiaTriLoi


def _kiem_tra_dang_chay_gia_lap() -> None:
    if VNPAY_CHE_DO != "gia_lap":
        raise GiaTriLoi("Cổng thanh toán giả lập chỉ dùng được khi VNPAY_CHE_DO = gia_lap")


def _kiem_tra_duong_dan(tham_so: dict) -> None:
    if tham_so.get("vnp_Command") != "pay" or not vnpay_service.chu_ky_hop_le(tham_so):
        raise GiaTriLoi("Đường dẫn thanh toán không hợp lệ (sai chữ ký)")


def thong_tin_giao_dich(tham_so: dict) -> dict:
    """Thông tin hiển thị trên trang thanh toán giả (chỉ sau khi chữ ký đúng)."""
    _kiem_tra_dang_chay_gia_lap()
    _kiem_tra_duong_dan(tham_so)
    return {
        "ma_giao_dich": tham_so["vnp_TxnRef"],
        "noi_dung": tham_so.get("vnp_OrderInfo", ""),
        "so_tien": int(tham_so["vnp_Amount"]) // 100,
        "han_thanh_toan": vnpay_service.doc_gio_vn(tham_so["vnp_ExpireDate"]),
    }


def xu_ly(tham_so: dict, ket_qua: str, bay_gio: datetime.datetime | None = None) -> dict:
    """Khách bấm "Thanh toán thành công" (`thanh_cong`) hoặc "Hủy giao dịch" (`huy`) trên trang thanh toán giả."""
    _kiem_tra_dang_chay_gia_lap()
    _kiem_tra_duong_dan(tham_so)
    bay_gio = bay_gio or datetime.datetime.now(datetime.timezone.utc)

    if bay_gio > vnpay_service.doc_gio_vn(tham_so["vnp_ExpireDate"]):
        ma_phan_hoi, trang_thai = "11", "02"  # hết thời gian thanh toán
    elif ket_qua == "thanh_cong":
        ma_phan_hoi, trang_thai = "00", "00"
    else:
        ma_phan_hoi, trang_thai = "24", "02"  # khách hủy giao dịch

    ket_qua_cong = {
        "vnp_TmnCode": tham_so["vnp_TmnCode"],
        "vnp_Amount": tham_so["vnp_Amount"],
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": f"VNP{random.randint(10**7, 10**8 - 1)}",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": tham_so.get("vnp_OrderInfo", ""),
        "vnp_PayDate": vnpay_service.dinh_dang_gio_vn(bay_gio),
        "vnp_ResponseCode": ma_phan_hoi,
        "vnp_TransactionNo": str(random.randint(10**7, 10**8 - 1)),
        "vnp_TransactionStatus": trang_thai,
        "vnp_TxnRef": tham_so["vnp_TxnRef"],
    }
    ket_qua_cong["vnp_SecureHash"] = vnpay_service.ky(ket_qua_cong)

    phan_hoi_ipn = thanh_toan_service.xu_ly_ipn(ket_qua_cong)  # "VNPay gọi IPN về hệ thống"
    return {"return_url": f"{tham_so['vnp_ReturnUrl']}?{vnpay_service.dung_query(ket_qua_cong)}", "ipn": phan_hoi_ipn}
