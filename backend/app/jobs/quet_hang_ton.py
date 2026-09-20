"""Tác vụ chạy định kỳ quét cảnh báo và chuyển hàng tồn — UC-46 (NGHIEP_VU.md mục 10.3 & mục 12).

- Mốc >= 7 ngày: Bật cờ co_canh_bao_cho_lau để nhắc nhân viên quầy xử lý (UC-25).
- Mốc >= 14 ngày: Chuyển hẳn sang qua_han_luu_kho ("hàng tồn").
- Không tự động hủy/thanh lý hàng của khách (luôn chờ con người xử lý).
"""

from app.services.gui_hang_service import quet_canh_bao_va_chuyen_hang_ton


def chay_job_quet_hang_ton():
    """Hàm thực thi job được APScheduler gọi định kỳ."""
    ket_qua = quet_canh_bao_va_chuyen_hang_ton()
    so_cb = ket_qua["so_don_canh_bao_7_ngay"]
    so_ton = ket_qua["so_don_chuyen_ton_14_ngay"]
    if so_cb > 0 or so_ton > 0:
        print(f"[JOB QUET HANG TON] Da bat canh bao: {so_cb} don, chuyen hang ton: {so_ton} don.")
    return ket_qua

