"""Tác vụ chạy định kỳ tự động hoàn tiền cho khách chờ quá 3 tiếng do lỗi nhà xe — UC-43.

Theo quy định tại NGHIEP_VU.md mục 7 & UC-43:
- Chuyến gap_su_co do loi_nha_xe kéo dài >= 3 tiếng.
- Tự động hoàn 100% tiền vé cho các vé da_thanh_toan chưa hủy.
- Vé VẪN GIỮ NGUYÊN trạng thái da_thanh_toan (không hủy vé), nhà xe vẫn tiếp tục chở khách miễn phí.
"""

from app.services.hoan_tien_service import quet_va_hoan_tien_su_co_qua_3_tieng


def chay_job_quet_hoan_tien_tu_dong():
    """Hàm thực thi job được scheduler gọi định kỳ."""
    so_ve = quet_va_hoan_tien_su_co_qua_3_tieng()
    if so_ve > 0:
        print(f"[JOB QUET HOAN TIEN UC-43] Da tu dong hoan tien thanh cong cho {so_ve} ve.")
    return so_ve

