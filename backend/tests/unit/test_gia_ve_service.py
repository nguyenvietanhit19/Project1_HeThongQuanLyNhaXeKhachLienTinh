"""Unit test đổi giá vé (UC-33): khóa sửa/xóa giá đã áp dụng khi tuyến có vé, giá mới mặc định từ ngày mai và tự đóng giá
cũ, cảnh báo giá bất thường — giả lập repository bằng monkeypatch, không cần DB."""

import datetime

import pytest

from app.services import gia_ve_service as gv
from app.utils.loi import GiaTriLoi

HOM_NAY = datetime.date(2026, 10, 15)
NGAY_MAI = HOM_NAY + datetime.timedelta(days=1)
HOM_QUA = HOM_NAY - datetime.timedelta(days=1)
A, B, C = "A", "B", "C"  # 3 khu vực của tuyến, đi theo thứ tự A → B → C


def dong(id_, di, den, gia, tu=None, den_ngay=None):
    return {"id": id_, "tuyen_id": "t1", "diem_di_id": di, "diem_den_id": den, "gia_goc": gia, "ap_dung_tu": tu, "ap_dung_den": den_ngay}


@pytest.fixture
def moi_truong(monkeypatch):
    """Dict điều khiển: dong (danh sách giá), so_chuyen (số chuyến đã sinh trong khoảng giá); ghi lại các lần ghi DB."""
    tt = {"dong": [], "so_chuyen": 0, "da_tao": [], "da_sua": [], "da_xoa": []}
    monkeypatch.setattr(gv, "hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(gv.dia_diem_repo, "tim_tuyen_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(
        gv.dia_diem_repo, "danh_sach_diem_theo_tuyen",
        lambda _id: [{"khu_vuc_id": k, "ten_khu_vuc": f"KV-{k}", "thu_tu": i} for i, k in enumerate([A, B, C], 1)],
    )
    monkeypatch.setattr(gv.repo, "danh_sach_gia_ve", lambda tuyen_id=None: [dict(d) for d in tt["dong"]])
    monkeypatch.setattr(gv.repo, "tim_gia_ve_theo_id", lambda id_: next((dict(d) for d in tt["dong"] if d["id"] == id_), None))
    monkeypatch.setattr(
        gv.repo, "danh_sach_gia_ve_theo_cap_diem",
        lambda t, di, den: [dict(d) for d in tt["dong"] if d["diem_di_id"] == di and d["diem_den_id"] == den],
    )
    monkeypatch.setattr(gv.repo, "so_chuyen_trong_khoang", lambda tuyen_id, tu, den: tt["so_chuyen"])
    monkeypatch.setattr(gv.repo, "tao_gia_ve_va_dong_gia_cu", lambda *a: tt["da_tao"].append(a) or {"id": "moi"})
    monkeypatch.setattr(gv.repo, "sua_gia_ve", lambda *a: tt["da_sua"].append(a))
    monkeypatch.setattr(gv.repo, "xoa_gia_ve", lambda id_: tt["da_xoa"].append(id_))
    return tt


# ---------- giá mới: mặc định ngày mai, tự đóng giá cũ ----------
def test_tao_gia_moi_bo_trong_ngay_bat_dau_thi_mac_dinh_ngay_mai(moi_truong):
    gv.tao_gia_ve("t1", A, B, 300_000, None, None)
    assert moi_truong["da_tao"][0][4] == NGAY_MAI


def test_tao_gia_bat_dau_trong_qua_khu_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        gv.tao_gia_ve("t1", A, B, 300_000, HOM_QUA, None)


def test_tao_gia_moi_tu_dong_dong_gia_cu_o_ngay_lien_truoc(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]  # vô thời hạn, đã áp dụng
    gv.tao_gia_ve("t1", A, B, 400_000, NGAY_MAI + datetime.timedelta(days=4), None)
    *_, gia_cu_id, ngay_dong = moi_truong["da_tao"][0]
    assert gia_cu_id == "cu" and ngay_dong == NGAY_MAI + datetime.timedelta(days=3)


def test_tao_gia_moi_khong_co_gia_cu_thi_khong_dong_gi(moi_truong):
    gv.tao_gia_ve("t1", A, B, 300_000, None, None)
    *_, gia_cu_id, ngay_dong = moi_truong["da_tao"][0]
    assert gia_cu_id is None and ngay_dong is None


def test_tao_gia_bat_dau_hom_nay_khi_gia_da_co_chuyen_va_gia_cu_dang_ap_dung_bi_chan(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    moi_truong["so_chuyen"] = 5
    with pytest.raises(GiaTriLoi, match="từ ngày mai"):
        gv.tao_gia_ve("t1", A, B, 400_000, HOM_NAY, None)
    assert moi_truong["da_tao"] == []


def test_tao_gia_bat_dau_hom_nay_khi_chua_co_chuyen_thi_duoc(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    gv.tao_gia_ve("t1", A, B, 400_000, HOM_NAY, None)
    assert moi_truong["da_tao"][0][-1] == HOM_QUA


def test_tao_gia_theo_mua_nam_gon_trong_gia_vo_thoi_han_bi_chan_vi_khong_tach_duoc(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    with pytest.raises(GiaTriLoi, match="chồng lấn"):
        gv.tao_gia_ve("t1", A, B, 450_000, NGAY_MAI, NGAY_MAI + datetime.timedelta(days=5))


# ---------- sửa ----------
def test_sua_gia_da_ap_dung_khi_gia_chua_co_chuyen_duoc_sua_tu_do(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 30_000)]
    gv.sua_gia_ve("g", 300_000, None, None, xac_nhan_canh_bao=True)
    assert moi_truong["da_sua"][0][1] == 300_000


def test_sua_so_tien_gia_da_ap_dung_khi_gia_da_co_chuyen_bi_chan(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    moi_truong["so_chuyen"] = 5
    with pytest.raises(GiaTriLoi, match="không sửa số tiền"):
        gv.sua_gia_ve("g", 400_000, None, None)
    assert moi_truong["da_sua"] == []


def test_dong_gia_da_ap_dung_bang_ngay_ket_thuc_khi_gia_da_co_chuyen_duoc(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    moi_truong["so_chuyen"] = 5
    gv.sua_gia_ve("g", 300_000, None, NGAY_MAI)
    assert moi_truong["da_sua"][0][3] == NGAY_MAI


def test_dong_gia_ve_ngay_trong_qua_khu_khi_gia_da_co_chuyen_bi_chan(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    moi_truong["so_chuyen"] = 5
    with pytest.raises(GiaTriLoi, match="trước hôm nay"):
        gv.sua_gia_ve("g", 300_000, None, HOM_QUA)


def test_sua_gia_chua_ap_dung_va_chua_co_chuyen_duoc_sua_tu_do(moi_truong):
    tu = NGAY_MAI + datetime.timedelta(days=9)
    moi_truong["dong"] = [dong("g", A, B, 300_000, tu=tu)]
    gv.sua_gia_ve("g", 350_000, tu, None)
    assert moi_truong["da_sua"][0][1] == 350_000


def test_sua_gia_sap_ap_dung_nhung_da_co_chuyen_trong_khoang_bi_khoa(moi_truong):
    tu = NGAY_MAI + datetime.timedelta(days=9)
    moi_truong["dong"] = [dong("g", A, B, 300_000, tu=tu)]
    moi_truong["so_chuyen"] = 3  # chuyến đã được sinh cho các ngày của giá này
    with pytest.raises(GiaTriLoi, match="3 chuyến"):
        gv.sua_gia_ve("g", 350_000, tu, None)


def test_sua_gia_da_ap_dung_chua_co_chuyen_nao_van_sua_duoc_du_chua_co_khach(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    moi_truong["so_chuyen"] = 0
    gv.sua_gia_ve("g", 320_000, None, None)
    assert moi_truong["da_sua"][0][1] == 320_000


# ---------- xóa ----------
def test_xoa_gia_da_ap_dung_khi_gia_da_co_chuyen_bi_chan(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    moi_truong["so_chuyen"] = 5
    with pytest.raises(GiaTriLoi, match="5 chuyến"):
        gv.xoa_gia_ve("g")
    assert moi_truong["da_xoa"] == []


def test_xoa_gia_chua_co_chuyen_nao_sinh_ra_thi_duoc(moi_truong):
    moi_truong["dong"] = [
        dong("cu", A, B, 300_000, den_ngay=NGAY_MAI),
        dong("moi", A, B, 400_000, tu=NGAY_MAI + datetime.timedelta(days=1)),
    ]
    gv.xoa_gia_ve("cu")  # dòng cũ chưa có chuyến nào sinh ra theo nó nên xóa được
    assert moi_truong["da_xoa"] == ["cu"]


def test_xoa_gia_don_gian_khi_tuyen_chua_co_chuyen_thi_duoc(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    gv.xoa_gia_ve("g")
    assert moi_truong["da_xoa"] == ["g"]


# ---------- cảnh báo giá bất thường ----------
def test_gia_qua_thap_bi_canh_bao_va_phai_xac_nhan(moi_truong):
    with pytest.raises(GiaTriLoi, match="bất thường"):
        gv.tao_gia_ve("t1", A, B, 30_000, None, None)
    assert moi_truong["da_tao"] == []
    gv.tao_gia_ve("t1", A, B, 30_000, None, None, xac_nhan_canh_bao=True)
    assert len(moi_truong["da_tao"]) == 1


def test_gia_giam_hon_mot_nua_so_voi_gia_hien_tai_bi_canh_bao(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    kq = gv.xem_truoc_tao_gia_ve("t1", A, B, 100_000, None, None)
    assert any("giảm hơn một nửa" in c for c in kq["canh_bao"])
    assert kq["gia_cu"]["se_ket_thuc_vao"] == HOM_NAY


def test_gia_tang_hon_gap_doi_bi_canh_bao(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    kq = gv.xem_truoc_tao_gia_ve("t1", A, B, 700_000, None, None)
    assert any("gấp đôi" in c for c in kq["canh_bao"])


def test_gia_doi_binh_thuong_khong_canh_bao(moi_truong):
    moi_truong["dong"] = [dong("cu", A, B, 300_000)]
    assert gv.xem_truoc_tao_gia_ve("t1", A, B, 340_000, None, None)["canh_bao"] == []


def test_chang_ngan_dat_hon_chang_dai_bi_canh_bao(moi_truong):
    moi_truong["dong"] = [dong("dai", A, C, 300_000)]  # A→C 300k
    kq = gv.xem_truoc_tao_gia_ve("t1", A, B, 350_000, NGAY_MAI, None)  # A→B (ngắn hơn) 350k > 300k
    assert any("Chặng dài hơn" in c for c in kq["canh_bao"])


def test_chang_dai_re_hon_chang_ngan_bi_canh_bao(moi_truong):
    moi_truong["dong"] = [dong("ngan", A, B, 250_000)]
    kq = gv.xem_truoc_tao_gia_ve("t1", A, C, 200_000, NGAY_MAI, None)
    assert any("Chặng ngắn hơn" in c for c in kq["canh_bao"])


def test_xem_truoc_sua_chi_canh_bao_khi_doi_so_tien(moi_truong):
    moi_truong["dong"] = [dong("g", A, B, 300_000)]
    assert gv.xem_truoc_sua_gia_ve("g", 300_000, None, NGAY_MAI)["canh_bao"] == []
    assert gv.xem_truoc_sua_gia_ve("g", 100_000, None, None)["canh_bao"]


# ---------- trạng thái dòng giá & danh sách ----------
def test_trang_thai_dong_gia():
    assert gv.trang_thai_dong_gia(dong("1", A, B, 1), HOM_NAY) == "dang_ap_dung"
    assert gv.trang_thai_dong_gia(dong("2", A, B, 1, tu=NGAY_MAI), HOM_NAY) == "sap_ap_dung"
    assert gv.trang_thai_dong_gia(dong("3", A, B, 1, den_ngay=HOM_QUA), HOM_NAY) == "da_ket_thuc"


def test_danh_sach_gia_ve_danh_dau_khoa_so_tien_khi_co_chuyen(moi_truong, monkeypatch):
    moi_truong["dong"] = [dong("dang", A, B, 300_000), dong("sap", A, B, 400_000, tu=NGAY_MAI + datetime.timedelta(days=5))]
    # chuyến chỉ được sinh trong khoảng của giá đang áp dụng (ap_dung_tu rỗng), chưa có chuyến nào cho giá sắp áp dụng
    monkeypatch.setattr(gv.repo, "so_chuyen_trong_khoang", lambda tuyen_id, tu, den: 5 if tu is None else 0)
    ds = {g["id"]: g for g in gv.danh_sach_gia_ve("t1")}
    assert ds["dang"]["khoa_so_tien"] is True and ds["dang"]["so_chuyen_da_sinh"] == 5 and ds["dang"]["trang_thai"] == "dang_ap_dung"
    assert ds["sap"]["khoa_so_tien"] is False and ds["sap"]["trang_thai"] == "sap_ap_dung"
