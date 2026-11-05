"""Unit test cho job nhắc quản lý sinh thêm chuyến / tạo bộ giá nối tiếp (jobs/nhac_quan_ly.py) — giả lập Repository bằng
monkeypatch, không cần DB thật."""

import datetime

import pytest

from app.jobs import nhac_quan_ly as job

HOM_NAY = datetime.date(2026, 10, 23)


def ngay(so_ngay_nua: int) -> datetime.date:
    return HOM_NAY + datetime.timedelta(days=so_ngay_nua)


def cap(ngay_cuoi, ten_tuyen="Hà Nội - Bắc Hà", tuyen_id="tuyen-1", cap_id="cap-1"):
    return {"cap_id": cap_id, "tuyen_id": tuyen_id, "ma_tuyen": "T002", "ten_tuyen": ten_tuyen,
            "gio_di": datetime.time(8, 0), "gio_ve": datetime.time(16, 0), "ngay_chuyen_cuoi": ngay_cuoi}


# ---------------------------------------------------------------- nội dung nhắc sinh chuyến
def test_cap_chua_sinh_chuyen_nao_duoc_nhac():
    nd = job.noi_dung_nhac_sinh_chuyen(cap(None), HOM_NAY)
    assert "chưa sinh chuyến nào" in nd and "Hà Nội - Bắc Hà" in nd and "đi 08:00 / về 16:00" in nd


def test_cap_da_het_chuyen_duoc_nhac_kem_ngay_het():
    nd = job.noi_dung_nhac_sinh_chuyen(cap(ngay(-2)), HOM_NAY)
    assert "đã hết chuyến từ ngày 21/10/2026" in nd


@pytest.mark.parametrize("con_ngay", [0, 1, 7])
def test_cap_sap_het_chuyen_trong_nguong_duoc_nhac_kem_ngay_cuoi(con_ngay):
    nd = job.noi_dung_nhac_sinh_chuyen(cap(ngay(con_ngay)), HOM_NAY)
    assert nd is not None and f"chỉ còn chuyến đến ngày {ngay(con_ngay):%d/%m/%Y}" in nd


def test_cap_con_nhieu_chuyen_khong_nhac():
    assert job.noi_dung_nhac_sinh_chuyen(cap(ngay(8)), HOM_NAY) is None


def test_noi_dung_nhac_khong_chua_so_ngay_con_lai_de_khong_bao_lap_moi_ngay():
    # nội dung chỉ phụ thuộc NGÀY CUỐI, không phụ thuộc hôm nay → hôm sau (cùng tình trạng) vẫn cùng nội dung → bị bỏ qua
    assert job.noi_dung_nhac_sinh_chuyen(cap(ngay(5)), HOM_NAY) == job.noi_dung_nhac_sinh_chuyen(cap(ngay(5)), ngay(1))


def test_nguong_nhac_sinh_chuyen_tuy_chinh():
    assert job.noi_dung_nhac_sinh_chuyen(cap(ngay(10)), HOM_NAY, nguong_ngay=14) is not None
    assert job.noi_dung_nhac_sinh_chuyen(cap(ngay(10)), HOM_NAY, nguong_ngay=3) is None


# ---------------------------------------------------------------- nội dung nhắc bộ giá
def test_tuyen_chua_co_bo_gia_duoc_nhac():
    assert "chưa có bộ giá vé nào" in job.noi_dung_nhac_bo_gia("Hà Nội - Bắc Hà", None, HOM_NAY)


def test_bo_gia_da_ket_thuc_duoc_nhac():
    nd = job.noi_dung_nhac_bo_gia("Hà Nội - Bắc Hà", (ngay(-30), ngay(-1)), HOM_NAY)
    assert "đã kết thúc ngày 22/10/2026" in nd


@pytest.mark.parametrize("con_ngay", [0, 5, 14])
def test_bo_gia_sap_het_trong_nguong_duoc_nhac(con_ngay):
    nd = job.noi_dung_nhac_bo_gia("Hà Nội - Bắc Hà", (ngay(-30), ngay(con_ngay)), HOM_NAY)
    assert nd is not None and f"sẽ kết thúc ngày {ngay(con_ngay):%d/%m/%Y}" in nd


def test_bo_gia_con_dai_khong_nhac():
    assert job.noi_dung_nhac_bo_gia("Hà Nội - Bắc Hà", (ngay(-30), ngay(15)), HOM_NAY) is None


# ---------------------------------------------------------------- chay()
@pytest.fixture
def moi_truong(monkeypatch):
    """Giả lập: 2 quản lý, danh sách cặp lịch do test đặt, khoảng giá do test đặt, ghi lại các thông báo đã gửi."""
    trang_thai = {"cac_cap": [], "khoang_gia": {}, "da_co": set(), "da_gui": [], "nguoi_nhan": ["ql-1", "ql-2"]}
    monkeypatch.setattr(job.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vai_tro, chi_dang_hoat_dong=False: trang_thai["nguoi_nhan"])
    monkeypatch.setattr(job.lich_chay_repository, "cac_cap_dang_ap_dung_kem_ngay_chuyen_cuoi", lambda: trang_thai["cac_cap"])
    monkeypatch.setattr(job.gia_ve_service, "khoang_ngay_co_gia", lambda tuyen_id: trang_thai["khoang_gia"].get(tuyen_id))
    monkeypatch.setattr(job.thong_bao_repo, "da_co_thong_bao_giong", lambda nguoi_id, noi_dung: (nguoi_id, noi_dung) in trang_thai["da_co"])
    monkeypatch.setattr(job.thong_bao, "gui", lambda nguoi_id, noi_dung, ve_id=None, duong_dan=None: trang_thai["da_gui"].append((nguoi_id, noi_dung, duong_dan)))
    return trang_thai


def test_chay_khong_co_quan_ly_nao_thi_khong_lam_gi(moi_truong):
    moi_truong["nguoi_nhan"] = []
    moi_truong["cac_cap"] = [cap(None)]
    assert job.chay(HOM_NAY) == (0, 0)
    assert moi_truong["da_gui"] == []


def test_chay_gui_cho_tung_quan_ly_kem_duong_dan_dung_trang(moi_truong):
    moi_truong["cac_cap"] = [cap(ngay(3))]
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(5))}
    assert job.chay(HOM_NAY) == (1, 1)
    gui = moi_truong["da_gui"]
    assert len(gui) == 4  # 2 quản lý × (1 nhắc sinh chuyến + 1 nhắc bộ giá)
    assert {(n, d) for n, _, d in gui} == {("ql-1", job.DUONG_DAN_LICH_CHAY), ("ql-2", job.DUONG_DAN_LICH_CHAY),
                                          ("ql-1", job.DUONG_DAN_GIA_VE), ("ql-2", job.DUONG_DAN_GIA_VE)}


def test_chay_chi_nhac_dung_muc_can_nhac(moi_truong):
    moi_truong["cac_cap"] = [cap(ngay(20), tuyen_id="tuyen-1", cap_id="cap-1"), cap(ngay(2), ten_tuyen="Hà Nội - Vinh", tuyen_id="tuyen-2", cap_id="cap-2")]
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(90)), "tuyen-2": (ngay(-60), ngay(90))}
    assert job.chay(HOM_NAY) == (1, 0)
    assert all("Hà Nội - Vinh" in nd for _, nd, _ in moi_truong["da_gui"])


def test_chay_bo_qua_nguoi_da_nhan_dung_noi_dung_roi(moi_truong):
    moi_truong["cac_cap"] = [cap(ngay(3))]
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(90))}
    nd = job.noi_dung_nhac_sinh_chuyen(moi_truong["cac_cap"][0], HOM_NAY)
    moi_truong["da_co"] = {("ql-1", nd)}
    assert job.chay(HOM_NAY) == (1, 0)
    assert [n for n, _, _ in moi_truong["da_gui"]] == ["ql-2"]  # ql-1 đã nhận rồi nên bỏ qua


def test_chay_tat_ca_da_nhan_roi_thi_dem_la_0(moi_truong):
    moi_truong["cac_cap"] = [cap(ngay(3))]
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(90))}
    nd = job.noi_dung_nhac_sinh_chuyen(moi_truong["cac_cap"][0], HOM_NAY)
    moi_truong["da_co"] = {("ql-1", nd), ("ql-2", nd)}
    assert job.chay(HOM_NAY) == (0, 0)
    assert moi_truong["da_gui"] == []


def test_chay_nhac_bo_gia_moi_tuyen_mot_lan_du_co_nhieu_cap_lich(moi_truong):
    moi_truong["cac_cap"] = [cap(ngay(30), cap_id="cap-1"), cap(ngay(30), cap_id="cap-2")]  # cùng tuyen-1
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(3))}
    assert job.chay(HOM_NAY) == (0, 1)
    assert len(moi_truong["da_gui"]) == 2  # 1 nội dung × 2 quản lý


def test_chay_loi_o_mot_muc_khong_chan_cac_muc_con_lai(moi_truong, monkeypatch):
    moi_truong["cac_cap"] = [cap(ngay(3), tuyen_id="tuyen-1", cap_id="cap-1"), cap(ngay(3), ten_tuyen="Hà Nội - Vinh", tuyen_id="tuyen-2", cap_id="cap-2")]
    moi_truong["khoang_gia"] = {"tuyen-1": (ngay(-60), ngay(90)), "tuyen-2": (ngay(-60), ngay(90))}
    goc = job.thong_bao_repo.da_co_thong_bao_giong

    def hong_o_tuyen_dau(nguoi_id, noi_dung):
        if "Hà Nội - Bắc Hà" in noi_dung:
            raise RuntimeError("db loi")
        return goc(nguoi_id, noi_dung)

    monkeypatch.setattr(job.thong_bao_repo, "da_co_thong_bao_giong", hong_o_tuyen_dau)
    assert job.chay(HOM_NAY) == (1, 0)  # cặp thứ nhất lỗi (ghi log), cặp thứ hai vẫn được nhắc
