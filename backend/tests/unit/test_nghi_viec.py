"""Unit test UC-51 (cho nghỉ việc) — service + schema + hàm repository có logic Python.
Repository/thông báo được giả lập, không cần DB."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.repositories import nhan_su_van_hanh_repository as repo
from app.schemas.nhan_su_schema import ChoNghiViecRequest
from app.services import ho_so_nhan_su_service as svc
from app.utils.loi import GiaTriLoi, KhongTimThay

QLNS = "quan_ly_nhan_su"
QL = "quan_ly"
HOM_NAY = datetime.now(svc.MUI_GIO_VN).date()


def _ho_so(chuc_danh="tai_xe", **kw):
    ho_so = {
        "id": uuid4(), "ma": "TX0001", "ho_ten": "Nguyen Van A", "chuc_danh": chuc_danh,
        "nguoi_dung_id": uuid4() if chuc_danh == "phu_xe" else None,
        "ngay_vao_lam": HOM_NAY - timedelta(days=30), "trang_thai": "dang_lam",
    }
    ho_so.update(kw)
    return ho_so


def _xe_thieu(bien_so="51B-111", tai_xe=True):
    return {
        "xe_id": uuid4(), "bien_so": bien_so, "thieu_tai_xe": tai_xe, "thieu_phu_xe": not tai_xe,
        "so_tai_xe_con_lai": 1, "so_phu_xe_con_lai": 0,
    }


@pytest.fixture
def gia_lap(monkeypatch):
    g = {
        "ho_so": _ho_so(), "xe_thieu": [], "xe_dang_chay": [], "ket_qua": "ok",
        "goi_nghi": [], "nk_qlns": [], "nk_admin": [], "tb": [],
    }
    monkeypatch.setattr(svc.nhan_su_repo, "tim_ho_so_day_du", lambda i: g["ho_so"])
    monkeypatch.setattr(svc.nhan_su_repo, "xe_thieu_nguoi_neu_nghi", lambda i: g["xe_thieu"])
    monkeypatch.setattr(svc.nhan_su_repo, "xe_co_chuyen_chua_xong", lambda i: g["xe_dang_chay"])
    monkeypatch.setattr(svc.nhan_su_repo, "bien_che_cua_nhan_su", lambda i: [])
    monkeypatch.setattr(svc.nhan_su_repo, "cho_nghi_viec", lambda *a: g["goi_nghi"].append(a) or g["ket_qua"])
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: g["nk_qlns"].append(a))
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: g["nk_admin"].append(a))
    monkeypatch.setattr(
        svc.nguoi_dung_repo, "danh_sach_id_theo_vai_tro",
        lambda vai_tro, chi_dang_hoat_dong=False: g.setdefault("nhan", {"quan_ly": [uuid4()], "dieu_do_vien": [uuid4(), uuid4()]})[vai_tro],
    )
    monkeypatch.setattr(svc.thong_bao, "gui", lambda nguoi_id, noi_dung: g["tb"].append((str(nguoi_id), noi_dung)))
    return g


def _yeu_cau(ly_do="Xin thôi việc", ngay=None):
    return ChoNghiViecRequest(ngay_nghi=ngay, ly_do=ly_do)


def _nghi(g, actor=QLNS, **kw):
    return svc.cho_nghi_viec(str(uuid4()), actor, str((g["ho_so"] or {"id": uuid4()})["id"]), _yeu_cau(**kw))


# ---------------------------------------------------------
# Schema
# ---------------------------------------------------------
@pytest.mark.parametrize("ly_do", ["", "   ", "x" * 501])
def test_schema_ly_do_khong_hop_le(ly_do):
    with pytest.raises(ValidationError):
        ChoNghiViecRequest(ly_do=ly_do)


def test_schema_ly_do_bi_cat_khoang_trang_va_ngay_co_the_bo_trong():
    r = ChoNghiViecRequest(ly_do="  abc  ")
    assert r.ly_do == "abc" and r.ngay_nghi is None


# ---------------------------------------------------------
# Kiểm tra đầu vào
# ---------------------------------------------------------
def test_ho_so_khong_ton_tai_la_404(gia_lap):
    gia_lap["ho_so"] = None
    with pytest.raises(KhongTimThay):
        _nghi(gia_lap)


def test_ho_so_da_nghi_viec_bi_chan_va_khong_ghi_gi(gia_lap):
    gia_lap["ho_so"]["trang_thai"] = "da_nghi_viec"
    with pytest.raises(GiaTriLoi, match="đã nghỉ việc"):
        _nghi(gia_lap)
    assert gia_lap["goi_nghi"] == [] and gia_lap["nk_qlns"] == []


def test_ngay_nghi_tuong_lai_bi_chan(gia_lap):
    with pytest.raises(GiaTriLoi, match="tương lai"):
        _nghi(gia_lap, ngay=HOM_NAY + timedelta(days=1))
    assert gia_lap["goi_nghi"] == []


def test_ngay_nghi_truoc_ngay_vao_lam_bi_chan(gia_lap):
    with pytest.raises(GiaTriLoi, match="trước ngày vào làm"):
        _nghi(gia_lap, ngay=HOM_NAY - timedelta(days=31))


def test_ngay_nghi_bang_ngay_vao_lam_hop_le(gia_lap):
    kq = _nghi(gia_lap, ngay=gia_lap["ho_so"]["ngay_vao_lam"])
    assert kq["ngay_nghi_viec"] == gia_lap["ho_so"]["ngay_vao_lam"]


def test_bo_trong_ngay_thi_lay_hom_nay(gia_lap):
    kq = _nghi(gia_lap)
    assert kq["ngay_nghi_viec"] == HOM_NAY
    assert gia_lap["goi_nghi"][0][1] == HOM_NAY


# ---------------------------------------------------------
# Kết quả từ repository (kiểm tra lại có khóa dòng)
# ---------------------------------------------------------
def test_xe_dang_chay_bi_chan_va_khong_ghi_nhat_ky_khong_thong_bao(gia_lap):
    gia_lap["ket_qua"] = "xe_dang_chay"
    gia_lap["xe_thieu"] = [_xe_thieu()]
    with pytest.raises(GiaTriLoi, match="chuyến"):
        _nghi(gia_lap)
    assert gia_lap["nk_qlns"] == [] and gia_lap["nk_admin"] == [] and gia_lap["tb"] == []


def test_repo_bao_da_nghi_viec_do_hai_nguoi_cung_luc(gia_lap):
    gia_lap["ket_qua"] = "da_nghi_viec"
    with pytest.raises(GiaTriLoi, match="đã nghỉ việc"):
        _nghi(gia_lap)
    assert gia_lap["nk_qlns"] == []


def test_repo_bao_khong_tim_thay(gia_lap):
    gia_lap["ket_qua"] = "khong_tim_thay"
    with pytest.raises(KhongTimThay):
        _nghi(gia_lap)


# ---------------------------------------------------------
# Tài khoản, nhật ký
# ---------------------------------------------------------
def test_tai_xe_khong_co_tai_khoan_nen_khong_khoa(gia_lap):
    kq = _nghi(gia_lap)
    assert kq["da_khoa_tai_khoan"] is False
    assert "khóa tài khoản" not in gia_lap["nk_qlns"][0][4]


def test_phu_xe_co_tai_khoan_duoc_bao_da_khoa(gia_lap):
    gia_lap["ho_so"] = _ho_so("phu_xe", ma="PX0001")
    kq = _nghi(gia_lap)
    assert kq["da_khoa_tai_khoan"] is True
    assert "đã khóa tài khoản" in gia_lap["nk_qlns"][0][4]


def test_nhat_ky_qlns_ghi_dung_bang_mot_dong_co_ly_do(gia_lap):
    _nghi(gia_lap, actor=QLNS, ly_do="Về quê")
    assert len(gia_lap["nk_qlns"]) == 1 and gia_lap["nk_admin"] == []
    actor_id, hanh_dong, loai, doi_tuong, ghi_chu = gia_lap["nk_qlns"][0]
    assert (hanh_dong, loai) == ("cho_nghi_viec", "nhan_su_van_hanh")
    assert doi_tuong == str(gia_lap["ho_so"]["id"]) and "Về quê" in ghi_chu


def test_nhat_ky_quan_ly_ghi_nhat_ky_admin_khong_ghi_cheo(gia_lap):
    _nghi(gia_lap, actor=QL)
    assert len(gia_lap["nk_admin"]) == 1 and gia_lap["nk_qlns"] == []
    assert gia_lap["nk_admin"][0][1] == "cho_nghi_viec"


# ---------------------------------------------------------
# Thông báo xe thiếu người
# ---------------------------------------------------------
def test_khong_thieu_xe_nao_thi_khong_thong_bao(gia_lap):
    _nghi(gia_lap)
    assert gia_lap["tb"] == []


def test_thieu_xe_bao_quan_ly_va_dieu_do_vien_moi_xe_mot_thong_bao(gia_lap):
    gia_lap["xe_thieu"] = [_xe_thieu("51B-111"), _xe_thieu("51B-222")]
    _nghi(gia_lap)
    # 1 quản lý + 2 điều độ viên = 3 người, 2 xe -> 6 thông báo
    assert len(gia_lap["tb"]) == 6
    nhan = {n for n, _ in gia_lap["tb"]}
    assert len(nhan) == 3
    assert any("51B-111" in nd for _, nd in gia_lap["tb"]) and any("51B-222" in nd for _, nd in gia_lap["tb"])
    assert all("TX0001" in nd and "tài xế" in nd for _, nd in gia_lap["tb"])


def test_thong_bao_phu_xe_thieu_phu_xe(gia_lap):
    gia_lap["ho_so"] = _ho_so("phu_xe", ma="PX0001")
    gia_lap["xe_thieu"] = [_xe_thieu(tai_xe=False)]
    _nghi(gia_lap)
    assert gia_lap["tb"] and all("Phụ xe" in nd and "thiếu phụ xe" in nd for _, nd in gia_lap["tb"])


def test_ket_qua_tra_ve_danh_sach_xe_thieu_de_giao_dien_canh_bao(gia_lap):
    gia_lap["xe_thieu"] = [_xe_thieu()]
    assert _nghi(gia_lap)["xe_thieu_nguoi"][0]["bien_so"] == "51B-111"


# ---------------------------------------------------------
# Xem trước: chỉ đọc
# ---------------------------------------------------------
def test_xem_truoc_khong_ghi_gi(gia_lap):
    gia_lap["xe_thieu"] = [_xe_thieu()]
    kq = svc.xem_truoc_nghi_viec(str(gia_lap["ho_so"]["id"]))
    assert kq["co_the_nghi"] is True and kq["se_khoa_tai_khoan"] is False
    assert gia_lap["goi_nghi"] == [] and gia_lap["nk_qlns"] == [] and gia_lap["tb"] == []


def test_xem_truoc_xe_dang_chay_thi_khong_the_nghi(gia_lap):
    gia_lap["xe_dang_chay"] = [{"xe_id": uuid4(), "bien_so": "51B-999"}]
    kq = svc.xem_truoc_nghi_viec(str(gia_lap["ho_so"]["id"]))
    assert kq["co_the_nghi"] is False and kq["xe_dang_chay"][0]["bien_so"] == "51B-999"


def test_xem_truoc_phu_xe_se_khoa_tai_khoan(gia_lap):
    gia_lap["ho_so"] = _ho_so("phu_xe")
    assert svc.xem_truoc_nghi_viec("x")["se_khoa_tai_khoan"] is True


def test_xem_truoc_ho_so_da_nghi_bi_chan(gia_lap):
    gia_lap["ho_so"]["trang_thai"] = "da_nghi_viec"
    with pytest.raises(GiaTriLoi):
        svc.xem_truoc_nghi_viec("x")


# ---------------------------------------------------------
# Repository: logic "thiếu người" (2 tài xế + 1 phụ xe) và transaction
# ---------------------------------------------------------
class _CursorHang:
    """Trả lần lượt: mỗi lần execute lấy bộ (cột, hàng) kế tiếp trong hàng đợi."""

    def __init__(self, kn):
        self.kn = kn
        self.description = []
        self._hang = []

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        return False

    def execute(self, sql, tham_so=None):
        self.kn.lenh.append((" ".join(sql.split()), tham_so))
        cot, hang = self.kn.hang_doi.pop(0) if self.kn.hang_doi else ([], [])
        self.description = [(c,) for c in cot]
        self._hang = hang

    def fetchone(self):
        return self._hang[0] if self._hang else None

    def fetchall(self):
        return list(self._hang)


class _KetNoi:
    def __init__(self, hang_doi):
        self.hang_doi = list(hang_doi)
        self.lenh = []
        self.da_commit = False
        self.da_rollback = False

    def cursor(self):
        return _CursorHang(self)

    def commit(self):
        self.da_commit = True

    def rollback(self):
        self.da_rollback = True


def _dung_ket_noi(monkeypatch, hang_doi):
    kn = _KetNoi(hang_doi)
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    return kn


_COT_THIEU = ["xe_id", "bien_so", "chuc_danh", "so_tai_xe_con_lai", "so_phu_xe_con_lai"]


@pytest.mark.parametrize(
    "chuc_danh,tai_xe,phu_xe,thieu_tx,thieu_px",
    [
        ("tai_xe", 1, 1, True, False),    # nghỉ 1 trong 2 tài xế -> còn 1 < 2
        ("tai_xe", 2, 0, False, False),   # còn đủ 2 tài xế; xe vốn thiếu phụ xe nhưng không phải lỗi của tài xế này
        ("phu_xe", 2, 0, False, True),    # phụ xe duy nhất nghỉ -> còn 0
        ("phu_xe", 2, 1, False, False),   # còn 1 phụ xe khác -> đủ
        ("phu_xe", 0, 0, False, True),    # xe vốn thiếu tài xế, chỉ báo phần phụ xe của người nghỉ
    ],
)
def test_repo_xe_thieu_nguoi_theo_chuc_danh(monkeypatch, chuc_danh, tai_xe, phu_xe, thieu_tx, thieu_px):
    xe_id = uuid4()
    _dung_ket_noi(monkeypatch, [(_COT_THIEU, [(xe_id, "51B-111", chuc_danh, tai_xe, phu_xe)])])
    kq = repo.xe_thieu_nguoi_neu_nghi("nhan-su")
    if not (thieu_tx or thieu_px):
        assert kq == []
    else:
        assert len(kq) == 1 and (kq[0]["thieu_tai_xe"], kq[0]["thieu_phu_xe"]) == (thieu_tx, thieu_px)


def test_repo_xe_thieu_nguoi_chi_xet_bien_che_co_dinh_dang_hoat_dong(monkeypatch):
    kn = _dung_ket_noi(monkeypatch, [(_COT_THIEU, [])])
    repo.xe_thieu_nguoi_neu_nghi("nhan-su")
    sql = kn.lenh[0][0]
    assert "loai = 'co_dinh'" in sql and "trang_thai = 'dang_hoat_dong'" in sql
    assert "p.trang_thai = 'dang_lam'" in sql and "u.dang_hoat_dong = true" in sql and "p.id <> n.id" in sql


def test_repo_chuyen_chua_xong_gom_dang_chay_va_gap_su_co_theo_xe_thuc_te(monkeypatch):
    kn = _dung_ket_noi(monkeypatch, [(["xe_id", "bien_so"], [])])
    repo.xe_co_chuyen_chua_xong("nhan-su")
    sql, tham_so = kn.lenh[0]
    assert "COALESCE(c.xe_thuc_te_id, c.xe_id)" in sql
    assert set(tham_so[1]) == {"dang_chay", "gap_su_co"}


def test_repo_cho_nghi_viec_khong_tim_thay(monkeypatch):
    kn = _dung_ket_noi(monkeypatch, [(["trang_thai", "nguoi_dung_id"], [])])
    assert repo.cho_nghi_viec("x", HOM_NAY, "ly do") == "khong_tim_thay"
    assert kn.da_rollback and not kn.da_commit


def test_repo_cho_nghi_viec_da_nghi_khong_ghi(monkeypatch):
    kn = _dung_ket_noi(monkeypatch, [(["a", "b"], [("da_nghi_viec", None)])])
    assert repo.cho_nghi_viec("x", HOM_NAY, "ly do") == "da_nghi_viec"
    assert kn.da_rollback and not kn.da_commit and len(kn.lenh) == 1


def test_repo_cho_nghi_viec_xe_dang_chay_khong_ghi(monkeypatch):
    kn = _dung_ket_noi(
        monkeypatch,
        [(["a", "b"], [("dang_lam", None)]), (["xe_id", "bien_so"], [(uuid4(), "51B-1")])],
    )
    assert repo.cho_nghi_viec("x", HOM_NAY, "ly do") == "xe_dang_chay"
    assert kn.da_rollback and not kn.da_commit
    assert not any(s.startswith("UPDATE") for s, _ in kn.lenh)


def test_repo_cho_nghi_viec_phu_xe_ghi_ba_viec_mot_commit_va_khong_xoa_bien_che(monkeypatch):
    kn = _dung_ket_noi(
        monkeypatch,
        [(["a", "b"], [("dang_lam", uuid4())]), (["xe_id", "bien_so"], [])],
    )
    assert repo.cho_nghi_viec("x", HOM_NAY, "ly do") == "ok"
    cau = [s for s, _ in kn.lenh]
    assert kn.da_commit and not kn.da_rollback
    assert "FOR UPDATE" in cau[0]
    assert any(s.startswith("UPDATE nhan_su_van_hanh SET trang_thai = 'da_nghi_viec'") for s in cau)
    assert any(s.startswith("UPDATE nguoi_dung SET dang_hoat_dong = false") for s in cau)
    assert any("UPDATE xe_nhan_su SET trang_thai = 'tam_nghi'" in s for s in cau)
    assert not any("DELETE" in s for s in cau)


def test_repo_cho_nghi_viec_tai_xe_khong_dong_toi_nguoi_dung(monkeypatch):
    kn = _dung_ket_noi(monkeypatch, [(["a", "b"], [("dang_lam", None)]), (["xe_id", "bien_so"], [])])
    assert repo.cho_nghi_viec("x", HOM_NAY, "ly do") == "ok"
    assert not any("nguoi_dung SET" in s for s, _ in kn.lenh)
