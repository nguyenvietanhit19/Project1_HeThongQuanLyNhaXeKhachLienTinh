"""Unit test UC-52 (xem nhật ký thao tác) — service + hàm repository dựng SQL. Không cần DB."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.repositories import nhat_ky_doc_repository as repo
from app.schemas.nhat_ky_schema import NhatKyTrangResponse, TuyChonLocResponse
from app.services import nhat_ky_service as svc
from app.utils.loi import CamTruyCap, GiaTriLoi

QLNS = "quan_ly_nhan_su"
QL = "quan_ly"
VN = svc.MUI_GIO_VN


def _dong(**kw):
    d = {
        "id": uuid4(), "nguon": "quan_ly_nhan_su", "nguoi_id": uuid4(), "ten_nguoi": "Hoàng Nghĩa", "ma_nguoi": "NS0001",
        "vai_tro_nguoi": "quan_ly_nhan_su", "hanh_dong": "khoa_tai_khoan", "doi_tuong_loai": "nguoi_dung",
        "doi_tuong_id": uuid4(), "ten_doi_tuong": "Trần Bình", "ma_doi_tuong": "PX0001", "ghi_chu": "lý do",
        "thoi_gian": datetime(2026, 11, 5, 10, 0, tzinfo=VN),
    }
    d.update(kw)
    return d


@pytest.fixture
def gia_lap(monkeypatch):
    g = {"goi": [], "dong": [_dong()], "tong": 1, "loc": {"hanh_dong": ["khoa_tai_khoan", "ham_la"], "doi_tuong_loai": ["nguoi_dung", "tuyen"]}, "nguoi": []}

    def tim(gioi_han, **kw):
        g["goi"].append({"gioi_han": gioi_han, **kw})
        return g["dong"], g["tong"]

    monkeypatch.setattr(repo, "tim", tim)
    monkeypatch.setattr(repo, "cac_gia_tri_loc", lambda gioi_han: g.setdefault("loc_goi", []).append(gioi_han) or g["loc"])
    monkeypatch.setattr(repo, "danh_sach_nguoi_thuc_hien", lambda: g["nguoi"])
    return g


def _xem(actor_vai_tro=QLNS, actor_id=None, **kw):
    return svc.xem_nhat_ky(actor_id or str(uuid4()), actor_vai_tro, **kw)


# ---------------------------------------------------------
# Phạm vi theo vai trò (quyết định 14)
# ---------------------------------------------------------
def test_qlns_bi_ep_ve_dong_cua_chinh_minh(gia_lap):
    me = str(uuid4())
    _xem(QLNS, me)
    assert gia_lap["goi"][0]["gioi_han"] == me


def test_qlns_gui_nguoi_id_nguoi_khac_van_bi_bo_qua(gia_lap):
    me, khac = str(uuid4()), str(uuid4())
    _xem(QLNS, me, nguoi_id=khac)
    assert gia_lap["goi"][0]["gioi_han"] == me and gia_lap["goi"][0]["nguoi_id"] is None


def test_quan_ly_xem_toan_bo_khong_gioi_han(gia_lap):
    _xem(QL)
    assert gia_lap["goi"][0]["gioi_han"] is None


def test_quan_ly_loc_duoc_theo_nguoi(gia_lap):
    nguoi = str(uuid4())
    _xem(QL, nguoi_id=nguoi)
    assert gia_lap["goi"][0]["nguoi_id"] == nguoi


@pytest.mark.parametrize("vai_tro", ["khach_hang", "phu_xe", "ke_toan", "dieu_do_vien", "nhan_vien_quay_ve", "tai_xe", ""])
def test_vai_tro_khac_bi_chan(gia_lap, vai_tro):
    with pytest.raises(CamTruyCap):
        _xem(vai_tro)
    with pytest.raises(CamTruyCap):
        svc.tuy_chon_loc(str(uuid4()), vai_tro)
    assert gia_lap["goi"] == []


# ---------------------------------------------------------
# Ngày lọc (giờ VN)
# ---------------------------------------------------------
def test_khong_co_ngay_thi_khong_loc_thoi_gian(gia_lap):
    _xem()
    assert gia_lap["goi"][0]["tu"] is None and gia_lap["goi"][0]["den"] is None


def test_ngay_loc_la_gio_vn_nua_mo_den_dau_ngay_ke_tiep(gia_lap):
    _xem(tu_ngay=date(2026, 11, 5), den_ngay=date(2026, 11, 5))
    g = gia_lap["goi"][0]
    assert g["tu"] == datetime(2026, 11, 5, 0, 0, tzinfo=VN)
    assert g["den"] == datetime(2026, 11, 6, 0, 0, tzinfo=VN)
    assert g["tu"].utcoffset() == timedelta(hours=7)


def test_chi_co_tu_ngay_hoac_chi_den_ngay(gia_lap):
    _xem(tu_ngay=date(2026, 11, 1))
    assert gia_lap["goi"][0]["tu"] is not None and gia_lap["goi"][0]["den"] is None
    _xem(den_ngay=date(2026, 11, 30))
    assert gia_lap["goi"][1]["tu"] is None and gia_lap["goi"][1]["den"] == datetime(2026, 12, 1, 0, 0, tzinfo=VN)


def test_den_ngay_cuoi_thang_sang_thang_sau(gia_lap):
    _xem(den_ngay=date(2026, 12, 31))
    assert gia_lap["goi"][0]["den"] == datetime(2027, 1, 1, 0, 0, tzinfo=VN)


def test_tu_ngay_sau_den_ngay_bi_chan(gia_lap):
    with pytest.raises(GiaTriLoi, match="Từ ngày"):
        _xem(tu_ngay=date(2026, 11, 6), den_ngay=date(2026, 11, 5))
    assert gia_lap["goi"] == []


# ---------------------------------------------------------
# Bộ lọc và phân trang
# ---------------------------------------------------------
def test_loc_hanh_dong_doi_tuong_duoc_cat_khoang_trang_chuoi_rong_thanh_none(gia_lap):
    _xem(hanh_dong="  khoa_tai_khoan ", doi_tuong_loai="   ")
    g = gia_lap["goi"][0]
    assert g["hanh_dong"] == "khoa_tai_khoan" and g["doi_tuong_loai"] is None


def test_mac_dinh_trang_1_50_dong(gia_lap):
    kq = _xem()
    g = gia_lap["goi"][0]
    assert (g["trang"], g["so_dong"]) == (1, 50) and (kq["trang"], kq["so_dong"]) == (1, 50)


@pytest.mark.parametrize("so_dong", [0, -1, 201, 1000])
def test_so_dong_ngoai_khoang_bi_chan(gia_lap, so_dong):
    with pytest.raises(GiaTriLoi):
        _xem(so_dong=so_dong)


@pytest.mark.parametrize("so_dong", [1, 50, 200])
def test_so_dong_hop_le_o_bien(gia_lap, so_dong):
    assert _xem(so_dong=so_dong)["so_dong"] == so_dong


@pytest.mark.parametrize("trang", [0, -3])
def test_trang_nho_hon_1_bi_chan(gia_lap, trang):
    with pytest.raises(GiaTriLoi):
        _xem(trang=trang)


@pytest.mark.parametrize("tong,so_dong,so_trang", [(0, 50, 0), (1, 50, 1), (50, 50, 1), (51, 50, 2), (401, 200, 3)])
def test_so_trang_lam_tron_len(gia_lap, tong, so_dong, so_trang):
    gia_lap["tong"] = tong
    assert _xem(so_dong=so_dong)["so_trang"] == so_trang


def test_trang_chuyen_den_repository(gia_lap):
    _xem(trang=3, so_dong=20)
    assert (gia_lap["goi"][0]["trang"], gia_lap["goi"][0]["so_dong"]) == (3, 20)


# ---------------------------------------------------------
# Nhãn + hiển thị đối tượng
# ---------------------------------------------------------
@pytest.mark.parametrize("hanh_dong,nhan", list(svc.NHAN_HANH_DONG.items()))
def test_nhan_tieng_viet_cho_6_hanh_dong(gia_lap, hanh_dong, nhan):
    gia_lap["dong"] = [_dong(hanh_dong=hanh_dong)]
    assert _xem()["items"][0]["nhan_hanh_dong"] == nhan


def test_hanh_dong_la_hien_nguyen_gia_tri_tho(gia_lap):
    gia_lap["dong"] = [_dong(hanh_dong="sua_gia_ve", nguon="admin")]
    assert _xem(QL)["items"][0]["nhan_hanh_dong"] == "sua_gia_ve"


def test_doi_tuong_tra_duoc_ten_hien_ho_ten_va_ma(gia_lap):
    assert _xem()["items"][0]["doi_tuong_hien_thi"] == "Trần Bình (PX0001)"


def test_doi_tuong_co_ten_nhung_khong_co_ma(gia_lap):
    gia_lap["dong"] = [_dong(ma_doi_tuong=None)]
    assert _xem()["items"][0]["doi_tuong_hien_thi"] == "Trần Bình"


def test_doi_tuong_la_nhom_khac_ghi_hien_loai_va_8_ky_tu_dau_cua_id(gia_lap):
    doi_tuong_id = uuid4()
    gia_lap["dong"] = [_dong(doi_tuong_loai="tuyen", doi_tuong_id=doi_tuong_id, ten_doi_tuong=None, ma_doi_tuong=None, nguon="admin")]
    assert _xem(QL)["items"][0]["doi_tuong_hien_thi"] == f"tuyen {str(doi_tuong_id)[:8]}"


def test_doi_tuong_nguoi_dung_da_bi_xoa_van_khong_loi(gia_lap):
    doi_tuong_id = uuid4()
    gia_lap["dong"] = [_dong(ten_doi_tuong=None, ma_doi_tuong=None, doi_tuong_id=doi_tuong_id)]
    assert _xem()["items"][0]["doi_tuong_hien_thi"] == f"Tài khoản {str(doi_tuong_id)[:8]}"


def test_ket_qua_hop_le_voi_schema_response(gia_lap):
    gia_lap["tong"] = 1
    NhatKyTrangResponse(**_xem())
    gia_lap["dong"] = [_dong(ghi_chu=None, ma_nguoi=None)]
    NhatKyTrangResponse(**_xem())


def test_khong_co_dong_nao_tra_danh_sach_rong(gia_lap):
    gia_lap["dong"], gia_lap["tong"] = [], 0
    kq = _xem()
    assert kq["items"] == [] and kq["tong"] == 0 and kq["so_trang"] == 0


# ---------------------------------------------------------
# Tùy chọn lọc
# ---------------------------------------------------------
def test_tuy_chon_loc_qlns_khong_co_nguoi_thuc_hien_va_loc_theo_chinh_minh(gia_lap):
    me = str(uuid4())
    kq = svc.tuy_chon_loc(me, QLNS)
    assert kq["nguoi_thuc_hien"] == [] and gia_lap["loc_goi"] == [me]
    TuyChonLocResponse(**kq)


def test_tuy_chon_loc_quan_ly_co_danh_sach_nguoi(gia_lap):
    gia_lap["nguoi"] = [{"id": uuid4(), "ho_ten": "A", "ma": "QL0000", "vai_tro": "quan_ly"}]
    kq = svc.tuy_chon_loc(str(uuid4()), QL)
    assert len(kq["nguoi_thuc_hien"]) == 1 and gia_lap["loc_goi"] == [None]
    TuyChonLocResponse(**kq)


def test_tuy_chon_loc_co_nhan_va_hanh_dong_la_giu_nguyen(gia_lap):
    kq = svc.tuy_chon_loc(str(uuid4()), QL)
    assert {"gia_tri": "khoa_tai_khoan", "nhan": "Khóa tài khoản"} in kq["hanh_dong"]
    assert {"gia_tri": "ham_la", "nhan": "ham_la"} in kq["hanh_dong"]
    assert {"gia_tri": "tuyen", "nhan": "tuyen"} in kq["doi_tuong_loai"]


# ---------------------------------------------------------
# Repository: SQL dựng ra (kết nối giả, ghi lại câu lệnh)
# ---------------------------------------------------------
class _Cur:
    def __init__(self, kn):
        self.kn = kn
        self.description = [("x",)]
        self._hang = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, tham_so=None):
        self.kn.lenh.append((" ".join(sql.split()), list(tham_so or [])))
        self._hang = [(0,)] if "count(*)" in sql else []

    def fetchone(self):
        return self._hang[0]

    def fetchall(self):
        return []


class _KN:
    def __init__(self):
        self.lenh = []

    def cursor(self):
        return _Cur(self)


@pytest.fixture
def kn(monkeypatch):
    k = _KN()
    monkeypatch.setattr(repo, "get_connection", lambda: k)
    monkeypatch.setattr(repo, "release_connection", lambda c: None)
    return k


def test_repo_qlns_chi_doc_bang_cua_qlns_khong_cham_nhat_ky_admin(kn):
    me = str(uuid4())
    repo.tim(me)
    for sql, tham_so in kn.lenh:
        assert "nhat_ky_admin" not in sql and "UNION" not in sql
        assert "WHERE quan_ly_nhan_su_id = %s" in sql
        assert tham_so[0] == me


def test_repo_quan_ly_gop_ca_hai_bang(kn):
    repo.tim(None)
    for sql, _ in kn.lenh:
        assert "nhat_ky_quan_ly_nhan_su" in sql and "nhat_ky_admin" in sql and "UNION ALL" in sql


def test_repo_sap_xep_moi_nhat_truoc_va_phan_trang_bang_tham_so(kn):
    repo.tim(None, trang=3, so_dong=20)
    sql, tham_so = kn.lenh[1]
    assert "ORDER BY nk.thoi_gian DESC" in sql and "LIMIT %s OFFSET %s" in sql
    assert tham_so[-2:] == [20, 40]


def test_repo_bo_loc_di_qua_tham_so_khong_noi_chuoi(kn):
    ma_doc = "x'; DROP TABLE nguoi_dung; --"
    tu, den = datetime(2026, 11, 1, tzinfo=VN), datetime(2026, 11, 2, tzinfo=VN)
    nguoi = str(uuid4())
    repo.tim(None, tu=tu, den=den, hanh_dong=ma_doc, doi_tuong_loai="nguoi_dung", nguoi_id=nguoi)
    for sql, tham_so in kn.lenh:
        assert ma_doc not in sql and "DROP" not in sql
        for dk in ("nk.thoi_gian >= %s", "nk.thoi_gian < %s", "nk.hanh_dong = %s", "nk.doi_tuong_loai = %s", "nk.nguoi_id = %s"):
            assert dk in sql
        assert ma_doc in tham_so and tu in tham_so and den in tham_so and nguoi in tham_so


def test_repo_khong_bo_loc_thi_khong_co_where_cua_bo_loc(kn):
    repo.tim(None)
    for sql, tham_so in kn.lenh[:2]:
        assert "%s" not in sql.split("LIMIT")[0].split("UNION ALL")[-1].split("FROM nhat_ky_admin")[-1]
        assert "nk.hanh_dong = %s" not in sql and "nk.thoi_gian >= %s" not in sql and "nk.nguoi_id = %s" not in sql


def test_repo_tra_cuu_ten_nguoi_va_doi_tuong_theo_loai_va_ma_phu_xe_lay_cua_tai_khoan(kn):
    repo.tim(None)
    sql = kn.lenh[1][0]
    assert "JOIN nguoi_dung u ON u.id = nk.nguoi_id" in sql
    assert "COALESCE(ns.ma, nsnd.ma)" in sql
    assert "nk.doi_tuong_loai = 'nguoi_dung' AND dn.id" in sql and "nk.doi_tuong_loai = 'nhan_su_van_hanh' AND ns.id" in sql


def test_repo_chi_doc_khong_co_lenh_ghi(kn):
    repo.tim(None)
    repo.tim(str(uuid4()))
    repo.danh_sach_nguoi_thuc_hien()
    repo.cac_gia_tri_loc(None)
    repo.cac_gia_tri_loc(str(uuid4()))
    for sql, _ in kn.lenh:
        assert not any(t in sql.upper().split() for t in ("INSERT", "UPDATE", "DELETE"))
