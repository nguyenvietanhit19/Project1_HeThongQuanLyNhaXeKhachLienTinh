"""Xử lý kết quả thanh toán VNPay — IPN (nguồn sự thật) và trang kết quả trả về cho trình duyệt (chỉ để hiển thị).

NGHIEP_VU.md mục 6, UC-05 nhánh A. Dùng chung cho cổng giả lập lẫn VNPay sandbox thật.

IPN: chỉ đổi trạng thái vé khi chữ ký đúng, số tiền khớp và vé chưa được xử lý — vì VNPay có thể gọi lại nhiều lần.
Mã phản hồi trả về cổng (RspCode): 00 xử lý xong · 01 không thấy đơn · 02 đã xử lý rồi · 04 sai số tiền · 97 sai chữ ký.
"""

from app.repositories import ve_thanh_toan_repository as repo
from app.services import vnpay_service


def _rsp(ma: str, thong_diep: str) -> dict:
    return {"RspCode": ma, "Message": thong_diep}


def xu_ly_ipn(tham_so: dict) -> dict:
    if not vnpay_service.chu_ky_hop_le(tham_so):
        return _rsp("97", "Invalid signature")

    ma_dat_cho = vnpay_service.ma_dat_cho_tu_ma_giao_dich(tham_so.get("vnp_TxnRef", ""))
    cac_ve = repo.lay_ve_cua_dat_cho(ma_dat_cho)
    ve_online = [
        v for v in cac_ve if v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v["trang_thai"] in ("giu_cho", "da_thanh_toan")
    ]
    if not ve_online:
        return _rsp("01", "Order not found")
    if all(v["trang_thai"] == "da_thanh_toan" for v in ve_online):
        return _rsp("02", "Order already confirmed")

    try:
        so_tien_cong = int(tham_so.get("vnp_Amount", "0"))
    except ValueError:
        return _rsp("04", "Invalid amount")
    if so_tien_cong != sum(int(v["gia"]) for v in ve_online) * 100:
        return _rsp("04", "Invalid amount")

    thanh_cong = tham_so.get("vnp_ResponseCode") == "00" and tham_so.get("vnp_TransactionStatus", "00") == "00"
    if thanh_cong:
        if not repo.ghi_nhan_thanh_toan_ngay(ma_dat_cho, str(tham_so.get("vnp_TransactionNo", ""))):
            # Tiền đã trừ nhưng vé đã quá hạn/không còn giữ chỗ (trả đúng sát giờ): dừng cổng gọi lại, cần hoàn tiền thủ công (UC-22)
            return _rsp("02", "Order expired")
    else:
        repo.huy_thanh_toan_ngay(ma_dat_cho)
    return _rsp("00", "Confirm Success")


def doc_ket_qua_tra_ve(tham_so: dict) -> dict:
    """Trình duyệt khách được cổng đưa về trang của mình: kiểm tra chữ ký rồi cho biết kết quả để HIỂN THỊ.
    Không đổi trạng thái vé ở đây — việc đó chỉ làm ở IPN."""
    if not vnpay_service.chu_ky_hop_le(tham_so):
        return {"hop_le": False, "thanh_cong": False, "ma_dat_cho": None, "ma_phan_hoi": None}
    return {
        "hop_le": True,
        "thanh_cong": tham_so.get("vnp_ResponseCode") == "00" and tham_so.get("vnp_TransactionStatus", "00") == "00",
        "ma_dat_cho": vnpay_service.ma_dat_cho_tu_ma_giao_dich(tham_so.get("vnp_TxnRef", "")),
        "ma_phan_hoi": tham_so.get("vnp_ResponseCode"),
    }
