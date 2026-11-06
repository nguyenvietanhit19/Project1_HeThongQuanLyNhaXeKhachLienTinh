"""Biên chế CỐ ĐỊNH của xe — UC-35, NGHIEP_VU.md mục 3.2. Quản lý chỉ gán/gỡ
biên chế cố định (xe_nhan_su.loai = 'co_dinh'); biên chế tạm thời khi có người
nghỉ do điều độ viên xử lý (mục 8.6), không làm ở đây.
"""

import datetime
from zoneinfo import ZoneInfo

from app.config import NGUONG_CANH_BAO_GIAY_TO_NGAY
from app.repositories import giay_to_nhan_su_repository as giay_to_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import xe_repository as xe_repo
from app.services import luu_tru_anh_service
from app.utils.bien_che import SO_TAI_XE_YEU_CAU
from app.utils.loi import GiaTriLoi

SO_TAI_XE_TOI_DA = SO_TAI_XE_YEU_CAU  # mục 3.2: mỗi xe đúng 2 tài xế (thay phiên nhau)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _hom_nay() -> datetime.date:
    return datetime.datetime.now(MUI_GIO_VN).date()


def phan_loai_han(ngay_het_han: datetime.date | None, hom_nay: datetime.date) -> str | None:
    """"het_han" (qua hạn) · "sap_het_han" (còn <= ngưỡng cảnh báo UC-49) · "con_han"; None khi chưa có ngày."""
    if ngay_het_han is None:
        return None
    if ngay_het_han < hom_nay:
        return "het_han"
    if (ngay_het_han - hom_nay).days <= NGUONG_CANH_BAO_GIAY_TO_NGAY:
        return "sap_het_han"
    return "con_han"


def lay_bien_che(xe_id: str) -> list[dict]:
    if not xe_repo.tim_xe_theo_id(xe_id):
        raise GiaTriLoi("Không tìm thấy xe")
    return nhan_su_repo.danh_sach_bien_che_theo_xe(xe_id)


def danh_sach_nhan_su_dang_lam() -> list[dict]:
    """Ứng viên đưa vào biên chế: mọi nhân sự đang làm (kèm xe hiện tại và dấu hiệu giấy tờ có vấn đề) — giao diện lọc/tìm tại chỗ."""
    hom_nay = _hom_nay()
    ket_qua = []
    for n in nhan_su_repo.danh_sach_dang_lam():
        tinh_trang = phan_loai_han(n.pop("ngay_het_han_giay_to_som", None), hom_nay)
        n["giay_to_tinh_trang"] = tinh_trang if tinh_trang in ("het_han", "sap_het_han") else None
        ket_qua.append(n)
    return ket_qua


def _url_anh(public_id: str | None) -> str | None:
    """URL xem ảnh có chữ ký; lỗi cấu hình/dịch vụ ảnh (VD chưa có CLOUDINARY_URL ở máy dev) thì coi như chưa có ảnh, không làm hỏng việc xem hồ sơ."""
    if not public_id:
        return None
    try:
        return luu_tru_anh_service.lay_url_xem(public_id)
    except Exception:  # noqa: BLE001
        return None


def chi_tiet_nhan_su(nhan_su_id: str) -> dict:
    """TOÀN BỘ hồ sơ của 1 nhân sự (chỉ xem) cho quản lý cân nhắc khi đưa người vào biên chế: thông tin cá nhân (CCCD, ngày sinh), ảnh, giấy tờ
    (số, hạng, ngày cấp/hết hạn, ảnh), tài khoản (phụ xe) và biên chế hiện tại. Quản lý đọc được nhưng không sửa — sửa hồ sơ là việc của
    quan_ly_nhan_su (UC-49, NGHIEP_VU.md mục 8.9). Ảnh phát bằng URL có chữ ký, không lưu URL."""
    ho_so = nhan_su_repo.tim_ho_so_day_du(nhan_su_id)
    if not ho_so:
        raise GiaTriLoi("Không tìm thấy nhân sự")
    hom_nay = _hom_nay()
    tai_khoan = nhan_su_repo.email_tai_khoan(str(ho_so["nguoi_dung_id"])) if ho_so["nguoi_dung_id"] else None
    giay_to = [
        {
            "loai": g["loai"], "so_giay_to": g["so_giay_to"], "hang": g["hang"], "ngay_cap": g["ngay_cap"], "ngay_het_han": g["ngay_het_han"],
            "tinh_trang": phan_loai_han(g["ngay_het_han"], hom_nay), "anh_url": _url_anh(g.get("anh_giay_to")),
        }
        for g in giay_to_repo.danh_sach_theo_nhan_su(nhan_su_id)
    ]
    return {
        "id": ho_so["id"], "ma": ho_so["ma"], "ho_ten": ho_so["ho_ten"], "so_dien_thoai": ho_so["so_dien_thoai"],
        "chuc_danh": ho_so["chuc_danh"], "trang_thai": ho_so["trang_thai"], "so_cccd": ho_so["so_cccd"], "ngay_sinh": ho_so["ngay_sinh"],
        "anh_url": _url_anh(ho_so["anh_ho_so"]), "ngay_vao_lam": ho_so["ngay_vao_lam"],
        "ngay_nghi_viec": ho_so["ngay_nghi_viec"], "ly_do_nghi_viec": ho_so["ly_do_nghi_viec"],
        "co_tai_khoan": bool(ho_so["nguoi_dung_id"]),
        "email": tai_khoan["email"] if tai_khoan else None,
        "tai_khoan_hoat_dong": tai_khoan["dang_hoat_dong"] if tai_khoan else None,
        "giay_to": giay_to,
        "bien_che": [
            {"xe_id": b["xe_id"], "bien_so": b["bien_so"], "loai": b["loai"], "trang_thai": b["trang_thai"]}
            for b in nhan_su_repo.bien_che_cua_nhan_su(nhan_su_id)
        ],
    }


def them_bien_che_co_dinh(xe_id: str, nhan_su_id: str) -> list[dict]:
    if not xe_repo.tim_xe_theo_id(xe_id):
        raise GiaTriLoi("Không tìm thấy xe")

    nhan_su = nhan_su_repo.tim_theo_id(nhan_su_id)
    if not nhan_su:
        raise GiaTriLoi("Không tìm thấy nhân sự")
    if nhan_su["trang_thai"] != "dang_lam":
        raise GiaTriLoi("Nhân sự này đã nghỉ việc, không thể gán vào biên chế")

    # Phụ xe là người duy nhất thao tác trên hệ thống trong đội vận hành nên bắt buộc có tài khoản
    if nhan_su["chuc_danh"] == "phu_xe" and not nhan_su["nguoi_dung_id"]:
        raise GiaTriLoi("Phụ xe bắt buộc phải có tài khoản đăng nhập trước khi gán vào biên chế")

    # 1 nhân viên vận hành chỉ thuộc biên chế cố định của 1 xe duy nhất tại 1 thời điểm
    da_co = nhan_su_repo.tim_bien_che_co_dinh_cua_nhan_su(nhan_su_id)
    if da_co:
        if str(da_co["xe_id"]) == str(xe_id):
            raise GiaTriLoi("Nhân sự này đã thuộc biên chế cố định của xe này")
        raise GiaTriLoi(f'Nhân sự này đang thuộc biên chế cố định của xe {da_co["bien_so"]} — hãy gỡ khỏi xe đó trước')

    if nhan_su["chuc_danh"] == "tai_xe" and nhan_su_repo.dem_co_dinh_theo_chuc_danh(xe_id, "tai_xe") >= SO_TAI_XE_TOI_DA:
        raise GiaTriLoi(f"Xe đã đủ {SO_TAI_XE_TOI_DA} tài xế cố định")

    nhan_su_repo.them_bien_che_co_dinh(xe_id, nhan_su_id)
    return nhan_su_repo.danh_sach_bien_che_theo_xe(xe_id)


def go_bien_che_co_dinh(xe_nhan_su_id: str) -> list[dict]:
    dong = nhan_su_repo.tim_bien_che_theo_id(xe_nhan_su_id)
    if not dong:
        raise GiaTriLoi("Không tìm thấy dòng biên chế")
    if dong["loai"] != "co_dinh":
        raise GiaTriLoi("Chỉ gỡ được biên chế cố định ở đây — biên chế tạm thời do điều độ viên xử lý")

    nhan_su_repo.xoa_bien_che(xe_nhan_su_id)
    return nhan_su_repo.danh_sach_bien_che_theo_xe(str(dong["xe_id"]))
