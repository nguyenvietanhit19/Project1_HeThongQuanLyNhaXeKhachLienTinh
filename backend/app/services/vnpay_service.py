"""Chữ ký + đường dẫn thanh toán theo đúng quy tắc của VNPay (tài liệu sandbox.vnpayment.vn/apis/docs/thanh-toan-pay).

Dùng chung cho cả cổng giả lập (cong_thanh_toan_gia_service) lẫn VNPay sandbox thật — đổi sang thật chỉ cần đổi
cấu hình (config.py), không đổi file này. Các hàm ở đây là hàm thuần (không đụng DB) nên dễ unit test.

Quy tắc chữ ký (HMAC-SHA512): bỏ `vnp_SecureHash`/`vnp_SecureHashType`, chỉ giữ tham số `vnp_*` có giá trị, sắp theo
tên A→Z, ghép `tên=giá_trị&tên=giá_trị` với giá trị mã hóa URL, rồi HMAC-SHA512 bằng khóa bí mật.
"""

import datetime
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
import uuid
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from app.config import CORS_ORIGINS, VNPAY_API_URL, VNPAY_CHE_DO, VNPAY_HASH_SECRET, VNPAY_TMN_CODE, VNPAY_URL
from app.utils.loi import GiaTriLoi

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
TRANG_THAI_THANH_TOAN_GIA = "/khach-hang/cong-thanh-toan-gia.html"
TRANG_KET_QUA = "/khach-hang/ket-qua-thanh-toan.html"


def dinh_dang_gio_vn(thoi_diem: datetime.datetime) -> str:
    """yyyyMMddHHmmss theo giờ Việt Nam (GMT+7) — định dạng thời gian của VNPay."""
    return thoi_diem.astimezone(MUI_GIO_VN).strftime("%Y%m%d%H%M%S")


def doc_gio_vn(chuoi: str) -> datetime.datetime:
    return datetime.datetime.strptime(chuoi, "%Y%m%d%H%M%S").replace(tzinfo=MUI_GIO_VN)


def chuoi_can_ky(tham_so: dict) -> str:
    cac_muc = sorted(
        (k, str(v)) for k, v in tham_so.items() if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType") and str(v) != ""
    )
    return "&".join(f"{k}={quote_plus(v)}" for k, v in cac_muc)


def ky(tham_so: dict, khoa_bi_mat: str | None = None) -> str:
    khoa_bi_mat = khoa_bi_mat or VNPAY_HASH_SECRET  # đọc lúc gọi, không đóng băng lúc import
    return hmac.new(khoa_bi_mat.encode(), chuoi_can_ky(tham_so).encode(), hashlib.sha512).hexdigest()


def chu_ky_hop_le(tham_so: dict, khoa_bi_mat: str | None = None) -> bool:
    chu_ky = str(tham_so.get("vnp_SecureHash", ""))
    return bool(chu_ky) and hmac.compare_digest(chu_ky.lower(), ky(tham_so, khoa_bi_mat))


def dung_query(tham_so: dict, khoa_bi_mat: str | None = None) -> str:
    """Chuỗi query đã ký, dùng cho đường dẫn thanh toán và đường dẫn trả về."""
    return f"{chuoi_can_ky(tham_so)}&vnp_SecureHash={ky(tham_so, khoa_bi_mat)}"


def kiem_tra_origin_frontend(origin: str | None) -> str:
    """Trang web nhận kết quả phải là 1 trong các địa chỉ frontend đã cho phép (CORS_ORIGINS) — chặn chuyển hướng ra ngoài."""
    if not origin or origin.rstrip("/") not in CORS_ORIGINS:
        raise GiaTriLoi("Địa chỉ trang web nhận kết quả thanh toán không hợp lệ")
    return origin.rstrip("/")


def tao_ma_giao_dich(ma_dat_cho: str, bay_gio: datetime.datetime) -> str:
    """`vnp_TxnRef`: duy nhất cho từng lần thanh toán — mã đặt chỗ + thời điểm tạo (1 lượt đặt có thể thử lại)."""
    return f"{ma_dat_cho}-{dinh_dang_gio_vn(bay_gio)}"


def ma_dat_cho_tu_ma_giao_dich(ma_giao_dich: str) -> str:
    return str(ma_giao_dich).split("-", 1)[0]


def tao_url_thanh_toan(
    ma_dat_cho: str,
    so_tien: int,
    han_thanh_toan: datetime.datetime,
    origin_frontend: str,
    ip_khach: str,
    bay_gio: datetime.datetime | None = None,
    ma_giao_dich: str | None = None,
) -> str:
    bay_gio = bay_gio or datetime.datetime.now(datetime.timezone.utc)
    origin = kiem_tra_origin_frontend(origin_frontend)
    tham_so = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": VNPAY_TMN_CODE,
        "vnp_Amount": int(so_tien) * 100,  # VNPay: nhân 100 để bỏ phần thập phân
        "vnp_CreateDate": dinh_dang_gio_vn(bay_gio),
        "vnp_CurrCode": "VND",
        "vnp_IpAddr": ip_khach,
        "vnp_Locale": "vn",
        "vnp_OrderInfo": f"Thanh toan ve xe ma dat cho {ma_dat_cho}",
        "vnp_OrderType": "other",
        "vnp_ReturnUrl": origin + TRANG_KET_QUA,
        "vnp_TxnRef": ma_giao_dich or tao_ma_giao_dich(ma_dat_cho, bay_gio),
        "vnp_ExpireDate": dinh_dang_gio_vn(han_thanh_toan),
    }
    goc = origin + TRANG_THAI_THANH_TOAN_GIA if VNPAY_CHE_DO == "gia_lap" else VNPAY_URL
    return f"{goc}?{dung_query(tham_so)}"


# ---------------------------------------------------------
# Truy vấn giao dịch (querydr): backend chủ động hỏi VNPay kết quả, không phụ thuộc IPN
# ---------------------------------------------------------
def _ky_chuoi(chuoi: str, khoa_bi_mat: str | None = None) -> str:
    return hmac.new((khoa_bi_mat or VNPAY_HASH_SECRET).encode(), chuoi.encode(), hashlib.sha512).hexdigest()


def ngay_tao_tu_ma_giao_dich(ma_giao_dich: str) -> str:
    """Phần yyyyMMddHHmmss ở cuối mã giao dịch (`tao_ma_giao_dich`) — VNPay cần đúng ngày giờ lúc tạo giao dịch."""
    return str(ma_giao_dich).rsplit("-", 1)[-1]


def tao_yeu_cau_truy_van(ma_giao_dich: str, bay_gio: datetime.datetime | None = None, ip: str = "127.0.0.1") -> dict:
    bay_gio = bay_gio or datetime.datetime.now(datetime.timezone.utc)
    yeu_cau = {
        "vnp_RequestId": uuid.uuid4().hex,
        "vnp_Version": "2.1.0",
        "vnp_Command": "querydr",
        "vnp_TmnCode": VNPAY_TMN_CODE,
        "vnp_TxnRef": ma_giao_dich,
        "vnp_OrderInfo": f"Truy van giao dich {ma_giao_dich}",
        "vnp_TransactionDate": ngay_tao_tu_ma_giao_dich(ma_giao_dich),
        "vnp_CreateDate": dinh_dang_gio_vn(bay_gio),
        "vnp_IpAddr": ip,
    }
    cac_truong = ("RequestId", "Version", "Command", "TmnCode", "TxnRef", "TransactionDate", "CreateDate", "IpAddr", "OrderInfo")
    yeu_cau["vnp_SecureHash"] = _ky_chuoi("|".join(str(yeu_cau[f"vnp_{t}"]) for t in cac_truong))
    return yeu_cau


_TRUONG_PHAN_HOI_TRUY_VAN = (
    "ResponseId", "Command", "ResponseCode", "Message", "TmnCode", "TxnRef", "Amount", "BankCode",
    "PayDate", "TransactionNo", "TransactionType", "TransactionStatus", "OrderInfo", "PromotionCode", "PromotionAmount",
)


def phan_hoi_truy_van_hop_le(phan_hoi: dict, khoa_bi_mat: str | None = None) -> bool:
    chu_ky = str(phan_hoi.get("vnp_SecureHash", ""))
    chuoi = "|".join(str(phan_hoi.get(f"vnp_{t}", "")) for t in _TRUONG_PHAN_HOI_TRUY_VAN)
    return bool(chu_ky) and hmac.compare_digest(chu_ky.lower(), _ky_chuoi(chuoi, khoa_bi_mat))


def truy_van_giao_dich(ma_giao_dich: str) -> dict | None:
    """Hỏi VNPay kết quả 1 giao dịch. Trả None nếu không gọi được hoặc phản hồi sai chữ ký (coi như chưa biết kết quả)."""
    yeu_cau = urllib.request.Request(
        VNPAY_API_URL,
        data=json.dumps(tao_yeu_cau_truy_van(ma_giao_dich)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(yeu_cau, timeout=15) as res:
            phan_hoi = json.loads(res.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        logger.warning("Không truy vấn được giao dịch VNPay %s", ma_giao_dich)
        return None
    if isinstance(phan_hoi, dict) and "vnp_SecureHash" not in phan_hoi:
        # Phản hồi lỗi của VNPay không có chữ ký (VD 94 "Request is duplicated": hỏi lặp quá sát nhau)
        logger.warning("VNPay từ chối truy vấn %s: %s %s", ma_giao_dich, phan_hoi.get("vnp_ResponseCode"), phan_hoi.get("vnp_Message"))
        return None
    if not isinstance(phan_hoi, dict) or not phan_hoi_truy_van_hop_le(phan_hoi):
        logger.warning("Phản hồi truy vấn VNPay %s sai chữ ký hoặc sai định dạng", ma_giao_dich)
        return None
    return phan_hoi
