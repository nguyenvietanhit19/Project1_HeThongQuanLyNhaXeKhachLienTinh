"""Quản lý hồ sơ nhân sự vận hành (tài xế/phụ xe) — UC-49, NGHIEP_VU.md mục
8.9 điểm 5, mục 12.

Actor: quan_ly_nhan_su hoặc quan_ly (route tự giới hạn qua yeu_cau_vai_tro).
Khác bien_che_service.py (UC-35, biên chế — "người đó đi xe nào"): file này
chỉ lo hồ sơ — "ai là nhân sự của công ty, giấy tờ còn hạn không"
(NGHIEP_VU.md mục 8.9, "Ranh giới với quan_ly").

Nhật ký (UC-52): chỉ ghi khi actor là quan_ly_nhan_su — đúng thiết kế
nhat_ky_quan_ly_nhan_su "tách riêng khỏi nhat_ky_admin", không lẫn hành động
của quan_ly (DATABASE.md mục 6.3).

Dùng repositories/nhan_su_van_hanh_repository.py (file của người khác trong
nhóm, chủ bảng nhan_su_van_hanh) — chỉ gọi các hàm hồ sơ mới được THÊM vào
cuối file đó (tim_ho_so_day_du, danh_sach_ho_so, tao_ho_so, cap_nhat_ho_so,
cap_nhat_anh_ho_so) và 1 hàm đã có sẵn từ trước (tim_theo_nguoi_dung_id) —
không sửa hàm nào cũ của họ.
"""

from app.repositories import giay_to_nhan_su_repository as giay_to_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import nhat_ky_quan_ly_nhan_su_repository as nhat_ky_repo
from app.services import luu_tru_anh_service
from app.utils.loi import GiaTriLoi, KhongTimThay, LoiHeThong


# ---------------------------------------------------------
# Hàm phụ (tiền tố _ = chỉ dùng nội bộ trong file này)
# ---------------------------------------------------------
def _ghi_nhat_ky(actor_id: str, actor_vai_tro: str, hanh_dong: str, nhan_su_id: str, ghi_chu: str | None = None) -> None:
    # Chỉ ghi nhật ký khi người thao tác là quan_ly_nhan_su.
    # Nếu là quan_ly làm cùng việc thì bỏ qua (nhật ký này tách riêng, UC-52).
    if actor_vai_tro != "quan_ly_nhan_su":
        return
    nhat_ky_repo.ghi(actor_id, hanh_dong, "nhan_su_van_hanh", nhan_su_id, ghi_chu)


def _gan_url_anh(ho_so: dict) -> dict:
    """DB chỉ lưu public_id của Cloudinary (anh_ho_so). Hàm này đổi public_id
    thành URL có chữ ký để frontend hiển thị; chưa có ảnh thì anh_url = None."""
    ho_so["anh_url"] = luu_tru_anh_service.lay_url_xem(ho_so["anh_ho_so"]) if ho_so.get("anh_ho_so") else None
    return ho_so


def _gan_url_giay_to(giay_to: dict) -> dict:
    """Giống _gan_url_anh nhưng cho ảnh chụp giấy tờ (anh_giay_to)."""
    giay_to["anh_url"] = luu_tru_anh_service.lay_url_xem(giay_to["anh_giay_to"]) if giay_to.get("anh_giay_to") else None
    return giay_to


# ---------------------------------------------------------
# Xem hồ sơ
# ---------------------------------------------------------
def danh_sach_ho_so(chi_dang_lam: bool = False) -> list[dict]:
    """Danh sách tóm tắt. chi_dang_lam=True thì bỏ qua người đã nghỉ việc.
    Thêm cờ co_tai_khoan (phụ xe có tài khoản, tài xế thì không)."""
    return [
        {**h, "co_tai_khoan": h["nguoi_dung_id"] is not None}
        for h in nhan_su_repo.danh_sach_ho_so(chi_dang_lam)
    ]


def xem_chi_tiet(nhan_su_id: str) -> dict:
    """Hồ sơ đầy đủ = thông tin nhân sự + ảnh + danh sách giấy tờ. Không có
    hồ sơ thì báo 404 (KhongTimThay). Cũng được dùng làm kết quả trả về sau
    khi tạo/sửa để frontend có ngay dữ liệu mới nhất."""
    ho_so = nhan_su_repo.tim_ho_so_day_du(nhan_su_id)
    if not ho_so:
        raise KhongTimThay("Không tìm thấy hồ sơ nhân sự")
    ho_so = _gan_url_anh(ho_so)
    ho_so["giay_to"] = [_gan_url_giay_to(g) for g in giay_to_repo.danh_sach_theo_nhan_su(nhan_su_id)]
    return ho_so


def _kiem_tra_tai_khoan_phu_xe(nguoi_dung_id: str, nhan_su_id_dang_sua: str | None = None) -> None:
    """Kiểm tra tài khoản được chọn cho hồ sơ phụ xe có hợp lệ không:
    (1) tài khoản tồn tại, (2) đúng vai trò phu_xe,
    (3) chưa gắn với hồ sơ nhân sự khác (1 tài khoản <-> 1 hồ sơ).
    nhan_su_id_dang_sua: khi sửa hồ sơ, bỏ qua chính hồ sơ đó lúc kiểm tra (3)."""
    tai_khoan = nguoi_dung_repo.tim_theo_id(nguoi_dung_id)
    if not tai_khoan:
        raise GiaTriLoi("Không tìm thấy tài khoản được chọn")
    if tai_khoan["vai_tro"] != "phu_xe":
        raise GiaTriLoi("Tài khoản được chọn không phải vai trò phụ xe")

    da_gan = nhan_su_repo.tim_theo_nguoi_dung_id(str(nguoi_dung_id))
    if da_gan and str(da_gan["id"]) != str(nhan_su_id_dang_sua):
        raise GiaTriLoi("Tài khoản này đã gắn với 1 hồ sơ khác")


def _luu_giay_to(nhan_su_id: str, danh_sach_giay_to) -> None:
    """Lưu từng giấy tờ gửi lên. Mỗi nhân sự chỉ có 1 dòng cho mỗi loại giấy tờ:
    - đã có loại đó -> cập nhật (gia hạn; repo tự xóa cờ cảnh báo để job nhắc lại từ đầu)
    - chưa có -> tạo mới."""
    for gt in danh_sach_giay_to:
        da_co = giay_to_repo.tim_theo_nhan_su_va_loai(nhan_su_id, gt.loai)
        if da_co:
            giay_to_repo.cap_nhat(da_co["id"], gt.so_giay_to, gt.hang, gt.ngay_cap, gt.ngay_het_han)
        else:
            giay_to_repo.tao(nhan_su_id, gt.loai, gt.so_giay_to, gt.hang, gt.ngay_cap, gt.ngay_het_han)


# ---------------------------------------------------------
# Tạo / sửa hồ sơ
# ---------------------------------------------------------
def tao_ho_so(actor_id: str, actor_vai_tro: str, du_lieu) -> dict:
    """Tạo hồ sơ mới. Các bước: kiểm tra quy tắc nghiệp vụ -> tạo hồ sơ ->
    lưu giấy tờ -> ghi nhật ký -> trả hồ sơ đầy đủ."""
    # Phụ xe: bắt buộc gắn với 1 tài khoản phu_xe hợp lệ
    # (việc "phụ xe phải có nguoi_dung_id, tài xế không được có" đã chặn sớm ở schema).
    if du_lieu.chuc_danh == "phu_xe":
        _kiem_tra_tai_khoan_phu_xe(str(du_lieu.nguoi_dung_id))

    # Tài xế: bắt buộc có thông tin bằng lái ngay lúc tạo hồ sơ.
    if du_lieu.chuc_danh == "tai_xe" and not any(gt.loai == "bang_lai" for gt in du_lieu.giay_to):
        raise GiaTriLoi("Tài xế bắt buộc có thông tin bằng lái")

    nhan_su_id = nhan_su_repo.tao_ho_so(
        du_lieu.ho_ten,
        du_lieu.so_dien_thoai,
        du_lieu.chuc_danh,
        str(du_lieu.nguoi_dung_id) if du_lieu.nguoi_dung_id else None,
        du_lieu.so_cccd,
        du_lieu.ngay_sinh,
        du_lieu.ngay_vao_lam,
    )
    _luu_giay_to(nhan_su_id, du_lieu.giay_to)
    _ghi_nhat_ky(actor_id, actor_vai_tro, "tao_ho_so_nhan_su", nhan_su_id)
    return xem_chi_tiet(nhan_su_id)


def sua_ho_so(actor_id: str, actor_vai_tro: str, nhan_su_id: str, du_lieu) -> dict:
    """Sửa hồ sơ. Trường nào client không gửi (None) thì giữ nguyên giá trị cũ
    (kiểu "cập nhật từng phần"). Không đổi được chuc_danh / tài khoản."""
    ho_so = nhan_su_repo.tim_ho_so_day_du(nhan_su_id)
    if not ho_so:
        raise KhongTimThay("Không tìm thấy hồ sơ nhân sự")

    nhan_su_repo.cap_nhat_ho_so(
        nhan_su_id,
        du_lieu.ho_ten if du_lieu.ho_ten is not None else ho_so["ho_ten"],
        du_lieu.so_dien_thoai if du_lieu.so_dien_thoai is not None else ho_so["so_dien_thoai"],
        du_lieu.so_cccd if du_lieu.so_cccd is not None else ho_so["so_cccd"],
        du_lieu.ngay_sinh if du_lieu.ngay_sinh is not None else ho_so["ngay_sinh"],
        du_lieu.ngay_vao_lam if du_lieu.ngay_vao_lam is not None else ho_so["ngay_vao_lam"],
    )
    _luu_giay_to(nhan_su_id, du_lieu.giay_to)
    _ghi_nhat_ky(actor_id, actor_vai_tro, "sua_ho_so_nhan_su", nhan_su_id)
    return xem_chi_tiet(nhan_su_id)


# ---------------------------------------------------------
# Upload ảnh (Cloudinary)
# ---------------------------------------------------------
def cap_nhat_anh_ho_so(actor_id: str, actor_vai_tro: str, nhan_su_id: str, du_lieu_anh: bytes) -> str:
    """Upload ảnh chân dung lên Cloudinary, lưu public_id vào hồ sơ, trả về
    URL có chữ ký để frontend hiển thị ngay. Upload lỗi -> báo LoiHeThong."""
    if not nhan_su_repo.tim_ho_so_day_du(nhan_su_id):
        raise KhongTimThay("Không tìm thấy hồ sơ nhân sự")

    public_id = luu_tru_anh_service.tai_anh_len(du_lieu_anh, luu_tru_anh_service.THU_MUC_ANH_HO_SO)
    if not public_id:
        raise LoiHeThong("Không thể tải ảnh lên, thử lại sau")

    nhan_su_repo.cap_nhat_anh_ho_so(nhan_su_id, public_id)
    _ghi_nhat_ky(actor_id, actor_vai_tro, "sua_ho_so_nhan_su", nhan_su_id, ghi_chu="Cập nhật ảnh hồ sơ")
    return luu_tru_anh_service.lay_url_xem(public_id)


def cap_nhat_anh_giay_to(actor_id: str, actor_vai_tro: str, nhan_su_id: str, loai: str, du_lieu_anh: bytes) -> str:
    """Upload ảnh chụp giấy tờ (bang_lai / giay_kham_suc_khoe). Phải nhập
    thông tin giấy tờ trước (tạo/sửa hồ sơ), sau đó mới gắn ảnh vào được."""
    giay_to = giay_to_repo.tim_theo_nhan_su_va_loai(nhan_su_id, loai)
    if not giay_to:
        raise KhongTimThay("Chưa có giấy tờ loại này cho nhân sự, nhập thông tin giấy tờ trước")

    public_id = luu_tru_anh_service.tai_anh_len(du_lieu_anh, luu_tru_anh_service.THU_MUC_ANH_GIAY_TO)
    if not public_id:
        raise LoiHeThong("Không thể tải ảnh lên, thử lại sau")

    giay_to_repo.cap_nhat_anh(giay_to["id"], public_id)
    _ghi_nhat_ky(actor_id, actor_vai_tro, "sua_ho_so_nhan_su", nhan_su_id, ghi_chu=f"Cập nhật ảnh giấy tờ {loai}")
    return luu_tru_anh_service.lay_url_xem(public_id)


# ---------------------------------------------------------
# Dữ liệu phụ cho form
# ---------------------------------------------------------
def danh_sach_tai_khoan_phu_xe_chua_gan() -> list[dict]:
    """Các tài khoản phu_xe chưa có hồ sơ — đổ vào ô chọn tài khoản khi tạo hồ sơ phụ xe."""
    return nhan_su_repo.danh_sach_tai_khoan_phu_xe_chua_gan()
