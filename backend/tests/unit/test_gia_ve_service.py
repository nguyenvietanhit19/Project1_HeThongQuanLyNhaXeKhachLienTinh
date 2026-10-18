"""Unit test bộ giá vé (UC-33): bộ đủ mọi chặng, có ngày bắt đầu + kết thúc bắt buộc, bộ mới nối liền bộ cuối, khóa bộ đã sinh
chuyến (riêng bộ cuối vẫn kéo dài/rút ngắn được), cảnh báo giá bất thường, kiểm tra giá phủ — giả lập repository bằng
monkeypatch, không cần DB."""

import datetime

import pytest

from app.services import gia_ve_service as gv
from app.utils.loi import GiaTriLoi

HOM_NAY = datetime.date(2026, 10, 15)
NGAY_MAI = HOM_NAY + datetime.timedelta(days=1)
HOM_QUA = HOM_NAY - datetime.timedelta(days=1)
A, B, C = "A", "B", "C"  # 3 khu vực của tuyến theo thứ tự A → B → C → 3 chặng: A-B, A-C, B-C


def ngay(so_ngay_tu_hom_nay: int) -> datetime.date:
    return HOM_NAY + datetime.timedelta(days=so_ngay_tu_hom_nay)


def cac_gia(ab=300_000, ac=500_000, bc=250_000):
    return [
        {"diem_di_id": A, "diem_den_id": B, "gia_goc": ab},
        {"diem_di_id": A, "diem_den_id": C, "gia_goc": ac},
        {"diem_di_id": B, "diem_den_id": C, "gia_goc": bc},
    ]


def gia_co_ten(ab=300_000, ac=500_000, bc=250_000):
    ten = {(A, B): ("KV-A", "KV-B"), (A, C): ("KV-A", "KV-C"), (B, C): ("KV-B", "KV-C")}
    return [dict(g, ten_diem_di=ten[(g["diem_di_id"], g["diem_den_id"])][0], ten_diem_den=ten[(g["diem_di_id"], g["diem_den_id"])][1])
            for g in cac_gia(ab, ac, bc)]


def bo(id_, tu, den, gia=None, tuyen="t1"):
    return {"id": id_, "tuyen_id": tuyen, "ten_tuyen": "Tuyến 1", "ma_tuyen": "T001", "ap_dung_tu": tu, "ap_dung_den": den,
            "ngay_tao": datetime.datetime(2026, 1, 1), "danh_sach_gia": gia if gia is not None else cac_gia()}


@pytest.fixture
def moi_truong(monkeypatch):
    """Dict điều khiển: bo (danh sách bộ), so_chuyen (số chuyến đã sinh trong khoảng được hỏi), chuyen_cuoi (ngày chuyến
    xa nhất); ghi lại các lần ghi DB."""
    tt = {"bo": [], "so_chuyen": 0, "chuyen_cuoi": None, "da_tao": [], "da_sua": [], "da_xoa": []}
    monkeypatch.setattr(gv, "hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(gv.dia_diem_repo, "tim_tuyen_theo_id", lambda _id: {"id": _id})
    monkeypatch.setattr(
        gv.dia_diem_repo, "danh_sach_diem_theo_tuyen",
        lambda _id: [{"khu_vuc_id": k, "ten_khu_vuc": f"KV-{k}", "thu_tu": i} for i, k in enumerate([A, B, C], 1)],
    )
    monkeypatch.setattr(gv.repo, "danh_sach_bo", lambda tuyen_id=None: [dict(b, danh_sach_gia=list(b["danh_sach_gia"])) for b in tt["bo"]])
    monkeypatch.setattr(gv.repo, "tim_bo_theo_id", lambda id_: next((dict(b) for b in tt["bo"] if b["id"] == id_), None))
    monkeypatch.setattr(gv.repo, "so_chuyen_trong_khoang", lambda tuyen_id, tu, den: tt["so_chuyen"])
    monkeypatch.setattr(gv.repo, "ngay_chuyen_cuoi_trong_khoang", lambda tuyen_id, tu, den: tt["chuyen_cuoi"])
    monkeypatch.setattr(gv.repo, "sua_bo", lambda *a: tt["da_sua"].append(a))
    monkeypatch.setattr(gv.repo, "xoa_bo", lambda id_: tt["da_xoa"].append(id_))

    def tao_roi_tra_ve(tuyen_id, tu, den, gia):
        tt["da_tao"].append((tuyen_id, tu, den, gia))
        tt["bo"].append(bo("moi", tu, den, [dict(g) for g in gia]))
        return "moi"

    monkeypatch.setattr(gv.repo, "tao_bo", tao_roi_tra_ve)
    return tt


# ---------- tạo bộ: ngày kết thúc bắt buộc, nối liền bộ cuối ----------
def test_tao_bo_dau_tien_bo_trong_ngay_bat_dau_thi_mac_dinh_ngay_mai(moi_truong):
    gv.tao_bo("t1", None, ngay(30), cac_gia())
    assert moi_truong["da_tao"][0][1:3] == (NGAY_MAI, ngay(30))


def test_tao_bo_khong_co_ngay_ket_thuc_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="ngày kết thúc"):
        gv.tao_bo("t1", None, None, cac_gia())


def test_tao_bo_ngay_ket_thuc_truoc_ngay_bat_dau_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="sau hoặc bằng ngày bắt đầu"):
        gv.tao_bo("t1", ngay(10), ngay(5), cac_gia())


def test_tao_bo_ngay_ket_thuc_o_qua_khu_bi_chan(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-40), ngay(-31))]  # bộ cũ đã hết từ lâu → bộ mới nối từ ngày -30
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        gv.tao_bo("t1", None, HOM_QUA, cac_gia())


def test_tao_bo_dau_tien_bat_dau_trong_qua_khu_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        gv.tao_bo("t1", HOM_QUA, ngay(30), cac_gia())


def test_tao_bo_thieu_chang_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="còn thiếu: KV-B → KV-C"):
        gv.tao_bo("t1", None, ngay(30), cac_gia()[:2])
    assert moi_truong["da_tao"] == []


def test_tao_bo_chang_sai_chieu_hoac_ngoai_tuyen_bi_chan(moi_truong):
    sai = cac_gia()[:2] + [{"diem_di_id": C, "diem_den_id": B, "gia_goc": 250_000}]
    with pytest.raises(GiaTriLoi, match="sai chiều"):
        gv.tao_bo("t1", None, ngay(30), sai)


def test_tao_bo_chang_bi_nhap_hai_lan_bi_chan(moi_truong):
    with pytest.raises(GiaTriLoi, match="2 lần"):
        gv.tao_bo("t1", None, ngay(30), cac_gia() + [{"diem_di_id": A, "diem_den_id": B, "gia_goc": 1}])


def test_tao_bo_ke_tiep_tu_dong_bat_dau_ngay_lien_sau_bo_truoc(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-5), ngay(20))]
    gv.tao_bo("t1", None, ngay(50), cac_gia())
    assert moi_truong["da_tao"][0][1:3] == (ngay(21), ngay(50))


def test_tao_bo_ke_tiep_ngay_bat_dau_khong_khop_bi_chan_va_bao_ngay_dung(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-5), ngay(20))]
    with pytest.raises(GiaTriLoi, match=ngay(21).strftime("%d/%m/%Y")):
        gv.tao_bo("t1", ngay(25), ngay(50), cac_gia())  # hở 4 ngày
    with pytest.raises(GiaTriLoi, match="phải bắt đầu từ ngày"):
        gv.tao_bo("t1", ngay(15), ngay(50), cac_gia())  # chồng lên bộ cũ
    assert moi_truong["da_tao"] == []


def test_tao_bo_ke_tiep_cho_phep_bat_dau_chinh_xac_ngay_lien_sau(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-5), ngay(20))]
    gv.tao_bo("t1", ngay(21), ngay(50), cac_gia())
    assert len(moi_truong["da_tao"]) == 1


def test_tao_bo_ke_tiep_khi_bo_cuoi_da_het_han_thi_bat_dau_o_qua_khu_nhung_van_noi_lien(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-40), ngay(-10))]  # hết hạn từ 10 ngày trước, chưa có chuyến nào ở các ngày đó
    gv.tao_bo("t1", None, ngay(30), cac_gia())
    assert moi_truong["da_tao"][0][1] == ngay(-9)


def test_tao_bo_bat_dau_hom_nay_khi_da_co_chuyen_tu_ngay_do_bi_chan(moi_truong):
    moi_truong["so_chuyen"] = 3
    with pytest.raises(GiaTriLoi, match="từ ngày mai"):
        gv.tao_bo("t1", HOM_NAY, ngay(30), cac_gia())
    assert moi_truong["da_tao"] == []


def test_tao_bo_bat_dau_hom_nay_khi_chua_co_chuyen_thi_duoc(moi_truong):
    gv.tao_bo("t1", HOM_NAY, ngay(30), cac_gia())
    assert moi_truong["da_tao"][0][1] == HOM_NAY


def test_xem_truoc_bo_noi_tiep_neu_bo_truoc_va_chang_doi_gia(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-30), ngay(9))]
    kq = gv.xem_truoc_tao_bo("t1", None, ngay(40), cac_gia(ab=320_000))
    assert kq["ap_dung_tu"] == ngay(10) and kq["ap_dung_den"] == ngay(40)
    assert kq["bo_truoc"] == {"ap_dung_tu": ngay(-30), "ap_dung_den": ngay(9)}
    doi = {c["ten_chang"]: (c["gia_cu"], c["gia_moi"]) for c in kq["thay_doi"]}
    assert doi["KV-A → KV-B"] == (300_000, 320_000)
    assert doi["KV-A → KV-C"] == (500_000, 500_000)


# ---------- sửa ----------
def test_sua_bo_chua_co_chuyen_nao_duoc_sua_gia(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(10), ngay(40))]
    gv.sua_bo("b", None, ngay(40), cac_gia(ab=310_000))
    assert moi_truong["da_sua"][0][3][0]["gia_goc"] == 310_000


def test_sua_bo_dau_tien_doi_duoc_ngay_bat_dau(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(10), ngay(40)), bo("c", ngay(41), ngay(70))]
    gv.sua_bo("b", ngay(12), ngay(40), cac_gia())
    assert moi_truong["da_sua"][0][1] == ngay(12)


def test_sua_bo_o_giua_khong_doi_duoc_ngay_ket_thuc_hay_ngay_bat_dau(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(10), ngay(40)), bo("b", ngay(41), ngay(70)), bo("c", ngay(71), ngay(100))]
    with pytest.raises(GiaTriLoi, match="bộ giá cuối cùng"):
        gv.sua_bo("b", None, ngay(60), cac_gia())
    with pytest.raises(GiaTriLoi, match="bộ giá đầu tiên"):
        gv.sua_bo("b", ngay(45), ngay(70), cac_gia())
    assert moi_truong["da_sua"] == []


def test_sua_gia_bo_o_giua_chua_khoa_van_duoc_khi_giu_nguyen_ngay(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(10), ngay(40)), bo("b", ngay(41), ngay(70))]
    gv.sua_bo("a", None, ngay(40), cac_gia(ab=310_000))
    assert len(moi_truong["da_sua"]) == 1


def test_sua_bo_cuoi_doi_duoc_ngay_ket_thuc(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(10), ngay(40))]
    gv.sua_bo("a", None, ngay(60), cac_gia())
    assert moi_truong["da_sua"][0][2] == ngay(60)


def test_sua_bo_da_co_chuyen_khong_doi_duoc_gia(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40))]
    moi_truong["so_chuyen"] = 20
    with pytest.raises(GiaTriLoi, match="20 chuyến"):
        gv.sua_bo("b", None, ngay(40), cac_gia(ab=310_000))
    assert moi_truong["da_sua"] == []


def test_sua_bo_cuoi_da_khoa_van_keo_dai_duoc_ngay_ket_thuc_khi_giu_nguyen_gia(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40))]
    moi_truong["so_chuyen"] = 20
    moi_truong["chuyen_cuoi"] = ngay(38)
    gv.sua_bo("b", None, ngay(90), cac_gia())
    assert moi_truong["da_sua"][0][2] == ngay(90)


def test_sua_bo_cuoi_da_khoa_rut_ngan_khong_duoc_truoc_chuyen_da_sinh(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40))]
    moi_truong["so_chuyen"] = 20
    moi_truong["chuyen_cuoi"] = ngay(38)
    with pytest.raises(GiaTriLoi, match=ngay(38).strftime("%d/%m/%Y")):
        gv.sua_bo("b", None, ngay(30), cac_gia())
    gv.sua_bo("b", None, ngay(38), cac_gia())  # đúng ngày chuyến cuối thì được
    assert moi_truong["da_sua"][0][2] == ngay(38)


def test_sua_bo_khong_phai_cuoi_da_khoa_khong_doi_duoc_gi(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(-30), ngay(40)), bo("b", ngay(41), ngay(70))]
    moi_truong["so_chuyen"] = 5
    with pytest.raises(GiaTriLoi, match="5 chuyến"):
        gv.sua_bo("a", None, ngay(40), cac_gia(ab=999_999))


def test_xem_truoc_sua_bo_da_khoa_doi_gia_cung_bi_chan(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40))]
    moi_truong["so_chuyen"] = 1
    with pytest.raises(GiaTriLoi, match="không sửa giá"):
        gv.xem_truoc_sua_bo("b", None, ngay(40), cac_gia(ab=1_000_000))


def test_sua_bo_dau_doi_ngay_bat_dau_ve_qua_khu_bi_chan(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(10), ngay(40))]
    with pytest.raises(GiaTriLoi, match="quá khứ"):
        gv.sua_bo("b", HOM_QUA, ngay(40), cac_gia())


# ---------- xóa ----------
def test_xoa_bo_cuoi_chua_co_chuyen_thi_duoc(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(1), ngay(10)), bo("b", ngay(11), ngay(20))]
    gv.xoa_bo("b")
    assert moi_truong["da_xoa"] == ["b"]


def test_xoa_bo_o_giua_bi_chan_vi_lam_ho_giua_cac_bo(moi_truong):
    moi_truong["bo"] = [bo("a", ngay(1), ngay(10)), bo("b", ngay(11), ngay(20))]
    with pytest.raises(GiaTriLoi, match="bộ giá cuối cùng"):
        gv.xoa_bo("a")
    assert moi_truong["da_xoa"] == []


def test_xoa_bo_cuoi_da_co_chuyen_bi_chan(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40))]
    moi_truong["so_chuyen"] = 7
    with pytest.raises(GiaTriLoi, match="7 chuyến"):
        gv.xoa_bo("b")
    assert moi_truong["da_xoa"] == []


def test_xoa_bo_khong_ton_tai(moi_truong):
    with pytest.raises(GiaTriLoi, match="Không tìm thấy"):
        gv.xoa_bo("khong-co")


# ---------- cảnh báo giá bất thường ----------
def test_gia_qua_thap_bi_canh_bao_va_phai_xac_nhan(moi_truong):
    gia = cac_gia(ab=30_000)
    with pytest.raises(GiaTriLoi, match="bất thường"):
        gv.tao_bo("t1", None, ngay(30), gia)
    assert moi_truong["da_tao"] == []
    gv.tao_bo("t1", None, ngay(30), gia, xac_nhan_canh_bao=True)
    assert len(moi_truong["da_tao"]) == 1


def test_gia_giam_hon_mot_nua_so_voi_bo_truoc_bi_canh_bao(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-30), ngay(4))]
    kq = gv.xem_truoc_tao_bo("t1", None, ngay(40), cac_gia(ab=100_000, ac=400_000, bc=250_000))  # A-B: 300k → 100k
    assert any("KV-A → KV-B" in c and "giảm hơn một nửa" in c for c in kq["canh_bao"])


def test_gia_tang_hon_gap_doi_so_voi_bo_truoc_bi_canh_bao(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-30), ngay(4))]
    kq = gv.xem_truoc_tao_bo("t1", None, ngay(40), cac_gia(ab=700_000, ac=800_000))  # A-B: 300k → 700k
    assert any("KV-A → KV-B" in c and "gấp đôi" in c for c in kq["canh_bao"])


def test_doi_gia_binh_thuong_khong_canh_bao(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-30), ngay(4))]
    assert gv.xem_truoc_tao_bo("t1", None, ngay(40), cac_gia(ab=320_000))["canh_bao"] == []


def test_chang_ngan_dat_hon_chang_dai_trong_cung_bo_bi_canh_bao(moi_truong):
    kq = gv.xem_truoc_tao_bo("t1", None, ngay(30), cac_gia(ab=600_000, ac=500_000))  # A-B (ngắn) 600k > A-C (dài) 500k
    assert any("chặng ngắn hơn" in c and "KV-A → KV-B" in c for c in kq["canh_bao"])


def test_bo_dau_tien_khong_so_sanh_voi_bo_truoc(moi_truong):
    assert gv.xem_truoc_tao_bo("t1", None, ngay(30), cac_gia())["canh_bao"] == []


def test_keo_dai_ngay_ket_thuc_khong_doi_gia_thi_khong_canh_bao_hay_doi_xac_nhan(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40), cac_gia(ab=30_000))]  # giá cũ "bất thường" nhưng không đụng tới
    moi_truong["so_chuyen"] = 3
    gv.sua_bo("b", None, ngay(60), cac_gia(ab=30_000))
    assert len(moi_truong["da_sua"]) == 1


# ---------- trạng thái, danh sách, khoảng có giá ----------
def test_trang_thai_bo():
    assert gv.trang_thai_bo(ngay(-5), ngay(10), HOM_NAY) == "dang_ap_dung"
    assert gv.trang_thai_bo(ngay(3), ngay(10), HOM_NAY) == "sap_ap_dung"
    assert gv.trang_thai_bo(ngay(-9), ngay(-1), HOM_NAY) == "da_ket_thuc"
    assert gv.trang_thai_bo(ngay(-9), HOM_NAY, HOM_NAY) == "dang_ap_dung"  # ngày kết thúc tính luôn


def test_danh_sach_bo_danh_dau_bo_cuoi_khoa_va_ngay_chuyen_cuoi(moi_truong):
    moi_truong["bo"] = [bo("hai", ngay(11), ngay(40)), bo("mot", ngay(-20), ngay(10))]  # cố ý đảo thứ tự
    moi_truong["so_chuyen"] = 4
    moi_truong["chuyen_cuoi"] = ngay(9)
    ds = {b["id"]: b for b in gv.danh_sach_bo("t1")}
    assert ds["mot"]["trang_thai"] == "dang_ap_dung" and ds["hai"]["trang_thai"] == "sap_ap_dung"
    assert ds["mot"]["la_bo_cuoi"] is False and ds["hai"]["la_bo_cuoi"] is True
    assert ds["mot"]["khoa"] is True and ds["mot"]["so_chuyen_da_sinh"] == 4 and ds["mot"]["ngay_chuyen_cuoi"] == ngay(9)
    assert ds["mot"]["cac_cap_thieu_gia"] == []


def test_khoang_ngay_co_gia(moi_truong):
    assert gv.khoang_ngay_co_gia("t1") is None
    moi_truong["bo"] = [bo("b", ngay(11), ngay(40)), bo("a", ngay(-5), ngay(10))]
    assert gv.khoang_ngay_co_gia("t1") == (ngay(-5), ngay(40))


def test_ngay_chua_co_gia_truoc_bo_dau_sau_bo_cuoi_va_khi_chua_co_bo(moi_truong):
    assert gv.ngay_chua_co_gia("t1", [HOM_NAY]) == [HOM_NAY]  # chưa có bộ nào
    moi_truong["bo"] = [bo("b", NGAY_MAI, ngay(10))]
    assert gv.ngay_chua_co_gia("t1", [HOM_NAY, NGAY_MAI, ngay(10), ngay(11)]) == [HOM_NAY, ngay(11)]


def test_ngay_chua_co_gia_bo_thieu_chang_cung_tinh_la_chua_co(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(10), cac_gia()[:2])]
    assert gv.ngay_chua_co_gia("t1", [HOM_NAY]) == [HOM_NAY]


def test_cac_cap_thieu_gia(moi_truong):
    assert gv.cac_cap_thieu_gia("t1") == ["KV-A → KV-B", "KV-A → KV-C", "KV-B → KV-C"]  # chưa có bộ nào
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(10), cac_gia()[:2])]
    assert gv.cac_cap_thieu_gia("t1") == ["KV-B → KV-C"]
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(10))]
    assert gv.cac_cap_thieu_gia("t1") == []
    moi_truong["bo"] = [bo("b", ngay(-50), ngay(-10))]  # bộ duy nhất đã hết hạn → coi như chưa có giá
    assert len(gv.cac_cap_thieu_gia("t1")) == 3


# ---------- bảng giá hiển thị ở chi tiết chuyến ----------
def test_bang_gia_chuyen_di_doc_theo_chieu_di_va_nhan_he_so(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40), gia_co_ten())]
    kq = gv.bang_gia_cua_chuyen("t1", "xuoi", HOM_NAY, "1.5")
    assert [(c["ten_chang"], c["gia_goc"], c["gia_ban"]) for c in kq["cac_chang"]] == [
        ("KV-A → KV-B", 300_000, 450_000), ("KV-A → KV-C", 500_000, 750_000), ("KV-B → KV-C", 250_000, 375_000)]
    assert kq["ap_dung_tu"] == ngay(-5)


def test_bang_gia_chuyen_ve_dao_chang_va_sap_theo_hanh_trinh_chieu_ve(moi_truong):
    moi_truong["bo"] = [bo("b", ngay(-5), ngay(40), gia_co_ten())]
    kq = gv.bang_gia_cua_chuyen("t1", "nguoc", HOM_NAY, "1")
    assert [c["ten_chang"] for c in kq["cac_chang"]] == ["KV-C → KV-B", "KV-C → KV-A", "KV-B → KV-A"]
    assert [c["gia_ban"] for c in kq["cac_chang"]] == [250_000, 500_000, 300_000]


def test_bang_gia_chuyen_lay_bo_theo_ngay_khoi_hanh_cua_chuyen(moi_truong):
    moi_truong["bo"] = [bo("cu", ngay(-30), HOM_NAY, gia_co_ten(ab=300_000)), bo("moi", NGAY_MAI, ngay(30), gia_co_ten(ab=400_000))]
    assert gv.bang_gia_cua_chuyen("t1", "xuoi", HOM_NAY, "1")["cac_chang"][0]["gia_ban"] == 300_000
    assert gv.bang_gia_cua_chuyen("t1", "nguoc", NGAY_MAI, "1")["cac_chang"][-1]["gia_ban"] == 400_000  # chuyến về +1 ngày: bộ mới


def test_bang_gia_chuyen_ngoai_moi_bo_thi_none(moi_truong):
    assert gv.bang_gia_cua_chuyen("t1", "xuoi", HOM_NAY, "1") is None
    moi_truong["bo"] = [bo("b", NGAY_MAI, ngay(10))]
    assert gv.bang_gia_cua_chuyen("t1", "xuoi", HOM_NAY, "1") is None  # trước bộ đầu
    assert gv.bang_gia_cua_chuyen("t1", "xuoi", ngay(11), "1") is None  # sau bộ cuối
