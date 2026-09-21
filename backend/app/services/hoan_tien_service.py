"""Service xử lý nghiệp vụ Kế toán & Hoàn tiền — NGHIEP_VU.md mục 7, 8.8, 11.

Hiện thực hóa:
- UC-21: Tự động tính & thông báo hoàn tiền khi hủy chuyến do sự cố khách quan
- UC-22: Kế toán chuyển khoản hoàn tiền thủ công (lưu vết đối soát ngân hàng)
- UC-43: Tự động hoàn tiền khi khách chờ >= 3 tiếng do lỗi nhà xe (vẫn chở miễn phí)
- UC-39: Báo cáo thống kê tài chính doanh thu cho Kế toán
"""

import asyncio
from typing import Any
from uuid import uuid4

from app.repositories import lich_su_hoan_tien_repository as repo
from app.services.websocket_manager import manager
from app.utils.loi import GiaTriLoi


def _gui_thong_bao_websocket(nguoi_dung_id: str | None, noi_dung: str) -> None:
    """Gửi thông báo real-time an toàn qua WebSocket nếu khách hàng đang online."""
    if not nguoi_dung_id:
        return
    try:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast(str(nguoi_dung_id), noi_dung))
        except RuntimeError:
            pass
    except Exception:
        pass


def _hoan_tien_cong_thanh_toan(ma_giao_dich_goc: str, so_tien: int) -> tuple[bool, str | None]:
    """Tích hợp hoặc giả lập gọi API hoàn tiền qua cổng thanh toán VNPay.
    
    Quy tắc:
    - Nếu mã giao dịch không rỗng và không chứa từ 'FAIL' -> Giả lập thành công.
    - Trả về tuple: (thanh_cong: bool, ma_giao_dich_hoan_tien: str | None)
    """
    if not ma_giao_dich_goc or "FAIL" in ma_giao_dich_goc.upper():
        return False, None
    
    ma_hoan = f"REFUND_{uuid4().hex[:12].upper()}"
    return True, ma_hoan


# ====================================================================
# 1. Tạo và Xử lý Hoàn tiền độc lập (Core Engine)
# ====================================================================

def tao_hoan_tien(ve_id: str, ly_do: str, so_tien: int | None = None) -> dict:
    """Tạo bản ghi hoàn tiền cho 1 vé và xử lý hoàn tự động nếu thanh toán online.
    
    - Kiểm tra vé tồn tại.
    - Idempotency: nếu đã có bản ghi hoàn tiền trước đó, trả về bản ghi hiện tại tránh hoàn trùng.
    - Nếu vé có ma_giao_dich_cong_thanh_toan (online VNPay) -> thử hoàn tự động.
    - Nếu tiền mặt hoặc hoàn online thất bại -> trạng thái 'cho_xu_ly' để Kế toán xử lý (UC-22).
    """
    ve = repo.tim_ve_theo_id(ve_id)
    if not ve:
        raise GiaTriLoi(f"Vé với ID {ve_id} không tồn tại trong hệ thống")

    # Kiểm tra bản ghi hoàn tiền đã tồn tại chưa (tránh trùng lặp hoàn tiền)
    bghi_hien_tai = repo.tim_theo_ve_id(ve_id)
    if bghi_hien_tai:
        return bghi_hien_tai

    tien_hoan = so_tien if (so_tien is not None and so_tien > 0) else int(ve["gia"])
    ma_giao_dich_online = ve.get("ma_giao_dich_cong_thanh_toan")
    phuong_thuc = ve.get("phuong_thuc_thanh_toan")

    trang_thai = "cho_xu_ly"
    ma_hoan_tien = None

    # Nếu khách thanh toán online qua cổng (chuyen_khoan VNPay)
    if phuong_thuc == "chuyen_khoan" and ma_giao_dich_online:
        thanh_cong, ma_hoan = _hoan_tien_cong_thanh_toan(ma_giao_dich_online, tien_hoan)
        if thanh_cong:
            trang_thai = "da_hoan_tu_dong"
            ma_hoan_tien = ma_hoan

    bghi = repo.tao_hoan_tien(
        ve_id=ve_id,
        ly_do=ly_do,
        so_tien=tien_hoan,
        trang_thai=trang_thai,
        ma_giao_dich_hoan_tien=ma_hoan_tien,
    )

    # Gửi thông báo WebSocket cho khách nếu có tài khoản
    if ve.get("khach_hang_id"):
        thong_diep = (
            f"Bạn đã được hoàn tiền {tien_hoan:,}đ cho vé ghế {ve.get('so_ghe')} "
            f"(Mã đặt: {ve.get('ma_dat_cho')}) thành công qua cổng thanh toán."
            if trang_thai == "da_hoan_tu_dong"
            else f"Yêu cầu hoàn tiền {tien_hoan:,}đ cho vé ghế {ve.get('so_ghe')} "
            f"(Mã đặt: {ve.get('ma_dat_cho')}) đang được bộ phận Kế toán xử lý."
        )
        _gui_thong_bao_websocket(str(ve["khach_hang_id"]), thong_diep)

    return bghi


# ====================================================================
# 2. UC-21: Hủy Chuyến do Sự cố Khách quan & Tự động Hoàn vé ⏱
# ====================================================================

def xu_ly_hoan_tien_chuyen_bi_huy(chuyen_id: str) -> list[dict]:
    """UC-21: Xử lý khi chuyến bị hủy giữa đường do sự cố khách quan (thiên tai, sạt lở...).
    
    Quy định tại NGHIEP_VU.md mục 7 & UC-21:
    - Tìm toàn bộ vé da_thanh_toan trên chuyến.
    - Đổi trạng thái vé sang da_huy (hết nghĩa vụ phục vụ).
    - Hoàn 100% tiền vé cho khách (ly_do = 'bat_kha_khang_khong_hoan_thanh').
    """
    danh_sach_ve = repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
    ket_qua = []

    for ve in danh_sach_ve:
        # Chuyển vé sang da_huy
        repo.cap_nhat_ve_da_huy(ve["id"])

        # Tạo bản ghi hoàn tiền
        bghi_hoan = tao_hoan_tien(
            ve_id=ve["id"],
            ly_do="bat_kha_khang_khong_hoan_thanh",
            so_tien=int(ve["gia"]),
        )
        ket_qua.append(bghi_hoan)

    return ket_qua


# ====================================================================
# 3. UC-22: Kế toán Duyệt Chuyển khoản Thủ công
# ====================================================================

def lay_danh_sach_cho_xu_ly() -> list[dict]:
    """UC-22: Kế toán xem toàn bộ các khoản đang chờ chuyển khoản thủ công."""
    return repo.lay_danh_sach_cho_xu_ly()


def duyet_hoan_tien_thu_cong(
    hoan_tien_id: str,
    nhan_vien_xu_ly_id: str,
    thong_tin_ngan_hang: dict,
) -> dict:
    """UC-22: Kế toán xác nhận đã chuyển khoản ngoài hệ thống và lưu vết thông tin nhận.
    
    - Kiểm tra bản ghi hoàn tiền đang ở trạng thái 'cho_xu_ly'.
    - Cập nhật số tài khoản, tên ngân hàng, tên chủ tài khoản nhận.
    - Cập nhật trạng thái 'da_hoan_chuyen_khoan_thu_cong', nhan_vien_xu_ly_id và thoi_gian_hoan_xong.
    """
    bghi = repo.tim_theo_id(hoan_tien_id)
    if not bghi:
        raise GiaTriLoi("Bản ghi hoàn tiền không tồn tại trong hệ thống")

    if bghi["trang_thai"] != "cho_xu_ly":
        raise GiaTriLoi(
            f"Khoản hoàn tiền này không ở trạng thái chờ xử lý (trạng thái hiện tại: {bghi['trang_thai']})"
        )

    stk = thong_tin_ngan_hang.get("so_tai_khoan_nhan", "").strip()
    ngan_hang = thong_tin_ngan_hang.get("ten_ngan_hang_nhan", "").strip()
    chu_tk = thong_tin_ngan_hang.get("ten_chu_tai_khoan_nhan", "").strip()

    if not stk or not ngan_hang or not chu_tk:
        raise GiaTriLoi("Bắt buộc cung cấp đầy đủ: số tài khoản, tên ngân hàng và tên chủ tài khoản nhận")

    cap_nhat = repo.cap_nhat_chuyen_khoan_thu_cong(
        hoan_tien_id=hoan_tien_id,
        nhan_vien_xu_ly_id=nhan_vien_xu_ly_id,
        so_tai_khoan_nhan=stk,
        ten_ngan_hang_nhan=ngan_hang,
        ten_chu_tai_khoan_nhan=chu_tk,
    )

    if not cap_nhat:
        raise GiaTriLoi("Cập nhật hoàn tiền thủ công thất bại, vui lòng thử lại")

    # Gửi thông báo WebSocket cho khách
    ve = repo.tim_ve_theo_id(bghi["ve_id"])
    if ve and ve.get("khach_hang_id"):
        _gui_thong_bao_websocket(
            str(ve["khach_hang_id"]),
            f"Bộ phận Kế toán đã hoàn tất chuyển khoản {bghi['so_tien']:,}đ vào tài khoản {stk} ({ngan_hang}).",
        )

    return cap_nhat


def lay_danh_sach_lich_su(
    limit: int = 50,
    offset: int = 0,
    trang_thai: str | None = None,
    tu_ngay: str | None = None,
    den_ngay: str | None = None,
) -> list[dict]:
    """Kế toán tra cứu lịch sử hoàn tiền phân trang toàn hệ thống."""
    return repo.lay_danh_sach_lich_su(
        limit=limit,
        offset=offset,
        trang_thai=trang_thai,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
    )


# ====================================================================
# 4. UC-43: Tự động Hoàn tiền Sự cố Lỗi nhà xe >= 3 tiếng ⏱
# ====================================================================

def quet_va_hoan_tien_su_co_qua_3_tieng() -> int:
    """UC-43: Tác vụ quét tự động (Job định kỳ).
    
    Điều kiện theo NGHIEP_VU.md mục 7 & UC-43:
    - Chuyến đang gap_su_co với loai_su_co = 'loi_nha_xe' kéo dài >= 3 tiếng.
    - Với mỗi vé da_thanh_toan chưa tự hủy và chưa có bản ghi hoàn tiền:
      - Tạo dòng hoàn tiền ly_do = 'tu_dong_hoan_qua_3_tieng'.
      - ĐẶC BIỆT: Vé VẪN GIỮ NGUYÊN trạng thái da_thanh_toan (không hủy vé).
      - Nhà xe tiếp tục nghĩa vụ chở khách miễn phí khi có xe thay thế.
    """
    chuyen_list = repo.tim_chuyen_gap_su_co_nha_xe_qua_3_tieng()
    tong_ve_hoan = 0

    for chuyen in chuyen_list:
        ve_list = repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen["id"])
        for ve in ve_list:
            # Kiểm tra xem vé này đã từng được hoàn tiền chưa
            bghi_hien_co = repo.tim_theo_ve_id(ve["id"])
            if not bghi_hien_co:
                # Tạo hoàn tiền nhưng KHÔNG hủy vé (vé vẫn da_thanh_toan)
                tao_hoan_tien(
                    ve_id=ve["id"],
                    ly_do="tu_dong_hoan_qua_3_tieng",
                    so_tien=int(ve["gia"]),
                )
                tong_ve_hoan += 1

                # Gửi thông báo WebSocket xin lỗi khách và xác nhận chở miễn phí
                if ve.get("khach_hang_id"):
                    _gui_thong_bao_websocket(
                        str(ve["khach_hang_id"]),
                        f"Nhà xe chân thành xin lỗi vì sự cố chậm trễ. "
                        f"Toàn bộ 100% tiền vé ({int(ve['gia']):,}đ) đã được kích hoạt hoàn lại. "
                        f"Quý khách vẫn được tiếp tục hành trình hoàn toàn MIỄN PHÍ khi xe sẵn sàng.",
                    )

    return tong_ve_hoan


# ====================================================================
# 5. UC-39: Báo cáo Thống kê Doanh thu dành cho Kế toán
# ====================================================================

def thong_ke_doanh_thu_ke_toan(tu_ngay: str | None = None, den_ngay: str | None = None) -> dict:
    """UC-39 (Kế toán): Thống kê tổng hợp doanh thu vé, cước gửi hàng, tiền hoàn và doanh thu thuần."""
    return repo.thong_ke_tai_chinh_tong_hop(tu_ngay=tu_ngay, den_ngay=den_ngay)

