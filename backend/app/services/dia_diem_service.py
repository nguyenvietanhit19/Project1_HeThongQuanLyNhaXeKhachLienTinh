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
# 3. Nhóm tuyến (gắn danh sách khu vực có thứ tự)
# ---------------------------------------------------------


def tao_nhom_tuyen(ten: str, danh_sach_khu_vuc_id: list[str]) -> dict:
    khu_vuc_ids = [str(i) for i in danh_sach_khu_vuc_id]
    if len(set(khu_vuc_ids)) != len(khu_vuc_ids):
        raise GiaTriLoi("Danh sách khu vực có khu vực bị lặp lại")

    khu_vuc_thuc_te = {str(k["id"]) for k in repo.tim_nhieu_khu_vuc_theo_id(khu_vuc_ids)}
    thieu = [i for i in khu_vuc_ids if i not in khu_vuc_thuc_te]
    if thieu:
        raise GiaTriLoi(f"Không tìm thấy khu vực: {', '.join(thieu)}")

    danh_sach_de_luu = [{"khu_vuc_id": i, "thu_tu": thu_tu} for thu_tu, i in enumerate(khu_vuc_ids, start=1)]
    return repo.tao_nhom_tuyen_voi_khu_vuc(ten, danh_sach_de_luu)


def danh_sach_nhom_tuyen() -> list[dict]:
    return repo.danh_sach_nhom_tuyen()


def lay_chi_tiet_nhom_tuyen(nhom_tuyen_id: str) -> dict:
    nhom_tuyen = repo.tim_nhom_tuyen_theo_id(nhom_tuyen_id)
    if not nhom_tuyen:
        raise GiaTriLoi("Không tìm thấy nhóm tuyến")
    nhom_tuyen["danh_sach_khu_vuc"] = repo.danh_sach_khu_vuc_theo_nhom_tuyen(nhom_tuyen_id)
    return nhom_tuyen


def xoa_nhom_tuyen(nhom_tuyen_id: str) -> None:
    if not repo.tim_nhom_tuyen_theo_id(nhom_tuyen_id):
        raise GiaTriLoi("Không tìm thấy nhóm tuyến")
    try:
        repo.xoa_nhom_tuyen(nhom_tuyen_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: nhóm tuyến này đang có tuyến hoặc xe cố định thuộc về nó")


# ---------------------------------------------------------
# 4. Tuyến (UC-31)
# ---------------------------------------------------------


def _don_dieu(day: list[int]) -> bool:
    """True nếu dãy tăng dần hoặc giảm dần (cho phép bằng nhau liên tiếp —
    nhiều điểm cùng 1 khu vực). Dùng để chặn chọn điểm xen kẽ lộn xộn giữa
    các khu vực của nhóm tuyến (đi 1 chiều hoặc chiều ngược lại đều hợp lệ)."""
    tang = all(a <= b for a, b in zip(day, day[1:]))
    giam = all(a >= b for a, b in zip(day, day[1:]))
    return tang or giam


def tao_tuyen(ten: str, nhom_tuyen_id: str, danh_sach_diem: list[dict]) -> dict:
    if not repo.tim_nhom_tuyen_theo_id(nhom_tuyen_id):
        raise GiaTriLoi("Nhóm tuyến không tồn tại")

    khu_vuc_cua_nhom = repo.danh_sach_khu_vuc_theo_nhom_tuyen(nhom_tuyen_id)
    thu_tu_khu_vuc = {str(k["khu_vuc_id"]): k["thu_tu"] for k in khu_vuc_cua_nhom}

    diem_ids = [str(d["diem_don_tra_id"]) for d in danh_sach_diem]
    if len(set(diem_ids)) != len(diem_ids):
        raise GiaTriLoi("Danh sách điểm có điểm bị lặp lại")

    diem_thuc_te = {str(d["id"]): d for d in repo.tim_nhieu_diem_don_tra_theo_id(diem_ids)}
    thieu = [d_id for d_id in diem_ids if d_id not in diem_thuc_te]
    if thieu:
        raise GiaTriLoi(f"Không tìm thấy điểm đón/trả: {', '.join(thieu)}")

    # Mỗi điểm phải thuộc 1 khu vực có trong nhóm tuyến đã chọn
    ngoai_nhom = [d_id for d_id in diem_ids if str(diem_thuc_te[d_id]["khu_vuc_id"]) not in thu_tu_khu_vuc]
    if ngoai_nhom:
        raise GiaTriLoi(
            f"{len(ngoai_nhom)} điểm không thuộc khu vực nào trong nhóm tuyến đã chọn — "
            "chỉ được chọn điểm thuộc khu vực đã cấu hình ở nhóm tuyến"
        )

    # Thứ tự khu vực của các điểm đã chọn phải đơn điệu (tăng hoặc giảm) theo đúng
    # thứ tự khu vực của nhóm tuyến — không cho chọn xen kẽ lộn xộn
    day_thu_tu_khu_vuc = [thu_tu_khu_vuc[str(diem_thuc_te[d_id]["khu_vuc_id"])] for d_id in diem_ids]
    if not _don_dieu(day_thu_tu_khu_vuc):
        raise GiaTriLoi(
            "Thứ tự điểm dừng không khớp thứ tự khu vực của nhóm tuyến — "
            "không được chọn xen kẽ lộn xộn giữa các khu vực"
        )

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
