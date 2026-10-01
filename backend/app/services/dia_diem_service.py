"""Khu vực/Điểm đón trả/Tuyến — UC-29/30/31, NGHIEP_VU.md mục 3.1.

Đúng theo ARCHITECTURE.md mục 2: Service quyết định quy tắc nghiệp vụ,
Repository chỉ đọc/ghi SQL thuần.
"""

import psycopg2.errors

from app.repositories import dia_diem_repository as repo
from app.utils.loi import GiaTriLoi

# ---------------------------------------------------------
# 1. Khu vực (UC-29)
# ---------------------------------------------------------


def tao_khu_vuc(ten: str, tinh_thanh: str) -> dict:
    return repo.tao_khu_vuc(ten, tinh_thanh)


def sua_khu_vuc(khu_vuc_id: str, ten: str, tinh_thanh: str) -> None:
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Không tìm thấy khu vực")
    repo.sua_khu_vuc(khu_vuc_id, ten, tinh_thanh)


def danh_sach_khu_vuc() -> list[dict]:
    return repo.danh_sach_khu_vuc()


def xoa_khu_vuc(khu_vuc_id: str) -> None:
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Không tìm thấy khu vực")
    try:
        repo.xoa_khu_vuc(khu_vuc_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: khu vực này đang có điểm đón/trả thuộc về nó")


# ---------------------------------------------------------
# 2. Điểm đón/trả (UC-30)
# ---------------------------------------------------------


def tao_diem_don_tra(khu_vuc_id: str, ten: str, dia_chi: str, loai: str, sdt_lien_he: str | None = None) -> dict:
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Khu vực không tồn tại")
    return repo.tao_diem_don_tra(khu_vuc_id, ten, dia_chi, loai, sdt_lien_he)


def sua_diem_don_tra(diem_id: str, khu_vuc_id: str, ten: str, dia_chi: str, loai: str, sdt_lien_he: str | None = None) -> None:
    if not repo.tim_diem_don_tra_theo_id(diem_id):
        raise GiaTriLoi("Không tìm thấy điểm đón/trả")
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Khu vực không tồn tại")
    repo.sua_diem_don_tra(diem_id, khu_vuc_id, ten, dia_chi, loai, sdt_lien_he)


def danh_sach_diem_don_tra(khu_vuc_id: str | None = None) -> list[dict]:
    return repo.danh_sach_diem_don_tra(khu_vuc_id)


def xoa_diem_don_tra(diem_id: str) -> None:
    if not repo.tim_diem_don_tra_theo_id(diem_id):
        raise GiaTriLoi("Không tìm thấy điểm đón/trả")
    try:
        repo.xoa_diem_don_tra(diem_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: điểm này đang được dùng trong tuyến, xe, đơn hàng hoặc vé")


# ---------------------------------------------------------
# 3. Tuyến (UC-31) — không còn khái niệm "nhóm tuyến": 1 tuyến tự thân
# đại diện cả 1 hành trình vật lý, chạy được cả 2 chiều. Danh sách điểm
# dừng nhập theo đúng "chiều xuôi"; chiều ngược suy ra bằng cách đọc lại
# chính danh sách này theo thu_tu giảm dần (NGHIEP_VU.md mục 3.1) — không
# còn cơ chế kiểm tra chéo với 1 "nhóm" nào khác nữa, mỗi tuyến độc lập.
# ---------------------------------------------------------


def _validate_tuyen(danh_sach_diem: list[dict]) -> list[dict]:
    diem_ids = [str(d["diem_don_tra_id"]) for d in danh_sach_diem]
    if len(set(diem_ids)) != len(diem_ids):
        raise GiaTriLoi("Danh sách điểm có điểm bị lặp lại")

    diem_thuc_te = {str(d["id"]): d for d in repo.tim_nhieu_diem_don_tra_theo_id(diem_ids)}
    thieu = [d_id for d_id in diem_ids if d_id not in diem_thuc_te]
    if thieu:
        raise GiaTriLoi(f"Không tìm thấy điểm đón/trả: {', '.join(thieu)}")

    # Luồng rẽ nhánh UC-31: điểm đầu/cuối (thu_tu nhỏ/lớn nhất, theo chiều
    # xuôi) bắt buộc là van_phong
    diem_dau = diem_thuc_te[diem_ids[0]]
    diem_cuoi = diem_thuc_te[diem_ids[-1]]
    if diem_dau["loai"] != "van_phong" or diem_cuoi["loai"] != "van_phong":
        raise GiaTriLoi("Điểm đầu tiên và điểm cuối cùng của tuyến bắt buộc phải là văn phòng")

    # Không được đi xen kẽ khu vực: các điểm của cùng 1 khu vực phải nằm liền
    # nhau (VD A,A,B,B ok — A,B,A không được). Vì tuyến chạy cả 2 chiều nên
    # xe không được "quay lại" 1 khu vực đã rời đi.
    khu_vuc_theo_thu_tu = [str(diem_thuc_te[d_id]["khu_vuc_id"]) for d_id in diem_ids]
    da_roi_di = set()
    for i, kv_id in enumerate(khu_vuc_theo_thu_tu):
        if i > 0 and kv_id != khu_vuc_theo_thu_tu[i - 1]:
            da_roi_di.add(khu_vuc_theo_thu_tu[i - 1])
        if kv_id in da_roi_di:
            ten_kv = repo.tim_khu_vuc_theo_id(kv_id)["ten"]
            raise GiaTriLoi(f'Các điểm thuộc khu vực "{ten_kv}" phải nằm liền nhau trong tuyến, không được xen kẽ với khu vực khác')

    # Mỗi tỉnh/thành chỉ được đi qua đúng 1 khu vực trong 1 tuyến
    khu_vuc_theo_tinh: dict[str, str] = {}
    for kv_id in dict.fromkeys(khu_vuc_theo_thu_tu):
        tinh = repo.tim_khu_vuc_theo_id(kv_id)["tinh_thanh"]
        if tinh in khu_vuc_theo_tinh:
            raise GiaTriLoi(f'Tỉnh/thành "{tinh}" đang có 2 khu vực khác nhau trong tuyến — mỗi tỉnh chỉ được đi qua 1 khu vực')
        khu_vuc_theo_tinh[tinh] = kv_id

    return [
        {
            "diem_don_tra_id": d["diem_don_tra_id"],
            "thu_tu": thu_tu,
            "thoi_gian_du_kien_phut": d["thoi_gian_du_kien_phut"],
        }
        for thu_tu, d in enumerate(danh_sach_diem, start=1)
    ]


def tao_tuyen(ten: str, danh_sach_diem: list[dict]) -> dict:
    danh_sach_de_luu = _validate_tuyen(danh_sach_diem)
    return repo.tao_tuyen_voi_diem(ten, danh_sach_de_luu)


def sua_tuyen(tuyen_id: str, ten: str, danh_sach_diem: list[dict]) -> None:
    if not repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Không tìm thấy tuyến")
    danh_sach_de_luu = _validate_tuyen(danh_sach_diem)
    repo.sua_tuyen_voi_diem(tuyen_id, ten, danh_sach_de_luu)


def danh_sach_tuyen() -> list[dict]:
    return repo.danh_sach_tuyen()


def xoa_tuyen(tuyen_id: str) -> None:
    if not repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Không tìm thấy tuyến")
    try:
        repo.xoa_tuyen(tuyen_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: tuyến này đang được dùng trong chuyến xe hoặc đơn hàng gửi")


def lay_chi_tiet_tuyen(tuyen_id: str) -> dict:
    tuyen = repo.tim_tuyen_theo_id(tuyen_id)
    if not tuyen:
        raise GiaTriLoi("Không tìm thấy tuyến")
    tuyen["danh_sach_diem"] = repo.danh_sach_diem_theo_tuyen(tuyen_id)
    return tuyen
