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


def tao_diem_don_tra(khu_vuc_id: str, ten: str, dia_chi: str, loai: str) -> dict:
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Khu vực không tồn tại")
    return repo.tao_diem_don_tra(khu_vuc_id, ten, dia_chi, loai)


def sua_diem_don_tra(diem_id: str, khu_vuc_id: str, ten: str, dia_chi: str, loai: str) -> None:
    if not repo.tim_diem_don_tra_theo_id(diem_id):
        raise GiaTriLoi("Không tìm thấy điểm đón/trả")
    if not repo.tim_khu_vuc_theo_id(khu_vuc_id):
        raise GiaTriLoi("Khu vực không tồn tại")
    repo.sua_diem_don_tra(diem_id, khu_vuc_id, ten, dia_chi, loai)


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
# 3. Tuyến (UC-31)
# ---------------------------------------------------------


def danh_sach_nhom_tuyen() -> list[dict]:
    return repo.danh_sach_nhom_tuyen()


def tao_tuyen(
    ten: str,
    nhom_tuyen_id: str | None,
    ten_nhom_tuyen_moi: str | None,
    danh_sach_diem: list[dict],
) -> dict:
    # Bước 1: chọn nhóm tuyến có sẵn, hoặc tạo mới nếu là hành trình vật lý mới (NGHIEP_VU.md mục 3.1)
    if nhom_tuyen_id:
        if not repo.tim_nhom_tuyen_theo_id(nhom_tuyen_id):
            raise GiaTriLoi("Nhóm tuyến không tồn tại")
    elif ten_nhom_tuyen_moi:
        nhom_tuyen_id = repo.tao_nhom_tuyen(ten_nhom_tuyen_moi)["id"]
    else:
        raise GiaTriLoi("Phải chọn nhóm tuyến có sẵn hoặc đặt tên cho nhóm tuyến mới")

    # Bước 2+3: kiểm tra danh sách điểm trước khi tạo tuyến + các dòng tuyen_diem_don_tra
    diem_ids = [str(d["diem_don_tra_id"]) for d in danh_sach_diem]
    if len(set(diem_ids)) != len(diem_ids):
        raise GiaTriLoi("Danh sách điểm có điểm bị lặp lại")

    diem_thuc_te = {str(d["id"]): d for d in repo.tim_nhieu_diem_don_tra_theo_id(diem_ids)}
    thieu = [d_id for d_id in diem_ids if d_id not in diem_thuc_te]
    if thieu:
        raise GiaTriLoi(f"Không tìm thấy điểm đón/trả: {', '.join(thieu)}")

    # Luồng rẽ nhánh UC-31: điểm đầu/cuối (thu_tu nhỏ/lớn nhất) bắt buộc là van_phong
    diem_dau = diem_thuc_te[diem_ids[0]]
    diem_cuoi = diem_thuc_te[diem_ids[-1]]
    if diem_dau["loai"] != "van_phong" or diem_cuoi["loai"] != "van_phong":
        raise GiaTriLoi("Điểm đầu tiên và điểm cuối cùng của tuyến bắt buộc phải là văn phòng")

    danh_sach_de_luu = [
        {
            "diem_don_tra_id": d["diem_don_tra_id"],
            "thu_tu": thu_tu,
            "thoi_gian_du_kien_phut": d["thoi_gian_du_kien_phut"],
        }
        for thu_tu, d in enumerate(danh_sach_diem, start=1)
    ]

    return repo.tao_tuyen_voi_diem(nhom_tuyen_id, ten, danh_sach_de_luu)


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
