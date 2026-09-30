"""Xem/sửa/xóa chuyến từ góc nhìn quản lý — trang "Chuyến", UC-18 (NGHIEP_VU.md
mục 3.5). Chỉ xem, đổi giờ, xóa chuyến CHƯA gán xe/chưa khởi hành/chưa có vé;
gán xe, đổi xe, xử lý sự cố (UC-19/20/40/44) thuộc điều độ viên, không ở đây.
"""

import datetime
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import chuyen_xe_repository as repo
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def danh_sach_chuyen(
    tuyen_id: str | None,
    chieu: str | None,
    tu_ngay: datetime.date | None,
    den_ngay: datetime.date | None,
    trang_thai: str | None,
    da_gan_xe: bool | None,
    lich_chay_id: str | None = None,
) -> list[dict]:
    # tu_ngay/den_ngay là ngày lịch (không có giờ) theo giờ VN — quy đổi thành
    # mốc TIMESTAMPTZ đúng nửa đêm giờ VN, đến ngày lấy tới HẾT ngày đó (mốc
    # đầu ngày hôm sau, so sánh "<").
    tu_thoi_diem = datetime.datetime.combine(tu_ngay, datetime.time.min, tzinfo=MUI_GIO_VN) if tu_ngay else None
    den_thoi_diem = (
        datetime.datetime.combine(den_ngay + datetime.timedelta(days=1), datetime.time.min, tzinfo=MUI_GIO_VN)
        if den_ngay
        else None
    )
    return repo.danh_sach_chuyen(tuyen_id, chieu, tu_thoi_diem, den_thoi_diem, trang_thai, da_gan_xe, lich_chay_id)


def chi_tiet_chuyen(chuyen_id: str) -> dict:
    chuyen = repo.tim_chuyen_theo_id_ql(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    return chuyen


def _kiem_tra_sua_xoa_duoc(chuyen: dict) -> None:
    if chuyen["xe_id"]:
        raise GiaTriLoi("Chuyến đã được gán xe — việc này thuộc điều độ viên, không sửa/xóa được ở đây")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chỉ sửa/xóa được chuyến chưa khởi hành")
    if chuyen["so_ve_dang_hoat_dong"] > 0:
        raise GiaTriLoi(f"Chuyến đã có {chuyen['so_ve_dang_hoat_dong']} vé giữ chỗ/đã thanh toán — không thể sửa/xóa")


def sua_gio_chuyen(chuyen_id: str, gio: datetime.time) -> dict:
    chuyen = repo.tim_chuyen_theo_id_ql(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    _kiem_tra_sua_xoa_duoc(chuyen)
    # Chỉ đổi GIỜ, giữ nguyên ngày hiện có của chuyến (tính theo giờ VN) —
    # muốn chuyến ở ngày khác thì xóa rồi sinh lại từ lịch chạy.
    ngay_hien_tai = chuyen["gio_khoi_hanh"].astimezone(MUI_GIO_VN).date()
    gio_khoi_hanh = datetime.datetime.combine(ngay_hien_tai, gio.replace(tzinfo=None), tzinfo=MUI_GIO_VN)
    if gio_khoi_hanh <= datetime.datetime.now(MUI_GIO_VN):
        raise GiaTriLoi("Giờ khởi hành mới đã qua — hãy chọn giờ còn ở phía trước")
    # Chỉ sửa được giờ xuất phát — chặn nếu trùng loại xe + trùng giờ xuất
    # phát với 1 chuyến khác trong đúng ngày đó (cùng loại xe = cùng "nguồn
    # xe" khả dụng, 2 chuyến cùng giờ sẽ không đủ xe để phục vụ cả 2).
    if repo.tim_trung_loai_xe_va_gio(str(chuyen["loai_xe_id"]), gio_khoi_hanh, chuyen_id):
        raise GiaTriLoi("Đã có chuyến khác cùng loại xe và cùng giờ xuất phát trong ngày này")
    repo.sua_gio_chuyen(chuyen_id, gio_khoi_hanh)
    return repo.tim_chuyen_theo_id_ql(chuyen_id)


def xoa_chuyen(chuyen_id: str) -> None:
    chuyen = repo.tim_chuyen_theo_id_ql(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    _kiem_tra_sua_xoa_duoc(chuyen)
    try:
        repo.xoa_chuyen(chuyen_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: chuyến này vẫn còn dữ liệu liên quan (vé/đơn hàng)")
