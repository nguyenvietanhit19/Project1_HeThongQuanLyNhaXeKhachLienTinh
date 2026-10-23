"""Tạo tài khoản cán bộ — UC-36, NGHIEP_VU.md mục 2, mục 8.7 điểm 2, mục 8.9.

Actor: quan_ly_nhan_su hoặc quan_ly (route tự giới hạn qua yeu_cau_vai_tro) —
dùng chung một service, quyền cụ thể từng vai trò quyết định ở bảng tra cứu
bên dưới (không rải `if` khắp nơi).

Mật khẩu ban đầu: email cán bộ do công ty cấp nên KHÔNG dùng OTP/thư mời.
Mọi tài khoản mới có cùng một mật khẩu mặc định (MAT_KHAU_MAC_DINH), chỉ lưu
bản băm bcrypt; người tạo báo cho cán bộ, cán bộ đổi ngay sau khi đăng nhập
(OTP chỉ dùng khi quên mật khẩu). Mật khẩu cố ý đơn giản vì chỉ dùng tạm đến
lần đổi đầu tiên.

Nhật ký (UC-52): chỉ ghi khi actor là quan_ly_nhan_su, giống
ho_so_nhan_su_service.py (nhat_ky_quan_ly_nhan_su tách riêng khỏi nhat_ky_admin).
"""

from passlib.context import CryptContext

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import nhat_ky_quan_ly_nhan_su_repository as nhat_ky_repo
from app.repositories import tai_khoan_can_bo_repository as repo
from app.schemas.tai_khoan_can_bo_schema import VAI_TRO_CAN_VAN_PHONG
from app.utils.loi import CamTruyCap, GiaTriLoi
from app.utils.so_dien_thoai import chuan_hoa_so_dien_thoai

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mật khẩu ban đầu cố định cho mọi tài khoản cán bộ mới. Cán bộ phải đổi ngay sau
# lần đăng nhập đầu (PUT /auth/doi-mat-khau). Muốn đổi quy tắc chỉ sửa hằng số này.
MAT_KHAU_MAC_DINH = "12345678"

# ---------------------------------------------------------
# Bảng phân quyền — đổi quy tắc ai tạo được gì chỉ sửa ở đây
# ---------------------------------------------------------
_VAI_TRO_VAN_HANH = ("phu_xe", "nhan_vien_quay_ve", "nhan_vien_gui_hang", "dieu_do_vien")

# Vai trò người gọi -> các vai trò được tạo (chưa tính luật riêng "chỉ tài khoản gốc")
_QUYEN_TAO = {
    "quan_ly_nhan_su": _VAI_TRO_VAN_HANH,
    "quan_ly": _VAI_TRO_VAN_HANH + ("ke_toan", "quan_ly", "quan_ly_nhan_su"),
}

# Luật riêng: các vai trò này chỉ quan_ly GỐC (la_tai_khoan_goc = true) mới tạo được
_CHI_TAI_KHOAN_GOC_MOI_TAO = ("quan_ly", "quan_ly_nhan_su")

# Vai trò hiện trong danh sách tài khoản cán bộ của từng người gọi.
# quan_ly_nhan_su không quản lý ke_toan / quan_ly / quan_ly_nhan_su (mục 8.9) nên không thấy.
_QUYEN_XEM = {
    "quan_ly_nhan_su": _VAI_TRO_VAN_HANH,
    "quan_ly": _VAI_TRO_VAN_HANH + ("ke_toan", "quan_ly", "quan_ly_nhan_su"),
}


def _ghi_nhat_ky(actor_id: str, actor_vai_tro: str, tai_khoan_moi_id: str, ghi_chu: str) -> None:
    # Chỉ ghi khi người thao tác là quan_ly_nhan_su; quan_ly làm cùng việc thì bỏ qua.
    if actor_vai_tro != "quan_ly_nhan_su":
        return
    nhat_ky_repo.ghi(actor_id, "tao_tai_khoan", "nguoi_dung", tai_khoan_moi_id, ghi_chu)


def _kiem_tra_quyen_tao(actor_id: str, actor_vai_tro: str, vai_tro_moi: str) -> None:
    duoc_tao = _QUYEN_TAO.get(actor_vai_tro, ())
    if vai_tro_moi not in duoc_tao:
        raise CamTruyCap("Không đủ quyền tạo tài khoản vai trò này")
    if vai_tro_moi in _CHI_TAI_KHOAN_GOC_MOI_TAO and not repo.la_tai_khoan_goc(actor_id):
        raise CamTruyCap("Chỉ tài khoản quản lý gốc mới tạo được tài khoản quản lý hoặc quản lý nhân sự")


def _kiem_tra_van_phong(vai_tro_moi: str, van_phong_id: str | None) -> None:
    if vai_tro_moi not in VAI_TRO_CAN_VAN_PHONG:
        if van_phong_id:
            raise GiaTriLoi("Vai trò này không gắn văn phòng")
        return
    if not van_phong_id:
        raise GiaTriLoi("Vai trò này bắt buộc chọn văn phòng phụ trách")
    van_phong = dia_diem_repo.tim_diem_don_tra_theo_id(van_phong_id)
    if not van_phong or van_phong.get("loai") != "van_phong":
        raise GiaTriLoi("Điểm phụ trách phải là văn phòng hợp lệ")


# ---------------------------------------------------------
# UC-36: tạo tài khoản cán bộ
# ---------------------------------------------------------
def tao_tai_khoan(actor_id: str, actor_vai_tro: str, du_lieu) -> dict:
    """Thứ tự: kiểm tra hết (quyền, SĐT, email, văn phòng) rồi mới ghi; tạo
    tài khoản + gán văn phòng cùng một transaction. Trả kèm mật khẩu ban đầu
    để giao diện nhắc người tạo báo cho cán bộ."""
    vai_tro_moi = du_lieu.vai_tro
    van_phong_id = str(du_lieu.van_phong_id) if du_lieu.van_phong_id else None

    _kiem_tra_quyen_tao(actor_id, actor_vai_tro, vai_tro_moi)
    so_dien_thoai = chuan_hoa_so_dien_thoai(du_lieu.so_dien_thoai)
    email = str(du_lieu.email).strip().lower()
    if nguoi_dung_repo.tim_theo_email(email):
        raise GiaTriLoi("Email đã tồn tại")
    _kiem_tra_van_phong(vai_tro_moi, van_phong_id)

    mat_khau = MAT_KHAU_MAC_DINH
    tai_khoan = repo.tao_tai_khoan(
        email, _pwd_context.hash(mat_khau), du_lieu.ho_ten.strip(), so_dien_thoai, vai_tro_moi, van_phong_id
    )

    # Nhật ký chỉ ghi vai trò + văn phòng, KHÔNG ghi mật khẩu
    ghi_chu = f"Tạo tài khoản {vai_tro_moi}" + (f", văn phòng {van_phong_id}" if van_phong_id else "")
    _ghi_nhat_ky(actor_id, actor_vai_tro, str(tai_khoan["id"]), ghi_chu)

    return {**tai_khoan, "mat_khau_ban_dau": mat_khau}


# ---------------------------------------------------------
# Hỗ trợ giao diện
# ---------------------------------------------------------
def vai_tro_duoc_tao(actor_id: str, actor_vai_tro: str) -> dict:
    """Các vai trò người đang đăng nhập được tạo — quan_ly chỉ thêm quan_ly /
    quan_ly_nhan_su vào danh sách nếu là tài khoản gốc."""
    duoc_tao = list(_QUYEN_TAO.get(actor_vai_tro, ()))
    if any(v in _CHI_TAI_KHOAN_GOC_MOI_TAO for v in duoc_tao) and not repo.la_tai_khoan_goc(actor_id):
        duoc_tao = [v for v in duoc_tao if v not in _CHI_TAI_KHOAN_GOC_MOI_TAO]
    return {"vai_tro": duoc_tao, "vai_tro_can_van_phong": list(VAI_TRO_CAN_VAN_PHONG)}


def danh_sach_tai_khoan(actor_vai_tro: str, vai_tro: str | None = None, tu_khoa: str | None = None) -> list[dict]:
    duoc_xem = list(_QUYEN_XEM.get(actor_vai_tro, ()))
    if vai_tro:
        if vai_tro not in duoc_xem:
            raise GiaTriLoi("Vai trò không hợp lệ")
        duoc_xem = [vai_tro]
    tu_khoa = tu_khoa.strip() if tu_khoa else None
    return repo.danh_sach_tai_khoan_can_bo(duoc_xem, tu_khoa or None)


def danh_sach_van_phong() -> list[dict]:
    return repo.danh_sach_van_phong()
