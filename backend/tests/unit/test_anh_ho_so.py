"""Unit test lưu ảnh hồ sơ nhân sự bằng Cloudinary (UC-49, KE_HOACH_CLOUDINARY.md): kiểm tra file tải lên, thứ tự
tải -> lưu DB -> xóa ảnh cũ, thư mục theo môi trường, hàm repository trả ảnh cũ. Cloudinary và DB đều được giả lập."""

import importlib
from datetime import date
from uuid import uuid4

import pytest

from app import config
from app.repositories import giay_to_nhan_su_repository as giay_to_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.services import ho_so_nhan_su_service as svc
from app.services import luu_tru_anh_service as luu_tru
from app.utils import kiem_tra_anh
from app.utils.kiem_tra_anh import KICH_THUOC_TOI_DA_BYTE, kiem_tra_file_anh, nhan_dien_dinh_dang
from app.utils.loi import GiaTriLoi, KhongTimThay, LoiHeThong

JPG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
WEBP = b"RIFF\x20\x00\x00\x00WEBPVP8 " + b"0" * 32
QLNS = "quan_ly_nhan_su"


# ---------------------------------------------------------
# Kiểm tra file tải lên (≤ 5MB, JPEG / PNG / WebP theo nội dung thật)
# ---------------------------------------------------------
@pytest.mark.parametrize("du_lieu,mong_doi", [(JPG, "jpeg"), (PNG, "png"), (WEBP, "webp")])
def test_dinh_dang_hop_le_duoc_nhan_dien_theo_noi_dung(du_lieu, mong_doi):
    assert nhan_dien_dinh_dang(du_lieu) == mong_doi
    assert kiem_tra_file_anh(du_lieu) == mong_doi


@pytest.mark.parametrize(
    "du_lieu",
    [
        b"MZ\x90\x00" + b"0" * 64,                            # file .exe đổi đuôi thành .jpg
        b"GIF89a" + b"0" * 64,                                 # GIF
        b"%PDF-1.4" + b"0" * 64,                               # PDF
        b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",     # SVG (có thể chứa script)
        b"RIFF\x20\x00\x00\x00WAVEfmt " + b"0" * 32,           # RIFF nhưng là WAV, không phải WebP
        b"\xff\xd8",                                           # cụt, chưa đủ 3 byte chữ ký JPEG
        b"\x89PNG",                                            # cụt chữ ký PNG
    ],
)
def test_dinh_dang_khac_bi_tu_choi(du_lieu):
    assert nhan_dien_dinh_dang(du_lieu) is None
    with pytest.raises(GiaTriLoi, match="JPEG, PNG hoặc WebP"):
        kiem_tra_file_anh(du_lieu)


def test_file_rong_bi_tu_choi():
    with pytest.raises(GiaTriLoi, match="rỗng"):
        kiem_tra_file_anh(b"")


def test_kich_thuoc_toi_da_la_5mb_dung_5mb_duoc_them_1_byte_bi_chan():
    assert KICH_THUOC_TOI_DA_BYTE == 5 * 1024 * 1024
    dung = JPG + b"0" * (KICH_THUOC_TOI_DA_BYTE - len(JPG))
    assert kiem_tra_file_anh(dung) == "jpeg"
    with pytest.raises(GiaTriLoi, match="5MB"):
        kiem_tra_file_anh(dung + b"0")


def test_kich_thuoc_duoc_kiem_tra_truoc_dinh_dang():
    with pytest.raises(GiaTriLoi, match="quá lớn"):
        kiem_tra_file_anh(b"MZ" + b"0" * KICH_THUOC_TOI_DA_BYTE)


# ---------------------------------------------------------
# Service: thứ tự tải -> lưu DB -> xóa ảnh cũ
# ---------------------------------------------------------
@pytest.fixture
def gia_lap(monkeypatch):
    g = {"su_kien": [], "tai_ket_qua": "moi-1", "xoa_ket_qua": True, "anh_cu": None, "ho_so": {"id": uuid4()}, "giay_to": {"id": uuid4(), "anh_giay_to": None},
         "nk": [], "thu_muc": []}

    def tai(du_lieu, thu_muc):
        g["su_kien"].append("tai")
        g["thu_muc"].append(thu_muc)
        return g["tai_ket_qua"]

    def xoa(public_id):
        g["su_kien"].append(("xoa", public_id))
        return g["xoa_ket_qua"]

    def luu_ho_so(nhan_su_id, public_id):
        g["su_kien"].append(("luu", public_id))
        return g["anh_cu"]

    def luu_giay_to(giay_to_id, public_id):
        g["su_kien"].append(("luu", public_id))
        return g["anh_cu"]

    monkeypatch.setattr(luu_tru, "tai_anh_len", tai)
    monkeypatch.setattr(luu_tru, "xoa_anh", xoa)
    monkeypatch.setattr(luu_tru, "lay_url_xem", lambda public_id: f"https://xem/{public_id}")
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda i: g["ho_so"])
    monkeypatch.setattr(svc.nhan_su_repo, "cap_nhat_anh_ho_so", luu_ho_so)
    monkeypatch.setattr(svc.giay_to_repo, "tim_theo_nhan_su_va_loai", lambda i, loai: g["giay_to"])
    monkeypatch.setattr(svc.giay_to_repo, "cap_nhat_anh", luu_giay_to)
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: g["nk"].append(a))
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: g["nk"].append(a))
    return g


def _anh_ho_so(du_lieu=JPG):
    return svc.cap_nhat_anh_ho_so(str(uuid4()), QLNS, str(uuid4()), du_lieu)


def _anh_giay_to(du_lieu=JPG, loai="bang_lai"):
    return svc.cap_nhat_anh_giay_to(str(uuid4()), QLNS, str(uuid4()), loai, du_lieu)


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
def test_thu_tu_tai_len_roi_luu_db_roi_moi_xoa_anh_cu(gia_lap, ham):
    gia_lap["anh_cu"] = "cu-1"
    url = ham()
    assert gia_lap["su_kien"] == ["tai", ("luu", "moi-1"), ("xoa", "cu-1")]
    assert url == "https://xem/moi-1"


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
def test_lan_dau_chua_co_anh_cu_thi_khong_xoa_gi(gia_lap, ham):
    gia_lap["anh_cu"] = None
    ham()
    assert gia_lap["su_kien"] == ["tai", ("luu", "moi-1")]


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
def test_anh_cu_trung_anh_moi_thi_khong_xoa(gia_lap, ham):
    gia_lap["anh_cu"] = "moi-1"
    ham()
    assert not any(isinstance(e, tuple) and e[0] == "xoa" for e in gia_lap["su_kien"])


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
def test_tai_len_loi_thi_giu_anh_cu_khong_luu_khong_xoa(gia_lap, ham):
    gia_lap["tai_ket_qua"] = None
    gia_lap["anh_cu"] = "cu-1"
    with pytest.raises(LoiHeThong, match="Không thể tải ảnh lên"):
        ham()
    assert gia_lap["su_kien"] == ["tai"] and gia_lap["nk"] == []


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
def test_xoa_anh_cu_loi_khong_lam_hong_viec_doi_anh(gia_lap, ham, capsys):
    gia_lap["anh_cu"] = "cu-1"
    gia_lap["xoa_ket_qua"] = False
    assert ham() == "https://xem/moi-1"
    assert "cu-1" in capsys.readouterr().out
    assert len(gia_lap["nk"]) == 1


@pytest.mark.parametrize("ham", [_anh_ho_so, _anh_giay_to])
@pytest.mark.parametrize("du_lieu", [b"", b"MZ" + b"0" * 64, JPG + b"0" * KICH_THUOC_TOI_DA_BYTE])
def test_file_sai_bi_chan_truoc_khi_cham_cloudinary(gia_lap, ham, du_lieu):
    with pytest.raises(GiaTriLoi):
        ham(du_lieu)
    assert gia_lap["su_kien"] == [] and gia_lap["nk"] == []


def test_ho_so_khong_ton_tai_la_404_chua_cham_cloudinary(gia_lap):
    gia_lap["ho_so"] = None
    with pytest.raises(KhongTimThay):
        _anh_ho_so()
    assert gia_lap["su_kien"] == []


def test_giay_to_chua_nhap_thong_tin_la_404_chua_cham_cloudinary(gia_lap):
    gia_lap["giay_to"] = None
    with pytest.raises(KhongTimThay, match="nhập thông tin giấy tờ"):
        _anh_giay_to()
    assert gia_lap["su_kien"] == []


def test_anh_chan_dung_vao_thu_muc_ho_so_anh_giay_to_vao_thu_muc_giay_to(gia_lap):
    _anh_ho_so()
    _anh_giay_to()
    assert gia_lap["thu_muc"] == [luu_tru.THU_MUC_ANH_HO_SO, luu_tru.THU_MUC_ANH_GIAY_TO]
    assert luu_tru.THU_MUC_ANH_HO_SO != luu_tru.THU_MUC_ANH_GIAY_TO


def test_nhat_ky_ghi_dung_mot_dong_cho_moi_lan_doi_anh(gia_lap):
    _anh_ho_so()
    _anh_giay_to(loai="giay_kham_suc_khoe")
    assert [d[1] for d in gia_lap["nk"]] == ["sua_ho_so_nhan_su", "sua_ho_so_nhan_su"]
    assert "giay_kham_suc_khoe" in gia_lap["nk"][1][4]


# ---------------------------------------------------------
# Gia hạn giấy tờ và cho nghỉ việc KHÔNG xóa ảnh
# ---------------------------------------------------------
def _cam_xoa(monkeypatch):
    def bao_loi(public_id):
        raise AssertionError(f"không được xóa ảnh ở luồng này: {public_id}")

    monkeypatch.setattr(luu_tru, "xoa_anh", bao_loi)


def test_gia_han_giay_to_doi_ngay_het_han_khong_xoa_anh(monkeypatch):
    _cam_xoa(monkeypatch)
    cap_nhat = []
    monkeypatch.setattr(svc.giay_to_repo, "tim_theo_nhan_su_va_loai", lambda i, loai: {"id": uuid4(), "anh_giay_to": "anh-cu"})
    monkeypatch.setattr(svc.giay_to_repo, "cap_nhat", lambda *a: cap_nhat.append(a))

    class GiayTo:
        loai, so_giay_to, hang, ngay_cap, ngay_het_han = "bang_lai", "123", "D", date(2020, 1, 1), date(2031, 1, 1)

    svc._luu_giay_to(str(uuid4()), [GiayTo()])
    assert len(cap_nhat) == 1


def test_cho_nghi_viec_khong_xoa_anh(monkeypatch):
    _cam_xoa(monkeypatch)
    ho_so = {"id": uuid4(), "ma": "TX0001", "ho_ten": "A", "chuc_danh": "tai_xe", "nguoi_dung_id": None, "ngay_vao_lam": date(2020, 1, 1),
             "trang_thai": "dang_lam", "anh_ho_so": "anh-chan-dung"}
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda i: ho_so)
    monkeypatch.setattr(svc.nhan_su_repo, "xe_thieu_nguoi_neu_nghi", lambda i: [])
    monkeypatch.setattr(svc.nhan_su_repo, "cho_nghi_viec", lambda *a: "ok")
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: None)

    class YeuCau:
        ngay_nghi = None
        ly_do = "Về quê"

    assert svc.cho_nghi_viec(str(uuid4()), QLNS, str(ho_so["id"]), YeuCau())["trang_thai"] == "da_nghi_viec"


# ---------------------------------------------------------
# luu_tru_anh_service: thư mục theo môi trường, tải / xóa / sinh link
# ---------------------------------------------------------
def _nap_lai_voi_moi_truong(monkeypatch, gia_tri):
    monkeypatch.setattr(config, "APP_ENV", gia_tri)
    return importlib.reload(luu_tru)


@pytest.fixture(autouse=False)
def khoi_phuc_luu_tru():
    yield
    importlib.reload(luu_tru)  # trả module về cấu hình thật sau test nạp lại


@pytest.mark.parametrize(
    "app_env,thu_muc",
    [("development", "development"), ("production", "production"), ("Staging Test!", "staging-test-"), ("PROD_2", "prod_2")],
)
def test_thu_muc_anh_theo_moi_truong(monkeypatch, khoi_phuc_luu_tru, app_env, thu_muc):
    m = _nap_lai_voi_moi_truong(monkeypatch, app_env)
    assert m.THU_MUC_ANH_HO_SO == f"nha_xe/{thu_muc}/nhan_su/ho_so"
    assert m.THU_MUC_ANH_GIAY_TO == f"nha_xe/{thu_muc}/nhan_su/giay_to"


def test_anh_thu_khi_phat_trien_khong_chung_thu_muc_voi_ban_trien_khai(monkeypatch, khoi_phuc_luu_tru):
    dev = _nap_lai_voi_moi_truong(monkeypatch, "development").THU_MUC_ANH_HO_SO
    prod = _nap_lai_voi_moi_truong(monkeypatch, "production").THU_MUC_ANH_HO_SO
    assert dev != prod


def test_app_env_rong_ve_development(monkeypatch, khoi_phuc_luu_tru):
    assert _nap_lai_voi_moi_truong(monkeypatch, "").THU_MUC_ANH_HO_SO == "nha_xe/development/nhan_su/ho_so"


def test_tai_anh_len_dung_kieu_authenticated_va_tra_public_id(monkeypatch):
    da_goi = {}

    def upload(du_lieu, **kw):
        da_goi.update(kw)
        return {"public_id": kw["folder"] + "/abc"}

    monkeypatch.setattr(luu_tru.cloudinary.uploader, "upload", upload)
    pid = luu_tru.tai_anh_len(JPG, luu_tru.THU_MUC_ANH_HO_SO)
    assert pid == luu_tru.THU_MUC_ANH_HO_SO + "/abc"
    assert da_goi["type"] == "authenticated" and da_goi["resource_type"] == "image" and da_goi["folder"] == luu_tru.THU_MUC_ANH_HO_SO


def test_tai_anh_len_loi_tra_none_khong_ném_loi(monkeypatch):
    def upload(*a, **kw):
        raise RuntimeError("Must supply api_key")

    monkeypatch.setattr(luu_tru.cloudinary.uploader, "upload", upload)
    assert luu_tru.tai_anh_len(JPG, luu_tru.THU_MUC_ANH_HO_SO) is None


def test_xoa_anh_ok_va_that_bai(monkeypatch):
    da_goi = {}
    monkeypatch.setattr(luu_tru.cloudinary.uploader, "destroy", lambda pid, **kw: da_goi.update(kw) or {"result": "ok"})
    assert luu_tru.xoa_anh("a/b") is True and da_goi["type"] == "authenticated"
    assert da_goi["invalidate"] is True  # xóa cả bản lưu tạm của CDN, link cũ không còn xem được
    monkeypatch.setattr(luu_tru.cloudinary.uploader, "destroy", lambda pid, **kw: {"result": "not found"})
    assert luu_tru.xoa_anh("a/b") is False

    def hong(*a, **kw):
        raise RuntimeError("mạng")

    monkeypatch.setattr(luu_tru.cloudinary.uploader, "destroy", hong)
    assert luu_tru.xoa_anh("a/b") is False


def test_lay_url_xem_ky_chu_ky_va_kieu_authenticated(monkeypatch):
    da_goi = {}
    monkeypatch.setattr(luu_tru.cloudinary.utils, "cloudinary_url", lambda pid, **kw: da_goi.update(kw) or ("https://x/" + pid, {}))
    assert luu_tru.lay_url_xem("a/b") == "https://x/a/b"
    assert da_goi["sign_url"] is True and da_goi["type"] == "authenticated"


# ---------------------------------------------------------
# Repository: đọc ảnh cũ + ghi ảnh mới nguyên tử (khóa dòng), trả ảnh cũ
# ---------------------------------------------------------
class _Cur:
    def __init__(self, kn):
        self.kn = kn

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, tham_so=None):
        if self.kn.loi:
            raise RuntimeError("hỏng")
        self.kn.lenh.append((" ".join(sql.split()), list(tham_so or [])))

    def fetchone(self):
        return self.kn.hang


class _KN:
    def __init__(self, hang=None, loi=False):
        self.hang, self.loi = hang, loi
        self.lenh = []
        self.da_commit = self.da_rollback = False

    def cursor(self):
        return _Cur(self)

    def commit(self):
        self.da_commit = True

    def rollback(self):
        self.da_rollback = True


def _ket_noi(monkeypatch, module, **kw):
    kn = _KN(**kw)
    monkeypatch.setattr(module, "get_connection", lambda: kn)
    monkeypatch.setattr(module, "release_connection", lambda c: None)
    return kn


@pytest.mark.parametrize(
    "module,ham,bang,cot",
    [
        (nhan_su_repo, nhan_su_repo.cap_nhat_anh_ho_so, "nhan_su_van_hanh", "anh_ho_so"),
        (giay_to_repo, giay_to_repo.cap_nhat_anh, "giay_to_nhan_su", "anh_giay_to"),
    ],
)
def test_repo_tra_anh_cu_dung_cau_lenh_khoa_dong_va_commit(monkeypatch, module, ham, bang, cot):
    kn = _ket_noi(monkeypatch, module, hang=("anh-cu",))
    assert ham("id-1", "anh-moi") == "anh-cu"
    sql, tham_so = kn.lenh[0]
    assert "FOR UPDATE" in sql and f"RETURNING cu.{cot}" in sql and f"UPDATE {bang}" in sql
    assert tham_so == ["id-1", "anh-moi"]  # giá trị đi qua tham số, không nối chuỗi
    assert kn.da_commit and not kn.da_rollback


@pytest.mark.parametrize(
    "module,ham",
    [(nhan_su_repo, nhan_su_repo.cap_nhat_anh_ho_so), (giay_to_repo, giay_to_repo.cap_nhat_anh)],
)
def test_repo_chua_co_anh_hoac_khong_co_dong_thi_tra_none(monkeypatch, module, ham):
    _ket_noi(monkeypatch, module, hang=(None,))
    assert ham("id-1", "anh-moi") is None
    _ket_noi(monkeypatch, module, hang=None)
    assert ham("id-khong-co", "anh-moi") is None


@pytest.mark.parametrize(
    "module,ham",
    [(nhan_su_repo, nhan_su_repo.cap_nhat_anh_ho_so), (giay_to_repo, giay_to_repo.cap_nhat_anh)],
)
def test_repo_loi_bat_ngo_thi_rollback_va_nem_lai(monkeypatch, module, ham):
    kn = _ket_noi(monkeypatch, module, loi=True)
    with pytest.raises(RuntimeError):
        ham("id-1", "anh-moi")
    assert kn.da_rollback and not kn.da_commit


def test_hang_so_kich_thuoc_dung_o_ca_route_va_util():
    from app.routes import nhan_su as route

    assert route.KICH_THUOC_TOI_DA_BYTE is kiem_tra_anh.KICH_THUOC_TOI_DA_BYTE
