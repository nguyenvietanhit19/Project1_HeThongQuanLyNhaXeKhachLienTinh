"""Unit test cho Tạo tài khoản cán bộ (UC-36) — giả lập Repository, không cần DB."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tai_khoan_can_bo_schema import TaoTaiKhoanCanBoRequest
from app.services import tai_khoan_can_bo_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi

QLNS = "quan_ly_nhan_su"
QL = "quan_ly"
VAI_TRO_VAN_HANH = ["phu_xe", "nhan_vien_quay_ve", "nhan_vien_gui_hang", "dieu_do_vien"]


def _yeu_cau(vai_tro="phu_xe", van_phong_id=None, **them):
    du_lieu = {
        "email": "canbo@gmail.com",
        "ho_ten": "Nguyen Van A",
        "so_dien_thoai": "0912345678",
        "vai_tro": vai_tro,
        "van_phong_id": van_phong_id,
    }
    du_lieu.update(them)
    return TaoTaiKhoanCanBoRequest(**du_lieu)


@pytest.fixture
def gia_lap(monkeypatch):
    """Giả lập mọi repository/dịch vụ ngoài; trả về dict ghi lại các lần gọi."""
    ghi = {"tao": [], "nhat_ky": []}

    monkeypatch.setattr(svc.repo, "la_tai_khoan_goc", lambda i: ghi.get("la_goc", False))

    def tao(email, mat_khau_hash, ho_ten, sdt, vai_tro, van_phong_id):
        ghi["tao"].append((email, ho_ten, sdt, vai_tro, van_phong_id, mat_khau_hash))
        return {"id": uuid4(), "email": email, "ho_ten": ho_ten, "vai_tro": vai_tro, "van_phong_id": van_phong_id}

    monkeypatch.setattr(svc.repo, "tao_tai_khoan", tao)
    monkeypatch.setattr(svc.nguoi_dung_repo, "tim_theo_email", lambda e: ghi.get("email_ton_tai"))
    monkeypatch.setattr(
        svc.dia_diem_repo, "tim_diem_don_tra_theo_id", lambda i: ghi.get("diem", {"id": i, "loai": "van_phong"})
    )
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: ghi["nhat_ky"].append(a))
    return ghi


# ---------------------------------------------------------
# Ma trận quyền (NGHIEP_VU.md mục 2, UC-36 bước 2)
# ---------------------------------------------------------
@pytest.mark.parametrize("vai_tro", VAI_TRO_VAN_HANH)
@pytest.mark.parametrize("actor", [QLNS, QL])
def test_ca_hai_vai_tro_tao_duoc_4_vai_tro_van_hanh(gia_lap, actor, vai_tro):
    van_phong = str(uuid4()) if vai_tro in ("nhan_vien_quay_ve", "nhan_vien_gui_hang") else None
    kq = svc.tao_tai_khoan(str(uuid4()), actor, _yeu_cau(vai_tro, van_phong))
    assert kq["vai_tro"] == vai_tro
    assert len(gia_lap["tao"]) == 1


@pytest.mark.parametrize("vai_tro", ["ke_toan", "quan_ly", "quan_ly_nhan_su"])
def test_qlns_khong_tao_duoc_ke_toan_quan_ly_qlns(gia_lap, vai_tro):
    with pytest.raises(CamTruyCap, match="Không đủ quyền"):
        svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau(vai_tro))
    assert gia_lap["tao"] == []


def test_quan_ly_thuong_tao_duoc_ke_toan(gia_lap):
    kq = svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau("ke_toan"))
    assert kq["vai_tro"] == "ke_toan"


@pytest.mark.parametrize("vai_tro", ["quan_ly", "quan_ly_nhan_su"])
def test_quan_ly_khong_goc_khong_tao_duoc_quan_ly_va_qlns(gia_lap, vai_tro):
    gia_lap["la_goc"] = False
    with pytest.raises(CamTruyCap, match="quản lý gốc"):
        svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau(vai_tro))
    assert gia_lap["tao"] == []


@pytest.mark.parametrize("vai_tro", ["quan_ly", "quan_ly_nhan_su"])
def test_quan_ly_goc_tao_duoc_quan_ly_va_qlns(gia_lap, vai_tro):
    gia_lap["la_goc"] = True
    kq = svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau(vai_tro))
    assert kq["vai_tro"] == vai_tro


def test_vai_tro_khac_khong_co_quyen_tao(gia_lap):
    with pytest.raises(CamTruyCap):
        svc.tao_tai_khoan(str(uuid4()), "nhan_vien_quay_ve", _yeu_cau("phu_xe"))


# ---------------------------------------------------------
# Dữ liệu nhập
# ---------------------------------------------------------
def test_email_trung_bi_chan(gia_lap):
    gia_lap["email_ton_tai"] = {"id": uuid4()}
    with pytest.raises(GiaTriLoi, match="Email đã tồn tại"):
        svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("phu_xe"))
    assert gia_lap["tao"] == []


def test_email_duoc_chuan_hoa_chu_thuong_va_sdt_chuan_hoa(gia_lap):
    svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("phu_xe", email="CanBo@Gmail.com", so_dien_thoai="+84 912 345 678"))
    email, _, sdt, _, _, _ = gia_lap["tao"][0]
    assert email == "canbo@gmail.com"
    assert sdt == "0912345678"


def test_sdt_sai_khong_tao_tai_khoan(gia_lap):
    with pytest.raises(GiaTriLoi, match="không hợp lệ"):
        svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("phu_xe", so_dien_thoai="12345"))
    assert gia_lap["tao"] == []


# ---------------------------------------------------------
# Văn phòng
# ---------------------------------------------------------
@pytest.mark.parametrize("vai_tro", ["nhan_vien_quay_ve", "nhan_vien_gui_hang"])
def test_quay_ve_gui_hang_gan_van_phong_khi_tao(gia_lap, vai_tro):
    van_phong = str(uuid4())
    svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau(vai_tro, van_phong))
    assert gia_lap["tao"][0][4] == van_phong


@pytest.mark.parametrize("vai_tro", ["phu_xe", "dieu_do_vien", "ke_toan"])
def test_vai_tro_khong_can_van_phong_khong_bi_doi_va_khong_gan(gia_lap, vai_tro):
    svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau(vai_tro))
    assert gia_lap["tao"][0][4] is None


def test_diem_khong_phai_van_phong_bi_chan(gia_lap):
    gia_lap["diem"] = {"id": "x", "loai": "diem_don_tra"}
    with pytest.raises(GiaTriLoi, match="văn phòng hợp lệ"):
        svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("nhan_vien_quay_ve", str(uuid4())))
    assert gia_lap["tao"] == []


def test_van_phong_khong_ton_tai_bi_chan(gia_lap):
    gia_lap["diem"] = None
    with pytest.raises(GiaTriLoi, match="văn phòng hợp lệ"):
        svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("nhan_vien_gui_hang", str(uuid4())))


# ---------------------------------------------------------
# Mật khẩu ban đầu (không gửi OTP/thư mời — email do công ty cấp)
# ---------------------------------------------------------
def test_mat_khau_ban_dau_la_12345678_va_chi_luu_ban_bam(gia_lap):
    kq = svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("phu_xe"))
    assert kq["mat_khau_ban_dau"] == "12345678"
    mat_khau_hash = gia_lap["tao"][0][5]
    assert mat_khau_hash != "12345678"  # DB không bao giờ nhận bản rõ
    assert svc._pwd_context.verify("12345678", mat_khau_hash)  # bản băm khớp mật khẩu mặc định


def test_nhat_ky_khong_chua_mat_khau(gia_lap):
    kq = svc.tao_tai_khoan(str(uuid4()), QLNS, _yeu_cau("phu_xe"))
    assert kq["mat_khau_ban_dau"] not in str(gia_lap["nhat_ky"])


# ---------------------------------------------------------
# Nhật ký (UC-52): chỉ khi actor là quan_ly_nhan_su
# ---------------------------------------------------------
def test_qlns_tao_tai_khoan_co_ghi_nhat_ky(gia_lap):
    actor = str(uuid4())
    kq = svc.tao_tai_khoan(actor, QLNS, _yeu_cau("phu_xe"))
    assert len(gia_lap["nhat_ky"]) == 1
    nguoi_ghi, hanh_dong, doi_tuong_loai, doi_tuong_id, _ = gia_lap["nhat_ky"][0]
    assert (nguoi_ghi, hanh_dong, doi_tuong_loai) == (actor, "tao_tai_khoan", "nguoi_dung")
    assert doi_tuong_id == str(kq["id"])


def test_quan_ly_tao_tai_khoan_khong_ghi_nhat_ky(gia_lap):
    svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau("phu_xe"))
    assert gia_lap["nhat_ky"] == []


# ---------------------------------------------------------
# Schema: bắt lỗi ngay ở cổng vào
# ---------------------------------------------------------
@pytest.mark.parametrize("vai_tro", ["nhan_vien_quay_ve", "nhan_vien_gui_hang"])
def test_schema_quay_ve_gui_hang_thieu_van_phong_bi_chan(vai_tro):
    with pytest.raises(ValidationError, match="bắt buộc chọn văn phòng"):
        _yeu_cau(vai_tro, None)


def test_schema_vai_tro_khong_gan_van_phong_ma_co_van_phong_bi_chan():
    with pytest.raises(ValidationError, match="không gắn văn phòng"):
        _yeu_cau("dieu_do_vien", str(uuid4()))


def test_schema_ho_ten_toan_khoang_trang_bi_chan():
    with pytest.raises(ValidationError, match="Họ tên"):
        _yeu_cau("phu_xe", ho_ten="   ")


def test_schema_email_sai_dinh_dang_bi_chan():
    with pytest.raises(ValidationError):
        _yeu_cau("phu_xe", email="khong-phai-email")


def test_schema_vai_tro_khach_hang_khong_duoc_tao_o_day():
    with pytest.raises(ValidationError):
        _yeu_cau("khach_hang")


# ---------------------------------------------------------
# Hỗ trợ giao diện
# ---------------------------------------------------------
def test_vai_tro_duoc_tao_cua_qlns_la_4_vai_tro_van_hanh(gia_lap):
    kq = svc.vai_tro_duoc_tao(str(uuid4()), QLNS)
    assert kq["vai_tro"] == VAI_TRO_VAN_HANH
    assert kq["vai_tro_can_van_phong"] == ["nhan_vien_quay_ve", "nhan_vien_gui_hang"]


def test_vai_tro_duoc_tao_cua_quan_ly_khong_goc_khong_co_quan_ly_va_qlns(gia_lap):
    gia_lap["la_goc"] = False
    assert svc.vai_tro_duoc_tao(str(uuid4()), QL)["vai_tro"] == VAI_TRO_VAN_HANH + ["ke_toan"]


def test_vai_tro_duoc_tao_cua_quan_ly_goc_co_du_7_vai_tro(gia_lap):
    gia_lap["la_goc"] = True
    assert svc.vai_tro_duoc_tao(str(uuid4()), QL)["vai_tro"] == VAI_TRO_VAN_HANH + ["ke_toan", "quan_ly", "quan_ly_nhan_su"]


def test_danh_sach_cua_qlns_khong_gom_ke_toan_quan_ly(monkeypatch):
    da_goi = []
    monkeypatch.setattr(svc.repo, "danh_sach_tai_khoan_can_bo", lambda vt, tk: da_goi.append((vt, tk)) or [])
    svc.danh_sach_tai_khoan(QLNS)
    assert da_goi[0][0] == VAI_TRO_VAN_HANH


def test_danh_sach_loc_vai_tro_ngoai_quyen_bi_chan(monkeypatch):
    monkeypatch.setattr(svc.repo, "danh_sach_tai_khoan_can_bo", lambda vt, tk: [])
    with pytest.raises(GiaTriLoi, match="Vai trò không hợp lệ"):
        svc.danh_sach_tai_khoan(QLNS, vai_tro="ke_toan")


def test_danh_sach_tu_khoa_trong_duoc_bo_qua(monkeypatch):
    da_goi = []
    monkeypatch.setattr(svc.repo, "danh_sach_tai_khoan_can_bo", lambda vt, tk: da_goi.append(tk) or [])
    svc.danh_sach_tai_khoan(QL, tu_khoa="   ")
    assert da_goi == [None]
