"""Xử lý kết quả thanh toán VNPay — IPN (nguồn sự thật) và trang kết quả trả về cho trình duyệt (chỉ để hiển thị).

NGHIEP_VU.md mục 6, UC-05 nhánh A. Dùng chung cho cổng giả lập lẫn VNPay sandbox thật.

IPN: chỉ đổi trạng thái vé khi chữ ký đúng, số tiền khớp và vé chưa được xử lý — vì VNPay có thể gọi lại nhiều lần.
Có 2 loại giao dịch, phân biệt qua tiền tố mã giao dịch (`vnp_TxnRef`): của cả lượt đặt (`DC…`, trả các vé "thanh toán ngay")
và của 1 vé riêng lẻ (`VE…`, khách trả online cho vé đã chọn "thanh toán tại quầy" — trang Booking). Giao dịch 1 vé thất bại
thì vé vẫn là "trả tại quầy" như cũ, không hết hạn.
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


TUOI_TOI_DA_DE_QUET_GIAY = 1200  # ngừng hỏi VNPay giao dịch đã quá 20 phút (vé trả tại quầy bỏ dở thì thôi, không hỏi mãi)


def _ap_dung_ket_qua_ve(ma_ve: str, so_tien_cong: str, thanh_cong: bool, ma_giao_dich_cong: str) -> dict:
    """Kết quả giao dịch thanh toán riêng 1 vé: thành công → vé `da_thanh_toan`; thất bại → giữ nguyên (vẫn trả tại quầy)."""
    ve = repo.lay_ve_theo_ma_ve(ma_ve)
    if not ve:
        return _rsp("01", "Order not found")
    if ve["trang_thai"] == "da_thanh_toan":
        return _rsp("02", "Order already confirmed")
    try:
        so_tien = int(so_tien_cong)
    except ValueError:
        return _rsp("04", "Invalid amount")
    if so_tien != int(ve["gia"]) * 100:
        return _rsp("04", "Invalid amount")
    if thanh_cong and not repo.ghi_nhan_thanh_toan_ve_le(ma_ve, ma_giao_dich_cong):
        # Tiền đã trừ nhưng vé đã bị hủy/hết hạn trong lúc thanh toán: dừng cổng gọi lại, cần hoàn tiền thủ công (UC-22)
        return _rsp("02", "Order expired")
    return _rsp("00", "Confirm Success")


def xu_ly_ipn(tham_so: dict) -> dict:
    if not vnpay_service.chu_ky_hop_le(tham_so):
        return _rsp("97", "Invalid signature")
    thanh_cong = tham_so.get("vnp_ResponseCode") == "00" and tham_so.get("vnp_TransactionStatus", "00") == "00"
    ma_giao_dich = tham_so.get("vnp_TxnRef", "")
    ap_dung = _ap_dung_ket_qua_ve if vnpay_service.la_giao_dich_cua_ve(ma_giao_dich) else _ap_dung_ket_qua
    return ap_dung(
        vnpay_service.ma_dat_cho_tu_ma_giao_dich(ma_giao_dich),  # phần trước dấu "-": mã đặt chỗ, hoặc mã vé nếu là giao dịch 1 vé
        tham_so.get("vnp_Amount", "0"),
        thanh_cong,
        str(tham_so.get("vnp_TransactionNo", "")),
    )


def _hoi_vnpay(ma_giao_dich: str) -> tuple[str, dict | None]:
    """Hỏi VNPay (querydr) kết quả 1 giao dịch. Trả (kết luận, phản hồi): kết luận là `chua_ro` (không hỏi được) ·
    `chua_thanh_toan` (VNPay chưa có giao dịch / đang xử lý) · `00` (thanh toán thành công) · `02` (thất bại)."""
    kq = vnpay_service.truy_van_giao_dich(ma_giao_dich)
    if kq is None:
        return "chua_ro", None
    if kq.get("vnp_ResponseCode") != "00" or kq.get("vnp_TxnRef") != ma_giao_dich:
        return "chua_thanh_toan", None  # VNPay chưa có giao dịch này (khách chưa tới cổng)
    tinh_trang = kq.get("vnp_TransactionStatus")
    if tinh_trang not in ("00", "02"):
        return "chua_thanh_toan", None  # 01: đang xử lý, các mã khác: chưa có kết luận
    return tinh_trang, kq


def xac_nhan_qua_truy_van(ma_giao_dich: str) -> dict:
    """Hỏi thẳng VNPay (querydr) kết quả của 1 giao dịch rồi đổi trạng thái vé như IPN — dùng khi IPN không tới được
    (VD sandbox chưa khai báo được IPN) hoặc làm dự phòng khi IPN tới trễ. Chỉ chạy ở chế độ sandbox; gọi lại bao nhiêu
    lần cũng an toàn (vé đã xử lý thì thôi). Dữ liệu lấy từ phản hồi có chữ ký của VNPay, không tin dữ liệu khách gửi.

    Trả `trang_thai`: bo_qua (không ở chế độ sandbox) · da_xac_nhan · thanh_cong · that_bai · chua_thanh_toan
    (VNPay chưa có/đang xử lý giao dịch) · chua_ro (không hỏi được VNPay) · khong_hop_le."""
    if VNPAY_CHE_DO != "sandbox":
        return {"trang_thai": "bo_qua"}
    ma_goc = vnpay_service.ma_dat_cho_tu_ma_giao_dich(ma_giao_dich)  # mã đặt chỗ, hoặc mã vé nếu là giao dịch 1 vé
    cua_ve = vnpay_service.la_giao_dich_cua_ve(ma_giao_dich)
    if cua_ve:
        ve = repo.lay_ve_theo_ma_ve(ma_goc)
        if not ve:
            return {"trang_thai": "khong_hop_le"}
        if ve["trang_thai"] == "da_thanh_toan":
            return {"trang_thai": "da_xac_nhan"}
    else:
        cac_ve = repo.lay_ve_cua_dat_cho(ma_goc)
        ve_online = [v for v in cac_ve if v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v["trang_thai"] in ("giu_cho", "da_thanh_toan")]
        if not ve_online:
            return {"trang_thai": "khong_hop_le"}
        if all(v["trang_thai"] == "da_thanh_toan" for v in ve_online):
            return {"trang_thai": "da_xac_nhan"}

    ket_luan, kq = _hoi_vnpay(ma_giao_dich)
    if kq is None:
        return {"trang_thai": ket_luan}
    ap_dung = _ap_dung_ket_qua_ve if cua_ve else _ap_dung_ket_qua
    rsp = ap_dung(ma_goc, str(kq.get("vnp_Amount", "0")), ket_luan == "00", str(kq.get("vnp_TransactionNo", "")))
    if ket_luan == "00":
        if rsp["RspCode"] == "00":
            return {"trang_thai": "thanh_cong"}
        return {"trang_thai": "da_xac_nhan" if rsp["RspCode"] == "02" else "khong_hop_le"}
    return {"trang_thai": "that_bai"}


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
        if not TUOI_TOI_THIEU_DE_QUET_GIAY <= tuoi_giay <= TUOI_TOI_DA_DE_QUET_GIAY:
            continue
        if xac_nhan_qua_truy_van(ma_giao_dich)["trang_thai"] in ("thanh_cong", "that_bai"):
            so_ket_luan += 1
    return so_ket_luan


def _ma_dat_cho_cua_giao_dich(ma_giao_dich: str) -> str | None:
    ma_goc = vnpay_service.ma_dat_cho_tu_ma_giao_dich(ma_giao_dich)
    if not vnpay_service.la_giao_dich_cua_ve(ma_giao_dich):
        return ma_goc
    ve = repo.lay_ve_theo_ma_ve(ma_goc)
    return ve["ma_dat_cho"] if ve else None


def doc_ket_qua_tra_ve(tham_so: dict) -> dict:
    """Trình duyệt khách được cổng đưa về trang của mình: kiểm tra chữ ký rồi cho biết kết quả để HIỂN THỊ.
    Không đổi trạng thái vé ở đây — việc đó chỉ làm ở IPN."""
    if not vnpay_service.chu_ky_hop_le(tham_so):
        return {"hop_le": False, "thanh_cong": False, "ma_dat_cho": None, "ma_phan_hoi": None}
    return {
        "hop_le": True,
        "thanh_cong": tham_so.get("vnp_ResponseCode") == "00" and tham_so.get("vnp_TransactionStatus", "00") == "00",
        "ma_dat_cho": _ma_dat_cho_cua_giao_dich(tham_so.get("vnp_TxnRef", "")),
        "ma_phan_hoi": tham_so.get("vnp_ResponseCode"),
    }
