"""Xem nhật ký thao tác — UC-52 (NGHIEP_VU.md UC-52, mục 8.9 điểm 7).

Actor: quan_ly_nhan_su (chỉ thấy dòng của CHÍNH MÌNH) hoặc quan_ly (thấy toàn bộ, lọc thêm theo người).
Quyền thật sự do service này quyết định — route chỉ lọc vai trò thô. quan_ly_nhan_su luôn bị ép về phạm vi
của mình dù client gửi `nguoi_id` là ai (NHAP_QUAN_LY_NHAN_SU.md mục 11.1, quyết định 14).

Chỉ ĐỌC: không có hàm ghi / sửa / xóa nhật ký ở đây.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.repositories import nhat_ky_doc_repository as repo
from app.utils.loi import CamTruyCap, GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
SO_DONG_MAC_DINH = 50
SO_DONG_TOI_DA = 200

NHAN_HANH_DONG = {
    "tao_tai_khoan": "Tạo tài khoản",
    "khoa_tai_khoan": "Khóa tài khoản",
    "mo_khoa_tai_khoan": "Mở khóa tài khoản",
    "tao_ho_so_nhan_su": "Tạo hồ sơ nhân sự",
    "sua_ho_so_nhan_su": "Sửa hồ sơ nhân sự",
    "cho_nghi_viec": "Cho nghỉ việc",
    "doi_van_phong": "Đổi văn phòng",
}
NHAN_DOI_TUONG = {
    "nguoi_dung": "Tài khoản",
    "nhan_su_van_hanh": "Hồ sơ nhân sự",
}


def _gioi_han(actor_id: str, actor_vai_tro: str) -> str | None:
    """None = xem cả hai bảng (quan_ly); id = chỉ dòng của người đó (quan_ly_nhan_su)."""
    if actor_vai_tro == "quan_ly_nhan_su":
        return str(actor_id)
    if actor_vai_tro == "quan_ly":
        return None
    raise CamTruyCap("Không đủ quyền xem nhật ký thao tác")


def _doi_tuong_hien_thi(dong: dict) -> str:
    """'Họ tên (mã)' nếu tra được tên; loại đối tượng lạ (nhóm khác ghi vào nhat_ky_admin) thì hiện loại + 8 ký tự
    đầu của id, không đoán bảng để tra tên."""
    if dong.get("ten_doi_tuong"):
        ma = f" ({dong['ma_doi_tuong']})" if dong.get("ma_doi_tuong") else ""
        return f"{dong['ten_doi_tuong']}{ma}"
    loai = NHAN_DOI_TUONG.get(dong["doi_tuong_loai"], dong["doi_tuong_loai"])
    return f"{loai} {str(dong['doi_tuong_id'])[:8]}"


def _gan_nhan(dong: dict) -> dict:
    return {
        **dong,
        "nhan_hanh_dong": NHAN_HANH_DONG.get(dong["hanh_dong"], dong["hanh_dong"]),
        "doi_tuong_hien_thi": _doi_tuong_hien_thi(dong),
    }


def _khoang_thoi_gian(tu_ngay: date | None, den_ngay: date | None) -> tuple[datetime | None, datetime | None]:
    """Ngày lọc là ngày GIỜ VN: từ 00:00 của tu_ngay đến hết den_ngay (= 00:00 của ngày kế tiếp, khoảng nửa mở)."""
    if tu_ngay and den_ngay and tu_ngay > den_ngay:
        raise GiaTriLoi("Từ ngày không được sau đến ngày")
    tu = datetime.combine(tu_ngay, time.min, tzinfo=MUI_GIO_VN) if tu_ngay else None
    den = datetime.combine(den_ngay + timedelta(days=1), time.min, tzinfo=MUI_GIO_VN) if den_ngay else None
    return tu, den


def xem_nhat_ky(
    actor_id: str,
    actor_vai_tro: str,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    hanh_dong: str | None = None,
    doi_tuong_loai: str | None = None,
    nguoi_id: str | None = None,
    trang: int = 1,
    so_dong: int = SO_DONG_MAC_DINH,
) -> dict:
    gioi_han = _gioi_han(actor_id, actor_vai_tro)
    if trang < 1:
        raise GiaTriLoi("Số trang phải từ 1")
    if not 1 <= so_dong <= SO_DONG_TOI_DA:
        raise GiaTriLoi(f"Số dòng mỗi trang từ 1 đến {SO_DONG_TOI_DA}")
    tu, den = _khoang_thoi_gian(tu_ngay, den_ngay)

    # quan_ly_nhan_su: bỏ qua nguoi_id client gửi (đã bị ép về chính mình ở `gioi_han`).
    nguoi_loc = None if gioi_han else (str(nguoi_id) if nguoi_id else None)
    dong, tong = repo.tim(
        gioi_han,
        tu=tu,
        den=den,
        hanh_dong=(hanh_dong or "").strip() or None,
        doi_tuong_loai=(doi_tuong_loai or "").strip() or None,
        nguoi_id=nguoi_loc,
        trang=trang,
        so_dong=so_dong,
    )
    return {
        "items": [_gan_nhan(d) for d in dong],
        "tong": tong,
        "trang": trang,
        "so_dong": so_dong,
        "so_trang": (tong + so_dong - 1) // so_dong,
    }


def tuy_chon_loc(actor_id: str, actor_vai_tro: str) -> dict:
    """Dữ liệu đổ các ô lọc. Người thực hiện chỉ dành cho quan_ly."""
    gioi_han = _gioi_han(actor_id, actor_vai_tro)
    gia_tri = repo.cac_gia_tri_loc(gioi_han)
    return {
        "hanh_dong": [{"gia_tri": g, "nhan": NHAN_HANH_DONG.get(g, g)} for g in gia_tri["hanh_dong"]],
        "doi_tuong_loai": [{"gia_tri": g, "nhan": NHAN_DOI_TUONG.get(g, g)} for g in gia_tri["doi_tuong_loai"]],
        "nguoi_thuc_hien": [] if gioi_han else repo.danh_sach_nguoi_thuc_hien(),
    }
