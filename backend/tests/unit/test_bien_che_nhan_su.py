"""Quy tắc "xe đủ nhân sự" (app/utils/bien_che.py), trường tính toán của XeResponse và dữ liệu cho hộp biên chế (bien_che_service)."""

import datetime
import uuid

import pytest

from app.schemas.xe_schema import NhanSuChiTietBienChe, NhanSuKhaDung, XeResponse
from app.services import bien_che_service as svc
from app.utils import bien_che
from app.utils.loi import GiaTriLoi


# ---------------------------------------------------------------- quy tắc thuần
@pytest.mark.parametrize("tai_xe, phu_xe, ket_qua", [(2, 1, True), (3, 2, True), (1, 1, False), (2, 0, False), (0, 0, False)])
def test_du_nhan_su(tai_xe, phu_xe, ket_qua):
    assert bien_che.du_nhan_su(tai_xe, phu_xe) is ket_qua


def test_mo_ta_thieu():
    assert bien_che.mo_ta_thieu(2, 1) == ""
    assert bien_che.mo_ta_thieu(1, 1) == "thiếu 1 tài xế"
    assert bien_che.mo_ta_thieu(2, 0) == "thiếu 1 phụ xe"
    assert bien_che.mo_ta_thieu(0, 0) == "thiếu 2 tài xế và 1 phụ xe"


def test_canh_bao_chi_cho_xe_dang_hoat_dong_co_dinh_tuyen_ma_thieu_nguoi():
    thieu = (1, 0)
    assert bien_che.can_canh_bao_thieu_nhan_su("hoat_dong", "tuyen-1", *thieu) is True
    assert bien_che.can_canh_bao_thieu_nhan_su("hoat_dong", None, *thieu) is False  # xe dự phòng: không cảnh báo
    assert bien_che.can_canh_bao_thieu_nhan_su("bao_tri", "tuyen-1", *thieu) is False  # xe không chạy: không cần
    assert bien_che.can_canh_bao_thieu_nhan_su("ngung_su_dung", "tuyen-1", *thieu) is False
    assert bien_che.can_canh_bao_thieu_nhan_su("hoat_dong", "tuyen-1", 2, 1) is False  # đã đủ


# ---------------------------------------------------------------- XeResponse tính sẵn cho trang Xe
def xe_dict(**ghi_de):
    d = {
        "id": uuid.uuid4(), "bien_so": "29B-1", "loai_xe_id": uuid.uuid4(), "ma_loai_xe": "LX001", "ten_loai_xe": "Giường nằm",
        "trang_thai": "hoat_dong", "diem_goc_id": uuid.uuid4(), "ma_diem_goc": "KV001-DT001", "ten_diem_goc": "Mỹ Đình",
        "tuyen_id": uuid.uuid4(), "ma_tuyen": "T001", "ten_tuyen": "Hà Nội - Sapa",
        "so_tai_xe_co_dinh": 2, "so_phu_xe_co_dinh": 1, "so_tai_xe_hieu_luc": 2, "so_phu_xe_hieu_luc": 1,
    }
    d.update(ghi_de)
    return d


def test_xe_response_du_nhan_su_khong_canh_bao():
    x = XeResponse(**xe_dict())
    assert x.du_nhan_su and not x.can_canh_bao_nhan_su and x.thieu_nhan_su == ""


def test_xe_response_thieu_nhan_su_co_dinh_tuyen_canh_bao_con_xe_du_phong_thi_khong():
    co_dinh = XeResponse(**xe_dict(so_tai_xe_hieu_luc=1, so_phu_xe_hieu_luc=0))
    assert not co_dinh.du_nhan_su and co_dinh.can_canh_bao_nhan_su and co_dinh.thieu_nhan_su == "thiếu 1 tài xế và 1 phụ xe"
    du_phong = XeResponse(**xe_dict(tuyen_id=None, ma_tuyen=None, ten_tuyen=None, so_tai_xe_hieu_luc=0, so_phu_xe_hieu_luc=0))
    assert not du_phong.du_nhan_su and not du_phong.can_canh_bao_nhan_su  # dự phòng: thiếu vẫn là thiếu nhưng không cảnh báo
    xuat = du_phong.model_dump()
    assert xuat["can_canh_bao_nhan_su"] is False and xuat["du_nhan_su"] is False  # có trong JSON trả ra


# ---------------------------------------------------------------- phân loại hạn giấy tờ
HOM_NAY = datetime.date(2026, 11, 6)


@pytest.mark.parametrize("ngay, ket_qua", [
    (None, None),
    (HOM_NAY - datetime.timedelta(days=1), "het_han"),
    (HOM_NAY, "sap_het_han"),
    (HOM_NAY + datetime.timedelta(days=30), "sap_het_han"),
    (HOM_NAY + datetime.timedelta(days=31), "con_han"),
])
def test_phan_loai_han(ngay, ket_qua):
    assert svc.phan_loai_han(ngay, HOM_NAY) == ket_qua


# ---------------------------------------------------------------- danh sách ứng viên
def _ung_vien(ngay_het_han_som):
    return {
        "id": uuid.uuid4(), "ma": "TX0001", "ho_ten": "A", "so_dien_thoai": "09", "chuc_danh": "tai_xe", "co_tai_khoan": False,
        "email": None, "ngay_vao_lam": None, "xe_id_co_dinh": None, "bien_so_xe_co_dinh": None, "ngay_het_han_giay_to_som": ngay_het_han_som,
    }


def test_danh_sach_ung_vien_gan_dau_hieu_giay_to_co_van_de(monkeypatch):
    monkeypatch.setattr(svc, "_hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(svc.nhan_su_repo, "danh_sach_dang_lam", lambda: [
        _ung_vien(HOM_NAY - datetime.timedelta(days=5)), _ung_vien(HOM_NAY + datetime.timedelta(days=10)),
        _ung_vien(HOM_NAY + datetime.timedelta(days=400)), _ung_vien(None),
    ])
    kq = svc.danh_sach_nhan_su_dang_lam()
    assert [n["giay_to_tinh_trang"] for n in kq] == ["het_han", "sap_het_han", None, None]
    assert all("ngay_het_han_giay_to_som" not in n for n in kq)
    NhanSuKhaDung(**kq[0])  # khớp schema trả ra API


# ---------------------------------------------------------------- chi tiết nhân sự cho hộp biên chế
def _ho_so(**ghi_de):
    d = {
        "id": uuid.uuid4(), "ma": "PX0003", "ho_ten": "Lê Thị Hương", "so_dien_thoai": "0912", "chuc_danh": "phu_xe", "nguoi_dung_id": uuid.uuid4(),
        "so_cccd": "001099000111", "ngay_sinh": datetime.date(1990, 1, 1), "anh_ho_so": "abc", "ngay_vao_lam": datetime.date(2024, 3, 1),
        "trang_thai": "dang_lam", "ngay_nghi_viec": None, "ly_do_nghi_viec": None,
    }
    d.update(ghi_de)
    return d


def test_chi_tiet_nhan_su_tra_toan_bo_ho_so_de_xem(monkeypatch):
    monkeypatch.setattr(svc, "_hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(svc.luu_tru_anh_service, "lay_url_xem", lambda public_id: f"https://anh.test/{public_id}")
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda _id: _ho_so())
    monkeypatch.setattr(svc.nhan_su_repo, "email_tai_khoan", lambda _id: {"email": "phuxe03@example.com", "dang_hoat_dong": True})
    monkeypatch.setattr(svc.giay_to_repo, "danh_sach_theo_nhan_su", lambda _id: [
        {"loai": "bang_lai", "so_giay_to": "BL123", "hang": "D", "ngay_cap": datetime.date(2023, 6, 1),
         "ngay_het_han": HOM_NAY + datetime.timedelta(days=10), "anh_giay_to": "x"}])
    xe_id = uuid.uuid4()
    monkeypatch.setattr(svc.nhan_su_repo, "bien_che_cua_nhan_su", lambda _id: [
        {"id": uuid.uuid4(), "xe_id": xe_id, "bien_so": "29B-1", "loai": "co_dinh", "trang_thai": "dang_hoat_dong"}])
    kq = svc.chi_tiet_nhan_su("x")
    # Toàn bộ hồ sơ để xem: CCCD, ngày sinh, ảnh (URL có chữ ký, không phải public_id), số giấy tờ + ảnh giấy tờ
    assert kq["so_cccd"] == "001099000111" and kq["ngay_sinh"] == datetime.date(1990, 1, 1)
    assert kq["anh_url"] == "https://anh.test/abc" and "anh_ho_so" not in kq and "nguoi_dung_id" not in kq
    assert kq["giay_to"][0]["so_giay_to"] == "BL123" and kq["giay_to"][0]["anh_url"] == "https://anh.test/x" and "anh_giay_to" not in kq["giay_to"][0]
    assert kq["ngay_nghi_viec"] is None and kq["ly_do_nghi_viec"] is None
    assert kq["email"] == "phuxe03@example.com" and kq["tai_khoan_hoat_dong"] is True and kq["co_tai_khoan"] is True
    assert kq["giay_to"][0]["tinh_trang"] == "sap_het_han" and kq["giay_to"][0]["hang"] == "D"
    assert kq["bien_che"][0]["bien_so"] == "29B-1"
    assert NhanSuChiTietBienChe(**kq).ma == "PX0003"  # khớp schema


def test_chi_tiet_tai_xe_khong_co_tai_khoan(monkeypatch):
    monkeypatch.setattr(svc, "_hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda _id: _ho_so(chuc_danh="tai_xe", nguoi_dung_id=None, ma="TX0001"))
    monkeypatch.setattr(svc.giay_to_repo, "danh_sach_theo_nhan_su", lambda _id: [])
    monkeypatch.setattr(svc.nhan_su_repo, "bien_che_cua_nhan_su", lambda _id: [])
    kq = svc.chi_tiet_nhan_su("x")
    assert kq["co_tai_khoan"] is False and kq["email"] is None and kq["tai_khoan_hoat_dong"] is None
    assert kq["giay_to"] == [] and kq["bien_che"] == []


def test_chi_tiet_nhan_su_khong_ton_tai(monkeypatch):
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda _id: None)
    with pytest.raises(GiaTriLoi, match="Không tìm thấy nhân sự"):
        svc.chi_tiet_nhan_su("x")


def test_chi_tiet_loi_sinh_url_anh_khong_lam_hong_viec_xem_ho_so(monkeypatch):
    # máy dev chưa cấu hình Cloudinary → lay_url_xem ném lỗi: chi tiết vẫn trả được, ảnh coi như chưa có
    monkeypatch.setattr(svc, "_hom_nay", lambda: HOM_NAY)

    def hong(_public_id):
        raise ValueError("Must supply api_secret")

    monkeypatch.setattr(svc.luu_tru_anh_service, "lay_url_xem", hong)
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda _id: _ho_so(chuc_danh="tai_xe", nguoi_dung_id=None, anh_ho_so="abc"))
    monkeypatch.setattr(svc.giay_to_repo, "danh_sach_theo_nhan_su", lambda _id: [
        {"loai": "bang_lai", "so_giay_to": "BL1", "hang": "E", "ngay_cap": None, "ngay_het_han": HOM_NAY + datetime.timedelta(days=500), "anh_giay_to": "x"}])
    monkeypatch.setattr(svc.nhan_su_repo, "bien_che_cua_nhan_su", lambda _id: [])
    kq = svc.chi_tiet_nhan_su("x")
    assert kq["anh_url"] is None and kq["giay_to"][0]["anh_url"] is None and kq["giay_to"][0]["so_giay_to"] == "BL1"


def test_chi_tiet_nhan_su_da_nghi_viec_co_ngay_va_ly_do_nghi(monkeypatch):
    monkeypatch.setattr(svc, "_hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda _id: _ho_so(trang_thai="da_nghi_viec", ngay_nghi_viec=datetime.date(2026, 10, 15), ly_do_nghi_viec="Nghỉ việc cá nhân"))
    monkeypatch.setattr(svc.nhan_su_repo, "email_tai_khoan", lambda _id: {"email": "a@example.com", "dang_hoat_dong": False})
    monkeypatch.setattr(svc.giay_to_repo, "danh_sach_theo_nhan_su", lambda _id: [])
    monkeypatch.setattr(svc.nhan_su_repo, "bien_che_cua_nhan_su", lambda _id: [])
    kq = svc.chi_tiet_nhan_su("x")
    assert kq["trang_thai"] == "da_nghi_viec" and kq["ngay_nghi_viec"] == datetime.date(2026, 10, 15) and kq["ly_do_nghi_viec"] == "Nghỉ việc cá nhân"
    assert kq["tai_khoan_hoat_dong"] is False
    NhanSuChiTietBienChe(**kq)
