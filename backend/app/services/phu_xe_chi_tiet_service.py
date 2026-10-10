"""Phần "xem lại" của phụ xe: tổng quan 1 chuyến (hành khách lên/xuống, hàng hóa, hành trình),
chi tiết 1 đơn hàng (mốc đổi trạng thái + báo cáo thất lạc/hư hỏng) và danh sách chuyến đã chạy.

Chỉ ĐỌC dữ liệu — mọi thao tác ghi (lên/xuống xe, chất/dỡ hàng, báo sự cố) vẫn ở
chuyen_xe_service / ve_service / gui_hang_service. Phụ xe chỉ xem được chuyến của xe mình
(biên chế, NGHIEP_VU.md mục 3.2), kể cả khi chuyến đã hoàn thành/sự cố/hủy.
"""

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import ve_repository as ve_repo
from app.services import chuyen_xe_service
from app.services.chuyen_xe_service import lay_chuyen_cua_phu_xe
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongDuQuyen, KhongTimThay


def tong_quan_chuyen(chuyen_id: str, nguoi_dung_id: str) -> dict:
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    xe_id_hien_thi = chuyen["xe_thuc_te_id"] or chuyen["xe_id"]
    ten = chuyen_xe_repo.lay_ten_tuyen_va_bien_so(chuyen["tuyen_id"], xe_id_hien_thi)

    return {
        "chuyen": {
            "id": chuyen["id"],
            "ma": chuyen.get("ma"),
            "tuyen_ten": ten["tuyen_ten"],
            "chieu": chuyen["chieu"],
            "bien_so": ten["bien_so"],
            "gio_khoi_hanh": chuyen["gio_khoi_hanh"],
            "gio_xac_nhan_xuat_phat": chuyen.get("gio_xac_nhan_xuat_phat"),
            "gio_hoan_thanh": chuyen.get("gio_hoan_thanh"),
            "trang_thai": chuyen["trang_thai"],
            "dang_hoan": chuyen["dang_hoan"],
            "loai_su_co": chuyen.get("loai_su_co"),
            "ly_do_su_co": chuyen.get("ly_do_su_co"),
        },
        "hanh_trinh": chuyen_xe_service.hanh_trinh(chuyen_id, nguoi_dung_id),
        "hanh_khach": ve_repo.tim_hanh_khach_cua_chuyen(chuyen_id),
        "hang_hoa": don_hang_repo.tim_hang_hoa_cua_chuyen(chuyen_id),
    }


def chi_tiet_don_hang(don_hang_id: str, nguoi_dung_id: str) -> dict:
    """Đơn đã lên xe → phải là chuyến của chính phụ xe. Đơn còn chờ chất → phụ xe phải có
    chuyến đang/sắp chạy cùng tuyến (giống quy tắc báo thất lạc, UC-28). Đơn khác → không xem."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")

    if don.get("chuyen_id"):
        lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), nguoi_dung_id)
    elif don["trang_thai"] == "cho_van_chuyen":
        chuyen_cua_toi = chuyen_xe_service.danh_sach_chuyen_cua_toi(nguoi_dung_id)
        if not any(str(c["tuyen_id"]) == str(don["tuyen_id"]) for c in chuyen_cua_toi):
            raise CamTruyCap("Đơn hàng này không thuộc tuyến xe của bạn")
    else:
        raise CamTruyCap("Đơn hàng này không thuộc chuyến của bạn")

    return {
        **don,
        "lich_su_trang_thai": don_hang_repo.lay_lich_su_trang_thai(don_hang_id),
        "bao_cao_su_co": don_hang_repo.lay_bao_cao_su_co(don_hang_id),
    }


def chuyen_da_chay(nguoi_dung_id: str, tu_ngay, den_ngay) -> list[dict]:
    """`den_ngay` là mốc loại trừ — route cộng thêm 1 ngày như thong_ke_cua_toi."""
    if tu_ngay >= den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước ngày kết thúc")

    nhan_su = nhan_su_repo.tim_theo_nguoi_dung_id(nguoi_dung_id)
    if not nhan_su or nhan_su["chuc_danh"] != "phu_xe":
        raise KhongDuQuyen("Tài khoản không phải phụ xe")

    xe_id = nhan_su_repo.tim_xe_dang_gan(nhan_su["id"])
    if not xe_id:
        return []
    return chuyen_xe_repo.danh_sach_chuyen_da_chay(xe_id, tu_ngay, den_ngay)
