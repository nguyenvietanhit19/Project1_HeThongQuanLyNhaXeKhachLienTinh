"""Hàm dựng MÃ HIỂN THỊ tự sinh: khu vực, điểm đón/trả, tuyến, loại xe, chuyến, vé.

Các hàm thuần (không đụng DB) — repository lấy số thứ tự từ sequence rồi gọi ở đây (xem repositories/ma_repository.py), nên mã
sinh trong giao dịch INSERT như trước nhưng logic nằm ở Python, unit test được. Mã chỉ để người đọc/tra cứu; khóa chính vẫn là id UUID.

Số thứ tự đệm 0 bằng định dạng của Python — KHÔNG cắt khi số dài hơn độ rộng (khác lpad() của Postgres cắt bớt, từng làm mã bị
trùng ở mục thứ 1000/1.000.000): `ma_khu_vuc(1000)` = "KV1000", không phải "KV100".
"""

import datetime
from zoneinfo import ZoneInfo

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _so(n: int, so_chu_so: int) -> str:
    return f"{int(n):0{so_chu_so}d}"


def ma_khu_vuc(so_thu_tu: int) -> str:
    """KV001"""
    return "KV" + _so(so_thu_tu, 3)


def ma_tuyen(so_thu_tu: int) -> str:
    """T001"""
    return "T" + _so(so_thu_tu, 3)


def ma_loai_xe(so_thu_tu: int) -> str:
    """LX001"""
    return "LX" + _so(so_thu_tu, 3)


def ma_diem_don_tra(ma_khu_vuc_cua_diem: str, so_thu_tu_trong_khu_vuc: int) -> str:
    """KV001-DT001 — số thứ tự đếm riêng từng khu vực."""
    return f"{ma_khu_vuc_cua_diem}-DT{_so(so_thu_tu_trong_khu_vuc, 3)}"


def ma_ve(so_thu_tu: int) -> str:
    """VE000001"""
    return "VE" + _so(so_thu_tu, 6)


def ma_chuyen(ma_tuyen_cua_chuyen: str, ma_loai_xe_cua_chuyen: str, gio_khoi_hanh: datetime.datetime, chieu: str) -> str:
    """T001-LX001-261008-0800-DI — ngày giờ theo giờ Việt Nam; `chieu`: xuoi → DI, nguoc → VE."""
    if gio_khoi_hanh.tzinfo is None:
        raise ValueError("gio_khoi_hanh phải có múi giờ")
    gio_vn = gio_khoi_hanh.astimezone(MUI_GIO_VN)
    return f"{ma_tuyen_cua_chuyen}-{ma_loai_xe_cua_chuyen}-{gio_vn:%y%m%d-%H%M}-{'DI' if chieu == 'xuoi' else 'VE'}"


# ---------------------------------------------------------
# Mã nhân viên (KE_HOACH_MA_NHAN_VIEN.md): tiền tố theo vai trò + số thứ tự 4 chữ số
# ---------------------------------------------------------
# Khóa là `nguoi_dung.vai_tro` (cán bộ có tài khoản) hoặc "tai_xe" (hồ sơ tài xế, không có tài khoản). Phụ xe dùng mã của
# tài khoản "phu_xe" nên không có mã riêng ở hồ sơ. Khách hàng không có mã (không có trong bảng này).
TIEN_TO_NHAN_VIEN = {
    "tai_xe": "TX",
    "phu_xe": "PX",
    "nhan_vien_quay_ve": "QV",
    "nhan_vien_gui_hang": "GH",
    "dieu_do_vien": "DDV",
    "ke_toan": "KT",
    "quan_ly_nhan_su": "NS",
    "quan_ly": "QL",
}

# Mã dành riêng cho tài khoản quản lý gốc (đặt cố định trong migration); số thứ tự cấp tự động luôn bắt đầu từ 1.
MA_QUAN_LY_GOC = "QL0000"


def ma_nhan_vien(vai_tro: str, so_thu_tu: int) -> str:
    """PX0001, DDV0012 — số đệm 0 đủ 4 chữ số, quá 9999 thì dài ra chứ không cắt (PX10000)."""
    tien_to = TIEN_TO_NHAN_VIEN.get(vai_tro)
    if tien_to is None:
        raise ValueError(f"Vai trò '{vai_tro}' không có mã nhân viên")
    if so_thu_tu < 1:
        raise ValueError("Số thứ tự mã nhân viên bắt đầu từ 1 (số 0 dành cho tài khoản quản lý gốc)")
    return tien_to + _so(so_thu_tu, 4)
