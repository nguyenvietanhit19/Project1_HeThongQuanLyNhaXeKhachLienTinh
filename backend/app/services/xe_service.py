"""Loại xe (UC-32) và Xe (UC-34) — NGHIEP_VU.md mục 3.1. Đúng theo
ARCHITECTURE.md mục 2: Service quyết định quy tắc nghiệp vụ, Repository chỉ
đọc/ghi SQL thuần.
"""

import psycopg2.errors

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.repositories import xe_repository as repo
from app.services.websocket_manager import broadcast_sync
from app.utils.loi import GiaTriLoi


def _kiem_tra_so_do_ghe(so_do_ghe: list[dict]) -> None:
    ma_ghe_list = [ghe["ma_ghe"] for ghe in so_do_ghe]
    if len(set(ma_ghe_list)) != len(ma_ghe_list):
        raise GiaTriLoi("Sơ đồ ghế có mã ghế bị trùng lặp")


def tao_loai_xe(ten: str, he_so_gia, so_do_ghe: list[dict]) -> dict:
    _kiem_tra_so_do_ghe(so_do_ghe)
    try:
        return repo.tao_loai_xe(ten, he_so_gia, so_do_ghe)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại loại xe tên "{ten}"')


def sua_loai_xe(loai_xe_id: str, ten: str, he_so_gia, so_do_ghe: list[dict]) -> None:
    if not repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Không tìm thấy loại xe")
    _kiem_tra_so_do_ghe(so_do_ghe)
    try:
        repo.sua_loai_xe(loai_xe_id, ten, he_so_gia, so_do_ghe)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại loại xe tên "{ten}"')


def danh_sach_loai_xe() -> list[dict]:
    return repo.danh_sach_loai_xe()


def xoa_loai_xe(loai_xe_id: str) -> None:
    if not repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Không tìm thấy loại xe")
    try:
        repo.xoa_loai_xe(loai_xe_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: loại xe này đang được gán cho ít nhất 1 xe")


# ---------------------------------------------------------
# Xe (UC-34)
# ---------------------------------------------------------


def _chuan_hoa_bien_so(bien_so: str) -> str:
    return bien_so.strip().upper()


def _kiem_tra_tham_chieu_xe(loai_xe_id: str, diem_goc_id: str, tuyen_id: str | None) -> None:
    if not repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Loại xe không tồn tại")

    diem_goc = dia_diem_repo.tim_diem_don_tra_theo_id(diem_goc_id)
    if not diem_goc:
        raise GiaTriLoi("Điểm gốc không tồn tại")
    if diem_goc["loai"] != "van_phong":
        raise GiaTriLoi("Điểm gốc của xe bắt buộc phải là văn phòng")

    if tuyen_id and not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến cố định không tồn tại")


def tao_xe(bien_so: str, loai_xe_id: str, diem_goc_id: str, tuyen_id: str | None, trang_thai: str) -> dict:
    bien_so = _chuan_hoa_bien_so(bien_so)
    _kiem_tra_tham_chieu_xe(loai_xe_id, diem_goc_id, tuyen_id)
    try:
        xe_id = repo.tao_xe(bien_so, loai_xe_id, diem_goc_id, tuyen_id, trang_thai)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại xe có biển số "{bien_so}"')
    return repo.tim_xe_theo_id(str(xe_id))


def sua_xe(xe_id: str, bien_so: str, loai_xe_id: str, diem_goc_id: str, tuyen_id: str | None, trang_thai: str) -> dict:
    xe_cu = repo.tim_xe_theo_id(xe_id)
    if not xe_cu:
        raise GiaTriLoi("Không tìm thấy xe")

    bien_so = _chuan_hoa_bien_so(bien_so)
    _kiem_tra_tham_chieu_xe(loai_xe_id, diem_goc_id, tuyen_id)

    # Đổi loại xe khi xe đang gắn với chuyến chưa xong sẽ làm sai lệch loại xe đã cam kết
    # với khách (chuyen_xe.loai_xe_id phải bằng xe.loai_xe_id khi gán xe, mục 3.5).
    if str(xe_cu["loai_xe_id"]) != str(loai_xe_id) and repo.dem_chuyen_chua_xong_cua_xe(xe_id) > 0:
        raise GiaTriLoi("Không thể đổi loại xe: xe đang được gán cho chuyến chưa hoàn thành")

    try:
        repo.sua_xe(xe_id, bien_so, loai_xe_id, diem_goc_id, tuyen_id, trang_thai)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f'Đã tồn tại xe có biển số "{bien_so}"')

    # Xe sửa xong (bao_tri -> hoat_dong) mà đang có chuyến được xe khác chạy thay:
    # nhắc điều độ viên xem lại để gán lại xe gốc nếu phù hợp (UC-34, UC-40).
    if xe_cu["trang_thai"] == "bao_tri" and trang_thai == "hoat_dong":
        so_chuyen = repo.dem_chuyen_dang_chay_thay(xe_id)
        if so_chuyen:
            noi_dung = f"Xe {bien_so} đã sửa xong, đang có {so_chuyen} chuyến do xe khác chạy thay — hãy xem lại để gán lại xe gốc nếu phù hợp."
            for dieu_do_vien_id in nguoi_dung_repo.danh_sach_id_theo_vai_tro("dieu_do_vien"):
                thong_bao_repo.tao(dieu_do_vien_id, noi_dung)
                broadcast_sync(dieu_do_vien_id, noi_dung)

    return repo.tim_xe_theo_id(xe_id)


def danh_sach_xe() -> list[dict]:
    return repo.danh_sach_xe()


def xoa_xe(xe_id: str) -> None:
    if not repo.tim_xe_theo_id(xe_id):
        raise GiaTriLoi("Không tìm thấy xe")
    try:
        repo.xoa_xe(xe_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: xe đã có chuyến hoặc biên chế — hãy chuyển sang trạng thái ngừng sử dụng")
