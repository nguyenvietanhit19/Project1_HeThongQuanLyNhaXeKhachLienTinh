"""Biên chế CỐ ĐỊNH của xe — UC-35, NGHIEP_VU.md mục 3.2. Quản lý chỉ gán/gỡ
biên chế cố định (xe_nhan_su.loai = 'co_dinh'); biên chế tạm thời khi có người
nghỉ do điều độ viên xử lý (mục 8.6), không làm ở đây.
"""

from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import xe_repository as xe_repo
from app.utils.loi import GiaTriLoi

SO_TAI_XE_TOI_DA = 2  # mục 3.2: mỗi xe đúng 2 tài xế (thay phiên nhau)


def lay_bien_che(xe_id: str) -> list[dict]:
    if not xe_repo.tim_xe_theo_id(xe_id):
        raise GiaTriLoi("Không tìm thấy xe")
    return nhan_su_repo.danh_sach_bien_che_theo_xe(xe_id)


def danh_sach_nhan_su_dang_lam() -> list[dict]:
    return nhan_su_repo.danh_sach_dang_lam()


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
