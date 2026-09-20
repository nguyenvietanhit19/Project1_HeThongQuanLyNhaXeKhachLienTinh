"""Pydantic schemas cho vé xe — UC-05, UC-08, UC-09, UC-10, UC-11, UC-41, UC-42.

Mỗi schema ứng với đúng 1 request/response của 1 endpoint.
Route khai báo schema này; Service chứa logic nghiệp vụ (ARCHITECTURE.md mục 2).
"""

from datetime import datetime

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, field_validator


# ─── Request ──────────────────────────────────────────────────────────────────

class GiuChoRequest(BaseModel):
    """UC-05 bước 4: Khách bấm 'Cập nhật điểm đón trả' — đây là mốc khóa ghế.

    Dùng đoạn rộng nhất (khu_vuc đi/đến) theo mục 3.4 bước 4 NGHIEP_VU.md.
    diem_don_id và diem_tra_id sẽ được thu hẹp lại ở CapNhatDiemDonTraRequest.
    """
    chuyen_id: str
    danh_sach_ghe: list[str]    # Ví dụ: ["A1", "A2"] — khớp loai_xe.so_do_ghe
    diem_don_id: str            # van_phong đầu tiên hợp lệ của khu_vuc đi (đoạn rộng)
    diem_tra_id: str            # Điểm cuối hợp lệ của khu_vuc đến (đoạn rộng)

    @field_validator("danh_sach_ghe")
    @classmethod
    def phai_co_it_nhat_1_ghe(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Phải chọn ít nhất 1 ghế")
        if len(v) > 10:
            raise ValueError("Không được chọn quá 10 ghế trong 1 lần đặt")
        return v


class CapNhatDiemDonTraRequest(BaseModel):
    """UC-05 bước 5: Thu hẹp đoạn về điểm đón/trả cụ thể khách chọn.

    Đoạn mới luôn hẹp hơn hoặc bằng đoạn đã khóa ở bước 4 (mục 6) nên
    không cần khóa lại — Service chỉ UPDATE diem_don_id/diem_tra_id.
    """
    ma_dat_cho: str
    diem_don_id: str   # van_phong cụ thể khách chọn (loai = 'van_phong')
    diem_tra_id: str   # van_phong hoặc diem_dung khách chọn


class ChonLoaiHinhThanhToanRequest(BaseModel):
    """UC-05 bước 7: Khách chọn 'thanh toán ngay' hoặc 'thanh toán tại quầy'."""
    ma_dat_cho: str
    loai_hinh: str  # 'thanh_toan_ngay' | 'thanh_toan_tai_quay'

    @field_validator("loai_hinh")
    @classmethod
    def loai_hinh_hop_le(cls, v: str) -> str:
        if v not in ("thanh_toan_ngay", "thanh_toan_tai_quay"):
            raise ValueError("loai_hinh phải là 'thanh_toan_ngay' hoặc 'thanh_toan_tai_quay'")
        return v


class HuyGiuChoRequest(BaseModel):
    """UC-08: Hủy vé chưa thanh toán — trước mốc chốt lên xe (mục 7)."""
    ve_id: str


class BanVeTaiQuayRequest(BaseModel):
    """UC-09: Nhân viên quầy vé bán vé trực tiếp — thanh toán tại chỗ."""
    chuyen_id: str
    danh_sach_ghe: list[str]
    diem_don_id: str
    diem_tra_id: str
    phuong_thuc_thanh_toan: str  # 'tien_mat' | 'chuyen_khoan'
    # Khách vãng lai (không có tài khoản)
    ten_khach_vang_lai: str | None = None
    sdt_khach_vang_lai: str | None = None
    # Khách có tài khoản (tìm theo SĐT tại quầy, mục 8.4)
    khach_hang_id: str | None = None


class BanVeHotlineRequest(BaseModel):
    """UC-10: Nhân viên quầy vé đặt vé thay khách qua hotline."""
    chuyen_id: str
    danh_sach_ghe: list[str]
    diem_don_id: str
    diem_tra_id: str
    ten_khach_vang_lai: str | None = None
    sdt_khach_vang_lai: str | None = None
    khach_hang_id: str | None = None


class HuyVeNhanHoanRequest(BaseModel):
    """UC-41/UC-42: Khách chủ động hủy vé nhận hoàn khi chuyến hoãn/sự cố."""
    ve_id: str


# ─── Response ─────────────────────────────────────────────────────────────────

class VeResponse(BaseModel):
    """Thông tin 1 vé — dùng cho lịch sử vé, xác nhận đặt vé."""
    id: str
    chuyen_id: str
    so_ghe: str
    diem_don_id: str
    diem_don_ten: str
    diem_tra_id: str
    diem_tra_ten: str
    gia: int
    ma_dat_cho: str
    loai_hinh_thanh_toan: str
    phuong_thuc_thanh_toan: str | None
    trang_thai: str
    gio_bat_dau_dem_han: datetime | None
    han_giu_cho_den: datetime | None
    gio_thanh_toan: datetime | None
    ngay_tao: datetime


class GiuChoResponse(BaseModel):
    """Response sau khi giữ ghế thành công — trả về nhóm vé theo ma_dat_cho."""
    ma_dat_cho: str
    danh_sach_ve: list[VeResponse]
    yeu_cau_dat_coc: bool = False        # True khi ≥2 vé và tổng > 600.000đ
    so_ve_phai_tra_truoc: int = 0        # floor(so_ve × 50%) nếu cần cọc


class ThanhToanNgayResponse(BaseModel):
    """Response khi chọn 'thanh toán ngay' — trả URL redirect sang VNPay."""
    pay_url: str     # URL trang thanh toán VNPay sandbox
    ma_dat_cho: str
    han_thanh_toan: datetime   # Hạn 5 phút tính từ lúc này
