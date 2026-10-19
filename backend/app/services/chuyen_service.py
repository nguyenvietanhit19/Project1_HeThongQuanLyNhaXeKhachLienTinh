"""Xem/sửa/xóa chuyến từ góc nhìn quản lý — trang "Chuyến", UC-18 (NGHIEP_VU.md
mục 3.5). Chỉ xem, đổi giờ, xóa chuyến CHƯA gán xe/chưa khởi hành/chưa có vé;
gán xe, đổi xe, xử lý sự cố (UC-19/20/40/44) thuộc điều độ viên, không ở đây.
"""

import datetime
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import chuyen_xe_repository as repo
from app.repositories import xe_repository as xe_repo
from app.services import gia_ve_service
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
    # Giá vé của chuyến: bộ giá áp dụng cho ngày khởi hành (giờ VN) × hệ số của chuyến và hệ số từng ghế (đều chốt lúc sinh chuyến) — None nếu ngày đó chưa có giá
    ngay = chuyen["gio_khoi_hanh"].astimezone(MUI_GIO_VN).date()
    loai_xe = xe_repo.tim_loai_xe_theo_id(str(chuyen["loai_xe_id"]))
    so_do = loai_xe["so_do_ghe"] if loai_xe else []
    cac_ma_ghe = [g["ma_ghe"] for g in so_do]
    he_so_ghe = chuyen.get("he_so_ghe") or {}
    chuyen["bang_gia"] = gia_ve_service.bang_gia_cua_chuyen(
        str(chuyen["tuyen_id"]), chuyen["chieu"], ngay, chuyen["he_so_gia"], cac_ma_ghe, he_so_ghe
    )
    # Sơ đồ ghế kèm hệ số đã chốt + vé đang chiếm ghế, để vẽ sơ đồ có giá và trạng thái ở màn chi tiết
    chuyen["so_tang"] = 2 if any(g["tang"] == 2 for g in so_do) else 1
    chuyen["so_do_ghe"] = [{**g, "he_so": he_so_ghe.get(g["ma_ghe"], 1)} for g in so_do]
    chuyen["cac_ve_tren_ghe"] = [{**v, "gia": int(v["gia"])} for v in repo.danh_sach_ve_dang_chiem_ghe(chuyen_id)]
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
    return chi_tiet_chuyen(chuyen_id)  # đủ bảng giá + sơ đồ ghế để giao diện vẽ lại ngay


def xoa_chuyen(chuyen_id: str) -> None:
    chuyen = repo.tim_chuyen_theo_id_ql(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    _kiem_tra_sua_xoa_duoc(chuyen)
    try:
        repo.xoa_chuyen(chuyen_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: chuyến này vẫn còn dữ liệu liên quan (vé/đơn hàng)")
