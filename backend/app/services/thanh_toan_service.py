"""Xử lý kết quả thanh toán VNPay — IPN (nguồn sự thật) và trang kết quả trả về cho trình duyệt (chỉ để hiển thị).

NGHIEP_VU.md mục 6, UC-05 nhánh A. Dùng chung cho cổng giả lập lẫn VNPay sandbox thật.

IPN: chỉ đổi trạng thái vé khi chữ ký đúng, số tiền khớp và vé chưa được xử lý — vì VNPay có thể gọi lại nhiều lần.
Mã phản hồi trả về cổng (RspCode): 00 xử lý xong · 01 không thấy đơn · 02 đã xử lý rồi · 04 sai số tiền · 97 sai chữ ký.
"""

import datetime

from app.config import VNPAY_CHE_DO
from app.repositories import ve_thanh_toan_repository as repo
from app.services import vnpay_service

TUOI_TOI_THIEU_DE_QUET_GIAY = 240  # job chỉ hỏi VNPay các giao dịch đã tạo từ 4 phút trước (hạn thanh toán 5 phút + 2 phút đệm)


def _rsp(ma: str, thong_diep: str) -> dict:
    return {"RspCode": ma, "Message": thong_diep}


def _ap_dung_ket_qua(ma_dat_cho: str, so_tien_cong: str, thanh_cong: bool, ma_giao_dich_cong: str) -> dict:
    """Đổi trạng thái vé theo kết quả giao dịch (dùng chung cho IPN và truy vấn querydr). Trả mã phản hồi kiểu IPN."""
    cac_ve = repo.lay_ve_cua_dat_cho(ma_dat_cho)
    ve_online = [
        v for v in cac_ve if v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v["trang_thai"] in ("giu_cho", "da_thanh_toan")
    ]
    if not ve_online:
        return _rsp("01", "Order not found")
    if all(v["trang_thai"] == "da_thanh_toan" for v in ve_online):
        return _rsp("02", "Order already confirmed")

    try:
        so_tien = int(so_tien_cong)
    except ValueError:
        return _rsp("04", "Invalid amount")
    if so_tien != sum(int(v["gia"]) for v in ve_online) * 100:
        return _rsp("04", "Invalid amount")

    if thanh_cong:
        if not repo.ghi_nhan_thanh_toan_ngay(ma_dat_cho, ma_giao_dich_cong):
            # Tiền đã trừ nhưng vé đã quá hạn/không còn giữ chỗ (trả đúng sát giờ): dừng cổng gọi lại, cần hoàn tiền thủ công (UC-22)
            return _rsp("02", "Order expired")
    else:
        repo.huy_thanh_toan_ngay(ma_dat_cho)
    return _rsp("00", "Confirm Success")


def xu_ly_ipn(tham_so: dict) -> dict:
    if not vnpay_service.chu_ky_hop_le(tham_so):
        return _rsp("97", "Invalid signature")
    thanh_cong = tham_so.get("vnp_ResponseCode") == "00" and tham_so.get("vnp_TransactionStatus", "00") == "00"
    return _ap_dung_ket_qua(
        vnpay_service.ma_dat_cho_tu_ma_giao_dich(tham_so.get("vnp_TxnRef", "")),
        tham_so.get("vnp_Amount", "0"),
        thanh_cong,
        str(tham_so.get("vnp_TransactionNo", "")),
    )


def xac_nhan_qua_truy_van(ma_giao_dich: str) -> dict:
    """Hỏi thẳng VNPay (querydr) kết quả của 1 giao dịch rồi đổi trạng thái vé như IPN — dùng khi IPN không tới được
    (VD sandbox chưa khai báo được IPN) hoặc làm dự phòng khi IPN tới trễ. Chỉ chạy ở chế độ sandbox; gọi lại bao nhiêu
    lần cũng an toàn (vé đã xử lý thì thôi). Dữ liệu lấy từ phản hồi có chữ ký của VNPay, không tin dữ liệu khách gửi.

    Trả `trang_thai`: bo_qua (không ở chế độ sandbox) · da_xac_nhan · thanh_cong · that_bai · chua_thanh_toan
    (VNPay chưa có/đang xử lý giao dịch) · chua_ro (không hỏi được VNPay) · khong_hop_le."""
    if VNPAY_CHE_DO != "sandbox":
        return {"trang_thai": "bo_qua"}
    ma_dat_cho = vnpay_service.ma_dat_cho_tu_ma_giao_dich(ma_giao_dich)
    cac_ve = repo.lay_ve_cua_dat_cho(ma_dat_cho)
    ve_online = [v for v in cac_ve if v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v["trang_thai"] in ("giu_cho", "da_thanh_toan")]
    if not ve_online:
        return {"trang_thai": "khong_hop_le"}
    if all(v["trang_thai"] == "da_thanh_toan" for v in ve_online):
        return {"trang_thai": "da_xac_nhan"}

    kq = vnpay_service.truy_van_giao_dich(ma_giao_dich)
    if kq is None:
        return {"trang_thai": "chua_ro"}
    if kq.get("vnp_ResponseCode") != "00" or kq.get("vnp_TxnRef") != ma_giao_dich:
        return {"trang_thai": "chua_thanh_toan"}  # VNPay chưa có giao dịch này (khách chưa tới cổng)
    tinh_trang = kq.get("vnp_TransactionStatus")
    if tinh_trang not in ("00", "02"):
        return {"trang_thai": "chua_thanh_toan"}  # 01: đang xử lý, các mã khác: chưa có kết luận
    rsp = _ap_dung_ket_qua(ma_dat_cho, str(kq.get("vnp_Amount", "0")), tinh_trang == "00", str(kq.get("vnp_TransactionNo", "")))
    if rsp["RspCode"] in ("00", "02") and tinh_trang == "00":
        return {"trang_thai": "thanh_cong" if rsp["RspCode"] == "00" else "da_xac_nhan"}
    return {"trang_thai": "that_bai" if tinh_trang == "02" else "khong_hop_le"}


def quet_giao_dich_dang_cho() -> int:
    """Job: hỏi VNPay kết quả các lượt đang chờ thanh toán (khách thanh toán xong rồi đóng trình duyệt, IPN không tới).
    Trả số lượt đã có kết luận."""
    if VNPAY_CHE_DO != "sandbox":
        return 0
    so_ket_luan = 0
    bay_gio = datetime.datetime.now(datetime.timezone.utc)
    for ma_giao_dich in repo.lay_ma_giao_dich_dang_cho():
        # VNPay từ chối hỏi lặp sát nhau (94) và khách còn đang ở cổng thì chưa có gì để hỏi: chỉ hỏi khi giao dịch đã
        # đủ cũ — tới lúc đó trang kết quả (nếu khách quay về) đã tự hỏi rồi, job chỉ bắt ca khách đóng trình duyệt
        try:
            tuoi_giay = (bay_gio - vnpay_service.doc_gio_vn(vnpay_service.ngay_tao_tu_ma_giao_dich(ma_giao_dich))).total_seconds()
        except ValueError:
            continue
        if tuoi_giay < TUOI_TOI_THIEU_DE_QUET_GIAY:
            continue
        if xac_nhan_qua_truy_van(ma_giao_dich)["trang_thai"] in ("thanh_cong", "that_bai"):
            so_ket_luan += 1
    return so_ket_luan


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
