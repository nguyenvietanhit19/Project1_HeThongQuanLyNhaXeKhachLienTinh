"""Unit test cho Tạo tài khoản cán bộ (UC-36) — giả lập Repository, không cần DB."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tai_khoan_can_bo_schema import TaoTaiKhoanCanBoRequest
from app.services import tai_khoan_can_bo_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

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


# =========================================================
# UC-37: khóa / mở khóa tài khoản cán bộ
# =========================================================
def _tk(vai_tro="phu_xe", hoat_dong=True, goc=False, ma=None):
    return {
        "id": ma or str(uuid4()), "email": "x@gmail.com", "ho_ten": "Tran Van B",
        "vai_tro": vai_tro, "dang_hoat_dong": hoat_dong, "la_tai_khoan_goc": goc,
    }


@pytest.fixture
def khoa_gia_lap(monkeypatch):
    """Giả lập repository + thông báo cho khóa / mở khóa."""
    g = {"muc_tieu": _tk(), "goc": False, "xe_thieu": [], "dat": [], "nk_qlns": [], "nk_admin": [], "tb": [], "so_lan_tra_bien_che": 0}
    monkeypatch.setattr(svc.repo, "tim_tai_khoan", lambda i: g["muc_tieu"])
    monkeypatch.setattr(svc.repo, "la_tai_khoan_goc", lambda i: g["goc"])
    monkeypatch.setattr(svc.repo, "dat_trang_thai_hoat_dong", lambda i, v: g["dat"].append((i, v)))

    def xe_thieu(i):
        g["so_lan_tra_bien_che"] += 1
        return g["xe_thieu"]

    monkeypatch.setattr(svc.repo, "xe_thieu_phu_xe", xe_thieu)
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: g["nk_qlns"].append(a))
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: g["nk_admin"].append(a))
    monkeypatch.setattr(
        svc.nguoi_dung_repo, "danh_sach_id_theo_vai_tro",
        lambda vt, chi_dang_hoat_dong=False: g.get("nguoi_nhan", {}).get(vt, []),
    )
    monkeypatch.setattr(svc.thong_bao, "gui", lambda nguoi, nd, **kw: g["tb"].append((nguoi, nd)))
    return g


def _khoa(g, actor, vai_tro_muc_tieu, **kw):
    g["muc_tieu"] = _tk(vai_tro_muc_tieu, **kw)
    return svc.khoa_tai_khoan(str(uuid4()), actor, g["muc_tieu"]["id"], "  vi pham  ")


# ---- Ma trận quyền theo bậc ----
@pytest.mark.parametrize("vai_tro", VAI_TRO_VAN_HANH)
@pytest.mark.parametrize("actor,goc", [(QLNS, False), (QL, False), (QL, True)])
def test_khoa_ba_bac_deu_khoa_duoc_4_vai_tro_van_hanh(khoa_gia_lap, actor, goc, vai_tro):
    khoa_gia_lap["goc"] = goc
    kq = _khoa(khoa_gia_lap, actor, vai_tro)
    assert kq["dang_hoat_dong"] is False
    assert khoa_gia_lap["dat"][-1][1] is False


@pytest.mark.parametrize("vai_tro", ["ke_toan", "quan_ly", "quan_ly_nhan_su"])
def test_qlns_khong_khoa_duoc_ke_toan_quan_ly_qlns(khoa_gia_lap, vai_tro):
    with pytest.raises(CamTruyCap, match="Không đủ quyền"):
        _khoa(khoa_gia_lap, QLNS, vai_tro)
    assert khoa_gia_lap["dat"] == []


def test_quan_ly_thuong_khoa_duoc_qlns(khoa_gia_lap):
    assert _khoa(khoa_gia_lap, QL, "quan_ly_nhan_su")["dang_hoat_dong"] is False


@pytest.mark.parametrize("vai_tro", ["quan_ly", "ke_toan"])
def test_quan_ly_thuong_khong_khoa_duoc_quan_ly_khac_va_ke_toan(khoa_gia_lap, vai_tro):
    with pytest.raises(CamTruyCap, match="Không đủ quyền"):
        _khoa(khoa_gia_lap, QL, vai_tro)


@pytest.mark.parametrize("vai_tro", ["quan_ly", "ke_toan", "quan_ly_nhan_su"])
def test_quan_ly_goc_khoa_duoc_cap_duoi(khoa_gia_lap, vai_tro):
    khoa_gia_lap["goc"] = True
    assert _khoa(khoa_gia_lap, QL, vai_tro)["dang_hoat_dong"] is False


# ---- Luật chặn ----
@pytest.mark.parametrize("actor", [QLNS, QL])
def test_khong_ai_khoa_duoc_tai_khoan_goc(khoa_gia_lap, actor):
    khoa_gia_lap["goc"] = True
    with pytest.raises(CamTruyCap, match="gốc"):
        _khoa(khoa_gia_lap, actor, "quan_ly", goc=True)


def test_khong_tu_khoa_chinh_minh(khoa_gia_lap):
    ma = str(uuid4())
    khoa_gia_lap["muc_tieu"] = _tk("phu_xe", ma=ma)
    with pytest.raises(CamTruyCap, match="tự khóa"):
        svc.khoa_tai_khoan(ma, QLNS, ma, "ly do")


def test_khoa_tai_khoan_da_khoa_bi_chan(khoa_gia_lap):
    with pytest.raises(GiaTriLoi, match="đã bị khóa"):
        _khoa(khoa_gia_lap, QLNS, "phu_xe", hoat_dong=False)


def test_mo_khoa_tai_khoan_dang_hoat_dong_bi_chan(khoa_gia_lap):
    khoa_gia_lap["muc_tieu"] = _tk("phu_xe", hoat_dong=True)
    with pytest.raises(GiaTriLoi, match="đang hoạt động"):
        svc.mo_khoa_tai_khoan(str(uuid4()), QLNS, khoa_gia_lap["muc_tieu"]["id"], "ly do")


def test_tai_khoan_khong_ton_tai_404(khoa_gia_lap):
    khoa_gia_lap["muc_tieu"] = None
    with pytest.raises(KhongTimThay):
        svc.khoa_tai_khoan(str(uuid4()), QLNS, str(uuid4()), "ly do")


@pytest.mark.parametrize("actor", [QLNS, QL])
def test_khong_khoa_khach_hang(khoa_gia_lap, actor):
    with pytest.raises(GiaTriLoi, match="khách hàng"):
        _khoa(khoa_gia_lap, actor, "khach_hang")


# ---- Mở khóa ----
def test_mo_khoa_thanh_cong(khoa_gia_lap):
    khoa_gia_lap["muc_tieu"] = _tk("dieu_do_vien", hoat_dong=False)
    kq = svc.mo_khoa_tai_khoan(str(uuid4()), QLNS, khoa_gia_lap["muc_tieu"]["id"], " da giai trinh ")
    assert kq["dang_hoat_dong"] is True and kq["canh_bao_xe_thieu_phu_xe"] == []
    assert khoa_gia_lap["dat"][-1][1] is True
    assert khoa_gia_lap["nk_qlns"][0][1] == "mo_khoa_tai_khoan"
    assert khoa_gia_lap["nk_qlns"][0][4] == "da giai trinh"


@pytest.mark.parametrize("vai_tro", ["ke_toan", "quan_ly", "quan_ly_nhan_su"])
def test_mo_khoa_qlns_cung_quy_tac_bac(khoa_gia_lap, vai_tro):
    khoa_gia_lap["muc_tieu"] = _tk(vai_tro, hoat_dong=False)
    with pytest.raises(CamTruyCap):
        svc.mo_khoa_tai_khoan(str(uuid4()), QLNS, khoa_gia_lap["muc_tieu"]["id"], "ly do")


def test_mo_khoa_quan_ly_thuong_bi_chan_voi_ke_toan(khoa_gia_lap):
    khoa_gia_lap["muc_tieu"] = _tk("ke_toan", hoat_dong=False)
    with pytest.raises(CamTruyCap):
        svc.mo_khoa_tai_khoan(str(uuid4()), QL, khoa_gia_lap["muc_tieu"]["id"], "ly do")


# ---- Nhật ký ----
def test_qlns_khoa_ghi_nhat_ky_qlns_kem_ly_do_da_strip(khoa_gia_lap):
    _khoa(khoa_gia_lap, QLNS, "phu_xe")
    assert len(khoa_gia_lap["nk_qlns"]) == 1 and khoa_gia_lap["nk_admin"] == []
    _, hanh_dong, loai, doi_tuong, ghi_chu = khoa_gia_lap["nk_qlns"][0]
    assert (hanh_dong, loai, ghi_chu) == ("khoa_tai_khoan", "nguoi_dung", "vi pham")
    assert doi_tuong == khoa_gia_lap["muc_tieu"]["id"]


@pytest.mark.parametrize("goc", [True, False])
def test_quan_ly_khoa_ghi_nhat_ky_admin_khong_ghi_sang_bang_qlns(khoa_gia_lap, goc):
    khoa_gia_lap["goc"] = goc
    _khoa(khoa_gia_lap, QL, "phu_xe")
    assert len(khoa_gia_lap["nk_admin"]) == 1 and khoa_gia_lap["nk_qlns"] == []
    assert khoa_gia_lap["nk_admin"][0][1] == "khoa_tai_khoan"
    assert khoa_gia_lap["nk_admin"][0][4] == "vi pham"


def test_khoa_bi_chan_thi_khong_ghi_nhat_ky(khoa_gia_lap):
    with pytest.raises(CamTruyCap):
        _khoa(khoa_gia_lap, QLNS, "ke_toan")
    assert khoa_gia_lap["nk_qlns"] == [] and khoa_gia_lap["nk_admin"] == []


def test_tao_tai_khoan_cua_quan_ly_van_khong_ghi_nhat_ky_admin(gia_lap, monkeypatch):
    ds = []
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: ds.append(a))
    svc.tao_tai_khoan(str(uuid4()), QL, _yeu_cau("phu_xe"))
    assert ds == []


# ---- Phụ xe: cảnh báo thiếu xe ----
def test_khoa_phu_xe_thieu_xe_co_canh_bao_va_thong_bao_dung_nguoi(khoa_gia_lap):
    quan_ly, dieu_do = str(uuid4()), str(uuid4())
    khoa_gia_lap["xe_thieu"] = [{"xe_id": uuid4(), "bien_so": "51B-111"}, {"xe_id": uuid4(), "bien_so": "51B-222"}]
    khoa_gia_lap["muc_tieu"] = _tk("phu_xe")
    vua_khoa = khoa_gia_lap["muc_tieu"]["id"]
    khoa_gia_lap["nguoi_nhan"] = {"quan_ly": [quan_ly], "dieu_do_vien": [dieu_do, vua_khoa]}
    kq = svc.khoa_tai_khoan(str(uuid4()), QLNS, vua_khoa, "ly do")
    assert [x["bien_so"] for x in kq["canh_bao_xe_thieu_phu_xe"]] == ["51B-111", "51B-222"]
    assert {n for n, _ in khoa_gia_lap["tb"]} == {quan_ly, dieu_do}
    assert "51B-111, 51B-222" in khoa_gia_lap["tb"][0][1]


def test_khoa_phu_xe_khong_thieu_xe_khong_thong_bao(khoa_gia_lap):
    khoa_gia_lap["nguoi_nhan"] = {"quan_ly": [str(uuid4())]}
    kq = _khoa(khoa_gia_lap, QLNS, "phu_xe")
    assert kq["canh_bao_xe_thieu_phu_xe"] == [] and khoa_gia_lap["tb"] == []


def test_chi_tim_quan_ly_va_dieu_do_vien_dang_hoat_dong_khong_tim_qlns(khoa_gia_lap, monkeypatch):
    goi = []
    monkeypatch.setattr(
        svc.nguoi_dung_repo, "danh_sach_id_theo_vai_tro",
        lambda vt, chi_dang_hoat_dong=False: goi.append((vt, chi_dang_hoat_dong)) or [],
    )
    khoa_gia_lap["xe_thieu"] = [{"xe_id": uuid4(), "bien_so": "51B-111"}]
    _khoa(khoa_gia_lap, QLNS, "phu_xe")
    assert sorted(goi) == [("dieu_do_vien", True), ("quan_ly", True)]


@pytest.mark.parametrize("vai_tro", ["dieu_do_vien", "nhan_vien_quay_ve", "nhan_vien_gui_hang"])
def test_vai_tro_khac_phu_xe_khong_tra_bien_che(khoa_gia_lap, vai_tro):
    _khoa(khoa_gia_lap, QLNS, vai_tro)
    assert khoa_gia_lap["so_lan_tra_bien_che"] == 0


def test_mo_khoa_khong_tra_bien_che_khong_thong_bao(khoa_gia_lap):
    khoa_gia_lap["muc_tieu"] = _tk("phu_xe", hoat_dong=False)
    svc.mo_khoa_tai_khoan(str(uuid4()), QLNS, khoa_gia_lap["muc_tieu"]["id"], "ly do")
    assert khoa_gia_lap["so_lan_tra_bien_che"] == 0 and khoa_gia_lap["tb"] == []
