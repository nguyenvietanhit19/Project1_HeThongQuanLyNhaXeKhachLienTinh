"""Giá vé — UC-33, NGHIEP_VU.md mục 3.1 (giá gốc theo cặp điểm đi/đến,
không phụ thuộc loại xe — hệ số loai_xe.he_so_gia nhân vào lúc bán vé).
Đúng theo ARCHITECTURE.md mục 2: Service quyết định quy tắc nghiệp vụ,
Repository chỉ đọc/ghi SQL thuần.
"""

import psycopg2.errors

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import gia_ve_repository as repo
from app.utils.loi import GiaTriLoi


def _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id: str) -> list[dict]:
    """Danh sách khu vực (không trùng lặp) mà tuyến đi qua, theo đúng thứ
    tự tuyến di chuyển (dùng thu_tu điểm dừng nhỏ nhất của mỗi khu vực) —
    dùng để xác định cặp điểm đi/đến hợp lệ (điểm đi phải đứng trước
    điểm đến theo đúng chiều tuyến)."""
    diem = dia_diem_repo.danh_sach_diem_theo_tuyen(tuyen_id)
    da_thay: dict[str, dict] = {}
    for d in sorted(diem, key=lambda x: x["thu_tu"]):
        kv_id = str(d["khu_vuc_id"])
        if kv_id not in da_thay:
            da_thay[kv_id] = {"khu_vuc_id": kv_id, "ten": d["ten_khu_vuc"]}
    return list(da_thay.values())


def _kiem_tra_cap_diem(tuyen_id: str, diem_di_id: str, diem_den_id: str) -> None:
    if diem_di_id == diem_den_id:
        raise GiaTriLoi("Điểm đi và điểm đến không được trùng nhau")

    khu_vuc_tuyen = _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id)
    thu_tu_theo_id = {kv["khu_vuc_id"]: i for i, kv in enumerate(khu_vuc_tuyen)}

    if diem_di_id not in thu_tu_theo_id or diem_den_id not in thu_tu_theo_id:
        raise GiaTriLoi("Điểm đi/điểm đến phải là khu vực mà tuyến này đi qua")

    if thu_tu_theo_id[diem_di_id] >= thu_tu_theo_id[diem_den_id]:
        raise GiaTriLoi("Điểm đi phải đứng trước điểm đến theo đúng chiều di chuyển của tuyến")


def _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den) -> None:
    if ap_dung_tu and ap_dung_den and ap_dung_tu > ap_dung_den:
        raise GiaTriLoi("Ngày bắt đầu áp dụng phải trước ngày kết thúc")


def _khoang_ngay_giao_nhau(a1, b1, a2, b2) -> bool:
    """True nếu 2 khoảng ngày [a1, b1] và [a2, b2] giao nhau — None ở đầu
    khoảng coi như vô cực về trước, None ở cuối coi như vô cực về sau
    (đúng nghĩa "áp dụng vô thời hạn")."""
    return (a1 is None or b2 is None or a1 <= b2) and (a2 is None or b1 is None or a2 <= b1)


def _kiem_tra_khong_chong_leo(tuyen_id: str, diem_di_id: str, diem_den_id: str, ap_dung_tu, ap_dung_den, tru_id: str | None = None) -> None:
    """UNIQUE constraint của bảng gia_ve không tự chặn được 2 dòng cùng
    ap_dung_tu = NULL (SQL coi NULL khác NULL, không tính là trùng) — phải
    tự kiểm tra chồng lấn khoảng ngày áp dụng ở đây, tránh 2 giá vé "vô
    thời hạn" (hoặc 2 khoảng ngày đè lên nhau) cùng tồn tại cho 1 cặp điểm,
    không biết giá nào là giá thật."""
    hien_co = repo.danh_sach_gia_ve_theo_cap_diem(tuyen_id, diem_di_id, diem_den_id)
    for gv in hien_co:
        if tru_id and str(gv["id"]) == str(tru_id):
            continue
        if _khoang_ngay_giao_nhau(ap_dung_tu, ap_dung_den, gv["ap_dung_tu"], gv["ap_dung_den"]):
            raise GiaTriLoi(
                "Khoảng thời gian áp dụng bị chồng lấn với 1 giá vé khác đã cấu hình "
                "cho đúng cặp điểm đi/đến này — sửa lại khoảng ngày hoặc sửa giá vé cũ"
            )


def tao_gia_ve(tuyen_id: str, diem_di_id: str, diem_den_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> dict:
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den)
    _kiem_tra_cap_diem(tuyen_id, diem_di_id, diem_den_id)
    _kiem_tra_khong_chong_leo(tuyen_id, diem_di_id, diem_den_id, ap_dung_tu, ap_dung_den)

    try:
        return repo.tao_gia_ve(tuyen_id, diem_di_id, diem_den_id, gia_goc, ap_dung_tu, ap_dung_den)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi("Đã có giá vé cho đúng cặp điểm đi/đến này (cùng thời hạn áp dụng)")


def sua_gia_ve(gia_ve_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> None:
    gia_ve_hien_tai = repo.tim_gia_ve_theo_id(gia_ve_id)
    if not gia_ve_hien_tai:
        raise GiaTriLoi("Không tìm thấy giá vé")
    _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den)
    _kiem_tra_khong_chong_leo(
        str(gia_ve_hien_tai["tuyen_id"]),
        str(gia_ve_hien_tai["diem_di_id"]),
        str(gia_ve_hien_tai["diem_den_id"]),
        ap_dung_tu,
        ap_dung_den,
        tru_id=gia_ve_id,
    )
    try:
        repo.sua_gia_ve(gia_ve_id, gia_goc, ap_dung_tu, ap_dung_den)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi("Đã có giá vé khác trùng thời hạn áp dụng cho đúng cặp điểm đi/đến này")


def danh_sach_gia_ve(tuyen_id: str | None = None) -> list[dict]:
    return repo.danh_sach_gia_ve(tuyen_id)


def xoa_gia_ve(gia_ve_id: str) -> None:
    if not repo.tim_gia_ve_theo_id(gia_ve_id):
        raise GiaTriLoi("Không tìm thấy giá vé")
    repo.xoa_gia_ve(gia_ve_id)
