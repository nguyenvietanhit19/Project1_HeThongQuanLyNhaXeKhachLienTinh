"""Unit test nhánh "Đổi văn phòng của cán bộ" (UC-36) — service + schema + hàm repository. Không cần DB."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.repositories import tai_khoan_can_bo_repository as repo
from app.schemas.tai_khoan_can_bo_schema import DoiVanPhongRequest
from app.services import nhat_ky_service
from app.services import tai_khoan_can_bo_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

QLNS = "quan_ly_nhan_su"
QL = "quan_ly"
VP_CU, VP_MOI = uuid4(), uuid4()


def _tk(vai_tro="nhan_vien_gui_hang", **kw):
    d = {"id": uuid4(), "ma": "GH0001", "email": "a@t.vn", "ho_ten": "Nhân Viên", "vai_tro": vai_tro, "dang_hoat_dong": True, "la_tai_khoan_goc": False}
    d.update(kw)
    return d


def _vp(id_, ten, loai="van_phong"):
    return {"id": id_, "ten": ten, "loai": loai}


@pytest.fixture
def gia_lap(monkeypatch):
    g = {
        "tk": _tk(), "ket_qua": ("ok", VP_CU), "goi": [], "nk_qlns": [], "nk_admin": [],
        "diem": {str(VP_CU): _vp(VP_CU, "Văn phòng Cũ"), str(VP_MOI): _vp(VP_MOI, "Văn phòng Mới")},
    }
    monkeypatch.setattr(svc.repo, "tim_tai_khoan", lambda i: g["tk"])
    monkeypatch.setattr(svc.dia_diem_repo, "tim_diem_don_tra_theo_id", lambda i: g["diem"].get(str(i)))
    monkeypatch.setattr(svc.repo, "doi_van_phong", lambda *a: g["goi"].append(a) or g["ket_qua"])
    monkeypatch.setattr(svc.nhat_ky_repo, "ghi", lambda *a: g["nk_qlns"].append(a))
    monkeypatch.setattr(svc.nhat_ky_admin_repo, "ghi", lambda *a: g["nk_admin"].append(a))
    return g


def _doi(actor=QLNS, ly_do="Điều chuyển theo nhu cầu", van_phong=None, muc_tieu=None):
    return svc.doi_van_phong(str(uuid4()), actor, muc_tieu or str(uuid4()), str(van_phong or VP_MOI), ly_do)


# ---------------------------------------------------------
# Quyền, đối tượng
# ---------------------------------------------------------
@pytest.mark.parametrize("vai_tro", ["nhan_vien_quay_ve", "nhan_vien_gui_hang"])
def test_qlns_doi_duoc_van_phong_quay_ve_va_gui_hang(gia_lap, vai_tro):
    gia_lap["tk"] = _tk(vai_tro)
    kq = _doi(QLNS)
    assert kq["ten_van_phong_cu"] == "Văn phòng Cũ" and kq["ten_van_phong_moi"] == "Văn phòng Mới"
    assert len(gia_lap["goi"]) == 1


# Từ 6/11/2026 quan_ly cũng KHÔNG còn đổi văn phòng — chỉ quan_ly_nhan_su.
@pytest.mark.parametrize("actor", ["quan_ly", "khach_hang", "phu_xe", "ke_toan", "dieu_do_vien", "nhan_vien_quay_ve", "nhan_vien_gui_hang", ""])
def test_vai_tro_khac_khong_duoc_doi_van_phong(gia_lap, actor):
    with pytest.raises(CamTruyCap):
        _doi(actor)
    assert gia_lap["goi"] == []


@pytest.mark.parametrize("vai_tro", ["phu_xe", "dieu_do_vien", "ke_toan", "quan_ly", "quan_ly_nhan_su", "khach_hang"])
def test_vai_tro_khong_gan_van_phong_bi_chan(gia_lap, vai_tro):
    gia_lap["tk"] = _tk(vai_tro)
    with pytest.raises(GiaTriLoi, match="không gắn văn phòng"):
        _doi()
    assert gia_lap["goi"] == [] and gia_lap["nk_qlns"] == [] and gia_lap["nk_admin"] == []


def test_tai_khoan_khong_ton_tai_la_404(gia_lap):
    gia_lap["tk"] = None
    with pytest.raises(KhongTimThay):
        _doi()


# ---------------------------------------------------------
# Lý do (bắt buộc, tối đa 200 từ)
# ---------------------------------------------------------
@pytest.mark.parametrize("ly_do", ["", "   ", "\n\t "])
def test_ly_do_trong_bi_chan_o_schema_va_service(gia_lap, ly_do):
    with pytest.raises(ValidationError):
        DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do=ly_do)
    with pytest.raises(GiaTriLoi):
        _doi(ly_do=ly_do)
    assert gia_lap["goi"] == []


def test_ly_do_dung_200_tu_hop_le_201_tu_bi_chan(gia_lap):
    hop_le = " ".join(["tu"] * 200)
    assert DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do=hop_le).ly_do == hop_le
    _doi(ly_do=hop_le)
    qua_dai = " ".join(["tu"] * 201)
    with pytest.raises(ValidationError, match="200 từ"):
        DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do=qua_dai)
    with pytest.raises(GiaTriLoi, match="200 từ"):
        _doi(ly_do=qua_dai)


def test_dem_tu_theo_khoang_trang_ke_ca_xuong_dong_va_khoang_cach_thua(gia_lap):
    assert len((" a  b\n c\t").split()) == 3
    nhieu_cach = ("tu " * 200).strip().replace(" ", "   ")
    assert DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do=nhieu_cach).ly_do.count("tu") == 200


def test_mot_tu_qua_dai_bi_chan_boi_gioi_han_ky_tu(gia_lap):
    with pytest.raises(ValidationError, match="2000 ký tự"):
        DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do="x" * 2001)
    assert DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do="x" * 2000)


def test_ly_do_bi_cat_khoang_trang_hai_dau(gia_lap):
    assert DoiVanPhongRequest(van_phong_id=VP_MOI, ly_do="  chuyển công tác  ").ly_do == "chuyển công tác"
    _doi(ly_do="   chuyển công tác   ")
    assert gia_lap["nk_qlns"][0][4].endswith(": chuyển công tác")


# ---------------------------------------------------------
# Văn phòng mới, trùng, hết người
# ---------------------------------------------------------
def test_van_phong_moi_khong_ton_tai_bi_chan(gia_lap):
    with pytest.raises(GiaTriLoi, match="văn phòng hợp lệ"):
        _doi(van_phong=uuid4())
    assert gia_lap["goi"] == []


def test_diem_duoc_chon_khong_phai_van_phong_bi_chan(gia_lap):
    khac = uuid4()
    gia_lap["diem"][str(khac)] = _vp(khac, "Bến xe", loai="ben_xe")
    with pytest.raises(GiaTriLoi, match="văn phòng hợp lệ"):
        _doi(van_phong=khac)
    assert gia_lap["goi"] == []


def test_trung_van_phong_hien_tai_bi_chan_khong_ghi_nhat_ky(gia_lap):
    gia_lap["ket_qua"] = ("trung_van_phong", VP_CU)
    with pytest.raises(GiaTriLoi, match="đang ở văn phòng này"):
        _doi()
    assert gia_lap["nk_qlns"] == [] and gia_lap["nk_admin"] == []


def test_van_phong_cu_het_nguoi_bi_chan_neu_ten_van_phong_va_khong_ghi_nhat_ky(gia_lap):
    gia_lap["ket_qua"] = ("het_nguoi", VP_CU)
    with pytest.raises(GiaTriLoi, match=r"Văn phòng Cũ.*chỉ còn mình người này.*cùng chức vụ"):
        _doi()
    assert gia_lap["nk_qlns"] == [] and gia_lap["nk_admin"] == []


def test_repo_bao_khong_tim_thay_do_bi_xoa_giua_chung(gia_lap):
    gia_lap["ket_qua"] = ("khong_tim_thay", None)
    with pytest.raises(KhongTimThay):
        _doi()


def test_gan_lan_dau_khong_co_van_phong_cu(gia_lap):
    gia_lap["ket_qua"] = ("ok", None)
    kq = _doi()
    assert kq["van_phong_cu_id"] is None and kq["ten_van_phong_cu"] is None
    assert "(chưa có)" in gia_lap["nk_qlns"][0][4]


def test_khong_chan_khi_con_don_dang_xu_ly_service_khong_tra_cuu_don_nao(gia_lap):
    # Quy tắc chốt 6/11/2026: không kiểm tra đơn đang xử lý; service chỉ gọi đúng các hàm đã giả lập, không có hàm đếm đơn.
    assert not hasattr(svc, "dem_don_dang_xu_ly") and not hasattr(svc.repo, "dem_don_dang_xu_ly")
    assert _doi()["ten_van_phong_moi"] == "Văn phòng Mới"


# ---------------------------------------------------------
# Nhật ký
# ---------------------------------------------------------
def test_nhat_ky_qlns_ghi_bang_rieng_mot_dong_co_ten_cu_moi_va_ly_do(gia_lap):
    muc_tieu = _tk()
    gia_lap["tk"] = muc_tieu
    _doi(QLNS, ly_do="Điều chuyển về Thủ Đức")
    assert len(gia_lap["nk_qlns"]) == 1 and gia_lap["nk_admin"] == []
    _, hanh_dong, loai, doi_tuong, ghi_chu = gia_lap["nk_qlns"][0]
    assert (hanh_dong, loai, doi_tuong) == ("doi_van_phong", "nguoi_dung", str(muc_tieu["id"]))
    assert ghi_chu == "Đổi văn phòng Văn phòng Cũ → Văn phòng Mới: Điều chuyển về Thủ Đức"


def test_quan_ly_doi_van_phong_bi_chan_khong_ghi_nhat_ky_nao(gia_lap):
    with pytest.raises(CamTruyCap, match="Không đủ quyền"):
        _doi(QL)
    assert gia_lap["goi"] == [] and gia_lap["nk_admin"] == [] and gia_lap["nk_qlns"] == []


def test_nhan_hanh_dong_hien_thi_o_man_nhat_ky_uc52():
    assert nhat_ky_service.NHAN_HANH_DONG["doi_van_phong"] == "Đổi văn phòng"


def test_gia_tri_hanh_dong_khop_voi_check_cua_migration():
    import pathlib

    sql = (pathlib.Path(__file__).resolve().parents[2] / "migrations" / "20261106_0900_nhat_ky_qlns_them_doi_van_phong.sql").read_text(encoding="utf-8")
    for hd in nhat_ky_service.NHAN_HANH_DONG:
        assert f"'{hd}'" in sql


# ---------------------------------------------------------
# Repository (kết nối giả; mỗi execute lấy kết quả kế tiếp trong hàng đợi)
# ---------------------------------------------------------
class _Cur:
    def __init__(self, kn):
        self.kn = kn
        self._ket_qua = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, tham_so=None):
        self.kn.lenh.append((" ".join(sql.split()), list(tham_so or [])))
        self._ket_qua = self.kn.hang_doi.pop(0) if self.kn.hang_doi else None

    def fetchone(self):
        return self._ket_qua


class _KN:
    def __init__(self, hang_doi):
        self.hang_doi = list(hang_doi)
        self.lenh = []
        self.da_commit = False
        self.da_rollback = False

    def cursor(self):
        return _Cur(self)

    def commit(self):
        self.da_commit = True

    def rollback(self):
        self.da_rollback = True


def _ket_noi(monkeypatch, hang_doi):
    kn = _KN(hang_doi)
    monkeypatch.setattr(repo, "get_connection", lambda: kn)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    return kn


def _cau(kn):
    return [s for s, _ in kn.lenh]


def test_repo_khong_tim_thay(monkeypatch):
    kn = _ket_noi(monkeypatch, [None])
    assert repo.doi_van_phong("x", str(VP_MOI)) == ("khong_tim_thay", None)
    assert kn.da_rollback and not kn.da_commit


def test_repo_trung_van_phong_khong_ghi(monkeypatch):
    kn = _ket_noi(monkeypatch, [("nhan_vien_gui_hang", True, VP_MOI)])
    assert repo.doi_van_phong("x", str(VP_MOI)) == ("trung_van_phong", VP_MOI)
    assert kn.da_rollback and not kn.da_commit and len(kn.lenh) == 1


def test_repo_het_nguoi_khoa_van_phong_cu_dem_dung_dieu_kien_va_khong_ghi(monkeypatch):
    kn = _ket_noi(monkeypatch, [("nhan_vien_gui_hang", True, VP_CU), (VP_CU,), (0,)])
    assert repo.doi_van_phong("nguoi-chuyen", str(VP_MOI)) == ("het_nguoi", VP_CU)
    cau = _cau(kn)
    assert "FOR UPDATE OF nd" in cau[0]
    assert "FROM diem_don_tra WHERE id = %s FOR UPDATE" in cau[1]
    assert "u.vai_tro = %s" in cau[2] and "u.dang_hoat_dong = true" in cau[2] and "u.id <> %s" in cau[2]
    assert kn.lenh[2][1] == [VP_CU, "nhan_vien_gui_hang", "nguoi-chuyen"]
    assert kn.da_rollback and not kn.da_commit and not any(s.startswith("INSERT") for s in cau)


def test_repo_con_dong_nghiep_thi_ghi_va_commit(monkeypatch):
    kn = _ket_noi(monkeypatch, [("nhan_vien_quay_ve", True, VP_CU), (VP_CU,), (1,)])
    assert repo.doi_van_phong("x", str(VP_MOI)) == ("ok", VP_CU)
    cau = _cau(kn)
    assert kn.da_commit and not kn.da_rollback
    assert cau[-1].startswith("INSERT INTO ho_so_can_bo_diem") and "ON CONFLICT (nguoi_dung_id) DO UPDATE" in cau[-1]
    assert kn.lenh[-1][1] == ["x", str(VP_MOI)]


def test_repo_gan_lan_dau_khong_khoa_khong_dem(monkeypatch):
    kn = _ket_noi(monkeypatch, [("nhan_vien_gui_hang", True, None)])
    assert repo.doi_van_phong("x", str(VP_MOI)) == ("ok", None)
    assert len(kn.lenh) == 2 and kn.lenh[1][0].startswith("INSERT") and kn.da_commit


def test_repo_nguoi_chuyen_dang_bi_khoa_thi_khong_ap_dung_quy_tac_dem(monkeypatch):
    kn = _ket_noi(monkeypatch, [("nhan_vien_gui_hang", False, VP_CU)])
    assert repo.doi_van_phong("x", str(VP_MOI)) == ("ok", VP_CU)
    assert len(kn.lenh) == 2 and not any("count(*)" in s for s in _cau(kn)) and kn.da_commit


def test_repo_loi_bat_ngo_thi_rollback_va_nem_lai(monkeypatch):
    class _Loi(_Cur):
        def execute(self, sql, tham_so=None):
            raise RuntimeError("hỏng")

    kn = _ket_noi(monkeypatch, [])
    kn.cursor = lambda: _Loi(kn)
    with pytest.raises(RuntimeError):
        repo.doi_van_phong("x", str(VP_MOI))
    assert kn.da_rollback and not kn.da_commit


def test_repo_khong_phu_thuoc_ham_cua_phan_gui_hang():
    # Repository này không import nguoi_dung_repository (nơi có gan_van_phong của phần gửi hàng).
    assert not hasattr(repo, "nguoi_dung_repository") and not hasattr(repo, "gan_van_phong")
