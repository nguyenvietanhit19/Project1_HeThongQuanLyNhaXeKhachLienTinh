"""Đăng ký/đăng nhập/quên mật khẩu — NGHIEP_VU.md mục 2.1.

Kế thừa luồng nghiệp vụ từ bản v1 (GiaoThongAnToan_API/routes/auth.py +
quen_mat_khau.py), viết lại theo kiến trúc 3 lớp. Sửa 1 điểm khác v1: hạn
mã OTP đăng ký nhất quán 1 phút cho MỌI trường hợp (v1 có chỗ để nhầm 10
phút khi email đã tồn tại nhưng chưa kích hoạt — không khớp NGHIEP_VU.md).
"""

import datetime
import random

from passlib.context import CryptContext

from app.middleware.auth_middleware import tao_token
from app.repositories import nguoi_dung_repository as repo
from app.services.email_service import gui_mail
from app.utils.loi import GiaTriLoi, KhongDuQuyen, LoiHeThong

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

HAN_MA_XAC_NHAN_PHUT = 1  # NGHIEP_VU.md mục 2.1 điểm 1 — ngắn vì gửi qua email gần như tức thời


def _sinh_ma_va_han() -> tuple[str, datetime.datetime]:
    ma = f"{random.randint(0, 999999):06d}"
    het_han = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=HAN_MA_XAC_NHAN_PHUT)
    return ma, het_han


def _da_het_han(ma_het_han: datetime.datetime | None) -> bool:
    return ma_het_han is None or datetime.datetime.now(datetime.timezone.utc) > ma_het_han


def gui_ma_dang_ky(email: str, mat_khau: str, ho_ten: str, so_dien_thoai: str) -> None:
    nguoi_dung = repo.tim_theo_email(email)
    ma, het_han = _sinh_ma_va_han()
    mat_khau_hash = _pwd_context.hash(mat_khau)

    if nguoi_dung:
        if nguoi_dung["da_xac_nhan"]:
            raise GiaTriLoi("Email đã được sử dụng")
        repo.cap_nhat_lai_thong_tin_va_ma(nguoi_dung["id"], mat_khau_hash, ho_ten, so_dien_thoai, ma, het_han)
    else:
        repo.tao_khach_hang_chua_kich_hoat(email, mat_khau_hash, ho_ten, so_dien_thoai, ma, het_han)

    if not gui_mail(email, ma, tieu_de="Mã xác nhận đăng ký tài khoản"):
        raise LoiHeThong("Không thể gửi email, thử lại sau")


def xac_nhan_dang_ky(email: str, ma_xac_nhan: str) -> None:
    nguoi_dung = repo.tim_theo_email(email)
    if not nguoi_dung:
        raise GiaTriLoi("Email không tồn tại, vui lòng đăng ký lại")
    if nguoi_dung["da_xac_nhan"]:
        raise GiaTriLoi("Tài khoản đã được kích hoạt, vui lòng đăng nhập")
    if not nguoi_dung["ma_xac_nhan"]:
        raise GiaTriLoi("Chưa yêu cầu gửi mã, vui lòng thực hiện lại từ đầu")
    if ma_xac_nhan != nguoi_dung["ma_xac_nhan"]:
        raise GiaTriLoi("Mã xác nhận không đúng")
    if _da_het_han(nguoi_dung["ma_het_han"]):
        repo.xoa_ma_xac_nhan(nguoi_dung["id"])
        raise GiaTriLoi("Mã đã hết hạn, vui lòng yêu cầu mã mới")

    repo.kich_hoat_tai_khoan(nguoi_dung["id"])


def dang_nhap(email: str, mat_khau: str) -> dict:
    nguoi_dung = repo.tim_theo_email(email)
    if not nguoi_dung or not nguoi_dung["mat_khau"]:
        raise KhongDuQuyen("Email hoặc mật khẩu sai")
    if not nguoi_dung["da_xac_nhan"]:
        raise KhongDuQuyen("Tài khoản chưa xác nhận")
    if not nguoi_dung["dang_hoat_dong"]:
        raise KhongDuQuyen("Tài khoản đã bị khóa")
    if not _pwd_context.verify(mat_khau, nguoi_dung["mat_khau"]):
        raise KhongDuQuyen("Email hoặc mật khẩu sai")

    token = tao_token(nguoi_dung["id"], nguoi_dung["vai_tro"])
    return {"token": token, "ho_ten": nguoi_dung["ho_ten"], "vai_tro": nguoi_dung["vai_tro"]}


def quen_mat_khau(email: str) -> None:
    nguoi_dung = repo.tim_theo_email(email)
    if not nguoi_dung:
        return  # không tiết lộ email có tồn tại hay không — NGHIEP_VU.md mục 2.1 điểm 4

    ma, het_han = _sinh_ma_va_han()
    repo.cap_nhat_ma_xac_nhan_quen_mat_khau(nguoi_dung["id"], ma, het_han)

    if not gui_mail(email, ma, tieu_de="Mã xác nhận đặt lại mật khẩu"):
        raise LoiHeThong("Không thể gửi email, thử lại sau")


def dat_lai_mat_khau(email: str, ma_xac_nhan: str, mat_khau_moi: str) -> None:
    nguoi_dung = repo.tim_theo_email(email)
    if not nguoi_dung:
        raise GiaTriLoi("Email không tồn tại")
    if not nguoi_dung["ma_xac_nhan"]:
        raise GiaTriLoi("Chưa yêu cầu đặt lại mật khẩu")
    if ma_xac_nhan != nguoi_dung["ma_xac_nhan"]:
        raise GiaTriLoi("Mã xác nhận không đúng")
    if _da_het_han(nguoi_dung["ma_het_han"]):
        repo.xoa_ma_xac_nhan(nguoi_dung["id"])
        raise GiaTriLoi("Mã xác nhận đã hết hạn, vui lòng yêu cầu mã mới")

    repo.dat_lai_mat_khau(nguoi_dung["id"], _pwd_context.hash(mat_khau_moi))


def doi_mat_khau(nguoi_dung_id: str, mat_khau_cu: str, mat_khau_moi: str) -> None:
    mat_khau_hash_cu = repo.lay_mat_khau_hash(nguoi_dung_id)
    if not mat_khau_hash_cu or not _pwd_context.verify(mat_khau_cu, mat_khau_hash_cu):
        raise GiaTriLoi("Mật khẩu cũ không đúng")

    repo.cap_nhat_mat_khau(nguoi_dung_id, _pwd_context.hash(mat_khau_moi))


def lay_thong_tin(nguoi_dung_id: str) -> dict:
    nguoi_dung = repo.tim_theo_id(nguoi_dung_id)
    if not nguoi_dung:
        raise GiaTriLoi("Không tìm thấy tài khoản")
    return nguoi_dung


def sua_ho_ten(nguoi_dung_id: str, ho_ten: str) -> None:
    repo.cap_nhat_ho_ten(nguoi_dung_id, ho_ten)
